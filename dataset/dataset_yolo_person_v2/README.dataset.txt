dataset_yolo_person_v2 - deteksi orang satu kelas (format YOLO, susunan ekspor Roboflow)

Perbaikan dari dataset_yolo_person (2 November 2026):

1. Orang tanpa label pada split test (video OneShopOneWait1cor).
   Orang yang berdiri di ujung koridor tidak dilabeli pada 51 dari 53 gambar. Ditambahkan
   66 kotak dari deteksi YOLO26s COCO (confidence >= 0,3, tidak bertumpuk dengan label lama),
   lalu ditinjau secara visual satu per satu.
2. Augmentasi offline dengan rotasi/skala (affine) dihapus: 174 gambar. Tepi gambar hasil
   rotasi diisi pantulan cermin sehingga muncul bagian ruangan palsu. Ultralytics sudah
   melakukan augmentasi saat pelatihan, jadi salinan offline ini tidak diperlukan.
   Augmentasi flip dan warna (86 gambar) tetap dipakai; labelnya sudah diperiksa cocok
   dengan gambar asal (selisih maksimal 1 piksel).
3. Kotak tipis di tepi gambar dihapus: 13 kotak (tinggi < 20 px atau lebar < 8 px yang
   menempel tepi, misalnya ujung rambut orang yang baru masuk gambar).

Jumlah:
  train: 216 gambar, 1163 kotak (130 gambar asli + 86 augmentasi flip/warna)
  valid:  43 gambar,   43 kotak
  test :  53 gambar,  246 kotak

Kolom baru di manifest: kotak_person (jumlah kotak setelah perbaikan) dan perubahan_v2.

Batasan yang tetap ada:
  - Hanya 5 video sumber (3 latih, 1 validasi, 1 uji). Split valid berisi satu orang per gambar
    dari satu video, sehingga nilai validasinya tidak mewakili kondisi nyata.
  - Label lain berasal dari anotasi CAVIAR dan belum ditinjau ulang satu per satu.
  Notebook *_v2 menggabungkan dataset ini dengan COCO dan Open Images untuk menutup batasan ini.

Kolom kelas_gambar dan alasan pada manifest berasal dari dataset dua kelas dan hanya
dipakai sebagai acuan evaluasi perilaku, bukan label detektor.
Sumber: CAVIAR, University of Edinburgh, Creative Commons BY-SA.
Atribusi: EC Funded CAVIAR project/IST 2001 37540.
