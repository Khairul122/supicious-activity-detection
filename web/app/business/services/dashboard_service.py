"""Business tier: ringkasan untuk dashboard."""
from datetime import date, timedelta

HARI = ["Sen", "Sel", "Rab", "Kam", "Jum", "Sab", "Min"]


class DashboardService:
    def __init__(self, peringatan_repo, sesi_repo, kamera_service, info_sistem):
        self.peringatan_repo, self.sesi_repo = peringatan_repo, sesi_repo
        self.kamera_service, self.info_sistem = kamera_service, info_sistem

    def ringkasan(self):
        today = date.today()
        days = [today - timedelta(days=i) for i in range(6, -1, -1)]
        per_day = {d.isoformat(): 0 for d in days}
        for row in self.peringatan_repo.count_per_day(days[0].isoformat()):
            per_day[row["tanggal"]] = row["n"]
        per_hour = [0] * 24
        for row in self.peringatan_repo.count_per_hour(today.isoformat()):
            per_hour[row["jam"]] = row["n"]
        max_day, max_hour = max(per_day.values()) or 1, max(per_hour) or 1
        nilai = self.peringatan_repo.count_assessment()
        benar, palsu, belum = nilai.get("benar", 0), nilai.get("alarm_palsu", 0), nilai.get("belum", 0)
        return {
            "hari_ini": per_day[today.isoformat()],
            "tujuh_hari": sum(per_day.values()),
            "total": self.peringatan_repo.count(),
            "jumlah_sesi": self.sesi_repo.count(),
            "penilaian": {"benar": benar, "alarm_palsu": palsu, "belum": belum,
                          "precision": (benar / (benar + palsu)) if benar + palsu else None},
            "per_hari": [{"label": f"{HARI[d.weekday()]} {d.day}", "n": per_day[d.isoformat()],
                          "persen": round(100 * per_day[d.isoformat()] / max_day)} for d in days],
            "per_jam": [{"jam": h, "n": n, "persen": round(100 * n / max_hour)} for h, n in enumerate(per_hour)],
            "terbaru": self.peringatan_repo.search(limit=6),
            "sesi_terbaru": self.sesi_repo.latest(5),
            "kamera": self.kamera_service.status(),
            "sistem": self.info_sistem,
        }
