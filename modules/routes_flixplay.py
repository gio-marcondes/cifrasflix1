import re
import sqlite3
import time
import random
from pathlib import Path
from flask import Blueprint, jsonify, request, render_template, session, url_for, redirect

from modules.layout import header
from modules.config import DB, connect_db, slugify, normalizar_slug

flixplay_bp = Blueprint('flixplay', __name__)


def titulo_base(titulo):
    return re.sub(r'\s*\(.*?\)', '', titulo).strip().lower()


def _normalizar_guitarpro_nome(texto):
    import unicodedata

    if not texto:
        return ""

    ascii_text = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    ascii_text = ascii_text.lower().strip()
    ascii_text = re.sub(r"[\'\u00b4`]+", "", ascii_text)
    ascii_text = re.sub(r"\s*\(.*?\)", " ", ascii_text)
    return re.sub(r"[^a-z0-9]+", " ", ascii_text).strip()


def _guitarpro_index_file_path():
    return Path("static") / "_gp_index.txt"


def _refresh_guitarpro_index_txt(max_age_seconds=86400):
    base_dir = Path("static") / "guitarpro"
    idx_path = _guitarpro_index_file_path()
    extensoes = {".gp", ".gp3", ".gp4", ".gp5", ".gpx"}

    print(f"[FlixPlay Indexer] Procurando em: {base_dir.resolve()} | Existe: {base_dir.exists()}")
    if not base_dir.exists():
        print(f"[FlixPlay Indexer] Erro: Pasta {base_dir.resolve()} nao existe!")
        return

    precisa_rebuild = True
    if idx_path.exists() and idx_path.stat().st_size > 0:
        try:
            dir_mtime = base_dir.stat().st_mtime
            idx_mtime = idx_path.stat().st_mtime
            idade = time.time() - idx_mtime
            precisa_rebuild = (dir_mtime > idx_mtime) or (idade > max_age_seconds)
        except Exception:
            precisa_rebuild = True

    if not precisa_rebuild:
        return

    linhas = []
    for arquivo in base_dir.iterdir():
        if not arquivo.is_file() or arquivo.suffix.lower() not in extensoes:
            continue

        stem = arquivo.stem.strip()
        if " - " in stem:
            artista_nome, musica_nome = stem.split(" - ", 1)
        elif "-" in stem:
            artista_nome, musica_nome = stem.split("-", 1)
        else:
            artista_nome, musica_nome = "", stem

        artista_norm = _normalizar_guitarpro_nome(artista_nome)
        musica_norm = _normalizar_guitarpro_nome(musica_nome)
        if not musica_norm:
            continue

        linhas.append(
            "\t".join(
                [
                    artista_norm,
                    musica_norm,
                    arquivo.name,
                    (artista_nome or "").strip().replace("\t", " "),
                    (musica_nome or "").strip().replace("\t", " "),
                ]
            )
        )

    try:
        idx_path.write_text("\n".join(linhas), encoding="utf-8")
        print(f"[FlixPlay Indexer] Indice de arquivos GP atualizado com {len(linhas)} musicas.")
    except Exception as e:
        print(f"[FlixPlay Indexer] Erro ao escrever indice: {e}")


_GUITARPRO_INDEX_CACHE = None
_GUITARPRO_INDEX_CACHE_MTIME = None

def _guitarpro_index():
    global _GUITARPRO_INDEX_CACHE, _GUITARPRO_INDEX_CACHE_MTIME

    _refresh_guitarpro_index_txt()
    idx_path = _guitarpro_index_file_path()
    index = {}

    if not idx_path.exists():
        _GUITARPRO_INDEX_CACHE = index
        _GUITARPRO_INDEX_CACHE_MTIME = None
        return _GUITARPRO_INDEX_CACHE

    try:
        mtime = idx_path.stat().st_mtime
    except Exception:
        mtime = None

    if _GUITARPRO_INDEX_CACHE is not None and _GUITARPRO_INDEX_CACHE_MTIME == mtime:
        return _GUITARPRO_INDEX_CACHE

    try:
        conteudo = idx_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        conteudo = ""

    for linha in conteudo.splitlines():
        if not linha.strip():
            continue
        partes = linha.split("\t")
        if len(partes) < 2:
            continue
        artista_norm = (partes[0] or "").strip()
        musica_norm = (partes[1] or "").strip()
        if not artista_norm or not musica_norm:
            continue
        index.setdefault(artista_norm, set()).add(musica_norm)

    _GUITARPRO_INDEX_CACHE = index
    _GUITARPRO_INDEX_CACHE_MTIME = mtime
    return _GUITARPRO_INDEX_CACHE


