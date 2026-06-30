import os
import re
import random
import sqlite3
import time
from flask import Flask, request, redirect, jsonify
from pathlib import Path

from flask import Flask, request, render_template, render_template_string
import os
import requests
from bs4 import BeautifulSoup
import json

import requests
import re
import urllib.parse
import requests
import urllib.parse
import re

app = Flask(__name__)
DB = "cifras.db"
PASTA_TXT = "cifras_txt"

from flask import Flask, request, redirect, url_for, render_template, render_template_string, session
import os
from werkzeug.utils import secure_filename

app.secret_key = "ttx15_secret"  # necessário para session

UPLOAD_FOLDER = "static/capas"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
HEADERS_MB = {
    "User-Agent": "CifrasFlix/1.0 (seuemail@exemplo.com)"
}

def formatar_data(data_str):
    if not data_str:
        return ""

    try:
        from datetime import datetime

        # tenta YYYY-MM-DD
        dt = datetime.strptime(data_str[:10], "%Y-%m-%d")

        meses = [
            "", "janeiro", "fevereiro", "março", "abril",
            "maio", "junho", "julho", "agosto",
            "setembro", "outubro", "novembro", "dezembro"
        ]

        return f"{dt.day} de {meses[dt.month]} de {dt.year}"

    except:
        return data_str
# ==========================================
# SLUGIFY
# ==========================================
def slugify(texto):
    texto = texto.lower()
    texto = re.sub(r'[^a-z0-9]+', '-', texto)
    return texto.strip('-')
def normalizar_slug(texto):
    import re
    texto = texto.lower().strip()
    texto = texto.replace(" ", "-")
    texto = re.sub(r"[^a-z0-9\-]", "", texto)
    return texto


def connect_db(timeout=30.0):
    conn = sqlite3.connect(DB, timeout=timeout)
    try:
        conn.execute("PRAGMA journal_mode=WAL")
    except Exception:
        pass
    try:
        conn.execute(f"PRAGMA busy_timeout={int(timeout * 1000)}")
    except Exception:
        pass
    try:
        conn.execute("PRAGMA synchronous=NORMAL")
    except Exception:
        pass
    return conn
# ==========================================
# BANCO
# ==========================================


def baixar_imagem_blob(url):

    print("URL CAPA:", url)

    if not url:
        print("❌ URL vazia")
        return None

    try:

        r = requests.get(url, timeout=20)

        print("STATUS IMG:", r.status_code)

        if r.status_code == 200:

            print("BYTES:", len(r.content))

            return r.content

    except Exception as e:

        print("ERRO DOWNLOAD:", e)

    return None

def pegar_ano(data_str):
    if not data_str:
        return ""

    # pega os 4 primeiros caracteres se forem números
    ano = str(data_str)[:4]

    return ano if ano.isdigit() else ""

