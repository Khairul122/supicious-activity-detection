"""Business tier: zona pengawasan per sumber kamera."""
from datetime import datetime

from ... import log
from ..detection.zones import JENIS, ZoneSet, ke_menit

logger = log.get("zona")


class ZonaTidakValid(ValueError):
    pass


class ZonaService:
    def __init__(self, zona_repo, engine):
        self.zona_repo, self.engine = zona_repo, engine

    def daftar(self, sumber):
        return self.zona_repo.list_by_source(sumber)

    def zone_set(self, sumber):
        return ZoneSet.from_rows(self.daftar(sumber))

    def _refresh_engine(self, sumber):
        self.engine.set_zones(sumber, self.zone_set(sumber))

    @staticmethod
    def _jadwal(jam_mulai, jam_selesai):
        """Validasi jam aktif. Kosong keduanya = selalu aktif."""
        jam_mulai, jam_selesai = (jam_mulai or "").strip(), (jam_selesai or "").strip()
        if not jam_mulai and not jam_selesai:
            return None, None
        if not jam_mulai or not jam_selesai:
            raise ZonaTidakValid("Isi jam mulai dan jam selesai, atau kosongkan keduanya agar zona selalu aktif.")
        try:
            a, b = ke_menit(jam_mulai), ke_menit(jam_selesai)
        except (ValueError, TypeError):
            raise ZonaTidakValid("Format jam harus HH:MM, misalnya 22:00.") from None
        if a == b:
            raise ZonaTidakValid("Jam mulai dan jam selesai tidak boleh sama.")
        return f"{a // 60:02d}:{a % 60:02d}", f"{b // 60:02d}:{b % 60:02d}"

    def tambah(self, sumber, nama, jenis, titik, jam_mulai=None, jam_selesai=None):
        nama = (nama or "").strip()
        if not 1 <= len(nama) <= 60:
            raise ZonaTidakValid("Nama zona wajib diisi, maksimal 60 karakter.")
        if jenis not in JENIS:
            raise ZonaTidakValid("Jenis zona harus santai, sensitif, atau terlarang.")
        try:
            pts = [(round(float(x), 4), round(float(y), 4)) for x, y in titik]
        except (TypeError, ValueError):
            raise ZonaTidakValid("Titik zona tidak valid.") from None
        if not 3 <= len(pts) <= 40 or not all(0 <= v <= 1 for p in pts for v in p):
            raise ZonaTidakValid("Zona memerlukan 3 sampai 40 titik di dalam gambar.")
        jam_mulai, jam_selesai = self._jadwal(jam_mulai, jam_selesai)
        zid = self.zona_repo.create(sumber, nama, jenis, pts, datetime.now().replace(microsecond=0), jam_mulai, jam_selesai)
        self._refresh_engine(sumber)
        logger.info("Zona ditambahkan: '%s' (%s, %d titik, %s) untuk sumber %s", nama, jenis, len(pts),
                    f"aktif {jam_mulai}-{jam_selesai}" if jam_mulai else "selalu aktif", sumber)
        return zid

    def hapus(self, zona_id):
        zone = self.zona_repo.get(zona_id)
        if zone is None:
            raise ZonaTidakValid("Zona tidak ditemukan.")
        self.zona_repo.delete(zona_id)
        self._refresh_engine(zone["sumber"])
        logger.info("Zona dihapus: '%s' (%s) dari sumber %s", zone["nama"], zone["jenis"], zone["sumber"])
