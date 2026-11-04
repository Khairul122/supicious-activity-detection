"""Data tier: akses tabel zona."""
import json


class ZonaRepository:
    def __init__(self, db):
        self.db = db

    @staticmethod
    def _jam(value):
        """Kolom TIME dibaca PyMySQL sebagai timedelta; ubah menjadi 'HH:MM'."""
        if value is None:
            return None
        if hasattr(value, "total_seconds"):
            menit = int(value.total_seconds()) // 60
            return f"{menit // 60 % 24:02d}:{menit % 60:02d}"
        return str(value)[:5]

    @classmethod
    def _decode(cls, row):
        row = dict(row)
        row["titik"] = json.loads(row["titik"])
        row["jam_mulai"], row["jam_selesai"] = cls._jam(row.get("jam_mulai")), cls._jam(row.get("jam_selesai"))
        row["dibuat"] = str(row["dibuat"]) if row.get("dibuat") is not None else None
        return row

    def list_by_source(self, sumber):
        return [self._decode(r) for r in self.db.query("SELECT * FROM zona WHERE sumber = %s ORDER BY id", (sumber,))]

    def get(self, zona_id):
        row = self.db.query_one("SELECT * FROM zona WHERE id = %s", (zona_id,))
        return self._decode(row) if row else None

    def create(self, sumber, nama, jenis, titik, dibuat, jam_mulai=None, jam_selesai=None):
        return self.db.execute(
            "INSERT INTO zona (sumber, nama, jenis, titik, jam_mulai, jam_selesai, dibuat) VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (sumber, nama, jenis, json.dumps(titik), jam_mulai, jam_selesai, dibuat))

    def delete(self, zona_id):
        self.db.execute("DELETE FROM zona WHERE id = %s", (zona_id,))
