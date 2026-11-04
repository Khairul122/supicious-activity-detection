from flask import Blueprint, jsonify, request, url_for

from ...business.services.kamera_service import SumberTidakValid
from ...business.services.zona_service import ZonaTidakValid
from ..filters import format_alasan, format_jam, format_kategori, format_waktu
from . import same_origin, services

bp = Blueprint("api", __name__, url_prefix="/api")


@bp.get("/status")
def status():
    return jsonify(services()["kamera"].status())


def _sumber(data):
    return services()["kamera"].kunci_sumber(data.get("jenis", ""), data.get("nilai", ""))


@bp.get("/zona")
def daftar_zona():
    try:
        sumber = _sumber(request.args)
    except SumberTidakValid as error:
        return jsonify({"galat": str(error), "zona": []}), 400
    kamera = services()["kamera"]
    return jsonify({"sumber": sumber, "zona": services()["zona"].daftar(sumber), "mode": kamera.mode_sumber(sumber),
                    "parkir_tersedia": kamera.parkir_tersedia})


@bp.post("/zona")
def tambah_zona():
    same_origin()
    data = request.get_json(silent=True) or {}
    try:
        sumber = _sumber(data)
        zid = services()["zona"].tambah(sumber, data.get("nama"), data.get("jenis_zona"), data.get("titik") or [],
                                        data.get("jam_mulai"), data.get("jam_selesai"))
    except (SumberTidakValid, ZonaTidakValid) as error:
        return jsonify({"galat": str(error)}), 400
    return jsonify({"id": zid, "sumber": sumber}), 201


@bp.delete("/zona/<int:zona_id>")
def hapus_zona(zona_id):
    same_origin()
    try:
        services()["zona"].hapus(zona_id)
    except ZonaTidakValid as error:
        return jsonify({"galat": str(error)}), 404
    return jsonify({"ok": True})


@bp.get("/belum-dinilai")
def belum_dinilai():
    return jsonify({"jumlah": services()["riwayat"].jumlah_belum()})


@bp.get("/peringatan")
def peringatan_terbaru():
    """Peringatan terbaru untuk umpan langsung di halaman Kamera."""
    baris = services()["riwayat"].terbaru(request.args.get("sesi"), request.args.get("limit", 8))
    return jsonify([{"id": p["id"], "waktu": format_waktu(p["waktu"]), "jam": format_jam(p["waktu"]),
                     "detik": p["detik"], "sesi_id": p["sesi_id"], "id_orang": p["id_orang"],
                     "kategori": p.get("kategori"), "kategori_label": format_kategori(p.get("kategori")),
                     "alasan": format_alasan(p["alasan"]), "penilaian": p.get("penilaian"),
                     "snapshot": url_for("riwayat.snapshot", name=p["snapshot"])} for p in baris])


@bp.post("/peringatan/<int:peringatan_id>/nilai")
def nilai_peringatan(peringatan_id):
    same_origin()
    data = request.get_json(silent=True) or {}
    try:
        services()["riwayat"].nilai(peringatan_id, data.get("penilaian", ""))
    except ValueError as error:
        return jsonify({"galat": str(error)}), 400
    return jsonify({"ok": True, "penilaian": data.get("penilaian") or None})
