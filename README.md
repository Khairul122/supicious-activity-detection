# Deteksi perilaku mencurigakan pada CCTV

Web pemantauan CCTV yang memberi peringatan saat ada perilaku mencurigakan, termasuk aturan khusus parkiran motor.

## Struktur folder

```
supicious-activity-detection/
├── web/                      aplikasi web Flask (panduan lengkap: web/README.md)
│   ├── app/                  kode: presentation, business, data
│   ├── models/               model yang dipakai web: best.pt (umum), motor.pt (parkiran), cadangan *_lama.pt
│   ├── storage/              video, snapshot peringatan, log, kunci session (tidak dibagikan)
│   ├── tests/                uji otomatis (python -m unittest discover -s web/tests)
│   ├── database/             skema SQL
│   └── run.py                menjalankan web
├── notebook/
│   ├── Latih_Semua_Model.ipynb   notebook Colab untuk melatih semua model web
│   └── arsip/                notebook lama dan salinan percobaan (tes/)
├── dataset/
│   ├── dataset_yolo_person_v2/   dataset orang CAVIAR yang labelnya sudah diperbaiki
│   └── arsip/dataset_yolo_person/  versi lama
├── hasil_latih/
│   ├── detect/               hasil training YOLO lama dari Colab
│   └── paket_model_web/      paket hasil Latih_Semua_Model: motor.pt, best.pt, evaluasi, KARTU_MODEL.md
├── dokumen/                  presentasi dan logo sumber
├── arsip/                    cadangan tampilan web lama dan paket pemasangan (boleh dihapus)
├── .venv/                    lingkungan Python
└── Buka web deteksi.cmd      klik dua kali untuk menjalankan web
```

## Menjalankan web

1. Buka Laragon, klik **Start All** (MySQL harus aktif).
2. Klik dua kali `Buka web deteksi.cmd`. Web terbuka di `http://127.0.0.1:5000`.
3. Pertama kali dibuka, buat akun admin. Lupa sandi: `.\.venv\Scripts\python.exe web\run.py --atur-ulang-sandi NAMA`.

## Melatih ulang model

1. Unggah ke `MyDrive/supicious-activity-detection/`: folder `dataset/dataset_yolo_person_v2` (sebagai `dataset_yolo_person_v2`), model lama pembanding (`detect/motor-1/weights/best.pt` dan `detect/train-4/weights/best.pt`), dan video uji ke `video_uji/`.
2. Buka `notebook/Latih_Semua_Model.ipynb` di Colab, lalu **Runtime > Run all**. Data dan checkpoint tersimpan di Drive, jadi bila terputus cukup Run all lagi.
3. Unduh `model_web.zip`, simpan isinya di `hasil_latih/paket_model_web/`. Pasang model berstatus LAYAK PASANG ke `web/models/`, simpan model lama dengan nama lain.

Label `suspicious` adalah peringatan untuk ditinjau petugas, bukan bukti niat atau tindak pidana.
