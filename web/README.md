# Web deteksi perilaku (Flask, arsitektur multitier)

Aplikasi web lokal untuk memantau CCTV dan menandai perilaku `safe` atau `suspicious`.

- **Masuk:** setiap petugas masuk dengan akun. Saat pertama kali dibuka, web meminta pembuatan akun admin.
- **Ringkasan:** status kamera, jumlah peringatan yang belum dinilai, grafik per hari dan per jam, peringatan terbaru, sesi terbaru, info sistem.
- **Kamera:** 3 langkah (sumber, mode, mulai), tayangan berkotak dalam bingkai monitor, peringatan sesi langsung dengan foto dan bunyi, penilaian cepat, zona pengawasan berjadwal, unggah video dengan kemajuan.
- **Riwayat:** kartu foto setiap peringatan, saringan penilaian, tanggal, dan sesi, penilaian satu klik, unduh CSV.
- **Akun:** data akun, ganti sandi, keluar.
- Semua pemberitahuan (mulai sesi, berhasil, gagal, masuk, keluar, konfirmasi hapus) tampil sebagai kotak dialog. Peringatan deteksi saat video berjalan tampil sebagai notifikasi di pojok agar tidak menutup tayangan.

Label `suspicious` adalah peringatan untuk ditinjau petugas, bukan bukti niat atau tindak pidana.

## Cara kerja deteksi

1. YOLO26s kelas `person` dan `motorcycle` (`web/models/best.pt` dan `web/models/motor.pt`, hasil `notebook/Latih_Semua_Model.ipynb`) mendeteksi orang dan motor.
2. BoT-SORT + ReID (`web/trackers/botsort_reid_b125.yaml`) memberi ID; ID yang terputus disambung bila muncul lagi dalam 2 detik dan dalam jarak 2 kali tinggi kotak.
3. Aturan perilaku (`app/business/detection/behavior.py`), bergantung pada ada atau tidaknya zona untuk sumber itu. Mode parkiran motor memakai model dan aturan tambahan (lihat di bawah).

**Dengan zona.** Posisi orang dinilai dari titik kakinya, yaitu tengah sisi bawah kotak.

| Zona | Kapan suspicious |
| --- | --- |
| Terlarang | Masuk zona minimal 1 detik |
| Sensitif | Berada di zona yang sama minimal 20 detik |
| Santai | Tidak pernah. Duduk, main gim, atau tidur dianggap wajar |
| Di luar zona | Hanya bila mondar-mandir setelah terlihat 20 detik |

Mondar-mandir berarti jalur minimal 3 kali tinggi kotak dan rasio jalur terhadap perpindahan bersih minimal 2,5, dalam 20 detik terakhir. Posisi dirata-rata per 1 detik sebelum jalur dihitung, sehingga getaran kotak deteksi tidak terhitung sebagai jarak tempuh dan hasilnya tidak bergantung pada fps. Jika zona tumpang tindih, prioritasnya terlarang, lalu sensitif, lalu santai. Satu orang mendapat satu peringatan per kategori, dan untuk zona sensitif atau terlarang juga per zona.

**Tanpa zona.** Dipakai aturan umum: terlihat minimal 20 detik, lalu diam atau mondar-mandir. Seseorang dianggap diam bila memenuhi semua syarat berikut dalam 20 detik terakhir:

- sebaran titik pusat maksimal 5 kali tinggi kotak;
- kecepatan median di bawah 0,3 kali tinggi badan per detik;
- bukan orang yang berjalan mendekat atau menjauh kamera. Orang dianggap berjalan searah kamera bila tinggi kotaknya berubah minimal 25% dan titik pusatnya tetap bergeser minimal 0,08 kali tinggi badan per detik. Orang diam yang membungkuk juga mengubah tinggi kotak, tetapi tidak bergeser, sehingga tetap dinilai diam.

Kotak yang terpotong tepi gambar tidak dipakai untuk menghitung perubahan ukuran. Halaman Cam menampilkan anjuran menggambar zona bila sumber belum punya zona.

### Jam aktif zona