def init_db():
    conn = connect_db()
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS artistas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT UNIQUE,
        slug TEXT UNIQUE
    )
    """)
    c.execute("""
    CREATE TABLE IF NOT EXISTS musicas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        titulo TEXT,
        slug TEXT,
        uid TEXT UNIQUE,
        artista_id INTEGER,
        conteudo TEXT,
        tom TEXT,
        afinacao TEXT,
        capotraste TEXT,
        views INTEGER DEFAULT 0,
        FOREIGN KEY (artista_id) REFERENCES artistas(id)
    )
    """)
    c.execute("""
    CREATE TABLE IF NOT EXISTS favoritos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        musica_id INTEGER UNIQUE
    )
    """)
    c.execute("""
    CREATE TABLE IF NOT EXISTS playlists (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT,
        publica INTEGER DEFAULT 0,
        likes INTEGER DEFAULT 0
    )
    """)
    c.execute("""
    CREATE TABLE IF NOT EXISTS playlist_musicas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        playlist_id INTEGER,
        musica_id INTEGER,
        FOREIGN KEY (playlist_id) REFERENCES playlists(id) ON DELETE CASCADE,
        FOREIGN KEY (musica_id) REFERENCES musicas(id) ON DELETE CASCADE
    )
    """)
    conn.commit()
    conn.close()

# ==========================================
# IMPORTADOR TXT
# ==========================================
def importar_txt():
    conn = connect_db()
    c = conn.cursor()

    pasta = Path(PASTA_TXT)

    if not pasta.exists():
        print("Pasta cifras_txt não encontrada.")
        return

    for pasta_artista in pasta.iterdir():

        if pasta_artista.is_dir():

            artista_nome = pasta_artista.name.strip()
            artista_slug = slugify(artista_nome)

            c.execute(
                "INSERT OR IGNORE INTO artistas (nome, slug) VALUES (?,?)",
                (artista_nome, artista_slug)
            )

            c.execute(
                "SELECT id FROM artistas WHERE slug=?",
                (artista_slug,)
            )

            artista_id = c.fetchone()[0]

            print(f"\n🎤 ARTISTA: {artista_nome}")

            for arquivo in pasta_artista.glob("*.txt"):

                try:

                    with open(arquivo, "r", encoding="utf-8", errors="ignore") as f:
                        conteudo_original = f.read()

                    linhas = conteudo_original.splitlines()

                    afinacao = ""
                    tom = ""
                    capotraste = ""

                    # ------------------------
                    # TITULO
                    # ------------------------
                    titulo = arquivo.stem.strip()

                    if linhas:
                        primeira = linhas[0].replace(" Cifra", "").strip()

                        if primeira:
                            titulo = primeira

                    # ------------------------
                    # CAPTURA INFORMAÇÕES
                    # ------------------------
                    for linha in linhas:

                        linha_strip = linha.strip()

                        # afinação
                        if linha_strip.lower().startswith("afinação:"):
                            afinacao = linha_strip.split(":", 1)[1].strip()

                        # tom
                        if linha_strip.lower().startswith("tecla:"):
                            tom = linha_strip.split(":", 1)[1].strip()

                        # capotraste
                        if linha_strip.lower().startswith("capotraste:"):

                            match = re.search(r"(\d+)", linha_strip)

                            if match:
                                capotraste = match.group(1)
                            else:
                                capotraste = "0"

                    # -----------------------------------
                    # PEGA SOMENTE O QUE VEM APÓS TAB:
                    # -----------------------------------
                    match_tab = re.search(
                        r"TAB:\s*(.*)",
                        conteudo_original,
                        re.DOTALL | re.IGNORECASE
                    )

                    if match_tab:
                        conteudo = match_tab.group(1).strip()
                    else:
                        conteudo = ""

                    slug = slugify(titulo)

                    uid = f"{slug}-{random.randint(10000,99999)}"

                    c.execute("""
                    INSERT OR IGNORE INTO musicas
                    (
                        titulo,
                        slug,
                        uid,
                        artista_id,
                        conteudo,
                        afinacao,
                        tom,
                        capotraste
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        titulo,
                        slug,
                        uid,
                        artista_id,
                        conteudo,
                        afinacao,
                        tom,
                        capotraste
                    ))

                    print(f"   ✅ {titulo}")
                    print(f"      Tom: {tom}")
                    print(f"      Afinação: {afinacao}")
                    print(f"      Capotraste: {capotraste}")

                except Exception as e:

                    print(f"   ❌ ERRO: {arquivo.name}")
                    print(e)

    conn.commit()
    conn.close()

    print("\n✅ Importação concluída.")

# ==========================================
# TRANSPOSIÇÃO REAL
# ==========================================
NOTAS = ["C","C#","D","D#","E","F","F#","G","G#","A","A#","B"]

def transpor_acordes(texto, semitons):
    if semitons == 0:
        return texto

    MAP_TO_INDEX = {
        "C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4, "F": 5, "F#": 6, "Gb": 6, "G": 7, "G#": 8, "Ab": 8, "A": 9, "A#": 10, "Bb": 10, "B": 11
    }

    def transpor_nota(nota):
        if not nota:
            return ""
        if nota not in MAP_TO_INDEX:
            return nota
        idx = MAP_TO_INDEX[nota]
        new_idx = (idx + semitons) % 12
        if "b" in nota or new_idx in [1, 3, 8, 10]:  # Db, Eb, Ab, Bb
            return ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"][new_idx]
        return ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"][new_idx]

    def transpor_chord_match(match):
        chord = match.group(0)
        m = re.match(r"^([A-G][#b]?)([^/]*)(?:\/([A-G][#b]?))?$", chord)
        if not m:
            return chord
        root = m.group(1)
        mod = m.group(2) or ""
        slash = m.group(3)

        new_root = transpor_nota(root)
        new_slash = transpor_nota(slash) if slash else ""

        if new_slash:
            return f"{new_root}{mod}/{new_slash}"
        return f"{new_root}{mod}"

    # Regex para capturar acordes completos (ex: C#m7/G#, Ebmaj9)
    chord_pattern = r'\b[A-G][#b]?(?:maj9|maj7|m7b5|m7|m|7sus4|7sus2|7#11|7b13|7#9|7b9|7#5|7b5|7|sus4|sus2|dim|aug|add9|m6|6|9|11|13|5|M|M7)?(?:\/[A-G][#b]?)?\b'

    return re.sub(chord_pattern, transpor_chord_match, texto)

# ==========================================
# HEADER / CSS estilo Netflix
# ==========================================
