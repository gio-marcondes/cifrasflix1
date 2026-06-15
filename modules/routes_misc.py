import re
import sqlite3
import threading
import time
import uuid
import mimetypes
import html as html_lib
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from flask import jsonify, redirect, request, send_file


MP3DETECT_JOBS = {}
MP3DETECT_LOCK = threading.Lock()
MP3_CACHE_DIR = Path("static") / "mp3detect_tmp"
MP3_NOTAS = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
MP3_PERFIS = {
    "": [1, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0],
    "m": [1, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0],
}


def _mp3detect_slug_variants(texto):
    base = str(texto or "").strip()
    if not base:
        return []

    candidatos = []
    for item in (
        base,
        base.lower(),
        base.replace("'", ""),
        base.replace("'", " "),
        base.replace("&", " and "),
        slugify(base),
        normalizar_slug(base),
    ):
        valor = str(item or "").strip().lower().strip("-")
        if valor and valor not in candidatos:
            candidatos.append(valor)
    return candidatos


def _mp3detect_sql_in_clause(values):
    itens = [v for v in values if v]
    if not itens:
        return "('')", []
    return "(" + ", ".join(["?"] * len(itens)) + ")", itens


def _mp3detect_format_cifra_html(texto):
    conteudo = str(texto or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    if not conteudo:
        return ""
    return "<pre class=\"mp3CifraBox\">" + html_lib.escape(conteudo) + "</pre>"


def _mp3detect_fetch_cifra_db(artist, title):
    artista = (artist or "").strip()
    titulo = (title or "").strip()
    if not titulo:
        return {"cifra_html": "", "cifra_title": "", "cifra_artist": ""}

    artist_variants = _mp3detect_slug_variants(artista)
    title_variants = _mp3detect_slug_variants(titulo)
    title_like = f"%{titulo}%"

    title_in_sql, title_in_params = _mp3detect_sql_in_clause(title_variants)
    artist_in_sql, artist_in_params = _mp3detect_sql_in_clause(artist_variants)
    title_slug_priority_sql, title_slug_priority_params = _mp3detect_sql_in_clause(title_variants)
    artist_slug_priority_sql, artist_slug_priority_params = _mp3detect_sql_in_clause(artist_variants)

    base_sql = f"""
        SELECT
            COALESCE(m.conteudo, '') AS conteudo,
            COALESCE(m.titulo, '') AS musica_titulo,
            COALESCE(a.nome, '') AS artista_nome
        FROM musicas m
        JOIN artistas a ON a.id = m.artista_id
        WHERE (
            LOWER(COALESCE(m.titulo, '')) = LOWER(?)
            OR LOWER(COALESCE(m.titulo, '')) LIKE LOWER(?)
            OR LOWER(COALESCE(m.slug, '')) IN {title_in_sql}
        )
        {{artist_clause}}
        ORDER BY
            CASE
                WHEN LOWER(COALESCE(m.slug, '')) IN {title_slug_priority_sql} THEN 0
                WHEN LOWER(COALESCE(m.titulo, '')) = LOWER(?) THEN 1
                WHEN LOWER(COALESCE(m.titulo, '')) LIKE LOWER(?) THEN 2
                ELSE 6
            END,
            CASE
                WHEN LOWER(COALESCE(a.slug, '')) IN {artist_slug_priority_sql} THEN 0
                WHEN LOWER(COALESCE(a.nome, '')) = LOWER(?) THEN 1
                WHEN LOWER(COALESCE(a.nome, '')) LIKE LOWER(?) THEN 2
                ELSE 6
            END,
            m.id
        LIMIT 1
    """

    try:
        conn = connect_db()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        row = None
        tentativas_artista = (True, False) if not artist_variants else (True,)
        for com_artista in tentativas_artista:
            if row:
                break

            artist_clause = ""
            params = [titulo, title_like, *title_in_params]
            if com_artista and artist_variants:
                artist_clause = f"""
                AND (
                    LOWER(COALESCE(a.nome, '')) = LOWER(?)
                    OR LOWER(COALESCE(a.slug, '')) IN {artist_in_sql}
                )
                """
                params.extend([artista, *artist_in_params])

            params.extend([
                *title_slug_priority_params,
                titulo,
                title_like,
                *artist_slug_priority_params,
                artista,
                artista,
            ])

            cur.execute(base_sql.format(artist_clause=artist_clause), tuple(params))
            row = cur.fetchone()

        conn.close()
        if not row:
            return {"cifra_html": "", "cifra_title": "", "cifra_artist": ""}

        return {
            "cifra_html": _mp3detect_format_cifra_html(row["conteudo"] or ""),
            "cifra_title": (row["musica_titulo"] or "").strip(),
            "cifra_artist": (row["artista_nome"] or "").strip(),
        }
    except Exception:
        return {"cifra_html": "", "cifra_title": "", "cifra_artist": ""}


def _mp3detect_parse_video_id(url):
    if not url:
        return ""

    texto = str(url).strip()
    if re.fullmatch(r"[A-Za-z0-9_-]{11}", texto):
        return texto

    if not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", texto):
        texto = "https://" + texto

    try:
        p = urlparse(texto)
    except Exception:
        return ""

    host = (p.netloc or "").lower()
    path = (p.path or "").strip("/")

    if host.startswith("youtu.be"):
        vid = path.split("/")[0] if path else ""
        return vid if re.fullmatch(r"[A-Za-z0-9_-]{11}", vid or "") else ""

    if host.endswith("youtube.com") or host.endswith("youtube-nocookie.com"):
        if path == "watch":
            q = parse_qs(p.query or "")
            vid = (q.get("v") or [""])[0]
            return vid if re.fullmatch(r"[A-Za-z0-9_-]{11}", vid or "") else ""

        partes = path.split("/") if path else []
        if len(partes) >= 2 and partes[0] in {"embed", "shorts", "live", "v"}:
            vid = partes[1]
            return vid if re.fullmatch(r"[A-Za-z0-9_-]{11}", vid or "") else ""

    # Fallback final para casos com texto misturado contendo v=
    m = re.search(r"[?&]v=([A-Za-z0-9_-]{11})", texto)
    if m:
        return m.group(1)

    return ""


def _mp3detect_cleanup_cache(max_age_seconds=7200):
    try:
        MP3_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        agora = time.time()
        for f in MP3_CACHE_DIR.iterdir():
            if not f.is_file():
                continue
            if (agora - f.stat().st_mtime) > max_age_seconds:
                try:
                    f.unlink()
                except Exception:
                    pass
    except Exception:
        pass


def _mp3detect_normalize_track_parts(track_title):
    bruto = (track_title or "").strip()
    if not bruto:
        return {"artist": "", "title": ""}

    txt = bruto
    txt = txt.replace("\u2013", "-").replace("\u2014", "-").replace("\u2212", "-")
    txt = re.sub(r"\s+", " ", txt).strip()

    partes = txt.split("-", 1)
    if len(partes) == 2:
        artist = partes[0].strip(" \t\r\n-|")
        title = partes[1].strip(" \t\r\n-|")
    else:
        artist = ""
        title = txt

    # Remove info promocional/complementar comum de titulos YouTube.
    title = re.sub(r"\(.*?\)|\[.*?\]|\{.*?\}", " ", title)
    title = re.sub(
        r"\b(official( music)? video|official audio|lyrics?|video oficial|audio oficial|hd|4k|remaster(?:ed)?)\b",
        " ",
        title,
        flags=re.IGNORECASE,
    )
    title = re.sub(r"\s+", " ", title).strip(" \t\r\n-|")

    return {"artist": artist, "title": title}


def _mp3detect_find_album_cover(track_title, artist_hint="", song_hint=""):
    partes = _mp3detect_normalize_track_parts(track_title)
    artista = (artist_hint or partes.get("artist") or "").strip()
    titulo = (song_hint or partes.get("title") or track_title or "").strip()
    cifra_info = _mp3detect_fetch_cifra_db(artista, titulo)
    if not titulo:
        return {
            "cover_url": "",
            "album_name": "",
            "artist_name": "",
            "album_year": "",
            "album_country": "",
            "album_label": "",
            "song_title": titulo,
            "lyrics_html": "",
            "translation_html": "",
            "cifra_html": cifra_info.get("cifra_html", ""),
        }

    try:
        conn = connect_db()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        titulo_variants = _mp3detect_slug_variants(titulo)
        titulo_like = f"%{titulo}%"
        artista_variants = _mp3detect_slug_variants(artista)
        titulo_in_sql, titulo_in_params = _mp3detect_sql_in_clause(titulo_variants)
        artista_in_sql, artista_in_params = _mp3detect_sql_in_clause(artista_variants)

        base_sql = """
            SELECT
                al.id AS album_id,
                al.nome AS album_nome,
                COALESCE(al.capa, '') AS album_capa,
                COALESCE(al.ano, '') AS album_ano,
                COALESCE(al.pais, '') AS album_pais,
                COALESCE(al.gravadora, '') AS album_gravadora,
                COALESCE(ar.nome, '') AS artist_name,
                COALESCE(c.titulo, '') AS song_title,
                COALESCE(c.letra_original, '') AS letra_original,
                COALESCE(c.letra_traduzida, '') AS letra_traduzida
            FROM cancao c
            JOIN albuns al ON al.id = c.album_id
            JOIN artistas ar ON ar.id = al.artista_id
            WHERE
                (
                    LOWER(COALESCE(c.titulo, '')) = LOWER(?)
                    OR LOWER(COALESCE(c.titulo, '')) LIKE LOWER(?)
                    OR LOWER(COALESCE(c.cancao_slug, '')) IN {titulo_in_sql}
                )
                {artist_clause}
            ORDER BY
                CASE
                    WHEN LOWER(COALESCE(c.cancao_slug, '')) IN {titulo_in_sql} THEN 0
                    WHEN LOWER(COALESCE(c.titulo, '')) = LOWER(?) THEN 1
                    WHEN LOWER(COALESCE(c.titulo, '')) LIKE LOWER(?) THEN 2
                    ELSE 6
                END,
                CASE
                    WHEN LOWER(COALESCE(ar.slug, '')) IN {artista_in_sql} THEN 0
                    WHEN LOWER(COALESCE(ar.nome, '')) = LOWER(?) THEN 1
                    WHEN LOWER(COALESCE(ar.nome, '')) LIKE LOWER(?) THEN 2
                    ELSE 6
                END,
                c.id
            LIMIT 1
        """.format(
            titulo_in_sql=titulo_in_sql,
            artista_in_sql=artista_in_sql,
            artist_clause="{artist_clause}",
        )

        row = None
        tentativas_artista = (True, False) if not artista_variants else (True,)
        for aplicar_artista in tentativas_artista:
            if row is not None:
                break

            artist_clause = ""
            params = [titulo, titulo_like, *titulo_in_params]

            if aplicar_artista and artista_variants:
                artist_clause = f"""
                AND (
                    LOWER(COALESCE(ar.nome, '')) = LOWER(?)
                    OR LOWER(COALESCE(ar.slug, '')) IN {artista_in_sql}
                )
                """
                params.extend([artista, *artista_in_params])

            params.extend([
                *titulo_in_params,
                titulo,
                titulo_like,
                *artista_in_params,
                artista,
                artista,
            ])

            cur.execute(base_sql.format(artist_clause=artist_clause), tuple(params))
            row = cur.fetchone()

        conn.close()

        if not row:
            return {
                "cover_url": "",
                "album_name": "",
                "artist_name": "",
                "album_year": "",
                "album_country": "",
                "album_label": "",
                "song_title": titulo,
                "lyrics_html": "",
                "translation_html": "",
                "cifra_html": cifra_info.get("cifra_html", ""),
            }

        album_id = row["album_id"]
        album_nome = (row["album_nome"] or "").strip()
        artist_name = (row["artist_name"] or "").strip()
        album_year = str(row["album_ano"] or "").strip()[:4]
        album_country = (row["album_pais"] or "").strip()
        album_label = (row["album_gravadora"] or "").strip()
        song_title = (row["song_title"] or titulo or "").strip()
        capa_raw = (row["album_capa"] or "").strip()

        if capa_raw.lower().startswith(("http://", "https://")):
            capa_url = capa_raw
        elif album_id:
            capa_url = f"/capa_album/{int(album_id)}"
        else:
            capa_url = ""

        return {
            "cover_url": capa_url,
            "album_name": album_nome,
            "artist_name": artist_name,
            "album_year": album_year,
            "album_country": album_country,
            "album_label": album_label,
            "song_title": song_title,
            "lyrics_html": _mp3detect_text_to_html(row["letra_original"] or ""),
            "translation_html": _mp3detect_text_to_html(row["letra_traduzida"] or ""),
            "cifra_html": _mp3detect_fetch_cifra_db(artist_name or artista, row["song_title"] or titulo).get("cifra_html", "") or cifra_info.get("cifra_html", ""),
        }
    except Exception:
        return {
            "cover_url": "",
            "album_name": "",
            "artist_name": "",
            "album_year": "",
            "album_country": "",
            "album_label": "",
            "song_title": titulo,
            "lyrics_html": "",
            "translation_html": "",
            "cifra_html": cifra_info.get("cifra_html", ""),
        }


def _mp3detect_text_to_html(texto):
    txt = html_lib.unescape(texto or "")
    txt = re.sub(r"<\s*br\s*/?\s*>", "\n", txt, flags=re.IGNORECASE)
    txt = re.sub(r"<\s*/\s*p\s*>", "\n\n", txt, flags=re.IGNORECASE)
    txt = re.sub(r"<\s*p(?:\s+[^>]*)?>", "", txt, flags=re.IGNORECASE)
    txt = re.sub(r"<[^>]+>", "", txt)
    txt = txt.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not txt:
        return ""
    safe = html_lib.escape(txt)
    blocos = [b.strip() for b in safe.split("\n\n") if b.strip()]
    if not blocos:
        return ""
    return "".join(f"<p>{b.replace(chr(10), '<br>')}</p>" for b in blocos)


def _mp3detect_fetch_lyrics_db(artist, title):
    artista = (artist or "").strip()
    titulo = (title or "").strip()
    if not titulo:
        return {"lyrics_html": "", "translation_html": ""}

    titulo_variants = _mp3detect_slug_variants(titulo)
    titulo_like = f"%{titulo}%"
    artista_variants = _mp3detect_slug_variants(artista)
    titulo_in_sql, titulo_in_params = _mp3detect_sql_in_clause(titulo_variants)
    artista_in_sql, artista_in_params = _mp3detect_sql_in_clause(artista_variants)

    base_sql = """
        SELECT c.letra_original, c.letra_traduzida
        FROM cancao c
        JOIN albuns al ON al.id = c.album_id
        JOIN artistas ar ON ar.id = al.artista_id
        WHERE (
            LOWER(COALESCE(c.titulo, '')) = LOWER(?)
            OR LOWER(COALESCE(c.titulo, '')) LIKE LOWER(?)
            OR LOWER(COALESCE(c.cancao_slug, '')) IN {titulo_in_sql}
        )
        {artist_clause}
        ORDER BY
            CASE
                WHEN LOWER(COALESCE(c.cancao_slug, '')) IN {titulo_in_sql} THEN 0
                WHEN LOWER(COALESCE(c.titulo, '')) = LOWER(?) THEN 1
                WHEN LOWER(COALESCE(c.titulo, '')) LIKE LOWER(?) THEN 2
                ELSE 6
            END,
            c.id
        LIMIT 1
    """.format(titulo_in_sql=titulo_in_sql, artist_clause="{artist_clause}")

    try:
        conn = connect_db()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        row = None
        tentativas_artista = (True, False) if not artista_variants else (True,)
        for com_artista in tentativas_artista:
            if row:
                break

            artist_clause = ""
            params = [titulo, titulo_like, *titulo_in_params]
            if com_artista and artista_variants:
                artist_clause = f"""
                AND (
                    LOWER(COALESCE(ar.nome, '')) = LOWER(?)
                    OR LOWER(COALESCE(ar.slug, '')) IN {artista_in_sql}
                )
                """
                params.extend([artista, *artista_in_params])

            params.extend([titulo, titulo_like])

            cur.execute(base_sql.format(artist_clause=artist_clause), tuple(params))
            row = cur.fetchone()

        conn.close()
        if not row:
            return {"lyrics_html": "", "translation_html": ""}

        letra_original = _mp3detect_text_to_html(row["letra_original"] or "")
        letra_traduzida = _mp3detect_text_to_html(row["letra_traduzida"] or "")
        return {"lyrics_html": letra_original, "translation_html": letra_traduzida}
    except Exception:
        return {"lyrics_html": "", "translation_html": ""}


def _mp3detect_detectar_acorde(chroma_vec):
    import numpy as np

    vec = np.asarray(chroma_vec, dtype=float)
    norma = np.linalg.norm(vec)
    if norma <= 1e-8:
        return "N"
    vec = vec / norma

    melhor_score = -1.0
    melhor = "N"
    for idx, nota in enumerate(MP3_NOTAS):
        for sufixo, perfil in MP3_PERFIS.items():
            p = np.roll(np.asarray(perfil, dtype=float), idx)
            p_norma = np.linalg.norm(p)
            if p_norma <= 1e-8:
                continue
            p = p / p_norma
            score = float(np.dot(vec, p))
            if score > melhor_score:
                melhor_score = score
                melhor = f"{nota}{sufixo}"
    return melhor


def _mp3detect_gerar_timeline(audio_path, max_seconds=420):
    import librosa
    import numpy as np

    y, sr = librosa.load(str(audio_path), mono=True, sr=22050, duration=max_seconds)
    if y is None or len(y) == 0:
        return [], 0.0, 0

    bpm = 0
    try:
        tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
        bpm = int(round(float(tempo))) if tempo else 0
    except Exception:
        bpm = 0

    hop_length = 512
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr, hop_length=hop_length)
    if chroma is None or chroma.size == 0:
        return [], float(librosa.get_duration(y=y, sr=sr)), bpm

    tempos = librosa.frames_to_time(np.arange(chroma.shape[1]), sr=sr, hop_length=hop_length)
    duracao = float(librosa.get_duration(y=y, sr=sr))

    passo = 0.75
    janela = 1.25
    pontos = []
    t = 0.0
    while t < duracao:
        mask = (tempos >= t) & (tempos < (t + janela))
        if np.any(mask):
            perfil = np.mean(chroma[:, mask], axis=1)
            acorde = _mp3detect_detectar_acorde(perfil)
            pontos.append({"time": round(float(t), 2), "chord": acorde})
        t += passo

    if not pontos:
        return [], duracao, bpm

    timeline = []
    atual = {"start": pontos[0]["time"], "end": min(duracao, pontos[0]["time"] + passo), "chord": pontos[0]["chord"]}
    for p in pontos[1:]:
        if p["chord"] == atual["chord"]:
            atual["end"] = min(duracao, p["time"] + passo)
        else:
            timeline.append(atual)
            atual = {"start": p["time"], "end": min(duracao, p["time"] + passo), "chord": p["chord"]}
    timeline.append(atual)

    return timeline, duracao, bpm


