from pathlib import Path
from flask import session

BASE_DIR = Path(__file__).resolve().parent.parent

def header(titulo="CifrasFlix"):
    template_path = BASE_DIR / "templates" / "header.html"
    html = template_path.read_text(encoding="utf-8")
    
    if session.get("user") == "adm":
        user_html = """
        <div class="profileDropdown">
            <button class="profileDropdownBtn" onclick="toggleProfileDropdown(event)" aria-label="Menu do perfil">
                <svg class="profileAvatar" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="width: 20px; height: 20px; display: block;">
                    <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
                    <circle cx="12" cy="7" r="4"></circle>
                </svg>
            </button>
            <div class="profileDropdownContent">
                <div class="profileInfo">
                    <strong>Administrador</strong>
                    <span>Acesso Adm</span>
                </div>
                <hr class="dropdownDivider">
                <a href="/painel">Painel de Controle</a>
                <a href="/admin">Configurações</a>
                <hr class="dropdownDivider">
                <a href="/logout" class="logoutLink">Sair</a>
            </div>
        </div>
        """
        html = html.replace('<button type="button" id="loginBtn" class="loginButton">Entrar</button>', user_html)
    else:
        login_html = '<button type="button" id="loginBtn" class="loginButton" onclick="location.href=\'/login\'">Entrar</button>'
        html = html.replace('<button type="button" id="loginBtn" class="loginButton">Entrar</button>', login_html)
        
    return html.replace("{{ titulo }}", str(titulo))


