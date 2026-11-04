"""Uji aturan mode parkiran dan jam aktif zona dengan lintasan buatan (5 fps, frame 640x480).

Motor: kotak 60x40 piksel. Orang: kotak 24x70 piksel. Posisi ditulis sebagai titik bawah-tengah.
Jalankan: python -m unittest discover -s web/tests
"""
import sys
import unittest
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.business.detection.behavior import BehaviorTracker  # noqa: E402
from app.business.detection.zones import Zone, ZoneSet  # noqa: E402

FPS, SIZE = 5, (640, 480)
DT = 1 / FPS


def motor(x, y):
    return (x - 30, y - 40, x + 30, y)


def orang(x, y):
    return (x - 12, y - 70, x + 12, y)


MERAH, BIRU, HIJAU, KUNING = (40, 40, 210), (200, 80, 30), (60, 180, 60), (40, 210, 230)


class Adegan:
    """Jalankan BehaviorTracker mode parkiran frame demi frame dan kumpulkan peristiwa.

    warna: {id track orang: (warna baju, warna celana)}; bila diisi, frame digambar agar penampilan
    orang bisa dikenali.
    """

    def __init__(self, zones=None, menit=None, warna=None):
        self.bt = BehaviorTracker(zones=zones, mode="parkir")
        self.t, self.menit, self.warna = 0.0, menit, warna
        self.peristiwa = []  # (t, id orang, kategori, alasan)

    def gambar(self, persons, motors):
        img = np.full((SIZE[1], SIZE[0], 3), 128, np.uint8)
        for _, (x1, y1, x2, y2) in motors:
            cv2.rectangle(img, (int(x1), int(y1)), (int(x2), int(y2)), (60, 60, 60), -1)
        for tid, (x1, y1, x2, y2) in persons:
            atas, bawah = self.warna.get(tid, ((128, 128, 128), (128, 128, 128)))
            tengah = int(y1 + 0.55 * (y2 - y1))
            cv2.rectangle(img, (int(x1), int(y1)), (int(x2), tengah), atas, -1)
            cv2.rectangle(img, (int(x1), tengah), (int(x2), int(y2)), bawah, -1)
        return img

    def frame(self, persons, motors):
        img = self.gambar(persons, motors) if self.warna else None
        hasil = self.bt.update(self.t, [(tid, *b) for tid, b in persons], SIZE,
                               motors=[(tid, *b) for tid, b in motors], menit=self.menit, frame=img)
        for pid, *_ in hasil:
            for kategori, _, alasan in self.bt.people[pid]["events"]:
                self.peristiwa.append((round(self.t, 1), pid, kategori, alasan))
        for pid, _, kategori, alasan in self.bt.tak_terlihat:
            self.peristiwa.append((round(self.t, 1), pid, kategori, alasan))
        self.t += DT
        return hasil

    def jalankan(self, detik, fungsi):
        """fungsi(t_relatif) -> (persons, motors)."""
        for i in range(int(round(detik * FPS))):
            self.frame(*fungsi(i * DT))

    def pertama(self, kategori):
        return next((p for p in self.peristiwa if p[2] == kategori), None)


BARIS = [motor(100 + 150 * i, 300) for i in range(4)]  # empat motor terparkir, jarak 150 piksel
MOTOR_BARIS = [(10 + i, b) for i, b in enumerate(BARIS)]


class MotorTerparkirTest(unittest.TestCase):
    def test_motor_yang_datang_terparkir_setelah_diam_10_detik(self):
        a = Adegan()
        a.jalankan(4, lambda t: ([], [(10, motor(100 + 50 * t, 300))]))  # datang dari kiri
        a.jalankan(9, lambda t: ([], [(10, motor(300, 300))]))
        self.assertFalse(a.bt.parkir.motors[1]["terparkir"])
        a.jalankan(2, lambda t: ([], [(10, motor(300, 300))]))
        self.assertTrue(a.bt.parkir.motors[1]["terparkir"])

    def test_motor_sejak_awal_rekaman_terparkir_setelah_3_detik(self):
        a = Adegan()
        a.jalankan(2.4, lambda t: ([], [(10, motor(300, 300))]))
        self.assertFalse(a.bt.parkir.motors[1]["terparkir"])
        a.jalankan(1.0, lambda t: ([], [(10, motor(300, 300))]))
        self.assertTrue(a.bt.parkir.motors[1]["terparkir"])


