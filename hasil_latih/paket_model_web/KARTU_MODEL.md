# Kartu model web deteksi perilaku

Tanggal: 2026-11-03 | Ultralytics 8.4.194 | YOLO26s, 640 px, 80 epoch maks

| Berkas | Kelas | Mode web | Keputusan |
| --- | --- | --- | --- |
| motor.pt | person, motorcycle | parkiran | LAYAK PASANG |
| best.pt | person | umum | LAYAK PASANG |

## Data latih

| Sumber | Jumlah | Lisensi |
| --- | --- | --- |
| COCO 2017 (train2017/val2017) | latih {'motorcycle': 3000, 'bicycle': 500, 'person': 3000}, validasi {'motorcycle': 200, 'person': 400} | Anotasi CC BY 4.0; gambar lisensi Flickr |
| Open Images V7 (test/validation) | latih {'Motorcycle': 1500, 'Person': 3000}, validasi {'Motorcycle': 300, 'Person': 500} | Anotasi CC BY 4.0; gambar CC BY 2.0 |
| dataset_yolo_person_v2 (CAVIAR) | 96 gambar validasi + data latih | CC BY-SA, EC Funded CAVIAR project/IST 2001 37540 |

Augmentasi: oklusi sintetis copy-paste 30% (Ghiasi dkk., CVPR 2021), simulasi malam 25%, simulasi CCTV 20%, ditambah augmentasi Ultralytics.

## Evaluasi

| model | data | kelas | precision | recall | F1 | mAP50 |
| --- | --- | --- | --- | --- | --- | --- |
| A-lama | validasi | person | 0.837 | 0.6226 | 0.7141 | 0.7293 |
| A-lama | validasi | motorcycle | 0.6725 | 0.7295 | 0.6998 | 0.7438 |
| A-lama | val_oklusi | person | 0.899 | 0.4503 | 0.6 | 0.6733 |
| A-lama | val_oklusi | motorcycle | 0.5971 | 0.9111 | 0.7214 | 0.7294 |
| A-lama | val_caviar | person | 0.9603 | 0.9343 | 0.9471 | 0.9712 |
| A-lama | malam (simulasi) | person | 0.8271 | 0.4679 | 0.5977 | 0.5985 |
| A-lama | malam (simulasi) | motorcycle | 0.5775 | 0.6623 | 0.617 | 0.6463 |
| A-lama | cctv (simulasi) | person | 0.844 | 0.5276 | 0.6493 | 0.649 |
| A-lama | cctv (simulasi) | motorcycle | 0.6371 | 0.6583 | 0.6475 | 0.6791 |
| A-baru | validasi | person | 0.8537 | 0.6866 | 0.761 | 0.7875 |
| A-baru | validasi | motorcycle | 0.8695 | 0.7108 | 0.7822 | 0.8119 |
| A-baru | val_oklusi | person | 0.8423 | 0.6566 | 0.738 | 0.7555 |
| A-baru | val_oklusi | motorcycle | 0.7774 | 0.9333 | 0.8483 | 0.9122 |
| A-baru | val_caviar | person | 0.9741 | 0.9096 | 0.9407 | 0.9632 |
| A-baru | malam (simulasi) | person | 0.7924 | 0.5897 | 0.6762 | 0.6767 |
| A-baru | malam (simulasi) | motorcycle | 0.8403 | 0.6676 | 0.744 | 0.7446 |
| A-baru | cctv (simulasi) | person | 0.8194 | 0.6198 | 0.7057 | 0.715 |
| A-baru | cctv (simulasi) | motorcycle | 0.8185 | 0.6623 | 0.7322 | 0.7587 |
| B-lama | validasi | person | 0.3383 | 0.178 | 0.2333 | 0.1447 |
| B-lama | val_oklusi | person | 0.2155 | 0.1265 | 0.1594 | 0.0632 |
| B-lama | val_caviar | person | 0.9801 | 0.8858 | 0.9306 | 0.9689 |
| B-lama | malam (simulasi) | person | 0.2964 | 0.1231 | 0.174 | 0.1009 |
| B-lama | cctv (simulasi) | person | 0.3012 | 0.1844 | 0.2288 | 0.1468 |
| B-baru | validasi | person | 0.8273 | 0.6735 | 0.7425 | 0.7651 |
| B-baru | val_oklusi | person | 0.8169 | 0.644 | 0.7202 | 0.7425 |
| B-baru | val_caviar | person | 0.9659 | 0.8812 | 0.9216 | 0.9461 |
| B-baru | malam (simulasi) | person | 0.7484 | 0.5273 | 0.6187 | 0.6091 |
| B-baru | cctv (simulasi) | person | 0.7915 | 0.5696 | 0.6625 | 0.6673 |

## Uji video

| video | model | frame berisi orang | frame berisi motor |
| --- | --- | --- | --- |
| 1000620467.mp4 | A-lama | 91% | 88% |
| 1000620467.mp4 | A-baru | 90% | 75% |
| 1000620467.mp4 | B-lama | 16% | - |
| 1000620467.mp4 | B-baru | 83% | - |

## Batasan

- Data parkiran dan toko dari lokasi pelanggan belum ada; kalibrasi ambang memakai penilaian petugas di web.
- Simulasi malam bukan rekaman inframerah asli.
- Lisensi Ultralytics (AGPL-3.0 atau Enterprise) berlaku untuk produk yang dijual.
