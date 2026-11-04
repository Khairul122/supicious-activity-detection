"""Business tier: zona pengawasan (poligon ternormalisasi 0-1) dan penentuan zona tiap orang.

Posisi orang memakai titik kaki (tengah sisi bawah kotak), karena titik inilah yang
menunjukkan di mana orang berdiri pada lantai.

Setiap zona boleh punya jam aktif (misalnya 22:00 sampai 06:00 untuk toko tutup). Di luar jam
aktif zona diabaikan. Jam aktif yang melewati tengah malam didukung.
"""
import cv2
import numpy as np

JENIS = ("santai", "sensitif", "terlarang")
PRIORITAS = {"terlarang": 0, "sensitif": 1, "santai": 2}  # bila zona tumpang tindih
WARNA = {"santai": (90, 170, 40), "sensitif": (0, 165, 255), "terlarang": (160, 40, 200)}  # BGR (magenta, beda dari kotak suspicious)


def ke_menit(teks):
    """'HH:MM' -> menit sejak tengah malam; None bila kosong."""
    if teks in (None, ""):
        return None
    jam, menit = str(teks).split(":")[:2]
    nilai = int(jam) * 60 + int(menit)
    if not 0 <= nilai < 24 * 60:
        raise ValueError("Jam di luar rentang 00:00 sampai 23:59.")
    return nilai


def menit_sekarang():
    from datetime import datetime
    now = datetime.now()
    return now.hour * 60 + now.minute


def point_in_polygon(x, y, pts):
    """Uji titik dalam poligon (ray casting)."""
    inside = False
    j = len(pts) - 1
    for i in range(len(pts)):
        xi, yi = pts[i]
        xj, yj = pts[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-12) + xi:
            inside = not inside
        j = i
    return inside


class Zone:
    def __init__(self, zid, nama, jenis, titik, jam_mulai=None, jam_selesai=None):
        self.id, self.nama, self.jenis = zid, nama, jenis
        self.titik = [(float(x), float(y)) for x, y in titik]
        self.mulai, self.selesai = ke_menit(jam_mulai), ke_menit(jam_selesai)

    def contains(self, xn, yn):
        return point_in_polygon(xn, yn, self.titik)

    @property
    def terjadwal(self):
        return self.mulai is not None and self.selesai is not None

    def aktif(self, menit=None):
        """True bila zona berlaku pada menit tersebut (menit sejak tengah malam)."""
        if not self.terjadwal or menit is None:
            return True
        if self.mulai < self.selesai:
            return self.mulai <= menit < self.selesai
        return menit >= self.mulai or menit < self.selesai  # melewati tengah malam


class ZoneSet:
    def __init__(self, zones=()):
        self.zones = sorted(zones, key=lambda z: PRIORITAS.get(z.jenis, 9))

    @classmethod
    def from_rows(cls, rows):
        return cls([Zone(r["id"], r["nama"], r["jenis"], r["titik"], r.get("jam_mulai"), r.get("jam_selesai"))
                    for r in rows])

    def __bool__(self):
        return bool(self.zones)

    def find(self, xn, yn, menit=None):
        """Zona aktif berprioritas tertinggi yang memuat titik (xn, yn)."""
        for zone in self.zones:
            if zone.aktif(menit) and zone.contains(xn, yn):
                return zone
        return None

    def draw(self, frame, menit=None):
        if not self.zones:
            return frame
        h, w = frame.shape[:2]
        overlay = frame.copy()
        for zone in self.zones:
            if zone.aktif(menit):  # zona di luar jam aktif hanya digambar garisnya
                pts = np.array([[int(x * w), int(y * h)] for x, y in zone.titik], dtype=np.int32)
                cv2.fillPoly(overlay, [pts], WARNA.get(zone.jenis, (200, 200, 200)))
        cv2.addWeighted(overlay, 0.22, frame, 0.78, 0, frame)
        for zone in self.zones:
            pts = np.array([[int(x * w), int(y * h)] for x, y in zone.titik], dtype=np.int32)
            aktif = zone.aktif(menit)
            color = WARNA.get(zone.jenis, (200, 200, 200)) if aktif else (150, 150, 150)
            cv2.polylines(frame, [pts], True, color, 1, cv2.LINE_AA)
            x, y = pts.min(axis=0)
            teks = f"{zone.nama} ({zone.jenis}{'' if aktif else ', nonaktif'})"
            cv2.putText(frame, teks, (int(x) + 3, int(y) + 13), cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1, cv2.LINE_AA)
        return frame