class DekatMotorTest(unittest.TestCase):
    def test_orang_asing_15_detik_di_dekat_motor(self):
        a = Adegan()
        a.jalankan(12, lambda t: ([], MOTOR_BARIS))  # motor terparkir, pemilik tidak diketahui
        a.jalankan(20, lambda t: ([(1, orang(140, 305))], MOTOR_BARIS))  # berdiri di samping motor pertama
        hit = a.pertama("dekat_motor")
        self.assertIsNotNone(hit)
        self.assertGreaterEqual(hit[0] - 12, 14.8)
        self.assertIn("pemilik tidak diketahui", hit[3])

    def test_orang_asing_naik_motor_yang_sudah_terparkir(self):
        # regresi video 1000620467: motor diam sejak awal; pencuri datang berjalan kaki, duduk di atas
        # motor beberapa detik sebelum motor terdeteksi terparkir, lalu mengutak-atik 20 detik.
        # Dulu pencuri tercatat sebagai pemilik sehingga tidak pernah dicurigai.
        a = Adegan()
        a.jalankan(7, lambda t: ([(3, orang(300 + 30 * (7 - t), 300))] if t > 4 else [], [(10, motor(300, 300))]))
        a.jalankan(25, lambda t: ([(3, orang(300, 300))], [(10, motor(300, 300))]))
        self.assertEqual(a.bt.parkir.motors[1]["pemilik"], set())
        self.assertIsNotNone(a.pertama("dekat_motor"))

    def test_dekat_sebentar_tidak_dicurigai(self):
        a = Adegan()
        a.jalankan(12, lambda t: ([], MOTOR_BARIS))
        a.jalankan(10, lambda t: ([(1, orang(140, 305))], MOTOR_BARIS))  # 10 detik, misalnya mengambil helm
        a.jalankan(10, lambda t: ([(1, orang(140, 450))], MOTOR_BARIS))  # menjauh
        self.assertEqual(a.peristiwa, [])

    def test_motor_tertutup_orang_tetap_dihitung(self):
        # motor tidak terdeteksi karena tertutup orang yang berjongkok di depannya
        a = Adegan()
        a.jalankan(12, lambda t: ([], [(10, motor(300, 300))]))
        a.jalankan(20, lambda t: ([(1, orang(300, 310))], []))
        self.assertIsNotNone(a.pertama("dekat_motor"))

    def test_pemilik_mengurus_motornya_tidak_dicurigai(self):
        a = Adegan()
        # datang berkendara dari kiri selama 5 detik, berhenti, turun pada detik 7
        def datang(t):
            x = 100 + 40 * min(t, 5)
            persons = [(1, orang(x, 300) if t < 7 else orang(x + 40, 305))]
            return persons, [(10, motor(x, 300))]
        a.jalankan(10, datang)
        # pemilik berdiri di samping motornya (memakai jas hujan, mencari kunci) selama 40 detik
        a.jalankan(40, lambda t: ([(1, orang(340, 305))], [(10, motor(300, 300))]))
        self.assertEqual(a.bt.parkir.motors[1]["pemilik"], {1})
        self.assertEqual(a.peristiwa, [])

    def test_pejalan_melewati_barisan_motor_rapat(self):
        rapat = [(10 + i, motor(100 + 80 * i, 300)) for i in range(5)]
        for kecepatan in (30, 60):  # piksel per detik: berjalan pelan dan normal
            with self.subTest(kecepatan=kecepatan):
                a = Adegan()
                a.jalankan(12, lambda t: ([], rapat))
                a.jalankan(500 / kecepatan, lambda t: ([(1, orang(20 + kecepatan * t, 312))], rapat))
                self.assertEqual(a.peristiwa, [])


    def test_pembonceng_ikut_dianggap_pemilik(self):
        a = Adegan()
        def datang(t):  # pengendara dan pembonceng (kotak lebih tinggi, menumpang bagian atas motor)
            x = 100 + 40 * min(t, 5)
            if t < 7:
                return [(1, orang(x, 300)), (2, (x - 30, 220, x - 6, 285))], [(10, motor(x, 300))]
            return [(1, orang(x + 40, 305)), (2, orang(x - 45, 305))], [(10, motor(x, 300))]
        a.jalankan(10, datang)
        a.jalankan(30, lambda t: ([(1, orang(340, 305)), (2, orang(255, 305))], [(10, motor(300, 300))]))
        self.assertEqual(a.bt.parkir.motors[1]["pemilik"], {1, 2})
        self.assertEqual(a.peristiwa, [])


