"""Business tier: aturan mode parkiran motor.

Model parkiran (motor.pt) mendeteksi orang dan motor. Modul ini membaca interaksi keduanya:

1. Motor terparkir   : kotak motor diam >= PARKIR_S detik (>= PARKIR_AWAL_S detik untuk motor yang
                       sudah ada saat sesi dimulai, karena motor itu jelas sudah terparkir).
2. Pemilik           : pengendara dan pembonceng yang datang bersama motor (motor terlihat bergerak
                       lalu berhenti). Penampilan mereka (warna pakaian atas dan bawah) disimpan, sehingga
                       pemilik yang pergi lalu kembali dengan ID baru tetap dikenali. Motor yang sudah diam
                       sejak awal rekaman tidak punya pemilik yang diketahui.
3. Dekat motor       : bukan pemilik, kaki berada dalam jarak <= DEKAT_FAKTOR x tinggi kotak motor
                       selama >= dekat_s detik (bawaan 15). Jarak adaptif dan ambang 15 detik mengikuti
                       Adeel dkk. 2026, Information 17(7):676 (doi:10.3390/info17070676).
4. Jongkok di motor  : bukan pemilik, tinggi kotak turun ke <= 65% tinggi berdirinya sambil diam di dekat
                       motor selama >= JONGKOK_S detik (posisi khas membobol kunci).
5. Pindah motor      : mendekati >= PINDAH_N motor berbeda (masing-masing >= KUNJUNGAN_S detik)
                       dalam PINDAH_JENDELA_S detik.
6. Motor didorong    : motor terparkir berpindah >= DORONG_JAUH x tingginya sambil dibawa orang
                       yang tidak duduk di atasnya selama >= DORONG_S detik.
7. Hilang di motor   : bukan pemilik, lenyap dari pandangan saat berada di dekat motor (tidak keluar lewat
                       tepi gambar), dan total waktu sejak mendekati motor >= dekat_s detik. Pencuri sering
                       berjongkok di balik motor sehingga detektor tidak melihatnya.
8. Motor dibawa      : penampilan pemilik tersimpan, tetapi motor dibawa pergi (dikendarai atau didorong)
                       oleh orang yang penampilannya berbeda.

Pencocokan penampilan memakai histogram warna HSV bagian atas dan bawah badan (pada rekaman
inframerah hitam-putih: histogram kecerahan), dibandingkan dengan jarak Bhattacharyya. Cara ini
adalah pembanding dasar re-identifikasi orang, bukan model ReID terlatih: pakaian yang mirip bisa
tertukar. Aturan 2, 4 sampai 7 adalah rancangan penelitian ini, belum divalidasi pada data lapangan.
Semua ambang perlu dikalibrasi lewat penilaian petugas.
"""
import math
from collections import deque

import cv2
import numpy as np

PARKIR_S = 10.0           # motor dianggap terparkir bila diam 10 detik
PARKIR_AWAL_S = 3.0       # motor yang sudah terlihat di 2 detik pertama sesi: cukup diam 3 detik
AWAL_S = 2.0
PARKIR_GERAK = 0.3        # ... dengan pergeseran titik pusat <= 0,3 x tinggi kotak motor
DEKAT_FAKTOR = 1.0        # jarak kaki ke kotak motor <= 1 x tinggi kotak motor (Adeel dkk. 2026)
DEKAT_S = 15.0            # lama berada dekat motor orang lain (Adeel dkk. 2026)
LEPAS_S = 2.0             # menjauh sebentar tidak mengulang hitungan
HILANG_S = 5.0            # orang tidak terdeteksi (jongkok di balik motor) sampai 5 detik tidak mengulang hitungan
SEMBUNYI_S = 60.0         # orang yang lenyap di dekat motor (bukan keluar lewat tepi gambar) lalu muncul lagi di
                          # motor yang sama <= 60 detik kemudian: waktu bersembunyinya ikut dihitung