def _mp3detect_baixar_audio(url, output_dir, job_id):
    try:
        import yt_dlp
    except Exception as exc:
        raise RuntimeError("Dependencia ausente: instale yt-dlp para analisar links do YouTube.") from exc

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": str(output_dir / f"{job_id}.%(ext)s"),
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        file_path = None
        requested = info.get("requested_downloads") or []
        if requested and requested[0].get("filepath"):
            file_path = requested[0].get("filepath")
        if not file_path:
            file_path = ydl.prepare_filename(info)

    caminho = Path(file_path)
    if not caminho.exists():
        raise RuntimeError("Nao foi possivel baixar o audio do video.")

    return {
        "path": caminho,
        "video_id": (info.get("id") or "").strip(),
        "title": (info.get("title") or "").strip(),
    }


def _mp3detect_worker(job_id, youtube_url):
    with MP3DETECT_LOCK:
        job = MP3DETECT_JOBS.get(job_id)
        if not job:
            return
        job["status"] = "running"
        job["progress"] = 5

    try:
        _mp3detect_cleanup_cache()
        MP3_CACHE_DIR.mkdir(parents=True, exist_ok=True)

        meta = _mp3detect_baixar_audio(youtube_url, MP3_CACHE_DIR, job_id)
        with MP3DETECT_LOCK:
            job = MP3DETECT_JOBS.get(job_id)
            if not job:
                return
            job["progress"] = 40
            if meta.get("title"):
                job["title"] = meta["title"]
            if meta.get("video_id"):
                job["video_id"] = meta["video_id"]
            job["audio_path"] = str(meta["path"])
            job["audio_mime"] = mimetypes.guess_type(str(meta["path"]))[0] or "audio/mpeg"

        partes = _mp3detect_normalize_track_parts(meta.get("title") or "")
        capa_info = _mp3detect_find_album_cover(
            meta.get("title") or "",
            artist_hint=partes.get("artist") or "",
            song_hint=partes.get("title") or "",
        )
        with MP3DETECT_LOCK:
            job = MP3DETECT_JOBS.get(job_id)
            if job:
                job["cover_url"] = capa_info.get("cover_url", "")
                job["cover_album"] = capa_info.get("album_name", "")
                job["cover_artist"] = capa_info.get("artist_name", "") or (partes.get("artist") or "")
                job["cover_year"] = capa_info.get("album_year", "")
                job["cover_country"] = capa_info.get("album_country", "")
                job["cover_label"] = capa_info.get("album_label", "")
                job["song_title"] = capa_info.get("song_title", "")
                job["lyrics_html"] = capa_info.get("lyrics_html", "")
                job["translation_html"] = capa_info.get("translation_html", "")
                job["cifra_html"] = capa_info.get("cifra_html", "")

        timeline, duration, bpm = _mp3detect_gerar_timeline(meta["path"])

        with MP3DETECT_LOCK:
            job = MP3DETECT_JOBS.get(job_id)
            if not job:
                return
            job["status"] = "done"
            job["progress"] = 100
            job["timeline"] = timeline
            job["duration"] = round(float(duration), 2)
            job["bpm"] = int(bpm or 0)
            job["finished_at"] = int(time.time())
    except Exception as exc:
        with MP3DETECT_LOCK:
            job = MP3DETECT_JOBS.get(job_id)
            if not job:
                return
            job["status"] = "error"
            job["error"] = str(exc)
            job["progress"] = 100
            job["finished_at"] = int(time.time())


