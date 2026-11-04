"""Data tier: akses tabel peringatan."""


class PeringatanRepository:
    def __init__(self, db):
        self.db = db

    def create(self, sesi_id, waktu, detik, id_orang, alasan, snapshot, box, kategori=None, zona=None):
        return self.db.execute(
            "INSERT INTO peringatan (sesi_id, waktu, detik, id_orang, alasan, kategori, zona, snapshot, x1, y1, x2, y2)"
            " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (sesi_id, waktu, detik, id_orang, alasan, kategori, zona, snapshot, *box))

    def set_assessment(self, peringatan_id, penilaian, waktu):
        self.db.execute("UPDATE peringatan SET penilaian = %s, dinilai_pada = %s WHERE id = %s",
                        (penilaian, waktu if penilaian else None, peringatan_id))

    def count_assessment(self):
        rows = self.db.query("SELECT COALESCE(penilaian, 'belum') AS penilaian, COUNT(*) AS n FROM peringatan"
                             " GROUP BY COALESCE(penilaian, 'belum')")
        return {r["penilaian"]: r["n"] for r in rows}

    @staticmethod
    def _filter(tanggal, sesi_id, penilaian=None):
        where, args = [], []
        if penilaian == "belum":
            where.append("p.penilaian IS NULL")
        elif penilaian:
            where.append("p.penilaian = %s")
            args.append(penilaian)
        if tanggal:
            where.append("DATE(p.waktu) = %s")
            args.append(tanggal)
        if sesi_id:
            where.append("p.sesi_id = %s")
            args.append(sesi_id)
        return ("WHERE " + " AND ".join(where)) if where else "", args

    def count(self, tanggal=None, sesi_id=None, penilaian=None):
        clause, args = self._filter(tanggal, sesi_id, penilaian)
        return self.db.query_one(f"SELECT COUNT(*) AS n FROM peringatan p {clause}", args)["n"]

    def search(self, tanggal=None, sesi_id=None, limit=25, offset=0, penilaian=None):
        clause, args = self._filter(tanggal, sesi_id, penilaian)
        return self.db.query(
            "SELECT p.*, s.jenis, s.sumber FROM peringatan p JOIN sesi s ON s.id = p.sesi_id"
            f" {clause} ORDER BY p.waktu DESC, p.id DESC LIMIT %s OFFSET %s", args + [int(limit), int(offset)])

    def count_per_day(self, since_date):
        """Kembalikan baris (tanggal 'YYYY-MM-DD', n)."""
        rows = self.db.query("SELECT DATE(waktu) AS tanggal, COUNT(*) AS n FROM peringatan"
                             " WHERE waktu >= %s GROUP BY DATE(waktu)", (since_date,))
        return [{"tanggal": str(r["tanggal"]), "n": r["n"]} for r in rows]

    def count_per_hour(self, date):
        return self.db.query("SELECT HOUR(waktu) AS jam, COUNT(*) AS n FROM peringatan"
                             " WHERE DATE(waktu) = %s GROUP BY HOUR(waktu)", (date,))
