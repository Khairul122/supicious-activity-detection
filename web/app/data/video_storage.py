"""Data tier: penyimpanan berkas video (contoh dan unggahan)."""
import re
from pathlib import Path

VIDEO_EXT = {".mp4", ".mpg", ".mpeg", ".avi", ".mov", ".mkv"}


class VideoStorage:
    def __init__(self, folder):
        self.folder = Path(folder)
        self.folder.mkdir(parents=True, exist_ok=True)

    def list(self):
        return sorted(p.name for p in self.folder.iterdir() if p.is_file() and p.suffix.lower() in VIDEO_EXT)

    def path(self, name):
        """Jalur aman di dalam folder video, atau None."""
        candidate = (self.folder / name).resolve()
        if candidate.parent != self.folder.resolve() or not candidate.is_file():
            return None
        return candidate

    def remove(self, name):
        path = self.path(name)
        if path is not None:
            path.unlink()

    def save(self, stream, original_name):
        """Simpan berkas unggahan dengan nama aman dan unik; kembalikan nama berkas."""
        stem, ext = Path(original_name).stem, Path(original_name).suffix.lower()
        stem = re.sub(r"[^A-Za-z0-9_-]+", "_", stem).strip("_")[:60] or "video"
        name, n = f"{stem}{ext}", 1
        while (self.folder / name).exists():
            n += 1
            name = f"{stem}_{n}{ext}"
        target = self.folder / name
        stream.save(str(target))
        return name
