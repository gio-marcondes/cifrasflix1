import re
import math
import sqlite3
from pathlib import Path
from flask import Blueprint, request, redirect, url_for, render_template, session, jsonify, Response

from modules.layout import header
from modules.config import DB, connect_db, slugify, normalizar_slug
from modules.ui_helpers import home_dashboard_data, fmt_int

main_bp = Blueprint('main', __name__)

def destacar_acordes(texto):


    """
    Garante span em C#, D#, F#, G#, A#
    mesmo dentro de textos com acento.
    """

    return texto

def titulo_base(titulo):
    return re.sub(r'\s*\(.*?\)', '', titulo).strip().lower()

    

@main_bp.route("/debug/banco")
def debug_banco():
    conn = sqlite3.connect("cifras.db")
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    resultado = {}

    # pegar tabelas
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tabelas = [t["name"] for t in cur.fetchall()]

    for tabela in tabelas:
        cur.execute(f"SELECT * FROM {tabela}")
        resultado[tabela] = [dict(r) for r in cur.fetchall()]

    conn.close()
    return jsonify(resultado)
    
# ==========================================
# ROTAS
# ==========================================
@main_bp.route("/")
def home():
    import math

    page = int(request.args.get("page", 1))
    per_page = 48
    offset = (page - 1) * per_page

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM artistas")
    total = c.fetchone()[0]
    total_pages = max(1, math.ceil(total / per_page))

    c.execute("""
        SELECT nome, slug
        FROM artistas
        ORDER BY nome COLLATE NOCASE
        LIMIT ? OFFSET ?
    """, (per_page, offset))
    artistas = c.fetchall()

    dashboard = home_dashboard_data(c)
    conn.close()

    # Categorizando as ferramentas para maior clareza visual
    ferramentas_estudio = [
        ("CifrasFlix DAW", "Produza suas músicas com um estúdio online completo.", "/daw", "Abrir DAW"),
        ("FlixPlay", "Explore o acervo de músicas e abra as cifras em modo player.", "/flix-play", "Tocar agora"),
        ("Music Genius", "Transcreva acordes de links do YouTube sincronizados.", "/mp3detect", "Analisar áudio"),
        ("Separador de Áudio", "Isole vocais, bateria, baixo e instrumentos de qualquer música.", "/separar-audio", "Separar stems"),
        ("Masterização IA", "Compare presets de masterização com preview imediato.", "/masterizacao", "Masterizar"),
        ("Treinar Piano", "Pratique notas e acordes com o módulo de treino interativo.", "/treinar/", "Treinar")
    ]

    ferramentas_gerenciamento = [
        ("Discografias", "Navegue pelos álbuns por artista e organize sua biblioteca.", "/albuns", "Ver álbuns"),
        ("Músicas Favoritas", "Acesse rapidamente suas cifras marcadas com coração.", "/favoritos", "Ver favoritos"),
        ("Importador TXT", "Sincronize e atualize o catálogo principal de cifras.", "/importar", "Importar"),
        ("Atualizar Capas", "Faça o download e atualize imagens de artistas e álbuns.", "/atualizarfoto", "Atualizar"),
        ("MusicBrainz", "Busque metadados avançados e edições externas de álbuns.", "/mb_album", "Caçar álbuns")
    ]

    html = header("CifrasFlix - Central")

    html += """
    <section class="dashboardHero">
        <div>
            <p class="eyebrow">CifrasFlix Studio</p>
            <h1>O seu hub musical definitivo</h1>
            <p class="heroCopy">Pratique com cifras sincronizadas, separe trilhas com IA, masterize áudios e gerencie seu acervo em um só lugar.</p>
        </div>
        <div class="heroActions">
            <a class="primaryAction glassBtn glassBtnFlix" href="/flix-play">🎸 Abrir FlixPlay</a>
            <a class="secondaryAction glassBtn glassBtnDaw" href="/daw">🎛️ Abrir DAW</a>
            <a class="secondaryAction glassBtn glassBtnGenius" href="/mp3detect">🎧 Music Genius</a>
        </div>
    </section>

    <section class="statsGrid" aria-label="Resumo da biblioteca">
    """

    for label, value, hint in dashboard["stats"]:
        html += f"""
        <article class="statCard">
            <span>{label}</span>
            <strong>{value}</strong>
            <small>{hint}</small>
        </article>
        """

    html += """
    </section>

    <section class="systemGrid">
        <div class="systemPanel">
            <div class="sectionHeader">
                <div>
                    <p class="eyebrow">Produção & Prática</p>
                    <h2>Ferramentas de Estúdio</h2>
                </div>
            </div>
            <div class="moduleGrid">
    """

    for title, desc, href, action in ferramentas_estudio:
        html += f"""
        <a class="moduleCard promoCard" href="{href}">
            <strong>{title}</strong>
            <span>{desc}</span>
            <em>{action}</em>
        </a>
        """

    html += """
            </div>

            <div class="sectionHeader" style="margin-top: 32px;">
                <div>
                    <p class="eyebrow">Administração</p>
                    <h2>Gerenciamento do Acervo</h2>
                </div>
            </div>
            <div class="moduleGrid">
    """

    for title, desc, href, action in ferramentas_gerenciamento:
        html += f"""
        <a class="moduleCard" href="{href}">
            <strong>{title}</strong>
            <span>{desc}</span>
            <em>{action}</em>
        </a>
        """

    html += """
            </div>
        </div>

        <aside class="systemPanel compactPanel">
            <div class="sectionHeader">
                <div>
                    <p class="eyebrow">Atividade</p>
                    <h2>Destaques</h2>
                </div>
            </div>
            <div class="rankingList">
    """

    if dashboard["top_artistas"]:
        for index, (nome, slug, total_musicas, total_views) in enumerate(dashboard["top_artistas"], start=1):
            html += f"""
            <a class="rankingItem" href="/artista/{slug}">
                <b>{index}</b>
                <span>{nome}</span>
                <small>{fmt_int(total_views)} views - {fmt_int(total_musicas)} cifras</small>
            </a>
            """
    else:
        html += '<p class="emptyState">Sem artistas para destacar ainda.</p>'

    html += """
            </div>
        </aside>
    </section>

    <section class="systemPanel">
        <div class="sectionHeader">
            <div>
                <p class="eyebrow">Navegação</p>
                <h2>Todos os Artistas</h2>
            </div>
            <span class="pageInfo">Pagina """ + f"{page} de {total_pages}" + """</span>
        </div>
        <div class="artistGrid">
    """

    for nome, slug in artistas:
        inicial = (nome[:1] or "?").upper()
        html += f"""
        <a class="artistCardHome" href="/artista/{slug}?page={page}">
            <span class="artistAvatar">{inicial}</span>
            <strong>{nome}</strong>
        </a>
        """

    html += "</div>"

    if total_pages > 1:
        html += '<nav class="pagination" aria-label="Paginacao de artistas">'
        if page > 1:
            html += f'<a href="/?page={page-1}" class="pageBtn">Anterior</a>'
        html += f'<span class="pageInfo">Pagina {page} de {total_pages}</span>'
        if page < total_pages:
            html += f'<a href="/?page={page+1}" class="pageBtn">Proxima</a>'
        html += "</nav>"

    html += """
    </section>
    </main>
    """

    return html


