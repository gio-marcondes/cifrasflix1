import os
import re
import time
import json
import requests
import tkinter as tk
import unicodedata

from tkinter import ttk, messagebox

# =========================================================
# CONFIG
# =========================================================

BASE_PATH = r"C:\Users\e179ti\Documents\cifras_baixadas"

DISCOGRAFIA_FILE = os.path.join(
    BASE_PATH,
    "discografia2.json"
)

API_URL = "https://musicbrainz.org/ws/2"

HEADERS = {
    "User-Agent": (
        "CifrasFlixDiscografia/2.1 "
        "( giovanimarcondes@email.com )"
    )
}

# =========================================================
# SAFE GET
# =========================================================

def safe_get(url, params=None):

    try:

        r = requests.get(
            url,
            params=params,
            headers=HEADERS,
            timeout=20
        )

        print("URL:", r.url)
        print("STATUS:", r.status_code)

        if r.status_code != 200:
            return None

        # RATE LIMIT
        time.sleep(0.3)

        return r.json()

    except Exception as e:

        print("ERRO:", e)

        return None

# =========================================================
# NORMALIZAR
# =========================================================
def limpar_texto(txt):

    if not txt:
        return txt

    return (
        str(txt)
        .replace("’", "'")
        .replace("‘", "'")
        .replace("`", "'")
        .replace("´", "'")
    )

def normalizar(txt):

    txt = str(txt)

    txt = txt.replace("’", "'")
    txt = txt.replace("‘", "'")
    txt = txt.replace("`", "'")
    txt = txt.replace("´", "'")

    txt = txt.lower()

    txt = unicodedata.normalize(
        "NFKD",
        txt
    ).encode(
        "ascii",
        "ignore"
    ).decode("ascii")

    txt = re.sub(r"[^a-z0-9]+", " ", txt)

    return txt.strip()

# =========================================================
# MBID ARTISTA
# =========================================================

def search_artist_mbid(artist_name):

    # IGNORAR NOMES MUITO CURTOS
    if len(artist_name.strip()) <= 1:
        return None

    url = f"{API_URL}/artist"

    params = {
        "query": f'artist:"{artist_name}"',
        "fmt": "json",
        "limit": 10
    }

    data = safe_get(url, params)

    if not data:
        return None

    artists = data.get("artists", [])

    if not artists:
        return None

    artist_norm = normalizar(artist_name)

    # =====================================================
    # PROCURAR MATCH EXATO
    # =====================================================

    for art in artists:

        nome_api = art.get("name", "")

        if normalizar(nome_api) == artist_norm:

            print("✅ MATCH:", nome_api)

            return art["id"]

    # =====================================================
    # MATCH PARCIAL
    # =====================================================

    for art in artists:

        nome_api = art.get("name", "")

        nome_norm = normalizar(nome_api)

        if artist_norm in nome_norm:

            print("⚠ MATCH PARCIAL:", nome_api)

            return art["id"]

    print("❌ ARTISTA NÃO CONFERE")

    return None

# =========================================================
# ÁLBUNS OFICIAIS
# =========================================================

def get_official_albums(artist_mbid):

    albums = []

    offset = 0

    while True:

        url = f"{API_URL}/release-group"

        params = {
            "artist": artist_mbid,
            "type": "album",
            "fmt": "json",
            "limit": 100,
            "offset": offset
        }

        data = safe_get(url, params)

        if not data:
            break

        groups = data.get("release-groups", [])

        if not groups:
            break

        for g in groups:

            title = g.get("title", "").strip()

            primary = g.get("primary-type", "")

            secondary = g.get("secondary-types", [])

            release_date = g.get(
                "first-release-date",
                ""
            )

            year = ""

            if release_date:
                year = release_date[:4]

            # IGNORAR COMPILAÇÕES
            if primary == "Album" and not secondary:

                rgid = g.get("id")

                if title and rgid:

                    albums.append({
                        "title": title,
                        "year": year,
                        "rgid": rgid
                    })

        offset += len(groups)

        if len(groups) < 100:
            break

    # =====================================================
    # REMOVER DUPLICADOS
    # =====================================================

    vistos = set()

    unicos = []

    for alb in albums:

        chave = normalizar(alb["title"])

        if chave not in vistos:

            vistos.add(chave)

            unicos.append(alb)

    return unicos

