"""Business tier: aturan perilaku, pembaca frame kamera, dan penggambar kotak.

Logika ini sama dengan pipeline yang dievaluasi (YOLO26s train-4, BoT-SORT + ReID,
penyambungan ID 2 detik). Aturan: orang terlihat >= DWELL_S detik DAN sebaran titik pusat
<= EXTENT_H x tinggi kotak (area terbatas) ATAU jalur >= PATH_H x tinggi dan jalur/perpindahan
bersih >= TORTUOSITY (mondar-mandir). Sumber ambang: Patel dkk. 2021 (20 detik, doi:10.3233/SW-200393);
waktu tinggal dan area aktivitas: Wahyono dkk. 2023 (doi:10.3390/jsan12010009); perubahan arah:
doi:10.1186/s13640-021-00576-0. Nilai 5, 3, dan 2,5 adalah pilihan penelitian ini.
"""
import math
import threading
import time
from collections import deque

import cv2
import numpy as np

from .parking import ParkingMonitor, iou as _iou

DWELL_S = 20
EXTENT_H = 5.0
PATH_H = 3.0
TORTUOSITY = 2.5
GREEN, RED = (0, 200, 0), (0, 0, 255)


class LatestFrameReader:
    """Baca kamera/stream di thread terpisah dan simpan hanya frame terbaru (hindari antrean tertinggal)."""

    def __init__(self, capture, pace_fps=0.0):
        self.capture, self.frame, self.ok, self.stopped = capture, None, True, False
        self.pace = 1.0 / pace_fps if pace_fps > 0 else 0.0  # untuk file yang diuji sebagai kamera
        self.dropped = 0
        self.lock = threading.Lock()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def _run(self):
        next_t = time.time()
        while not self.stopped:
            ok, frame = self.capture.read()
            with self.lock:
                if ok and self.frame is not None:
                    self.dropped += 1
                self.ok, self.frame = ok, frame if ok else self.frame
            if self.pace:
                next_t += self.pace
                time.sleep(max(0.0, next_t - time.time()))
            if not ok:
                break

    def read(self):
        with self.lock:
            frame, self.frame = self.frame, None
            return self.ok or frame is not None, frame

    def release(self):
        self.stopped = True
        self.thread.join(timeout=1)
        self.capture.release()


RESAMPLE_S = 1.0     # posisi dirata-rata per 1 detik agar getaran kotak dan fps tidak menambah jarak tempuh
ZONE_GRACE_S = 1.5   # keluar zona sebentar (kaki goyah di tepi) tidak mengulang hitungan
ENTRY_S = 1.0        # minimal berada di zona terlarang sebelum dianggap masuk
SPEED_H = 0.3        # "diam" bila kecepatan median < 0,3 x tinggi badan per detik
DEPTH_RATIO = 1.25   # tinggi kotak berubah >= 25% dalam 20 detik = berjalan mendekat/menjauh kamera
DEPTH_SPEED_H = 0.08 # ...asal titik pusat juga bergeser >= 0,08xH/detik; orang diam yang membungkuk tidak lolos
KELUAR_TEPI_S = 1.0  # orang yang terakhir terlihat di tepi gambar dan hilang > 1 detik dianggap sudah keluar
DUPLIKAT_IOU = 0.5   # dua kotak satu orang pada frame yang sama bila bertumpuk >= 50%
EDGE_PX = 2          # kotak yang menyentuh tepi gambar terpotong; tingginya tidak dipakai