Setiap zona boleh diberi jam aktif, misalnya zona terlarang di rolling door toko yang hanya aktif pukul 22:00 sampai 06:00. Di luar jam itu zona diabaikan dan digambar abu-abu dengan tanda "nonaktif". Jam yang melewati tengah malam didukung. Kosongkan kedua kolom jam agar zona selalu aktif. Untuk kamera, jam mengikuti jam komputer server. Untuk berkas, isi **Jam awal rekaman** di halaman Cam (misalnya 23:15) agar jam aktif zona mengikuti jam di dalam rekaman; bila kosong, dipakai jam komputer.

### Mode otomatis

Pilihan bawaan di langkah 2. Selama 10 detik pertama, aturan umum dan parkiran berjalan bersama tanpa memberi peringatan. Pada detik 10:

- minimal 2 motor terparkir: aturan parkiran;
- kurang dari 2 motor tetapi sumber ini sebelumnya terdeteksi parkiran (misalnya parkiran kosong malam hari): tetap parkiran;
- selain itu: aturan umum.

Aturan pemenang melanjutkan riwayat sejak detik 0, jadi peringatan paling lama tertunda 10 detik. Hasilnya tampil di dialog dan panel sesi, tersimpan di `sesi.mode` dan `sumber_mode.hasil_otomatis`. Pilih Umum atau Parkiran secara manual bila tebakan kurang tepat; pilihan diingat per sumber.

### Mode parkiran motor

Pilih **Parkiran** di langkah 2, atau biarkan mode otomatis memilihnya. Pilihan tersimpan per sumber video. Mode ini memakai `web/models/motor.pt` (kelas `person` dan `motorcycle`, hasil `notebook/Latih_Semua_Model.ipynb`) sebagai pengganti model orang. Hanya satu model yang berjalan per sesi.

| Aturan | Kapan suspicious | Dasar |
| --- | --- | --- |
| Motor dibawa orang lain | Pemilik dikenal dari penampilannya, tetapi motor dibawa pergi (dikendarai atau didorong) ≥ 2 detik oleh orang berpenampilan lain | Rancangan penelitian ini |
| Motor didorong | Motor terparkir dibawa sejauh ≥ 3 × tinggi motor selama ≥ 4 detik oleh orang yang tidak duduk di atasnya | Rancangan penelitian ini |
| Hilang di dekat motor | Bukan pemilik, lenyap dari pandangan saat di dekat motor (tidak keluar lewat tepi gambar) dan total ≥ 15 detik sejak mendekat | Rancangan penelitian ini |
| Jongkok di dekat motor | Bukan pemilik, tinggi kotak turun ke ≤ 65% tinggi berdirinya sambil diam di dekat motor ≥ 5 detik | Rancangan penelitian ini |
| Dekat motor orang lain | Bukan pemilik, kaki berada dalam jarak ≤ 1 × tinggi kotak motor selama ≥ 15 detik di dekat motor yang sama (ubah lewat `SAD_PARKIR_DEKAT_S`) | Adeel dkk. 2026 |
| Berpindah antarmotor | Mendekati ≥ 3 motor berbeda (masing-masing ≥ 3 detik) dalam 60 detik | Rancangan penelitian ini |

- **Motor terparkir:** kotak motor bergeser ≤ 0,3 × tingginya selama 10 detik. Motor yang sudah ada saat sesi dimulai cukup diam 3 detik. Motor terparkir yang tertutup orang tetap diingat.
- **Pemilik:** pengendara dan pembonceng yang datang bersama motor (motor terlihat bergerak lalu berhenti). Penampilan mereka (histogram warna pakaian atas dan bawah; histogram kecerahan pada rekaman inframerah) disimpan. Pemilik yang pergi lalu kembali dengan ID baru dikenali dari penampilannya. Motor yang sudah diam sejak awal rekaman tidak punya pemilik yang diketahui.
- **Dekat berarti sejajar.** Orang yang berjalan jauh di belakang motor bisa tampak dekat pada gambar 2D. Orang hanya dihitung dekat bila kakinya sejajar roda motor dan tinggi badannya sebanding dengan tinggi motor.
- **Orang tertutup motor.** Orang yang tidak terdeteksi sampai 5 detik (misalnya jongkok di balik motor) tetap dihitung sebagai orang yang sama, dan hitungan waktunya tidak mengulang. Orang yang muncul lagi di motor yang sama sampai 60 detik kemudian dengan ID baru mewarisi hitungan waktunya: langsung bila ia muncul di tempat (bukan masuk dari tepi gambar), atau bila penampilannya tidak berbeda. Peringatan untuk orang yang sedang tidak terlihat memakai kotak terakhirnya.
- **Mondar-mandir** tetap berlaku. Aturan **diam** umum tidak dipakai, karena orang menunggu dan petugas parkir wajar diam.
- **Zona tetap berlaku.** Gambar zona santai di pos petugas parkir agar petugas tidak memicu aturan parkiran. Zona terlarang berjadwal cocok untuk parkiran yang tutup pada malam hari.
- Motor butuh confidence ≥ 0,3; orang tetap 0,15.

