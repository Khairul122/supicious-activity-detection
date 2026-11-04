"""Data tier: koneksi MySQL/MariaDB (Laragon) dan skema. Hanya lapisan data yang menyentuh SQL.

Database dan tabel dibuat otomatis saat web dimulai, lalu dapat dilihat di phpMyAdmin.
"""
import re

import pymysql
from pymysql.cursors import DictCursor

from .. import log

logger = log.get("database")

TABLES = [
    """
    CREATE TABLE IF NOT EXISTS sesi (
        id INT UNSIGNED NOT NULL AUTO_INCREMENT,
        jenis VARCHAR(10) NOT NULL COMMENT 'webcam, stream, atau berkas',
        sumber VARCHAR(255) NOT NULL COMMENT 'sandi RTSP disamarkan',
        mulai DATETIME NOT NULL,
        selesai DATETIME NULL,
        frame INT UNSIGNED NOT NULL DEFAULT 0,
        status VARCHAR(20) NOT NULL COMMENT 'berjalan, selesai, dihentikan, terputus, galat, terhenti',
        catatan TEXT NULL,
        mode VARCHAR(10) NULL COMMENT 'umum atau parkir',
        PRIMARY KEY (id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Sesi pemantauan kamera'
    """,
    """
    CREATE TABLE IF NOT EXISTS peringatan (
        id INT UNSIGNED NOT NULL AUTO_INCREMENT,
        sesi_id INT UNSIGNED NOT NULL,
        waktu DATETIME NOT NULL,
        detik DOUBLE NOT NULL COMMENT 'detik sejak sesi dimulai',
        id_orang INT NOT NULL,
        alasan VARCHAR(255) NOT NULL,
        kategori VARCHAR(20) NULL COMMENT 'terlarang, sensitif, mondar-mandir, diam, atau kategori parkiran (dekat_motor, jongkok_motor, pindah_motor, motor_didorong, motor_dibawa)',
        zona VARCHAR(60) NULL,
        snapshot VARCHAR(255) NULL,
        x1 INT NULL, y1 INT NULL, x2 INT NULL, y2 INT NULL,
        penilaian VARCHAR(12) NULL COMMENT 'benar atau alarm_palsu (penilaian petugas)',
        dinilai_pada DATETIME NULL,
        PRIMARY KEY (id),
        KEY idx_peringatan_waktu (waktu),
        KEY idx_peringatan_sesi (sesi_id),
        CONSTRAINT fk_peringatan_sesi FOREIGN KEY (sesi_id) REFERENCES sesi (id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Peringatan perilaku suspicious'
    """,
    """
    CREATE TABLE IF NOT EXISTS zona (
        id INT UNSIGNED NOT NULL AUTO_INCREMENT,
        sumber VARCHAR(255) NOT NULL COMMENT 'kunci sumber: Webcam 0, alamat stream tersamar, atau nama berkas',
        nama VARCHAR(60) NOT NULL,
        jenis VARCHAR(12) NOT NULL COMMENT 'santai, sensitif, atau terlarang',
        titik TEXT NOT NULL COMMENT 'JSON [[x, y], ...] ternormalisasi 0-1',
        jam_mulai TIME NULL COMMENT 'jam aktif; NULL = selalu aktif',
        jam_selesai TIME NULL,
        dibuat DATETIME NOT NULL,
        PRIMARY KEY (id),
        KEY idx_zona_sumber (sumber)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Zona pengawasan per sumber kamera'
    """,
    """
    CREATE TABLE IF NOT EXISTS sumber_mode (
        sumber VARCHAR(255) NOT NULL COMMENT 'kunci sumber, sama dengan tabel zona',
        mode VARCHAR(10) NOT NULL COMMENT 'pilihan pengguna: otomatis, umum, atau parkir',
        hasil_otomatis VARCHAR(10) NULL COMMENT 'hasil mode otomatis terakhir: umum atau parkir',
        diubah DATETIME NOT NULL,
        PRIMARY KEY (sumber)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Mode deteksi terakhir per sumber kamera'
    """,
    """
    CREATE TABLE IF NOT EXISTS pengguna (
        id INT UNSIGNED NOT NULL AUTO_INCREMENT,
        nama_pengguna VARCHAR(40) NOT NULL,
        nama VARCHAR(80) NOT NULL,
        hash_sandi VARCHAR(255) NOT NULL COMMENT 'PBKDF2-SHA256, tidak pernah sandi asli',
        dibuat DATETIME NOT NULL,
        masuk_terakhir DATETIME NULL,
        gagal INT UNSIGNED NOT NULL DEFAULT 0 COMMENT 'percobaan masuk gagal berturut-turut',
        terkunci_sampai DATETIME NULL,
        versi_sesi INT UNSIGNED NOT NULL DEFAULT 1 COMMENT 'naik saat sandi diganti: semua sesi lama keluar',
        PRIMARY KEY (id),
        UNIQUE KEY uk_nama_pengguna (nama_pengguna)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Akun petugas yang boleh masuk ke web'
    """,
]

