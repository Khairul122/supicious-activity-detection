"""Data tier: akses tabel sesi."""


class SesiRepository:
    def __init__(self, db):
        self.db = db

    def create(self, jenis, sumber, mulai, mode="umum"):
        return self.db.execute("INSERT INTO sesi (jenis, sumber, mulai, status, mode) VALUES (%s, %s, %s, 'berjalan', %s)",
                               (jenis, sumber, mulai, mode))

    def set_mode(self, sesi_id, mode, otomatis=False):
        """Catat mode akhir sesi (mode otomatis diputuskan beberapa detik setelah mulai)."""
        self.db.execute("UPDATE sesi SET mode = %s, mode_otomatis = %s WHERE id = %s", (mode, int(bool(otomatis)), sesi_id))

    def finish(self, sesi_id, selesai, frame, status, catatan=""):
        self.db.execute("UPDATE sesi SET selesai = %s, frame = %s, status = %s, catatan = %s WHERE id = %s",
                        (selesai, frame, status, catatan, sesi_id))

    def mark_interrupted(self):
        """Sesi yang masih 'berjalan' saat server dimulai berarti server sebelumnya berhenti mendadak."""
        self.db.execute("UPDATE sesi SET status = 'terhenti', selesai = COALESCE(selesai, mulai) WHERE status = 'berjalan'")

    def get(self, sesi_id):
        return self.db.query_one("SELECT * FROM sesi WHERE id = %s", (sesi_id,))

    def latest(self, limit=10):
        return self.db.query(
            "SELECT s.*, (SELECT COUNT(*) FROM peringatan p WHERE p.sesi_id = s.id) AS jumlah_peringatan"
            " FROM sesi s ORDER BY s.id DESC LIMIT %s", (limit,))

    def count(self):
        return self.db.query_one("SELECT COUNT(*) AS n FROM sesi")["n"]
