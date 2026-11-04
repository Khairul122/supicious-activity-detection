"""Data tier: penyimpanan berkas snapshot peringatan."""
from pathlib import Path

import cv2


class SnapshotStorage:
    def __init__(self, folder):
        self.folder = Path(folder)
        self.folder.mkdir(parents=True, exist_ok=True)

    def save(self, name, image):
        cv2.imwrite(str(self.folder / name), image, [cv2.IMWRITE_JPEG_QUALITY, 90])
        return name

    def path(self, name):
        """Kembalikan jalur aman di dalam folder snapshot, atau None."""
        candidate = (self.folder / name).resolve()
        if candidate.parent != self.folder.resolve() or not candidate.is_file():
            return None
        return candidate
