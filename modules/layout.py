from pathlib import Path
from flask import session

BASE_DIR = Path(__file__).resolve().parent.parent

def header(titulo="CifrasFlix"):
    template_path = BASE_DIR / "templates" / "header.html"
    html = template_path.read_text(encoding="utf-8")
    
    if session.get("user") == "adm":
        user_html = """
        <a href="/painel" class="loginButton" style="background:#ff7a00; color:#fff; text-decoration:none; display:inline-flex; align-items:center; justify-content:center; padding: 8px 16px; border-radius: 8px;">Painel (adm)</a>
        <a href="/logout" style="color:#ef4444; font-size:13px; margin-left:10px; text-decoration:none; font-weight:bold; display: inline-block; vertical-align: middle;">Sair</a>
        """
        html = html.replace('<button type="button" id="loginBtn" class="loginButton">Entrar</button>', user_html)
    else:
        login_html = '<button type="button" id="loginBtn" class="loginButton" onclick="location.href=\'/login\'">Entrar</button>'
        html = html.replace('<button type="button" id="loginBtn" class="loginButton">Entrar</button>', login_html)
        
    return html.replace("{{ titulo }}", str(titulo))