Kotak motor terparkir digambar biru, motor bergerak abu-abu, dan motor yang terlibat peringatan merah.

### Kamera CCTV terputus

Bila stream RTSP terputus atau tidak mengirim gambar selama 15 detik, web menyambung ulang otomatis dengan jeda 2, 4, 8, 16, lalu 30 detik, sampai tersambung atau sesi dihentikan. Webcam yang tercabut dicoba 3 kali. Sesi dan hitungan tetap berlanjut, dan statusnya tampil di halaman Cam serta log terminal.

### Pemutaran berkas

Berkas diputar sesuai waktu aslinya. Jam putar mulai dihitung setelah frame pertama selesai diproses, sehingga waktu muat awal tidak membuat frame dilewati. Bila pemrosesan macet lebih dari 3 detik, jam putar disesuaikan ulang. Tracker juga dipanaskan saat web dimulai.

### Menggambar zona

1. Di halaman Cam, pilih sumber (webcam, CCTV, atau berkas). Zona berlaku per sumber.
2. Klik **Tambah zona**. Gambar dari sumber muncul di panel kiri.
3. Klik sudut-sudut area (minimal 3 titik). Isi nama, pilih jenis, lalu klik **Simpan zona**. Ulangi untuk zona lain, lalu klik **Selesai**.
4. Zona yang diubah saat sesi berjalan langsung dipakai tanpa perlu memulai ulang.

### Penilaian petugas

Setiap peringatan di halaman Riwayat bisa dinilai **Benar** atau **Alarm palsu**. Dashboard menghitung **precision lapangan** = benar / (benar + alarm palsu). Angka ini mengukur kinerja nyata di lokasi pemasangan dan menjadi dasar kalibrasi ambang.

Hasil evaluasi pada 8 video test CAVIAR: mAP50 deteksi orang 0,916; F1 safe 0,756; F1 suspicious 0,800.

## Menjalankan

1. Buka **Laragon**, klik **Start All**, dan pastikan MySQL berjalan.
2. Klik dua kali `Buka web deteksi.cmd` di folder proyek. Skrip memasang paket yang belum ada (Flask, PyMySQL, waitress), lalu membuka `http://127.0.0.1:5000`.
3. Web membuat database `deteksi_perilaku` beserta tabelnya secara otomatis. Lihat isinya di phpMyAdmin (Laragon > Database, atau `http://localhost/phpmyadmin`).
4. Saat pertama kali dibuka, buat akun admin (nama lengkap, nama pengguna, sandi minimal 8 karakter berisi huruf dan angka).

**Lupa sandi:** di komputer server, jalankan `.\.venv\Scripts\python.exe web\run.py --atur-ulang-sandi NAMA`. Perintah ini hanya bisa dijalankan dari terminal komputer itu, bukan dari jaringan.

**Server:** bila paket `waitress` terpasang, web memakai server produksi waitress (32 thread, batas 200 koneksi, koneksi diam diputus setelah 60 detik). Tanpa waitress, server pengembangan Flask dipakai dan log menampilkan anjuran memasangnya.

Manual (PowerShell, dari folder proyek):

```powershell
.\.venv\Scripts\python.exe -m pip install -r web\requirements.txt
.\.venv\Scripts\python.exe web\run.py --buka
```

