"""Presentation tier: filter Jinja untuk format tampilan."""
import re

KATEGORI = {"terlarang": "Zona terlarang", "sensitif": "Zona sensitif", "mondar-mandir": "Mondar-mandir",
            "diam": "Diam terlalu lama", "dekat_motor": "Dekat motor orang lain",
            "pindah_motor": "Berpindah antarmotor", "motor_didorong": "Motor didorong",
            "motor_dibawa": "Motor dibawa orang lain", "jongkok_motor": "Jongkok di dekat motor",
            "hilang_dekat_motor": "Hilang di dekat motor"}


def format_waktu(value):
    if not value:
        return "-"
    if hasattr(value, "strftime"):  # DATETIME dari MySQL
        return value.strftime("%Y-%m-%d %H:%M:%S")
    return str(value).replace("T", " ")


def format_jam(value):
    """Jam saja (HH:MM:SS) untuk daftar yang sudah dikelompokkan per tanggal."""
    teks = format_waktu(value)
    return teks[11:19] if len(teks) >= 19 else teks


def format_alasan(text):
    """Ubah alasan teknis dari mesin deteksi menjadi kalimat formal."""
    if not text:
        return "-"
    m = re.match(r"tinggal>=(\d+)s di area terbatas \(sebaran ([\d.]+)xH\)", text)
    if m:
        return f"Berada di area terbatas selama lebih dari {m[1]} detik (sebaran gerak {m[2].replace('.', ',')}× tinggi badan)"
    m = re.match(r"mondar-mandir \(jalur/bersih ([\d.]+)\)", text)
    if m:
        return f"Bergerak mondar-mandir (rasio lintasan {m[1].replace('.', ',')})"
    return text


def format_kategori(value):
    return KATEGORI.get(value, value or "-")


def format_durasi(seconds):
    seconds = int(seconds or 0)
    return f"{seconds // 3600:02d}:{seconds % 3600 // 60:02d}:{seconds % 60:02d}"


def register(app):
    app.add_template_filter(format_waktu, "waktu")
    app.add_template_filter(format_jam, "jam")
    app.add_template_filter(format_alasan, "alasan")
    app.add_template_filter(format_kategori, "kategori")
    app.add_template_filter(format_durasi, "durasi")
