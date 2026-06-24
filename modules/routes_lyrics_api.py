import sqlite3
from flask import Blueprint, Response, jsonify, request
from deep_translator import GoogleTranslator
from bs4 import BeautifulSoup

from modules.config import DB
from modules.routes_lyrics import procura_letra

lyrics_api_bp = Blueprint('lyrics_api', __name__)

@lyrics_api_bp.route("/traduzir-letra", methods=["POST"])
def traduzir_letra():
    data = request.get_json()

    artista = data.get("artista")
    musica = data.get("musica")

    letra_html = procura_letra(artista, musica)

    if not letra_html:
        return jsonify({"erro": "letra não encontrada"})

    try:
        texto_puro = BeautifulSoup(letra_html, "html.parser").get_text("\n")

        traducao = GoogleTranslator(
            source="auto",
            target="pt"
        ).translate(texto_puro)

        traducao_html = "<p>" + traducao.replace("\n", "</p><p>") + "</p>"

        return jsonify({"traducao": traducao_html})

    except Exception as e:
        return jsonify({"erro": str(e)})


@lyrics_api_bp.route("/capa_album/<int:album_id>")
def capa_album(album_id):
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("""
        SELECT capa_blob
        FROM albuns
        WHERE id=?
    """, (album_id,))

    row = c.fetchone()
    conn.close()

    if not row or not row[0]:
        return "", 404

    return Response(
        row[0],
        mimetype="image/jpeg"
    )
