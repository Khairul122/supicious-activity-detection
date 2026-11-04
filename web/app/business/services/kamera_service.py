"""Business tier: logika kamera (validasi sumber, unggah video, sesi, dan penanganan peringatan)."""
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from ... import log
from ...data.video_storage import VIDEO_EXT
from ..detection.zones import ke_menit

logger = log.get("kamera")

MAX_UPLOAD_MB = 500


class SumberTidakValid(ValueError):
    pass


def now():
    return datetime.now().replace(microsecond=0)


def mask_url(url):
    """Sembunyikan sandi pada alamat stream sebelum disimpan atau ditampilkan."""
    parts = urlsplit(url)
    if parts.password:
        netloc = f"{parts.username}:***@{parts.hostname}" + (f":{parts.port}" if parts.port else "")
        return urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))
    return url


MODE = {"otomatis": "Otomatis", "umum": "Umum", "parkir": "Parkiran motor"}


class KameraService:
    def __init__(self, engine, sesi_repo, peringatan_repo, snapshots, videos, zona_service, sumber_repo):
        self.engine, self.sesi_repo, self.peringatan_repo = engine, sesi_repo, peringatan_repo
        self.snapshots, self.videos, self.zona_service = snapshots, videos, zona_service
        self.sumber_repo = sumber_repo
        self.sesi_repo.mark_interrupted()

    @property
    def parkir_tersedia(self):
        return self.engine.parkir_tersedia

    def mode_sumber(self, sumber):
        """Mode pilihan terakhir untuk sumber ini; bawaan 'otomatis' bila model motor terpasang."""
        mode = self.sumber_repo.get_mode(sumber) or ("otomatis" if self.parkir_tersedia else "umum")
        return mode if mode == "umum" or self.parkir_tersedia else "umum"

    def daftar_video(self):
        return self.videos.list()

    def unggah(self, berkas):
        """berkas: objek unggahan Flask (FileStorage). Kembalikan nama berkas tersimpan."""
        if berkas is None or not berkas.filename:
            raise SumberTidakValid("Pilih berkas video terlebih dahulu.")
        if Path(berkas.filename).suffix.lower() not in VIDEO_EXT:
            raise SumberTidakValid("Format tidak didukung. Gunakan " + ", ".join(sorted(VIDEO_EXT)) + ".")
        name = self.videos.save(berkas, berkas.filename)
        if not self._video_terbaca(self.videos.path(name)):   # ekstensi bisa dipalsukan: periksa isinya
            self.videos.remove(name)
            logger.warning("Unggahan ditolak, bukan video yang bisa dibaca: %s", berkas.filename)
            raise SumberTidakValid("Berkas ini bukan video yang bisa dibaca. Pilih berkas video lain.")
        size = self.videos.path(name).stat().st_size / 1e6
        logger.info("Video diunggah: %s (%.1f MB)", name, size)
        return name

    @staticmethod
    def _video_terbaca(path):
        import cv2
        capture = cv2.VideoCapture(str(path))
        try:
            ok, frame = capture.read()
            return bool(ok) and frame is not None and frame.size > 0
        finally:
            capture.release()

    def _resolve(self, jenis, nilai):
        nilai = (nilai or "").strip()
        if jenis == "webcam":
            if not re.fullmatch(r"\d{1,2}", nilai):
                raise SumberTidakValid("Nomor webcam harus berupa angka, misalnya 0.")
            return nilai, f"Webcam {nilai}", True
        if jenis == "stream":
            if not re.match(r"^(rtsp|rtsps|http|https)://", nilai, re.I):
                raise SumberTidakValid("Alamat stream harus diawali rtsp://, http://, atau https://.")
            return nilai, mask_url(nilai), True
        if jenis == "berkas":
            path = self.videos.path(nilai) if nilai else None
            if path is None:
                raise SumberTidakValid("Pilih atau unggah berkas video terlebih dahulu.")
            return str(path), nilai, False
        raise SumberTidakValid("Jenis sumber tidak dikenal.")

    def kunci_sumber(self, jenis, nilai):
        """Nama sumber yang dipakai sebagai kunci zona (sama dengan yang tercatat di sesi)."""
        return self._resolve(jenis, nilai)[1]

    def pratinjau(self, jenis, nilai):
        """Satu gambar mentah dari sumber untuk menggambar zona."""
        source, label, live = self._resolve(jenis, nilai)
        state = self.engine.status()
        if state["berjalan"] and state["sumber"] == label:
            jpeg = self.engine.latest_raw_jpeg()
            if jpeg:
                return jpeg
        if state["berjalan"] and jenis == "webcam":
            raise SumberTidakValid("Webcam sedang dipakai sesi lain. Hentikan sesi terlebih dahulu.")
        try:
            return self.engine.capture_still(source, live)
        except RuntimeError as error:
            raise SumberTidakValid(str(error)) from None

    def mulai(self, jenis, nilai, analisis_penuh=False, mode="umum", jam_rekaman=None):
        """analisis_penuh: untuk berkas, proses setiap frame (lebih lambat dari waktu asli bila tanpa GPU).
        mode: 'otomatis' (diputuskan dari jumlah motor terparkir setelah 10 detik), 'umum', atau 'parkir'.
        jam_rekaman: untuk berkas, jam saat rekaman dimulai ('HH:MM'); jam aktif zona mengikutinya."""
        source, label, live = self._resolve(jenis, nilai)
        jam_awal = None
        if jam_rekaman and not live:
            try:
                jam_awal = ke_menit(jam_rekaman)
            except (ValueError, TypeError):
                raise SumberTidakValid("Format jam rekaman harus HH:MM, misalnya 23:15.") from None
        mode = mode or "otomatis"
        if mode not in MODE:
            raise SumberTidakValid("Mode deteksi tidak dikenal.")
        if mode == "otomatis" and not self.parkir_tersedia:
            mode = "umum"   # tanpa model motor, tempat parkir tidak bisa dikenali
        if mode == "parkir" and not self.parkir_tersedia:
            raise SumberTidakValid("Model parkiran belum terpasang. Simpan motor.pt di folder web/models.")
        if self.engine.is_running():
            raise SumberTidakValid("Kamera masih berjalan. Hentikan dahulu sebelum memulai sumber lain.")
        self.sumber_repo.set_mode(label, mode, now())
        hasil_otomatis = self.sumber_repo.get_hasil_otomatis(label) if mode == "otomatis" else None
        sesi_id = self.sesi_repo.create(jenis, label, now(), None if mode == "otomatis" else mode)
        zones = self.zona_service.zone_set(label)
        putar = "langsung" if live else ("analisis setiap frame" if analisis_penuh else "putar sesuai waktu asli")
        aturan = (f"{len(zones.zones)} zona (" + ", ".join(
            f"{z.nama}:{z.jenis}" + (f" {z.mulai // 60:02d}:{z.mulai % 60:02d}-{z.selesai // 60:02d}:{z.selesai % 60:02d}"
                                     if z.terjadwal else "") for z in zones.zones) + ")") if zones \
            else "tanpa zona"
        if jam_awal is not None:
            putar += f" | jam rekaman {jam_awal // 60:02d}:{jam_awal % 60:02d}"
        logger.info("Sesi %s dimulai | %s: %s | mode %s | %s | %s", sesi_id, jenis, label, MODE[mode], putar, aturan)

        def on_alert(detik, id_orang, alasan, box, image, kategori=None, zona=None):
            name = f"sesi{sesi_id}_id{id_orang}_{detik:07.1f}s_{kategori or 'umum'}.jpg"
            self.snapshots.save(name, image)
            self.peringatan_repo.create(sesi_id, now(), round(detik, 1), id_orang, alasan, name, box, kategori, zona)

        def on_mode(mode_akhir, alasan):
            self.sesi_repo.set_mode(sesi_id, mode_akhir, otomatis=True)
            self.sumber_repo.set_hasil_otomatis(label, mode_akhir)

        def on_finish(frames, status, catatan):
            self.sesi_repo.finish(sesi_id, now(), frames, status, catatan)

        self.engine.start(source, jenis, label, sesi_id, live, on_alert, on_finish, zones,
                          full_analysis=bool(analisis_penuh) and not live, mode=mode, jam_awal=jam_awal,
                          on_mode=on_mode, hasil_otomatis=hasil_otomatis)
        return sesi_id

    def hentikan(self):
        if not self.engine.is_running():
            return False
        logger.info("Permintaan hentikan sesi %s dari halaman Cam", self.engine.status().get("sesi_id"))
        self.engine.stop()
        return True

    def status(self):
        state = self.engine.status()
        state["perangkat"] = {0: "GPU", "cpu": "CPU"}.get(self.engine.device, "-")
        mode = state.get("mode") or ""
        if mode == "otomatis":
            state["mode_label"] = "Otomatis: menentukan…"
        elif state.get("mode_otomatis") and mode in MODE:
            state["mode_label"] = f"{MODE[mode]} (otomatis)"
        else:
            state["mode_label"] = MODE.get(mode, "-")
        return state

    def frame(self, last_id, timeout=1.0):
        return self.engine.wait_frame(last_id, timeout)