# =========================================================
# PRIMEIRA RELEASE
# =========================================================

def buscar_release_id(rgid):

    url = f"{API_URL}/release"

    params = {
        "release-group": rgid,
        "fmt": "json",
        "limit": 10
    }

    data = safe_get(url, params)

    if not data:
        return None

    releases = data.get("releases", [])

    if not releases:
        return None

    # =====================================================
    # PRIORIDADE:
    # 1. RELEASE OFICIAL
    # 2. US
    # 3. PRIMEIRA
    # =====================================================

    for rel in releases:

        status = rel.get("status", "")

        if status == "Official":

            return rel["id"]

    return releases[0]["id"]

# =========================================================
# DETALHES RELEASE
# =========================================================

def buscar_detalhes_release(
    release_id,
    artista_original
):

    try:

        url = f"{API_URL}/release/{release_id}"

        params = {
            "inc": "recordings+labels+artist-credits",
            "fmt": "json"
        }

        r = safe_get(url, params)

        if not r:
            return None

        album = limpar_texto(
            r.get("title", "")
        )

        data = r.get("date", "")

        ano = data[:4] if data else ""

        pais = r.get("country", "")

        # =================================================
        # FORÇAR ARTISTA ORIGINAL
        # =================================================

        artista = artista_original
        artista = limpar_texto(
            artista
        )
        if r.get("artist-credit"):

            nome_api = r["artist-credit"][0].get(
                "name",
                ""
            )

            nome_norm = normalizar(nome_api)

            # IGNORAR VARIOUS ARTISTS
            if nome_norm not in [
                "various artists",
                "various"
            ]:

                artista = nome_api

        # =================================================
        # GRAVADORA
        # =================================================

        gravadora = "—"

        if r.get("label-info"):

            info = r["label-info"][0]

            if info.get("label"):

                gravadora = info["label"].get(
                    "name",
                    "—"
                )

        # =================================================
        # TRACKS
        # =================================================

        tracks = []

        for media in r.get("media", []):

            for pos, t in enumerate(
                media.get("tracks", []),
                start=1
            ):

                duracao = t.get("length")

                if duracao:
                    duracao = round(
                        duracao / 1000
                    )

                tracks.append({

                    "faixa": pos,

                    "titulo": limpar_texto(
                        t.get("title", "")
                    ),

                    "duracao_segundos": duracao
                })

        return {
            "album": album,
            "artista": artista,
            "ano": ano,
            "pais": pais,
            "gravadora": gravadora,
            "musicas": tracks
        }

    except Exception as e:

        print("ERRO:", e)

        return None

# =========================================================
# GUI
# =========================================================

