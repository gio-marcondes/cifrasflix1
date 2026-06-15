import re
import sqlite3
import unicodedata
import tkinter as tk
import requests

from tkinter import filedialog, messagebox

# =========================================================
# NORMALIZAR
# =========================================================

def normalizar(texto):

    if not texto:
        return ""

    texto = texto.lower()

    texto = unicodedata.normalize(
        "NFKD",
        texto
    )

    texto = texto.encode(
        "ascii",
        "ignore"
    ).decode("utf-8")

    texto = re.sub(
        r"[^a-z0-9]+",
        " ",
        texto
    )

    texto = texto.strip()

    return texto

# =========================================================
# CAPA DEEZER
# =========================================================

def buscar_capa_deezer(artista, album):

    try:

        from urllib.parse import quote

        query = f'artist:"{artista}" album:"{album}"'

        url = (
            "https://api.deezer.com/search/album"
            f"?q={quote(query)}"
        )

        r = requests.get(
            url,
            timeout=15
        ).json()

        data = r.get("data", [])

        if not data:
            return None

        album_norm = normalizar(album)

        artista_norm = normalizar(artista)

        melhor = None

        for item in data:

            nome_album = normalizar(
                item.get("title", "")
            )

            nome_artista = normalizar(
                item.get(
                    "artist",
                    {}
                ).get("name", "")
            )

            if (
                nome_album == album_norm
                and nome_artista == artista_norm
            ):

                melhor = item
                break

        if not melhor:
            melhor = data[0]

        capa = melhor.get("cover_xl")

        if not capa:
            capa = melhor.get("cover_big")

        print(
            f"🖼 Deezer capa encontrada: "
            f"{melhor.get('title')}"
        )

        return capa

    except Exception as e:

        print("ERRO DEEZER:", e)

    return None

# =========================================================
# APP
# =========================================================

class AtualizadorCapas:

    def __init__(self, root):

        self.root = root

        self.root.title("Atualizador de Capas Deezer")

        self.root.geometry("1000x700")

        self.db_path = ""

        self.criar_ui()

    # =====================================================
    # UI
    # =====================================================

    def criar_ui(self):

        frame = tk.Frame(self.root)
        frame.pack(fill="x", padx=10, pady=10)

        tk.Label(
            frame,
            text="Banco SQLite"
        ).grid(row=0, column=0, sticky="w")

        self.entry_db = tk.Entry(
            frame,
            width=90
        )

        self.entry_db.grid(
            row=0,
            column=1,
            padx=5
        )

        tk.Button(
            frame,
            text="Selecionar",
            command=self.selecionar_db
        ).grid(row=0, column=2)

        # BTN
        tk.Button(
            self.root,
            text="BUSCAR CAPAS",
            bg="#3498db",
            fg="white",
            font=("Arial", 12, "bold"),
            height=2,
            command=self.processar
        ).pack(fill="x", padx=10, pady=10)

        # LOG
        self.log_text = tk.Text(
            self.root,
            font=("Consolas", 10)
        )

        self.log_text.pack(
            fill="both",
            expand=True,
            padx=10,
            pady=10
        )

    # =====================================================
    # LOG
    # =====================================================

    def log(self, texto):

        self.log_text.insert(
            tk.END,
            texto + "\n"
        )

        self.log_text.see(tk.END)

        print(texto)

        self.root.update()

    # =====================================================
    # DB
    # =====================================================

    def selecionar_db(self):

        path = filedialog.askopenfilename(
            title="Banco SQLite",
            filetypes=[
                (
                    "SQLite",
                    "*.db *.sqlite *.sqlite3"
                )
            ]
        )

        if path:

            self.db_path = path

            self.entry_db.delete(0, tk.END)

            self.entry_db.insert(0, path)

    # =====================================================
    # PROCESSAR
    # =====================================================

    def processar(self):

        if not self.db_path:

            messagebox.showerror(
                "Erro",
                "Selecione o banco SQLite."
            )

            return

        try:

            conn = sqlite3.connect(self.db_path)

            cursor = conn.cursor()

            self.log("")
            self.log("========================================")
            self.log("BUSCANDO ÁLBUNS SEM CAPA")
            self.log("========================================")

            sql = """
            SELECT
                albuns.id,
                albuns.nome,
                albuns.capa,
                artistas.nome
            FROM albuns
            LEFT JOIN artistas
                ON artistas.id = albuns.artista_id
            WHERE
                albuns.capa IS NULL
                OR trim(albuns.capa) = ''
            ORDER BY albuns.id
            """

            self.log(sql.strip())

            cursor.execute(sql)

            albuns = cursor.fetchall()

            self.log("")
            self.log(
                f"📦 TOTAL ÁLBUNS SEM CAPA: {len(albuns)}"
            )

            atualizados = 0
            sem_capa = 0

            for item in albuns:

                album_id = item[0]
                album_nome = item[1]
                capa = item[2]
                artista_nome = item[3]

                self.log("")
                self.log("========================================")

                self.log(f"ID: {album_id}")

                self.log(f"ARTISTA: {artista_nome}")

                self.log(f"ALBUM: {album_nome}")

                # =============================================
                # DEEZER
                # =============================================

                capa_url = buscar_capa_deezer(
                    artista_nome,
                    album_nome
                )

                if not capa_url:

                    self.log("❌ CAPA NÃO ENCONTRADA")

                    sem_capa += 1

                    continue

                self.log(f"🖼 CAPA: {capa_url}")

                # =============================================
                # UPDATE
                # =============================================

                sql_update = """
                UPDATE albuns
                SET capa = ?
                WHERE id = ?
                """

                params = (
                    capa_url,
                    album_id
                )

                self.log("")
                self.log("SQL UPDATE:")
                self.log(sql_update.strip())

                self.log(f"PARAMS: {params}")

                cursor.execute(
                    sql_update,
                    params
                )

                conn.commit()

                atualizados += 1

                self.log("✅ CAPA SALVA")

            # =================================================
            # FINAL
            # =================================================

            conn.close()

            self.log("")
            self.log("========================================")
            self.log("FINALIZADO")
            self.log("========================================")

            self.log(
                f"✅ CAPAS ATUALIZADAS: {atualizados}"
            )

            self.log(
                f"❌ SEM CAPA: {sem_capa}"
            )

            messagebox.showinfo(
                "Finalizado",
                f"""
Capas atualizadas: {atualizados}

Sem capa: {sem_capa}
"""
            )

        except Exception as e:

            self.log("")
            self.log("========================================")
            self.log("ERRO")
            self.log("========================================")

            self.log(str(e))

            messagebox.showerror(
                "Erro",
                str(e)
            )

# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":

    root = tk.Tk()

    app = AtualizadorCapas(root)

    root.mainloop()