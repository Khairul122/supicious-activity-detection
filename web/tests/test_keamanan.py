"""Uji keamanan tanpa database: akun, kunci akun, kebijakan sandi, pembatas permintaan, dan pengalihan aman.

Jalankan: python -m unittest discover -s web/tests
"""
import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.business.services.auth_service import MAKS_GAGAL, AkunTidakValid, AuthService  # noqa: E402
from app.presentation.security import RateLimiter, alamat_aman  # noqa: E402


class RepoPalsu:
    """Pengganti PenggunaRepository di memori."""

    def __init__(self):
        self.baris = {}

    def count(self):
        return len(self.baris)

    def by_username(self, nama):
        return next((dict(b) for b in self.baris.values() if b["nama_pengguna"] == nama), None)

    def by_id(self, pid):
        b = self.baris.get(int(pid))
        return dict(b) if b else None

    def create(self, nama_pengguna, nama, hash_sandi, waktu):
        pid = len(self.baris) + 1
        self.baris[pid] = {"id": pid, "nama_pengguna": nama_pengguna, "nama": nama, "hash_sandi": hash_sandi,
                           "dibuat": waktu, "masuk_terakhir": None, "gagal": 0, "terkunci_sampai": None, "versi_sesi": 1}
        return pid

    def catat_gagal(self, pid, gagal, terkunci_sampai):
        self.baris[pid].update(gagal=gagal, terkunci_sampai=terkunci_sampai)

    def catat_masuk(self, pid, waktu):
        self.baris[pid].update(gagal=0, terkunci_sampai=None, masuk_terakhir=waktu)

    def set_sandi(self, pid, hash_sandi):
        b = self.baris[pid]
        b.update(hash_sandi=hash_sandi, versi_sesi=b["versi_sesi"] + 1, gagal=0, terkunci_sampai=None)


class TestAkun(unittest.TestCase):
    def setUp(self):
        self.repo = RepoPalsu()
        self.auth = AuthService(self.repo)
        self.auth.buat_admin_pertama("admin", "Admin Toko", "Rahasia2026", "Rahasia2026")

    def test_sandi_tidak_disimpan_asli(self):
        h = self.repo.by_username("admin")["hash_sandi"]
        self.assertNotIn("Rahasia2026", h)
        self.assertTrue(h.startswith("pbkdf2:sha256:600000$"))

    def test_admin_pertama_hanya_sekali(self):
        with self.assertRaises(AkunTidakValid):
            self.auth.buat_admin_pertama("kedua", "Orang Lain", "Rahasia2026", "Rahasia2026")

    def test_masuk_benar_dan_salah(self):
        self.assertEqual(self.auth.masuk("ADMIN ", "Rahasia2026")["nama_pengguna"], "admin")
        with self.assertRaises(AkunTidakValid) as e1:
            self.auth.masuk("admin", "salah")
        with self.assertRaises(AkunTidakValid) as e2:
            self.auth.masuk("tidakada", "salah")
        self.assertEqual(str(e1.exception), str(e2.exception), "pesan sama agar nama akun tidak bisa ditebak")

    def test_sql_injection_tidak_lolos(self):
        for nama in ("admin' OR '1'='1", "admin'--", "' UNION SELECT 1 --"):
            with self.assertRaises(AkunTidakValid):
                self.auth.masuk(nama, "x' OR '1'='1")

    def test_kunci_setelah_gagal_berulang(self):
        for _ in range(MAKS_GAGAL):
            with self.assertRaises(AkunTidakValid):
                self.auth.masuk("admin", "salah-terus-1")
        with self.assertRaises(AkunTidakValid) as e:
            self.auth.masuk("admin", "Rahasia2026")
        self.assertIn("dikunci", str(e.exception))
        self.repo.baris[1]["terkunci_sampai"] = datetime.now() - timedelta(seconds=1)   # waktu kunci habis
        self.assertTrue(self.auth.masuk("admin", "Rahasia2026"))

    def test_kebijakan_sandi(self):
        for sandi in ("pendek1", "hanyahurufsaja", "1234567890", "admin2026xx"):
            with self.assertRaises(AkunTidakValid):
                self.auth.buat_akun("petugas", "Petugas", sandi.replace("admin", "petugas"), sandi.replace("admin", "petugas"))

    def test_ganti_sandi_mengeluarkan_sesi_lama(self):
        akun = self.auth.masuk("admin", "Rahasia2026")
        self.assertIsNotNone(self.auth.pengguna_sesi(akun["id"], akun["versi_sesi"]))
        self.auth.ganti_sandi(akun["id"], "Rahasia2026", "BaruLagi2027", "BaruLagi2027")
        self.assertIsNone(self.auth.pengguna_sesi(akun["id"], akun["versi_sesi"]))
        with self.assertRaises(AkunTidakValid):
            self.auth.masuk("admin", "Rahasia2026")


class TestPembatas(unittest.TestCase):
    def test_jendela_geser(self):
        b = RateLimiter(3, 10)
        self.assertEqual([b.izinkan("ip", t) for t in (0, 1, 2, 3)], [True, True, True, False])
        self.assertFalse(b.izinkan("ip", 9.9))
        self.assertTrue(b.izinkan("ip", 10.5), "permintaan lama sudah keluar dari jendela")
        self.assertTrue(b.izinkan("ip-lain", 3), "setiap IP dihitung sendiri")


class TestPengalihan(unittest.TestCase):
    def test_hanya_jalur_lokal(self):
        self.assertEqual(alamat_aman("/riwayat?sesi=2"), "/riwayat?sesi=2")
        for jahat in ("//situs-jahat.example", "https://situs-jahat.example", "/\\situs-jahat.example",
                      "javascript:alert(1)", "", None):
            self.assertEqual(alamat_aman(jahat, "/"), "/")


if __name__ == "__main__":
    unittest.main()