Video contoh tersedia di `web/storage/video/`: `contoh_1_koridor_berhenti.mp4` (29 detik) dan `contoh_2_koridor_menunggu.mp4` (55 detik), dari CAVIAR (CC BY-SA). Pilih **Berkas** di halaman Cam. Video lain bisa diunggah lewat form **Unggah video baru** (mp4, avi, mov, mkv, mpg; maksimal 500 MB).

Berkas video diputar sesuai waktu aslinya: bila komputer lebih lambat dari video, frame yang tertinggal dilewati (jumlahnya tampil di "Frame dilewati"). Waktu aturan memakai detik di dalam video. Centang **Analisis setiap frame** untuk memproses semua frame; tanpa GPU video akan berjalan lebih lambat dari aslinya.

Webcam: model dimuat di latar saat server menyala, dan webcam di Windows dibuka lewat DirectShow (backend bawaan Windows bisa butuh 10 sampai 30 detik). Jika Mulai ditekan sebelum model siap, halaman Cam menampilkan tahap persiapan.

Server hanya mendengarkan `127.0.0.1`. Opsi `--host 0.0.0.0` membuka akses dari jaringan lokal (misalnya dari ponsel petugas). Semua halaman tetap wajib masuk. Untuk akses dari luar jaringan, pasang HTTPS di depan web (misalnya reverse proxy) dan setel `SAD_COOKIE_AMAN=1`.

## Log terminal

Saat `web\run.py` berjalan, terminal menampilkan log proses dan menyimpannya ke `web/storage/log/web.log` (berputar, 5 berkas x 2 MB). Contoh:

```
2026-11-01 17:31:45 | INFO    | database | Terhubung ke MySQL ... database 'deteksi_perilaku'
2026-11-01 17:31:51 | INFO    | mesin    | Model siap dalam 2.3 detik (total pemanasan 5.5 detik). Kamera bisa dimulai.
2026-11-01 17:31:59 | INFO    | kamera   | Sesi 3 dimulai | berkas: contoh_1_koridor_berhenti.mp4 | mode putar sesuai waktu asli | 1 zona (Depan pintu:sensitif)
2026-11-01 17:32:00 | INFO    | mesin    | Sesi 3: gambar pertama tampil 0.6 detik setelah Mulai
2026-11-01 17:32:04 | INFO    | mesin    | Sesi 3 | detik video    5.0 |    26 frame diproses |  5.2 fps | dilewati 99 | orang 2 (suspicious 0) | peringatan 0
2026-11-01 17:32:20 | WARNING | mesin    | PERINGATAN sesi 3 | detik 20.6 | ID 1 | sensitif | zona Depan pintu | Berada 20 detik di zona sensitif 'Depan pintu'
2026-11-01 17:32:28 | INFO    | mesin    | Sesi 3 SELESAI | 29.2 detik | 156 frame diproses (5.3 fps rata-rata) | 569 dilewati | 1 peringatan
```

Pilihan:

| Opsi | Fungsi |
| --- | --- |
| `--log-level DEBUG` | Tambah rincian per orang (ID, kelas, durasi, zona, alasan) di setiap ringkasan progres |
| `--log-progres 2` | Ringkasan progres tiap 2 detik (bawaan 5; 0 = mati) |
| `--tanpa-log-http` | Sembunyikan log permintaan halaman |

Permintaan rutin (status tiap detik, stream video, berkas statis) tidak ditampilkan agar log tetap terbaca.

## Konfigurasi (variabel lingkungan, opsional)

