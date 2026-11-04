"""Data tier: akun pengguna web."""


class PenggunaRepository:
    def __init__(self, db):
        self.db = db

    def count(self):
        return self.db.query_one("SELECT COUNT(*) AS n FROM pengguna")["n"]

    def by_username(self, nama_pengguna):
        return self.db.query_one("SELECT * FROM pengguna WHERE nama_pengguna = %s", (nama_pengguna,))

    def by_id(self, pengguna_id):
        return self.db.query_one("SELECT * FROM pengguna WHERE id = %s", (int(pengguna_id),))

    def create(self, nama_pengguna, nama, hash_sandi, waktu):
        return self.db.execute("INSERT INTO pengguna (nama_pengguna, nama, hash_sandi, dibuat) VALUES (%s, %s, %s, %s)",
                               (nama_pengguna, nama, hash_sandi, waktu))

    def catat_gagal(self, pengguna_id, gagal, terkunci_sampai):
        self.db.execute("UPDATE pengguna SET gagal = %s, terkunci_sampai = %s WHERE id = %s",
                        (gagal, terkunci_sampai, pengguna_id))

    def catat_masuk(self, pengguna_id, waktu):
        self.db.execute("UPDATE pengguna SET gagal = 0, terkunci_sampai = NULL, masuk_terakhir = %s WHERE id = %s",
                        (waktu, pengguna_id))

    def set_sandi(self, pengguna_id, hash_sandi):
        self.db.execute("UPDATE pengguna SET hash_sandi = %s, versi_sesi = versi_sesi + 1, gagal = 0,"
                        " terkunci_sampai = NULL WHERE id = %s", (hash_sandi, pengguna_id))