def _has_flixplayer_tab(artista_nome, musica_titulo):
    tracks = _guitarpro_index().get(_normalizar_guitarpro_nome(artista_nome), set())
    if not tracks:
        return False

    titulo_norm = _normalizar_guitarpro_nome(musica_titulo)
    titulo_base_norm = _normalizar_guitarpro_nome(titulo_base(musica_titulo))

    if titulo_norm in tracks or titulo_base_norm in tracks:
        return True

    for track_norm in tracks:
        if titulo_norm and (titulo_norm in track_norm or track_norm in titulo_norm):
            return True
        if titulo_base_norm and (titulo_base_norm in track_norm or track_norm in titulo_base_norm):
            return True

    return False


_GP_CATALOGO_CACHE = None
_GP_CATALOGO_CACHE_MTIME = None

def _obter_gp_catalogo_cacheado():
    global _GP_CATALOGO_CACHE, _GP_CATALOGO_CACHE_MTIME

    _refresh_guitarpro_index_txt()
    idx_path = _guitarpro_index_file_path()
    if not idx_path.exists():
        return []

    try:
        mtime = idx_path.stat().st_mtime
    except Exception:
        mtime = None

    if _GP_CATALOGO_CACHE is not None and _GP_CATALOGO_CACHE_MTIME == mtime:
        return _GP_CATALOGO_CACHE

    def limpar_titulo_gp(texto):
        valor = (texto or "").strip()
        if not valor:
            return ""
        valor = re.sub(r"\(([^)]*?)\s+by\s+[^)]*\)", r"(\1)", valor, flags=re.IGNORECASE)
        valor = re.sub(r"\s{2,}", " ", valor).strip()
        return valor

    vistos = set()
    catalogo = []
    try:
        conteudo = idx_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return []

    for linha in conteudo.splitlines():
        if not linha.strip():
            continue
        partes = linha.split("\t")
        if len(partes) < 5:
            continue

        artista_norm = (partes[0] or "").strip()
        musica_norm = (partes[1] or "").strip()
        file_name = (partes[2] or "").strip()
        artista_raw = (partes[3] or "").strip()
        musica_raw = (partes[4] or "").strip()
        if not musica_norm or not file_name:
            continue

        chave = (artista_norm, musica_norm)
        if chave in vistos:
            continue
        vistos.add(chave)

        catalogo.append(
            {
                "artista_nome": artista_raw or artista_norm.title(),
                "musica_titulo": limpar_titulo_gp(musica_raw or musica_norm.title()),
                "artista_norm": artista_norm,
                "musica_norm": musica_norm,
            }
        )

    print(f"[FlixPlay] Catalogo GP carregado em memoria com {len(catalogo)} musicas.")
    _GP_CATALOGO_CACHE = catalogo
    _GP_CATALOGO_CACHE_MTIME = mtime
    return _GP_CATALOGO_CACHE


