"""Jalankan web deteksi perilaku: python web/run.py --buka  lalu buka http://127.0.0.1:5000

Log proses tampil di terminal ini dan disimpan ke web/storage/log/web.log.
"""
import argparse
import sys
import time
import webbrowser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app import log  # noqa: E402
from config import STORAGE_DIR  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--host", default="127.0.0.1", help="127.0.0.1 = hanya komputer ini (disarankan)")
    ap.add_argument("--port", type=int, default=5000)
    ap.add_argument("--buka", action="store_true", help="buka peramban otomatis")
    ap.add_argument("--log-level", default="INFO", choices=("DEBUG", "INFO", "WARNING"),
                    help="DEBUG menampilkan rincian per orang setiap ringkasan progres")
    ap.add_argument("--log-progres", type=float, default=5.0, help="jeda ringkasan progres sesi dalam detik (0 = mati)")
    ap.add_argument("--tanpa-log-http", action="store_true", help="sembunyikan log permintaan halaman")
    ap.add_argument("--atur-ulang-sandi", metavar="NAMA", help="atur ulang sandi akun NAMA lewat terminal, lalu keluar")
    ap.add_argument("--server-dev", action="store_true", help="pakai server pengembangan Flask walau waitress terpasang")
    args = ap.parse_args()
    if args.atur_ulang_sandi:
        sys.exit(atur_ulang_sandi(args.atur_ulang_sandi))

    berkas_log = log.setup(STORAGE_DIR / "log", args.log_level, not args.tanpa_log_http)
    logger = log.get("server")
    logger.info("=" * 64)
    logger.info("Web deteksi perilaku dimulai (log juga disimpan di %s)", berkas_log)
    mulai = time.time()
    try:
        from app import create_app
        app = create_app(progress_s=args.log_progres)
    except Exception as error:  # galat awal ditampilkan jelas tanpa jejak panjang
        logger.error("Web gagal dimulai: %s", error)
        logger.debug("Rincian galat", exc_info=True)
        sys.exit(1)
    import flask.cli
    flask.cli.show_server_banner = lambda *a, **k: None  # alamat sudah tertulis di log
    url = f"http://{args.host}:{args.port}"
    logger.info("Siap dalam %.1f detik. Buka %s  (Ctrl+C untuk berhenti)", time.time() - mulai, url)
    if args.buka:
        webbrowser.open(url)
    try:
        try:
            if args.server_dev:
                raise ImportError
            from waitress import serve
        except ImportError:
            logger.warning("Server pengembangan Flask dipakai. Untuk pemakaian sehari-hari pasang waitress: "
                           "pip install waitress")
            app.run(host=args.host, port=args.port, threaded=True, debug=False, use_reloader=False)
        else:
            # waitress: server produksi dengan jumlah thread terbatas, batas antrean, dan batas waktu koneksi diam
            if not args.tanpa_log_http:
                http = log.get("http")

                @app.after_request
                def catat(resp):
                    from flask import request
                    if request.endpoint != "static":
                        http.info("%s %s -> %s", request.method, request.path, resp.status_code)
                    return resp
            logger.info("Server produksi waitress aktif (32 thread)")
            serve(app, host=args.host, port=args.port, threads=32, connection_limit=200, backlog=256,
                  channel_timeout=60, cleanup_interval=30, ident=None, clear_untrusted_proxy_headers=True)
    finally:
        logger.info("Web dihentikan.")


def atur_ulang_sandi(nama):
    """Pemilik komputer mengatur ulang sandi yang lupa. Butuh akses terminal, jadi tidak bisa dipakai dari jaringan."""
    import getpass
    from app.business.services.auth_service import AkunTidakValid, AuthService
    from app.data.database import Database
    from app.data.repositories.pengguna_repository import PenggunaRepository
    from config import Config
    db = Database(Config.DB_HOST, Config.DB_PORT, Config.DB_USER, Config.DB_PASSWORD, Config.DB_NAME)
    sandi = getpass.getpass(f"Sandi baru untuk {nama}: ")
    if sandi != getpass.getpass("Ulangi sandi baru: "):
        print("Kedua sandi tidak sama. Tidak ada yang diubah.")
        return 1
    try:
        AuthService(PenggunaRepository(db)).atur_ulang_sandi(nama, sandi)
    except AkunTidakValid as error:
        print(error)
        return 1
    print(f"Sandi {nama} diganti. Semua sesi lama akun ini sudah keluar.")
    return 0


if __name__ == "__main__":
    main()
