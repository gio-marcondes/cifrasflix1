import os
import re
import sqlite3
import tkinter as tk
import unicodedata

from tkinter import filedialog, ttk, messagebox

LOG_FILE = "C:/Users/e179ti/Documents/log_letrassalvasnobd.log"
# =========================================================
# NORMALIZAR
# =========================================================

def carregar_log():
    if not os.path.exists(LOG_FILE):
        return set()

    with open(LOG_FILE, "r", encoding="utf-8") as f:
        return set(
            linha.strip()
            for linha in f
            if linha.strip()
        )


def salvar_no_log(chave):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(chave + "\n")


def normalizar(texto):

    if not texto:
        return ""

    texto = texto.lower().strip()

    texto = unicodedata.normalize(
        "NFKD",
        texto
    )

    texto = texto.encode(
        "ascii",
        "ignore"
    ).decode("utf-8")

    texto = re.sub(
        r"[^\w\s-]",
        "",
        texto
    )

    texto = re.sub(
        r"\s+",
        " ",
        texto
    )

    return texto.strip()


# =========================================================
# SLUG
# =========================================================

def slug(texto):

    texto = normalizar(texto)

    texto = texto.replace(
        " ",
        "-"
    )

    return texto
# =========================================================
# REMOVER (2), (3), (4)...
# =========================================================

def remover_sufixo_duplicado(nome):

    return re.sub(
        r"\s+\(\d+\)$",
        "",
        nome
    ).strip()

# =========================================================
# EXTRAIR LETRA / TRADUÇÃO
# =========================================================

# =========================================================
# EXTRAIR LETRA / TRADUÇÃO
# =========================================================

# =========================================================
# TEXTO -> HTML
# =========================================================

def texto_para_html(texto):

    linhas = texto.splitlines()

    html = []

    for linha in linhas:

        if linha.strip() == "":
            html.append("<br>")
        else:
            html.append(linha + "<br>")

    return "".join(html).strip()


# =========================================================
# EXTRAIR LETRA / TRADUÇÃO
# =========================================================

def extrair_blocos(texto):

    letra_original = None
    letra_traduzida = None

    titulo_original = None
    titulo_traduzido = None

    # =====================================================
    # SPLIT
    # =====================================================

    partes = texto.split(
        "TRADUÇÃO\n===========",
        1
    )

    # =====================================================
    # LETRA
    # =====================================================

    parte_letra = partes[0]

    parte_letra = parte_letra.replace(
        "LETRA\n===========",
        "",
        1
    ).lstrip()

    linhas = parte_letra.splitlines()

    while linhas and not linhas[0].strip():
        linhas.pop(0)

    if linhas:

        titulo_original = linhas[0].strip()

        corpo_original = "\n".join(
            linhas[1:]
        ).lstrip()

        letra_original = (
            f"<p>{titulo_original}</p>\n"
            + texto_para_html(corpo_original)
        )

    # =====================================================
    # TRADUÇÃO
    # =====================================================

    if len(partes) > 1:

        parte_traducao = partes[1].lstrip()

        linhas_trad = parte_traducao.splitlines()

        while linhas_trad and not linhas_trad[0].strip():
            linhas_trad.pop(0)

        if linhas_trad:

            titulo_traduzido = linhas_trad[0].strip()

            corpo_trad = "\n".join(
                linhas_trad[1:]
            ).lstrip()

            letra_traduzida = (
                f"<p>{titulo_traduzido}</p>\n"
                + texto_para_html(corpo_trad)
            )

    return (
        letra_original,
        letra_traduzida,
        titulo_original,
        titulo_traduzido
    )


# =========================================================
# ENCONTRAR MÚSICA NO BD
# =========================================================

def encontrar_cancao(
    conn,
    artista_nome,
    musica_nome
):

    cursor = conn.cursor()

    musica_limpa = remover_sufixo_duplicado(
        musica_nome
    )

    musica_slug = slug(
        musica_limpa
    )

    # ===================================
    # TENTA PELO SLUG
    # ===================================

    cursor.execute(
        """
        SELECT cancao.id
        FROM cancao
        JOIN albuns
            ON cancao.album_id = albuns.id
        JOIN artistas
            ON albuns.artista_id = artistas.id
        WHERE
            lower(artistas.nome)=lower(?)
        AND
            lower(cancao.cancao_slug)=lower(?)
        LIMIT 1
        """,
        (
            artista_nome,
            musica_slug
        )
    )

    row = cursor.fetchone()

    if row:
        return row[0]

    # ===================================
    # FALLBACK PELO TÍTULO
    # ===================================

    cursor.execute(
        """
        SELECT cancao.id
        FROM cancao
        JOIN albuns
            ON cancao.album_id = albuns.id
        JOIN artistas
            ON albuns.artista_id = artistas.id
        WHERE
            lower(artistas.nome)=lower(?)
        AND
            lower(cancao.titulo)=lower(?)
        LIMIT 1
        """,
        (
            artista_nome,
            musica_limpa
        )
    )

    row = cursor.fetchone()

    if row:
        return row[0]

    return None


# =========================================================
# SALVAR LETRA
# =========================================================