@flixplay_bp.route("/flix-play")
def flix_play():
    import html as html_escape
    q = (request.args.get("q") or "").strip()

    catalogo_gp = _obter_gp_catalogo_cacheado()

    sugestoes = random.sample(catalogo_gp, min(6, len(catalogo_gp))) if catalogo_gp else []

    def _card_html(row):
        titulo = (row["musica_titulo"] or "").strip()
        artista_nome = (row["artista_nome"] or "").strip()
        artista_slug = normalizar_slug(artista_nome)
        lyric_link = f"/letra/{artista_slug}/{normalizar_slug(titulo)}"
        play_link = f"/tocador-gp4/{artista_slug}/{normalizar_slug(titulo)}"
        train_link = f"/treinar/{artista_slug}/{normalizar_slug(titulo)}"
        destino = play_link
        acao_html = f'<a class="flixCardAction" href="{play_link}">Tocar no FlixPlayer</a>'

        return f"""
        <article class="flixSongCard" role="button" tabindex="0" onclick="location.href='{destino}'" onkeydown="if(event.key==='Enter'||event.key===' '){{event.preventDefault();location.href='{destino}'}}">
            <div class="flixSongInfo">
                <p class="eyebrow">{html_escape.escape(artista_nome)}</p>
                <h3><a href="{play_link}">{html_escape.escape(titulo)}</a></h3>
                <div class="flixCardLinks">
                    {acao_html}
                    <a class="flixCardAction ghost" href="{lyric_link}">Ver letra</a>
                    <a class="flixCardAction alt" href="{train_link}">Treinar</a>
                </div>
            </div>
        </article>
        """

    html = header("Flix Play") + f"""
    <style>
    .flixHero {{
        margin-top: 18px;
        padding: 24px;
        border-radius: 16px;
        border: 1px solid #e5e7eb;
        background: radial-gradient(circle at 16% -20%, rgba(255, 122, 0, 0.18), transparent 45%), #ffffff;
    }}
    .flixHero h1 {{
        margin: 0;
        font-size: clamp(30px, 4vw, 48px);
    }}
    .flixHero p {{
        margin: 10px 0 0;
        color: #6b7280;
        max-width: 760px;
    }}
    .flixSearchBar {{
        margin-top: 18px;
        display: grid;
        grid-template-columns: minmax(0, 1fr) auto;
        gap: 10px;
    }}
    .flixSearchBar input {{
        height: 46px;
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 0 14px;
        font-size: 15px;
        background: var(--bg);
        color: var(--text);
    }}
    .flixSearchBar button {{
        height: 46px;
        border-radius: 12px;
        border: 1px solid var(--accent);
        background: var(--accent);
        color: #fff;
        font-weight: 800;
        padding: 0 18px;
        cursor: pointer;
    }}
    .flixQuickActions {{
        margin-top: 10px;
        display: flex;
        gap: 8px;
        flex-wrap: wrap;
    }}
    .flixQuickBtn {{
        display: inline-flex;
        align-items: center;
        justify-content: center;
        min-height: 34px;
        border-radius: 999px;
        border: 1px solid #cbd5e1;
        background: #f8fafc;
        color: #334155;
        padding: 0 12px;
        font-size: 12px;
        font-weight: 800;
        text-decoration: none;
    }}
    .flixSection {{
        margin-top: 22px;
    }}
    .flixSuggestionsSection {{
        border: 1px solid #c7d2fe;
        border-radius: 18px;
        padding: 16px;
        background: linear-gradient(160deg, #eef2ff 0%, #f8fafc 52%, #ecfeff 100%);
    }}
    .flixSuggestionsSection .sectionHeader h2 {{
        color: #312e81;
    }}
    .flixSuggestionsSection .eyebrow {{
        color: #4338ca;
        font-weight: 800;
        letter-spacing: .04em;
    }}
    .flixSuggestionsSection .flixSongCard {{
        border-color: #c7d2fe;
        background: linear-gradient(180deg, #ffffff 0%, #f8faff 100%);
        box-shadow: 0 8px 22px rgba(79, 70, 229, 0.10);
    }}
    .flixSuggestionsSection .flixSongCard:hover {{
        border-color: #6366f1;
        box-shadow: 0 12px 26px rgba(79, 70, 229, 0.16);
    }}
    .flixSuggestionsSection .flixCardAction {{
        border-color: #818cf8;
        background: #eef2ff;
        color: #3730a3;
    }}
    .flixSuggestionsSection .flixCardAction.ghost {{
        border-color: #c7d2fe;
        background: #ffffff;
        color: #312e81;
    }}
    .flixGrid {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
        gap: 12px;
    }}
    .flixSongCard {{
        display: block;
        border: 1px solid #e5e7eb;
        border-radius: 14px;
        background: #ffffff;
        padding: 12px;
        cursor: pointer;
        transition: border-color .16s ease, transform .16s ease, box-shadow .16s ease;
    }}
    .flixSongCard:hover {{
        border-color: #fdba74;
        transform: translateY(-1px);
        box-shadow: 0 8px 20px rgba(15, 23, 42, 0.08);
    }}
    .flixSongInfo h3 {{
        margin: 0;
        font-size: 17px;
        line-height: 1.25;
    }}
    .flixSongInfo h3 a {{
        color: inherit;
        text-decoration: none;
    }}
    .flixSongInfo .eyebrow {{
        margin: 0 0 5px;
    }}
    .flixSearchSection .flixSongCard.withThumb {{
        display: grid;
        grid-template-columns: 60px minmax(0, 1fr);
        gap: 12px;
        align-items: center;
    }}
    .flixSearchThumb {{
        width: 60px;
        height: 60px;
        border-radius: 10px;
        object-fit: cover;
        border: 1px solid #dbeafe;
        background: #f8fafc;
    }}
    .flixAlbumName {{
        margin: 6px 0 0;
        color: var(--muted);
        font-size: 13px;
    }}
    .flixCardLinks {{
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        margin-top: 10px;
    }}
    .flixCardAction {{
        display: inline-flex;
        align-items: center;
        justify-content: center;
        min-height: 32px;
        border-radius: 999px;
        border: 1px solid #fdba74;
        background: #fff7ed;
        color: #9a3412;
        padding: 0 10px;
        font-size: 12px;
        font-weight: 800;
        text-decoration: none;
    }}
    .flixCardAction.ghost {{
        border-color: #cbd5e1;
        background: #ffffff;
        color: #334155;
    }}
    .flixCardAction.alt {{
        border-color: #cbd5e1;
        background: #f8fafc;
        color: #334155;
    }}
    .flixEmpty {{
        border: 1px dashed #cbd5e1;
        border-radius: 12px;
        padding: 14px;
        color: #64748b;
        background: #f8fafc;
    }}
    @media (max-width: 720px) {{
        .flixSearchBar {{
            grid-template-columns: 1fr;
        }}
    }}
    
    /* DARK MODE STYLES FOR FLIX PLAY */
    body.dark-mode .flixHero {{
        background: radial-gradient(circle at 16% -20%, rgba(255, 122, 0, 0.25), transparent 45%), #1c1c1e;
        border-color: #2c2c2e;
    }}
    
    body.dark-mode .flixHero h1 {{
        color: #ffffff;
    }}
    
    body.dark-mode .flixHero p {{
        color: #a1a1a6;
    }}
    
    body.dark-mode .flixSuggestionsSection {{
        background: linear-gradient(160deg, #1e1b4b 0%, #111827 52%, #0f172a 100%);
        border-color: #312e81;
    }}
    
    body.dark-mode .flixSuggestionsSection .sectionHeader h2 {{
        color: #e0e7ff;
    }}
    
    body.dark-mode .flixSuggestionsSection .eyebrow {{
        color: #818cf8;
    }}
    
    body.dark-mode .flixSuggestionsSection .flixSongCard {{
        border-color: #312e81;
        background: linear-gradient(180deg, #1e1b4b 0%, #111329 100%);
        box-shadow: 0 8px 22px rgba(0, 0, 0, 0.3);
    }}
    
    body.dark-mode .flixSuggestionsSection .flixSongCard:hover {{
        border-color: #818cf8;
        box-shadow: 0 12px 26px rgba(99, 102, 241, 0.2);
    }}
    
    body.dark-mode .flixSuggestionsSection .flixCardAction {{
        border-color: #4f46e5;
        background: #312e81;
        color: #e0e7ff;
    }}
    
    body.dark-mode .flixSuggestionsSection .flixCardAction.ghost {{
        border-color: #312e81;
        background: #111329;
        color: #c7d2fe;
    }}
    
    body.dark-mode .flixSongCard {{
        border-color: #2c2c2e;
        background: #1c1c1e;
        color: #ffffff;
    }}
    
    body.dark-mode .flixSongCard:hover {{
        border-color: #f59e0b;
        box-shadow: 0 8px 20px rgba(0, 0, 0, 0.4);
    }}
    
    body.dark-mode .flixSongCard h3 a {{
        color: #ffffff;
    }}
    
    body.dark-mode .flixSongInfo .eyebrow {{
        color: #ff9f0a;
    }}

    body.dark-mode .flixSearchThumb {{
        border-color: #2c2c2e;
        background: #1c1c1e;
    }}
    
    body.dark-mode .flixCardAction {{
        border-color: #d97706;
        background: #7c2d12;
        color: #ffedd5;
    }}
    
    body.dark-mode .flixCardAction.ghost {{
        border-color: #2c2c2e;
        background: #2c2c2e;
        color: #e5e5ea;
    }}
    
    body.dark-mode .flixCardAction.alt {{
        border-color: #2c2c2e;
        background: #2c2c2e;
        color: #e5e5ea;
    }}
    
    body.dark-mode .flixEmpty {{
        border-color: #48484a;
        background: #1c1c1e;
        color: #aeaeb2;
    }}
    </style>

    <section class="flixHero">
        <p class="eyebrow">Flix Play</p>
        <h1>Bem vindo ao Flix Play</h1>
        <p>Digite uma musica ou artista para aprender a tocar.</p>
        <form class="flixSearchBar" id="flixSearchForm" onsubmit="return false;">
            <input type="text" id="flixSearchInput" placeholder="Ex: Animals, Maroon 5, The Kill..." autocomplete="off" value="{html_escape.escape(q)}">
            <button type="button" id="flixSearchBtn">Buscar</button>
        </form>
        <div class="flixQuickActions">
            <a class="flixQuickBtn" href="/treinar/">Treinar Piano</a>
        </div>
    </section>
    """

    html += """
    <section class="flixSection flixSearchSection" id="flixSearchSection" style="display:none;">
        <div class="sectionHeader">
            <div>
                <p class="eyebrow">Resultados</p>
                <h2 id="flixSearchTitle">Busca</h2>
            </div>
        </div>
        <div class="flixGrid" id="flixSearchGrid"></div>
    </section>
    """

    html += """
    <section class="flixSection flixSuggestionsSection">
        <div class="sectionHeader">
            <div>
                <p class="eyebrow">Sugestoes</p>
                <h2>Comece por aqui</h2>
            </div>
        </div>
        <div class="flixGrid">
    """

    if sugestoes:
        for row in sugestoes:
            html += _card_html(row)
    else:
        html += '<div class="flixEmpty">Nenhuma sugestao GP encontrada no indice.</div>'

    html += """
        </div>
    </section>
        <script>
        (function () {
            const input = document.getElementById("flixSearchInput");
            const btn = document.getElementById("flixSearchBtn");
            const section = document.getElementById("flixSearchSection");
            const grid = document.getElementById("flixSearchGrid");
            const title = document.getElementById("flixSearchTitle");

            if (!input || !btn || !section || !grid || !title) return;

            const esc = (v) => String(v || "")
                .replace(/&/g, "&amp;")
                .replace(/</g, "&lt;")
                .replace(/>/g, "&gt;")
                .replace(/\"/g, "&quot;")
                .replace(/'/g, "&#39;");

            function card(item) {
                const hasThumb = !!item.album_thumb;
                const albumLine = item.album_name ? `<p class="flixAlbumName">${esc(item.album_name)}</p>` : "";
                return `
                    <article class="flixSongCard ${hasThumb ? "withThumb" : ""}" role="button" tabindex="0" onclick="location.href='${esc(item.play_url)}'" onkeydown="if(event.key==='Enter'||event.key===' '){event.preventDefault();location.href='${esc(item.play_url)}'}">
                        ${hasThumb ? `<img class="flixSearchThumb" src="${esc(item.album_thumb)}" alt="${esc(item.album_name || item.title)}">` : ""}
                        <div class="flixSongInfo">
                            <p class="eyebrow">${esc(item.artist)}</p>
                            <h3><a href="${esc(item.play_url)}">${esc(item.title)}</a></h3>
                            ${albumLine}
                            <div class="flixCardLinks">
                                <a class="flixCardAction" href="${esc(item.play_url)}">Tocar no FlixPlayer</a>
                                <a class="flixCardAction ghost" href="${esc(item.lyric_url)}">Ver letra</a>
                                <a class="flixCardAction alt" href="${esc(item.train_url)}">Treinar</a>
                            </div>
                        </div>
                    </article>
                `;
            }

            async function runSearch() {
                const q = (input.value || "").trim();
                if (!q) {
                    section.style.display = "none";
                    grid.innerHTML = "";
                    return;
                }

                title.textContent = `Busca por "${q}"`;
                section.style.display = "block";
                grid.innerHTML = '<div class="flixEmpty">Buscando...</div>';

                try {
                    const r = await fetch(`/api/flix-play/search?q=${encodeURIComponent(q)}&limit=10`);
                    const data = await r.json();
                    const items = Array.isArray(data.results) ? data.results : [];
                    if (!items.length) {
                        grid.innerHTML = '<div class="flixEmpty">Nada encontrado para essa busca. Tente outro termo.</div>';
                        return;
                    }
                    grid.innerHTML = items.map(card).join("");
                } catch (_) {
                    grid.innerHTML = '<div class="flixEmpty">Falha ao buscar agora. Tente novamente.</div>';
                }
            }

            let timer = null;
            input.addEventListener("input", () => {
                clearTimeout(timer);
                timer = setTimeout(runSearch, 220);
            });
            btn.addEventListener("click", runSearch);
            input.addEventListener("keydown", (ev) => {
                if (ev.key === "Enter") {
                    ev.preventDefault();
                    runSearch();
                }
            });

            if ((input.value || "").trim()) {
                runSearch();
            }
        })();
        </script>
    """
    return html