class BehaviorTracker:
    """Penilaian perilaku online per orang, memakai waktu (detik) agar tidak bergantung pada fps.

    Tanpa zona: aturan umum, setelah terlihat 20 detik:
      - diam: sebaran <= 5xH DAN kecepatan median < 0,3xH/detik, kecuali tinggi kotak berubah >= 25%
              sambil titik pusat bergeser >= 0,08xH/detik (berjalan mendekat/menjauh kamera)
      - mondar-mandir: jalur >= 3xH DAN jalur/perpindahan bersih >= 2,5
    Dengan zona (posisi = titik kaki):
      - terlarang : masuk >= 1 detik -> suspicious
      - santai    : selalu safe (duduk, main gim, tidur dianggap wajar)
      - sensitif  : berada >= 20 detik di zona yang sama -> suspicious
      - di luar zona atau sensitif < 20 detik: hanya mondar-mandir (setelah 20 detik) yang suspicious
    Zona di luar jam aktifnya diabaikan.
    Mode parkiran (mode="parkir"): aturan "diam" umum tidak dipakai (orang menunggu dan petugas
    parkir wajar diam), lalu aturan interaksi orang dan motor di parking.py ditambahkan.
    """

    def __init__(self, gap_s=2.0, link_h=2.0, min_coverage=0.5, zones=None, mode="umum", parkir_dekat_s=None):
        self.gap_s, self.link_h, self.min_coverage = gap_s, link_h, min_coverage
        self.zones = zones
        self.mode = mode
        self.parkir = None
        if mode == "parkir":
            self.parkir = ParkingMonitor(**({"dekat_s": parkir_dekat_s} if parkir_dekat_s else {}))
            # orang yang jongkok di balik motor sering hilang beberapa detik: sambung ID sampai 5 detik
            self.gap_s = max(gap_s, 5.0) if gap_s > 0 else gap_s
        self.menit = None  # menit sejak tengah malam, untuk jam aktif zona
        self.tak_terlihat = []  # mode parkiran: (pid, kotak terakhir, kategori, alasan) orang yang tidak terlihat
        self.alias = {}    # id tracker -> id orang (setelah penyambungan)
        self.people = {}   # id orang -> data jejak
        self.next_person = 1

    def set_zones(self, zones):
        self.zones = zones

    def _new_person(self, t, tid=None):
        pid = self.next_person
        self.next_person += 1
        self.people[pid] = {"first": t, "hist": deque(), "last_t": t, "label": 0, "why": "", "kategori": None,
                            "zone": None, "zone_enter": None, "zone_last": None, "alerted": set(),
                            "events": [], "tid_asal": tid}
        return pid

    def _petakan(self, t, detections):
        """Tentukan orang (pid) untuk setiap kotak pada frame ini.

        Track baru disambungkan ke orang yang baru saja hilang (track putus). Bila dua kotak jatuh ke
        orang yang sama pada frame yang sama:
        - kotaknya bertumpuk: kotak ganda untuk satu orang, yang dipakai satu saja;
        - kotaknya terpisah: dua orang berbeda. Track asli orang itu tetap memakai ID-nya, track yang
          keliru disambungkan diberi orang baru. Tanpa aturan ini orang asli bisa terbuang karena ID-nya
          sudah dipakai deteksi lain (misalnya deteksi palsu pada tumpukan motor).
        """
        dipakai = {}   # pid -> (tid, kotak)
        for tid, x1, y1, x2, y2 in detections:
            box = (x1, y1, x2, y2)
            if tid not in self.alias:
                linked = self._link(t, (x1 + x2) / 2, (y1 + y2) / 2, y2 - y1, set(dipakai)) if self.gap_s > 0 else None
                self.alias[tid] = linked if linked is not None else self._new_person(t, tid)
            pid = self.alias[tid]
            if pid in dipakai:
                tid_lain, box_lain = dipakai[pid]
                if _iou(box, box_lain) >= DUPLIKAT_IOU:
                    continue   # kotak ganda pada satu orang
                if self.people[pid].get("tid_asal") == tid:   # track asli kembali: yang lain salah sambung
                    self.alias[tid_lain] = baru = self._new_person(t, tid_lain)
                    dipakai[baru] = (tid_lain, box_lain)
                else:
                    self.alias[tid] = pid = self._new_person(t, tid)
            dipakai[pid] = (tid, box)
        return [(pid, tid, box) for pid, (tid, box) in dipakai.items()]

    def _link(self, t, cx, cy, h, active):
        best, best_d = None, None
        for pid, p in self.people.items():
            if pid in active or not p["hist"] or t - p["last_t"] > self.gap_s:
                continue
            _, px, py, ph, di_tepi = p["hist"][-1]
            if di_tepi and t - p["last_t"] > KELUAR_TEPI_S:
                continue   # sudah keluar lewat tepi gambar; track baru di dekat tepi adalah orang lain
            d = math.hypot(px - cx, py - cy) / max(min(h, ph), 8.0)
            if d <= self.link_h and (best_d is None or d < best_d):
                best, best_d = pid, d
        return best

    def _update_zone(self, p, t, foot, size):
        zone = None
        if self.zones and size:
            zone = self.zones.find(foot[0] / size[0], foot[1] / size[1], self.menit)
        prev = p["zone"]
        if zone is not None:
            same = prev is not None and prev.id == zone.id
            back_soon = (p.get("last_zone_id") == zone.id and p["zone_last"] is not None
                         and t - p["zone_last"] <= ZONE_GRACE_S)
            if not same and not back_soon:
                p["zone_enter"] = t
            p["zone"], p["zone_last"], p["last_zone_id"] = zone, t, zone.id
        elif prev is not None and t - p["zone_last"] > ZONE_GRACE_S:
            p["zone"], p["zone_enter"] = None, None

    def update(self, t, detections, size=None, motors=None, menit=None, frame=None):
        """detections: list (track_id, x1, y1, x2, y2); size: (lebar, tinggi) frame;
        motors: list (track_id, x1, y1, x2, y2) untuk mode parkiran; menit: menit sejak tengah malam;
        frame: gambar BGR (mode parkiran memakainya untuk mengenali penampilan pemilik motor).

        Kembalikan list (pid, kotak, label, alasan, durasi, track_id, kategori, nama_zona).
        Semua aturan yang sedang terpenuhi per orang ada di self.people[pid]["events"]
        sebagai list (kategori, zona, alasan).
        """
        self.menit = menit
        out = []
        for pid, tid, (x1, y1, x2, y2) in self._petakan(t, detections):
            cx, cy, h = (x1 + x2) / 2, (y1 + y2) / 2, y2 - y1
            p = self.people[pid]
            edge = bool(size) and (y1 <= EDGE_PX or x1 <= EDGE_PX or x2 >= size[0] - EDGE_PX
                                   or y2 >= size[1] - EDGE_PX)
            p["hist"].append((t, cx, cy, h, edge))
            p["last_t"] = t
            while p["hist"] and p["hist"][0][0] < t - DWELL_S - 1:
                p["hist"].popleft()
            self._update_zone(p, t, (cx, y2), size)
            p["label"], p["why"], p["kategori"] = self._classify(p, t)
            zone_name = p["zone"].nama if p["zone"] is not None else None
            p["events"] = [(p["kategori"], zone_name, p["why"])] if p["label"] else []
            out.append((pid, (x1, y1, x2, y2), p["label"], p["why"], t - p["first"], tid, p["kategori"], zone_name))
        if self.parkir is not None:
            out = self._gabung_parkir(t, out, motors or [], frame, size)
        # buang orang yang lama hilang agar memori tidak tumbuh
        for pid in [k for k, p in self.people.items() if t - p["last_t"] > max(60, self.gap_s * 5)]:
            del self.people[pid]
        return out

    def _gabung_parkir(self, t, out, motors, frame=None, size=None):
        """Tambahkan aturan parkiran. Peristiwa parkiran menjadi label utama bila aturan orang tidak terpenuhi."""
        persons = [(r[0], r[1], self.people[r[0]]["zone"]) for r in out]
        events = self.parkir.update(t, persons, [(tid, tuple(box)) for tid, *box in motors], frame, size)
        # peristiwa orang yang sedang tidak terlihat (hilang di balik motor): dilaporkan dengan kotak terakhirnya
        terlihat = {r[0] for r in out}
        self.tak_terlihat = [(pid, self.parkir.kotak_terakhir(pid), kat, alasan)
                             for pid, daftar in events.items() if pid not in terlihat and pid in self.people
                             for kat, alasan in daftar]
        hasil = []
        for pid, box, label, why, dur, tid, kategori, zona in out:
            p = self.people[pid]
            for kat, alasan in events.get(pid, []):
                p["events"].append((kat, None, alasan))
            if not label and events.get(pid):
                kategori, why = events[pid][0]
                label, p["label"], p["why"], p["kategori"] = 1, 1, why, kategori
            hasil.append((pid, box, label, why, dur, tid, kategori, zona))
        return hasil

    def _motion(self, p, t):
        """Ukur gerak pada jendela 20 detik terakhir, dari posisi rata-rata per RESAMPLE_S detik.

        Kembalikan dict: status (ok/pendek/putus), sebaran (xH), rasio (jalur/bersih), jalur (xH),
        kecepatan (median langkah per detik, xH lokal), kedalaman (rasio tinggi kotak akhir/awal).
        """
        kosong = {"status": "pendek", "sebaran": 0.0, "rasio": 0.0, "jalur": 0.0, "kecepatan": 0.0, "kedalaman": 1.0}
        if t - p["first"] < DWELL_S:
            return kosong
        win = [s for s in p["hist"] if s[0] >= t - DWELL_S]
        if len(win) < 2:
            return dict(kosong, status="putus")
        times = np.array([s[0] for s in win])
        gaps = np.diff(times)
        observed = DWELL_S - float(np.clip(gaps - 1.0, 0, None).sum()) - max(0.0, times[0] - (t - DWELL_S))
        if observed < DWELL_S * self.min_coverage:
            return dict(kosong, status="putus")
        # rata-rata posisi per RESAMPLE_S detik: lintasan tidak bergantung pada fps dan getaran kotak
        raw = np.array([[s[0], s[1], s[2], s[3], s[4]] for s in win], dtype=float)
        bins = np.floor((raw[:, 0] - raw[0, 0]) / RESAMPLE_S)
        per_bin = [raw[bins == b] for b in np.unique(bins)]
        pts = np.array([b[:, 1:3].mean(axis=0) for b in per_bin])
        tinggi = np.array([max(float(np.median(b[:, 3])), 8.0) for b in per_bin])
        utuh = np.array([not b[:, 4].any() for b in per_bin])  # tidak ada kotak terpotong tepi
        if len(pts) < 2:
            return dict(kosong, status="putus")
        h = max(float(np.median([s[3] for s in p["hist"]])), 8.0)
        extent = float(np.hypot(*(pts.max(0) - pts.min(0))))
        steps = np.hypot(*np.diff(pts, axis=0).T)
        path = float(steps.sum())
        net = float(np.hypot(*(pts[-1] - pts[0])))
        local_h = (tinggi[1:] + tinggi[:-1]) / 2
        kecepatan = float(np.median(steps / local_h))
        kedalaman = 1.0
        if utuh.sum() >= 6:  # bandingkan tinggi kotak 3 detik awal dan 3 detik akhir yang tidak terpotong
            hh = tinggi[utuh]
            awal, akhir = float(np.median(hh[:3])), float(np.median(hh[-3:]))
            kedalaman = max(awal, akhir) / min(awal, akhir)
        return {"status": "ok", "sebaran": extent / h, "rasio": path / max(net, 1.0), "jalur": path / h,
                "kecepatan": kecepatan, "kedalaman": kedalaman}

    def _classify(self, p, t):
        """Kembalikan (label, alasan, kategori)."""
        m = self._motion(p, t)
        status, spread, tortuosity = m["status"], m["sebaran"], m["rasio"]
        pacing = status == "ok" and m["jalur"] >= PATH_H and tortuosity >= TORTUOSITY
        if not self.zones and self.mode == "parkir":  # parkiran tanpa zona: hanya mondar-mandir
            if pacing:
                return 1, f"mondar-mandir (jalur/bersih {tortuosity:.1f})", "mondar-mandir"
            return 0, "Di area parkir" if status == "ok" else f"dwell<{DWELL_S}s", None
        if not self.zones:  # aturan umum
            if status == "pendek":
                return 0, f"dwell<{DWELL_S}s", None
            if status == "putus":
                return 0, "jejak putus", None
            if spread <= EXTENT_H:
                # diam = area sempit DAN lambat DAN jarak ke kamera tetap (bukan berjalan searah garis pandang)
                if m["kedalaman"] >= DEPTH_RATIO and m["kecepatan"] >= DEPTH_SPEED_H:
                    return 0, f"Berjalan mendekat/menjauh kamera (ukuran berubah {(m['kedalaman'] - 1) * 100:.0f}%)", None
                if m["kecepatan"] >= SPEED_H:
                    return 0, f"Bergerak terus ({m['kecepatan']:.2f}xH per detik)".replace(".", ","), None
                return 1, f"tinggal>={DWELL_S}s di area terbatas (sebaran {spread:.1f}xH)", "diam"
            if pacing:
                return 1, f"mondar-mandir (jalur/bersih {tortuosity:.1f})", "mondar-mandir"
            return 0, f"melintas (sebaran {spread:.1f}xH)", None
        zone = p["zone"]
        in_zone = t - p["zone_enter"] if zone is not None else 0.0
        if zone is not None and zone.jenis == "terlarang":
            if in_zone >= ENTRY_S:
                return 1, f"Masuk zona terlarang '{zone.nama}'", "terlarang"
            return 0, f"Mendekati zona terlarang '{zone.nama}'", None
        if zone is not None and zone.jenis == "santai":
            return 0, f"Berada di zona santai '{zone.nama}'", None
        if zone is not None and zone.jenis == "sensitif" and in_zone >= DWELL_S:
            return 1, f"Berada {in_zone:.0f} detik di zona sensitif '{zone.nama}'", "sensitif"
        if pacing:
            return 1, f"Bergerak mondar-mandir (rasio lintasan {tortuosity:.1f})".replace(".", ","), "mondar-mandir"
        if zone is not None:
            return 0, f"Berada {in_zone:.0f} detik di zona sensitif '{zone.nama}'", None
        return 0, "Di area umum, tidak mondar-mandir", None


