from flask import Blueprint, Response, current_app, flash, redirect, render_template, request, url_for
from werkzeug.exceptions import RequestEntityTooLarge

from ...business.services.kamera_service import SumberTidakValid
from . import same_origin, services

bp = Blueprint("kamera", __name__, url_prefix="/kamera")


@bp.get("/")
def index():
    svc = services()["kamera"]
    return render_template("kamera.html", status=svc.status(), video=svc.daftar_video(), aktif="kamera",
                           parkir_tersedia=svc.parkir_tersedia,
                           jenis=request.args.get("jenis", "webcam"), pilih=request.args.get("pilih", ""))


@bp.post("/unggah")
def unggah():
    same_origin()
    try:
        name = services()["kamera"].unggah(request.files.get("video"))
    except SumberTidakValid as error:
        flash(str(error), "galat")
        return redirect(url_for("kamera.index", jenis="berkas"))
    flash(f"Video {name} berhasil diunggah. Tekan Mulai untuk memproses.", "sukses")
    return redirect(url_for("kamera.index", jenis="berkas", pilih=name))


@bp.app_errorhandler(RequestEntityTooLarge)
def terlalu_besar(_error):
    flash("Ukuran video melebihi batas 500 MB.", "galat")
    return redirect(url_for("kamera.index", jenis="berkas"))


@bp.post("/mulai")
def mulai():
    same_origin()
    jenis = request.form.get("jenis", "")
    nilai = request.form.get("nilai_" + jenis, "")
    try:
        sesi_id = services()["kamera"].mulai(jenis, nilai, request.form.get("analisis_penuh") == "1",
                                             request.form.get("mode", "umum"), request.form.get("jam_rekaman"))
        flash(f"Sesi {sesi_id} dimulai.", "sukses")
    except SumberTidakValid as error:
        flash(str(error), "galat")
    return redirect(url_for("kamera.index", jenis=jenis, pilih=nilai if jenis == "berkas" else None))


@bp.get("/pratinjau")
def pratinjau():
    try:
        jpeg = services()["kamera"].pratinjau(request.args.get("jenis", ""), request.args.get("nilai", ""))
    except SumberTidakValid as error:
        return Response(str(error), status=400, mimetype="text/plain")
    return Response(jpeg, mimetype="image/jpeg", headers={"Cache-Control": "no-store"})


@bp.post("/hentikan")
def hentikan():
    same_origin()
    if services()["kamera"].hentikan():
        flash("Kamera dihentikan.", "sukses")
    return redirect(url_for("kamera.index"))


@bp.get("/stream")
def stream():
    svc = services()["kamera"]
    tayangan, ip = current_app.extensions["tayangan"], request.remote_addr or "-"
    if not tayangan.ambil(ip):
        return Response("Terlalu banyak tayangan terbuka dari komputer ini. Tutup tab lain.", status=429,
                        mimetype="text/plain")

    def generate():
        last = -1
        idle = 0
        while True:
            frame_id, jpeg = svc.frame(last, timeout=1.0)
            if frame_id != last and jpeg:
                last, idle = frame_id, 0
                yield b"--frame\r\nContent-Type: image/jpeg\r\nContent-Length: " + str(len(jpeg)).encode() + b"\r\n\r\n" + jpeg + b"\r\n"
            else:
                idle += 1
                if not svc.status()["berjalan"] and idle >= 2:
                    break

    def generate_aman():
        try:
            yield from generate()
        finally:
            tayangan.lepas(ip)

    return Response(generate_aman(), mimetype="multipart/x-mixed-replace; boundary=frame",
                    headers={"Cache-Control": "no-store"})