@app.route("/favoritar/<int:id>")
def favoritar(id):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO favoritos (musica_id) VALUES (?)", (id,))
    conn.commit()
    conn.close()
    return redirect("/favoritos")


@app.route("/favoritos")
def favoritos():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""
    SELECT m.titulo, a.slug, m.uid
    FROM favoritos f
    JOIN musicas m ON f.musica_id=m.id
    JOIN artistas a ON m.artista_id=a.id
    """)
    favs = c.fetchall()
    conn.close()
    html = header("Favoritos") + "<ul>"
    for titulo, slug, uid in favs:
        html += f"<li style='padding:6px 0;'><a href='/artista/{slug}/{uid}' style='color:white;text-decoration:none;'>{titulo}</a></li>"
    html += "</ul></main>"
    return html


@app.route("/stats")
def stats():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT titulo, views FROM musicas ORDER BY views DESC LIMIT 10")
    top = c.fetchall()
    conn.close()
    html = header("Mais Vistas") + "<ul>"
    for titulo, views in top:
        html += f"<li style='padding:6px 0;'>{titulo} 👁 {views}</li>"
    html += "</ul></main>"
    return html


@app.route("/buscar")
def buscar():
    q = request.args.get("q", "").strip().lower()
    page = int(request.args.get("page", 1))
    per_page = 7
    offset = (page - 1) * per_page

    if not q:
        return jsonify({"results": [], "page": 1, "has_next": False})

    q_like = f"%{q}%"
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""
        SELECT m.titulo, m.uid, a.slug, a.nome
        FROM musicas m
        JOIN artistas a ON m.artista_id = a.id
        WHERE LOWER(m.titulo) LIKE ? OR LOWER(a.nome) LIKE ?
        ORDER BY m.titulo ASC
        LIMIT ? OFFSET ?
    """, (q_like, q_like, per_page, offset))
    dados = [
        {"titulo": r[0], "uid": r[1], "artista": r[2], "artista_nome": r[3]}
        for r in c.fetchall()
    ]

    c.execute("""
        SELECT COUNT(*)
        FROM musicas m
        JOIN artistas a ON m.artista_id = a.id
        WHERE LOWER(m.titulo) LIKE ? OR LOWER(a.nome) LIKE ?
    """, (q_like, q_like))
    total = c.fetchone()[0]
    has_next = (offset + per_page) < total

    conn.close()
    return jsonify({"results": dados, "page": page, "has_next": has_next})


@app.route("/importar")
def importar():
    importar_txt()
    return redirect("/")


@app.route("/login")
def login():
    html = header("Favoritos")
    html += """
    <div class="container">
        <h2>Entrar</h2>
        <form id="loginForm">
            <label for="email">E-mail</label>
            <input type="email" id="email" name="email" placeholder="seu@email.com" required>

            <label for="senha">Senha</label>
            <input type="password" id="senha" name="senha" placeholder="******" required>

            <button type="submit">Entrar</button>
        </form>

        <p>Não tem conta? <a href="/cadastro">Cadastre-se</a></p>
    </div>
    """
    return html


@app.route("/cadastro")
def cadastro():
    html = header("Favoritos")
    html += """
    <div class="container">
        <h2>Cadastro</h2>
        <form id="cadastroForm">
            <label for="nome">Nome</label>
            <input type="text" id="nome" name="nome" placeholder="Seu nome" required>

            <label for="email">E-mail</label>
            <input type="email" id="email" name="email" placeholder="seu@email.com" required>

            <label for="senha">Senha</label>
            <input type="password" id="senha" name="senha" placeholder="******" required>

            <button type="submit">Cadastrar</button>
        </form>

        <p>Já tem conta? <a href="/login">Entrar</a></p>
    </div>
    """
    return html