MOTOR_PARKIR, MOTOR_JALAN = (230, 160, 0), (190, 190, 190)


def draw(frame, results, fps_text, live, zones=None, menit=None, motors=None):
    if zones:
        zones.draw(frame, menit)
    for mid, (x1, y1, x2, y2), parkir, pemilik, waspada in motors or []:
        color = RED if waspada else (MOTOR_PARKIR if parkir else MOTOR_JALAN)
        cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), color, 1 if not waspada else 2)
        text = f"M{mid} {'parkir' if parkir else 'jalan'}" + (" pemilik " + ",".join(str(i) for i in pemilik) if pemilik else "")
        cv2.putText(frame, text, (int(x1), min(int(y2) + 12, frame.shape[0] - 4)), cv2.FONT_HERSHEY_SIMPLEX, 0.38,
                    color, 1, cv2.LINE_AA)
    for pid, (x1, y1, x2, y2), label, _, dur, *_ in results:
        color = RED if label else GREEN
        cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), color, 2)
        text = f"ID {pid} {'SUSPICIOUS' if label else 'safe'} {dur:.0f}s"
        ty = int(y1) - 5 if y1 >= 36 else int(y2) + 14  # hindari tertutup baris judul
        cv2.putText(frame, text, (int(x1), min(ty, frame.shape[0] - 4)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1, cv2.LINE_AA)
    n_sus = sum(1 for r in results if r[2])
    header = f"{'LANGSUNG' if live else 'FILE'} | {fps_text} | orang {len(results)} | suspicious {n_sus}"
    if motors is not None:
        header += f" | motor {len(motors)}"
    cv2.rectangle(frame, (0, 0), (min(frame.shape[1], 9 * len(header)), 20), (0, 0, 0), -1)
    cv2.putText(frame, header, (4, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)
    return frame