| Variabel | Bawaan |
| --- | --- |
| `SAD_MODEL` | `web/models/best.pt` (bila tidak ada: `hasil_latih/detect/train-4/weights/best.pt`) |
| `SAD_MODEL_PARKIR` | `web/models/motor.pt` (mode parkiran; bila tidak ada, mode parkiran tidak bisa dipilih) |
| `SAD_PARKIR_DEKAT_S` | `15` (ambang aturan "dekat motor orang lain", detik) |
| `SAD_TRACKER` | `web/trackers/botsort_reid_b125.yaml` |
| `SAD_CONFIDENCE` | `0.15` |
| `SAD_IMAGE_SIZE` | `640` (320 lebih cepat di CPU) |
| `SAD_SAMBUNG_DETIK` | `2.0` (0 = tanpa penyambungan ID) |
| `SAD_DB_HOST`, `SAD_DB_PORT` | `127.0.0.1`, `3306` (MySQL Laragon) |
| `SAD_DB_USER`, `SAD_DB_PASSWORD` | `root`, kosong (bawaan Laragon) |
| `SAD_DB_NAME` | `deteksi_perilaku` |
| `SAD_STORAGE` | `web/storage` |
| `SAD_VIDEO_DIR` | `web/storage/video` |
| `SAD_SECRET_KEY` | kosong: kunci session dibuat sekali dan disimpan di `web/storage/.kunci_session` (jangan dibagikan) |
| `SAD_COOKIE_AMAN` | `0` (setel `1` bila web dibuka lewat HTTPS) |

Contoh memakai model hasil training baru: `$env:SAD_MODEL="hasil_latih\detect\nama_hasil\weights\best.pt"` lalu jalankan `web\run.py`.

## Arsitektur multitier

```
web/
├── run.py                       titik masuk
├── config.py                    konfigurasi
├── requirements.txt             ultralytics, lap, flask, pymysql
├── database/deteksi_perilaku.sql skema untuk impor manual di phpMyAdmin (opsional)
├── models/best.pt               salinan detektor orang train-4
├── trackers/                    konfigurasi BoT-SORT + ReID
├── app/
│   ├── __init__.py              composition root: merakit ketiga lapisan
│   ├── presentation/            LAPISAN 1: PRESENTASI
│   │   ├── routes/              blueprint Flask (dashboard, kamera, riwayat, api)
│   │   ├── templates/           Jinja: base, dashboard, kamera, riwayat
│   │   ├── static/              style.css, app.js, kamera.js
│   │   └── filters.py           format tampilan (waktu, durasi, alasan)
│   ├── business/                LAPISAN 2: LOGIKA BISNIS
│   │   ├── services/            kamera_service, riwayat_service, dashboard_service
│   │   ├── services/            zona_service (zona per sumber)
│   │   └── detection/           engine.py (thread deteksi), behavior.py (aturan perilaku), parking.py (aturan parkiran), zones.py (zona dan jam aktif)
│   └── data/                    LAPISAN 3: AKSES DATA
│       ├── database.py          koneksi MySQL, buat database dan tabel otomatis
│       ├── repositories/        sesi_repository, peringatan_repository, zona_repository, sumber_repository
│       ├── snapshot_storage.py  berkas snapshot
│       └── video_storage.py     video contoh dan unggahan
├── storage/                     snapshot/ dan video/
└── tests/                       test_arsitektur.py (aturan lapisan), test_aturan_zona.py (aturan per zona),
                                 test_parkiran.py (aturan parkiran dan jam aktif zona)
```