@main_bp.route("/flix-play")
def flix_play():
    import html as html_escape
    import random
    q = (request.args.get("q") or "").strip()

    def limpar_titulo_gp(texto):
        valor = (texto or "").strip()
        if not valor:
            return ""
        valor = re.sub(r"\(([^)]*?)\s+by\s+[^)]*\)", r"(\1)", valor, flags=re.IGNORECASE)
        valor = re.sub(r"\s{2,}", " ", valor).strip()
        return valor

    def _carregar_gp_catalogo():
        _refresh_guitarpro_index_txt()
        idx_path = _guitarpro_index_file_path()
        if not idx_path.exists():
            return []

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

        return catalogo

    catalogo_gp = _carregar_gp_catalogo()

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
    """

    html += """
        </div>
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
    </main>
    """

    return html

def titulo_base(titulo):
    return re.sub(r'\s*\(.*?\)', '', titulo).strip().lower()


_GUITARPRO_INDEX_CACHE = None
_GUITARPRO_INDEX_CACHE_MTIME = None


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
    return Path("static") / "guitarpro" / "_gp_index.txt"


def _refresh_guitarpro_index_txt(max_age_seconds=21600):
    import time

    base_dir = Path("static") / "guitarpro"
    idx_path = _guitarpro_index_file_path()
    extensoes = {".gp", ".gp3", ".gp4", ".gp5", ".gpx"}

    if not base_dir.exists():
        return

    precisa_rebuild = True
    if idx_path.exists():
        try:
            idade = time.time() - idx_path.stat().st_mtime
            precisa_rebuild = idade > max_age_seconds
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
    except Exception:
        pass


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



@main_bp.route("/artista/<slug>")
def artista(slug):
    page_voltar = request.args.get("page", 1)
    pagina = int(request.args.get("p", 1))
    ordem = request.args.get("o", "views")
    mostrar_todas = request.args.get("todas") == "1"

    por_pagina = 50
    offset = (pagina - 1) * por_pagina
    limite_inicial = 18

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("SELECT id,nome FROM artistas WHERE slug=?", (slug,))
    artista = c.fetchone()
    if not artista:
        conn.close()
        return "Artista nao encontrado"

    artista_id, nome = artista
    fotoartista = pegar_foto_artista(artista)

    c.execute("SELECT COUNT(*) FROM musicas WHERE artista_id=?", (artista_id,))
    total_musicas = c.fetchone()[0]

    c.execute("SELECT COALESCE(SUM(views), 0) FROM musicas WHERE artista_id=?", (artista_id,))
    total_views = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM albuns WHERE artista_id=?", (artista_id,))
    total_albuns = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM favoritos f JOIN musicas m ON m.id = f.musica_id WHERE m.artista_id=?", (artista_id,))
    total_favoritos = c.fetchone()[0]

    if ordem == "flixplayer":
        c.execute(
            """
            SELECT titulo, uid, views, conteudo, tom, slug
            FROM musicas
            WHERE artista_id=?
            """,
            (artista_id,),
        )
        musicas_raw = c.fetchall()
    else:
        order_sql = "views DESC" if ordem == "views" else "titulo COLLATE NOCASE ASC"
        c.execute(
            f"""
            SELECT titulo, uid, views, conteudo, tom, slug
            FROM musicas
            WHERE artista_id=?
            ORDER BY {order_sql}
            LIMIT ? OFFSET ?
            """,
            (artista_id, por_pagina, offset),
        )
        musicas_raw = c.fetchall()

    c.execute("""
        SELECT id, nome, ano
        FROM albuns
        WHERE artista_id=?
        ORDER BY ano
    """, (artista_id,))
    albuns = c.fetchall()
    conn.close()

    agrupadas = {}
    for titulo, uid, views, conteudo, tom_salvo, musica_slug in musicas_raw:
        base = titulo_base(titulo)
        if base not in agrupadas:
            tom = tom_salvo or extrair_tom_da_cifra(conteudo or "") or "-"
            agrupadas[base] = {
                "titulo": re.sub(r'\s*\(.*?\)', '', titulo).strip(),
                "uid": uid,
                "slug": musica_slug or slugify(titulo),
                "views": views or 0,
                "count": 0,
                "tom": tom,
            }
        else:
            agrupadas[base]["count"] += 1

    musicas = list(agrupadas.values())
    if ordem == "flixplayer":
        for m in musicas:
            m["has_player"] = _has_flixplayer_tab(nome, m["titulo"])

        musicas.sort(
            key=lambda m: (
                not m.get("has_player", False),
                -(m.get("views") or 0),
                (m.get("titulo") or "").lower(),
            )
        )

        total_agrupadas = len(musicas)
        total_paginas = max(1, (total_agrupadas // por_pagina) + (1 if total_agrupadas % por_pagina else 0))
        inicio = max(0, (pagina - 1) * por_pagina)
        fim = inicio + por_pagina
        musicas = musicas[inicio:fim]

    musicas_exibir = musicas if mostrar_todas else musicas[:limite_inicial]

    import os
    nome_safe = nome.replace(" ", "+")
    nome_pasta = nome.lower().replace(" ", "_")
    mini_path = os.path.join("static", "fotos", "artista", nome_pasta, "mini.jpg")

    if os.path.exists(mini_path):
        foto_url = f"/static/fotos/artista/{nome_pasta}/mini.jpg"
    else:
        foto_url = f"https://ui-avatars.com/api/?name={nome_safe}&background=ddd&color=333&size=256"

    if ordem != "flixplayer":
        total_paginas = max(1, (total_musicas // por_pagina) + (1 if total_musicas % por_pagina else 0))

    html = header(nome) + f"""
    <section class="artistProfileHero">
        <a class="backBtn softBack" href="/?page={page_voltar}">Voltar para artistas</a>
        <div class="artistHeroMain">
            <div class="artistPortrait">
                <img src="{foto_url}" alt="{nome}">
                {fotoartista}
            </div>
            <div class="artistHeroCopy">
                <p class="eyebrow">Artista</p>
                <h1>{nome}</h1>
                <p>Catalogo de cifras, letras e discografia organizado para tocar, estudar e revisar rapido.</p>
                <div class="artistStats">
                    <span><strong>{fmt_int(total_musicas)}</strong> musicas</span>
                    <span><strong>{fmt_int(total_albuns)}</strong> albuns</span>
                    <span><strong>{fmt_int(total_views)}</strong> views</span>
                    <span><strong>{fmt_int(total_favoritos)}</strong> favoritos</span>
                </div>
            </div>
        </div>
    </section>

    <section class="artistWorkspace">
        <aside class="artistSidePanel">
            <div class="sectionHeader">
                <div>
                    <p class="eyebrow">Organizacao</p>
                    <h2>Cifras</h2>
                </div>
            </div>
            <div class="sortChips">
                <a href="?o=views&p=1" class="ordBtn {'active' if ordem=='views' else ''}">Mais vistas</a>
                <a href="?o=alpha&p=1" class="ordBtn {'active' if ordem=='alpha' else ''}">A-Z</a>
                <a href="?o=flixplayer&p=1" class="ordBtn {'active' if ordem=='flixplayer' else ''}">FlixPlayer</a>
            </div>
            <p class="panelHint">A lista agrupa versoes da mesma musica e mostra o tom detectado quando existe cifra.</p>
        </aside>

        <div class="artistMainPanel">
            <div class="sectionHeader">
                <div>
                    <p class="eyebrow">Repertorio</p>
                    <h2>Musicas</h2>
                </div>
                <span class="pageInfo">Pagina {pagina} de {total_paginas}</span>
            </div>
            <div class="musicListHeader artistMusicHeader">
                <span>#</span><span>Musica</span><span>Views</span><span>Tom</span><span>Acoes</span>
            </div>
            <div class="musicGrid artistMusicList">
    """

    if musicas_exibir:
        for i, m in enumerate(musicas_exibir, start=1 + offset):
            badge = f'<span class="versaoBadge">+{m["count"]}</span>' if m["count"] > 0 else ""
            html += f"""
            <div class="musicRow artistTrackRow">
                <div class="musicIndex">{i:02d}</div>
                <a class="musicTitle trackMainLink" href="/artista/{slug}/{m["uid"]}">{m["titulo"]} {badge}</a>
                <div class="musicViews">{fmt_int(m["views"])}</div>
                <div class="musicKey">{m["tom"]}</div>
                <div class="artistTrackActions">
                    <a class="trackActionBtn cifraBtn" href="/artista/{slug}/{m["uid"]}" title="Ver cifra">Cifra</a>
                    <a class="trackActionBtn letraBtn" href="/letra/{slug}/{m["slug"]}" title="Ver letra">Letra</a>
                </div>
            </div>
            """
    else:
        html += """
        <div class="emptyState artistEmptyState">
            <strong>Nenhuma cifra vinculada ainda.</strong>
            <span>Use a discografia abaixo para navegar pelas letras e depois vincule cifras quando elas forem importadas.</span>
        </div>
        """

    html += "</div>"

    if not mostrar_todas and len(musicas) > limite_inicial:
        html += f"""
        <div class="centerActions">
            <a href="?todas=1&o={ordem}&p={pagina}" class="pageBtn">Mostrar todas as cifras desta pagina</a>
        </div>
        """

    html += '<nav class="paginacao">'
    if pagina > 1:
        html += f'<a href="?p={pagina-1}&o={ordem}" class="pageBtn">Anterior</a>'
    html += f'<span class="pageInfo">Pagina {pagina} de {total_paginas}</span>'
    if pagina < total_paginas:
        html += f'<a href="?p={pagina+1}&o={ordem}" class="pageBtn">Proxima</a>'
    html += "</nav></div></section>"

    if albuns:
        html += """
        <section class="discographyPanel">
            <div class="sectionHeader">
                <div>
                    <p class="eyebrow">Discografia</p>
                    <h2>Albuns</h2>
                </div>
            </div>
            <div class="albumGrid">
        """
        for aid, nome_album, ano_album in albuns:
            ano_fmt = str(ano_album)[:4] if ano_album else ""
            html += f"""
            <a href="/album/{aid}" class="albumCard">
                <img src="/capa_album/{aid}" class="albumCover" alt="{nome_album}">
                <div class="albumTitle">{nome_album}</div>
                <div class="albumYear">{ano_fmt}</div>
            </a>
            """
        html += "</div></section>"

    html += "</main>"
    return html


import re


import requests

def pegar_foto_artista(nome_artista):
        return ""


def extrair_tom_da_cifra(texto_pre):
    import re
    # -------------------------------------------------
    # 1️⃣ Procurar Tecla ou Key
    # -------------------------------------------------
    m = re.search(r'(?:Tecla|Key)\s*:\s*([A-G](?:#|b)?)', texto_pre, re.IGNORECASE)
    if m:
        return m.group(1)

    # regex de acorde (mesmo padrão que você usa)
    chord_pattern = (
        r'\b([A-G](?:#|b)?'
        r'(?:maj7|m7|m|7sus4|sus4|sus2|dim|aug|add9|m6|6|9|11|13|'
        r'7#9|7b9|7#5|7b5|7#11|7b13|7|5)?'
        r'(?:/[A-G](?:#|b)?)?)\b'
    )

    # -------------------------------------------------
    # 2️⃣ Procurar após [Verse ou [Intro
    # -------------------------------------------------
    bloco = re.search(
        r'\[(?:Verse|Intro)[^\]]*\](.*)',
        texto_pre,
        re.IGNORECASE | re.DOTALL
    )

    if bloco:
        trecho = bloco.group(1)
        m2 = re.search(chord_pattern, trecho)
        if m2:
            raiz = re.match(r'^([A-G](?:#|b)?)', m2.group(1))
            if raiz:
                return raiz.group(1)

    # -------------------------------------------------
    # 3️⃣ Fallback: primeiro acorde do texto inteiro
    # -------------------------------------------------
    m3 = re.search(chord_pattern, texto_pre)
    if m3:
        raiz = re.match(r'^([A-G](?:#|b)?)', m3.group(1))
        if raiz:
            return raiz.group(1)

    return None

def extrair_tom(texto):
    """
    Procura por:
    Tecla: C
    Key: C
    Tom: C
    """

    padrao = re.search(
        r'(?:Tecla|Key|Tom)\s*:\s*([A-G][#b]?(?:m|maj7|7)?)',
        texto,
        re.IGNORECASE
    )

    if padrao:
        return padrao.group(1).upper()

    return None


@main_bp.route("/artista/<slug>/<uid>")
def musica(slug, uid):
    semitons = int(request.args.get("t", 0))

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("""
    SELECT 
        m.id,
        m.titulo,
        m.conteudo,
        m.tom,
        m.capotraste,
        m.afinacao,
        a.nome,
        a.slug
    FROM musicas m
    JOIN artistas a ON m.artista_id = a.id
    WHERE a.slug=? AND m.uid=?
    """, (slug, uid))

    musica = c.fetchone()

    if not musica:
        return "Não encontrada"

    (
        musica_id,
        titulo,
        conteudo,
        tom_musica,
        capotraste,
        afinacao,
        artista_nome,
        artista_slug
    ) = musica

    c.execute(
        "UPDATE musicas SET views=views+1 WHERE id=?",
        (musica_id,)
    )

    conn.commit()
    conn.close()

    # buscar outras versões da mesma música
    base_titulo = titulo.split("(")[0].strip()

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("""
    SELECT uid, titulo
    FROM musicas
    WHERE artista_id = (
        SELECT id FROM artistas WHERE slug=?
    )
    AND titulo LIKE ?
    ORDER BY titulo
    """, (slug, base_titulo + "%"))

    versoes = c.fetchall()

    conn.close()

    video_url = buscar_video_youtube(artista_nome, titulo)

    # extrai o ID do vídeo
    video_id = video_url.split("v=")[-1]

    iframe_video = f'''
    <iframe id="ytplayer"
            src="https://www.youtube.com/embed/{video_id}"
            frameborder="0"
            allowfullscreen>
    </iframe>
    '''

    conteudo = transpor_acordes(conteudo, semitons)

    tom_musica = tom_musica or "—"
    capotraste = capotraste or ""
    afinacao = afinacao or ""
    #tom_musica = video_url
    conteudo = re.sub(
        r'(?:Tecla|Key|Tom)\s*:\s*[A-G][#b]?(?:m|maj7|7)?',
        '',
        conteudo,
        flags=re.IGNORECASE
    )
        
        
    conteudo = destacar_acordes(conteudo)

    html = header(titulo) + f"""
  <style>main{{
    
    width:100%;
    max-width:none;   /* 🔥 ESSENCIAL */
}}
        /* ===== LAYOUT 3 COLUNAS ===== */
       .songLayout{{
    width:100%;
    max-width:1280px;
    margin:20px auto;
    padding:0 20px;

    display:grid;

    /* 🎯 centro manda no layout */
    grid-template-columns: 250px minmax(0, 1fr) 300px;

    gap:28px;
    align-items:start;
}}

        /* ===== CONTROLES ===== */
        .songLeft{{
            display:flex;
            flex-direction:column;
            gap:18px;
        }}

        .controlCard{{
            background:#ffffff;
            border:1px solid #e5e7eb;
            border-radius:16px;
            padding:18px;
            box-shadow:0 2px 6px rgba(0,0,0,0.04);
            border: 1px solid #666;
            margin-bottom: 13px;
        }}

        .controlTitle{{
            font-size:16px;
            font-weight:600;
            color:#111827;
            margin-bottom:14px;
        }}

        .controlBtns{{
            display:flex;
            gap:10px;
            margin-bottom:14px;
        }}

        .controlBtn{{
            height:38px;
            border-radius:10px;
            border:1px solid #e5e7eb;
            background:#f9fafb;
            font-weight:700;
            cursor:pointer;
            transition:.15s;
        }}

        .controlBtn:hover{{
            background:#f3f4f6;
        }}

        .favBtn{{
            width:100%;
            border:1px solid #e5e7eb;
            background:#fafafa;
            border-radius:12px;
            padding:10px;
            font-weight:600;
            cursor:pointer;
            transition:.15s;
        }}
    .songKeyBadge{{
        font-size:22px;
        font-weight:800;
        background:#ff7a00;
        color:#fff;
        padding:10px 0;
        border-radius:12px;
        text-align:center;
        letter-spacing:1px;
    }}
        .favBtn:hover{{
            background:#f3f4f6;
        }}

        .autoScrollBtn{{
            width:100%;
            border:1px solid #e5e7eb;
            background:#f9fafb;
            border-radius:12px;
            padding:10px;
            font-weight:600;
            cursor:pointer;
        }}

        .speedBox{{
            margin-top:12px;
            padding:12px;
            border-radius:12px;
            background-color:#eee;
            border-color:#ccc;
            display:flex;
            align-items:center;
            justify-content:space-between;
            gap:10px; font-size:10px;
        }}

        .speedLabel{{
            font-size:10px;
            color:#6b7280;
        }}

        .speedValue{{
            font-weight:600;
            color:#111827;
        }}

        .speedBtn{{
            width:32px;
            height:32px;
            border-radius:8px;
            border:1px solid #d1d5db;
            background:#ffffff;
            font-weight:700;
            cursor:pointer;
        }}
        /* ===== CIFRA ===== */
        .songCenter{{
            min-width:0;
            
    margin-top: 0;
    padding-top: 0;

        }}

        .songTitle{{
            margin-bottom:14px;
            margin-top:0px;
        }}

        .cifraBox{{
            background:#ffffff;
            border:1px solid #e5e7eb;
            border-radius:14px;
            padding:24px;
            font-size:15px;
            line-height:1.6;
            white-space:pre-wrap;
            color:#111827;
        }}
        .songCenter{{
    min-width:0;
    width:100%;
}}