def salvar_letra():

    pasta = entry_pasta.get().strip()
    db_path = entry_db.get().strip()

    if not os.path.exists(pasta):

        messagebox.showerror(
            "Erro",
            "Pasta não encontrada"
        )

        return

    if not os.path.exists(db_path):

        messagebox.showerror(
            "Erro",
            "Banco não encontrado"
        )

        return

    arquivos = [
        arq
        for arq in os.listdir(pasta)
        if arq.lower().endswith(".txt")
    ]

    if not arquivos:

        messagebox.showwarning(
            "Aviso",
            "Nenhum TXT encontrado"
        )

        return

    conn = sqlite3.connect(db_path)
    log_processados = carregar_log()
    total = 0
    sucesso = 0

    for arquivo in arquivos:

        total += 1

        caminho = os.path.join(
            pasta,
            arquivo
        )

        nome = os.path.splitext(
            arquivo
        )[0]

        # =================================================
        # ARTISTA - MÚSICA
        # =================================================

        if " - " not in nome:

            print(
                f"❌ Nome inválido: {arquivo}"
            )

            continue

        artista_nome, musica_nome = nome.split(
            " - ",
            1
        )

        artista_nome = artista_nome.strip()
        musica_key = f"{slug(artista_nome)}::{slug(musica_nome)}"
        musica_nome = remover_sufixo_duplicado(
            musica_nome.strip()
        )

        status_var.set(
            f"Processando: {arquivo}"
        )

        root.update()

        print(
            "\n=================================="
        )

        print(
            f"🎵 {artista_nome} - {musica_nome}"
        )

        # =================================================
        # LER TXT
        # =================================================

        try:

            with open(
                caminho,
                "r",
                encoding="utf-8"
            ) as f:

                conteudo = f.read()

        except Exception as e:

            print("❌ Erro lendo:", e)

            continue

        # =================================================
        # EXTRAIR
        # =================================================

        (
            letra_original,
            letra_traduzida,
            titulo_original,
            titulo_traduzido
        ) = extrair_blocos(conteudo)

        print(
            "Título original:",
            titulo_original
        )

        print(
            "Título traduzido:",
            titulo_traduzido
        )

        # =================================================
        # LOCALIZAR CANÇÃO
        # =================================================

        cancao_id = encontrar_cancao(
            conn,
            artista_nome,
            musica_nome
        )

        if not cancao_id:

            print(
                "❌ Música não encontrada no BD"
            )

            continue



        # =================================================
        # JÁ POSSUI LETRA?
        # =================================================

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT letra_original
            FROM cancao
            WHERE id = ?
            """,
            (cancao_id,)
        )

        row = cursor.fetchone()

        if (
            row
            and row[0]
            and str(row[0]).strip()
        ):
            print(
                "⏭️ Letra já existe no BD"
            )

            continue
        # =================================================
        # UPDATE
        # =================================================

        try:

            cursor = conn.cursor()

            cursor.execute(
                """
                UPDATE cancao
                SET
                    letra_original = ?,
                    letra_traduzida = ?,
                    titulo_traduzido = ?,
                    cancao_slug = ?
                WHERE id = ?
                """,
                (
                    letra_original.strip(),
                    letra_traduzida.strip() if letra_traduzida else None,
                    titulo_traduzido.strip() if titulo_traduzido else None,
                    slug(musica_nome),
                    cancao_id
                )
            )

            conn.commit()

            sucesso += 1
            salvar_no_log(musica_key)
            log_processados.add(musica_key)
            print(
                "✅ Salvo no banco"
            )

        except Exception as e:

            print(
                "❌ Erro ao salvar:",
                e
            )

    conn.close()

    status_var.set(
        f"Finalizado! {sucesso}/{total}"
    )

    messagebox.showinfo(
        "Concluído",
        f"""
Finalizado!

Total: {total}
Sucesso: {sucesso}
"""
    )


# =========================================================
# ESCOLHER PASTA
# =========================================================

def escolher_pasta():

    caminho = filedialog.askdirectory(
        title="Escolha a pasta"
    )

    if caminho:

        entry_pasta.delete(
            0,
            tk.END
        )

        entry_pasta.insert(
            0,
            caminho
        )


# =========================================================
# ESCOLHER DB
# =========================================================

def escolher_db():

    caminho = filedialog.askopenfilename(
        title="Escolha o banco",
        filetypes=[
            (
                "SQLite",
                "*.db *.sqlite *.sqlite3"
            )
        ]
    )

    if caminho:

        entry_db.delete(
            0,
            tk.END
        )

        entry_db.insert(
            0,
            caminho
        )


# =========================================================
# UI
# =========================================================

root = tk.Tk()

root.title(
    "Importador de Letras"
)

root.geometry("700x230")

frame = ttk.Frame(
    root,
    padding=15
)

frame.pack(
    fill="both",
    expand=True
)

# =========================================================
# PASTA
# =========================================================

ttk.Label(
    frame,
    text="Pasta das letras:"
).pack(anchor="w")

entry_pasta = ttk.Entry(
    frame,
    width=80
)

entry_pasta.pack(
    fill="x"
)

ttk.Button(
    frame,
    text="Escolher Pasta",
    command=escolher_pasta
).pack(
    anchor="w",
    pady=5
)

# =========================================================
# DB
# =========================================================

ttk.Label(
    frame,
    text="Banco SQLite:"
).pack(anchor="w")

entry_db = ttk.Entry(
    frame,
    width=80
)

entry_db.pack(
    fill="x"
)

ttk.Button(
    frame,
    text="Escolher Banco",
    command=escolher_db
).pack(
    anchor="w",
    pady=5
)

# =========================================================
# BOTÃO
# =========================================================

ttk.Button(
    frame,
    text="IMPORTAR LETRAS",
    command=salvar_letra
).pack(
    pady=15
)

# =========================================================
# STATUS
# =========================================================

status_var = tk.StringVar()

status_var.set(
    "Aguardando..."
)

ttk.Label(
    frame,
    textvariable=status_var
).pack()

root.mainloop()