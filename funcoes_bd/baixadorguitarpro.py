import os
import time
import re
import random
import threading
import tkinter as tk
from tkinter import scrolledtext, messagebox

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

PASTA_DOWNLOAD = r"C:\Users\e179ti\Downloads"
# CONTROLE
pular_artista = False
lista_artistas_global = []

def atualizar_lista():

    global lista_artistas_global

    texto = entrada.get("1.0", tk.END).strip().lower()

    novos = [
        a.strip()
        for a in texto.split("\n")
        if a.strip()
    ]

    adicionados = 0

    for artista in novos:

        if artista not in lista_artistas_global:

            lista_artistas_global.append(artista)
            adicionados += 1

    log(f"🔄 Lista atualizada. {adicionados} artistas adicionados.")

def pular_artista_atual():
    global pular_artista
    pular_artista = True
    log("⏭ Artista marcado para pular...")

def artista_ja_existe(nome_artista):
    nome_artista = nome_artista.lower()

    for arquivo in os.listdir(PASTA_DOWNLOAD):
        if nome_artista in arquivo.lower():
            return True
    return False
# ---------------- UTIL ----------------

def limpar_nome(nome):
    return re.sub(r'[\\/*?:"<>|]', "", nome)


def log(msg):
    log_box.insert(tk.END, msg + "\n")
    log_box.see(tk.END)
    root.update()


# ---------------- PEGAR LINKS ----------------

def pegar_links_guitarpro(driver, link_artista):

    todos_links = []
    page = 1

    while True:

        url = f"{link_artista}&page={page}"
        log(f"Página: {url}")

        driver.get(url)
        time.sleep(random.uniform(2,3))

        url_atual = driver.current_url

        if page > 1 and f"page={page}" not in url_atual:
            break

        links = driver.find_elements(By.CSS_SELECTOR, "a[href*='guitar-pro-']")

        if not links:
            break

        for link in links:
            
            href = link.get_attribute("href")
            if href and "guitar-pro-" in href:
                todos_links.append(href)

        page += 1

    return list(dict.fromkeys(todos_links))


# ---------------- MODO ÚNICO (continua depois) ----------------

def modo_unico(driver, artista_inicio):

    letras = list("abcdefghijklmnopqrstuvwxyz")

    iniciar = artista_inicio == ""

    if artista_inicio:
        primeira = artista_inicio[0]
        if primeira in letras:
            letras = letras[letras.index(primeira):]

    primeiro_acesso = True
    primeiro_download = True

    for letra in letras:

        pagina = 0

        while True:

            if pagina == 0:
                url = f"https://www.ultimate-guitar.com/bands/{letra}.htm"
            else:
                url = f"https://www.ultimate-guitar.com/bands/{letra}{pagina}.htm"

            log(f"Abrindo: {url}")

            driver.get(url)

            if primeiro_acesso:
                log("Resolva login/captcha...")
                time.sleep(9)
                primeiro_acesso = False
            else:
                time.sleep(4)

            artistas = driver.find_elements(By.CSS_SELECTOR, "a[href^='/artist/']")

            lista_artistas = []

            for a in artistas:
                href = a.get_attribute("href")
                nome = a.text.strip()

                if href and nome:
                    if "?filter=" not in href:
                        href = href + "?filter=guitar_pro"
                    lista_artistas.append((nome, href))

            lista_artistas = list(dict.fromkeys(lista_artistas))

            if not lista_artistas:
                break

            for nome_artista, link_artista in lista_artistas:

                nome_lower = nome_artista.lower()

                if not iniciar:
                    if artista_inicio in nome_lower:
                        log(f"▶ Começando em: {nome_artista}")
                        iniciar = True
                    else:
                        continue

                log(f"Artista: {nome_artista}")

                try:
                    links = pegar_links_guitarpro(driver, link_artista)
                    log(f"Tabs: {len(links)}")

                    for link in links:

                        if pular_artista:
                            log("⏭ Pulando artista...")
                            pular_artista = False
                            break
                        
                        log(f"Baixando: {link}")
                        driver.get(link)

                        if primeiro_download:
                            time.sleep(4)
                            primeiro_download = False
                        else:
                            time.sleep(3)

                        try:
                            botao = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
                            botao.click()
                            log("✔ Download")
                            time.sleep(2)
                        except:
                            log("❌ Botão não encontrado")

                except Exception as e:
                    log(f"Erro: {e}")

            pagina += 1


# ---------------- MODO LISTA ----------------

