from datetime import datetime

from flask import Blueprint, Response, abort, flash, redirect, render_template, request, send_file, url_for

from . import same_origin, services

bp = Blueprint("riwayat", __name__)


@bp.get("/riwayat")
def index():
    data = services()["riwayat"].cari(request.args.get("tanggal"), request.args.get("sesi"),
                                       request.args.get("halaman", 1), request.args.get("penilaian"))
    return render_template("riwayat.html", data=data, aktif="riwayat")


@bp.post("/riwayat/<int:peringatan_id>/nilai")
def nilai(peringatan_id):
    same_origin()
    try:
        services()["riwayat"].nilai(peringatan_id, request.form.get("penilaian", ""))
    except ValueError as error:
        flash(str(error), "galat")
    kembali = request.form.get("kembali") or url_for("riwayat.index")
    if not kembali.startswith("/") or kembali.startswith("//") or "\\" in kembali:  # cegah pengalihan ke situs lain
        kembali = url_for("riwayat.index")
    return redirect(kembali)


@bp.get("/riwayat/ekspor.csv")
def ekspor():
    body = services()["riwayat"].ekspor_csv(request.args.get("tanggal"), request.args.get("sesi"))
    name = f"riwayat_peringatan_{datetime.now():%Y%m%d_%H%M}.csv"
    return Response("﻿" + body, mimetype="text/csv",
                    headers={"Content-Disposition": f"attachment; filename={name}"})


@bp.get("/snapshot/<path:name>")
def snapshot(name):
    path = services()["riwayat"].snapshot(name)
    if path is None:
        abort(404)
    return send_file(path, mimetype="image/jpeg", max_age=3600)
