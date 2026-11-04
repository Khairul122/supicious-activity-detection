# Third-Party Notices

The AI CCTV Suspicious Activity Detection system uses the components below. Each one stays under its own license. The commercial license in `LICENSE.md` does not change these licenses.

## Software

| Component | Version | License | Source |
| --- | --- | --- | --- |
| Ultralytics (YOLO, BoT-SORT tracker) | 8.4.194 | AGPL-3.0, or Ultralytics Enterprise License | https://github.com/ultralytics/ultralytics |
| lap | 0.5.13 | BSD-2-Clause | https://github.com/gatagat/lap |
| Flask | 3.1.3 | BSD-3-Clause | https://github.com/pallets/flask |
| PyMySQL | 1.1.2 | MIT | https://github.com/PyMySQL/PyMySQL |
| waitress | 3.0.2 | Zope Public License 2.1 | https://github.com/Pylons/waitress |
| OpenCV (installed with Ultralytics) | per installed version | Apache-2.0 | https://github.com/opencv/opencv |
| PyTorch (installed with Ultralytics) | per installed version | BSD-3-Clause | https://github.com/pytorch/pytorch |
| NumPy (installed with Ultralytics) | per installed version | BSD-3-Clause | https://github.com/numpy/numpy |

Packages installed as dependencies of the packages above keep their own licenses. Run `pip-licenses` in the virtual environment for a full list.

### Important: Ultralytics and AGPL-3.0

Ultralytics publishes its library under AGPL-3.0. Ultralytics states that this license also covers models trained with its tools. AGPL-3.0 requires that anyone who distributes the software, or lets users interact with it over a network, makes the complete corresponding source code available under AGPL-3.0.

For closed-source commercial use, Ultralytics sells an Ultralytics Enterprise License: https://www.ultralytics.com/license

Before Production Use, confirm which option applies to your copy. The Order for your license states it (see Section 6.2 of `LICENSE.md`).

## Fonts and icons

| Asset | License | Source |
| --- | --- | --- |
| Plus Jakarta Sans | SIL Open Font License 1.1 (full text in `web/app/presentation/static/fonts/OFL-PlusJakartaSans.txt`) | https://github.com/tokotype/PlusJakartaSans |
| Lucide icons | ISC License | https://lucide.dev |

## Training data for the model weights

| Dataset | Use | License | Attribution |
| --- | --- | --- | --- |
| COCO 2017 | Person, motorcycle, and bicycle images for training and validation | Annotations CC BY 4.0. Images belong to their Flickr owners under the licenses listed in the COCO annotation files. | Lin et al., "Microsoft COCO: Common Objects in Context", ECCV 2014. https://cocodataset.org |
| Open Images V7 | Person and motorcycle images for training and validation | Annotations CC BY 4.0. Images listed as CC BY 2.0. | Kuznetsova et al., "The Open Images Dataset V4", IJCV 2020. https://storage.googleapis.com/openimages/web/index.html |
| CAVIAR | Corridor footage for person training, validation, and behavior tests | CC BY-SA | EC Funded CAVIAR project/IST 2001 37540. https://groups.inf.ed.ac.uk/vision/DATASETS/CAVIAR/CAVIARDATA1/ |

The sample videos `contoh_1_koridor_berhenti.mp4` and `contoh_2_koridor_menunggu.mp4` come from CAVIAR (clips OneStopNoEnter1cor and OneShopOneWait1cor) and are shared under CC BY-SA with the attribution above.

## Methods

- Rule "near another person's motorbike": Adeel et al. (2026).
- Synthetic occlusion augmentation: Ghiasi et al., "Simple Copy-Paste is a Strong Data Augmentation Method for Instance Segmentation", CVPR 2021.
