from flask import Flask
from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent
app = Flask(__name__)
app.secret_key = "ttx15_secret"

# Configurações de pastas
UPLOAD_FOLDER = "static/capas"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# Em vez de exec(), o ideal é importar Blueprints. 
# Exemplo de como ficaria após converter routes_main.py em um Blueprint:
# from modules.routes_main import main_bp
# app.register_blueprint(main_bp)

# Mantendo seu carregamento dinâmico mas de forma um pouco mais controlada
# enquanto você não refatora para Blueprints:
def load_modules(app):
    MODULE_DIR = Path(__file__).parent / "modules"
    # Nota: A ordem importa se houver dependências de globals
    for module_file in MODULE_DIR.glob("*.py"):
        with open(module_file, "r", encoding="utf-8") as f:
            exec(f.read(), globals())

load_modules(app)

if __name__ == "__main__":
    app.run(debug=True)