@app.route("/mp3detect")
def mp3detect():
    html = header("MP3 Detect")
    html += """
    <section class="mp3DetectPage">
        <article class="mp3DetectHero">
            <p class="mp3Eyebrow">MP3 Detect</p>
            <h1>Transcricao de acordes por link do YouTube</h1>
            <p>Cole o link do video, rode a analise e acompanhe os acordes sincronizados com o playback.</p>
            <div class="mp3HeroControls">
                <div class="mp3DetectForm">
                    <input id="mp3YoutubeUrl" type="hidden" />
                </div>
                <div class="mp3FinderRow">
                    <input id="mp3SearchArtist" type="text" placeholder="Artista" />
                    <input id="mp3SearchSong" type="text" placeholder="Musica" />
                    <button id="mp3FindYoutubeBtn" type="button">Buscar</button>
                </div>
                <div id="mp3Status" class="mp3Status"></div>
                <div class="mp3ProgressWrap"><div id="mp3Progress" class="mp3Progress"></div></div>
            </div>
        </article>

        <article id="mp3TimelineCard" class="mp3DetectCard mp3Hidden">
            <h3>Timeline de acordes</h3>
            <div id="mp3Timeline" class="mp3Timeline"></div>
        </article>

        <section id="mp3MainGrid" class="mp3DetectGrid mp3Hidden">
            <article class="mp3DetectCard">
                <h3>Player</h3>
                <div id="mp3PlayerWrap" class="mp3PlayerWrap">
                    <div class="mp3NowPlaying">
                        <img id="mp3CoverArt" class="mp3CoverArt" alt="Capa do album" />
                        <div class="mp3NowInfo">
                            <div id="mp3SongTitle" class="mp3SongTitle">Aguardando analise...</div>
                            <div id="mp3SongMeta" class="mp3SongMeta"></div>
                            <div id="mp3SongMetaExtra" class="mp3SongMetaExtra"></div>
                        </div>
                    </div>
                    <audio id="mp3Audio" class="mp3Audio" controls></audio>
                </div>
            </article>

            <article class="mp3DetectCard">
                <h3>Transcricao</h3>
                <div class="mp3MetaGrid">
                    <div class="mp3MetaItem">
                        <span class="mp3MetaLabel">BPM</span>
                        <span id="mp3Bpm" class="mp3MetaValue">--</span>
                    </div>
                    <div class="mp3MetaItem">
                        <span class="mp3MetaLabel">Acordes</span>
                        <div id="mp3ChordTable" class="mp3ChordTable"></div>
                    </div>
                </div>
                <h4 class="mp3Sub">Acorde atual</h4>
                <div id="mp3CurrentChord" class="mp3CurrentChord">--</div>
                <p class="mp3Hint">Os acordes mudam conforme o tempo do player.</p>
                <div class="mp3DiagramWrap">
                    <div id="mp3ChordDiagram" class="mp3ChordDiagram"></div>
                </div>
            </article>
        </section>

        <article id="mp3LyricsCard" class="mp3DetectCard mp3Hidden">
            <div class="mp3LyricsHeader">
                <h3 style="margin:0;">Letra</h3>
                <button id="mp3ToggleTranslation" type="button" class="mp3TranslateBtn">Traducao: OFF</button>
            </div>
            <div class="mp3LyricsGrid" id="mp3LyricsGrid">
                <section>
                    <h4 class="mp3LyricColTitle">Original</h4>
                    <div id="mp3LyricText" class="mp3LyricBox">A letra sera carregada apos a analise.</div>
                </section>
                <section id="mp3TranslationCol" style="display:none;">
                    <h4 class="mp3LyricColTitle">Traducao</h4>
                    <div id="mp3TranslationText" class="mp3LyricBox">Traducao desativada.</div>
                </section>
            </div>
            <section id="mp3CifraSection" class="mp3CifraSection" style="display:none;">
                <h4 class="mp3LyricColTitle">Cifra</h4>
                <div id="mp3CifraText" class="mp3CifraWrap">Cifra nao encontrada.</div>
            </section>
        </article>
    </section>

    <style>
        .mp3DetectPage{max-width:1100px;margin:24px auto;padding:0 16px 28px;display:grid;gap:14px}
        .mp3DetectHero,.mp3DetectCard{background:#fff;border:1px solid #e5e7eb;border-radius:14px;padding:16px;box-shadow:0 8px 18px rgba(15,23,42,.06)}
        .mp3Hidden{display:none}
        .mp3Eyebrow{margin:0 0 4px;font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:#64748b}
        .mp3DetectHero h1{margin:0 0 6px;font-size:31px;line-height:1.1;color:#0f172a}
        .mp3DetectHero p{margin:0;color:#475569}
        .mp3HeroControls{margin-top:14px;display:grid;gap:10px}
        .mp3DetectForm{display:none}
        .mp3FinderRow{margin-top:10px;display:grid;grid-template-columns:1fr 1fr auto;gap:10px}
        .mp3FinderRow input{height:40px;border:1px solid #cbd5e1;border-radius:10px;padding:0 12px;font-size:14px}
        .mp3FinderRow button{height:40px;border:1px solid #cbd5e1;border-radius:10px;padding:0 14px;font-weight:700;cursor:pointer;background:#fff;color:#0f172a}
        .mp3Status{min-height:20px;color:#334155;font-size:14px}
        .mp3ProgressWrap{height:8px;background:#e2e8f0;border-radius:999px;overflow:hidden}
        .mp3Progress{height:100%;width:0%;background:linear-gradient(90deg,#22c55e,#16a34a);transition:width .2s ease}
        .mp3DetectGrid{display:grid;grid-template-columns:1.4fr .8fr;gap:14px}
        .mp3DetectGrid.mp3Hidden{display:none}
        .mp3PlayerWrap{border:1px solid #d1d5db;border-radius:16px;padding:16px;min-height:220px;background:linear-gradient(145deg,#f8fafc 0%,#eef2f7 100%);display:grid;gap:14px}
        .mp3NowPlaying{display:grid;grid-template-columns:220px 1fr;gap:16px;align-items:center}
        .mp3CoverArt{display:block;width:220px;height:220px;object-fit:cover;border-radius:14px;border:1px solid #cbd5e1;background:#e2e8f0;box-shadow:0 18px 35px rgba(15,23,42,.2)}
        .mp3NowInfo{display:grid;gap:8px;align-content:center}
        .mp3SongTitle{font-size:34px;line-height:1.05;font-weight:900;letter-spacing:-.02em;color:#0b1220}
        .mp3SongMeta{font-size:14px;color:#334155;min-height:18px;text-transform:uppercase;letter-spacing:.06em;font-weight:700}
        .mp3SongMetaExtra{font-size:13px;color:#64748b;min-height:18px;line-height:1.45}
        .mp3Audio{display:block;width:100%;margin-top:2px;accent-color:#16a34a}
        .mp3MetaGrid{display:grid;grid-template-columns:.5fr 1.5fr;gap:10px;margin-bottom:10px}
        .mp3MetaItem{background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;padding:8px}
        .mp3MetaLabel{display:block;font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:.06em;margin-bottom:4px}
        .mp3MetaValue{font-size:30px;font-weight:800;color:#0f172a}
        .mp3ChordTable{display:flex;flex-wrap:wrap;gap:6px;align-items:flex-start;min-height:30px}
        .mp3ChordPill{padding:4px 8px;border-radius:999px;background:#e2e8f0;color:#0f172a;font-size:12px;font-weight:700}
        .mp3ChordPill.active{background:#0f172a;color:#fff}
        .mp3Sub{margin:0 0 8px;color:#334155;font-size:13px;text-transform:uppercase;letter-spacing:.04em}
        .mp3CurrentChord{font-size:48px;font-weight:800;line-height:1;color:#0f172a;letter-spacing:.02em}
        .mp3Hint{margin:8px 0 0;color:#64748b;font-size:12px}
        .mp3DiagramWrap{margin-top:10px;padding:10px;border:1px solid #e2e8f0;border-radius:10px;background:#fff}
        .mp3ChordDiagram{min-height:140px;display:grid;place-items:center}
        .mp3ChordDiagram svg{max-width:100%}
        .mp3Timeline{display:flex;flex-wrap:nowrap;gap:8px;overflow-x:auto;overflow-y:hidden;padding:8px 6px 10px;scroll-behavior:smooth;width:100%;max-width:760px;height:108px;border:1px solid #e2e8f0;border-radius:12px;background:#f8fafc}
        .mp3Timeline::-webkit-scrollbar{height:8px}
        .mp3Timeline::-webkit-scrollbar-thumb{background:#cbd5e1;border-radius:999px}
        .mp3ChordChip{flex:0 0 auto;display:grid;place-items:center;width:76px;height:96px;border:1px solid #cbd5e1;background:#fff;border-radius:12px;transition:all .18s ease}
        .mp3ChordChip.active{background:#fef9c3;color:#0f172a;border-color:#facc15;transform:translateY(-1px);box-shadow:0 8px 14px rgba(245,158,11,.22)}
        .mp3ChordMini{width:66px;height:88px;display:grid;grid-template-rows:74px 1fr;place-items:center}
        .mp3ChordMini svg{width:62px;height:72px}
        .mp3ChordMiniName{font-size:11px;line-height:1;font-weight:800;color:#334155;margin-top:2px}
        .mp3ChordChip.active .mp3ChordMiniName{color:#0f172a}
        .mp3MiniFallback{font-size:11px;font-weight:800;color:#334155}
        .mp3ChordChip.active .mp3MiniFallback{color:#0f172a}
        .mp3LyricsHeader{display:flex;align-items:center;justify-content:space-between;gap:12px}
        .mp3TranslateBtn{height:34px;padding:0 12px;border:1px solid #cbd5e1;border-radius:999px;background:#fff;font-weight:700;cursor:pointer;color:#0f172a}
        .mp3TranslateBtn.on{background:#dcfce7;border-color:#86efac;color:#166534}
        .mp3LyricsGrid{display:grid;grid-template-columns:1fr;gap:12px;margin-top:12px}
        .mp3LyricsGrid.split{grid-template-columns:1fr 1fr}
        .mp3LyricColTitle{margin:0 0 8px;color:#334155;font-size:13px;text-transform:uppercase;letter-spacing:.05em}
        .mp3LyricBox{border:1px solid #e2e8f0;background:#f8fafc;border-radius:12px;padding:12px;min-height:220px;max-height:360px;overflow:auto;color:#0f172a;line-height:1.5}
        .mp3LyricBox p{margin:0 0 10px}
        .mp3CifraSection{margin-top:14px}
        .mp3CifraWrap{border:1px solid #e2e8f0;background:#f8fafc;border-radius:12px;padding:12px;color:#0f172a}
        .mp3CifraBox{margin:0;font:600 13px/1.6 'Consolas','Courier New',monospace;white-space:pre-wrap;word-break:break-word}
        @media (max-width: 900px){.mp3DetectGrid{grid-template-columns:1fr}.mp3MetaGrid{grid-template-columns:1fr}.mp3NowPlaying{grid-template-columns:1fr}.mp3CoverArt{width:180px;height:180px;justify-self:center}.mp3NowInfo{text-align:center}.mp3SongTitle{font-size:28px}.mp3FinderRow{grid-template-columns:1fr}}
    </style>

    <script>
        let mp3JobId = null;
        let mp3Poll = null;
        let mp3Timeline = [];
        let mp3Tick = null;
        let mp3ActiveSource = 'audio';
        let mp3CurrentTimelineIndex = -1;
        let mp3LyricsHtml = '';
        let mp3TranslationHtml = '';
        let mp3CifraHtml = '';
        let mp3TranslationOn = false;
        let mp3LyricArtist = '';
        let mp3LyricTitle = '';
        let mp3SyncingLyricsScroll = false;
        const MP3_COVER_PLACEHOLDER = 'data:image/svg+xml;utf8,' + encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 300"><defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0%" stop-color="#e2e8f0"/><stop offset="100%" stop-color="#cbd5e1"/></linearGradient></defs><rect width="300" height="300" fill="url(#g)"/><circle cx="105" cy="105" r="28" fill="#94a3b8"/><rect x="58" y="168" width="184" height="18" rx="9" fill="#94a3b8"/><rect x="72" y="196" width="156" height="12" rx="6" fill="#a8b4c7"/></svg>');

        const MP3_NOTA_TO_SEMITONE = {
            'C':0,'C#':1,'Db':1,'D':2,'D#':3,'Eb':3,'E':4,'F':5,'F#':6,'Gb':6,
            'G':7,'G#':8,'Ab':8,'A':9,'A#':10,'Bb':10,'B':11
        };

        const MP3_CHORD_SHAPES = {
            'C': { baseFret: 1, frets: [-1, 3, 2, 0, 1, 0], fingers: [0, 3, 2, 0, 1, 0] },
            'Cm': { baseFret: 3, frets: [-1, 3, 5, 5, 4, 3], fingers: [0, 1, 3, 4, 2, 1] },
            'D': { baseFret: 1, frets: [-1, -1, 0, 2, 3, 2], fingers: [0, 0, 0, 1, 3, 2] },
            'Dm': { baseFret: 1, frets: [-1, -1, 0, 2, 3, 1], fingers: [0, 0, 0, 2, 3, 1] },
            'E': { baseFret: 1, frets: [0, 2, 2, 1, 0, 0], fingers: [0, 2, 3, 1, 0, 0] },
            'Em': { baseFret: 1, frets: [0, 2, 2, 0, 0, 0], fingers: [0, 2, 3, 0, 0, 0] },
            'F': { baseFret: 1, frets: [1, 3, 3, 2, 1, 1], fingers: [1, 3, 4, 2, 1, 1] },
            'Fm': { baseFret: 1, frets: [1, 3, 3, 1, 1, 1], fingers: [1, 3, 4, 1, 1, 1] },
            'G': { baseFret: 1, frets: [3, 2, 0, 0, 0, 3], fingers: [3, 2, 0, 0, 0, 4] },
            'Gm': { baseFret: 3, frets: [3, 5, 5, 3, 3, 3], fingers: [1, 3, 4, 1, 1, 1] },
            'A': { baseFret: 1, frets: [-1, 0, 2, 2, 2, 0], fingers: [0, 0, 1, 2, 3, 0] },
            'Am': { baseFret: 1, frets: [-1, 0, 2, 2, 1, 0], fingers: [0, 0, 2, 3, 1, 0] },
            'B': { baseFret: 2, frets: [-1, 2, 4, 4, 4, 2], fingers: [0, 1, 2, 3, 4, 1] },
            'Bm': { baseFret: 2, frets: [-1, 2, 4, 4, 3, 2], fingers: [0, 1, 3, 4, 2, 1] },
            'C#': { baseFret: 4, frets: [-1, 4, 6, 6, 6, 4], fingers: [0, 1, 2, 3, 4, 1] },
            'C#m': { baseFret: 4, frets: [-1, 4, 6, 6, 5, 4], fingers: [0, 1, 3, 4, 2, 1] },
            'D#': { baseFret: 6, frets: [-1, 6, 8, 8, 8, 6], fingers: [0, 1, 2, 3, 4, 1] },
            'D#m': { baseFret: 6, frets: [-1, 6, 8, 8, 7, 6], fingers: [0, 1, 3, 4, 2, 1] },
            'F#': { baseFret: 2, frets: [2, 4, 4, 3, 2, 2], fingers: [1, 3, 4, 2, 1, 1] },
            'F#m': { baseFret: 2, frets: [2, 4, 4, 2, 2, 2], fingers: [1, 3, 4, 1, 1, 1] },
            'G#': { baseFret: 4, frets: [4, 6, 6, 5, 4, 4], fingers: [1, 3, 4, 2, 1, 1] },
            'G#m': { baseFret: 4, frets: [4, 6, 6, 4, 4, 4], fingers: [1, 3, 4, 1, 1, 1] },
            'A#': { baseFret: 1, frets: [-1, 1, 3, 3, 3, 1], fingers: [0, 1, 2, 3, 4, 1] },
            'A#m': { baseFret: 1, frets: [-1, 1, 3, 3, 2, 1], fingers: [0, 1, 3, 4, 2, 1] },
            'Db': { alias: 'C#' },
            'Eb': { alias: 'D#' },
            'Gb': { alias: 'F#' },
            'Ab': { alias: 'G#' },
            'Bb': { alias: 'A#' },
            'Dbm': { alias: 'C#m' },
            'Ebm': { alias: 'D#m' },
            'Gbm': { alias: 'F#m' },
            'Abm': { alias: 'G#m' },
            'Bbm': { alias: 'A#m' }
        };

        function setStatus(text) {
            const el = document.getElementById('mp3Status');
            if (el) el.textContent = text;
        }

        function setResultsVisible(show) {
            const ids = ['mp3TimelineCard', 'mp3MainGrid', 'mp3LyricsCard'];
            ids.forEach((id) => {
                const el = document.getElementById(id);
                if (!el) return;
                el.classList.toggle('mp3Hidden', !show);
            });
        }

        function setProgress(value) {
            const el = document.getElementById('mp3Progress');
            if (el) el.style.width = Math.max(0, Math.min(100, Number(value) || 0)) + '%';
        }

        function setTranslationToggle(on) {
            mp3TranslationOn = !!on;
            const btn = document.getElementById('mp3ToggleTranslation');
            const col = document.getElementById('mp3TranslationCol');
            const grid = document.getElementById('mp3LyricsGrid');
            const lyricEl = document.getElementById('mp3LyricText');
            const trEl = document.getElementById('mp3TranslationText');
            if (btn) {
                btn.textContent = 'Traducao: ' + (mp3TranslationOn ? 'ON' : 'OFF');
                btn.classList.toggle('on', mp3TranslationOn);
            }
            if (col) col.style.display = mp3TranslationOn ? '' : 'none';
            if (grid) grid.classList.toggle('split', mp3TranslationOn);

            if (lyricEl && trEl) {
                if (mp3TranslationOn) {
                    trEl.style.overflow = 'hidden';
                    trEl.style.pointerEvents = 'none';
                    trEl.scrollTop = lyricEl.scrollTop;
                } else {
                    trEl.style.overflow = 'auto';
                    trEl.style.pointerEvents = 'auto';
                    trEl.scrollTop = 0;
                }
            }
        }

        function bindLyricsScrollSync() {
            const lyricEl = document.getElementById('mp3LyricText');
            const trEl = document.getElementById('mp3TranslationText');
            if (!lyricEl || !trEl) return;

            lyricEl.addEventListener('scroll', () => {
                if (!mp3TranslationOn || mp3SyncingLyricsScroll) return;
                mp3SyncingLyricsScroll = true;
                trEl.scrollTop = lyricEl.scrollTop;
                mp3SyncingLyricsScroll = false;
            });
        }

        async function loadLyrics(artist, title, lyricsHtml) {
            mp3LyricArtist = (artist || '').trim();
            mp3LyricTitle = (title || '').trim();
            mp3LyricsHtml = (lyricsHtml || '').trim();

            const lyricEl = document.getElementById('mp3LyricText');
            const trEl = document.getElementById('mp3TranslationText');
            if (lyricEl) lyricEl.innerHTML = 'Carregando letra...';
            if (trEl) trEl.innerHTML = 'Traducao desativada.';

            if (!mp3LyricsHtml) {
                try {
                    const qs = new URLSearchParams({ artist: mp3LyricArtist, title: mp3LyricTitle });
                    const r = await fetch('/mp3detect/lyrics?' + qs.toString());
                    const data = await r.json();
                    mp3LyricsHtml = (data.lyrics_html || '').trim();
                    if (!mp3TranslationHtml) {
                        mp3TranslationHtml = (data.translation_html || '').trim();
                    }
                } catch (err) {
                    mp3LyricsHtml = '';
                }
                if (!mp3LyricsHtml) {
                    if (lyricEl) lyricEl.innerHTML = 'Letra nao encontrada.';
                    return;
                }
            }

            if (lyricEl) lyricEl.innerHTML = mp3LyricsHtml;
        }

        function loadCifra(cifraHtml) {
            mp3CifraHtml = (cifraHtml || '').trim();
            const section = document.getElementById('mp3CifraSection');
            const root = document.getElementById('mp3CifraText');
            if (!section || !root) return;
            if (!mp3CifraHtml) {
                section.style.display = 'none';
                root.innerHTML = 'Cifra nao encontrada.';
                return;
            }
            section.style.display = '';
            root.innerHTML = mp3CifraHtml;
        }

        async function loadTranslationIfNeeded() {
            if (!mp3TranslationOn) return;
            const trEl = document.getElementById('mp3TranslationText');
            if (mp3TranslationHtml) {
                if (trEl) trEl.innerHTML = mp3TranslationHtml;
                return;
            }
            if (trEl) trEl.innerHTML = 'Traducao nao encontrada.';
        }

        function parseTrackTitle(rawTitle) {
            const txt = String(rawTitle || '').trim();
            if (!txt) return { artist: '', title: '' };
            const cleaned = txt.replace(/[\u2013\u2014\u2212]/g, '-').trim();
            const parts = cleaned.split('-', 2);
            let artist = '';
            let title = cleaned;
            if (parts.length === 2) {
                artist = parts[0].trim();
                title = parts[1].trim();
            }
            title = title
                .replace(/\(.*?\)|\[.*?\]|\{.*?\}/g, ' ')
                .replace(/\b(official( music)? video|official audio|lyrics?|video oficial|audio oficial|hd|4k|remaster(?:ed)?)\b/ig, ' ')
                .replace(/\s+/g, ' ')
                .trim();
            return { artist: artist, title: title || cleaned };
        }

        function setCoverArt(coverUrl, albumName, artistName, albumYear, albumCountry, albumLabel, rawTitle, matchedSongTitle) {
            const img = document.getElementById('mp3CoverArt');
            const titleEl = document.getElementById('mp3SongTitle');
            const metaEl = document.getElementById('mp3SongMeta');
            const metaExtraEl = document.getElementById('mp3SongMetaExtra');
            const parsed = parseTrackTitle(rawTitle || '');
            if (!img) return;
            img.onerror = () => {
                img.onerror = null;
                img.src = MP3_COVER_PLACEHOLDER;
            };
            if (!coverUrl) {
                img.src = MP3_COVER_PLACEHOLDER;
                img.style.background = '#e2e8f0';
            } else {
                img.src = coverUrl;
            }
            const altParts = [];
            if (albumName) altParts.push(albumName);
            if (artistName) altParts.push(artistName);
            img.alt = altParts.length ? altParts.join(' - ') : 'Capa do album';

            if (titleEl) {
                titleEl.textContent = matchedSongTitle || parsed.title || rawTitle || albumName || 'Faixa';
            }
            if (metaEl) {
                const bits = [];
                const artistOut = artistName || parsed.artist;
                if (artistOut) bits.push(artistOut);
                if (albumName) bits.push(albumName);
                if (albumYear) bits.push(albumYear);
                metaEl.textContent = bits.join(' • ');
            }
            if (metaExtraEl) {
                const bits = [];
                if (albumCountry) bits.push(albumCountry);
                if (albumLabel) bits.push(albumLabel);
                metaExtraEl.textContent = bits.join(' • ');
            }
        }

        function attachAudioTrack(audioUrl) {
            const audio = document.getElementById('mp3Audio');
            if (!audio) return;
            if (!audioUrl) {
                audio.style.display = 'none';
                audio.removeAttribute('src');
                return;
            }
            audio.style.display = 'block';
            if ((audio.getAttribute('src') || '') !== audioUrl) {
                audio.src = audioUrl;
                audio.load();
            }
        }

        function renderTimeline(items) {
            const root = document.getElementById('mp3Timeline');
            if (!root) return;
            if (!Array.isArray(items) || !items.length) {
                root.innerHTML = '<span class="mp3ChordChip">Sem acordes detectados.</span>';
                renderChordTable([]);
                return;
            }
            root.innerHTML = items.map((seg, i) => {
                const chord = String(seg.chord || 'N');
                return '<span class="mp3ChordChip" title="' + chord + '" data-i="' + i + '">' + renderMiniChordSVG(chord) + '</span>';
            }).join('');

            const uniq = [];
            const seen = new Set();
            items.forEach((seg) => {
                const c = String(seg.chord || 'N');
                if (c === 'N' || seen.has(c)) return;
                seen.add(c);
                uniq.push(c);
            });
            renderChordTable(uniq);
        }

        function renderChordTable(chords) {
            const root = document.getElementById('mp3ChordTable');
            if (!root) return;
            if (!Array.isArray(chords) || !chords.length) {
                root.innerHTML = '<span class="mp3ChordPill">--</span>';
                return;
            }
            root.innerHTML = chords.map((c) => '<span class="mp3ChordPill" data-chord="' + c + '">' + c + '</span>').join('');
        }

        function resolveChordShape(chord) {
            const key = String(chord || '').trim();
            if (!key) return null;
            const item = MP3_CHORD_SHAPES[key];
            if (!item) return null;
            if (item.alias) return MP3_CHORD_SHAPES[item.alias] || null;
            return item;
        }

        function chordToShape(chord) {
            if (!chord || chord === 'N') return null;
            const m = String(chord).match(/^([A-G](?:#|b)?)(m?)$/i);
            if (!m) return null;

            const root = m[1].charAt(0).toUpperCase() + m[1].slice(1);
            const isMinor = m[2] === 'm';
            const normalized = root + (isMinor ? 'm' : '');
            const fromDict = resolveChordShape(normalized);
            if (fromDict) {
                return {
                    chord: chord,
                    baseFret: Number(fromDict.baseFret || 1),
                    frets: Array.isArray(fromDict.frets) ? fromDict.frets.slice(0, 6) : [],
                    fingers: Array.isArray(fromDict.fingers) ? fromDict.fingers.slice(0, 6) : [],
                };
            }

            const semitone = MP3_NOTA_TO_SEMITONE[root];
            if (semitone === undefined) return null;
            const eRoot = isMinor ? 4 : 4;
            let base = semitone - eRoot;
            while (base < 1) base += 12;
            const frets = isMinor
                ? [base, base + 2, base + 2, base, base, base]
                : [base, base + 2, base + 2, base + 1, base, base];
            return { chord: chord, baseFret: base, frets: frets, fingers: [1, 3, 4, 2, 1, 1] };
        }

        function renderMiniChordSVG(chord) {
            const chordName = String(chord || '--');
            const shape = chordToShape(chord);
            if (!shape) {
                return '<div class="mp3ChordMini"><span class="mp3MiniFallback">' + chordName + '</span></div>';
            }

            const frets = shape.frets || [];
            const baseFret = Number(shape.baseFret || 1);
            const top = 14;
            const left = 10;
            const sx = 8;
            const sy = 12;
            const totalFrets = 4;
            const width = sx * 5;
            const height = sy * totalFrets;

            let svg = '';
            svg += '<div class="mp3ChordMini">';
            svg += '<svg viewBox="0 0 62 76" aria-label="Mini diagrama">';
            if (baseFret > 1) {
                svg += '<text x="46" y="11" font-size="7" fill="#64748b">' + baseFret + 'fr</text>';
            }
            for (let i = 0; i < 6; i++) {
                const x = left + (sx * i);
                svg += '<line x1="' + x + '" y1="' + top + '" x2="' + x + '" y2="' + (top + height) + '" stroke="#334155" stroke-width="1" />';
            }
            for (let f = 0; f <= totalFrets; f++) {
                const y = top + (sy * f);
                svg += '<line x1="' + left + '" y1="' + y + '" x2="' + (left + width) + '" y2="' + y + '" stroke="#334155" stroke-width="' + (baseFret === 1 && f === 0 ? 2 : 1) + '" />';
            }

            frets.forEach((p, idx) => {
                const x = left + (sx * idx);
                if (p < 0) {
                    svg += '<text x="' + (x - 2.5) + '" y="10" font-size="8" fill="#94a3b8">x</text>';
                    return;
                }
                if (p === 0) {
                    svg += '<circle cx="' + x + '" cy="8" r="2.6" fill="none" stroke="#334155" stroke-width="1" />';
                    return;
                }
                const rel = p - baseFret;
                if (rel < 0 || rel >= totalFrets) return;
                const y = top + (sy * rel) + (sy / 2);
                svg += '<circle cx="' + x + '" cy="' + y + '" r="3.2" fill="#1e293b" />';
            });

            svg += '</svg>';
            svg += '<span class="mp3ChordMiniName">' + chordName + '</span>';
            svg += '</div>';
            return svg;
        }

        function renderChordDiagram(chord) {
            const root = document.getElementById('mp3ChordDiagram');
            if (!root) return;
            const shape = chordToShape(chord);
            if (!shape) {
                root.innerHTML = '<div style="color:#64748b;font-size:13px;">Diagrama indisponivel para este acorde.</div>';
                return;
            }

            const frets = shape.frets || [];
            const fingers = shape.fingers || [];
            const baseFret = Number(shape.baseFret || 1);
            const played = frets.filter((p) => p > 0);
            const maxFret = played.length ? Math.max.apply(null, played) : baseFret + 3;
            const totalFrets = Math.max(4, maxFret - baseFret + 1);

            const sx = 24;
            const sy = 24;
            const top = 16;
            const left = 26;
            const width = sx * 5;
            const height = sy * totalFrets;

            let svg = '';
            svg += '<svg viewBox="0 0 190 170" width="190" height="170" aria-label="Diagrama de acorde">';
            svg += '<text x="6" y="14" font-size="12" fill="#334155">' + shape.chord + '</text>';
            if (baseFret > 1) {
                svg += '<text x="145" y="14" font-size="11" fill="#334155">' + baseFret + 'fr</text>';
            }

            for (let i = 0; i < 6; i++) {
                const x = left + (sx * i);
                svg += '<line x1="' + x + '" y1="' + top + '" x2="' + x + '" y2="' + (top + height) + '" stroke="#475569" stroke-width="1.4" />';
            }
            for (let f = 0; f <= totalFrets; f++) {
                const y = top + (sy * f);
                svg += '<line x1="' + left + '" y1="' + y + '" x2="' + (left + width) + '" y2="' + y + '" stroke="#475569" stroke-width="' + (baseFret === 1 && f === 0 ? 3 : 1.2) + '" />';
            }

            frets.forEach((p, idx) => {
                const x = left + (sx * idx);
                if (p < 0) {
                    svg += '<text x="' + (x - 4) + '" y="12" font-size="11" fill="#64748b">x</text>';
                    return;
                }
                if (p === 0) {
                    svg += '<circle cx="' + x + '" cy="10" r="4" fill="none" stroke="#334155" stroke-width="1.3" />';
                    return;
                }
                const rel = p - baseFret;
                const y = top + (sy * rel) + (sy / 2);
                svg += '<circle cx="' + x + '" cy="' + y + '" r="6" fill="#0f172a" />';
                const finger = Number(fingers[idx] || 0);
                if (finger > 0) {
                    svg += '<text x="' + (x - 2.5) + '" y="' + (y + 3) + '" font-size="8" fill="#fff">' + finger + '</text>';
                }
            });

            svg += '</svg>';
            root.innerHTML = svg;
        }

        function highlightChordTable(chord) {
            const pills = document.querySelectorAll('.mp3ChordPill[data-chord]');
            pills.forEach((p) => p.classList.remove('active'));
            const active = document.querySelector('.mp3ChordPill[data-chord="' + chord + '"]');
            if (active) active.classList.add('active');
        }

        function updateCurrentChordByTime(currentTime) {
            if (!Array.isArray(mp3Timeline) || !mp3Timeline.length) return;
            let idx = -1;
            for (let i = 0; i < mp3Timeline.length; i++) {
                const seg = mp3Timeline[i];
                if ((currentTime >= Number(seg.start || 0)) && (currentTime < Number(seg.end || 0))) {
                    idx = i;
                    break;
                }
            }
            if (idx < 0) return;
            if (idx === mp3CurrentTimelineIndex) return;
            mp3CurrentTimelineIndex = idx;

            const chord = mp3Timeline[idx].chord || '--';
            const current = document.getElementById('mp3CurrentChord');
            if (current) current.textContent = chord;
            renderChordDiagram(chord);
            highlightChordTable(chord);

            const chips = document.querySelectorAll('.mp3ChordChip[data-i]');
            chips.forEach((chip) => chip.classList.remove('active'));
            const active = document.querySelector('.mp3ChordChip[data-i="' + idx + '"]');
            if (active) {
                active.classList.add('active');
                const timeline = document.getElementById('mp3Timeline');
                if (timeline) {
                    const left = active.offsetLeft - ((timeline.clientWidth / 2) - (active.clientWidth / 2));
                    const maxLeft = Math.max(0, timeline.scrollWidth - timeline.clientWidth);
                    const clamped = Math.max(0, Math.min(left, maxLeft));
                    timeline.scrollTo({ left: clamped, behavior: 'smooth' });
                }
            }
        }

        function seekToTimelineIndex(idx) {
            const i = Number(idx);
            if (!Number.isFinite(i) || i < 0 || i >= mp3Timeline.length) return;
            const seg = mp3Timeline[i] || {};
            const t = Number(seg.start || 0);
            if (!Number.isFinite(t)) return;

            const audio = document.getElementById('mp3Audio');
            if (!audio) return;
            audio.currentTime = Math.max(0, t);
            updateCurrentChordByTime(t);
        }

        function bindTimelineSeek() {
            const timeline = document.getElementById('mp3Timeline');
            if (!timeline) return;
            timeline.addEventListener('click', (ev) => {
                const chip = ev.target && ev.target.closest ? ev.target.closest('.mp3ChordChip[data-i]') : null;
                if (!chip) return;
                seekToTimelineIndex(chip.getAttribute('data-i'));
            });
        }

        function mountAudioFallback(audioUrl) {
            const audio = document.getElementById('mp3Audio');
            if (!audio) return;
            if (audioUrl) {
                audio.style.display = 'block';
                audio.src = audioUrl;
                audio.load();
            } else {
                audio.style.display = 'none';
            }
            mp3ActiveSource = 'audio';

            if (mp3Tick) clearInterval(mp3Tick);
            mp3Tick = setInterval(() => {
                updateCurrentChordByTime(Number(audio.currentTime || 0));
            }, 250);
        }

        async function mountPlayer(videoId, audioUrl) {
            mountAudioFallback(audioUrl || '');
        }

        async function startAnalysis() {
            const input = document.getElementById('mp3YoutubeUrl');
            const url = (input?.value || '').trim();
            if (!url) {
                setStatus('Cole um link do YouTube para iniciar.');
                return;
            }

            setStatus('Enviando video para analise...');
            setProgress(2);
            setResultsVisible(false);

            const r = await fetch('/mp3detect/start', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ youtube_url: url }),
            });
            const data = await r.json();
            if (!r.ok || !data.job_id) {
                setStatus(data.error || 'Falha ao iniciar a analise.');
                setProgress(0);
                return;
            }

            mp3JobId = data.job_id;
            if (mp3Poll) clearInterval(mp3Poll);
            mp3Poll = setInterval(checkJob, 1800);
            await checkJob();
        }

        async function findYoutubeFromText() {
            const artist = (document.getElementById('mp3SearchArtist')?.value || '').trim();
            const song = (document.getElementById('mp3SearchSong')?.value || '').trim();
            if (!artist || !song) {
                setStatus('Preencha artista e musica para buscar no YouTube.');
                return;
            }

            setStatus('Buscando primeiro resultado no YouTube...');
            const r = await fetch('/mp3detect/youtube-search?artist=' + encodeURIComponent(artist) + '&song=' + encodeURIComponent(song));
            const data = await r.json();
            if (!r.ok || !data.youtube_url) {
                setStatus(data.error || 'Nao foi possivel achar link no YouTube.');
                return;
            }

            const urlInput = document.getElementById('mp3YoutubeUrl');
            if (urlInput) urlInput.value = data.youtube_url;
            setStatus('Link encontrado. Iniciando analise...');
            await startAnalysis();
        }

        async function checkJob() {
            if (!mp3JobId) return;
            const r = await fetch('/mp3detect/status/' + encodeURIComponent(mp3JobId));
            const data = await r.json();
            if (!r.ok) {
                setStatus(data.error || 'Falha ao consultar status.');
                return;
            }

            setProgress(data.progress || 0);

            if (data.status === 'queued') {
                setStatus('Job na fila...');
                return;
            }
            if (data.status === 'running') {
                setStatus('Transcrevendo acordes... isso pode levar alguns minutos.');
                return;
            }
            if (data.status === 'error') {
                if (mp3Poll) clearInterval(mp3Poll);
                setStatus('Erro: ' + (data.error || 'nao foi possivel processar o video.'));
                return;
            }
            if (data.status === 'done') {
                if (mp3Poll) clearInterval(mp3Poll);
                setStatus('Analise concluida.');
                setResultsVisible(true);
                mp3Timeline = Array.isArray(data.timeline) ? data.timeline : [];
                mp3CurrentTimelineIndex = -1;
                renderTimeline(mp3Timeline);
                const bpmEl = document.getElementById('mp3Bpm');
                if (bpmEl) bpmEl.textContent = Number(data.bpm || 0) > 0 ? String(data.bpm) : '--';
                setCoverArt(
                    data.cover_url || '',
                    data.cover_album || '',
                    data.cover_artist || '',
                    data.cover_year || '',
                    data.cover_country || '',
                    data.cover_label || '',
                    data.title || '',
                    data.song_title || ''
                );
                attachAudioTrack(data.audio_url || '');
                await mountPlayer(data.video_id || '', data.audio_url || '');

                const parsed = parseTrackTitle(data.title || '');
                const lyricArtist = (data.cover_artist || parsed.artist || '').trim();
                const lyricTitle = (parsed.title || data.title || '').trim();
                mp3TranslationHtml = data.translation_html || '';
                await loadLyrics(lyricArtist, lyricTitle, data.lyrics_html || '');
                loadCifra(data.cifra_html || '');
                if (mp3TranslationOn) {
                    await loadTranslationIfNeeded();
                }

                if (mp3Timeline.length) {
                    updateCurrentChordByTime(0);
                }
            }
        }

        document.addEventListener('DOMContentLoaded', () => {
            const btnFind = document.getElementById('mp3FindYoutubeBtn');
            if (btnFind) btnFind.addEventListener('click', findYoutubeFromText);
            const trBtn = document.getElementById('mp3ToggleTranslation');
            if (trBtn) {
                trBtn.addEventListener('click', async () => {
                    setTranslationToggle(!mp3TranslationOn);
                    if (mp3TranslationOn) {
                        await loadTranslationIfNeeded();
                    }
                });
            }
            const searchArtist = document.getElementById('mp3SearchArtist');
            const searchSong = document.getElementById('mp3SearchSong');
            const bindEnter = (el) => {
                if (!el) return;
                el.addEventListener('keydown', (ev) => {
                    if (ev.key === 'Enter') {
                        ev.preventDefault();
                        findYoutubeFromText();
                    }
                });
            };
            bindEnter(searchArtist);
            bindEnter(searchSong);
            bindLyricsScrollSync();
            bindTimelineSeek();
            setTranslationToggle(false);
            setResultsVisible(false);
        });
    </script>
    </main>
    """
    return html


