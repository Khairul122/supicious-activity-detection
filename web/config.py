"""Konfigurasi aplikasi. Nilai dapat diganti lewat variabel lingkungan."""
import os
from pathlib import Path

WEB_DIR = Path(__file__).resolve().parent
PROJECT_DIR = WEB_DIR.parent
STORAGE_DIR = Path(os.environ.get("SAD_STORAGE", WEB_DIR / "storage"))


class Config:
    # Kunci session: dari variabel lingkungan, atau dibuat sekali dan disimpan di storage/.kunci_session
    SECRET_KEY = os.environ.get("SAD_SECRET_KEY")
    # Aktifkan (1) bila web dibuka lewat HTTPS, agar cookie session hanya dikirim lewat koneksi terenkripsi
    COOKIE_AMAN = os.environ.get("SAD_COOKIE_AMAN", "0") == "1"
    # MySQL Laragon (bawaan: root tanpa sandi di 127.0.0.1:3306). Lihat hasilnya di phpMyAdmin.
    DB_HOST = os.environ.get("SAD_DB_HOST", "127.0.0.1")
    DB_PORT = int(os.environ.get("SAD_DB_PORT", 3306))
    DB_USER = os.environ.get("SAD_DB_USER", "root")
    DB_PASSWORD = os.environ.get("SAD_DB_PASSWORD", "")
    DB_NAME = os.environ.get("SAD_DB_NAME", "deteksi_perilaku")
    MAX_CONTENT_LENGTH = 500 * 1024 * 1024  # batas unggah video 500 MB
    SNAPSHOT_DIR = STORAGE_DIR / "snapshot"
    VIDEO_DIR = Path(os.environ.get("SAD_VIDEO_DIR", STORAGE_DIR / "video"))  # taruh berkas video demo di sini
    # Model di web/models; bila tidak ada, pakai hasil training lama di hasil_latih/detect/train-4.
    _MODEL_WEB = WEB_DIR / "models" / "best.pt"
    MODEL = Path(os.environ.get("SAD_MODEL") or (_MODEL_WEB if _MODEL_WEB.is_file()
                                                 else PROJECT_DIR / "hasil_latih/detect/train-4/weights/best.pt"))
    # Model mode parkiran (kelas person dan motorcycle), hasil notebook/Latih_Semua_Model.ipynb.
    MODEL_PARKIR = Path(os.environ.get("SAD_MODEL_PARKIR") or WEB_DIR / "models" / "motor.pt")
    PARKIR_DEKAT_S = float(os.environ.get("SAD_PARKIR_DEKAT_S", 15))  # ambang aturan "dekat motor orang lain"
    TRACKER = Path(os.environ.get("SAD_TRACKER", WEB_DIR / "trackers/botsort_reid_b125.yaml"))
    CONFIDENCE = float(os.environ.get("SAD_CONFIDENCE", 0.15))
    IMAGE_SIZE = int(os.environ.get("SAD_IMAGE_SIZE", 640))
    LINK_GAP_S = float(os.environ.get("SAD_SAMBUNG_DETIK", 2.0))
