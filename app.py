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

# Inicializa o banco de dados e cria tabelas se não existirem
from modules.config import init_db
init_db()

from modules.routes_main import main_bp
from modules.routes_admin import admin_bp
from modules.routes_albums import albums_bp
from modules.routes_lyrics import lyrics_bp
from modules.routes_lyrics_api import lyrics_api_bp
from modules.routes_master import master_bp
from modules.routes_master_analysis import master_analysis_bp
from modules.routes_misc import misc_bp
from modules.routes_player import player_bp
from modules.routes_separador import separador_bp
from modules.routes_treinar import treinar_bp
from modules.routes_daw import daw_bp
from modules.routes_conversor import conversor_bp
from modules.routes_afinador import afinador_bp
from modules.routes_jamstudio import jamstudio_bp
from modules.routes_flixplay import flixplay_bp

app.register_blueprint(main_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(albums_bp)
app.register_blueprint(lyrics_bp)
app.register_blueprint(lyrics_api_bp)
app.register_blueprint(master_bp)
app.register_blueprint(master_analysis_bp)
app.register_blueprint(misc_bp)
app.register_blueprint(player_bp)
app.register_blueprint(separador_bp)
app.register_blueprint(treinar_bp)
app.register_blueprint(daw_bp)
app.register_blueprint(conversor_bp)
app.register_blueprint(afinador_bp)
app.register_blueprint(jamstudio_bp)
app.register_blueprint(flixplay_bp)

if __name__ == "__main__":
    app.run(debug=True)
