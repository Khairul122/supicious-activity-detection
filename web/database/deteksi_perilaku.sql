-- Skema basis data web deteksi perilaku (MySQL 5.7+/8, MariaDB 10+).
-- Web membuat database dan tabel ini otomatis saat dijalankan, termasuk menambah kolom baru ke tabel lama.
-- Berkas ini hanya untuk impor manual lewat phpMyAdmin bila diperlukan.

CREATE DATABASE IF NOT EXISTS `deteksi_perilaku` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE `deteksi_perilaku`;

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
    mode_otomatis TINYINT(1) NOT NULL DEFAULT 0 COMMENT '1 = mode dipilih otomatis',
    PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Sesi pemantauan kamera';

CREATE TABLE IF NOT EXISTS peringatan (
    id INT UNSIGNED NOT NULL AUTO_INCREMENT,
    sesi_id INT UNSIGNED NOT NULL,
    waktu DATETIME NOT NULL,
    detik DOUBLE NOT NULL COMMENT 'detik sejak sesi dimulai',
    id_orang INT NOT NULL,
    alasan VARCHAR(255) NOT NULL,
    kategori VARCHAR(20) NULL COMMENT 'terlarang, sensitif, mondar-mandir, diam, dekat_motor, pindah_motor, motor_didorong',
    zona VARCHAR(60) NULL,
    snapshot VARCHAR(255) NULL,
    x1 INT NULL, y1 INT NULL, x2 INT NULL, y2 INT NULL,
    penilaian VARCHAR(12) NULL COMMENT 'benar atau alarm_palsu (penilaian petugas)',
    dinilai_pada DATETIME NULL,
    PRIMARY KEY (id),
    KEY idx_peringatan_waktu (waktu),
    KEY idx_peringatan_sesi (sesi_id),
    CONSTRAINT fk_peringatan_sesi FOREIGN KEY (sesi_id) REFERENCES sesi (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Peringatan perilaku suspicious';

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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Zona pengawasan per sumber kamera';

CREATE TABLE IF NOT EXISTS sumber_mode (
    sumber VARCHAR(255) NOT NULL COMMENT 'kunci sumber, sama dengan tabel zona',
    mode VARCHAR(10) NOT NULL COMMENT 'pilihan pengguna: otomatis, umum, atau parkir',
    hasil_otomatis VARCHAR(10) NULL COMMENT 'hasil mode otomatis terakhir: umum atau parkir',
    diubah DATETIME NOT NULL,
    PRIMARY KEY (sumber)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Mode deteksi terakhir per sumber kamera';
