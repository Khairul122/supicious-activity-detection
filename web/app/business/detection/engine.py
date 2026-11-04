"""Business tier: mesin deteksi berjalan di thread latar.

Mesin ini tidak mengenal database. Hasil disampaikan lewat callback on_alert dan on_finish
yang disediakan service, sehingga lapisan bisnis tidak bergantung pada detail penyimpanan.
Komponen perilaku ada di behavior.py (aturan dan penyambungan ID yang sudah diuji).
"""
import os
import threading
import time
from collections import deque

import cv2
import numpy as np

from ... import log
from .behavior import BehaviorTracker, LatestFrameReader, draw
from .zones import menit_sekarang

logger = log.get("mesin")

# RTSP: batas tunggu soket 5 detik agar kamera yang mati terdeteksi, bukan membuat pembacaan menggantung
os.environ.setdefault("OPENCV_FFMPEG_CAPTURE_OPTIONS", "timeout;5000000")

STALL_S = 3.0  # satu frame lebih lama dari ini = komputer tersendat; jangan dihitung sebagai keterlambatan video
SAMBUNG_MAKS_S = 30.0   # jeda terlama antar percobaan sambung ulang CCTV
STREAM_DIAM_S = 15.0    # tidak ada gambar baru selama 15 detik = stream macet, sambung ulang
WEBCAM_COBA = 3         # webcam yang tercabut dicoba 3 kali, CCTV dicoba terus sampai dihentikan
MOTOR_CONF = 0.3  # motor butuh keyakinan lebih tinggi dari orang: motor palsu menimbulkan alarm "dekat motor"
MODE = ("otomatis", "umum", "parkir")
OTOMATIS_S = 10.0        # mode otomatis diputuskan setelah 10 detik gambar
OTOMATIS_MIN_MOTOR = 2   # minimal 2 motor terparkir = parkiran


def putuskan_mode(motor_parkir, hasil_sebelumnya=None):
    """Mode otomatis: kembalikan (mode, alasan).

    Parkiran bila ada minimal 2 motor terparkir. Satu motor di depan toko atau rumah tidak cukup.
    Bila motor terparkir kurang dari 2 tetapi sumber ini sebelumnya terdeteksi parkiran
    (misalnya parkiran kosong pada malam hari), mode parkiran tetap dipakai.
    """
    if motor_parkir >= OTOMATIS_MIN_MOTOR:
        return "parkir", f"{motor_parkir} motor terparkir terlihat"
    if hasil_sebelumnya == "parkir":
        return "parkir", (f"hanya {motor_parkir} motor terparkir, tetapi sumber ini sebelumnya terdeteksi parkiran"
                          if motor_parkir else "parkiran sedang kosong; sumber ini sebelumnya terdeteksi parkiran")
    return "umum", (f"hanya {motor_parkir} motor terparkir" if motor_parkir else "tidak ada motor terparkir")


def kelas_model(names, mode):
    """Indeks kelas person dan motorcycle dari nama kelas model."""
    nama = {str(v).lower(): int(k) for k, v in (names.items() if isinstance(names, dict) else enumerate(names))}
    person = nama.get("person", 0)
    motor = nama.get("motorcycle", nama.get("motor"))
    if mode == "parkir" and motor is None:
        raise RuntimeError("Model parkiran tidak memiliki kelas motorcycle.")
    return person, motor


