import os
import re
import json
import time
import tkinter as tk
import unicodedata

from tkinter import filedialog, messagebox, ttk

# ==========================================
# SELENIUM
# ==========================================

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait

from difflib import SequenceMatcher
import threading
ARQUIVO_PULADOS = (
    r"C:\Users\e179ti\Documents\artistaspuladosletra.txt"
)
pular_artista = False

def musica_ja_existe(
    pasta_letras,
    artista,
    titulo
):

    nome_base = nome_seguro(
        f"{artista} - {titulo}"
    )

    caminho = os.path.join(
        pasta_letras,
        nome_base + ".txt"
    )

    return os.path.exists(
        caminho
    )

def carregar_artistas_pulados():

    if not os.path.exists(
        ARQUIVO_PULADOS
    ):
        return set()

    with open(
        ARQUIVO_PULADOS,
        "r",
        encoding="utf-8"
    ) as f:

        return {
            linha.strip().lower()
            for linha in f
            if linha.strip()
        }
    
def salvar_artista_pulado(
    artista
):

    artista = artista.strip()

    existentes = carregar_artistas_pulados()

    if artista.lower() in existentes:
        return

    with open(
        ARQUIVO_PULADOS,
        "a",
        encoding="utf-8"
    ) as f:

        f.write(
            artista + "\n"
        )
            
# ==========================================
# SLUG LETRAS
# ==========================================

def slug_letras(texto):

    texto = texto.lower().strip()

    texto = unicodedata.normalize(
        "NFKD",
        texto
    )

    texto = texto.encode(
        "ascii",
        "ignore"
    ).decode("utf-8")

    texto = re.sub(r"[^\w\s-]", "", texto)
    texto = re.sub(r"\s+", "-", texto)

    return texto.strip("-")


# ==========================================
# NOME SEGURO
# ==========================================

def nome_seguro(nome):

    nome = re.sub(
        r'[\\/*?:"<>|]',
        "",
        nome
    )

    return nome.strip()


# ==========================================
# LIMPAR HTML
# ==========================================

def limpar_html(texto):

    if not texto:
        return ""

    texto = texto.replace("<br>", "\n")
    texto = texto.replace("<br/>", "\n")
    texto = texto.replace("<br />", "\n")

    texto = re.sub(
        r"<[^>]+>",
        "",
        texto
    )

    return texto.strip()


# ==========================================
# GERAR NOME ÚNICO
# ==========================================

def gerar_nome_unico(pasta, nome_base):

    caminho = os.path.join(
        pasta,
        nome_base + ".txt"
    )

    if not os.path.exists(caminho):
        return caminho

    contador = 2

    while True:

        novo = os.path.join(
            pasta,
            f"{nome_base} ({contador}).txt"
        )

        if not os.path.exists(novo):
            return novo

        contador += 1


# ==========================================
# BUSCAR LETRA
# ==========================================

