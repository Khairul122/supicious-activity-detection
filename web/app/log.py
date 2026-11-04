"""Pengaturan log terminal dan berkas untuk memantau proses web.

Format: 2026-11-01 17:30:01 | INFO  | mesin   | pesan
Log juga disimpan ke web/storage/log/web.log (berputar, 5 berkas x 2 MB).
"""
import logging
import logging.handlers
import re
import sys
from pathlib import Path

NAMA = "deteksi"
SENYAP = ("/api/status", "/kamera/stream", "/static/", "/snapshot/", "/favicon", "/kamera/pratinjau",
          "development server", "Press CTRL+C")
_ANSI = re.compile(r"\x1b\[[0-9;]*m")
_WERKZEUG = re.compile(r'^(\S+) - - \[[^\]]*\] "(.*)" (\d{3}) .*$')


class _SaringPermintaanRutin(logging.Filter):
    """Sembunyikan permintaan berkala (status tiap detik, stream, berkas statis) dari log werkzeug."""

    def filter(self, record):
        pesan = _ANSI.sub("", record.getMessage())
        if any(k in pesan for k in SENYAP):
            return False
        cocok = _WERKZEUG.match(pesan)  # "127.0.0.1 - - [tanggal] "GET / HTTP/1.1" 200 -" -> ringkas
        record.msg, record.args = (f"{cocok[2]} -> {cocok[3]}" if cocok else pesan), None
        return True


class _Format(logging.Formatter):
    def format(self, record):
        record.komponen = record.name.split(".")[-1] if record.name.startswith(NAMA + ".") else \
            ("http" if record.name == "werkzeug" else record.name)
        return super().format(record)


def setup(log_dir, level="INFO", log_requests=True):
    fmt = _Format("%(asctime)s | %(levelname)-7s | %(komponen)-8s | %(message)s", "%Y-%m-%d %H:%M:%S")
    root = logging.getLogger(NAMA)
    root.setLevel(level)
    root.handlers.clear()
    try:  # konsol Windows lama: jangan gagal karena karakter khusus
        sys.stdout.reconfigure(errors="replace")
    except (AttributeError, ValueError):
        pass
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(fmt)
    root.addHandler(console)
    log_dir = Path(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    berkas = logging.handlers.RotatingFileHandler(log_dir / "web.log", maxBytes=2 * 1024 * 1024, backupCount=5,
                                                  encoding="utf-8")
    berkas.setFormatter(fmt)
    root.addHandler(berkas)
    root.propagate = False

    # permintaan HTTP dari werkzeug: tampilkan dengan format yang sama, tanpa yang rutin
    wz = logging.getLogger("werkzeug")
    wz.handlers.clear()
    wz.propagate = False
    if log_requests:
        wz.setLevel(logging.INFO)
        for h in (console, berkas):
            wz.addHandler(h)
        wz.addFilter(_SaringPermintaanRutin())
    else:
        wz.setLevel(logging.WARNING)
    # sembunyikan log internal yang berisik
    for noisy in ("ultralytics", "PIL", "matplotlib"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    return log_dir / "web.log"


def get(nama):
    return logging.getLogger(f"{NAMA}.{nama}")
