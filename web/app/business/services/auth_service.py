"""Business tier: akun dan proses masuk.

- Sandi disimpan sebagai hash PBKDF2-SHA256 600.000 putaran (rekomendasi OWASP 2023), tidak pernah teks asli.
- Lima kali gagal berturut-turut mengunci akun selama 15 menit.
- Pesan gagal sama untuk nama pengguna salah dan sandi salah agar nama akun tidak bisa ditebak.
- versi_sesi naik setiap sandi diganti, sehingga semua sesi lama otomatis keluar.
"""
import re
from datetime import datetime, timedelta

from werkzeug.security import check_password_hash, generate_password_hash

from ... import log

logger = log.get("akun")

METODE_HASH = "pbkdf2:sha256:600000"
MAKS_GAGAL = 5
KUNCI_MENIT = 15
POLA_NAMA = re.compile(r"[a-z0-9._-]{3,40}")
SANDI_MIN = 8
# hash tiruan agar pemeriksaan nama yang tidak ada butuh waktu sama dengan nama yang ada
_HASH_TIRUAN = generate_password_hash("sandi-tiruan-untuk-waktu-sama", method=METODE_HASH)


class AkunTidakValid(ValueError):
    pass


def periksa_sandi_baru(sandi, nama_pengguna=""):
    if len(sandi or "") < SANDI_MIN:
        raise AkunTidakValid(f"Sandi minimal {SANDI_MIN} karakter.")
    if len(sandi) > 128:
        raise AkunTidakValid("Sandi maksimal 128 karakter.")
    if not (re.search(r"[A-Za-z]", sandi) and re.search(r"\d", sandi)):
        raise AkunTidakValid("Sandi harus berisi huruf dan angka.")
    if nama_pengguna and nama_pengguna.lower() in sandi.lower():
        raise AkunTidakValid("Sandi tidak boleh memuat nama pengguna.")


class AuthService:
    def __init__(self, pengguna_repo):
        self.repo = pengguna_repo

    def perlu_pengaturan_awal(self):
        return self.repo.count() == 0

    def buat_admin_pertama(self, nama_pengguna, nama, sandi, ulang_sandi):
        """Hanya boleh saat belum ada akun sama sekali."""
        if not self.perlu_pengaturan_awal():
            raise AkunTidakValid("Akun admin sudah dibuat. Silakan masuk.")
        return self.buat_akun(nama_pengguna, nama, sandi, ulang_sandi)

    def buat_akun(self, nama_pengguna, nama, sandi, ulang_sandi):
        nama_pengguna = (nama_pengguna or "").strip().lower()
        nama = (nama or "").strip()
        if not POLA_NAMA.fullmatch(nama_pengguna):
            raise AkunTidakValid("Nama pengguna 3 sampai 40 karakter: huruf kecil, angka, titik, garis bawah, atau strip.")
        if not 1 <= len(nama) <= 80:
            raise AkunTidakValid("Nama lengkap wajib diisi, maksimal 80 karakter.")
        if sandi != ulang_sandi:
            raise AkunTidakValid("Kedua sandi tidak sama.")
        periksa_sandi_baru(sandi, nama_pengguna)
        if self.repo.by_username(nama_pengguna):
            raise AkunTidakValid("Nama pengguna sudah dipakai.")
        pid = self.repo.create(nama_pengguna, nama, generate_password_hash(sandi, method=METODE_HASH),
                               datetime.now().replace(microsecond=0))
        logger.info("Akun dibuat: %s", nama_pengguna)
        return pid

    def masuk(self, nama_pengguna, sandi, ip="-"):
        """Kembalikan baris pengguna bila berhasil; lempar AkunTidakValid bila gagal."""
        nama_pengguna = (nama_pengguna or "").strip().lower()[:40]
        sandi = (sandi or "")[:128]
        akun = self.repo.by_username(nama_pengguna) if POLA_NAMA.fullmatch(nama_pengguna) else None
        sekarang = datetime.now().replace(microsecond=0)
        if akun and akun["terkunci_sampai"] and akun["terkunci_sampai"] > sekarang:
            menit = max(1, round((akun["terkunci_sampai"] - sekarang).total_seconds() / 60))
            logger.warning("Masuk ditolak (akun terkunci): %s dari %s", nama_pengguna, ip)
            raise AkunTidakValid(f"Akun dikunci sementara karena terlalu banyak percobaan. Coba lagi {menit} menit lagi.")
        if not akun:
            check_password_hash(_HASH_TIRUAN, sandi)   # samakan waktu respons
            logger.warning("Masuk gagal (nama tidak dikenal) dari %s", ip)
            raise AkunTidakValid("Nama pengguna atau sandi salah.")
        if not check_password_hash(akun["hash_sandi"], sandi):
            gagal = akun["gagal"] + 1
            kunci = sekarang + timedelta(minutes=KUNCI_MENIT) if gagal >= MAKS_GAGAL else None
            self.repo.catat_gagal(akun["id"], 0 if kunci else gagal, kunci)
            logger.warning("Masuk gagal: %s dari %s (percobaan %d)%s", nama_pengguna, ip, gagal,
                           f", akun dikunci {KUNCI_MENIT} menit" if kunci else "")
            if kunci:
                raise AkunTidakValid(f"Sandi salah {MAKS_GAGAL} kali. Akun dikunci {KUNCI_MENIT} menit.")
            sisa = MAKS_GAGAL - gagal
            raise AkunTidakValid("Nama pengguna atau sandi salah." + (f" Sisa {sisa} percobaan sebelum akun dikunci." if sisa <= 2 else ""))
        self.repo.catat_masuk(akun["id"], sekarang)
        logger.info("Masuk: %s dari %s", nama_pengguna, ip)
        return akun

    def pengguna_sesi(self, pengguna_id, versi_sesi):
        """Pengguna untuk sesi yang masih sah, atau None bila akun hilang atau sandi sudah diganti."""
        try:
            akun = self.repo.by_id(pengguna_id)
        except (TypeError, ValueError):
            return None
        if not akun or akun["versi_sesi"] != versi_sesi:
            return None
        return akun

    def ganti_sandi(self, pengguna_id, sandi_lama, sandi_baru, ulang_sandi):
        akun = self.repo.by_id(pengguna_id)
        if not akun or not check_password_hash(akun["hash_sandi"], sandi_lama or ""):
            raise AkunTidakValid("Sandi lama salah.")
        if sandi_baru != ulang_sandi:
            raise AkunTidakValid("Kedua sandi baru tidak sama.")
        periksa_sandi_baru(sandi_baru, akun["nama_pengguna"])
        self.repo.set_sandi(akun["id"], generate_password_hash(sandi_baru, method=METODE_HASH))
        logger.info("Sandi diganti: %s", akun["nama_pengguna"])
        return self.repo.by_id(akun["id"])

    def atur_ulang_sandi(self, nama_pengguna, sandi_baru):
        """Untuk pemilik komputer lewat terminal (run.py --atur-ulang-sandi)."""
        akun = self.repo.by_username((nama_pengguna or "").strip().lower())
        if not akun:
            raise AkunTidakValid(f"Akun '{nama_pengguna}' tidak ditemukan.")
        periksa_sandi_baru(sandi_baru, akun["nama_pengguna"])
        self.repo.set_sandi(akun["id"], generate_password_hash(sandi_baru, method=METODE_HASH))
        logger.info("Sandi diatur ulang lewat terminal: %s", akun["nama_pengguna"])
