"""Presentation tier: blueprint Flask. Route hanya memanggil service, tidak menyentuh database."""
from urllib.parse import urlsplit

from flask import abort, current_app, request


def services():
    return current_app.extensions["services"]


def same_origin():
    """Tolak POST dari situs lain (perlindungan CSRF sederhana untuk aplikasi lokal)."""
    origin = request.headers.get("Origin") or request.headers.get("Referer")
    if origin and urlsplit(origin).netloc != request.host:
        abort(403)