class App:

    def __init__(self, root):

        self.root = root

        self.root.title(
            "Discografia MusicBrainz"
        )

        self.root.geometry("900x650")

        title = ttk.Label(
            root,
            text="Discografia Completa",
            font=("Arial", 18, "bold")
        )

        title.pack(pady=10)

        self.btn_start = ttk.Button(
            root,
            text="Iniciar processamento",
            command=self.start
        )

        self.btn_start.pack(pady=5)

        self.buscar_pasta = tk.BooleanVar(value=True)

        ttk.Checkbutton(
            root,
            text="Buscar artistas da pasta",
            variable=self.buscar_pasta
        ).pack(pady=5)
        self.pular_limite_albuns = tk.BooleanVar(value=False)

        ttk.Checkbutton(
            root,
            text="Baixar todos os álbuns (ignorar limite de 10)",
            variable=self.pular_limite_albuns
        ).pack(pady=2)

        self.reprocessar_artistas = tk.BooleanVar(value=False)

        ttk.Checkbutton(
            root,
            text="Baixar mesmo se artista já existir no JSON",
            variable=self.reprocessar_artistas
        ).pack(pady=2)
        ttk.Label(
            root,
            text="Lista de artistas (1 por linha)"
        ).pack()

        self.txt_artistas = tk.Text(
            root,
            height=8,
            font=("Consolas", 10)
        )

        self.txt_artistas.pack(
            fill="x",
            padx=10,
            pady=5
        )

        self.btn_lista = ttk.Button(
            root,
            text="Baixar lista",
            command=self.start_lista
        )

        self.btn_lista.pack(pady=5)

        self.progress = ttk.Progressbar(
            root,
            length=700,
            mode="determinate"
        )

        self.progress.pack(pady=10)

        self.log = tk.Text(
            root,
            height=35,
            font=("Consolas", 10)
        )

        self.log.pack(
            fill="both",
            expand=True,
            padx=10,
            pady=10
        )

    # =====================================================

    def write_log(self, msg):

        print(msg)

        self.log.insert(
            "end",
            msg + "\n"
        )

        self.log.see("end")

        self.root.update()

    # =====================================================

    def salvar_json(self):

        with open(
            DISCOGRAFIA_FILE,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                self.dados_existentes,
                f,
                ensure_ascii=False,
                indent=4
            )

    # =====================================================

    def obter_artistas_lista(self):

        texto = self.txt_artistas.get("1.0", "end")

        artistas = []

        for linha in texto.splitlines():
            linha = linha.strip()
            if linha:
                artistas.append(linha)

        return artistas

    # =====================================================

    def start_lista(self):

        artistas = self.obter_artistas_lista()

        if not artistas:

            messagebox.showwarning(
                "Aviso",
                "Informe ao menos um artista."
            )

            return

        self.processar_artistas_forcados = artistas

        self.start()

    # =====================================================

    def start(self):

        self.write_log("")
        self.write_log("🌐 TESTANDO API...")

        teste = safe_get(
            f"{API_URL}/artist",
            {
                "query": "queen",
                "fmt": "json"
            }
        )

        if not teste:

            self.write_log(
                "❌ API NÃO RESPONDEU"
            )

            return

        self.write_log(
            "✅ API OK"
        )

        self.write_log("")
        self.write_log("===================================")
        self.write_log("INICIANDO PROCESSAMENTO")
        self.write_log("===================================")

        # =====================================================
        # CARREGAR JSON
        # =====================================================

        self.dados_existentes = []

        if os.path.exists(DISCOGRAFIA_FILE):

            try:

                with open(
                    DISCOGRAFIA_FILE,
                    "r",
                    encoding="utf-8"
                ) as f:

                    self.dados_existentes = json.load(f)

            except:
                self.dados_existentes = []

        # =====================================================
        # ÁLBUNS EXISTENTES
        # =====================================================

        self.albuns_existentes = {

            (
                normalizar(
                    item.get("artista", "")
                ),

                normalizar(
                    item.get("album", "")
                )
            )

            for item in self.dados_existentes
        }

        # =====================================================
        # ARTISTAS EXISTENTES
        # =====================================================

        # =====================================================
