from flask import Blueprint, render_template

from modules.layout import header

daw_bp = Blueprint('daw', __name__)

@daw_bp.route("/daw")
def daw_home():
    # Render the daw.html template
    return render_template("daw.html")
