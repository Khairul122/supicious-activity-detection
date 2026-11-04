"""Data tier: mode deteksi terakhir per sumber kamera."""


class SumberRepository:
    def __init__(self, db):
        self.db = db

    def get_mode(self, sumber):
        row = self.db.query_one("SELECT mode FROM sumber_mode WHERE sumber = %s", (sumber,))
        return row["mode"] if row else None

    def get_hasil_otomatis(self, sumber):
        row = self.db.query_one("SELECT hasil_otomatis FROM sumber_mode WHERE sumber = %s", (sumber,))
        return row["hasil_otomatis"] if row else None

    def set_hasil_otomatis(self, sumber, mode):
        self.db.execute("UPDATE sumber_mode SET hasil_otomatis = %s WHERE sumber = %s", (mode, sumber))

    def set_mode(self, sumber, mode, waktu):
        self.db.execute("INSERT INTO sumber_mode (sumber, mode, diubah) VALUES (%s, %s, %s)"
                        " ON DUPLICATE KEY UPDATE mode = VALUES(mode), diubah = VALUES(diubah)", (sumber, mode, waktu))