_GP_RECORDS_CACHE = None
_GP_RECORDS_CACHE_MTIME = None

def _obter_gp_records_cacheado():
    global _GP_RECORDS_CACHE, _GP_RECORDS_CACHE_MTIME

    _refresh_guitarpro_index_txt()
    idx_path = _guitarpro_index_file_path()
    if not idx_path.exists():
        return []

    try:
        mtime = idx_path.stat().st_mtime
    except Exception:
        mtime = None

    if _GP_RECORDS_CACHE is not None and _GP_RECORDS_CACHE_MTIME == mtime:
        return _GP_RECORDS_CACHE

    def limpar_titulo_gp(texto):
        valor = (texto or "").strip()
        if not valor:
            return ""
        valor = re.sub(r"\(([^)]*?)\s+by\s+[^)]*\)", r"(\1)", valor, flags=re.IGNORECASE)
        valor = re.sub(r"\s{2,}", " ", valor).strip()
        return valor

    def titulo_exibicao(texto):
        valor = (texto or "").strip()
        if not valor:
            return ""
        valor = re.sub(r"\s*\((?:ver\.?\s*)?\d+\)\s*$", "", valor, flags=re.IGNORECASE)
        return valor.strip()

    records = []
    try:
        conteudo = idx_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return []

    for linha in conteudo.splitlines():
        if not linha.strip():
            continue
        partes = linha.split("\t")
        if len(partes) < 5:
            continue

        artista_norm = (partes[0] or "").strip()
        musica_norm = (partes[1] or "").strip()
        artista_nome = (partes[3] or partes[0].title()).strip()
        musica_titulo = limpar_titulo_gp((partes[4] or partes[1].title()).strip())
        musica_titulo_view = titulo_exibicao(musica_titulo) or musica_titulo
        if not artista_norm or not musica_norm:
            continue

        records.append({
            "artista_norm": artista_norm,
            "musica_norm": musica_norm,
            "artista_nome": artista_nome,
            "musica_titulo": musica_titulo,
            "musica_titulo_view": musica_titulo_view,
            "artista_flat": artista_norm.replace(" ", ""),
            "musica_flat": musica_norm.replace(" ", ""),
            "combined_norm": f"{artista_norm} {musica_norm}",
        })

    _GP_RECORDS_CACHE = records
    _GP_RECORDS_CACHE_MTIME = mtime
    return _GP_RECORDS_CACHE