.cifraBox{{
    width:100%;
    max-width:none;
    overflow-x:auto;   /* 🔥 evita quebrar tudo */
}}

        .cifraBox{{
            width:100%;
            max-width:none;   /* 🔥 MUITO IMPORTANTE */
        }}
                /* ===== VIDEO ===== */
                .songVideo{{
                    position:sticky;
                    top:90px;
                }}
        .songVideo{{
            position:sticky;
            top:90px;
            max-width:300px;
        }}
        .videoWrapper{{
            background:#ffffff;
            border:1px solid #e5e7eb;
            border-radius:14px;
            padding:10px;
        }}

        .videoWrapper iframe{{
            width:100%;
            height:210px;
            border:none;
            border-radius:10px;
        }}

        /* ===== RESPONSIVO ===== */

*,
*::before,
*::after{{
    box-sizing:border-box;
}}
         .versionSelect{{
            width:100%;
            display:block;
            margin-top:8px;
            padding:12px 40px 12px 14px; /* espaço pra setinha */
            border-radius:12px;
            border:1px solid #e5e7eb;
            background:#f3f4f6;
            color:#111827;
            font-weight:600;
            font-size:14px;
            cursor:pointer;
            appearance:none;
            -webkit-appearance:none;
            -moz-appearance:none;
            transition:all .18s ease;
        }}

        .versionSelect:hover{{
            border-color:#d1d5db;
        }}

        .versionSelect:focus{{
            outline:none;
            border-color:#9ca3af;
            box-shadow:0 0 0 2px rgba(156,163,175,.15);
        }}
        .versionSelect{{
            width:100%;
            margin-top:8px;
            padding:12px 14px;
            border-radius:12px;
            border:1px solid #e5e7eb;
            background:#f3f4f6; /* cinzinha clean */
            color:#111827;
            font-weight:600;
            font-size:14px;
            cursor:pointer;
            appearance:none;
            -webkit-appearance:none;
            -moz-appearance:none;
            transition:all .18s ease;
            position:relative;
        }}

        /* hover clean */
        .versionSelect:hover{{
            background:#e5e7eb;
            border-color:#d1d5db;
        }}
        .selectWrapper{{
            position:relative;
        }}

        .selectWrapper::after{{
             content:"▾";
            position:absolute;
            right:14px;
            top:50%;
            transform:translateY(-50%);
            pointer-events:none;
            color:#6b7280;
            font-size:14px;
        }}
        /* focus elegante */
        .versionSelect:focus{{
            outline:none;
            background:#e5e7eb;
            border-color:#9ca3af;
            box-shadow:0 0 0 3px rgba(156,163,175,.18);
        }}
        /* ===== VOLTAR ===== */
        .backWrapper{{
            margin-bottom:16px;
        }}
        .songControls {{
            position: sticky;
            top: 90px;
            max-width: 360px;
                         /* ajuste conforme quiser */
            background: #f4f4f4;
            box-sizing: border-box;
            position: sticky;         /* faz ficar fixo ao rolar */
         
            overflow-y: auto;         /* rolagem interna do menu se necessário */
        }}
        .play-btn {{
            width: 34px;
            height: 34px;
            border-radius: 50%;
            border: 1px solid #d1d5db;
            background: #ffffff;
            cursor: pointer;
            font-size: 14px;
            font-weight: bold;
            transition: all .15s ease;
        }}

        .play-btn:hover {{
            background: #f3f4f6;
            transform: scale(1.05);
        }}

        .play-btn.playing {{
            background: #00e676;
            color: white;
            border-color: #00e676;
        }}

        
        </style>
        <script>
        function trocarVersao(uid){{
            const partes = window.location.pathname.split("/");
            const artista = partes[2];
            window.location.href = "/artista/" + artista + "/" + uid;
        }}

        </script>

        <div class="backWrapper">
            <button class="backBtn" onclick="location.href='/artista/{slug}'">
                ← Voltar para músicas
            </button>
        </div>
        
        <div class="songLayout">

            <!-- 🎛️ CONTROLES ESQUERDA -->
            <aside class="songControls">
                <div class="controlCard">
                    <div class="controlTitle">🎸 Versões</div>
                <div class="selectWrapper">
                    <select class="versionSelect"
                        onchange="trocarVersao(this.value)">
                        {''.join([
                            f"<option value='{v_uid}' {'selected' if v_uid==uid else ''}>{v_titulo}</option>"
                            for v_uid, v_titulo in versoes
                        ])}
                    </select>
                    </div>
                </div>
                <div class="controlCard chordControlCard">
                    <div class="controlTitle">Tom da cifra</div>

                    <div class="transposePanel">
                        <button class="controlBtn toneStep" onclick="transpor(-1)">-</button>
                        <div class="transposeState">
                            <strong>{tom_musica}</strong>
                            <span id="transposeLabel">{semitons:+d} semitons</span>
                        </div>
                        <button class="controlBtn toneStep" onclick="transpor(1)">+</button>
                    </div>
                    <div class="transposeQuick">
                        <button class="controlBtn" onclick="transpor(-2)">-1 tom</button>
                        <button class="controlBtn" onclick="resetTransposicao()">Original</button>
                        <button class="controlBtn" onclick="transpor(2)">+1 tom</button>
                    </div>

                    <button class="controlBtn favoriteWide"
                        onclick="location.href='/favoritar/{musica_id}'">
                        Favoritar
                    </button>
                </div>

                <div class="controlCard chordControlCard">
                    <div class="controlTitle">Rolagem</div>

                    <button class="controlBtn autoScrollPrimary" onclick="toggleScroll()" id="scrollBtn">
                        Iniciar autorrolagem
                    </button>

                    <div class="speedBox autoScrollBox">
                        <span>Velocidade</span>
                        <button class="controlBtn" onclick="changeSpeed(-0.2)">-</button>
                        <span id="speedLabel">1.0x</span>
                        <button class="controlBtn" onclick="changeSpeed(0.2)">+</button>
                    </div>
                    <div class="autoScrollHint">Espaco pausa/continua. Esc interrompe.</div>
                </div>

            </aside>

            <!-- 🎸 CIFRA CENTRAL -->
            <main class="songCenter">
                <h2 class="songTitle">{titulo} </h2>
                <p><a class="chord" href="/artista/{artista_slug}">{artista_nome}</a></p>
                <div class="musicMetaGrid">
                    <div class="musicMetaCard">
                        <span>Capotraste</span>
                        <strong>{capotraste or "Sem capotraste"}</strong>
                    </div>
                    <div class="musicMetaCard">
                        <span>Afinacao</span>
                        <strong>{afinacao or "Padrao"}</strong>
                    </div>
                    <div class="musicMetaCard highlight">
                        <span>Tom</span>
                        <strong>{tom_musica}</strong>
                    </div>
                </div>
                <pre class="cifraBox">{conteudo}</pre>
            </main>

            <!-- 🎬 VÍDEO DIREITA -->
            <aside class="songVideo">
                <div class="videoWrapper">
                   {iframe_video}
                </div>
            </aside>

        </div>

        </main>
    <script>
    document.addEventListener("DOMContentLoaded", function () {{
        const chordRegex = /\\b([A-G](?:[#b])?(?:maj9|maj7|m7b5|m7|m|7sus4|7sus2|7#11|7b13|7#9|7b9|7#5|7b5|7|sus4|sus2|dim|aug|add9|m6|6|9|11|13|5)?(?:\/[A-G](?:[#b])?)?)\\b/g;

        document.querySelectorAll("pre.cifraBox").forEach((pre) => {{
            const walker = document.createTreeWalker(pre, NodeFilter.SHOW_TEXT, null, false);
            const textNodes = [];
            let node;

            while ((node = walker.nextNode())) {{
                textNodes.push(node);
            }}

            textNodes.forEach((textNode) => {{
                const text = textNode.nodeValue || "";
                if (!text.match(chordRegex)) return;
                chordRegex.lastIndex = 0;

                const frag = document.createDocumentFragment();
                let lastIndex = 0;

                text.replace(chordRegex, (match, _cap, offset) => {{
                    frag.appendChild(document.createTextNode(text.slice(lastIndex, offset)));

                    const span = document.createElement("span");
                    span.className = "chord";
                    span.textContent = match;

                    const diagram = document.createElement("div");
                    diagram.className = "chord-diagram";

                    const jtabDiv = document.createElement("div");
                    jtabDiv.className = "jtab";
                    diagram.appendChild(jtabDiv);
                    span.appendChild(diagram);

                    let rendered = false;
                    span.addEventListener("mouseenter", () => {{
                        diagram.style.display = "block";
                        if (!rendered && window.jtab && typeof window.jtab.render === "function") {{
                            try {{
                                window.jtab.render(jtabDiv, match);
                                rendered = true;
                            }} catch (_err) {{}}
                        }}
                    }});

                    span.addEventListener("mouseleave", () => {{
                        diagram.style.display = "none";
                    }});

                    frag.appendChild(span);
                    lastIndex = offset + match.length;
                    return match;
                }});

                frag.appendChild(document.createTextNode(text.slice(lastIndex)));
                textNode.parentNode.replaceChild(frag, textNode);
            }});
        }});
    }});
    </script>
    <script>
        // =============================
        // AUTO ROLAGEM
        // =============================
        let scrollSpeed = 1.0;
        let scrolling = false;
        let scrollFrame = null;
        let lastScrollTs = 0;

        function updateScrollButton(){{
            const btn = document.getElementById("scrollBtn");
            if (btn) btn.innerText = scrolling ? "Pausar autorrolagem" : "Iniciar autorrolagem";
        }}

        function scrollStep(ts){{
            if (!scrolling) return;
            if (!lastScrollTs) lastScrollTs = ts;
            const delta = Math.min(48, ts - lastScrollTs);
            lastScrollTs = ts;
            window.scrollBy(0, scrollSpeed * delta / 12);

            const chegouFim = window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 8;
            if (chegouFim) {{
                scrolling = false;
                lastScrollTs = 0;
                updateScrollButton();
                return;
            }}

            scrollFrame = requestAnimationFrame(scrollStep);
        }}

        function toggleScroll(){{
            scrolling = !scrolling;
            updateScrollButton();
            if (scrolling) {{
                lastScrollTs = 0;
                cancelAnimationFrame(scrollFrame);
                scrollFrame = requestAnimationFrame(scrollStep);
            }} else {{
                cancelAnimationFrame(scrollFrame);
            }}
        }}

        function changeSpeed(delta){{
            scrollSpeed = Math.max(0.2, Math.min(4, scrollSpeed + delta));
            document.getElementById("speedLabel").innerText = scrollSpeed.toFixed(1) + "x";
        }}

        // =============================
        // TRANSPOSICAO VIA URL
        // =============================
        function transpor(v){{
            const url = new URL(window.location.href);
            const t = parseInt(url.searchParams.get("t") || "0");
            url.searchParams.set("t", t + v);
            window.location.href = url.toString();
        }}

        function resetTransposicao(){{
            const url = new URL(window.location.href);
            url.searchParams.delete("t");
            window.location.href = url.toString();
        }}

        document.addEventListener("keydown", (event) => {{
            if (event.code === "Space" && !["INPUT", "TEXTAREA", "SELECT"].includes(document.activeElement.tagName)) {{
                event.preventDefault();
                toggleScroll();
            }}
            if (event.key === "Escape" && scrolling) {{
                scrolling = false;
                cancelAnimationFrame(scrollFrame);
                updateScrollButton();
            }}
        }});

        // =============================
        // BUSCA YOUTUBE AUTOMÁTICA
        // =============================
        document.addEventListener("DOMContentLoaded", async () => {{

            const titulo = document.querySelector("h2")?.innerText || "";
            const artista = document.querySelector("#tituloPagina")?.innerText || "";
            const query = `${{artista}} ${{titulo}}`;

            try{{
                const r = await fetch(
                    "https://ytsearch.vercel.app/api?q=" +
                    encodeURIComponent(query)
                );

                const data = await r.json();

                if(data?.videos?.length){{
                    const videoId = data.videos[0].videoId;
                    document.getElementById("ytplayer").src =
                        "https://www.youtube.com/embed/" + videoId;
                }}
            }}catch(e){{
                console.log("YT search falhou");
            }}

        }});
        </script>"""
    return html

def buscar_video_youtube(artista, musica, indice=5):
    query = urllib.parse.quote(f"{artista}  {musica}")
    url = f"https://www.youtube.com/results?search_query={query}"

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    html = requests.get(url, headers=headers).text

    # pega TODOS os vídeos
    matches = re.findall(r"watch\?v=([a-zA-Z0-9_-]{11})", html)

    # remove duplicados mantendo ordem
    vistos = []
    for m in matches:
        if m not in vistos:
            vistos.append(m)

    # 🔥 terceiro vídeo = índice 2
    if len(vistos) > indice:
        video_id = vistos[indice]
        return f"https://www.youtube.com/watch?v={video_id}"

    return None