TEPI = 0.03               # kotak dalam 3% dari tepi gambar = orang keluar dari gambar, bukan bersembunyi
KUNJUNGAN_S = 3.0         # dekat satu motor >= 3 detik dihitung satu kunjungan
PINDAH_N = 3              # mendekati >= 3 motor berbeda ...
PINDAH_JENDELA_S = 60.0   # ... dalam 60 detik
GESER_H = 1.0             # motor terparkir bergeser >= 1 x tingginya = mulai dipindahkan
DORONG_JAUH = 3.0         # didorong sejauh >= 3 x tinggi motor (bukan sekadar memundurkan motor) ...
DORONG_S = 4.0            # ... selama >= 4 detik tanpa dikendarai
DIBAWA_S = 2.0            # motor dibawa orang yang bukan pemilik selama >= 2 detik
TUMPANG_KENDARA = 0.35    # >= 35% kotak orang menumpang kotak motor dan kaki sejajar roda = duduk di motor
PEMILIK_S = 15.0          # pengendara/pembonceng yang terlihat <= 15 detik sebelum motor terparkir menjadi pemilik
TUMPANG_BONCENG = 0.2     # pembonceng: >= 20% kotak orang menumpang motor dan kakinya di dalam rentang tinggi motor
INGAT_MOTOR_S = 30.0      # motor terparkir yang sempat hilang (tertutup) dikenali lagi bila muncul di tempat sama
JONGKOK_RASIO = 0.65      # tinggi kotak <= 65% tinggi berdiri orang itu sendiri
JONGKOK_S = 5.0
SAMA_ORANG = 0.40         # jarak Bhattacharyya < 0,40 = penampilan sama
CIRI_JEDA_S = 0.5         # ambil contoh penampilan paling sering 2 kali per detik
CIRI_MAKS = 8             # simpan 8 contoh penampilan per orang
SEJAJAR_KAKI = 0.6        # kaki orang dan roda motor berselisih <= 0,6 x tinggi motor pada sumbu tegak gambar
SEJAJAR_TINGGI = (0.5, 3.5)  # tinggi orang 0,5 sampai 3,5 x tinggi motor (jongkok sampai berdiri dekat kamera)
KATEGORI = ("motor_dibawa", "motor_didorong", "jongkok_motor", "hilang_dekat_motor", "dekat_motor",
            "pindah_motor")  # urutan prioritas


def jarak_ke_kotak(x, y, box):
    """Jarak titik (x, y) ke tepi kotak; 0 bila titik di dalam kotak."""
    x1, y1, x2, y2 = box
    return math.hypot(max(x1 - x, 0.0, x - x2), max(y1 - y, 0.0, y - y2))


def tumpang(person_box, motor_box):
    """Bagian kotak orang yang menumpang kotak motor (0 sampai 1)."""
    px1, py1, px2, py2 = person_box
    mx1, my1, mx2, my2 = motor_box
    iw, ih = min(px2, mx2) - max(px1, mx1), min(py2, my2) - max(py1, my1)
    luas = max((px2 - px1) * (py2 - py1), 1.0)
    return max(iw, 0.0) * max(ih, 0.0) / luas


def iou(a, b):
    iw, ih = min(a[2], b[2]) - max(a[0], b[0]), min(a[3], b[3]) - max(a[1], b[1])
    inter = max(iw, 0.0) * max(ih, 0.0)
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union if union > 0 else 0.0


def sejajar(person_box, motor_box):
    """Orang berdiri pada kedalaman yang sama dengan motor, bukan jauh di belakangnya.

    Pada gambar 2D, orang yang berjalan jauh di belakang motor bisa tampak dekat (masalah perspektif
    yang juga dibahas Adeel dkk. 2026). Orang di samping motor menapak pada baris gambar yang hampir
    sama dengan roda motor, dan tinggi badannya sebanding dengan tinggi motor.
    """
    mh = max(motor_box[3] - motor_box[1], 1.0)
    ph = person_box[3] - person_box[1]
    return abs(person_box[3] - motor_box[3]) <= SEJAJAR_KAKI * mh and SEJAJAR_TINGGI[0] <= ph / mh <= SEJAJAR_TINGGI[1]


def bersama_motor(person_box, motor_box):
    """Pengendara atau pembonceng: kotak orang menumpang motor dan kakinya berada di rentang tinggi motor."""
    h = max(motor_box[3] - motor_box[1], 1.0)
    return (tumpang(person_box, motor_box) >= TUMPANG_BONCENG
            and motor_box[1] <= person_box[3] <= motor_box[3] + 0.5 * h)