@flixplay_bp.route("/api/flix-play/search")
def flix_play_search_api():
    q = (request.args.get("q") or "").strip()
    try:
        limit = int(request.args.get("limit") or 10)
    except Exception:
        limit = 10
    limit = max(1, min(10, limit))

    if not q:
        return jsonify({"results": []})

    records = _obter_gp_records_cacheado()
    q_norm = _normalizar_guitarpro_nome(q)
    if not q_norm:
        return jsonify({"results": []})
    q_flat = q_norm.replace(" ", "")
    q_tokens = [tok for tok in q_norm.split(" ") if tok]
    q_low = q.lower()

    out = []
    vistos = set()
    conn = None
    cur = None

    def _album_info_for_track(artista_slug, musica_slug, musica_titulo):
        if not cur:
            return ("", "")

        try:
            slug_base = re.sub(r"-(?:ver-\d+|\d+)$", "", musica_slug or "").strip("-")
            cur.execute(
                """
                SELECT
                    al.nome AS album_nome,
                    COALESCE(al.capa, '') AS album_capa
                FROM cancao c
                JOIN albuns al ON al.id = c.album_id
                JOIN artistas ar ON ar.id = al.artista_id
                WHERE ar.slug = ? AND (c.cancao_slug = ? OR c.cancao_slug = ?)
                LIMIT 1
                """,
                (artista_slug, musica_slug, slug_base),
            )
            row = cur.fetchone()
            if not row:
                return ("", "")

            album_nome = (row[0] or "").strip()
            capa_raw = (row[1] or "").strip()
            if capa_raw and capa_raw.lower() not in {"null", "none", "nan"}:
                return (album_nome, capa_raw)

            return (album_nome, "")
        except Exception:
            return ("", "")

    try:
        conn = sqlite3.connect(DB)
        cur = conn.cursor()
    except Exception:
        conn = None
        cur = None

    for rec in records:
        artista_norm = rec["artista_norm"]
        musica_norm = rec["musica_norm"]
        artista_nome = rec["artista_nome"]
        musica_titulo = rec["musica_titulo"]
        musica_titulo_view = rec["musica_titulo_view"]

        combined_norm = rec["combined_norm"]
        token_match = bool(q_tokens) and all(tok in combined_norm for tok in q_tokens)

        direct_match = (
            q_norm in combined_norm
            or q_flat in rec["artista_flat"]
            or q_flat in rec["musica_flat"]
            or q_low in artista_nome.lower()
            or q_low in musica_titulo.lower()
        )

        if not direct_match and not token_match:
            continue

        chave = (artista_norm, musica_norm)
        if chave in vistos:
            continue
        vistos.add(chave)

        artista_slug = normalizar_slug(artista_nome)
        musica_slug = normalizar_slug(musica_titulo)
        musica_slug_padrao = normalizar_slug(musica_titulo_view) or musica_slug
        album_nome, album_thumb = _album_info_for_track(artista_slug, musica_slug, musica_titulo)
        out.append(
            {
                "artist": artista_nome,
                "title": musica_titulo_view,
                "play_url": f"/tocador-gp4/{artista_slug}/{musica_slug_padrao}",
                "lyric_url": f"/letra/{artista_slug}/{musica_slug}",
                "train_url": f"/treinar/{artista_slug}/{musica_slug}",
                "album_name": album_nome,
                "album_thumb": album_thumb,
            }
        )

        if len(out) >= limit:
            break

    if conn:
        conn.close()

    return jsonify({"results": out})


@flixplay_bp.route("/sorteio-flixplayer")
def sorteio_flixplayer():
    import random
    catalogo = _obter_gp_catalogo_cacheado()
    if not catalogo:
        return redirect("/flix-play")

    item = random.choice(catalogo)
    artista_slug = normalizar_slug(item["artista_nome"])
    musica_slug = normalizar_slug(item["musica_titulo"])

    return redirect(f"/tocador-gp4/{artista_slug}/{musica_slug}")
