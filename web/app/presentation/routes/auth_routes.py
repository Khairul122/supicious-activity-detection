import secrets
import time

from flask import (Blueprint, Response, current_app, flash, g, redirect, render_template, request, send_from_directory,
                   session, url_for)

from ...business.services.auth_service import AkunTidakValid
from ..security import alamat_aman
from . import services

bp = Blueprint("auth", __name__)


def _mulai_sesi(akun, tetap_masuk):
    """Session baru setelah masuk (mencegah session fixation)."""
    session.clear()
    session.permanent = bool(tetap_masuk)
    session.update(uid=akun["id"], versi=akun["versi_sesi"], aktif=time.time(), csrf=secrets.token_urlsafe(32))


def _bot(form):
    """Kolom jebakan tersembunyi: manusia tidak melihatnya, bot pengisi formulir biasanya mengisinya."""
    return bool(form.get("situs_web"))


@bp.route("/masuk", methods=["GET", "POST"])
def masuk():
    auth = services()["auth"]
    if auth.perlu_pengaturan_awal():
        return redirect(url_for("auth.pengaturan_awal"))
    lanjut = alamat_aman(request.values.get("lanjut"), url_for("dashboard.index"))
    if request.method == "GET":
        if "uid" in session and auth.pengguna_sesi(session["uid"], session.get("versi")):
            return redirect(lanjut)
        pesan = session.pop("pesan_keluar", None)
        if pesan:
            flash(pesan, "info")
        return render_template("masuk.html", lanjut=lanjut, nama_pengguna="")
    ip = request.remote_addr or "-"
    nama = request.form.get("nama_pengguna", "")
    batas = current_app.extensions["batas_masuk"]
    if not batas.izinkan(ip):
        menit = max(1, round(batas.tunggu(ip) / 60))
        flash(f"Terlalu banyak percobaan masuk dari komputer ini. Coba lagi {menit} menit lagi.", "galat")
        return render_template("masuk.html", lanjut=lanjut, nama_pengguna=nama), 429
    if _bot(request.form):
        flash("Nama pengguna atau sandi salah.", "galat")
        return render_template("masuk.html", lanjut=lanjut, nama_pengguna=nama), 400
    try:
        akun = auth.masuk(nama, request.form.get("sandi", ""), ip)
    except AkunTidakValid as error:
        flash(str(error), "galat")
        return render_template("masuk.html", lanjut=lanjut, nama_pengguna=nama), 401
    _mulai_sesi(akun, request.form.get("tetap_masuk") == "1")
    flash(f"Selamat datang, {akun['nama']}.", "sukses")
    return redirect(lanjut)


@bp.route("/pengaturan-awal", methods=["GET", "POST"])
def pengaturan_awal():
    """Hanya terbuka saat belum ada akun: membuat akun admin pertama."""
    auth = services()["auth"]
    if not auth.perlu_pengaturan_awal():
        return redirect(url_for("auth.masuk"))
    isian = {"nama": request.form.get("nama", ""), "nama_pengguna": request.form.get("nama_pengguna", "")}
    if request.method == "POST":
        if _bot(request.form):
            return "Permintaan ditolak.", 400
        try:
            auth.buat_admin_pertama(isian["nama_pengguna"], isian["nama"], request.form.get("sandi", ""),
                                    request.form.get("ulang_sandi", ""))
            akun = auth.masuk(isian["nama_pengguna"], request.form.get("sandi", ""), request.remote_addr or "-")
        except AkunTidakValid as error:
            flash(str(error), "galat")
            return render_template("pengaturan_awal.html", isian=isian), 400
        _mulai_sesi(akun, False)
        flash("Akun admin dibuat. Anda sudah masuk.", "sukses")
        return redirect(url_for("dashboard.index"))
    return render_template("pengaturan_awal.html", isian=isian)


@bp.post("/keluar")
def keluar():
    session.clear()
    flash("Anda sudah keluar.", "sukses")
    return redirect(url_for("auth.masuk"))


@bp.route("/akun", methods=["GET", "POST"])
def akun():
    if request.method == "POST":
        try:
            baru = services()["auth"].ganti_sandi(g.pengguna["id"], request.form.get("sandi_lama", ""),
                                                  request.form.get("sandi_baru", ""), request.form.get("ulang_sandi", ""))
        except AkunTidakValid as error:
            flash(str(error), "galat")
            return render_template("akun.html", aktif="akun"), 400
        _mulai_sesi(baru, session.permanent)   # sesi di perangkat lain otomatis keluar
        flash("Sandi berhasil diganti. Perangkat lain yang memakai akun ini sudah dikeluarkan.", "sukses")
        return redirect(url_for("auth.akun"))
    return render_template("akun.html", aktif="akun")


@bp.get("/favicon.ico")
def favicon():
    return send_from_directory(current_app.static_folder, "ikon/favicon.ico", mimetype="image/vnd.microsoft.icon",
                               max_age=86400)


@bp.get("/robots.txt")
def robots():
    return Response("User-agent: *\nDisallow: /\n", mimetype="text/plain")