class DetectionEngine:
    def __init__(self, model_path, tracker_path, confidence=0.15, image_size=640, link_gap_s=2.0, progress_s=5.0,
                 parkir_model_path=None, parkir_dekat_s=15.0):
        self.progress_s = progress_s
        self.model_path, self.tracker_path = str(model_path), str(tracker_path)
        self.parkir_model_path = str(parkir_model_path) if parkir_model_path else None
        self.parkir_dekat_s = parkir_dekat_s
        self.confidence, self.image_size, self.link_gap_s = confidence, image_size, link_gap_s
        self._lock = threading.Lock()
        self._frame_cond = threading.Condition()
        self._thread = None
        self._stop = threading.Event()
        self._jpeg, self._frame_id = None, 0
        self._state = self._idle_state()
        self.device = None
        self._ready = threading.Event()
        self._zones = None
        self._raw = None
        self._warmup_error = None
        self._mode = "umum"
        self._jam_awal = None

    def warmup(self):
        """Muat PyTorch, Ultralytics, dan bobot model di latar saat server mulai.

        Impor PyTorch dan inisialisasi model memakan beberapa detik. Dengan pemanasan ini,
        tombol Mulai tidak perlu menunggu proses tersebut lagi.
        """
        def run():
            t0 = time.time()
            logger.info("Memuat PyTorch dan model di latar…")
            try:
                import torch
                from ultralytics import YOLO

                self.device = 0 if torch.cuda.is_available() else "cpu"
                if self.device == "cpu":
                    torch.set_num_threads(min(4, os.cpu_count() or 1))
                    perangkat = f"CPU ({torch.get_num_threads()} thread)"
                else:
                    perangkat = f"GPU {torch.cuda.get_device_name(0)}"
                logger.info("PyTorch %s siap dalam %.1f detik, perangkat: %s", torch.__version__, time.time() - t0, perangkat)
                for mode, path in (("umum", self.model_path), ("parkir", self.parkir_model_path)):
                    if not path:
                        continue
                    t1 = time.time()
                    model = YOLO(path)
                    model.predict(np.zeros((480, 640, 3), dtype=np.uint8), imgsz=self.image_size,
                                  device=self.device, verbose=False)
                    person, motor = kelas_model(model.names, mode)
                    logger.info("Model %s siap dalam %.1f detik (%s): kelas %s", mode, time.time() - t1,
                                os.path.basename(path), ", ".join(str(v) for v in model.names.values()))
                    # panaskan juga tracker (BoT-SORT + ReID): pemanggilan track pertama bisa lama di beberapa komputer
                    t2 = time.time()
                    dummy = np.full((480, 640, 3), 127, dtype=np.uint8)
                    classes = [person] if mode == "umum" else [person, motor]
                    for _ in range(3):
                        model.track(dummy, persist=True, classes=classes, conf=self.confidence, imgsz=self.image_size,
                                    tracker=self.tracker_path, device=self.device, verbose=False)
                    logger.info("Tracker mode %s siap dalam %.1f detik.", mode, time.time() - t2)
                logger.info("Pemanasan selesai dalam %.1f detik. Kamera bisa dimulai.", time.time() - t0)
            except Exception as error:  # dilaporkan saat sesi dimulai
                self._warmup_error = str(error)
                logger.error("Model gagal dimuat: %s", error)
            finally:
                self._ready.set()

        threading.Thread(target=run, daemon=True).start()

    @staticmethod
    def _open_capture(source):
        """Buka sumber video. Webcam di Windows memakai DirectShow karena backend bawaan (MSMF) lambat sekali."""
        if str(source).isdigit():
            index = int(source)
            if os.name == "nt":
                capture = cv2.VideoCapture(index, cv2.CAP_DSHOW)
                if capture.isOpened():
                    capture.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
                    capture.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                    capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                    return capture
                capture.release()
            return cv2.VideoCapture(index)
        return cv2.VideoCapture(source)

    def latest_raw_jpeg(self):
        """Gambar terakhir tanpa kotak dan zona (untuk editor zona)."""
        with self._lock:
            frame = self._raw
        if frame is None:
            return None
        ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        return buf.tobytes() if ok else None

    @classmethod
    def capture_still(cls, source, live):
        """Ambil satu gambar dari sumber yang tidak sedang dipakai (untuk editor zona)."""
        capture = cls._open_capture(source)
        try:
            if not capture.isOpened():
                raise RuntimeError("Sumber video gagal dibuka.")
            frame = None
            for _ in range(10 if live else 1):  # kamera butuh beberapa gambar untuk menyesuaikan cahaya
                ok, img = capture.read()
                if ok:
                    frame = img
            if frame is None:
                raise RuntimeError("Tidak ada gambar dari sumber video.")
            ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            return buf.tobytes()
        finally:
            capture.release()

    def _set_stage(self, text):
        with self._lock:
            self._state["tahap"] = text

    @staticmethod
    def _idle_state():
        return {"berjalan": False, "sumber": None, "jenis": None, "sesi_id": None, "mulai": None, "selesai": None,
                "detik": 0.0, "fps": 0.0, "frame": 0, "orang": [], "peringatan_sesi": 0, "galat": None, "tahap": None,
                "dilewati": 0, "mode": None, "motor": 0, "motor_parkir": 0, "mode_otomatis": False,
                "mode_alasan": None}

    # kendali
    @property
    def parkir_tersedia(self):
        return bool(self.parkir_model_path) and os.path.isfile(self.parkir_model_path)

    def is_running(self):
        return self._thread is not None and self._thread.is_alive()

    def set_zones(self, sumber, zones):
        """Perbarui zona saat sesi berjalan, hanya bila zona itu milik sumber yang sedang aktif."""
        with self._lock:
            if self._state.get("sumber") == sumber:
                self._zones = zones

    def start(self, source, jenis, label, sesi_id, live, on_alert, on_finish, zones=None, full_analysis=False,
              mode="umum", jam_awal=None, on_mode=None, hasil_otomatis=None):
        """jam_awal: untuk berkas, menit sejak tengah malam saat rekaman dimulai (jam aktif zona mengikuti
        jam di dalam rekaman, bukan jam komputer). None = pakai jam komputer.
        mode 'otomatis': mode umum atau parkir diputuskan setelah OTOMATIS_S detik, lalu on_mode(mode, alasan)
        dipanggil. hasil_otomatis: hasil mode otomatis terakhir untuk sumber ini."""
        if self.is_running():
            raise RuntimeError("Kamera masih berjalan. Hentikan dahulu sebelum memulai sumber lain.")
        if mode not in MODE:
            raise RuntimeError("Mode deteksi tidak dikenal.")
        if mode in ("parkir", "otomatis") and not self.parkir_tersedia:
            raise RuntimeError("Model parkiran (models/motor.pt) tidak ditemukan.")
        self._stop.clear()
        self._on_mode, self._hasil_otomatis = on_mode, hasil_otomatis
        self._zones = zones
        self._mode = mode
        self._jam_awal = jam_awal if not live else None
        with self._lock:
            self._state = self._idle_state()
            self._state.update(berjalan=True, sumber=label, jenis=jenis, sesi_id=sesi_id, mulai=time.time(), mode=mode,
                               mode_otomatis=mode == "otomatis")
        self._full_analysis = full_analysis
        self._thread = threading.Thread(target=self._run, args=(source, live, on_alert, on_finish), daemon=True)
        self._thread.start()

    def stop(self, wait=True):
        self._stop.set()
        if wait and self._thread is not None:
            self._thread.join(timeout=10)

    # baca keadaan
    def status(self):
        with self._lock:
            state = dict(self._state)
            state["orang"] = list(state["orang"])
            if state["mulai"]:
                state["durasi_sesi"] = (state["selesai"] or time.time()) - state["mulai"]
        return state

    def wait_frame(self, last_id, timeout=1.0):
        with self._frame_cond:
            if self._frame_id == last_id:
                self._frame_cond.wait(timeout)
            return self._frame_id, self._jpeg

    def _sambung_ulang(self, source, jenis, sesi, reader):
        """Buka ulang kamera yang terputus. Kembalikan LatestFrameReader baru, atau None bila menyerah/dihentikan."""
        if reader:
            reader.release()
        percobaan = 0
        while not self._stop.is_set():
            percobaan += 1
            if jenis == "webcam" and percobaan > WEBCAM_COBA:
                return None
            tunggu = min(2.0 ** percobaan, SAMBUNG_MAKS_S)
            pesan = f"Koneksi kamera terputus. Menyambung ulang dalam {tunggu:.0f} detik (percobaan {percobaan})."
            logger.warning("Sesi %s: %s", sesi, pesan)
            with self._lock:
                self._state.update(tahap="Menyambung ulang…", galat=pesan)
            if self._stop.wait(tunggu):
                return None
            capture = self._open_capture(source)
            if capture.isOpened():
                ok, _ = capture.read()
                if ok:
                    logger.info("Sesi %s: kamera tersambung kembali setelah %d percobaan", sesi, percobaan)
                    with self._lock:
                        self._state.update(tahap="Berjalan", galat=None)
                    return LatestFrameReader(capture)
            capture.release()
        return None

    # inti
    def _run(self, source, live, on_alert, on_finish):
        frames, status, note = 0, "selesai", ""
        capture = reader = None
        sesi = self._state.get("sesi_id")
        t_sesi = time.time()
        try:
            if not self._ready.is_set():
                self._set_stage("Memuat model deteksi…")
                logger.info("Sesi %s menunggu pemanasan model selesai…", sesi)
                self._ready.wait()
            if self._warmup_error:
                raise RuntimeError("Model gagal dimuat: " + self._warmup_error)
            from ultralytics import YOLO

            self._set_stage("Membuka kamera…" if live else "Membuka berkas video…")
            capture = self._open_capture(source)
            if not capture.isOpened():
                raise RuntimeError("Sumber video gagal dibuka. Periksa nomor webcam, alamat RTSP, atau berkas video.")
            video_fps = capture.get(cv2.CAP_PROP_FPS) or 25.0
            if video_fps <= 0 or video_fps > 120:
                video_fps = 25.0
            width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
            total = int(capture.get(cv2.CAP_PROP_FRAME_COUNT)) if not live else 0
            logger.info("Sesi %s: sumber terbuka dalam %.1f detik | %dx%d | %.1f fps%s", sesi, time.time() - t_sesi,
                        width, height, video_fps,
                        f" | ±{total} frame ({total / video_fps:.0f} detik)" if total > 0 else " | langsung")
            reader = LatestFrameReader(capture) if live else None
            otomatis = self._mode == "otomatis"   # selama penentuan, aturan parkiran dan umum berjalan bersama
            parkir = self._mode == "parkir" or otomatis
            # model baru per sesi agar status tracker bersih (bobot sudah di cache)
            model = YOLO(self.parkir_model_path if parkir else self.model_path)
            person_cls, motor_cls = kelas_model(model.names, "parkir" if parkir else "umum")
            classes = [person_cls, motor_cls] if parkir else [person_cls]
            logger.info("Sesi %s: mode %s, model %s", sesi, self._mode,
                        os.path.basename(self.parkir_model_path if parkir else self.model_path))
            self._set_stage("Menunggu gambar pertama…")
            behavior = BehaviorTracker(gap_s=self.link_gap_s, zones=self._zones, mode="parkir" if parkir else "umum",
                                       parkir_dekat_s=self.parkir_dekat_s)
            calon_umum = BehaviorTracker(gap_s=self.link_gap_s, zones=self._zones, mode="umum") if otomatis else None
            start, tick, fps_hist = time.time(), time.time(), deque(maxlen=30)
            decoded = skipped = 0
            next_log, first_logged, alerts_total = time.time() + self.progress_s, False, 0
            jenis = self._state.get("jenis")
            gambar_terakhir = time.time()
            while not self._stop.is_set():
                if live:
                    ok, frame = reader.read()
                    if frame is None:
                        macet = time.time() - gambar_terakhir > STREAM_DIAM_S
                        if not ok or macet:
                            if macet:
                                logger.warning("Sesi %s: tidak ada gambar baru selama %.0f detik", sesi, STREAM_DIAM_S)
                            reader = self._sambung_ulang(source, jenis, sesi, reader)
                            if reader is None:
                                if not self._stop.is_set():
                                    status, note = "terputus", "Stream berhenti atau terputus dan gagal disambung ulang."
                                break
                            gambar_terakhir = time.time()
                            continue
                        time.sleep(0.005)
                        continue
                    gambar_terakhir = time.time()
                    t = time.time() - start
                else:
                    # Berkas: waktu = nomor frame / fps video (detik di dalam video, bukan jam komputer).
                    if not self._full_analysis and frames > 0:
                        # Putar sesuai waktu asli: frame yang sudah terlambat dilewati tanpa diproses.
                        # Jam putar baru berjalan setelah gambar pertama tampil (lihat di bawah).
                        late = time.time() - start
                        while (decoded + 1) / video_fps < late and capture.grab():
                            decoded += 1
                            skipped += 1
                    ok, frame = capture.read()
                    if not ok:
                        break
                    t = decoded / video_fps
                    decoded += 1
                    ahead = start + t - time.time()
                    if ahead > 0:  # jangan lebih cepat dari waktu aslinya
                        time.sleep(ahead)
                now_loop = time.time()
                result = model.track(frame, persist=True, classes=classes, conf=self.confidence, imgsz=self.image_size,
                                     tracker=self.tracker_path, device=self.device, verbose=False)[0]
                dets, motor_dets = [], []
                if result.boxes is not None and result.boxes.id is not None:
                    for box, tid, cls, conf in zip(result.boxes.xyxy.cpu().numpy(), result.boxes.id.int().cpu().tolist(),
                                                   result.boxes.cls.int().cpu().tolist(), result.boxes.conf.cpu().tolist()):
                        if cls == person_cls:
                            dets.append((tid, *[float(v) for v in box]))
                        elif cls == motor_cls and conf >= MOTOR_CONF:
                            motor_dets.append((tid, *[float(v) for v in box]))
                with self._lock:
                    self._raw = frame
                zones = self._zones
                if behavior.zones is not zones:  # zona diubah dari halaman Cam
                    behavior.set_zones(zones)
                # jam aktif zona: jam di dalam rekaman bila diisi, selain itu jam komputer
                menit = int(self._jam_awal + t / 60) % 1440 if self._jam_awal is not None else menit_sekarang()
                ukuran = (frame.shape[1], frame.shape[0])
                people = behavior.update(t, dets, ukuran, motors=motor_dets, menit=menit,
                                         frame=frame if parkir else None)
                if otomatis:
                    if calon_umum.zones is not zones:
                        calon_umum.set_zones(zones)
                    people_umum = calon_umum.update(t, dets, ukuran, menit=menit)
                    if t >= OTOMATIS_S:
                        n_parkir = sum(1 for m in behavior.parkir.snapshot(t) if m[2])
                        pilih, alasan = putuskan_mode(n_parkir, self._hasil_otomatis)
                        otomatis = False
                        if pilih == "umum":   # aturan umum dengan riwayat sejak detik 0
                            behavior, people, parkir = calon_umum, people_umum, False
                        calon_umum = None
                        self._mode = pilih
                        with self._lock:
                            self._state.update(mode=pilih, mode_alasan=alasan)
                        logger.info("Sesi %s: mode otomatis memilih %s (%s)", sesi, pilih, alasan)
                        if self._on_mode:
                            self._on_mode(pilih, alasan)
                motors = behavior.parkir.snapshot(t) if parkir else None
                now = time.time()
                fps_hist.append(1.0 / max(now - tick, 1e-6))
                tick = now
                shown = draw(frame.copy(), people, f"{np.mean(fps_hist):.1f} fps", live, zones, menit, motors)
                new_alerts = 0
                # selama mode otomatis belum diputuskan, peringatan ditahan; aturan pemenang tetap
                # menyimpan riwayat sejak detik 0, jadi peringatannya muncul tepat setelah keputusan
                for pid, box, *_ in (people if not otomatis else []):
                    person = behavior.people.get(pid)
                    for kategori, zona, why in (person or {}).get("events", []):
                        # satu peringatan per orang per kategori; untuk zona sensitif/terlarang juga per zona
                        key = (kategori, zona if kategori in ("sensitif", "terlarang") else None)
                        if key in person["alerted"]:
                            continue
                        person["alerted"].add(key)
                        on_alert(t, pid, why, [int(v) for v in box], shown, kategori, zona)
                        new_alerts += 1
                        logger.warning("PERINGATAN sesi %s | detik %.1f | ID %s | %s%s | %s", sesi, t, pid,
                                       kategori or "-", f" | zona {zona}" if zona else "", why)
                for pid, box, kategori, why in (behavior.tak_terlihat if not otomatis else []):  # hilang di balik motor
                    person = behavior.people.get(pid)
                    if person is None or box is None or (kategori, None) in person["alerted"]:
                        continue
                    person["alerted"].add((kategori, None))
                    on_alert(t, pid, why, [int(v) for v in box], shown, kategori, None)
                    new_alerts += 1
                    logger.warning("PERINGATAN sesi %s | detik %.1f | ID %s (tidak terlihat) | %s | %s", sesi, t, pid,
                                   kategori, why)
                ok_jpg, buf = cv2.imencode(".jpg", shown, [cv2.IMWRITE_JPEG_QUALITY, 80])
                if ok_jpg:
                    with self._frame_cond:
                        self._jpeg, self._frame_id = buf.tobytes(), self._frame_id + 1
                        self._frame_cond.notify_all()
                frames += 1
                alerts_total += new_alerts
                if not first_logged:
                    first_logged = True
                    logger.info("Sesi %s: gambar pertama tampil %.1f detik setelah Mulai", sesi, time.time() - t_sesi)
                    if not live:
                        start = time.time() - t  # jam putar mulai dari gambar pertama, bukan dari tombol Mulai
                elif not live:
                    lambat = time.time() - now_loop
                    if lambat > STALL_S:
                        # satu frame butuh waktu tidak wajar (komputer tersendat): jangan lompati video
                        start += lambat - 1.0 / video_fps
                        logger.warning("Sesi %s: pemrosesan tersendat %.1f detik; pemutaran dilanjutkan tanpa melompati video",
                                       sesi, lambat)
                if self.progress_s and time.time() >= next_log:
                    next_log = time.time() + self.progress_s
                    n_sus = sum(1 for r in people if r[2])
                    posisi = f"detik video {t:6.1f}" if not live else f"berjalan {t:6.1f} dtk"
                    logger.info("Sesi %s | %s | %5d frame diproses | %4.1f fps | dilewati %d | orang %d (suspicious %d)%s | peringatan %d",
                                sesi, posisi, frames, float(np.mean(fps_hist)), skipped, len(people), n_sus,
                                f" | motor {len(motors)} ({sum(1 for m in motors if m[2])} parkir)" if parkir else "",
                                alerts_total)
                    for pid, _, label, why, dur, _, _, zona in people:
                        logger.debug("   ID %s %-10s %5.1f dtk%s | %s", pid, "SUSPICIOUS" if label else "safe", dur,
                                     f" | zona {zona}" if zona else "", why)
                with self._lock:
                    self._state.update(
                        tahap="Berjalan", dilewati=skipped,
                        motor=len(motors) if parkir else 0,
                        motor_parkir=sum(1 for m in motors if m[2]) if parkir else 0,
                        detik=t, fps=float(np.mean(fps_hist)), frame=frames,
                        peringatan_sesi=self._state["peringatan_sesi"] + new_alerts,
                        orang=[{"id": pid, "kelas": "suspicious" if label else "safe", "durasi": round(dur, 1),
                                "alasan": why, "zona": zona} for pid, _, label, why, dur, _, _, zona in people])
            if self._stop.is_set():
                status = "dihentikan"
        except Exception as error:  # galat dilaporkan ke halaman, bukan menghentikan server
            status, note = "galat", str(error)
            logger.error("Sesi %s galat: %s", sesi, error)
            logger.debug("Rincian galat", exc_info=True)
            with self._lock:
                self._state["galat"] = note
        finally:
            if reader:
                reader.release()
            elif capture:
                capture.release()
            with self._lock:
                self._state.update(berjalan=False, orang=[], selesai=time.time(), tahap=None)
            on_finish(frames, status, note)
            durasi = time.time() - t_sesi
            logger.info("Sesi %s %s | %.1f detik | %d frame diproses (%.1f fps rata-rata) | %d dilewati | %s",
                        sesi, status.upper(), durasi, frames, frames / durasi if durasi > 0 else 0,
                        locals().get("skipped", 0), note or f"{self._state.get('peringatan_sesi', 0)} peringatan")
