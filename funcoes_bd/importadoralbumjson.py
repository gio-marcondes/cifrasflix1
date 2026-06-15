import json
import re
import sqlite3
import unicodedata
import tkinter as tk

from tkinter import filedialog, messagebox

# =========================================================
# IMPORTADOR JSON -> SQLITE
# =========================================================

class ImportadorAlbuns:

    def __init__(self, root):

        self.root = root

        self.root.title("Importador de Discografia")
        self.root.geometry("1000x700")

        self.db_path = ""
        self.json_path = ""

        self.criar_ui()

    # =====================================================
    # UI
    # =====================================================

    def criar_ui(self):

        frame = tk.Frame(self.root)
        frame.pack(fill="x", padx=10, pady=10)

        # SQLITE
        tk.Label(frame, text="Banco SQLite").grid(row=0, column=0, sticky="w")

        self.entry_db = tk.Entry(frame, width=90)
        self.entry_db.grid(row=0, column=1, padx=5)

        tk.Button(
            frame,
            text="Selecionar",
            command=self.selecionar_db
        ).grid(row=0, column=2)

        # JSON
        tk.Label(frame, text="Arquivo JSON").grid(
            row=1,
            column=0,
            sticky="w",
            pady=(10, 0)
        )

        self.entry_json = tk.Entry(frame, width=90)
        self.entry_json.grid(row=1, column=1, padx=5, pady=(10, 0))

        tk.Button(
            frame,
            text="Selecionar",
            command=self.selecionar_json
        ).grid(row=1, column=2, pady=(10, 0))

        # BOTAO IMPORTAR
        tk.Button(
            self.root,
            text="IMPORTAR TODOS OS ÁLBUNS",
            bg="#27ae60",
            fg="white",
            font=("Arial", 12, "bold"),
            height=2,
            command=self.importar_todos
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

        self.log_text.insert(tk.END, texto + "\n")

        self.log_text.see(tk.END)

        print(texto)

        self.root.update()

    # =====================================================
    # FILE PICKERS
    # =====================================================

    def selecionar_db(self):

        path = filedialog.askopenfilename(
            title="Banco SQLite",
            filetypes=[("SQLite", "*.db *.sqlite *.sqlite3")]
        )

        if path:

            self.db_path = path

            self.entry_db.delete(0, tk.END)
            self.entry_db.insert(0, path)

    def selecionar_json(self):

        path = filedialog.askopenfilename(
            title="Arquivo JSON",
            filetypes=[("JSON", "*.json")]
        )

        if path:

            self.json_path = path

            self.entry_json.delete(0, tk.END)
            self.entry_json.insert(0, path)

    # =====================================================
    # SLUG
    # =====================================================

    def slugify(self, texto):

        if not texto:
            return ""

        texto = texto.lower()

        texto = unicodedata.normalize("NFKD", texto)
        texto = texto.encode("ascii", "ignore").decode("utf-8")

        texto = re.sub(r"[^a-z0-9]+", "-", texto)

        texto = texto.strip("-")

        return texto

    # =====================================================
    # BUSCAR / CRIAR ARTISTA
    # =====================================================

    def obter_artista(self, cursor, nome_artista):

        sql = """
        SELECT id
        FROM artistas
        WHERE lower(nome) = lower(?)
        """

        cursor.execute(sql, (nome_artista,))

        resultado = cursor.fetchone()

        if resultado:

            artista_id = resultado[0]

            self.log(f"👤 ARTISTA EXISTE -> {nome_artista} (ID {artista_id})")

            return artista_id

        slug = self.slugify(nome_artista)

        sql_insert = """
        INSERT INTO artistas (
            nome,
            slug
        )
        VALUES (?, ?)
        """

        cursor.execute(
            sql_insert,
            (
                nome_artista,
                slug
            )
        )

        artista_id = cursor.lastrowid

        self.log(f"✅ ARTISTA CRIADO -> {nome_artista} (ID {artista_id})")

        return artista_id

    # =====================================================
    # VERIFICAR ALBUM
    # =====================================================

    def album_existe(self, cursor, artista_id, nome_album):

        sql = """
        SELECT id
        FROM albuns
        WHERE artista_id = ?
        AND lower(nome) = lower(?)
        """

        cursor.execute(
            sql,
            (
                artista_id,
                nome_album
            )
        )

        resultado = cursor.fetchone()

        if resultado:

            return resultado[0]

        return None

    # =====================================================
    # VERIFICAR MUSICA
    # =====================================================

    def musica_existe(self, cursor, album_id, titulo):

        sql = """
        SELECT id
        FROM cancao
        WHERE album_id = ?
        AND lower(titulo) = lower(?)
        """

        cursor.execute(
            sql,
            (
                album_id,
                titulo
            )
        )

        resultado = cursor.fetchone()

        if resultado:

            return resultado[0]

        return None

    # =====================================================
    # IMPORTAR
    # =====================================================

    def importar_todos(self):

        if not self.db_path:

            messagebox.showerror(
                "Erro",
                "Selecione o banco SQLite."
            )

            return

        if not self.json_path:

            messagebox.showerror(
                "Erro",
                "Selecione o JSON."
            )

            return

        try:

            self.log("")
            self.log("========================================")
            self.log("ABRINDO JSON")
            self.log("========================================")

            with open(self.json_path, "r", encoding="utf-8") as f:

                dados = json.load(f)

            self.log(f"📦 TOTAL DE ÁLBUNS NO JSON: {len(dados)}")

            # =================================================
            # SQLITE
            # =================================================

            conn = sqlite3.connect(self.db_path)

            cursor = conn.cursor()

            total_albuns = 0
            total_musicas = 0
            total_ignorados = 0

            # =================================================
            # LOOP ALBUNS
            # =================================================

            for album in dados:

                try:

                    self.log("")
                    self.log("========================================")

                    nome_artista = album.get("artista", "").strip()

                    nome_album = album.get("album", "").strip()

                    ano = str(album.get("ano", "")).strip()

                    pais = album.get("pais", "").strip()

                    gravadora = album.get("gravadora", "").strip()

                    self.log(f"🎵 ÁLBUM: {nome_album}")
                    self.log(f"👤 ARTISTA: {nome_artista}")

                    # =============================================
                    # ARTISTA
                    # =============================================

                    artista_id = self.obter_artista(
                        cursor,
                        nome_artista
                    )

                    # =============================================
                    # VERIFICAR ALBUM
                    # =============================================

                    album_existente = self.album_existe(
                        cursor,
                        artista_id,
                        nome_album
                    )

                    if album_existente:

                        self.log(
                            f"⚠️ ÁLBUM JÁ EXISTE -> ID {album_existente}"
                        )

                        total_ignorados += 1

                        continue

                    # =============================================
                    # INSERIR ALBUM
                    # =============================================

                    sql_album = """
                    INSERT INTO albuns (
                        artista_id,
                        nome,
                        ano,
                        pais,
                        gravadora,
                        titulo
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    """

                    params_album = (
                        artista_id,
                        nome_album,
                        ano,
                        pais,
                        gravadora,
                        nome_album
                    )

                    self.log("")
                    self.log("SQL INSERT ALBUM:")
                    self.log(sql_album.strip())

                    self.log(f"PARAMS: {params_album}")

                    cursor.execute(
                        sql_album,
                        params_album
                    )

                    album_id = cursor.lastrowid

                    self.log(f"✅ ALBUM INSERIDO -> ID {album_id}")

                    total_albuns += 1

                    # =============================================
                    # MUSICAS
                    # =============================================

                    musicas = album.get("musicas", [])

                    self.log(
                        f"🎼 TOTAL MUSICAS: {len(musicas)}"
                    )

                    for musica in musicas:

                        titulo = musica.get("titulo", "").strip()

                        duracao = musica.get(
                            "duracao_segundos",
                            0
                        )

                        if not titulo:

                            continue

                        musica_existente = self.musica_existe(
                            cursor,
                            album_id,
                            titulo
                        )

                        if musica_existente:

                            self.log(
                                f"⚠️ MÚSICA JÁ EXISTE -> {titulo}"
                            )

                            continue

                        slug_musica = self.slugify(titulo)

                        sql_musica = """
                        INSERT INTO cancao (
                            album_id,
                            titulo,
                            duracao,
                            cancao_slug
                        )
                        VALUES (?, ?, ?, ?)
                        """

                        params_musica = (
                            album_id,
                            titulo,
                            str(duracao),
                            slug_musica
                        )

                        self.log("")
                        self.log("SQL INSERT MUSICA:")
                        self.log(sql_musica.strip())

                        self.log(
                            f"PARAMS: {params_musica}"
                        )

                        cursor.execute(
                            sql_musica,
                            params_musica
                        )

                        musica_id = cursor.lastrowid

                        self.log(
                            f"✅ MÚSICA INSERIDA -> ID {musica_id}"
                        )

                        total_musicas += 1

                    # =============================================
                    # COMMIT A CADA ALBUM
                    # =============================================

                    conn.commit()

                    self.log("💾 COMMIT OK")

                except Exception as erro_album:

                    self.log("")
                    self.log("❌ ERRO NO ÁLBUM")
                    self.log(str(erro_album))

                    conn.rollback()

            # =================================================
            # FINAL
            # =================================================

            conn.close()

            self.log("")
            self.log("========================================")
            self.log("FINALIZADO")
            self.log("========================================")

            self.log(f"✅ ÁLBUNS INSERIDOS: {total_albuns}")

            self.log(f"✅ MUSICAS INSERIDAS: {total_musicas}")

            self.log(f"⚠️ ÁLBUNS IGNORADOS: {total_ignorados}")

            messagebox.showinfo(
                "Finalizado",
                f"""
Álbuns inseridos: {total_albuns}

Músicas inseridas: {total_musicas}

Álbuns ignorados: {total_ignorados}
"""
            )

        except Exception as e:

            self.log("")
            self.log("========================================")
            self.log("ERRO GERAL")
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

    app = ImportadorAlbuns(root)

    root.mainloop()