@app.route("/mp3detect/start", methods=["POST"])
def mp3detect_start():
    payload = request.get_json(silent=True) or {}
    youtube_url = (payload.get("youtube_url") or "").strip()
    video_id = _mp3detect_parse_video_id(youtube_url)
    if not video_id:
        return jsonify({"error": "Link do YouTube invalido."}), 400

    job_id = uuid.uuid4().hex
    with MP3DETECT_LOCK:
        MP3DETECT_JOBS[job_id] = {
            "status": "queued",
            "progress": 0,
            "error": "",
            "created_at": int(time.time()),
            "video_id": video_id,
            "title": "",
            "timeline": [],
            "duration": 0.0,
            "bpm": 0,
            "audio_path": "",
            "audio_mime": "audio/mpeg",
            "cover_url": "",
            "cover_album": "",
            "cover_artist": "",
            "cover_year": "",
            "cover_country": "",
            "cover_label": "",
            "song_title": "",
            "lyrics_html": "",
            "translation_html": "",
            "cifra_html": "",
        }

    t = threading.Thread(target=_mp3detect_worker, args=(job_id, youtube_url), daemon=True)
    t.start()

    return jsonify({"job_id": job_id})


@app.route("/mp3detect/status/<job_id>", methods=["GET"])
def mp3detect_status(job_id):
    with MP3DETECT_LOCK:
        job = MP3DETECT_JOBS.get(job_id)
        if not job:
            return jsonify({"error": "Job nao encontrado."}), 404

        return jsonify(
            {
                "status": job.get("status", "queued"),
                "progress": int(job.get("progress", 0)),
                "error": job.get("error", ""),
                "video_id": job.get("video_id", ""),
                "title": job.get("title", ""),
                "duration": float(job.get("duration", 0.0)),
                "bpm": int(job.get("bpm", 0)),
                "timeline": job.get("timeline", []),
                "audio_url": f"/mp3detect/audio/{job_id}" if job.get("audio_path") else "",
                "cover_url": job.get("cover_url", ""),
                "cover_album": job.get("cover_album", ""),
                "cover_artist": job.get("cover_artist", ""),
                "cover_year": job.get("cover_year", ""),
                "cover_country": job.get("cover_country", ""),
                "cover_label": job.get("cover_label", ""),
                "song_title": job.get("song_title", ""),
                "lyrics_html": job.get("lyrics_html", ""),
                "translation_html": job.get("translation_html", ""),
                "cifra_html": job.get("cifra_html", ""),
            }
        )