Aturan ketergantungan: presentasi hanya memanggil service; service memegang logika; mesin deteksi melaporkan hasil lewat callback dan tidak mengenal database; hanya lapisan data yang berisi SQL dan akses berkas. Uji otomatis:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s web\tests
```

## Basis data (MySQL, lihat di phpMyAdmin)

Database `deteksi_perilaku`:

| Tabel | Kolom utama |
| --- | --- |
| `sesi` | id, jenis (webcam/stream/berkas), sumber (sandi RTSP disamarkan), mulai, selesai, frame, status, mode (umum/parkir) |
| `peringatan` | id, sesi_id, waktu, detik dalam sesi, id_orang, alasan, kategori, zona, snapshot, kotak x1 y1 x2 y2, penilaian, dinilai_pada |
| `zona` | id, sumber, nama, jenis (santai/sensitif/terlarang), titik (JSON, koordinat 0 sampai 1), jam_mulai, jam_selesai (kosong = selalu aktif), dibuat |
| `sumber_mode` | sumber, mode pilihan (otomatis/umum/parkir), hasil_otomatis terakhir, diubah |
| `pengguna` | id, nama_pengguna, nama, hash_sandi (PBKDF2-SHA256), dibuat, masuk_terakhir, gagal, terkunci_sampai, versi_sesi |

Kolom baru ditambahkan otomatis ke tabel lama saat web dijalankan; data lama tetap ada.

## Keamanan

| Ancaman | Perlindungan |
| --- | --- |
| Akses tanpa izin | Semua halaman, API, tayangan, dan snapshot wajib masuk. Session cookie bertanda tangan, `HttpOnly`, `SameSite=Lax`; keluar otomatis setelah 8 jam tanpa aktivitas; "Tetap masuk" maksimal 30 hari. Session lama keluar saat sandi diganti |
| Tebak sandi | Hash PBKDF2-SHA256 600.000 putaran. 5 kali salah: akun dikunci 15 menit. Maksimal 10 percobaan masuk per 10 menit per IP. Pesan gagal sama untuk nama dan sandi salah |
| Banjir permintaan (DoS) | Maksimal 600 permintaan per menit per IP, 20 unggahan per jam per IP, 4 tayangan video bersamaan per IP; waitress membatasi thread, koneksi, dan waktu koneksi diam. Serangan DDoS skala jaringan tetap harus ditahan di router atau firewall |
| SQL injection | Semua query memakai parameter (`%s`); nilai dari pengguna tidak pernah digabung ke teks SQL. Tanggal, sesi, halaman, dan penilaian divalidasi dahulu |
| CSRF dan situs lain | Token CSRF wajib di setiap POST/DELETE (kolom formulir atau header `X-CSRF-Token`), ditambah pemeriksaan Origin/Referer |
| Bot dan skrip | Kolom jebakan tersembunyi di formulir masuk dan pengaturan awal; pembatas per IP; `robots.txt` dan `X-Robots-Tag: noindex` |
| XSS dan clickjacking | Template meng-escape semua isi; Content-Security-Policy dengan nonce (hanya skrip dari web ini), `X-Frame-Options: DENY`, `nosniff`, `Referrer-Policy`, `Permissions-Policy` |
| Berkas berbahaya | Unggahan diperiksa ekstensi, ukuran, dan isinya (harus bisa dibaca sebagai video); nama berkas dibersihkan; snapshot dan video hanya dari foldernya sendiri (path traversal ditolak) |
| Pengalihan ke situs lain | Tujuan setelah masuk hanya boleh jalur lokal |
| Kebocoran data | Sandi RTSP tidak disimpan dan tidak ditampilkan; halaman tidak di-cache peramban |

Uji otomatis keamanan ada di `tests/test_keamanan.py`.

## Batasan

- Satu sumber kamera aktif dalam satu waktu.
- Ambang 20 detik dan aturan mondar-mandir berasal dari literatur loitering; kalibrasi dengan precision lapangan di lokasi Anda.
- Semua akun memiliki hak yang sama (belum ada peran admin dan petugas terpisah). Akun tambahan belum bisa dibuat dari web.
- Model dilatih pada video CAVIAR (lobi dan koridor). Kamera kos memerlukan data dan kalibrasi ambang sendiri.
- Mode parkiran baru diuji pada dua klip berita dan lintasan buatan, belum pada rekaman parkiran panjang. Ambang 15 detik dan jarak adaptif berasal dari Adeel dkk. 2026 (mobil, bukan motor); aturan lain adalah rancangan penelitian ini.
- Pencocokan penampilan memakai warna pakaian, bukan model ReID terlatih. Pakaian yang mirip (seragam, jaket ojek daring) bisa tertukar; pemilik yang berganti jaket tidak dikenali.
- Motor yang sudah terparkir sebelum kamera menyala tidak punya pemilik yang diketahui. Pencuri yang langsung membawa motor seperti itu dalam kurang dari 15 detik tanpa jongkok belum tertangkap.
- Kamera yang terlalu dekat (motor memenuhi gambar dan terpotong) membuat motor dan orang sering tidak terdeteksi. Pasang kamera tinggi dengan sudut lebar.
- Rekaman penghuni memerlukan izin pemilik dan pemberitahuan kepada penghuni (UU No. 27 Tahun 2022 tentang Pelindungan Data Pribadi).

Data latih: CAVIAR, University of Edinburgh, Creative Commons BY-SA (atribusi EC Funded CAVIAR project/IST 2001 37540). Ultralytics: lisensi AGPL-3.0 atau enterprise.