# Kolom yang ditambahkan setelah versi awal. Diperiksa lewat information_schema agar aman
# untuk MySQL 8 (tidak mendukung ADD COLUMN IF NOT EXISTS) maupun MariaDB.
MIGRATIONS = [
    ("peringatan", "kategori", "VARCHAR(20) NULL COMMENT 'terlarang, sensitif, mondar-mandir, atau diam' AFTER alasan"),
    ("peringatan", "zona", "VARCHAR(60) NULL AFTER kategori"),
    ("peringatan", "penilaian", "VARCHAR(12) NULL COMMENT 'benar atau alarm_palsu (penilaian petugas)' AFTER y2"),
    ("peringatan", "dinilai_pada", "DATETIME NULL AFTER penilaian"),
    ("zona", "jam_mulai", "TIME NULL COMMENT 'jam aktif; NULL = selalu aktif' AFTER titik"),
    ("zona", "jam_selesai", "TIME NULL AFTER jam_mulai"),
    ("sesi", "mode", "VARCHAR(10) NULL COMMENT 'umum atau parkir' AFTER catatan"),
    ("sesi", "mode_otomatis", "TINYINT(1) NOT NULL DEFAULT 0 COMMENT '1 = mode dipilih otomatis' AFTER mode"),
    ("sumber_mode", "hasil_otomatis", "VARCHAR(10) NULL COMMENT 'hasil mode otomatis terakhir' AFTER mode"),
]


class DatabaseUnavailable(RuntimeError):
    pass


class Database:
    def __init__(self, host, port, user, password, name):
        self.params = {"host": host, "port": int(port), "user": user, "password": password,
                       "charset": "utf8mb4", "autocommit": True, "cursorclass": DictCursor, "connect_timeout": 5}
        if not re.fullmatch(r"[A-Za-z0-9_]{1,64}", name or ""):
            raise DatabaseUnavailable("Nama database hanya boleh huruf, angka, dan garis bawah.")
        self.name = name
        try:
            server = pymysql.connect(**self.params)
        except pymysql.err.OperationalError as error:
            raise DatabaseUnavailable(
                f"Tidak dapat terhubung ke MySQL di {host}:{port} sebagai '{user}'. "
                "Pastikan Laragon sudah dijalankan (Start All) dan MySQL aktif.") from error
        with server, server.cursor() as cur:
            cur.execute(f"CREATE DATABASE IF NOT EXISTS `{name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            versi = server.get_server_info()
        logger.info("Terhubung ke MySQL %s di %s:%s, database '%s'", versi, host, port, name)
        with self.connect() as conn, conn.cursor() as cur:
            for ddl in TABLES:
                cur.execute(ddl)
            for table, column, definition in MIGRATIONS:
                cur.execute("SELECT COUNT(*) AS n FROM information_schema.COLUMNS"
                            " WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s AND COLUMN_NAME = %s", (name, table, column))
                if cur.fetchone()["n"] == 0:
                    cur.execute(f"ALTER TABLE `{table}` ADD COLUMN `{column}` {definition}")
                    logger.info("Migrasi: kolom %s.%s ditambahkan", table, column)
            cur.execute("SELECT (SELECT COUNT(*) FROM sesi) AS sesi, (SELECT COUNT(*) FROM peringatan) AS peringatan,"
                        " (SELECT COUNT(*) FROM zona) AS zona")
            n = cur.fetchone()
        logger.info("Tabel siap: %d sesi, %d peringatan, %d zona tersimpan", n["sesi"], n["peringatan"], n["zona"])

    def connect(self):
        return pymysql.connect(database=self.name, **self.params)

    def execute(self, sql, args=()):
        """Tulis data; kembalikan id baris terakhir."""
        with self.connect() as conn, conn.cursor() as cur:
            cur.execute(sql, args)
            return cur.lastrowid

    def query(self, sql, args=()):
        with self.connect() as conn, conn.cursor() as cur:
            cur.execute(sql, args)
            return list(cur.fetchall())

    def query_one(self, sql, args=()):
        rows = self.query(sql, args)
        return rows[0] if rows else None