@app.route("/mp3detect/audio/<job_id>", methods=["GET"])
def mp3detect_audio(job_id):
    with MP3DETECT_LOCK:
        job = MP3DETECT_JOBS.get(job_id)
        if not job:
            return jsonify({"error": "Job nao encontrado."}), 404
        audio_path = (job.get("audio_path") or "").strip()
        audio_mime = (job.get("audio_mime") or "audio/mpeg").strip()

    if not audio_path:
        return jsonify({"error": "Audio nao disponivel para este job."}), 404

    caminho = Path(audio_path)
    if not caminho.exists() or not caminho.is_file():
        return jsonify({"error": "Arquivo de audio expirado ou removido."}), 404

    return send_file(str(caminho), mimetype=audio_mime, as_attachment=False, conditional=True)


@app.route("/mp3detect/lyrics", methods=["GET"])
def mp3detect_lyrics():
    artist = (request.args.get("artist") or "").strip()
    title = (request.args.get("title") or "").strip()
    translate = (request.args.get("translate") or "0").strip() == "1"

    if not title:
        return jsonify({"found": False, "error": "Titulo obrigatorio."}), 400

    from_db = _mp3detect_fetch_lyrics_db(artist, title)
    letra_html = from_db.get("lyrics_html", "")
    traducao_html = from_db.get("translation_html", "")

    # Fallback: tenta buscar externamente apenas se nao houver letra no BD.
    if not letra_html:
        try:
            artist_slug = slugify(artist) or normalizar_slug(artist)
            title_slug = slugify(title) or normalizar_slug(title)
            letra_ext, traducao_ext = procura_letra(artist_slug, title_slug)
            letra_ext = re.sub(r"<script.*?>.*?</script>", "", letra_ext or "", flags=re.IGNORECASE | re.DOTALL)
            traducao_ext = re.sub(r"<script.*?>.*?</script>", "", traducao_ext or "", flags=re.IGNORECASE | re.DOTALL)
            letra_html = letra_ext
            if not traducao_html:
                traducao_html = traducao_ext
        except Exception:
            letra_html = ""

    resp = {
        "found": bool(letra_html),
        "lyrics_html": letra_html or "",
        "translation_html": "",
    }

    if translate:
        if traducao_html:
            resp["translation_html"] = traducao_html
        elif letra_html:
            try:
                from bs4 import BeautifulSoup
                from deep_translator import GoogleTranslator

                texto_puro = BeautifulSoup(letra_html, "html.parser").get_text("\n")
                traducao = GoogleTranslator(source="auto", target="pt").translate(texto_puro)
                traducao_html = "<p>" + (traducao or "").replace("\n", "</p><p>") + "</p>"
                traducao_html = re.sub(r"<script.*?>.*?</script>", "", traducao_html, flags=re.IGNORECASE | re.DOTALL)
                resp["translation_html"] = traducao_html
            except Exception:
                resp["translation_html"] = ""

    return jsonify(resp)