def buscar_letra_html(artista1: str, musica1: str):

    url = (
        f"https://www.letras.mus.br/"
        f"{slug_letras(artista1)}/"
        f"{slug_letras(musica1)}/print.html?translation=pt"
    )

    driver = None

    try:

        options = Options()

        options.add_argument("--headless=new")

        options.add_argument(
            "--disable-blink-features=AutomationControlled"
        )

        options.add_argument(
            "--user-agent=Mozilla/5.0"
        )

        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")

        driver = webdriver.Chrome(
            options=options
        )

        driver.get(url)

        WebDriverWait(driver, 30).until(
            lambda d: d.execute_script(
                "return document.readyState"
            ) == "complete"
        )

        time.sleep(2)

        # ==========================================
        # VALIDAR TITULO
        # ==========================================

        try:

            titulo_site = driver.find_element(
                By.CSS_SELECTOR,
                "div.page-header h1"
            ).text.strip()

        except:

            print("❌ Não encontrou título")

            return None, None, None

        esperado = slug_letras(musica1)

        titulo_normalizado = slug_letras(
            titulo_site
        )

        porcentagem = (
            SequenceMatcher(
                None,
                esperado,
                titulo_normalizado
            ).ratio() * 100
        )

        print(
            f"Compatibilidade: "
            f"{porcentagem:.1f}%"
        )

        # ==========================================
        # REJEITA MUSICA ERRADA
        # ==========================================

        if porcentagem < 54:

            print("❌ Música incompatível")
            print("Buscada   :", musica1)
            print("Encontrada:", titulo_site)

            return None, None, None

        # ==========================================
        # PEGA CONTAINERS
        # ==========================================

        containers = driver.find_elements(
            By.CSS_SELECTOR,
            "div.page-container"
        )

        if not containers:
            return None, None, None

        original_parts = []
        traducao_parts = []

        titulo_traduzido = None

        # ==========================================
        # LOOP
        # ==========================================
       
        for i, div in enumerate(containers):

            try:

                h3 = div.find_element(
                    By.TAG_NAME,
                    "h3"
                ).text.strip()

            except:

                h3 = None

            linhas = div.text.strip().splitlines()

            if h3 and linhas and linhas[0] == h3:
                linhas = linhas[1:]

            html_parte = (
                "<p>"
                + (h3 or "")
                + "</p>\n"
                + "<br>".join(linhas)
            )

            if i % 2 == 0:
                original_parts.append(html_parte)
            else:
                traducao_parts.append(html_parte)

        # ==========================================
        # TITULO TRADUZIDO
        # ==========================================

        if len(containers) > 1:

            try:

                titulo_traduzido = containers[1].find_element(
                    By.TAG_NAME,
                    "h3"
                ).text.strip()

            except:

                titulo_traduzido = (
                    musica1 + " (Tradução)"
                )

        letra_html = (
            "\n".join(original_parts)
            if original_parts
            else None
        )

        traducao_html = (
            "\n".join(traducao_parts)
            if traducao_parts
            else None
        )

        return (
            letra_html,
            traducao_html,
            titulo_traduzido
        )

    except Exception as e:

        print("Erro Selenium:", e)

        return None, None, None

    finally:

        if driver:
            driver.quit()



# ==========================================
# PULAR ARTISTA
# ==========================================

def pular_artista_atual():
    global pular_artista
    pular_artista = True


# ==========================================
# LOG DE ALBUNS BAIXADOS
# ==========================================

def caminho_log_albuns(pasta_letras):

    return os.path.join(
        pasta_letras,
        "log-letrasbaixadas.log"
    )


def album_ja_baixado(
    pasta_letras,
    artista,
    album
):

    log_path = caminho_log_albuns(
        pasta_letras
    )

    if not os.path.exists(log_path):
        return False

    chave = (
        f"{artista.strip().lower()}|"
        f"{album.strip().lower()}"
    )

    try:

        with open(
            log_path,
            "r",
            encoding="utf-8"
        ) as f:

            for linha in f:

                if linha.strip().lower() == chave:
                    return True

    except:
        pass

    return False


def marcar_album_baixado(
    pasta_letras,
    artista,
    album
):

    with open(
        caminho_log_albuns(pasta_letras),
        "a",
        encoding="utf-8"
    ) as f:

        f.write(
            f"{artista}|{album}\n"
        )


# ==========================================
# PROCESSAR JSON
# ==========================================