def mengendarai(person_box, motor_box):
    """Orang duduk di atas motor: kotaknya banyak menumpang kotak motor dan kakinya sejajar roda."""
    h = max(motor_box[3] - motor_box[1], 1.0)
    return tumpang(person_box, motor_box) >= TUMPANG_KENDARA and abs(person_box[3] - motor_box[3]) <= 0.5 * h


def ciri_penampilan(frame, box):
    """Histogram warna bagian atas (bahu sampai pinggang) dan bawah (pinggang sampai kaki) badan.

    Kembalikan (hitam_putih, [hist_atas, hist_bawah]) atau None bila kotak terlalu kecil.
    """
    if frame is None:
        return None
    fh, fw = frame.shape[:2]
    x1, y1, x2, y2 = (int(round(v)) for v in box)
    x1, y1, x2, y2 = max(x1, 0), max(y1, 0), min(x2, fw), min(y2, fh)
    if x2 - x1 < 8 or y2 - y1 < 24:
        return None
    lebar = x2 - x1
    crop = frame[y1:y2, x1 + lebar // 5:x2 - lebar // 5]  # buang tepi kiri-kanan yang berisi latar
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    tinggi = hsv.shape[0]
    hitam_putih = float(hsv[..., 1].mean()) < 25  # kamera inframerah malam: warna tidak bisa dipakai
    hist = []
    for a, b in ((0.15, 0.55), (0.55, 0.95)):
        bagian = hsv[int(tinggi * a):int(tinggi * b)]
        if bagian.size == 0:
            return None
        if hitam_putih:
            h = cv2.calcHist([bagian], [2], None, [32], [0, 256])
        else:
            h = cv2.calcHist([bagian], [0, 1], None, [16, 8], [0, 180, 0, 256])
        cv2.normalize(h, h, 1, 0, cv2.NORM_L1)
        hist.append(h)
    return hitam_putih, hist


def beda_penampilan(a, b):
    """Jarak Bhattacharyya berbobot atas dan bawah badan (0 = sama persis, 1 = berbeda total)."""
    if a is None or b is None or a[0] != b[0]:
        return None
    atas, bawah = (cv2.compareHist(x, y, cv2.HISTCMP_BHATTACHARYYA) for x, y in zip(a[1], b[1]))
    return float(0.65 * atas + 0.35 * bawah)  # bagian bawah sering tertutup motor; bagian atas lebih andal


class ParkingMonitor:
    def __init__(self, dekat_s=DEKAT_S):
        self.dekat_s = float(dekat_s)
        self.motors = {}     # id motor internal -> keadaan
        self.alias = {}      # id track motor -> id motor internal
        self.orang = {}      # id orang -> keadaan aturan parkiran
        self.ciri = {}       # id orang -> deque contoh penampilan
        self.next_motor = 1
        self.t0 = None
        self._size, self._terlihat = None, set()

    # penampilan
    def _catat_ciri(self, t, frame, persons):
        if frame is None:
            return
        for pid, box, _ in persons:
            q = self.ciri.setdefault(pid, deque(maxlen=CIRI_MAKS))
            if q and t - q[-1][0] < CIRI_JEDA_S:
                continue
            c = ciri_penampilan(frame, box)
            if c is not None:
                q.append((t, c))

    def _beda_dengan_pemilik(self, pid, m):
        """Jarak penampilan terkecil antara orang ini dan pemilik motor; None bila tidak bisa dinilai."""
        if not m["ciri_pemilik"] or not self.ciri.get(pid):
            return None
        jarak = [beda_penampilan(a, b) for _, a in self.ciri[pid] for _, _, b in m["ciri_pemilik"]]
        jarak = [d for d in jarak if d is not None]
        return min(jarak) if jarak else None

    def _pemilik(self, pid, m):
        """True bila orang ini pemilik motor: tercatat saat parkir, atau penampilannya cocok."""
        if pid in m["pemilik"]:
            return True
        d = self._beda_dengan_pemilik(pid, m)
        if d is not None and d < SAMA_ORANG:
            m["pemilik"].add(pid)  # pemilik kembali dengan ID baru
            return True
        return False

    # motor
    def _motor_baru(self, t, box):
        mid = self.next_motor
        self.next_motor += 1
        self.motors[mid] = {"id": mid, "hist": deque(), "box": box, "last_t": t, "pertama": t, "terparkir": False,
                            "jangkar": None, "pemilik": set(), "ciri_pemilik": [], "pengendara": {}, "pindah": None,
                            "awal": ((box[0] + box[2]) / 2, (box[1] + box[3]) / 2), "datang": False,
                            "waspada_t": -1e9}
        return mid

    def _kenali(self, t, tid, box, aktif):
        if tid in self.alias and self.alias[tid] in self.motors:
            return self.alias[tid]
        terbaik, skor = None, 0.5
        for mid, m in self.motors.items():  # motor terparkir yang sempat hilang, muncul lagi di tempat sama
            if mid in aktif or not m["terparkir"] or t - m["last_t"] > 600:
                continue
            s = iou(box, m["box"])
            if s >= skor:
                terbaik, skor = mid, s
        self.alias[tid] = terbaik if terbaik is not None else self._motor_baru(t, box)
        return self.alias[tid]

    def _perbarui_motor(self, m, t, box, persons):
        cx, cy, h = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2, max(box[3] - box[1], 8.0)
        m["box"], m["last_t"] = box, t
        m["hist"].append((t, cx, cy, h))
        if not m["datang"] and math.hypot(cx - m["awal"][0], cy - m["awal"][1]) / h >= GESER_H:
            m["datang"] = True  # motor terlihat bergerak: orang yang bersamanya memang datang dengan motor itu
        while m["hist"] and m["hist"][0][0] < t - PARKIR_S - 2:
            m["hist"].popleft()
        # siapa yang bersama motor (calon pemilik bila motor lalu terparkir)
        if not m["terparkir"]:
            for pid, pbox, _ in persons:
                if bersama_motor(pbox, box):
                    m["pengendara"][pid] = t
        if m["terparkir"]:
            jx, jy = m["jangkar"]
            if math.hypot(cx - jx, cy - jy) / h >= GESER_H:  # motor terparkir mulai dipindahkan
                m["terparkir"] = False
                m["pindah"] = {"mulai": t, "dorong_s": 0.0, "asing_s": 0.0, "t": t, "jangkar": (jx, jy, h)}
            return
        # cek apakah motor sudah diam cukup lama untuk dianggap terparkir
        perlu = PARKIR_AWAL_S if m["pertama"] - self.t0 <= AWAL_S and not m["datang"] else PARKIR_S
        if t - m["hist"][0][0] < perlu * 0.9:
            return
        win = np.array([(x, y, hh) for tt, x, y, hh in m["hist"] if tt >= t - perlu])
        if len(win) < 3:
            return
        sebaran = float(np.hypot(*(win[:, :2].max(0) - win[:, :2].min(0))))
        if sebaran <= PARKIR_GERAK * float(np.median(win[:, 2])):
            m["terparkir"] = True
            m["jangkar"] = tuple(np.median(win[:, :2], axis=0))
            m["pindah"] = None
            if not m["pemilik"] and m["datang"]:
                m["pemilik"] = {pid for pid, tt in m["pengendara"].items() if t - tt <= PARKIR_S + PEMILIK_S}
                m["ciri_pemilik"] = [(pid, tt, c) for pid in m["pemilik"] for tt, c in self.ciri.get(pid, ())]
            m["pengendara"] = {}

    def _cek_pindah(self, m, t, persons, events):
        """Motor yang sedang dipindahkan dari tempat parkirnya: dikendarai atau didorong."""
        p = m["pindah"]
        if p is None:
            return
        dt, p["t"] = min(t - p["t"], 1.0), t
        box = m["box"]
        h = max(box[3] - box[1], 8.0)
        dekat = [(jarak_ke_kotak((b[0] + b[2]) / 2, b[3], box) / h, pid, b) for pid, b, _ in persons]
        dekat = [d for d in dekat if d[0] <= DEKAT_FAKTOR]
        if not dekat:
            return
        pengendara = [d for d in dekat if mengendarai(d[2], box)]
        _, pembawa, pbox = min(pengendara or dekat, key=lambda d: d[0])
        if self._pemilik(pembawa, m):
            return
        # pemilik dikenal dari penampilannya, dan pembawa jelas berbeda: motor dibawa orang lain
        d = self._beda_dengan_pemilik(pembawa, m)
        if d is not None and d >= SAMA_ORANG:
            p["asing_s"] += dt
            if p["asing_s"] >= DIBAWA_S:
                m["waspada_t"] = t
                events.setdefault(pembawa, []).append(
                    ("motor_dibawa", f"Motor M{m['id']} dibawa orang yang berbeda dari pemiliknya "
                                     f"(beda penampilan {d:.2f})".replace(".", ",")))
        if pengendara:
            return
        jx, jy, jh = p["jangkar"]
        jauh = math.hypot((box[0] + box[2]) / 2 - jx, (box[1] + box[3]) / 2 - jy) / jh
        p["dorong_s"] += dt
        if p["dorong_s"] >= DORONG_S and jauh >= DORONG_JAUH:
            m["waspada_t"] = t
            events.setdefault(pembawa, []).append(
                ("motor_didorong", f"Motor M{m['id']} didorong {p['dorong_s']:.0f} detik sejauh {jauh:.1f}x tinggi motor"
                 .replace(".", ",")))

    # orang
    def _jongkok(self, st, t, box):
        """Catat tinggi kotak; True bila orang sedang jongkok (tinggi turun dari tinggi berdirinya, posisi diam)."""
        h, kaki = box[3] - box[1], ((box[0] + box[2]) / 2, box[3])
        st["tinggi"].append((t, h, kaki))
        while st["tinggi"] and st["tinggi"][0][0] < t - 30:
            st["tinggi"].popleft()
        data = st["tinggi"]
        if len(data) < 5 or t - data[0][0] < 3:
            return False
        berdiri = float(np.percentile([x[1] for x in data], 80))
        baru = [x for x in data if x[0] >= t - 1.0]
        sekarang = float(np.median([x[1] for x in baru]))
        dua_detik = [x for x in data if x[0] >= t - 2.0]
        geser = math.hypot(dua_detik[-1][2][0] - dua_detik[0][2][0], dua_detik[-1][2][1] - dua_detik[0][2][1])
        return sekarang <= JONGKOK_RASIO * berdiri and geser <= 0.5 * berdiri

    def _sembunyi(self, pid, mid, t):
        """Keadaan orang lain yang lenyap di dekat motor mid dan kemungkinan orang yang sama dengan pid.

        Orang yang muncul langsung di dekat motor (tidak masuk dari tepi gambar) pasti tadi tersembunyi
        di sana, jadi penampilannya tidak perlu cocok (pencuri bisa melepas jaket). Orang yang masuk dari
        tepi gambar hanya mewarisi bila penampilannya tidak jelas berbeda.
        """
        baru = self.orang[pid]
        muncul_di_tempat = not baru.get("masuk_tepi") and t - baru["pertama_t"] <= 1.0
        for opid, s in self.orang.items():
            if opid == pid or opid in self._terlihat or s.get("diwarisi") or s.get("tepi"):
                continue
            if s.get("dekat_id") != mid or s["dekat_mulai"] is None or t - s["terlihat_t"] > SEMBUNYI_S:
                continue
            beda = None if muncul_di_tempat else self._beda_orang(pid, opid)
            if beda is not None and beda >= SAMA_ORANG:  # masuk dari tepi dan penampilannya berbeda: orang lain
                continue
            return s
        return None

    def _beda_orang(self, a, b):
        jarak = [beda_penampilan(x, y) for _, x in self.ciri.get(a, ()) for _, y in self.ciri.get(b, ())]
        jarak = [d for d in jarak if d is not None]
        return min(jarak) if jarak else None

    def _cek_orang(self, t, pid, box, zone, events):
        st = self.orang.setdefault(pid, {"dekat_mulai": None, "dekat_t": None, "calon": None, "terlihat_t": t,
                                         "kunjungan": deque(), "motor": None, "tinggi": deque(),
                                         "jongkok_mulai": None, "jongkok_t": None, "warisan": False,
                                         "pertama_t": t, "masuk_tepi": None, "box": box})
        st["box"] = box
        if self._size:
            w, h = self._size
            st["tepi"] = (box[0] <= TEPI * w or box[2] >= (1 - TEPI) * w or box[1] <= TEPI * h or box[3] >= (1 - TEPI) * h)
            if st["masuk_tepi"] is None:
                st["masuk_tepi"] = st["tepi"]
        muncul_lagi = t - st["terlihat_t"] > 1.0  # sempat tidak terdeteksi, misalnya jongkok di balik motor
        st["terlihat_t"] = t
        jeda = HILANG_S if muncul_lagi else LEPAS_S
        jongkok = self._jongkok(st, t, box)
        if zone is not None and zone.jenis == "santai":  # misalnya pos petugas parkir
            st["dekat_mulai"] = st["calon"] = st["jongkok_mulai"] = None
            return
        fx, fy = (box[0] + box[2]) / 2, box[3]
        dekat = {}
        for m in self.motors.values():
            # motor terparkir tidak bergerak: posisi terakhirnya tetap dipakai walau tertutup orang di depannya
            if not m["terparkir"] or t - m["last_t"] > INGAT_MOTOR_S:
                continue
            r = jarak_ke_kotak(fx, fy, m["box"]) / max(m["box"][3] - m["box"][1], 8.0)
            if r <= DEKAT_FAKTOR and sejajar(box, m["box"]):
                dekat[m["id"]] = r
        # motor yang sedang didekati tetap dipakai selama orang masih di dekatnya, agar di barisan
        # motor yang rapat pilihan tidak berpindah-pindah karena getaran kotak
        if st["motor"] in dekat:
            mid = st["motor"]
        else:
            mid = min(dekat, key=dekat.get) if dekat else None
        if mid is None or self._pemilik(pid, self.motors[mid]):  # menjauh, atau mengurus motornya sendiri
            if mid is not None or (st["dekat_t"] is not None and t - st["dekat_t"] > jeda):
                st["dekat_mulai"] = st["jongkok_mulai"] = None
            st["motor"] = mid
            return
        m = self.motors[mid]
        if st.get("dekat_id") != mid:  # pindah ke motor lain: hitungan dekat mulai lagi
            st["dekat_mulai"] = st["jongkok_mulai"] = None
        st["motor"] = st["dekat_id"] = mid
        if not st["warisan"]:  # pertama kali di dekat motor: mungkin orang yang tadi bersembunyi di sini
            st["warisan"] = True
            lama = self._sembunyi(pid, mid, t)
            if lama is not None:
                lama["diwarisi"] = True
                st["dekat_mulai"], st["dekat_t"] = lama["dekat_mulai"], t
        if st["dekat_mulai"] is None or t - st["dekat_t"] > jeda:
            st["dekat_mulai"] = t
        st["dekat_t"] = t
        pemilik = ("pemilik ID " + ", ".join(str(i) for i in sorted(m["pemilik"]))) if m["pemilik"] \
            else "pemilik tidak diketahui"
        lama = t - st["dekat_mulai"]
        if lama >= self.dekat_s:
            events.setdefault(pid, []).append(
                ("dekat_motor", f"Berada {lama:.0f} detik di dekat motor M{m['id']} ({pemilik})"))
            m["waspada_t"] = t
        # jongkok di dekat motor orang lain
        if jongkok:
            if st["jongkok_mulai"] is None or t - st["jongkok_t"] > jeda:
                st["jongkok_mulai"] = t
            st["jongkok_t"] = t
        elif st["jongkok_t"] is not None and t - st["jongkok_t"] > jeda:
            st["jongkok_mulai"] = None
        if st["jongkok_mulai"] is not None and t - st["jongkok_mulai"] >= JONGKOK_S:
            events.setdefault(pid, []).append(
                ("jongkok_motor", f"Berjongkok {t - st['jongkok_mulai']:.0f} detik di dekat motor M{m['id']} ({pemilik})"))
            m["waspada_t"] = t
        # kunjungan: motor terdekat yang sama selama >= KUNJUNGAN_S detik
        calon = st["calon"]
        if calon is None or calon[0] != m["id"] or t - calon[2] > jeda:
            st["calon"] = calon = [m["id"], t, t]
        calon[2] = t
        if t - calon[1] >= KUNJUNGAN_S and (not st["kunjungan"] or st["kunjungan"][-1][1] != m["id"]):
            st["kunjungan"].append((t, m["id"]))
        while st["kunjungan"] and st["kunjungan"][0][0] < t - PINDAH_JENDELA_S:
            st["kunjungan"].popleft()
        n = len({mid for _, mid in st["kunjungan"]})
        if n >= PINDAH_N:
            events.setdefault(pid, []).append(
                ("pindah_motor", f"Mendekati {n} motor berbeda dalam {PINDAH_JENDELA_S:.0f} detik"))

    def _cek_hilang(self, t, events):
        """Orang yang lenyap di dekat motor orang lain dan belum muncul lagi."""
        for pid, st in self.orang.items():
            if pid in self._terlihat or st.get("diwarisi") or st.get("tepi") or st["dekat_mulai"] is None:
                continue
            hilang = t - st["terlihat_t"]
            m = self.motors.get(st.get("dekat_id"))
            if hilang < HILANG_S or hilang > SEMBUNYI_S or m is None or not m["terparkir"]:
                continue
            lama = t - st["dekat_mulai"]
            if lama >= self.dekat_s:
                events.setdefault(pid, []).append(
                    ("hilang_dekat_motor", f"Hilang dari pandangan {hilang:.0f} detik di dekat motor M{m['id']} "
                                           f"(total {lama:.0f} detik sejak mendekat)"))
                m["waspada_t"] = t

    def kotak_terakhir(self, pid):
        st = self.orang.get(pid)
        return st["box"] if st else None

    def update(self, t, persons, motors, frame=None, size=None):
        """persons: list (id orang, kotak, zona); motors: list (id track, kotak); frame: gambar BGR untuk
        mencatat penampilan orang (boleh None); size: (lebar, tinggi) gambar.

        Kembalikan {id orang: [(kategori, alasan), ...]} untuk aturan yang sedang terpenuhi.
        """
        if self.t0 is None:
            self.t0 = t
        self._size = size or ((frame.shape[1], frame.shape[0]) if frame is not None else None)
        self._catat_ciri(t, frame, persons)
        terlihat = self._terlihat = {pid for pid, _, _ in persons}
        for m in self.motors.values():  # tambah contoh penampilan pemilik selama ia masih terlihat (berjalan pergi)
            if not m["ciri_pemilik"] or len(m["ciri_pemilik"]) >= 2 * CIRI_MAKS:
                continue
            ada = {(pid, tt) for pid, tt, _ in m["ciri_pemilik"]}
            for pid in m["pemilik"] & terlihat:
                for tt, c in self.ciri.get(pid, ()):
                    if (pid, tt) not in ada and len(m["ciri_pemilik"]) < 2 * CIRI_MAKS:
                        m["ciri_pemilik"].append((pid, tt, c))
        events, aktif = {}, set()
        for tid, box in motors:
            mid = self._kenali(t, tid, box, aktif)
            if mid in aktif:
                continue
            aktif.add(mid)
            self._perbarui_motor(self.motors[mid], t, box, persons)
        for mid in aktif:
            self._cek_pindah(self.motors[mid], t, persons, events)
        for pid, box, zone in persons:
            self._cek_orang(t, pid, box, zone, events)
        self._cek_hilang(t, events)
        # lupakan orang yang lama hilang; motor terparkir diingat lebih lama (pemiliknya bisa kembali berjam-jam)
        for mid in [k for k, m in self.motors.items()
                    if t - m["last_t"] > (INGAT_MOTOR_S if not m["terparkir"] else 600)]:
            del self.motors[mid]
        self.alias = {k: v for k, v in self.alias.items() if v in self.motors}
        for pid in [k for k, s in self.orang.items() if k not in terlihat and s["terlihat_t"] < t - 120]:
            del self.orang[pid]
            self.ciri.pop(pid, None)
        for pid in events:  # urutkan menurut prioritas kategori
            events[pid].sort(key=lambda e: KATEGORI.index(e[0]))
        return events

    def snapshot(self, t):
        """Motor yang terlihat pada frame ini, untuk digambar: (id, kotak, terparkir, pemilik, waspada)."""
        return [(m["id"], m["box"], m["terparkir"], sorted(m["pemilik"]), t - m["waspada_t"] <= 3.0)
                for m in self.motors.values() if m["last_t"] == t]
