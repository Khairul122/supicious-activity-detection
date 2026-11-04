"""Business tier: riwayat peringatan (pencarian, halaman, ekspor)."""
import csv
import io
import math
from datetime import date, datetime

from ... import log

logger = log.get("riwayat")

PER_PAGE = 20
PENILAIAN = ("benar", "alarm_palsu")
FILTER_PENILAIAN = ("belum", "benar", "alarm_palsu")


class RiwayatService:
    def __init__(self, peringatan_repo, sesi_repo, snapshots):
        self.peringatan_repo, self.sesi_repo, self.snapshots = peringatan_repo, sesi_repo, snapshots

    @staticmethod
    def _valid_date(value):
        try:
            return date.fromisoformat(value).isoformat() if value else None
        except ValueError:
            return None

    def cari(self, tanggal=None, sesi_id=None, halaman=1, penilaian=None):
        tanggal = self._valid_date(tanggal)
        sesi_id = int(sesi_id) if str(sesi_id or "").isdigit() else None
        penilaian = penilaian if penilaian in FILTER_PENILAIAN else None
        total = self.peringatan_repo.count(tanggal, sesi_id, penilaian)
        pages = max(1, math.ceil(total / PER_PAGE))
        halaman = min(max(1, int(halaman) if str(halaman).isdigit() else 1), pages)
        items = self.peringatan_repo.search(tanggal, sesi_id, PER_PAGE, (halaman - 1) * PER_PAGE, penilaian)
        return {"baris": items, "total": total, "halaman": halaman, "jumlah_halaman": pages,
                "tanggal": tanggal or "", "sesi_id": sesi_id or "", "penilaian": penilaian or "",
                "daftar_sesi": self.sesi_repo.latest(100)}

    def jumlah_belum(self):
        """Jumlah peringatan yang belum dinilai petugas."""
        return self.peringatan_repo.count(None, None, "belum")

    def terbaru(self, sesi_id=None, limit=8):
        """Peringatan terbaru (paling baru dulu), opsional untuk satu sesi."""
        sesi_id = int(sesi_id) if str(sesi_id or "").isdigit() else None
        limit = min(max(int(limit) if str(limit).isdigit() else 8, 1), 50)
        return self.peringatan_repo.search(None, sesi_id, limit, 0)

    def nilai(self, peringatan_id, penilaian):
        """Simpan penilaian petugas: benar, alarm_palsu, atau kosong untuk membatalkan."""
        if penilaian not in PENILAIAN + ("",):
            raise ValueError("Penilaian tidak dikenal.")
        self.peringatan_repo.set_assessment(int(peringatan_id), penilaian or None, datetime.now().replace(microsecond=0))
        logger.info("Peringatan %s dinilai: %s", peringatan_id, penilaian or "dibatalkan")

    def ekspor_csv(self, tanggal=None, sesi_id=None):
        tanggal = self._valid_date(tanggal)
        sesi_id = int(sesi_id) if str(sesi_id or "").isdigit() else None
        total = self.peringatan_repo.count(tanggal, sesi_id)
        rows = self.peringatan_repo.search(tanggal, sesi_id, max(total, 1), 0)
        out = io.StringIO()
        writer = csv.writer(out)
        writer.writerow(["id", "waktu", "sesi", "sumber", "detik_sesi", "id_orang", "kategori", "zona", "alasan",
                         "penilaian", "dinilai_pada", "snapshot", "x1", "y1", "x2", "y2"])
        for r in rows:
            writer.writerow([r["id"], r["waktu"], r["sesi_id"], r["sumber"], r["detik"], r["id_orang"], r.get("kategori"),
                             r.get("zona"), r["alasan"], r.get("penilaian") or "belum", r.get("dinilai_pada") or "",
                             r["snapshot"], r["x1"], r["y1"], r["x2"], r["y2"]])
        return out.getvalue()

    def snapshot(self, name):
        return self.snapshots.path(name)