# MAPA DE ARTISTAS DO JSON
# =====================================================

        self.artistas_existentes = set()

        for item in self.dados_existentes:

            artista_json = item.get(
                "artista",
                ""
            )

            artista_norm = normalizar(
                artista_json
            )

            # IGNORAR LIXO
            if artista_norm in [
                "",
                "various artists",
                "various",
                "name",
                "live"
            ]:
                continue

            self.artistas_existentes.add(
                artista_norm
            )

        self.write_log("")
        self.write_log("===================================")
        self.write_log("✅ JSON VERIFICADO")
        self.write_log(
            f"📀 {len(self.dados_existentes)} álbuns carregados"
        )
        self.write_log(
            f"🎤 {len(self.artistas_existentes)} artistas encontrados"
        )
        self.write_log("===================================")

        # =====================================================
        # ARTISTAS
        # =====================================================

        if hasattr(self, "processar_artistas_forcados"):

            artists = self.processar_artistas_forcados
            del self.processar_artistas_forcados

        elif self.buscar_pasta.get():

            artists = [

                d for d in os.listdir(BASE_PATH)

                if os.path.isdir(
                    os.path.join(BASE_PATH, d)
                )

            ]

        else:

            artists = self.obter_artistas_lista()

            if not artists:

                messagebox.showwarning(
                    "Aviso",
                    "Informe artistas na lista."
                )

                return

        total = len(artists)

        self.progress["maximum"] = total

        # =====================================================
        # LOOP
        # =====================================================

        for i, artist in enumerate(
            artists,
            start=1
        ):

            self.write_log("")
            self.write_log(f"🎤 {artist}")

            artista_norm = normalizar(artist)

            # =================================================
            # IGNORAR VARIOUS
            # =================================================

            if artista_norm in [
                "various artists",
                "various"
            ]:

                self.write_log(
                    "   ⏭ pulando Various Artists"
                )

                continue

            # =================================================
            # IGNORAR NOMES MUITO CURTOS
            # =================================================

            if len(artista_norm) <= 1:

                self.write_log(
                    "   ⏭ nome muito curto"
                )

                continue

            # =================================================
            # JÁ EXISTE
            # =================================================

            if (
                artista_norm in self.artistas_existentes
                and not self.reprocessar_artistas.get()
            ):

                self.write_log(
                    "   ⏭ artista já existe no JSON"
                )

                continue
            # =================================================
            # MBID
            # =================================================

            mbid = search_artist_mbid(
                artist
            )

            if not mbid:

                self.write_log(
                    "   ❌ MBID não encontrado"
                )

                continue

            # =================================================
            # ÁLBUNS
            # =================================================

            albums = get_official_albums(
                mbid
            )

            if not albums:

                self.write_log(
                    "   ❌ nenhum álbum"
                )

                continue

            # =================================================
            # LIMITE
            # =================================================

            if (
                len(albums) > 15
                and not self.pular_limite_albuns.get()
            ):

                self.write_log(
                    f"   ⚠ artista possui {len(albums)} álbuns"
                )

                self.write_log(
                    "   ⏭ baixando apenas os 10 primeiros"
                )

                albums = albums[:10]

            elif self.pular_limite_albuns.get():

                self.write_log(
                    f"   ✅ baixando todos os {len(albums)} álbuns"
                )

            self.write_log(
                f"   💿 {len(albums)} álbuns"
            )

            # =================================================
            # LOOP ÁLBUNS
            # =================================================

            for alb in albums:

                album = alb["title"]

                rgid = alb["rgid"]

                if (
                    normalizar(artist),
                    normalizar(album)
                ) in self.albuns_existentes:

                    self.write_log(
                        f"      ⚠ já existe: {album}"
                    )

                    continue

                self.write_log(
                    f"      🔍 {album}"
                )

                release_id = buscar_release_id(
                    rgid
                )

                if not release_id:

                    self.write_log(
                        "         ❌ release não encontrada"
                    )

                    continue

                dados_album = buscar_detalhes_release(
                    release_id,
                    artist
                )

                if not dados_album:

                    self.write_log(
                        "         ❌ erro detalhes"
                    )

                    continue

                self.dados_existentes.append(
                    dados_album
                )

                self.albuns_existentes.add(
                    (
                        normalizar(
                            dados_album["artista"]
                        ),

                        normalizar(
                            dados_album["album"]
                        )
                    )
                )

                self.salvar_json()

                self.write_log(
                    f"         ✔ "
                    f"{len(dados_album['musicas'])} músicas"
                )

            self.progress["value"] = i

            self.root.update()

        self.write_log("")
        self.write_log("===================================")
        self.write_log("✅ FINALIZADO")
        self.write_log("===================================")

        messagebox.showinfo(
            "Concluído",
            f"Arquivo salvo em:\n\n{DISCOGRAFIA_FILE}"
        )

# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":

    root = tk.Tk()

    app = App(root)

    root.mainloop()