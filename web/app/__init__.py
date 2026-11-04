"""Composition root: merakit tiga lapisan.

  presentation (routes, template, static)
        |  memanggil
  business (services, mesin deteksi)
        |  memanggil
  data (database, repository, penyimpanan snapshot)
"""
import os

from flask import Flask

from config import PROJECT_DIR, STORAGE_DIR, Config

os.environ.setdefault("YOLO_CONFIG_DIR", str(STORAGE_DIR / ".ultralytics"))


def create_app(config=Config, progress_s=5.0):
    from .business.detection.engine import DetectionEngine
    from .business.services.auth_service import AuthService
    from .business.services.dashboard_service import DashboardService
    from .business.services.kamera_service import KameraService
    from .business.services.riwayat_service import RiwayatService
    from .business.services.zona_service import ZonaService
    from .data.database import Database
    from .data.repositories.pengguna_repository import PenggunaRepository
    from .data.repositories.peringatan_repository import PeringatanRepository
    from .data.repositories.sesi_repository import SesiRepository
    from .data.repositories.sumber_repository import SumberRepository
    from .data.repositories.zona_repository import ZonaRepository
    from .data.snapshot_storage import SnapshotStorage
    from .data.video_storage import VideoStorage
    from . import log
    from .presentation import filters, security
    from .presentation.routes import api_routes, auth_routes, dashboard_routes, kamera_routes, riwayat_routes

    app = Flask(__name__, template_folder="presentation/templates", static_folder="presentation/static")
    app.config.from_object(config)
    app.config["SECRET_KEY"] = config.SECRET_KEY or security.kunci_rahasia(STORAGE_DIR)
    logger = log.get("server")
    for key in ("MODEL", "TRACKER"):
        if not getattr(config, key).is_file():
            raise FileNotFoundError(f"{key} tidak ditemukan: {getattr(config, key)}")
    logger.info("Model    : %s", config.MODEL)
    logger.info("Tracker  : %s | confidence %.2f | ukuran %d px | sambung ID %.0f detik",
                config.TRACKER.name, config.CONFIDENCE, config.IMAGE_SIZE, config.LINK_GAP_S)
    logger.info("Parkiran : %s", config.MODEL_PARKIR if config.MODEL_PARKIR.is_file()
                else f"tidak tersedia ({config.MODEL_PARKIR} tidak ditemukan)")
    logger.info("Video    : %s", config.VIDEO_DIR)

    # data tier
    db = Database(config.DB_HOST, config.DB_PORT, config.DB_USER, config.DB_PASSWORD, config.DB_NAME)
    sesi_repo, peringatan_repo, zona_repo = SesiRepository(db), PeringatanRepository(db), ZonaRepository(db)
    snapshots = SnapshotStorage(config.SNAPSHOT_DIR)
    videos = VideoStorage(config.VIDEO_DIR)

    # business tier
    engine = DetectionEngine(config.MODEL, config.TRACKER, config.CONFIDENCE, config.IMAGE_SIZE, config.LINK_GAP_S,
                             progress_s=progress_s,
                             parkir_model_path=config.MODEL_PARKIR if config.MODEL_PARKIR.is_file() else None,
                             parkir_dekat_s=config.PARKIR_DEKAT_S)
    engine.warmup()  # muat model di latar agar kamera cepat menyala
    zona = ZonaService(zona_repo, engine)
    kamera = KameraService(engine, sesi_repo, peringatan_repo, snapshots, videos, zona, SumberRepository(db))
    model_path = config.MODEL.resolve()
    info = {"model": model_path.relative_to(PROJECT_DIR.resolve()).as_posix() if model_path.is_relative_to(PROJECT_DIR.resolve()) else str(model_path),
            "tracker": config.TRACKER.name, "confidence": config.CONFIDENCE, "image_size": config.IMAGE_SIZE,
            "sambung": config.LINK_GAP_S,
            "model_parkir": config.MODEL_PARKIR.name if config.MODEL_PARKIR.is_file() else "tidak terpasang",
            "database": f"MySQL {config.DB_NAME} @ {config.DB_HOST}:{config.DB_PORT}"}
    auth = AuthService(PenggunaRepository(db))
    if auth.perlu_pengaturan_awal():
        logger.info("Belum ada akun. Buka web untuk membuat akun admin pertama.")
    app.extensions["services"] = {
        "auth": auth,
        "kamera": kamera,
        "zona": zona,
        "riwayat": RiwayatService(peringatan_repo, sesi_repo, snapshots),
        "dashboard": DashboardService(peringatan_repo, sesi_repo, kamera, info),
    }

    # presentation tier
    security.pasang(app, auth, secure_cookie=config.COOKIE_AMAN)
    for module in (auth_routes, dashboard_routes, kamera_routes, riwayat_routes, api_routes):
        app.register_blueprint(module.bp)

    filters.register(app)

    return app