def modo_lista(driver, artistas):
    global pular_artista
    global lista_artistas_global

    primeiro_download = True

    indice = 0
    while indice < len(lista_artistas_global):

        artista_inicio = lista_artistas_global[indice]
        indice += 1

        log(f"\n🎯 Buscando: {artista_inicio}")

        letras = list("abcdefghijklmnopqrstuvwxyz")

        primeira = artista_inicio[0]

        if primeira in letras:
            letras = letras[letras.index(primeira):]

        primeiro_acesso = True
        encontrado = False

        for letra in letras:

            if pular_artista:
                log(f"⏭ Pulando artista: {artista_inicio}")
                pular_artista = False
                encontrado = True
                break

            pagina = 0

            while True:

                if pular_artista:
                    log(f"⏭ Pulando artista: {artista_inicio}")
                    pular_artista = False
                    encontrado = True
                    break

                if pagina == 0:
                    url = f"https://www.ultimate-guitar.com/bands/{letra}.htm"
                else:
                    url = f"https://www.ultimate-guitar.com/bands/{letra}{pagina}.htm"

                log(f"Abrindo: {url}")

                driver.get(url)

                if primeiro_acesso:
                    log("Resolva captcha...")
                    time.sleep(9)
                    primeiro_acesso = False
                else:
                    time.sleep(4)

                artistas_pg = driver.find_elements(
                    By.CSS_SELECTOR,
                    "a[href^='/artist/']"
                )

                lista = []

                for a in artistas_pg:

                    href = a.get_attribute("href")
                    nome = a.text.strip()

                    if href and nome:

                        if "?filter=" not in href:
                            href = href + "?filter=guitar_pro"

                        lista.append((nome, href))

                lista = list(dict.fromkeys(lista))

                if not lista:
                    break

                for nome_artista, link_artista in lista:

                    if pular_artista:
                        log(f"⏭ Pulando artista: {artista_inicio}")
                        pular_artista = False
                        encontrado = True
                        break

                    if artista_inicio in nome_artista.lower():

                        log(f"▶ Encontrado: {nome_artista}")

                        try:

                            links = pegar_links_guitarpro(
                                driver,
                                link_artista
                            )

                            for link in links:

                                if pular_artista:
                                    log(f"⏭ Pulando artista: {artista_inicio}")
                                    pular_artista = False
                                    encontrado = True
                                    break

                                driver.get(link)

                                if primeiro_download:
                                    time.sleep(4)
                                    primeiro_download = False
                                else:
                                    time.sleep(3)

                                try:

                                    botao = driver.find_element(
                                        By.CSS_SELECTOR,
                                        "button[type='submit']"
                                    )

                                    botao.click()

                                    log("✔ Download")

                                    time.sleep(2)

                                except:
                                    log("❌ Falha download")

                        except Exception as e:
                            log(f"Erro: {e}")

                        encontrado = True
                        break

                if encontrado:
                    break

                pagina += 1

            if encontrado:
                break


# ---------------- THREAD ----------------

def iniciar():
    global lista_artistas_global
    texto = entrada.get("1.0", tk.END).strip().lower()

    if not texto:
        messagebox.showerror("Erro", "Digite artista")
        return

    artistas = [a.strip() for a in texto.split("\n") if a.strip()]

    # 🔥 FILTRA AQUI
    artistas_filtrados = []
    removidos = []

    for artista in artistas:
        if artista_ja_existe(artista):
            removidos.append(artista)
        else:
            artistas_filtrados.append(artista)

    # Atualiza a caixa de texto (remove os já baixados)
    entrada.delete("1.0", tk.END)
    entrada.insert(tk.END, "\n".join(artistas_filtrados))

    log(f"⏭ Removidos ({len(removidos)}): {', '.join(removidos[:5])}")
    log(f"🚀 Restantes: {len(artistas_filtrados)}")

    artistas = artistas_filtrados
    lista_artistas_global = artistas

    def run():

        options = Options()
        options = Options()
        options.add_argument("--start-maximized")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)

        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=options
        )
        try:
            if len(artistas) == 1:
                log("🚀 Modo contínuo")
                modo_unico(driver, artistas[0])
            else:
                log("🚀 Modo lista")
                modo_lista(driver, artistas)
        finally:
            driver.quit()
            log("\n✅ Finalizado")

    threading.Thread(target=run).start()


# ---------------- UI ----------------

root = tk.Tk()
root.title("Ultimate Guitar Downloader")
root.geometry("700x600")

tk.Label(root, text="Digite artistas (1 por linha):").pack(pady=5)

entrada = scrolledtext.ScrolledText(root, height=10)
entrada.pack(fill="x", padx=10)

tk.Button(root, text="INICIAR", command=iniciar, bg="green", fg="white").pack(pady=10)
tk.Button(
    root,
    text="PULAR ARTISTA",
    command=pular_artista_atual,
    bg="orange"
).pack(pady=5)
tk.Button(
    root,
    text="ATUALIZAR LISTA",
    command=atualizar_lista,
    bg="blue",
    fg="white"
).pack(pady=5)

log_box = scrolledtext.ScrolledText(root)
log_box.pack(fill="both", expand=True, padx=10, pady=10)

root.mainloop()