def processar():

    json_path = entry_json.get().strip()

    pasta_letras = entry_pasta.get().strip()

    if not os.path.exists(json_path):

        messagebox.showerror(
            "Erro",
            "JSON não encontrado"
        )

        return

    os.makedirs(
        pasta_letras,
        exist_ok=True
    )

    # ==========================================
    # ABRIR JSON
    # ==========================================

    with open(
        json_path,
        "r",
        encoding="utf-8"
    ) as f:

        dados = json.load(f)

    total = 0
    sucesso = 0
    artistas_pulados = (
        carregar_artistas_pulados()
    )
    # ==========================================
    # LOOP ALBUNS
    # ==========================================
    
    for album in dados:
        artista = album.get(
            "artista",
            ""
        ).strip()

        if artista.lower() in artistas_pulados:

            print(
                f"⏭️ Ignorando artista: {artista}"
            )

            continue
        global pular_artista

        pular_artista = False

        falhas_artista = 0

        nome_album = album.get(
            "album",
            ""
        ).strip()

        artista = album.get(
            "artista",
            ""
        ).strip()

        if album_ja_baixado(
            pasta_letras,
            artista,
            nome_album
        ):

            print(
                f"⏭️ Álbum já baixado: {artista} - {nome_album}"
            )

            continue

        musicas = album.get(
            "musicas",
            []
        )

        print("\n" + "=" * 60)
        print(f"📀 ÁLBUM: {artista} - {nome_album}")
        print(f"🎵 Faixas: {len(musicas)}")
        print("=" * 60)

        album_concluido = True

        for musica in musicas:
            titulo = musica.get(
                "titulo",
                ""
            ).strip()

            if musica_ja_existe(
                pasta_letras,
                artista,
                titulo
            ):

                print(
                    f"⏭️ TXT já existe: "
                    f"{artista} - {titulo}"
                )

                continue
            if pular_artista:

                print(
                    f"⏭️ Artista pulado: {artista}"
                )

                break

            titulo = musica.get(
                "titulo",
                ""
            ).strip()

            total += 1

            status_var.set(
                f"Buscando: {artista} - {titulo}"
            )

            root.update()

            print(
                "\n================================="
            )

            print(
                f"🎵 {artista} - {titulo}"
            )

            letra_html, traducao_html, titulo_traduzido = buscar_letra_html(
                artista,
                titulo
            )

            # ==========================================
            # NÃO ENCONTROU
            # ==========================================

            if not letra_html:

                falhas_artista += 1

                print(
                    f"❌ Não encontrou ({falhas_artista}/3)"
                )

                if falhas_artista >= 3:

                    print(
                        f"⏭️ Pulando artista: "
                        f"{artista}"
                    )

                    artistas_pulados.add(
                        artista.lower()
                    )

                    salvar_artista_pulado(
                        artista
                    )

                    album_concluido = False

                    break

                continue

            # ==========================================
            # TXT
            # ==========================================

            letra_txt = limpar_html(
                letra_html
            )

            traducao_txt = limpar_html(
                traducao_html
            )

            conteudo = f"""
LETRA
===========

{letra_txt}
"""

            if traducao_txt:

                conteudo += f"""


TRADUÇÃO
===========

{traducao_txt}
"""

            # ==========================================
            # SALVAR
            # ==========================================

            nome_base = nome_seguro(
                f"{artista} - {titulo}"
            )

            caminho = gerar_nome_unico(
                pasta_letras,
                nome_base
            )

            with open(
                caminho,
                "w",
                encoding="utf-8"
            ) as f:

                f.write(
                    conteudo.strip()
                )

            print(
                f"✅ Salvo: {caminho}"
            )

            sucesso += 1

            falhas_artista = 0

            time.sleep(1)

        if album_concluido and not pular_artista:

            marcar_album_baixado(
                pasta_letras,
                artista,
                nome_album
            )

            print(
                f"✅ Álbum concluído: {artista} - {nome_album}"
            )

    status_var.set(
        f"Finalizado! {sucesso}/{total}"
    )

    messagebox.showinfo(
        "Concluído",
        f"Finalizado!\n\n"
        f"Sucesso: {sucesso}\n"
        f"Total: {total}"
    )


# ==========================================
# ESCOLHER JSON
# ==========================================

def escolher_json():

    caminho = filedialog.askopenfilename(
        title="Escolha o JSON",
        filetypes=[
            ("JSON", "*.json")
        ]
    )

    if caminho:

        entry_json.delete(0, tk.END)

        entry_json.insert(
            0,
            caminho
        )


# ==========================================
# ESCOLHER PASTA
# ==========================================

def escolher_pasta():

    caminho = filedialog.askdirectory(
        title="Escolha a pasta"
    )

    if caminho:

        entry_pasta.delete(0, tk.END)

        entry_pasta.insert(
            0,
            caminho
        )


# ==========================================
# UI
# ==========================================

root = tk.Tk()

root.title(
    "Downloader de Letras"
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

# ==========================================
# JSON
# ==========================================

ttk.Label(
    frame,
    text="Arquivo JSON:"
).pack(anchor="w")

entry_json = ttk.Entry(
    frame,
    width=80
)

entry_json.pack(
    fill="x"
)

ttk.Button(
    frame,
    text="Escolher JSON",
    command=escolher_json
).pack(
    anchor="w",
    pady=5
)

# ==========================================
# PASTA
# ==========================================

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

# ==========================================
# BOTÃO
# ==========================================

ttk.Button(
    frame,
    text="INICIAR DOWNLOAD",
    command=lambda: threading.Thread(target=processar, daemon=True).start()
).pack(
    pady=12
)

ttk.Button(
    frame,
    text="PULAR ARTISTA",
    command=pular_artista_atual
).pack(
    pady=3
)

# ==========================================
# STATUS
# ==========================================

status_var = tk.StringVar()

status_var.set(
    "Aguardando..."
)

ttk.Label(
    frame,
    textvariable=status_var
).pack()

root.mainloop()