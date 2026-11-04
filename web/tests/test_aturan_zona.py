"""Uji aturan perilaku per zona dengan lintasan buatan (25 fps, frame 400x300).

Jalankan: python -m unittest discover -s web/tests
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.business.detection.behavior import BehaviorTracker  # noqa: E402
from app.business.detection.zones import Zone, ZoneSet, point_in_polygon  # noqa: E402

FPS, SIZE = 25, (400, 300)
# zona di kiri (x 0-0.5) dan kanan (x 0.5-1), seluruh tinggi gambar
KIRI = [(0, 0), (0.5, 0), (0.5, 1), (0, 1)]
KANAN = [(0.5, 0), (1, 0), (1, 1), (0.5, 1)]


def diam(x, y, detik):
    """Orang diam: kotak 20x60 dengan kaki di (x, y) piksel."""
    return [(i / FPS, (x - 10, y - 60, x + 10, y)) for i in range(int(detik * FPS))]


def mondar_mandir(y, detik, x0=220, x1=380):
    """Orang bolak-balik horizontal setiap 4 detik antara x0 dan x1."""
    out = []
    for i in range(int(detik * FPS)):
        t = i / FPS
        phase = (t % 8) / 4
        x = x0 + (x1 - x0) * (phase if phase <= 1 else 2 - phase)
        out.append((t, (x - 10, y - 60, x + 10, y)))
    return out


def berjalan_bergetar(detik, fps, getar=4, seed=0):
    """Orang berjalan lurus pelan (6 px/detik) dengan kotak yang bergetar acak beberapa piksel."""
    import random
    rnd = random.Random(seed)
    out = []
    for i in range(int(detik * fps)):
        t = i / fps
        x = 40 + 6 * t + rnd.uniform(-getar, getar)
        y = 250 + rnd.uniform(-getar, getar)
        out.append((t, (x - 10, y - 60, x + 10, y)))
    return out


def run(track, zones=None):
    bt = BehaviorTracker(zones=zones)
    hasil = []
    for t, box in track:
        r = bt.update(t, [(1, *box)], SIZE)[0]
        hasil.append((t, r[2], r[3], r[6], r[7]))  # waktu, label, alasan, kategori, zona
    return hasil


def pertama_suspicious(hasil):
    return next(((t, kat, zona) for t, label, _, kat, zona in hasil if label), None)


class AturanZonaTest(unittest.TestCase):
    def test_point_in_polygon(self):
        self.assertTrue(point_in_polygon(0.25, 0.5, KIRI))
        self.assertFalse(point_in_polygon(0.75, 0.5, KIRI))

    def test_tanpa_zona_aturan_umum(self):
        hit = pertama_suspicious(run(diam(100, 200, 25)))
        self.assertIsNotNone(hit)
        self.assertAlmostEqual(hit[0], 20.0, delta=0.1)
        self.assertEqual(hit[1], "diam")

    def test_zona_santai_diam_lama_tetap_safe(self):
        zones = ZoneSet([Zone(1, "Teras", "santai", KIRI)])
        self.assertIsNone(pertama_suspicious(run(diam(100, 200, 60), zones)))

    def test_zona_santai_mondar_mandir_tetap_safe(self):
        zones = ZoneSet([Zone(1, "Ruang tamu", "santai", KANAN)])
        self.assertIsNone(pertama_suspicious(run(mondar_mandir(200, 60), zones)))

    def test_zona_sensitif_diam_20_detik(self):
        zones = ZoneSet([Zone(2, "Depan kamar 3", "sensitif", KIRI)])
        hasil = run(diam(100, 200, 25), zones)
        hit = pertama_suspicious(hasil)
        self.assertAlmostEqual(hit[0], 20.0, delta=0.1)
        self.assertEqual(hit[1:], ("sensitif", "Depan kamar 3"))
        self.assertFalse(any(label for t, label, *_ in hasil if t < 19.9))

    def test_zona_terlarang_langsung(self):
        zones = ZoneSet([Zone(3, "Gudang", "terlarang", KIRI)])
        hit = pertama_suspicious(run(diam(100, 200, 5), zones))
        self.assertAlmostEqual(hit[0], 1.0, delta=0.1)
        self.assertEqual(hit[1], "terlarang")

    def test_area_umum_diam_safe_mondar_mandir_suspicious(self):
        zones = ZoneSet([Zone(1, "Teras", "santai", [(0, 0), (0.2, 0), (0.2, 0.2), (0, 0.2)])])
        self.assertIsNone(pertama_suspicious(run(diam(300, 250, 60), zones)))
        hit = pertama_suspicious(run(mondar_mandir(250, 40), zones))
        self.assertIsNotNone(hit)
        self.assertEqual(hit[1], "mondar-mandir")

    def test_prioritas_zona_tumpang_tindih(self):
        zones = ZoneSet([Zone(1, "Seluruh", "santai", [(0, 0), (1, 0), (1, 1), (0, 1)]),
                         Zone(2, "Pintu", "terlarang", KIRI)])
        hit = pertama_suspicious(run(diam(100, 200, 3), zones))
        self.assertEqual(hit[1], "terlarang")

    def test_titik_kaki_menentukan_zona(self):
        # badan di zona atas (y < 0.5), kaki di zona bawah (y > 0.5): yang dipakai titik kaki
        atas = [(0, 0), (1, 0), (1, 0.5), (0, 0.5)]
        bawah = [(0, 0.5), (1, 0.5), (1, 1), (0, 1)]
        zones = ZoneSet([Zone(1, "Atas", "terlarang", atas), Zone(2, "Bawah", "santai", bawah)])
        track = [(i / FPS, (190, 120, 210, 180)) for i in range(5 * FPS)]  # kaki di y=180 (0.6)
        self.assertIsNone(pertama_suspicious(run(track, zones)))


def mendekat(detik, fps=25, h0=34, h1=58, y0=80):
    """Orang berjalan mendekati kamera koridor: kotak membesar dan kaki turun pelan di gambar
    (sekitar 0,1xH per detik, sesuai pejalan ID3 pada contoh 1)."""
    out = []
    for i in range(int(detik * fps)):
        t = i / fps
        h = h0 + (h1 - h0) * t / detik
        y2 = y0 + 6 * (h - h0)  # kaki turun sedikit demi sedikit
        out.append((t, (100 - h / 6, y2 - h, 100 + h / 6, y2)))
    return out


class AturanDiamTest(unittest.TestCase):
    """Regresi: orang berjalan searah garis pandang kamera dulu terbaca 'diam'."""

    def test_berjalan_mendekat_kamera_tidak_diam(self):
        self.assertIsNone(pertama_suspicious(run(mendekat(30))))

    def test_diam_dengan_kotak_berubah_ukuran_tetap_diam(self):
        # orang berhenti lalu membungkuk: tinggi kotak turun 40% tetapi posisinya tidak bergeser
        track = [(t, (100 - 10, 200 - h, 100 + 10, 200)) for t, h in
                 ((i / 5, 60 if i < 60 else 36) for i in range(25 * 5))]
        hit = pertama_suspicious(run(track))
        self.assertIsNotNone(hit)
        self.assertEqual(hit[1], "diam")

    def test_diam_dengan_kotak_terpotong_tepi_tetap_diam(self):
        # kaki di tepi bawah gambar (y2 = 300): tinggi kotak tidak dipakai, orang tetap dinilai diam
        hit = pertama_suspicious(run(diam(100, 300, 25)))
        self.assertIsNotNone(hit)
        self.assertEqual(hit[1], "diam")


class GetaranDanFpsTest(unittest.TestCase):
    """Regresi bug: getaran kotak per frame dulu terhitung sebagai jarak tempuh sehingga pejalan
    normal tertandai mondar-mandir, terutama saat berkas diproses 25 fps."""

    ZONA_LAIN = ZoneSet([Zone(1, "Teras", "santai", [(0.9, 0), (1, 0), (1, 0.1), (0.9, 0.1)])])

    def test_pejalan_bergetar_tidak_mondar_mandir(self):
        for fps in (25, 10, 5):
            track = berjalan_bergetar(40, fps)
            with self.subTest(fps=fps):
                self.assertIsNone(pertama_suspicious(run(track, self.ZONA_LAIN)))

    def test_mondar_mandir_tetap_terdeteksi_pada_fps_rendah(self):
        for step in (1, 5):  # 25 fps dan 5 fps
            track = mondar_mandir(250, 40)[::step]
            with self.subTest(fps=25 // step):
                hit = pertama_suspicious(run(track, self.ZONA_LAIN))
                self.assertIsNotNone(hit)
                self.assertEqual(hit[1], "mondar-mandir")


if __name__ == "__main__":
    unittest.main()


class TestSambungTrack(unittest.TestCase):
    def test_track_asli_kembali_tidak_terbuang(self):
        """Track orang putus sebentar, deteksi lain muncul di dekatnya dan disambungkan ke orang itu.
        Saat track asli kembali, keduanya harus tetap terlacak dan track asli memakai ID-nya sendiri."""
        bt = BehaviorTracker(gap_s=5.0)
        orang = (180, 100, 220, 220)
        lain = (90, 100, 130, 220)     # jarak pusat 90 px, tinggi 120 px: masih dalam batas sambung
        pid_asli = bt.update(0.0, [(1, *orang)], SIZE)[0][0]
        pid_lain = bt.update(0.5, [(5, *lain)], SIZE)[0][0]
        self.assertEqual(pid_lain, pid_asli, 'skenario uji: track 5 memang tersambung ke orang track 1')
        hasil = bt.update(1.0, [(5, *lain), (1, *orang)], SIZE)
        per_track = {r[5]: r[0] for r in hasil}
        self.assertEqual(set(per_track), {1, 5}, 'kedua kotak harus dilaporkan')
        self.assertEqual(per_track[1], pid_asli, 'track asli memakai ID-nya sendiri')
        self.assertNotEqual(per_track[5], pid_asli)
        # frame berikutnya tetap stabil
        hasil = bt.update(1.5, [(1, *orang), (5, *lain)], SIZE)
        self.assertEqual({r[5]: r[0] for r in hasil}, per_track)

    def test_kotak_ganda_satu_orang_tetap_satu(self):
        bt = BehaviorTracker(gap_s=5.0)
        a = (180, 100, 220, 220)
        bt.update(0.0, [(1, *a)], SIZE)
        bt.update(0.5, [(7, 182, 101, 222, 221)], SIZE)        # track baru menumpang orang yang sama
        hasil = bt.update(1.0, [(1, *a), (7, 182, 101, 222, 221)], SIZE)
        self.assertEqual(len(hasil), 1, 'kotak bertumpuk pada satu orang dilaporkan sekali')

    def test_keluar_tepi_tidak_disambung(self):
        """Orang keluar lewat tepi bawah; 3 detik kemudian orang lain masuk di titik yang sama.
        Orang baru tidak boleh mewarisi ID dan lintasan orang yang sudah keluar (mode parkiran, jeda 5 detik)."""
        bt = BehaviorTracker(gap_s=2.0, mode='parkir')
        pid_lama = bt.update(0.0, [(1, 300, 180, 340, 300)], SIZE)[0][0]   # kaki di tepi bawah (300)
        pid_baru = bt.update(3.0, [(9, 290, 170, 330, 290)], SIZE)[0][0]
        self.assertNotEqual(pid_baru, pid_lama)

    def test_putus_sebentar_tetap_disambung(self):
        bt = BehaviorTracker(gap_s=2.0)
        pid_lama = bt.update(0.0, [(1, 180, 100, 220, 220)], SIZE)[0][0]   # di tengah gambar
        pid_baru = bt.update(1.5, [(9, 185, 100, 225, 220)], SIZE)[0][0]
        self.assertEqual(pid_baru, pid_lama)