@app.route("/mp3detect/youtube-search", methods=["GET"])
def mp3detect_youtube_search():
    artist = (request.args.get("artist") or "").strip()
    song = (request.args.get("song") or "").strip()
    if not artist or not song:
        return jsonify({"error": "Informe artista e musica."}), 400

    # Prioriza helper existente no projeto (primeiro resultado).
    try:
        url = buscar_video_youtube(artist, song, indice=0)
        if url:
            return jsonify({"youtube_url": url})
    except Exception:
        pass

    # Fallback rapido via API publica de busca.
    try:
        query = f"{artist} {song}".strip()
        r = requests.get(
            "https://ytsearch.vercel.app/api",
            params={"q": query},
            timeout=10,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        data = r.json() if r.ok else {}
        videos = data.get("videos") or []
        if videos:
            video_id = (videos[0].get("videoId") or "").strip()
            if video_id and re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id):
                return jsonify({"youtube_url": f"https://www.youtube.com/watch?v={video_id}"})
    except Exception:
        pass

    return jsonify({"error": "Nenhum resultado encontrado no YouTube."}), 404


@app.route("/api/flix-play/search")
def flix_play_search_api():
    q = (request.args.get("q") or "").strip()
    try:
        limit = int(request.args.get("limit") or 10)
    except Exception:
        limit = 10
    limit = max(1, min(10, limit))

    if not q:
        return jsonify({"results": []})

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

    _refresh_guitarpro_index_txt()
    idx_path = _guitarpro_index_file_path()
    if not idx_path.exists():
        return jsonify({"results": []})

    q_norm = _normalizar_guitarpro_nome(q)
    if not q_norm:
        return jsonify({"results": []})
    q_flat = q_norm.replace(" ", "")
    q_tokens = [tok for tok in q_norm.split(" ") if tok]

    out = []
    vistos = set()
    conn = None
    cur = None

    def _album_info_for_track(artista_slug, musica_slug, musica_titulo):
        if not cur:
            return ("", "")

        try:
            slug_base = re.sub(r"-(?:ver-\d+|\d+)$", "", musica_slug or "").strip("-")
            titulo_base_txt = re.sub(r"\s*\(.*?\)\s*$", "", (musica_titulo or "").strip())
            titulo_base_like = f"{titulo_base_txt} (%" if titulo_base_txt else ""
            artista_hint_like = f"%{(artista_slug or '').replace('-', ' ')}%"
            cur.execute(
                """
                SELECT
                    al.id AS album_id,
                    al.nome AS album_nome,
                    COALESCE(al.capa, '') AS album_capa
                FROM cancao c
                JOIN albuns al ON al.id = c.album_id
                JOIN artistas ar ON ar.id = al.artista_id
                WHERE (ar.slug = ? OR ar.slug = 'unknown')
                  AND (
                    c.cancao_slug = ?
                    OR c.cancao_slug = ?
                    OR c.cancao_slug LIKE ?
                    OR LOWER(TRIM(c.titulo)) = LOWER(TRIM(?))
                    OR LOWER(TRIM(c.titulo)) LIKE LOWER(TRIM(?))
                  )
                ORDER BY
                    CASE
                        WHEN ar.slug = ? THEN 0
                        WHEN ar.slug = 'unknown' AND LOWER(COALESCE(al.nome, '')) LIKE LOWER(?) THEN 1
                        WHEN ar.slug = 'unknown' THEN 2
                        ELSE 9
                    END,
                    CASE
                        WHEN c.cancao_slug = ? THEN 0
                        WHEN c.cancao_slug = ? THEN 1
                        WHEN LOWER(TRIM(c.titulo)) = LOWER(TRIM(?)) THEN 2
                        WHEN LOWER(TRIM(c.titulo)) LIKE LOWER(TRIM(?)) THEN 3
                        WHEN c.cancao_slug LIKE ? THEN 4
                        ELSE 8
                    END,
                    c.id
                LIMIT 1
                """,
                (
                    artista_slug,
                    musica_slug,
                    musica_slug,
                    slug_base,
                    titulo_base_txt,
                    titulo_base_like,
                    artista_slug,
                    artista_hint_like,
                    musica_slug,
                    slug_base,
                    titulo_base_txt,
                    titulo_base_like,
                    f"{slug_base}-%",
                ),
            )
            row = cur.fetchone()
            if not row:
                return ("", "")

            album_nome = (row[1] or "").strip()
            capa_raw = (row[2] or "").strip()
            if capa_raw and capa_raw.lower() not in {"null", "none", "nan"}:
                return (album_nome, capa_raw)

            return (album_nome, "")
        except Exception:
            return ("", "")

        return ("", "")

    try:
        conteudo = idx_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return jsonify({"results": []})

    try:
        conn = sqlite3.connect(DB)
        cur = conn.cursor()
    except Exception:
        conn = None
        cur = None

    for linha in conteudo.splitlines():
        if not linha.strip():
            continue
        partes = linha.split("\t")
        if len(partes) < 5:
            continue

        artista_norm = (partes[0] or "").strip()
        musica_norm = (partes[1] or "").strip()
        artista_nome = (partes[3] or artista_norm.title()).strip()
        musica_titulo = limpar_titulo_gp((partes[4] or musica_norm.title()).strip())
        musica_titulo_view = titulo_exibicao(musica_titulo) or musica_titulo
        if not artista_norm or not musica_norm:
            continue

        artista_raw_norm = _normalizar_guitarpro_nome(artista_nome)
        musica_raw_norm = _normalizar_guitarpro_nome(musica_titulo)
        artista_raw_low = artista_nome.lower()
        musica_raw_low = musica_titulo.lower()
        artista_flat = (artista_norm or artista_raw_norm).replace(" ", "")
        musica_flat = (musica_norm or musica_raw_norm).replace(" ", "")
        q_low = q.lower()
        combined_norm = " ".join(
            [artista_norm, musica_norm, artista_raw_norm, musica_raw_norm]
        ).strip()
        token_match = bool(q_tokens) and all(tok in combined_norm for tok in q_tokens)

        direct_match = not (
            q_norm not in artista_norm
            and q_norm not in musica_norm
            and q_norm not in artista_raw_norm
            and q_norm not in musica_raw_norm
            and q_flat not in artista_flat
            and q_flat not in musica_flat
            and q_low not in artista_raw_low
            and q_low not in musica_raw_low
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
