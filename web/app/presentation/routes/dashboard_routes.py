from flask import Blueprint, render_template

from . import services

bp = Blueprint("dashboard", __name__)


@bp.get("/")
def index():
    return render_template("dashboard.html", data=services()["dashboard"].ringkasan(), aktif="dashboard")
