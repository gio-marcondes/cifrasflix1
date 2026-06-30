import re
import math
import sqlite3
import urllib.parse
import requests
from pathlib import Path
from flask import Blueprint, request, redirect, url_for, render_template, session, jsonify, Response

from modules.layout import header
from modules.config import DB, connect_db, slugify, normalizar_slug, transpor_acordes
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

    ferramentas_estudio = [
        ("CifrasFlix DAW", "Produza suas músicas com um estúdio online completo.", "/daw", "Abrir DAW"),
        ("Conversor & Edição", "Converta formatos, corte, junte áudios e altere o tom em tempo real.", "/conversor", "Abrir Conversor"),
        ("Afinador Digital", "Afine seu violão, guitarra ou outro instrumento diretamente pelo navegador.", "/afinador", "Afinar agora"),
        ("Estúdio Jam & Voz", "Grave sua voz e instrumento com efeitos de reverb e delay integrados.", "/jam-studio", "Iniciar Jam"),
        ("Dicionário de Acordes", "Busque posições de acordes e visualize os diagramas com áudio interativo de violão.", "/dicionario", "Abrir dicionário"),
        ("Dicionário de Estilos", "Aprenda a estrutura dos acordes de cada gênero musical e compreenda as regras da harmonia.", "/estilos", "Aprender"),
        ("FlixPlay", "Explore o acervo de músicas e abra as cifras em modo player.", "/flix-play", "Tocar agora"),
        ("Music Genius", "Transcreva acordes de links do YouTube sincronizados.", "/mp3detect", "Analisar áudio"),
        ("Separador de Áudio", "Isole vocais, bateria, baixo e instrumentos de qualquer música.", "/separar-audio", "Separar stems"),
        ("Masterização IA", "Compare presets de masterização com preview imediato.", "/masterizacao", "Masterizar"),
        ("Treinar Piano", "Pratique notas e acordes com o módulo de treino interativo.", "/treinar/", "Treinar")
    ]

    ferramentas_gerenciamento = [
        ("Discografias", "Navegue pelos álbuns por artista e organize sua biblioteca.", "/albuns", "Ver álbuns"),
        ("Músicas Favoritas", "Acesse rapidamente suas cifras marcadas com coração.", "/painel", "Ver favoritos"),
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

    c.execute("SELECT id FROM favoritos WHERE musica_id = ?", (musica_id,))
    is_favorited = c.fetchone() is not None

    playlists = []
    if session.get("user") == "adm":
        c.execute("SELECT id, nome FROM playlists ORDER BY nome")
        playlists = c.fetchall()

    playlist_options = "".join([f'<option value="{pid}">{pnome}</option>' for pid, pnome in playlists])
    playlist_selector_html = ""
    if playlists:
        playlist_selector_html = f"""
        <form method="POST" action="/painel/playlist/adicionar" style="margin-top: 10px;">
            <input type="hidden" name="musica_id" value="{musica_id}" />
            <select name="playlist_id" onchange="this.form.submit()" autocomplete="off" style="width: 100%; padding: 10px; border-radius: 8px; border: 1px solid #d1d5db; background: #fff; font-weight: bold; color: #475569; font-size: 13px; cursor: pointer; outline: none; box-sizing: border-box;">
                <option value="" selected>➕ Adicionar a Playlist...</option>
                {playlist_options}
            </select>
        </form>
        """

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
    position:relative;
    z-index:2000;
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

        /* Chord Tooltip & Styling */
        .chord {{
            color: #ff7a00;
            font-weight: 700;
            position: relative;
            cursor: pointer;
            display: inline-block;
            padding: 0 4px;
            border-radius: 4px;
            background: rgba(255, 122, 0, 0.05);
            transition: all 0.15s ease;
        }}
        .chord:hover {{
            background: #ff7a00;
            color: #fff !important;
        }}
        .chord-diagram {{
            display: none;
            position: fixed;
            transform: translateX(-50%);
            z-index: 99999999;
            pointer-events: auto;
            animation: chordFadeIn 0.15s ease-out;
        }}
        @keyframes chordFadeIn {{
            from {{ opacity: 0; transform: translate(-50%, 8px); }}
            to {{ opacity: 1; transform: translate(-50%, 0); }}
        }}
        </style>
        <script src="https://cdn.jsdelivr.net/npm/soundfont-player@0.12.0/dist/soundfont-player.min.js"></script>
        <script>
        let guitarPlayer = null;
        let audioCtx = null;
        function initSoundfont() {{
            if (audioCtx) return;
            try {{
                const AudioContextClass = window.AudioContext || window.webkitAudioContext;
                audioCtx = new AudioContextClass();
                const preset = localStorage.getItem("defaultPreset") || "acoustic_guitar_nylon";
                Soundfont.instrument(audioCtx, preset).then(function (inst) {{
                    guitarPlayer = inst;
                }}).catch(e => console.log("SoundFont failed, using synth", e));
            }} catch(e) {{
                console.log("Audio not supported", e);
            }}
        }}
        // Initialize early on interaction
        document.addEventListener("mouseenter", initSoundfont, {{ once: true }});
        document.addEventListener("click", initSoundfont, {{ once: true }});

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
                            <strong id="currentKeyLabel" data-original-key="{tom_musica}">{tom_musica}</strong>
                            <span id="transposeLabel">{semitons:+d} semitons</span>
                        </div>
                        <button class="controlBtn toneStep" onclick="transpor(1)">+</button>
                    </div>
                    <button class="controlBtn resetToneBtn" onclick="resetTransposicao()" style="width: 100%; margin-top: 10px; margin-bottom: 10px;">
                        Restaurar original
                    </button>

                    <button class="controlBtn favoriteWide"
                        onclick="location.href='/favoritar/{musica_id}'"
                        style="background: {'#ffebe0' if is_favorited else '#fff'}; color: {'#ff7a00' if is_favorited else '#4b5563'}; border-color: {'#ff7a00' if is_favorited else '#d1d5db'}; font-weight: bold;">
                        {'❤️ Curtida' if is_favorited else '🤍 Curtir Cifra'}
                    </button>
                    
                    {playlist_selector_html}
                    
                    <button class="controlBtn" id="leftHandedToggleBtn" onclick="toggleLeftHanded()" style="width: 100%; margin-top: 10px; background: #374151; color: #fff;">
                        Modo Canhoto: Desativado
                    </button>
                </div>

                <div class="controlCard chordControlCard">
                    <div class="controlTitle">Rolagem</div>

                    <button class="controlBtn autoScrollPrimary" onclick="toggleScroll()" id="scrollBtn">
                        Iniciar autorrolagem
                    </button>

                    <div class="speedBox autoScrollBox">
                        <span>Velocidade</span>
                        <button class="controlBtn" onclick="changeSpeed(-0.1)">-</button>
                        <span id="speedLabel">1.0x</span>
                        <button class="controlBtn" onclick="changeSpeed(0.1)">+</button>
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
                        <strong id="currentKeyMeta" data-original-key="{tom_musica}">{tom_musica}</strong>
                    </div>
                </div>
                <pre class="cifraBox">{conteudo}</pre>
            </main>

            <!-- 🎬 VÍDEO DIREITA -->
            <aside class="songVideo">
                <div class="videoWrapper">
                   {iframe_video}
                </div>
                <div id="asideChordDictionary" style="margin-top:20px;"></div>
            </aside>

        </div>

        </main>
    <script src="/static/js/chords_db_v2.js?v=2.0"></script>
    <script>
    document.addEventListener("DOMContentLoaded", function () {{

        const playChordSound = (shape) => {{
            if (!shape) return;
            try {{
                if (!audioCtx) {{
                    initSoundfont();
                }}
                if (audioCtx && audioCtx.state === 'suspended') {{
                    audioCtx.resume();
                }}
                const baseMidi = [40, 45, 50, 55, 59, 64];
                const notesToPlay = [];
                
                shape.frets.forEach((f, idx) => {{
                    if (f !== null && f !== 'x') {{
                        notesToPlay.push(baseMidi[idx] + f);
                    }}
                }});

                const strumDelay = 0.08; // Slower arpeggiation (dedilhado)

                if (guitarPlayer && audioCtx) {{
                    const now = audioCtx.currentTime;
                    notesToPlay.forEach((midi, i) => {{
                        guitarPlayer.play(midi, now + (i * strumDelay), {{ duration: 2.0, gain: 0.85 }});
                    }});
                }} else {{
                    const ctx = audioCtx || new AudioContext();
                    const now = ctx.currentTime;
                    notesToPlay.forEach((midi, i) => {{
                        const freq = 440 * Math.pow(2, (midi - 69) / 12);
                        const startTime = now + (i * strumDelay);
                        
                        const osc = ctx.createOscillator();
                        const subOsc = ctx.createOscillator();
                        const filter = ctx.createBiquadFilter();
                        const gainNode = ctx.createGain();
                        
                        osc.type = 'triangle';
                        osc.frequency.setValueAtTime(freq, startTime);
                        subOsc.type = 'sine';
                        subOsc.frequency.setValueAtTime(freq, startTime);
                        
                        filter.type = 'lowpass';
                        filter.Q.setValueAtTime(1, startTime);
                        filter.frequency.setValueAtTime(2500, startTime);
                        filter.frequency.exponentialRampToValueAtTime(140, startTime + 0.18);
                        
                        gainNode.gain.setValueAtTime(0, startTime);
                        gainNode.gain.linearRampToValueAtTime(0.15, startTime + 0.005);
                        gainNode.gain.exponentialRampToValueAtTime(0.001, startTime + 2.0);
                        
                        osc.connect(filter);
                        subOsc.connect(filter);
                        filter.connect(gainNode);
                        gainNode.connect(ctx.destination);
                        
                        osc.start(startTime);
                        subOsc.start(startTime);
                        
                        osc.stop(startTime + 2.1);
                        subOsc.stop(startTime + 2.1);
                    }});
                }}
            }} catch(e) {{
                console.error(e);
            }}
        }};

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
                    span.dataset.originalChord = match;
                    span.dataset.chord = match;

                    const diagram = document.createElement("div");
                    diagram.className = "chord-diagram";

                    span.appendChild(diagram);

                    let rendered = false;
                    let currentIndex = 0;
                    let shapes = null;

                    span.resetDiagram = () => {{
                        rendered = false;
                        currentIndex = 0;
                        shapes = null;
                        if (diagram.style.display === "block") {{
                            render();
                        }}
                    }};

                    const render = () => {{
                        if (!shapes) {{
                            shapes = getChordShapes(span.dataset.chord);
                        }}
                        const currentShape = (shapes && shapes.length > 0) ? shapes[currentIndex] : null;
                        
                        let htmlContent = `<div style="background:#fff; border-radius:10px; overflow:hidden; box-shadow:0 4px 16px rgba(0,0,0,0.18); display:flex; flex-direction:column; width:150px;">`;
                        
                        htmlContent += `
                        <div class="chord-header" style="display:flex; justify-content:space-between; align-items:center; padding: 6px 12px; border-bottom: 1px solid #e5e7eb; background:#fafafa; pointer-events: auto;">
                            <span style="font-size:13px; font-weight:bold; color:#1f2937; font-family:Arial, sans-serif;">${{span.dataset.chord}}</span>
                            <button class="play-chord-btn" style="border:none; background:none; cursor:pointer; padding:2px; display:flex; align-items:center; outline:none;" title="Ouvir acorde">
                                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#ff7a00" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                                    <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon>
                                    <path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07"></path>
                                </svg>
                            </button>
                        </div>
                        `;
                        
                        htmlContent += drawChordSVG(span.dataset.chord, currentShape);

                        if (shapes && shapes.length > 1) {{
                            htmlContent += `
                            <div class="chord-paginator" style="display:flex; justify-content:space-between; align-items:center; padding: 6px 12px; background:#fafafa; border-top:1px solid #e5e7eb; pointer-events: auto;">
                                <button class="prev-var-btn" style="border:none; background:none; cursor:pointer; font-weight:bold; color:#ff7a00; font-size:15px; padding:2px 8px; transition:0.2s; outline:none;">&larr;</button>
                                <span style="font-size:11px; color:#6b7280; font-family:Arial, sans-serif; font-weight:bold;">Posição ${{currentIndex + 1}}/${{shapes.length}}</span>
                                <button class="next-var-btn" style="border:none; background:none; cursor:pointer; font-weight:bold; color:#ff7a00; font-size:15px; padding:2px 8px; transition:0.2s; outline:none;">&rarr;</button>
                            </div>
                            `;
                        }}
                        htmlContent += `</div>`;
                        diagram.innerHTML = htmlContent;

                        if (currentShape) {{
                            const playBtn = diagram.querySelector(".play-chord-btn");
                            playBtn.addEventListener("click", (e) => {{
                                e.stopPropagation();
                                e.preventDefault();
                                playChordSound(currentShape);
                            }});
                        }}

                        if (shapes && shapes.length > 1) {{
                            const prevBtn = diagram.querySelector(".prev-var-btn");
                            const nextBtn = diagram.querySelector(".next-var-btn");
                            
                            prevBtn.addEventListener("click", (e) => {{
                                e.stopPropagation();
                                e.preventDefault();
                                currentIndex = (currentIndex - 1 + shapes.length) % shapes.length;
                                render();
                            }});

                            nextBtn.addEventListener("click", (e) => {{
                                e.stopPropagation();
                                e.preventDefault();
                                currentIndex = (currentIndex + 1) % shapes.length;
                                render();
                            }});
                        }}
                        
                        diagram.addEventListener("click", (e) => {{
                            e.stopPropagation();
                            e.preventDefault();
                        }});
                    }};

                    let hideTimeout = null;

                    span.addEventListener("mouseenter", () => {{
                        if (hideTimeout) {{
                            clearTimeout(hideTimeout);
                            hideTimeout = null;
                        }}
                        const rect = span.getBoundingClientRect();
                        diagram.style.left = (rect.left + rect.width / 2) + "px";
                        if (rect.top > 240) {{
                            diagram.style.bottom = (window.innerHeight - rect.top + 8) + "px";
                            diagram.style.top = "auto";
                        }} else {{
                            diagram.style.top = (rect.bottom + 8) + "px";
                            diagram.style.bottom = "auto";
                        }}
                        diagram.style.display = "block";
                        if (!rendered) {{
                            render();
                            rendered = true;
                        }}
                    }});

                    span.addEventListener("mouseleave", () => {{
                        hideTimeout = setTimeout(() => {{
                            diagram.style.display = "none";
                        }}, 150);
                    }});

                    diagram.addEventListener("mouseenter", () => {{
                        if (hideTimeout) {{
                            clearTimeout(hideTimeout);
                            hideTimeout = null;
                        }}
                    }});

                    diagram.addEventListener("mouseleave", () => {{
                        hideTimeout = setTimeout(() => {{
                            diagram.style.display = "none";
                        }}, 150);
                    }});

                    frag.appendChild(span);
                    lastIndex = offset + match.length;
                    return match;
                }});

                frag.appendChild(document.createTextNode(text.slice(lastIndex)));
                textNode.parentNode.replaceChild(frag, textNode);
            }});
        }});

        const buildAsideDictionary = () => {{
            const container = document.getElementById("asideChordDictionary");
            if (!container) return;
            container.innerHTML = "";

            const uniqueChords = new Set();
            document.querySelectorAll("pre.cifraBox .chord").forEach(span => {{
                const chordName = span.dataset.chord;
                if (chordName) {{
                    let isTuning = false;
                    let prev = span.previousSibling;
                    let lineText = "";
                    while (prev) {{
                        if (prev.nodeType === Node.TEXT_NODE) {{
                            const text = prev.nodeValue;
                            if (text.includes('\\n')) {{
                                lineText = text.substring(text.lastIndexOf('\\n') + 1) + lineText;
                                break;
                            }} else {{
                                lineText = text + lineText;
                            }}
                        }} else if (prev.classList && prev.classList.contains("chord")) {{
                            lineText = prev.innerText + lineText;
                        }}
                        prev = prev.previousSibling;
                    }}
                    if (lineText.toLowerCase().includes("afina") || lineText.toLowerCase().includes("tuning")) {{
                        isTuning = true;
                    }}
                    if (!isTuning) {{
                        uniqueChords.add(chordName);
                    }}
                }}
            }});

            if (uniqueChords.size === 0) return;

            const card = document.createElement("div");
            card.className = "controlCard";
            card.innerHTML = `
                <div class="controlTitle" style="margin-bottom:12px;">🎸 Acordes da Música</div>
                <div id="asideChordsGrid" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(70px, 1fr)); gap: 6px;"></div>
            `;
            container.appendChild(card);

            const grid = card.querySelector("#asideChordsGrid");

            uniqueChords.forEach(chordName => {{
                const shapes = getChordShapes(chordName);
                const firstShape = (shapes && shapes.length > 0) ? shapes[0] : null;

                const chordBox = document.createElement("div");
                chordBox.style.cssText = "background: #fafafa; border: 1px solid #e5e7eb; border-radius: 8px; padding: 6px; display: flex; flex-direction: column; align-items: center; cursor: pointer; transition: transform 0.15s, box-shadow 0.15s; text-align: center;";
                
                chordBox.addEventListener("mouseenter", () => {{
                    chordBox.style.transform = "scale(1.05)";
                    chordBox.style.boxShadow = "0 4px 8px rgba(0,0,0,0.06)";
                    chordBox.style.borderColor = "#ff7a00";
                }});
                chordBox.addEventListener("mouseleave", () => {{
                    chordBox.style.transform = "scale(1)";
                    chordBox.style.boxShadow = "none";
                    chordBox.style.borderColor = "#e5e7eb";
                }});

                chordBox.addEventListener("click", () => {{
                    if (firstShape) {{
                        playChordSound(firstShape);
                        chordBox.style.backgroundColor = "#ffebe0";
                        setTimeout(() => {{
                            chordBox.style.backgroundColor = "#fafafa";
                        }}, 200);
                    }}
                }});

                const titleSpan = document.createElement("span");
                titleSpan.style.cssText = "font-size: 11px; font-weight: bold; color: #1f2937; font-family: Arial, sans-serif; margin-bottom: 2px; display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; width: 100%;";
                titleSpan.textContent = chordName;
                chordBox.appendChild(titleSpan);

                const miniSvgContainer = document.createElement("div");
                miniSvgContainer.style.width = "55px";
                miniSvgContainer.style.height = "70px";
                miniSvgContainer.innerHTML = drawChordSVG(chordName, firstShape);
                
                const svgEl = miniSvgContainer.querySelector("svg");
                if (svgEl) {{
                    svgEl.setAttribute("width", "100%");
                    svgEl.setAttribute("height", "100%");
                }}

                chordBox.appendChild(miniSvgContainer);
                grid.appendChild(chordBox);
            }});
        }};

        // Build it initially
        buildAsideDictionary();

        // Expose it globally so the transposition function can call it
        window.buildAsideDictionary = buildAsideDictionary;
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
            window.scrollBy(0, scrollSpeed * delta / 45);

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
            scrollSpeed = Math.max(0.1, Math.min(4, scrollSpeed + delta));
            document.getElementById("speedLabel").innerText = scrollSpeed.toFixed(1) + "x";
        }}

        // =============================
        // TRANSPOSICAO VIA JAVASCRIPT
        // =============================
        const MAP_TO_INDEX = {{
            "C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4, "F": 5, "F#": 6, "Gb": 6, "G": 7, "G#": 8, "Ab": 8, "A": 9, "A#": 10, "Bb": 10, "B": 11
        }};
        const NOTAS_SHARP = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"];
        const NOTAS_FLAT = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"];

        function transporNotaJS(nota, semitons) {{
            if (!nota) return "";
            if (MAP_TO_INDEX[nota] === undefined) return nota;
            let idx = MAP_TO_INDEX[nota];
            let newIdx = (idx + semitons) % 12;
            if (newIdx < 0) newIdx += 12;
            if (nota.includes("b") || [1, 3, 8, 10].includes(newIdx)) {{
                return NOTAS_FLAT[newIdx];
            }}
            return NOTAS_SHARP[newIdx];
        }}

        function transporAcordeJS(chord, semitons) {{
            const m = chord.match(/^([A-G][#b]?)([^/]*)(?:\/([A-G][#b]?))?$/);
            if (!m) return chord;
            const root = m[1];
            const mod = m[2] || "";
            const slash = m[3];

            const newRoot = transporNotaJS(root, semitons);
            const newSlash = slash ? transporNotaJS(slash, semitons) : "";

            if (newSlash) {{
                return `${{newRoot}}${{mod}}/${{newSlash}}`;
            }}
            return `${{newRoot}}${{mod}}`;
        }}

        let currentSemitones = 0;

        function aplicarTransposicao(semitons) {{
            currentSemitones = semitons;
            
            // Update chord spans
            document.querySelectorAll(".chord").forEach(span => {{
                const orig = span.dataset.originalChord;
                if (!orig) return;
                const newChord = transporAcordeJS(orig, semitons);
                span.dataset.chord = newChord;
                span.firstChild.nodeValue = newChord;
                if (typeof span.resetDiagram === "function") {{
                    span.resetDiagram();
                }}
            }});

            // Update Key Labels (sidebar and meta)
            const keyLabel = document.getElementById("currentKeyLabel");
            if (keyLabel) {{
                const origKey = keyLabel.dataset.originalKey;
                if (origKey && origKey !== "—") {{
                    keyLabel.innerText = transporAcordeJS(origKey, semitons);
                }}
            }}
            const keyMeta = document.getElementById("currentKeyMeta");
            if (keyMeta) {{
                const origKey = keyMeta.dataset.originalKey;
                if (origKey && origKey !== "—") {{
                    keyMeta.innerText = transporAcordeJS(origKey, semitons);
                }}
            }}

            // Update Transpose UI label
            const label = document.getElementById("transposeLabel");
            if (label) {{
                label.innerText = (semitons >= 0 ? "+" : "") + semitons + " semitons";
            }}

            if (typeof buildAsideDictionary === "function") {{
                buildAsideDictionary();
            }}
        }}

        function transpor(v) {{
            const nextSemitones = currentSemitones + v;
            window.location.hash = "t=" + nextSemitones;
            aplicarTransposicao(nextSemitones);
        }}

        function resetTransposicao() {{
            window.location.hash = "t=0";
            aplicarTransposicao(0);
        }}

        window.isLeftHanded = localStorage.getItem("isLeftHanded") === "true";

        function toggleLeftHanded() {{
            window.isLeftHanded = !window.isLeftHanded;
            localStorage.setItem("isLeftHanded", window.isLeftHanded);
            const btn = document.getElementById("leftHandedToggleBtn");
            if (btn) {{
                btn.innerText = window.isLeftHanded ? "Modo Canhoto: Ativado" : "Modo Canhoto: Desativado";
                btn.style.background = window.isLeftHanded ? "#ff7a00" : "#374151";
            }}
            if (typeof buildAsideDictionary === 'function') {{
                buildAsideDictionary();
            }}
        }}

        // Apply transposition on load based on hash/search
        document.addEventListener("DOMContentLoaded", () => {{
            const leftHandedBtn = document.getElementById("leftHandedToggleBtn");
            if (leftHandedBtn) {{
                leftHandedBtn.innerText = window.isLeftHanded ? "Modo Canhoto: Ativado" : "Modo Canhoto: Desativado";
                leftHandedBtn.style.background = window.isLeftHanded ? "#ff7a00" : "#374151";
            }}
            // If the song doesn't have a defined key, grab the first chord on the page and use it
            const keyLabel = document.getElementById("currentKeyLabel");
            const keyMeta = document.getElementById("currentKeyMeta");
            if (keyLabel && (!keyLabel.dataset.originalKey || keyLabel.dataset.originalKey === "—" || keyLabel.dataset.originalKey.trim() === "")) {{
                const chords = document.querySelectorAll("pre.cifraBox .chord");
                let firstChord = null;
                for (let span of chords) {{
                    if (span.dataset.originalChord) {{
                        let isTuning = false;
                        let prev = span.previousSibling;
                        let lineText = "";
                        while (prev) {{
                            if (prev.nodeType === Node.TEXT_NODE) {{
                                const text = prev.nodeValue;
                                if (text.includes('\\n')) {{
                                    lineText = text.substring(text.lastIndexOf('\\n') + 1) + lineText;
                                    break;
                                }} else {{
                                    lineText = text + lineText;
                                }}
                            }} else if (prev.classList && prev.classList.contains("chord")) {{
                                lineText = prev.innerText + lineText;
                            }}
                            prev = prev.previousSibling;
                        }}
                        if (lineText.toLowerCase().includes("afina") || lineText.toLowerCase().includes("tuning")) {{
                            isTuning = true;
                        }}
                        if (isTuning) continue;

                        firstChord = span.dataset.originalChord;
                        break;
                    }}
                }}
                if (firstChord) {{
                    keyLabel.dataset.originalKey = firstChord;
                    if (keyMeta) {{
                        keyMeta.dataset.originalKey = firstChord;
                    }}
                    keyLabel.innerText = firstChord;
                    if (keyMeta) {{
                        keyMeta.innerText = firstChord;
                    }}
                }}
            }}

            let initialT = 0;
            const hash = window.location.hash;
            const match = hash.match(/t=(-?\d+)/);
            if (match) {{
                initialT = parseInt(match[1]);
            }} else {{
                const urlParams = new URLSearchParams(window.location.search);
                initialT = parseInt(urlParams.get("t") || "0");
            }}
            if (initialT !== 0) {{
                aplicarTransposicao(initialT);
            }}
        }});

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


@main_bp.route("/dicionario")
def dicionario_page():
    from modules.layout import header
    html = header("Dicionário de Acordes")
    html += """
    <style>
        .dictContainer {
            max-width: 1200px;
            margin: 30px auto;
            padding: 0 20px;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }
        .dictHeader {
            text-align: center;
            margin-bottom: 40px;
        }
        .dictHeader h1 {
            font-size: 32px;
            font-weight: 800;
            color: #111827;
            margin-bottom: 10px;
        }
        .dictHeader p {
            font-size: 16px;
            color: #6b7280;
        }
        .rootsPanel {
            display: flex;
            flex-wrap: wrap;
            justify-content: center;
            gap: 10px;
            margin-bottom: 30px;
        }
        .rootBtn {
            padding: 10px 18px;
            border-radius: 12px;
            border: 1px solid #e5e7eb;
            background: #ffffff;
            font-weight: 700;
            color: #1f2937;
            cursor: pointer;
            transition: all 0.15s ease;
        }
        .rootBtn:hover, .rootBtn.active {
            background: #ff7a00;
            color: #ffffff;
            border-color: #ff7a00;
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(255, 122, 0, 0.2);
        }
        .chordGrid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }
        .chordCard {
            background: #ffffff;
            border: 1px solid #e5e7eb;
            border-radius: 16px;
            padding: 16px;
            display: flex;
            flex-direction: column;
            align-items: center;
            cursor: pointer;
            transition: all 0.2s ease;
            box-shadow: 0 4px 6px rgba(0,0,0,0.02);
        }
        .chordCard:hover {
            transform: translateY(-4px);
            box-shadow: 0 8px 24px rgba(0,0,0,0.08);
            border-color: #ff7a00;
        }
        .chordCardName {
            font-size: 18px;
            font-weight: 800;
            color: #111827;
            margin-bottom: 12px;
        }
        .chordSvgContainer {
            width: 120px;
            height: 120px;
        }
        #chordSearch:focus {
            border-color: #ff7a00;
            box-shadow: 0 4px 14px rgba(255, 122, 0, 0.15);
        }
    </style>

    <div class="dictContainer">
        <div class="dictHeader">
            <h1>🎸 Dicionário de Acordes</h1>
            <p>Selecione uma nota fundamental ou digite o nome de um acorde para visualizar e ouvir os desenhos.</p>
        </div>

        <div class="searchWrapper" style="max-width: 500px; margin: 0 auto 30px auto; position: relative; display: flex; gap: 10px;">
            <input type="text" id="chordSearch" placeholder="Busque por um acorde (ex: C, F#m7, Bb...)" 
                   style="flex: 1; padding: 14px 20px; font-size: 16px; border-radius: 14px; border: 1px solid #e5e7eb; box-shadow: 0 4px 6px rgba(0,0,0,0.02); outline: none; transition: all 0.2s;" />
            <button id="leftHandedToggleBtn" onclick="toggleLeftHanded()" 
                    style="padding: 0 20px; font-size: 14px; font-weight: 700; border-radius: 14px; border: none; background: #374151; color: #fff; cursor: pointer; transition: all 0.2s; white-space: nowrap;">
                Modo Canhoto: Desativado
            </button>
        </div>

        <div class="rootsPanel">
            <button class="rootBtn active" onclick="selectRoot('C')">C</button>
            <button class="rootBtn" onclick="selectRoot('C#')">C# / Db</button>
            <button class="rootBtn" onclick="selectRoot('D')">D</button>
            <button class="rootBtn" onclick="selectRoot('D#')">D# / Eb</button>
            <button class="rootBtn" onclick="selectRoot('E')">E</button>
            <button class="rootBtn" onclick="selectRoot('F')">F</button>
            <button class="rootBtn" onclick="selectRoot('F#')">F# / Gb</button>
            <button class="rootBtn" onclick="selectRoot('G')">G</button>
            <button class="rootBtn" onclick="selectRoot('G#')">G# / Ab</button>
            <button class="rootBtn" onclick="selectRoot('A')">A</button>
            <button class="rootBtn" onclick="selectRoot('A#')">A# / Bb</button>
            <button class="rootBtn" onclick="selectRoot('B')">B</button>
            <button class="rootBtn" onclick="selectRoot('Todos')">Todos</button>
        </div>

        <div id="dictionaryGrid" class="chordGrid"></div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/soundfont-player@0.12.0/dist/soundfont-player.min.js"></script>
    <script src="/static/js/chords_db_v2.js?v=2.0"></script>
    <script>
        let guitarPlayer = null;
        let audioCtx = null;

        window.isLeftHanded = localStorage.getItem("isLeftHanded") === "true";

        function toggleLeftHanded() {
            window.isLeftHanded = !window.isLeftHanded;
            localStorage.setItem("isLeftHanded", window.isLeftHanded);
            const btn = document.getElementById("leftHandedToggleBtn");
            if (btn) {
                btn.innerText = window.isLeftHanded ? "Modo Canhoto: Ativado" : "Modo Canhoto: Desativado";
                btn.style.background = window.isLeftHanded ? "#ff7a00" : "#374151";
            }
            // Trigger redrawing of the dictionary or search results
            const searchInput = document.getElementById("chordSearch");
            if (searchInput && searchInput.value.trim() !== "") {
                renderSearchResults(searchInput.value.trim());
            } else {
                renderDictionary();
            }
        }

        function initSoundfont() {
            if (audioCtx) return;
            try {
                const AudioContextClass = window.AudioContext || window.webkitAudioContext;
                audioCtx = new AudioContextClass();
                const preset = localStorage.getItem("defaultPreset") || "acoustic_guitar_nylon";
                Soundfont.instrument(audioCtx, preset).then(function (inst) {
                    guitarPlayer = inst;
                }).catch(e => console.log("SoundFont failed, using synth", e));
            } catch(e) {
                console.log("Audio not supported", e);
            }
        }
        document.addEventListener("mouseenter", initSoundfont, { once: true });
        document.addEventListener("click", initSoundfont, { once: true });

        const playChordSound = (shape) => {
            if (!shape) return;
            try {
                if (!audioCtx) initSoundfont();
                if (audioCtx && audioCtx.state === 'suspended') audioCtx.resume();
                
                const baseMidi = [40, 45, 50, 55, 59, 64];
                const notesToPlay = [];
                shape.frets.forEach((f, idx) => {
                    if (f !== null && f !== 'x') {
                        notesToPlay.push(baseMidi[idx] + f);
                    }
                });

                const strumDelay = 0.08;
                if (guitarPlayer && audioCtx) {
                    const now = audioCtx.currentTime;
                    notesToPlay.forEach((midi, i) => {
                        guitarPlayer.play(midi, now + (i * strumDelay), { duration: 2.0, gain: 0.85 });
                    });
                } else {
                    const ctx = audioCtx || new AudioContext();
                    const now = ctx.currentTime;
                    notesToPlay.forEach((midi, i) => {
                        const freq = 440 * Math.pow(2, (midi - 69) / 12);
                        const startTime = now + (i * strumDelay);
                        const osc = ctx.createOscillator();
                        const subOsc = ctx.createOscillator();
                        const filter = ctx.createBiquadFilter();
                        const gainNode = ctx.createGain();
                        
                        osc.type = 'triangle';
                        osc.frequency.setValueAtTime(freq, startTime);
                        subOsc.type = 'sine';
                        subOsc.frequency.setValueAtTime(freq, startTime);
                        
                        filter.type = 'lowpass';
                        filter.Q.setValueAtTime(1, startTime);
                        filter.frequency.setValueAtTime(2500, startTime);
                        filter.frequency.exponentialRampToValueAtTime(140, startTime + 0.18);
                        
                        gainNode.gain.setValueAtTime(0, startTime);
                        gainNode.gain.linearRampToValueAtTime(0.15, startTime + 0.005);
                        gainNode.gain.exponentialRampToValueAtTime(0.001, startTime + 2.0);
                        
                        osc.connect(filter);
                        subOsc.connect(filter);
                        filter.connect(gainNode);
                        gainNode.connect(ctx.destination);
                        
                        osc.start(startTime);
                        subOsc.start(startTime);
                        osc.stop(startTime + 2.1);
                        subOsc.stop(startTime + 2.1);
                    });
                }
            } catch(e) {
                console.error(e);
            }
        };

        let currentRoot = 'C';

        function selectRoot(note) {
            document.getElementById("chordSearch").value = "";
            document.querySelectorAll('.rootBtn').forEach(btn => {
                if (btn.innerText.startsWith(note)) {
                    btn.classList.add('active');
                } else {
                    btn.classList.remove('active');
                }
            });
            currentRoot = note;
            renderDictionary();
        }

        function renderDictionary() {
            const grid = document.getElementById("dictionaryGrid");
            grid.innerHTML = "";

            if (currentRoot === 'Todos') {
                Object.keys(chordShapes).forEach(chordName => {
                    const shapes = chordShapes[chordName];
                    if (shapes && shapes.length > 0) {
                        shapes.forEach((shape, index) => {
                            const card = document.createElement("div");
                            card.className = "chordCard";
                            
                            card.innerHTML = `
                                <div class="chordCardName">${chordName} <span style="font-size:11px; color:#6b7280; font-weight:normal;">(Pos. ${index + 1})</span></div>
                                <div class="chordSvgContainer"></div>
                            `;
                            
                            const svgContainer = card.querySelector(".chordSvgContainer");
                            svgContainer.innerHTML = drawChordSVG(chordName, shape);
                            
                            const svgEl = svgContainer.querySelector("svg");
                            if (svgEl) {
                                svgEl.setAttribute("width", "100%");
                                svgEl.setAttribute("height", "100%");
                            }

                            card.addEventListener("click", () => {
                                playChordSound(shape);
                                card.style.backgroundColor = "#ffebe0";
                                setTimeout(() => {
                                    card.style.backgroundColor = "#ffffff";
                                }, 200);
                            });

                            grid.appendChild(card);
                        });
                    }
                });
                return;
            }

            const suffixes = ["", "m", "7", "maj7", "9", "sus4", "5"];
            
            let notesToQuery = [currentRoot];
            if (currentRoot === 'C#') notesToQuery.push('Db');
            if (currentRoot === 'D#') notesToQuery.push('Eb');
            if (currentRoot === 'F#') notesToQuery.push('Gb');
            if (currentRoot === 'G#') notesToQuery.push('Ab');
            if (currentRoot === 'A#') notesToQuery.push('Bb');

            notesToQuery.forEach(root => {
                suffixes.forEach(suffix => {
                    const chordName = root + suffix;
                    const shapes = getChordShapes(chordName);
                    if (shapes && shapes.length > 0) {
                        shapes.forEach((shape, index) => {
                            const card = document.createElement("div");
                            card.className = "chordCard";
                            
                            card.innerHTML = `
                                <div class="chordCardName">${chordName} <span style="font-size:11px; color:#6b7280; font-weight:normal;">(Pos. ${index + 1})</span></div>
                                <div class="chordSvgContainer"></div>
                            `;
                            
                            const svgContainer = card.querySelector(".chordSvgContainer");
                            svgContainer.innerHTML = drawChordSVG(chordName, shape);
                            
                            const svgEl = svgContainer.querySelector("svg");
                            if (svgEl) {
                                svgEl.setAttribute("width", "100%");
                                svgEl.setAttribute("height", "100%");
                            }

                            card.addEventListener("click", () => {
                                playChordSound(shape);
                                card.style.backgroundColor = "#ffebe0";
                                setTimeout(() => {
                                    card.style.backgroundColor = "#ffffff";
                                }, 200);
                            });

                            grid.appendChild(card);
                        });
                    }
                });
            });
        }

        function renderSearchResults(query) {
            const grid = document.getElementById("dictionaryGrid");
            grid.innerHTML = "";

            document.querySelectorAll('.rootBtn').forEach(btn => btn.classList.remove('active'));

            const queryLower = query.toLowerCase();
            const matchingKeys = Object.keys(chordShapes).filter(key => 
                key.toLowerCase().includes(queryLower)
            );

            matchingKeys.sort((a, b) => {
                const aLower = a.toLowerCase();
                const bLower = b.toLowerCase();
                if (aLower === queryLower) return -1;
                if (bLower === queryLower) return 1;
                if (aLower.startsWith(queryLower) && !bLower.startsWith(queryLower)) return -1;
                if (!aLower.startsWith(queryLower) && bLower.startsWith(queryLower)) return 1;
                return a.localeCompare(b);
            });

            if (matchingKeys.length === 0) {
                grid.innerHTML = `
                    <div style="grid-column: 1/-1; text-align: center; padding: 40px; color: #9ca3af; font-size: 16px; font-weight: bold;">
                        Nenhum acorde encontrado para "${query}"
                    </div>
                `;
                return;
            }

            matchingKeys.forEach(chordName => {
                const shapes = chordShapes[chordName];
                if (shapes && shapes.length > 0) {
                    shapes.forEach((shape, index) => {
                        const card = document.createElement("div");
                        card.className = "chordCard";
                        
                        card.innerHTML = `
                            <div class="chordCardName">${chordName} <span style="font-size:11px; color:#6b7280; font-weight:normal;">(Pos. ${index + 1})</span></div>
                            <div class="chordSvgContainer"></div>
                        `;
                        
                        const svgContainer = card.querySelector(".chordSvgContainer");
                        svgContainer.innerHTML = drawChordSVG(chordName, shape);
                        
                        const svgEl = svgContainer.querySelector("svg");
                        if (svgEl) {
                            svgEl.setAttribute("width", "100%");
                            svgEl.setAttribute("height", "100%");
                        }

                        card.addEventListener("click", () => {
                            playChordSound(shape);
                            card.style.backgroundColor = "#ffebe0";
                            setTimeout(() => {
                                card.style.backgroundColor = "#ffffff";
                            }, 200);
                        });

                        grid.appendChild(card);
                    });
                }
            });
        }

         document.addEventListener("DOMContentLoaded", () => {
            const btn = document.getElementById("leftHandedToggleBtn");
            if (btn) {
                btn.innerText = window.isLeftHanded ? "Modo Canhoto: Ativado" : "Modo Canhoto: Desativado";
                btn.style.background = window.isLeftHanded ? "#ff7a00" : "#374151";
            }
            renderDictionary();

            const searchInput = document.getElementById("chordSearch");
            searchInput.addEventListener("input", (e) => {
                const query = e.target.value.trim();
                if (query === "") {
                    selectRoot('C');
                } else {
                    renderSearchResults(query);
                }
            });
        });
    </script>
    """
    return html


# ==========================================
# PAINEL DE CONTROLE DO USUÁRIO
# ==========================================
import uuid

@main_bp.route("/login", methods=["GET", "POST"])
def login_route():
    erro = None
    if request.method == "POST":
        user = request.form.get("username")
        senha = request.form.get("password")
        if user == "adm" and senha == "adm":
            session["user"] = "adm"
            return redirect(url_for("main.painel_route"))
        else:
            erro = "Credenciais inválidas. Tente 'adm' e 'adm'."
            
    html = header("CifrasFlix - Login")
    html += f"""
    <div style="max-width: 400px; margin: 80px auto; padding: 40px; background: rgba(255,255,255,0.7); backdrop-filter: blur(16px); border-radius: 20px; border: 1px solid rgba(255,255,255,0.4); box-shadow: 0 10px 30px rgba(0,0,0,0.05); text-align: center; font-family: 'Inter', sans-serif;">
        <h2 style="font-weight: 800; font-size: 28px; color: #111827; margin-bottom: 8px;">Entrar no CifrasFlix</h2>
        <p style="color: #6b7280; font-size: 14px; margin-bottom: 30px;">Acesse seu painel com a conta temporária</p>
        
        {f'<div style="background: #fee2e2; color: #ef4444; padding: 12px; border-radius: 10px; font-size: 13px; font-weight: 600; margin-bottom: 20px; text-align: left;">{erro}</div>' if erro else ''}
        
        <form method="POST" style="display: flex; flex-direction: column; gap: 16px;">
            <div style="text-align: left;">
                <label style="font-size: 13px; font-weight: bold; color: #374151; display: block; margin-bottom: 6px;">Usuário</label>
                <input type="text" name="username" placeholder="adm" required style="width: 100%; padding: 12px 16px; border-radius: 10px; border: 1px solid #d1d5db; font-size: 15px; outline: none; transition: border 0.2s;" />
            </div>
            <div style="text-align: left;">
                <label style="font-size: 13px; font-weight: bold; color: #374151; display: block; margin-bottom: 6px;">Senha</label>
                <input type="password" name="password" placeholder="adm" required style="width: 100%; padding: 12px 16px; border-radius: 10px; border: 1px solid #d1d5db; font-size: 15px; outline: none; transition: border 0.2s;" />
            </div>
            <button type="submit" style="width: 100%; padding: 14px; margin-top: 10px; background: #ff7a00; color: #fff; border: none; border-radius: 10px; font-weight: 700; font-size: 16px; cursor: pointer; transition: background 0.2s; box-shadow: 0 4px 12px rgba(255,122,0,0.2);">Acessar Painel</button>
        </form>
    </div>
    """
    return html

@main_bp.route("/logout")
def logout_route():
    session.pop("user", None)
    return redirect(url_for("main.home"))

@main_bp.route("/painel")
def painel_route():
    if session.get("user") != "adm":
        return redirect(url_for("main.login_route"))
        
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""
        SELECT m.id, m.titulo, m.slug, a.nome, a.slug, m.tom, m.uid
        FROM favoritos f
        JOIN musicas m ON f.musica_id = m.id
        JOIN artistas a ON m.artista_id = a.id
        ORDER BY m.titulo
    """)
    favoritos = c.fetchall()
    
    c.execute("""
        SELECT p.id, p.nome, p.publica, p.likes, COUNT(pm.musica_id)
        FROM playlists p
        LEFT JOIN playlist_musicas pm ON p.id = pm.playlist_id
        GROUP BY p.id
        ORDER BY p.id DESC
    """)
    playlists = c.fetchall()
    conn.close()
    
    sucesso = request.args.get("sucesso")
    
    html = header("CifrasFlix - Painel de Controle")
    
    # Render layout
    html += f"""
    <style>
        .panelWrapper {{
            max-width: 1200px;
            margin: 40px auto;
            padding: 0 20px;
            font-family: 'Inter', sans-serif;
        }}
        .panelHeader {{
            margin-bottom: 30px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .panelGrid {{
            display: grid;
            grid-template-columns: 1fr 2fr;
            gap: 30px;
        }}
        @media(max-width: 768px) {{
            .panelGrid {{
                grid-template-columns: 1fr;
            }}
        }}
        .panelCard {{
            background: rgba(255,255,255,0.7);
            backdrop-filter: blur(16px);
            border-radius: 20px;
            border: 1px solid rgba(255,255,255,0.4);
            padding: 24px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.02);
            margin-bottom: 30px;
        }}
        .cardTitle {{
            font-weight: 800;
            font-size: 20px;
            color: #111827;
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .favItem {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 12px 16px;
            background: #f9fafb;
            border-radius: 12px;
            margin-bottom: 10px;
            border: 1px solid #f3f4f6;
            transition: all 0.2s;
        }}
        .favItem:hover {{
            background: #f3f4f6;
            transform: translateX(4px);
        }}
        .favInfo a {{
            text-decoration: none;
            color: #111827;
            font-weight: 700;
        }}
        .favInfo span {{
            font-size: 12px;
            color: #6b7280;
            margin-left: 8px;
        }}
        .formGroup {{
            margin-bottom: 16px;
            text-align: left;
        }}
        .formGroup label {{
            font-size: 13px;
            font-weight: bold;
            color: #374151;
            display: block;
            margin-bottom: 6px;
        }}
        .formGroup input, .formGroup textarea, .formGroup select {{
            width: 100%;
            padding: 12px;
            border-radius: 10px;
            border: 1px solid #d1d5db;
            font-size: 14px;
            outline: none;
            transition: border 0.2s;
            box-sizing: border-box;
        }}
        .formGroup input:focus, .formGroup textarea:focus {{
            border-color: #ff7a00;
        }}
        .formRow {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 16px;
        }}
        .toggleBtn {{
            padding: 12px;
            border-radius: 10px;
            border: 2px solid #d1d5db;
            background: #fff;
            font-weight: 700;
            cursor: pointer;
            transition: all 0.2s;
            text-align: center;
        }}
        .toggleBtn.active {{
            border-color: #ff7a00;
            background: #ffebe0;
            color: #ff7a00;
        }}
    </style>
    
    <div class="panelWrapper">
        <div class="panelHeader">
            <div>
                <p style="font-size:14px; color:#ff7a00; font-weight:700; text-transform:uppercase; margin:0 0 4px 0;">Painel do Usuário</p>
                <h1 style="font-size:32px; font-weight:800; color:#111827; margin:0;">Olá, Administrador!</h1>
            </div>
            <a href="/logout" style="padding:10px 20px; background:#fee2e2; color:#ef4444; text-decoration:none; border-radius:10px; font-weight:bold; font-size:14px;">Sair da Conta</a>
        </div>
        
        {f'<div style="background: #ecfdf5; color: #10b981; padding: 16px; border-radius: 14px; font-weight: bold; margin-bottom: 24px; box-shadow: 0 4px 12px rgba(16,185,129,0.1);">Cifra enviada com sucesso e cadastrada no acervo!</div>' if sucesso else ''}

        <div class="panelGrid">
            <!-- Coluna Esquerda: Configurações -->
            <div>
                <div class="panelCard">
                    <div class="cardTitle">⚙️ Configurações Gerais</div>
                    
                    <div class="formGroup">
                        <label>Orientação da Mão</label>
                        <div style="display:flex; gap:10px;">
                            <button id="handDestro" class="toggleBtn" style="flex:1;" onclick="setHandPreference(false)">Destro</button>
                            <button id="handCanhoto" class="toggleBtn" style="flex:1;" onclick="setHandPreference(true)">Canhoto</button>
                        </div>
                    </div>
                    
                    <div class="formGroup">
                        <label>Timbre Padrão do Reprodutor</label>
                        <select id="defaultPreset" onchange="setDefaultPreset(this.value)">
                            <option value="acoustic_guitar_nylon">Violão de Nylon (Padrão)</option>
                            <option value="acoustic_guitar_steel">Violão de Aço</option>
                            <option value="electric_guitar_clean">Guitarra Limpa</option>
                            <option value="acoustic_grand_piano">Piano Acústico</option>
                        </select>
                    </div>
                    
                    <div class="formGroup">
                        <label>Velocidade Padrão de Autorolagem</label>
                        <div style="display:flex; align-items:center; gap:10px;">
                            <input type="range" id="defaultSpeed" min="0.5" max="3" step="0.1" value="1.0" oninput="updateSpeedLabel(this.value)" onchange="setDefaultSpeed(this.value)" style="flex:1;" />
                            <strong id="speedLabel" style="width:40px; text-align:right;">1.0x</strong>
                        </div>
                    </div>
                </div>

                <div class="panelCard">
                    <div class="cardTitle">📁 Minhas Playlists ({len(playlists)})</div>
                    
                    <form method="POST" action="/painel/playlist/criar" style="display:flex; flex-direction:column; gap:10px; margin-bottom:20px;">
                        <input type="text" name="nome_playlist" placeholder="Nome da Playlist (ex: Ensaios)" required style="padding:10px; border-radius:8px; border:1px solid #d1d5db; width:100%; box-sizing:border-box;" />
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            <label style="font-size:13px; color:#4b5563; font-weight:700;">Tornar Pública</label>
                            <input type="checkbox" name="publica" value="1" style="width:20px; height:20px;" />
                        </div>
                        <button type="submit" style="padding:10px; background:#ff7a00; color:#fff; border:none; border-radius:8px; font-weight:700; cursor:pointer;">Criar Playlist</button>
                    </form>
                    
                    <div class="playlistList" style="max-height: 250px; overflow-y: auto;">
    """
    
    if playlists:
        for pid, nome, publica, likes, total_musicas in playlists:
            pub_label = "Pública" if publica else "Privada"
            pub_color = "#10b981" if publica else "#9ca3af"
            html += f"""
            <div class="favItem" style="padding: 10px 12px; margin-bottom: 8px;">
                <div class="favInfo">
                    <a href="/playlists/{pid}" style="font-size:14px; font-weight:700; text-decoration:none; color:#111827;">{nome}</a>
                    <span style="font-size:11px; color:#6b7280; margin-left:5px;">({total_musicas} músicas)</span>
                </div>
                <div style="display:flex; gap:10px; align-items:center;">
                    <span style="font-size:11px; font-weight:bold; color:{pub_color};">{pub_label}</span>
                    <form method="POST" action="/painel/playlist/deletar/{pid}" style="margin:0;">
                        <button type="submit" style="background:none; border:none; color:#ef4444; font-weight:bold; font-size:12px; cursor:pointer;">Excluir</button>
                    </form>
                </div>
            </div>
            """
    else:
        html += '<p style="color:#9ca3af; text-align:center; padding:10px; font-size:13px; font-weight:bold; margin:0;">Nenhuma playlist criada.</p>'
        
    html += f"""
                    </div>
                </div>
            </div>
            
            <!-- Coluna Direita: Favoritos e Enviar Música -->
            <div>
                <div class="panelCard">
                    <div class="cardTitle">⭐️ Minhas Cifras Favoritas ({len(favoritos)})</div>
                    <div class="favList">
    """
    
    if favoritos:
        for fid, title, slug, artist_name, artist_slug, tom, suid in favoritos:
            html += f"""
            <div class="favItem">
                <div class="favInfo">
                    <a href="/artista/{artist_slug}/{suid}">{title}</a>
                    <span>({artist_name})</span>
                </div>
                <div style="display:flex; gap:10px; align-items:center;">
                    <span style="background:#fff; border:1px solid #d1d5db; padding:2px 8px; border-radius:6px; font-size:12px; font-weight:bold; color:#4b5563;">Tom: {tom or "N/D"}</span>
                    <a href="/favoritar/{fid}" style="color:#ef4444; font-size:13px; font-weight:700; text-decoration:none;">Remover</a>
                </div>
            </div>
            """
    else:
        html += '<p style="color:#9ca3af; text-align:center; padding:20px; font-weight:bold; margin:0;">Você ainda não favoritou nenhuma música.</p>'
        
    html += """
                    </div>
                </div>
                
                <div class="panelCard">
                    <div class="cardTitle">➕ Enviar Nova Música</div>
                    <form method="POST" action="/painel/enviar">
                        <div class="formGroup">
                            <label>Artista / Banda</label>
                            <input type="text" name="artista" placeholder="Ex: Legião Urbana" required />
                        </div>
                        <div class="formGroup">
                            <label>Título da Música</label>
                            <input type="text" name="titulo" placeholder="Ex: Eduardo e Mônica" required />
                        </div>
                        
                        <div class="formRow">
                            <div class="formGroup">
                                <label>Tom Inicial</label>
                                <input type="text" name="tom" placeholder="Ex: C, G, Am..." required />
                            </div>
                            <div class="formGroup">
                                <label>Capotraste</label>
                                <input type="text" name="capotraste" placeholder="Ex: Sem capo, 2ª casa..." />
                            </div>
                        </div>
                        
                        <div class="formGroup">
                            <label>Afinação</label>
                            <input type="text" name="afinacao" placeholder="Ex: Padrão (E A D G B E)" value="Padrão (E A D G B E)" />
                        </div>
                        
                        <div class="formGroup">
                            <label>Conteúdo da Cifra (Letras & Acordes)</label>
                            <textarea name="conteudo" rows="12" placeholder="Digite ou cole a cifra aqui... Coloque os acordes entre parênteses para renderização alinhada." required style="font-family: monospace; line-height: 1.5; font-size: 13px;"></textarea>
                        </div>
                        
                        <button type="submit" style="width:100%; padding:14px; background:#ff7a00; color:#fff; border:none; border-radius:10px; font-weight:700; font-size:16px; cursor:pointer; box-shadow:0 4px 12px rgba(255,122,0,0.2);">Cadastrar Cifra</button>
                    </form>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        // Settings Sync
        document.addEventListener("DOMContentLoaded", () => {
            // Hand preference
            const isLeft = localStorage.getItem("isLeftHanded") === "true";
            updateHandUI(isLeft);
            
            // Instrument preset
            const preset = localStorage.getItem("defaultPreset") || "acoustic_guitar_nylon";
            document.getElementById("defaultPreset").value = preset;
            
            // Speed
            const speed = localStorage.getItem("defaultSpeed") || "1.0";
            document.getElementById("defaultSpeed").value = speed;
            document.getElementById("speedLabel").innerText = speed + "x";
        });
        
        function updateHandUI(isLeft) {
            document.getElementById("handDestro").className = isLeft ? "toggleBtn" : "toggleBtn active";
            document.getElementById("handCanhoto").className = isLeft ? "toggleBtn active" : "toggleBtn";
        }
        
        function setHandPreference(isLeft) {
            localStorage.setItem("isLeftHanded", isLeft);
            window.isLeftHanded = isLeft;
            updateHandUI(isLeft);
        }
        
        function setDefaultPreset(preset) {
            localStorage.setItem("defaultPreset", preset);
        }
        
        function updateSpeedLabel(val) {
            document.getElementById("speedLabel").innerText = val + "x";
        }
        
        function setDefaultSpeed(speed) {
            localStorage.setItem("defaultSpeed", speed);
        }
    </script>
    """
    return html

@main_bp.route("/painel/enviar", methods=["POST"])
def enviar_musica_route():
    if session.get("user") != "adm":
        return redirect(url_for("main.login_route"))
        
    artista_nome = request.form.get("artista", "").strip()
    titulo = request.form.get("titulo", "").strip()
    tom = request.form.get("tom", "").strip()
    capo = request.form.get("capotraste", "").strip() or "Sem capotraste"
    afinacao = request.form.get("afinacao", "").strip() or "Padrão (E A D G B E)"
    conteudo = request.form.get("conteudo", "").strip()
    
    if not artista_nome or not titulo or not conteudo:
        return redirect(url_for("main.painel_route"))
        
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    
    # 1. Artista
    artista_slug = slugify(artista_nome)
    c.execute("SELECT id FROM artistas WHERE slug = ?", (artista_slug,))
    row_art = c.fetchone()
    if row_art:
        artista_id = row_art[0]
    else:
        c.execute("INSERT INTO artistas (nome, slug) VALUES (?, ?)", (artista_nome, artista_slug))
        artista_id = c.lastrowid
        
    # 2. Musica
    song_uid = str(uuid.uuid4())[:8] # Generates 8-character uid
    song_slug = slugify(titulo)
    
    c.execute("""
        INSERT INTO musicas (titulo, slug, uid, artista_id, conteudo, tom, afinacao, capotraste)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (titulo, song_slug, song_uid, artista_id, conteudo, tom, afinacao, capo))
    
    conn.commit()
    conn.close()
    
    return redirect(url_for("main.painel_route", sucesso=1))


# ==========================================
# PLAYLISTS / REPERTÓRIOS
# ==========================================

@main_bp.route("/painel/playlist/criar", methods=["POST"])
def criar_playlist_route():
    if session.get("user") != "adm":
        return redirect(url_for("main.login_route"))
        
    nome = request.form.get("nome_playlist", "").strip()
    publica = 1 if request.form.get("publica") else 0
    
    if not nome:
        return redirect(url_for("main.painel_route"))
        
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("INSERT INTO playlists (nome, publica) VALUES (?, ?)", (nome, publica))
    conn.commit()
    conn.close()
    return redirect(url_for("main.painel_route"))

@main_bp.route("/painel/playlist/deletar/<int:pid>", methods=["POST"])
def deletar_playlist_route(pid):
    if session.get("user") != "adm":
        return redirect(url_for("main.login_route"))
        
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("DELETE FROM playlists WHERE id = ?", (pid,))
    c.execute("DELETE FROM playlist_musicas WHERE playlist_id = ?", (pid,))
    conn.commit()
    conn.close()
    return redirect(url_for("main.painel_route"))

@main_bp.route("/painel/playlist/adicionar", methods=["POST"])
def adicionar_musica_playlist():
    if session.get("user") != "adm":
        return redirect(url_for("main.login_route"))
        
    pid = request.form.get("playlist_id")
    mid = request.form.get("musica_id")
    
    if not pid or not mid:
        return redirect(request.referrer or url_for("main.home"))
        
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    
    # Check if already added
    c.execute("SELECT id FROM playlist_musicas WHERE playlist_id = ? AND musica_id = ?", (pid, mid))
    if not c.fetchone():
        c.execute("INSERT INTO playlist_musicas (playlist_id, musica_id) VALUES (?, ?)", (pid, mid))
        conn.commit()
        
    conn.close()
    return redirect(request.referrer or url_for("main.home"))

@main_bp.route("/playlists")
@main_bp.route("/listas")
def playlists_gallery():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    
    # 1. Load community public playlists
    c.execute("""
        SELECT p.id, p.nome, p.likes, COUNT(pm.musica_id)
        FROM playlists p
        LEFT JOIN playlist_musicas pm ON p.id = pm.playlist_id
        WHERE p.publica = 1
        GROUP BY p.id
        ORDER BY p.likes DESC
    """)
    public_playlists = c.fetchall()
    
    # 2. Load my playlists (both public and private) if logged in
    my_playlists = []
    liked_songs = []
    is_logged = session.get("user") == "adm"
    if is_logged:
        c.execute("""
            SELECT p.id, p.nome, p.publica, p.likes, COUNT(pm.musica_id)
            FROM playlists p
            LEFT JOIN playlist_musicas pm ON p.id = pm.playlist_id
            GROUP BY p.id
            ORDER BY p.id DESC
        """)
        my_playlists = c.fetchall()
        
        c.execute("""
            SELECT m.id, m.titulo, m.slug, a.nome, a.slug, m.tom, m.uid
            FROM favoritos f
            JOIN musicas m ON f.musica_id = m.id
            JOIN artistas a ON m.artista_id = a.id
            ORDER BY m.titulo
        """)
        liked_songs = c.fetchall()
        
    conn.close()
    
    html = header("CifrasFlix - Repertórios & Playlists")
    
    html += """
    <style>
        .playlistsWrapper {
            max-width: 1200px;
            margin: 40px auto;
            padding: 0 20px;
            font-family: 'Inter', sans-serif;
        }
        .playlistsHero {
            text-align: center;
            margin-bottom: 50px;
        }
        .playlistsHero h1 {
            font-size: 38px;
            font-weight: 800;
            color: #111827;
            margin-bottom: 12px;
        }
        .playlistsHero p {
            color: #6b7280;
            font-size: 16px;
            max-width: 600px;
            margin: 0 auto;
        }
        .sectionTitle {
            font-size: 26px;
            font-weight: 800;
            color: #111827;
            margin: 40px 0 20px 0;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 2px solid #f3f4f6;
            padding-bottom: 10px;
        }
        .playlistsGrid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 24px;
        }
        .playlistCard {
            background: rgba(255,255,255,0.7);
            backdrop-filter: blur(16px);
            border-radius: 20px;
            border: 1px solid rgba(255,255,255,0.4);
            padding: 24px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.02);
            transition: all 0.2s ease;
            text-decoration: none;
            color: #111827;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            min-height: 180px;
            box-sizing: border-box;
            position: relative;
        }
        .playlistCard:hover {
            transform: translateY(-4px);
            box-shadow: 0 12px 30px rgba(255,122,0,0.08);
            border-color: #ff7a00;
        }
        .playlistName {
            font-size: 20px;
            font-weight: 800;
            margin: 0 0 8px 0;
        }
        .playlistMeta {
            font-size: 13px;
            color: #6b7280;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .playlistFooter {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-top: 20px;
            border-top: 1px solid #f3f4f6;
            padding-top: 15px;
        }
        .likeBtn {
            background: none;
            border: none;
            color: #ef4444;
            font-weight: bold;
            display: inline-flex;
            align-items: center;
            gap: 6px;
            cursor: pointer;
            transition: transform 0.2s;
            font-size: 14px;
        }
        .likeBtn:hover {
            transform: scale(1.1);
        }
        .badge {
            position: absolute;
            top: 20px;
            right: 20px;
            padding: 4px 8px;
            border-radius: 6px;
            font-size: 11px;
            font-weight: bold;
        }
        .pub { background: #ecfdf5; color: #10b981; }
        .priv { background: #f3f4f6; color: #6b7280; }
    </style>
    
    <div class="playlistsWrapper">
        <div class="playlistsHero">
            <p style="font-size:14px; color:#ff7a00; font-weight:700; text-transform:uppercase; margin-bottom:6px;">Repertórios & Playlists</p>
            <h1>Playlists de Cifras</h1>
            <p>Explore as seleções públicas da comunidade ou organize suas próprias listas de ensaios e apresentações.</p>
        </div>
    """
    
    # Render user playlists if logged in
    if is_logged:
        html += """
        <div class="sectionTitle">
            <span>📁 Minhas Listas</span>
            <a href="/painel" style="font-size:14px; color:#ff7a00; text-decoration:none; font-weight:bold; background:#ffebe0; padding:6px 12px; border-radius:8px;">+ Nova Playlist</a>
        </div>
        <div class="playlistsGrid" style="margin-bottom: 50px;">
        """
        if my_playlists:
            for pid, nome, publica, likes, total_musicas in my_playlists:
                badge_class = "pub" if publica else "priv"
                badge_label = "Pública" if publica else "Privada"
                html += f"""
                <div class="playlistCard">
                    <span class="badge {badge_class}">{badge_label}</span>
                    <a href="/playlists/{pid}" style="text-decoration:none; color:inherit; flex:1;">
                        <h3 class="playlistName" style="padding-right: 60px;">{nome}</h3>
                        <div class="playlistMeta">
                            <span>📁 Reperório</span>
                            <span>•</span>
                            <span>{total_musicas} músicas</span>
                        </div>
                    </a>
                    <div class="playlistFooter">
                        <span style="font-size:13px; color:#ef4444; font-weight:bold;">❤️ {likes} curtidas</span>
                        <a href="/playlists/{pid}" style="font-size:13px; font-weight:700; color:#ff7a00; text-decoration:none;">Abrir Playlist →</a>
                    </div>
                </div>
                """
        else:
            html += """
            <div style="grid-column: 1/-1; text-align: center; padding: 40px; color: #9ca3af; background:rgba(255,255,255,0.4); border-radius:14px;">
                <p style="font-size:15px; font-weight:bold; margin:0;">Você ainda não criou nenhuma playlist.</p>
                <p style="font-size:13px; margin-top:5px;">Acesse seu Painel para criar sua primeira lista!</p>
            </div>
            """
        html += "</div>"
        
        # Render liked songs
        html += """
        <div class="sectionTitle">
            <span>❤️ Minhas Músicas Curtidas</span>
        </div>
        <div class="playlistsGrid" style="margin-bottom: 50px; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));">
        """
        if liked_songs:
            for mid, title, slug, artist_name, artist_slug, tom, suid in liked_songs:
                html += f"""
                <div class="playlistCard" style="min-height: 100px; padding: 16px;">
                    <a href="/artista/{artist_slug}/{suid}" style="text-decoration:none; color:inherit; display:block;">
                        <h4 style="font-size:16px; font-weight:800; margin:0 0 4px 0;">{title}</h4>
                        <div style="font-size:12px; color:#6b7280;">👤 {artist_name}</div>
                    </a>
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-top:10px; font-size:11px; font-weight:bold;">
                        <span style="color:#ff7a00; background:#ffebe0; padding:2px 6px; border-radius:4px;">Tom: {tom or "N/D"}</span>
                        <a href="/favoritar/{mid}" style="color:#ef4444; text-decoration:none;">Descurtir</a>
                    </div>
                </div>
                """
        else:
            html += """
            <div style="grid-column: 1/-1; text-align: center; padding: 30px; color: #9ca3af; background:rgba(255,255,255,0.4); border-radius:14px;">
                <p style="font-size:14px; font-weight:bold; margin:0;">Você ainda não curtiu nenhuma música.</p>
                <p style="font-size:12px; margin-top:3px;">Clique no coração das cifras para que elas apareçam aqui!</p>
            </div>
            """
        html += "</div>"
        
    # Render community playlists
    html += """
        <div class="sectionTitle">
            <span>💖 Playlists da Comunidade</span>
        </div>
        <div class="playlistsGrid">
    """
    
    if public_playlists:
        for pid, nome, likes, total_musicas in public_playlists:
            html += f"""
            <div class="playlistCard">
                <a href="/playlists/{pid}" style="text-decoration:none; color:inherit; flex:1;">
                    <h3 class="playlistName">{nome}</h3>
                    <div class="playlistMeta">
                        <span>📁 Reperório</span>
                        <span>•</span>
                        <span>{total_musicas} músicas</span>
                    </div>
                </a>
                <div class="playlistFooter">
                    <button class="likeBtn" onclick="likePlaylist(event, {pid}, this)">
                        ❤️ <span class="likeCount">{likes}</span>
                    </button>
                    <a href="/playlists/{pid}" style="font-size:13px; font-weight:700; color:#ff7a00; text-decoration:none;">Ver Playlist →</a>
                </div>
            </div>
            """
    else:
        html += """
        <div style="grid-column: 1/-1; text-align: center; padding: 60px; color: #9ca3af; background:rgba(255,255,255,0.4); border-radius:14px;">
            <p style="font-size:16px; font-weight:bold; margin:0;">Nenhuma playlist pública cadastrada ainda.</p>
            <p style="font-size:14px; margin-top:5px;">Crie uma playlist e marque como Pública no painel para que ela apareça aqui!</p>
        </div>
        """
        
    html += """
        </div>
    </div>
    
    <script>
        function likePlaylist(event, pid, btn) {
            event.preventDefault();
            event.stopPropagation();
            
            fetch('/playlists/like/' + pid, { method: 'POST' })
            .then(res => res.json())
            .then(data => {
                if (data && typeof data.likes === 'number') {
                    const countSpan = btn.querySelector('.likeCount');
                    if (countSpan) countSpan.innerText = data.likes;
                    
                    btn.style.transform = "scale(1.3)";
                    setTimeout(() => { btn.style.transform = "scale(1)"; }, 150);
                }
            })
            .catch(err => console.error(err));
        }
    </script>
    """
    return html


@main_bp.route("/playlists/like/<int:pid>", methods=["POST"])
def like_playlist_route(pid):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("UPDATE playlists SET likes = likes + 1 WHERE id = ?", (pid,))
    conn.commit()
    c.execute("SELECT likes FROM playlists WHERE id = ?", (pid,))
    new_likes = c.fetchone()[0]
    conn.close()
    return jsonify({"likes": new_likes})

@main_bp.route("/playlists/<int:pid>")
def playlist_details_route(pid):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    
    # Get playlist meta
    c.execute("SELECT nome, publica, likes FROM playlists WHERE id = ?", (pid,))
    row = c.fetchone()
    if not row:
        conn.close()
        return redirect(url_for("main.playlists_gallery"))
        
    nome, publica, likes = row
    
    # Get tracks
    c.execute("""
        SELECT m.id, m.titulo, m.slug, a.nome, a.slug, m.tom, m.uid
        FROM playlist_musicas pm
        JOIN musicas m ON pm.musica_id = m.id
        JOIN artistas a ON m.artista_id = a.id
        WHERE pm.playlist_id = ?
        ORDER BY pm.id
    """, (pid,))
    tracks = c.fetchall()
    conn.close()
    
    html = header(f"Playlist - {nome}")
    
    html += f"""
    <style>
        .playlistDetailsWrapper {{
            max-width: 800px;
            margin: 40px auto;
            padding: 0 20px;
            font-family: 'Inter', sans-serif;
        }}
        .detailsHeader {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid #e5e7eb;
            padding-bottom: 24px;
            margin-bottom: 30px;
        }}
        .detailsHeader h1 {{
            font-size: 32px;
            font-weight: 800;
            color: #111827;
            margin: 0 0 6px 0;
        }}
        .badge {{
            display: inline-block;
            padding: 4px 10px;
            border-radius: 8px;
            font-size: 11px;
            font-weight: bold;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}
        .pubBadge {{ background: #ecfdf5; color: #10b981; }}
        .privBadge {{ background: #f3f4f6; color: #6b7280; }}
        .trackItem {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 16px 20px;
            background: rgba(255,255,255,0.7);
            backdrop-filter: blur(16px);
            border-radius: 14px;
            border: 1px solid rgba(255,255,255,0.4);
            margin-bottom: 12px;
            box-shadow: 0 4px 10px rgba(0,0,0,0.01);
            transition: all 0.2s ease;
        }}
        .trackItem:hover {{
            transform: translateX(6px);
            border-color: #ff7a00;
            box-shadow: 0 6px 15px rgba(255,122,0,0.05);
        }}
        .trackInfo a {{
            font-size: 18px;
            font-weight: 800;
            color: #111827;
            text-decoration: none;
        }}
        .trackInfo span {{
            font-size: 13px;
            color: #6b7280;
            margin-left: 10px;
        }}
        .trackNum {{
            font-weight: 800;
            color: #d1d5db;
            font-size: 20px;
            width: 35px;
        }}
    </style>
    
    <div class="playlistDetailsWrapper">
        <div class="detailsHeader">
            <div>
                <span class="badge {'pubBadge' if publica else 'privBadge'}">{'Pública' if publica else 'Privada'}</span>
                <h1 style="margin-top:8px;">{nome}</h1>
                <p style="color:#6b7280; font-size:14px; margin:0;">Contém {len(tracks)} cifras cadastradas</p>
            </div>
            <div>
                <button class="likeBtn" style="font-size:18px; background:rgba(239,68,68,0.1); padding:10px 20px; border-radius:12px;" onclick="likePlaylist(event, {pid}, this)">
                    ❤️ <span class="likeCount">{likes}</span>
                </button>
            </div>
        </div>
        
        <div class="tracksList">
    """
    
    if tracks:
        for idx, (tid, title, slug, artist_name, artist_slug, tom, suid) in enumerate(tracks, start=1):
            html += f"""
            <div class="trackItem">
                <div style="display:flex; align-items:center;">
                    <div class="trackNum">{idx:02d}</div>
                    <div class="trackInfo">
                        <a href="/artista/{artist_slug}/{suid}">{title}</a>
                        <span>({artist_name})</span>
                    </div>
                </div>
                <span style="background:#fff; border:1px solid #e5e7eb; padding:4px 10px; border-radius:8px; font-size:12px; font-weight:bold; color:#4b5563;">Tom: {tom or "N/D"}</span>
            </div>
            """
    else:
        html += """
        <div style="text-align: center; padding: 60px; color: #9ca3af;">
            <p style="font-size:16px; font-weight:bold; margin:0;">Esta playlist está vazia.</p>
            <p style="font-size:14px; margin-top:5px;">Navegue pelas cifras do site e utilize o menu lateral para adicionar músicas!</p>
        </div>
        """
        
    html += """
        </div>
    </div>
    
    <script>
        function likePlaylist(event, pid, btn) {
            event.preventDefault();
            
            fetch('/playlists/like/' + pid, { method: 'POST' })
            .then(res => res.json())
            .then(data => {
                if (data && typeof data.likes === 'number') {
                    const countSpan = btn.querySelector('.likeCount');
                    if (countSpan) countSpan.innerText = data.likes;
                }
            })
            .catch(err => console.error(err));
        }
    </script>
    """
    return html