class PindahMotorTest(unittest.TestCase):
    def test_mendekati_tiga_motor_berbeda(self):
        a = Adegan()
        a.jalankan(12, lambda t: ([], MOTOR_BARIS))

        def keliling(t):
            i = min(int(t // 8), 3)        # tiap 8 detik: 5 detik di motor i, 3 detik berjalan
            x = 140 + 150 * i if t % 8 < 5 else 140 + 150 * i + 50 * (t % 8 - 5)
            return [(1, orang(x, 305))], MOTOR_BARIS
        a.jalankan(24, keliling)
        hit = a.pertama("pindah_motor")
        self.assertIsNotNone(hit)
        self.assertIsNone(a.pertama("dekat_motor"))  # tidak ada motor yang didekati 15 detik


class MotorDidorongTest(unittest.TestCase):
    def test_motor_terparkir_didorong_menjauh(self):
        a = Adegan()
        a.jalankan(12, lambda t: ([], [(10, motor(200, 300))]))
        a.jalankan(5, lambda t: ([(1, orang(245, 305))], [(10, motor(200, 300))]))

        def dorong(t):  # berjalan di samping motor sambil mendorongnya 30 piksel per detik
            x = 200 + 30 * t
            return [(1, orang(x + 45, 305))], [(10, motor(x, 300))]
        a.jalankan(10, dorong)
        hit = a.pertama("motor_didorong")
        self.assertIsNotNone(hit)
        self.assertEqual(hit[1], 1)

    def test_motor_dikendarai_bukan_didorong(self):
        a = Adegan()
        a.jalankan(12, lambda t: ([], [(10, motor(200, 300))]))
        a.jalankan(5, lambda t: ([(1, orang(200, 300))], [(10, motor(200, 300))]))  # naik ke motor

        def pergi(t):
            x = 200 + 60 * t
            return [(1, orang(x, 300))], [(10, motor(x, 300))]
        a.jalankan(6, pergi)
        self.assertEqual(a.peristiwa, [])


def datang_parkir(a, tid):
    """Pemilik datang berkendara dari kiri, parkir di x=300, turun, lalu berjalan keluar gambar."""
    def datang(t):
        x = 100 + 40 * min(t, 5)
        return [(tid, orang(x, 300) if t < 7 else orang(x + 40, 305))], [(10, motor(x, 300))]
    a.jalankan(12, datang)
    a.jalankan(6, lambda t: ([(tid, orang(340 + 50 * t, 305))], [(10, motor(300, 300))]))


class PenampilanPemilikTest(unittest.TestCase):
    def test_pemilik_kembali_dengan_id_baru_tidak_dicurigai(self):
        a = Adegan(warna={1: (MERAH, BIRU), 5: (MERAH, BIRU)})
        datang_parkir(a, 1)
        a.jalankan(60, lambda t: ([], [(10, motor(300, 300))]))  # pergi satu menit
        a.jalankan(25, lambda t: ([(5, orang(340, 305))], [(10, motor(300, 300))]))  # kembali, bersiap lama
        self.assertEqual(a.peristiwa, [])
        self.assertIn(a.bt.alias[5], a.bt.parkir.motors[1]["pemilik"])

    def test_motor_dibawa_orang_lain(self):
        a = Adegan(warna={1: (MERAH, BIRU), 7: (HIJAU, KUNING)})
        datang_parkir(a, 1)
        a.jalankan(30, lambda t: ([], [(10, motor(300, 300))]))
        a.jalankan(5, lambda t: ([(7, orang(300, 300))], [(10, motor(300, 300))]))  # pencuri naik

        def kabur(t):
            x = 300 + 60 * t
            return [(7, orang(x, 300))], [(10, motor(x, 300))]
        a.jalankan(4, kabur)
        hit = a.pertama("motor_dibawa")
        self.assertIsNotNone(hit)
        self.assertEqual(hit[1], a.bt.alias[7])
        self.assertIsNone(a.pertama("dekat_motor"))  # hanya 5 detik di dekat motor: aturan lama tidak menangkapnya

    def test_pemilik_pergi_dengan_motornya_tidak_dicurigai(self):
        a = Adegan(warna={1: (MERAH, BIRU), 8: (MERAH, BIRU)})
        datang_parkir(a, 1)
        a.jalankan(30, lambda t: ([], [(10, motor(300, 300))]))
        a.jalankan(5, lambda t: ([(8, orang(300, 300))], [(10, motor(300, 300))]))

        def pergi(t):
            x = 300 + 60 * t
            return [(8, orang(x, 300))], [(10, motor(x, 300))]
        a.jalankan(4, pergi)
        self.assertEqual(a.peristiwa, [])


class JongkokTest(unittest.TestCase):
    def test_jongkok_di_dekat_motor(self):
        a = Adegan()
        a.jalankan(5, lambda t: ([(3, orang(500 - 30 * t, 305))], [(10, motor(300, 300))]))  # berjalan mendekat
        a.jalankan(8, lambda t: ([(3, (340 - 14, 305 - 40, 340 + 14, 305))], [(10, motor(300, 300))]))  # jongkok
        hit = a.pertama("jongkok_motor")
        self.assertIsNotNone(hit)
        self.assertLess(hit[0], 12)  # jauh sebelum ambang dekat motor 15 detik
        self.assertIsNone(a.pertama("dekat_motor"))

    def test_hilang_sebentar_di_balik_motor_tidak_mengulang_hitungan(self):
        a = Adegan()
        a.jalankan(4, lambda t: ([], [(10, motor(300, 300))]))
        a.jalankan(8, lambda t: ([(3, orang(340, 305))], [(10, motor(300, 300))]))
        a.jalankan(3, lambda t: ([], [(10, motor(300, 300))]))      # tidak terdeteksi 3 detik
        a.jalankan(8, lambda t: ([(9, orang(340, 305))], [(10, motor(300, 300))]))  # ID tracker baru
        hit = a.pertama("dekat_motor")
        self.assertIsNotNone(hit)
        self.assertLess(hit[0], 4 + 16)


class BersembunyiTest(unittest.TestCase):
    """Regresi video cctv-percobaan-pencurian-motor: pencuri lenyap di balik motor beratap selama
    20 detik, lalu muncul lagi di motor yang sama dengan ID baru."""

    def test_waktu_bersembunyi_ikut_dihitung(self):
        a = Adegan(warna={3: (HIJAU, KUNING), 9: (HIJAU, KUNING)})
        a.jalankan(4, lambda t: ([], [(10, motor(300, 300))]))
        a.jalankan(3, lambda t: ([(3, orang(340, 305))], [(10, motor(300, 300))]))
        a.jalankan(20, lambda t: ([], [(10, motor(300, 300))]))   # lenyap di balik motor
        a.jalankan(3, lambda t: ([(9, orang(340, 305))], [(10, motor(300, 300))]))
        hit = a.pertama("dekat_motor")
        self.assertIsNotNone(hit)
        self.assertLess(hit[0], 4 + 3 + 20 + 1)  # langsung saat muncul lagi

    def test_orang_lain_yang_datang_tidak_mewarisi(self):
        a = Adegan(warna={3: (HIJAU, KUNING), 9: (MERAH, BIRU)})
        a.jalankan(4, lambda t: ([], [(10, motor(300, 300))]))
        a.jalankan(3, lambda t: ([(3, orang(340, 305))], [(10, motor(300, 300))]))
        a.jalankan(20, lambda t: ([], [(10, motor(300, 300))]))
        # orang lain berpenampilan berbeda masuk dari tepi kanan menuju motor
        a.jalankan(3, lambda t: ([(9, orang(630 - 96 * t, 305))], [(10, motor(300, 300))]))
        a.jalankan(8, lambda t: ([(9, orang(340, 305))], [(10, motor(300, 300))]))
        baru = a.bt.alias[9]
        self.assertEqual([p for p in a.peristiwa if p[1] == baru], [])

    def test_hilang_di_balik_motor_dan_tidak_muncul_lagi(self):
        # regresi video cctv-percobaan-pencurian-motor: pencuri tidak terlihat lagi setelah ke balik motor
        a = Adegan()
        a.jalankan(4, lambda t: ([], [(10, motor(300, 300))]))
        a.jalankan(3, lambda t: ([(3, orang(340, 305))], [(10, motor(300, 300))]))
        a.jalankan(20, lambda t: ([], [(10, motor(300, 300))]))
        hit = a.pertama("hilang_dekat_motor")
        self.assertIsNotNone(hit)
        self.assertLess(hit[0], 4 + 15 + 1)

    def test_muncul_langsung_di_motor_walau_berganti_baju(self):
        a = Adegan(warna={3: (HIJAU, KUNING), 9: (MERAH, BIRU)})
        a.jalankan(4, lambda t: ([], [(10, motor(300, 300))]))
        a.jalankan(3, lambda t: ([(3, orang(340, 305))], [(10, motor(300, 300))]))
        a.jalankan(20, lambda t: ([], [(10, motor(300, 300))]))
        a.jalankan(2, lambda t: ([(9, orang(340, 305))], [(10, motor(300, 300))]))  # muncul dari balik motor
        self.assertIsNotNone(a.pertama("dekat_motor"))

    def test_orang_yang_keluar_lewat_tepi_tidak_diwarisi(self):
        a = Adegan()
        a.jalankan(4, lambda t: ([], [(10, motor(300, 300))]))
        a.jalankan(3, lambda t: ([(3, orang(340, 305))], [(10, motor(300, 300))]))
        a.jalankan(2, lambda t: ([(3, orang(340 + 150 * t, 305))], [(10, motor(300, 300))]))  # keluar ke kanan
        a.jalankan(20, lambda t: ([], [(10, motor(300, 300))]))
        a.jalankan(3, lambda t: ([(9, orang(630 - 96 * t, 305))], [(10, motor(300, 300))]))  # orang lain masuk
        a.jalankan(8, lambda t: ([(9, orang(340, 305))], [(10, motor(300, 300))]))
        self.assertEqual(a.peristiwa, [])


class ZonaParkiranTest(unittest.TestCase):
    def test_petugas_di_zona_santai_tidak_dicurigai(self):
        pos = ZoneSet([Zone(1, "Pos petugas", "santai", [(0.1, 0.5), (0.4, 0.5), (0.4, 0.8), (0.1, 0.8)])])
        a = Adegan(zones=pos)
        a.jalankan(12, lambda t: ([], MOTOR_BARIS))
        a.jalankan(40, lambda t: ([(1, orang(140, 305))], MOTOR_BARIS))
        self.assertEqual(a.peristiwa, [])

    def test_mode_parkiran_tanpa_zona_diam_tidak_dicurigai(self):
        a = Adegan()
        a.jalankan(40, lambda t: ([(1, orang(500, 450))], []))  # menunggu jauh dari motor
        self.assertEqual(a.peristiwa, [])


class JamAktifZonaTest(unittest.TestCase):
    PINTU = [(0.4, 0.4), (0.6, 0.4), (0.6, 0.8), (0.4, 0.8)]

    def test_jam_melewati_tengah_malam(self):
        z = Zone(1, "Rolling door", "terlarang", self.PINTU, "22:00", "06:00")
        self.assertTrue(z.aktif(23 * 60))
        self.assertTrue(z.aktif(2 * 60))
        self.assertFalse(z.aktif(12 * 60))
        self.assertFalse(z.aktif(6 * 60))
        self.assertTrue(Zone(2, "x", "terlarang", self.PINTU).aktif(12 * 60))  # tanpa jadwal: selalu aktif

    def test_zona_terlarang_hanya_saat_toko_tutup(self):
        zones = ZoneSet([Zone(1, "Rolling door", "terlarang", self.PINTU, "22:00", "06:00")])
        for menit, harap in ((12 * 60, False), (23 * 60, True)):
            with self.subTest(menit=menit):
                bt = BehaviorTracker(zones=zones)
                hit = False
                for i in range(5 * FPS):
                    r = bt.update(i * DT, [(1, *orang(320, 300))], SIZE, menit=menit)[0]
                    hit = hit or r[6] == "terlarang"
                self.assertEqual(hit, harap)


if __name__ == "__main__":
    unittest.main()


class TestModeOtomatis(unittest.TestCase):
    def test_putuskan_mode(self):
        from app.business.detection.engine import putuskan_mode
        self.assertEqual(putuskan_mode(3)[0], "parkir")
        self.assertEqual(putuskan_mode(2)[0], "parkir")
        self.assertEqual(putuskan_mode(1)[0], "umum", "satu motor di depan toko bukan parkiran")
        self.assertEqual(putuskan_mode(0)[0], "umum")
        self.assertEqual(putuskan_mode(0, "parkir")[0], "parkir", "parkiran kosong di malam hari tetap parkiran")
        self.assertEqual(putuskan_mode(1, "umum")[0], "umum")
        self.assertIn("motor terparkir", putuskan_mode(3)[1])
