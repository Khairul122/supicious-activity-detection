"""Video portofolio gaya kartu terang (versi 2) untuk penonton awam.

Sumber: naskah.json (satu kalimat = satu ketukan). Durasi kalimat dibaca dari
assets/suara/durasi.json hasil VoiceStudio; bila belum ada, durasi diperkirakan.
Jalankan ulang setiap kali suara atau musik berubah:
  python3 bangun.py        versi Indonesia (naskah.json, assets/suara)
  python3 bangun.py en     versi Inggris (naskah_en.json, assets/suara_en)
"""
import json
import subprocess
import sys
from pathlib import Path

DIR = Path(__file__).resolve().parent
BAHASA = sys.argv[1] if len(sys.argv) > 1 else "id"
NASKAH = json.load(open(DIR / ("naskah_en.json" if BAHASA == "en" else "naskah.json"), encoding="utf-8"))
SUARA = "assets/suara_en" if BAHASA == "en" else "assets/suara"
TERJEMAH = {
    "Rekaman CCTV": "CCTV recording", "Kejadian": "It happens", "Tersimpan": "Saved", "Ketahuan besok": "Found next day",
    "Pelaku sudah pergi": "The thief is gone", "Orang": "People", "Motor": "Motorbikes", "Gerak-gerik": "Behavior",
    "Mengenali tempat": "Reading the scene", "Parkiran terdeteksi": "Parking lot detected", "Koridor": "Hallway",
    "Toko, rumah": "Shops, homes", "Parkiran": "Parking", "Area motor": "Motorbike area",
    "Jongkok lama di dekat motor": "Crouching by a bike too long", "Motor didorong pergi": "Bike pushed away",
    "Hilang di balik motor": "Hiding behind a bike", "Ada yang mencurigakan!": "Something looks wrong!",
    "Hilang di dekat motor": "Vanished near a motorbike", "Foto tersimpan otomatis": "Photo saved automatically",
    "Aman, tidak ditandai": "Safe, not flagged", "Benar": "Real", "Alarm palsu": "False alarm",
    "Area terlarang": "Restricted area", "Dijaga jam 22.00 sampai 06.00": "Guarded 10 PM to 6 AM",
    "uji serangan lolos": "attack tests passed", "Login aman": "Secure login", "Siap pakai": "Ready to use",
    "Langsung dipasang": "Install and run", "Pesan khusus": "Custom build", "Sesuai kebutuhanmu": "Built for your needs",
}


def terjemah(html):
    if BAHASA != "en":
        return html
    for a in sorted(TERJEMAH, key=len, reverse=True):
        html = html.replace(f">{a}<", f">{TERJEMAH[a]}<")
    return html
IKON = json.load(open(DIR / "ikon.json"))
IKON["bookmark"] = '<path d="m19 21-7-4-7 4V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v16z"/>'
IKON["message-circle"] = '<path d="M7.9 20A9 9 0 1 0 4 16.1L2 22Z"/>'
IKON["shopping-bag"] = '<path d="M6 2 3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4Z"/><path d="M3 6h18"/><path d="M16 10a4 4 0 0 1-8 0"/>'
IKON["wrench"] = '<path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/>'
W, H = 1080, 1920
AWAL, JEDA, EKOR = 0.6, (0.7 if BAHASA == "en" else 0.5), (2.7 if BAHASA == "en" else 2.2)
NAVY, TEAL, TEAL_TUA = "#10233b", "#1a8aa6", "#177e97"

# ---------------------------------------------------------------- waktu
f_dur = DIR / f"{SUARA}/durasi.json"
dur_asli = json.load(open(f_dur, encoding="utf-8-sig")) if f_dur.exists() else {}
KAL = NASKAH["kalimat"]
t = AWAL
for k in KAL:
    k["dur"] = float(dur_asli.get(k["id"]) or round(len(k["ucapan"]) / 15.5 + 0.3, 2))
    k["mulai"] = round(t, 3)
    t += k["dur"] + JEDA
for i, k in enumerate(KAL):
    k["b_mulai"] = 0.0 if i == 0 else round(k["mulai"] - 0.35, 3)
for i, k in enumerate(KAL):
    akhir = KAL[i + 1]["b_mulai"] if i + 1 < len(KAL) else k["mulai"] + k["dur"] + EKOR
    k["b_dur"] = round(akhir - k["b_mulai"], 3)
    k["t0"] = round(k["mulai"] - k["b_mulai"], 3)      # suara mulai, waktu lokal ketukan
TOTAL = round(KAL[-1]["b_mulai"] + KAL[-1]["b_dur"], 3)


def ikon(nama, ukuran=40, warna="currentColor", lebar=2):
    return (f'<svg class="ik" width="{ukuran}" height="{ukuran}" viewBox="0 0 24 24" fill="none" stroke="{warna}" '
            f'stroke-width="{lebar}" stroke-linecap="round" stroke-linejoin="round">{IKON[nama]}</svg>')


def panjang_audio(f):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(f)],
                         capture_output=True, text=True).stdout.strip()
    return round(float(out) - 0.02, 3)


PUNCAK = {"notification.mp3": .229, "pop.mp3": .12, "click-soft.mp3": .073, "whoosh-short.mp3": .162, "whoosh.mp3": .162,
          "ping.mp3": .324, "sparkle.mp3": .027, "typing.mp3": .457, "key-press.mp3": .076}
SFX = []


def sfx(k, t_lokal, f, vol=0.4):
    """Puncak bunyi jatuh satu frame setelah gambarnya."""
    SFX.append((round(max(0.0, k["b_mulai"] + t_lokal - PUNCAK[f] + 1 / 30), 3), f, vol))


FONT = "".join(
    f'@font-face{{font-family:"Plus Jakarta Sans";font-weight:{w};src:url("assets/fonts/plus-jakarta-sans-latin-{w}-normal.woff2") format("woff2");}}'
    for w in (400, 500, 600, 700, 800))
DASAR = FONT + f"""
#root{{position:absolute;inset:0;overflow:hidden;font-family:"Plus Jakarta Sans",sans-serif;color:{NAVY}}}
.ik{{flex:none;display:block}}
"""

# ---------------------------------------------------------------- kartu
# Setiap fungsi menerima kalimat k (t0 = suara mulai, d = durasi suara, D = durasi ketukan)
# dan mengembalikan (html di dalam kartu, css, js, kartu_polos)

def kartu_rekam(k):
    n, t0, d = k["id"], k["t0"], k["dur"]
    langkah = [("cctv", "Kejadian", "#5b6f86"), ("history", "Tersimpan", "#5b6f86"), ("triangle-alert", "Ketahuan besok", "#d9822b")]
    html = f"""<div class="rk-kepala"><span class="rk-dot" id="k{n}-dot"></span>Rekaman CCTV</div>
      <div class="rk-garis"><div id="k{n}-garis"></div></div>
      {''.join(f'<div class="rk-step" id="k{n}-s{i}" style="left:{90 + i * 240}px"><div class="rk-bul" style="color:{c}">{ikon(ic, 54, c)}</div><div class="rk-lbl">{tx}</div></div>' for i, (ic, tx, c) in enumerate(langkah))}
      <div class="rk-telat" id="k{n}-telat">{ikon("clock", 32, "#b4641c", 2.4)}Pelaku sudah pergi</div>"""
    css = """.rk-kepala{position:absolute;left:44px;top:40px;display:flex;align-items:center;gap:14px;font-size:30px;font-weight:700}
.rk-dot{width:18px;height:18px;border-radius:50%;background:#ef4a4a}
.rk-garis{position:absolute;left:150px;right:150px;top:212px;height:6px;border-radius:3px;background:#e6edf3;overflow:hidden}
.rk-garis div{width:100%;height:100%;background:#9fb3c8;transform-origin:left center}
.rk-step{position:absolute;top:140px;width:120px;text-align:center}
.rk-bul{width:120px;height:120px;border-radius:50%;background:#fff;border:4px solid #e6edf3;display:flex;align-items:center;justify-content:center}
.rk-lbl{position:absolute;left:-60px;right:-60px;top:140px;font-size:30px;font-weight:700;color:#3d5168}
.rk-telat{position:absolute;left:0;right:0;margin:0 auto;width:380px;top:400px;display:flex;justify-content:center;align-items:center;gap:12px;
  background:#fdf0e3;color:#b4641c;font-size:30px;font-weight:800;padding:14px 0;border-radius:999px}"""
    js = f"""    tl.fromTo("#k{n}-dot", {{opacity:1}}, {{opacity:.2, duration:.45, yoyo:true, repeat:7, ease:"none"}}, .4);
    tl.fromTo("#k{n}-s0", {{opacity:0, y:20}}, {{opacity:1, y:0, duration:.4, ease:"back.out(2)"}}, {t0 + .2});
    tl.fromTo("#k{n}-garis", {{scaleX:0}}, {{scaleX:1, duration:{d * .6:.2f}, ease:"none"}}, {t0 + .4});
    tl.fromTo("#k{n}-s1", {{opacity:0, y:20}}, {{opacity:1, y:0, duration:.4, ease:"back.out(2)"}}, {t0 + d * .3:.2f});
    tl.fromTo("#k{n}-s2", {{opacity:0, y:20}}, {{opacity:1, y:0, duration:.4, ease:"back.out(2)"}}, {t0 + d * .55:.2f});
    tl.fromTo("#k{n}-telat", {{opacity:0, scale:.8}}, {{opacity:1, scale:1, duration:.4, ease:"back.out(2)"}}, {t0 + d * .7:.2f});
"""
    sfx(k, t0 + d * .55, "pop.mp3", .3)
    return html, css, js, False


def kartu_logo(k):
    n, t0, d = k["id"], k["t0"], k["dur"]
    chips = [("users", "Orang"), ("motorbike", "Motor"), ("footprints", "Gerak-gerik")]
    html = f"""<div class="lg-cincin" id="k{n}-cin"></div>
      <img class="lg-img" id="k{n}-logo" src="assets/img/logo.png" alt="">
      <div class="lg-chips">{''.join(f'<span class="chip" id="k{n}-c{i}">{ikon(ic, 32, TEAL)}{tx}</span>' for i, (ic, tx) in enumerate(chips))}</div>"""
    css = """.lg-img{position:absolute;left:290px;top:50px;width:200px}
.lg-cincin{position:absolute;left:265px;top:20px;width:250px;height:250px;border-radius:50%;border:4px solid rgba(26,138,166,.5)}
.lg-chips{position:absolute;left:0;right:0;top:350px;display:flex;justify-content:center;gap:16px}"""
    js = f"""    tl.fromTo("#k{n}-logo", {{opacity:0, scale:.6}}, {{opacity:1, scale:1, duration:.6, ease:"back.out(1.8)"}}, .45);
    tl.fromTo("#k{n}-cin", {{opacity:.9, scale:.8}}, {{opacity:0, scale:1.5, duration:1.6, ease:"power2.out"}}, .8);
    tl.fromTo("#k{n} .lg-chips .chip", {{opacity:0, y:24}}, {{opacity:1, y:0, duration:.4, ease:"back.out(2)", stagger:.3}}, {t0 + d * .45:.2f});
"""
    sfx(k, t0 + d * .45 + .02, "pop.mp3", .3)
    return html, css, js, False


def kartu_mode(k):
    n, t0, d = k["id"], k["t0"], k["dur"]
    t_pilih = round(t0 + d * .62, 2)
    html = f"""<div class="md-kepala"><span id="k{n}-h1">{ikon("scan-eye", 34, TEAL)}Mengenali tempat</span>
        <span id="k{n}-h2">{ikon("circle-check", 34, "#1f9d5c")}Parkiran terdeteksi</span></div>
      <div class="md-jalur"><div id="k{n}-bar"></div></div>
      <div class="md-tile" id="k{n}-u" style="left:44px">{ikon("users", 64, "#5b6f86")}<b>Koridor</b><span>Toko, rumah</span></div>
      <div class="md-tile" id="k{n}-p" style="left:406px">{ikon("motorbike", 64, TEAL)}<b>Parkiran</b><span>Area motor</span>
        <div class="md-cek" id="k{n}-cek">{ikon("check", 32, "#fff", 3)}</div></div>"""
    css = """.md-kepala{position:absolute;left:44px;top:40px;height:44px;font-size:32px;font-weight:700}
.md-kepala span{position:absolute;left:0;top:0;display:flex;gap:14px;align-items:center;white-space:nowrap}
.md-jalur{position:absolute;left:44px;right:44px;top:108px;height:14px;border-radius:7px;background:#e6edf3;overflow:hidden}
.md-jalur div{width:100%;height:100%;background:#1a8aa6;transform-origin:left center}
.md-tile{position:absolute;top:170px;width:330px;height:300px;border-radius:30px;border:3px solid #e6edf3;background:#f8fafc;
  display:flex;flex-direction:column;align-items:center;justify-content:center;gap:10px}
.md-tile b{font-size:38px;font-weight:800} .md-tile span{font-size:28px;color:#5b6f86;font-weight:600}
.md-cek{position:absolute;right:-16px;top:-16px;width:60px;height:60px;border-radius:50%;background:#1a8aa6;display:flex;align-items:center;justify-content:center}"""
    js = f"""    tl.fromTo("#k{n}-h2", {{opacity:0}}, {{opacity:0}}, 0);
    tl.fromTo("#k{n}-bar", {{scaleX:0}}, {{scaleX:1, duration:{t_pilih - .5:.2f}, ease:"power1.inOut"}}, .5);
    tl.fromTo("#k{n}-u, #k{n}-p", {{opacity:0, y:30}}, {{opacity:1, y:0, duration:.45, ease:"power3.out", stagger:.15}}, .55);
    tl.to("#k{n}-h1", {{opacity:0, duration:.2}}, {t_pilih});
    tl.to("#k{n}-h2", {{opacity:1, duration:.2}}, {t_pilih + .1:.2f});
    tl.to("#k{n}-u", {{opacity:.45, duration:.3}}, {t_pilih});
    tl.to("#k{n}-p", {{borderColor:"#1a8aa6", backgroundColor:"#e8f6fa", duration:.3}}, {t_pilih});
    tl.fromTo("#k{n}-cek", {{opacity:0, scale:.3}}, {{opacity:1, scale:1, duration:.4, ease:"back.out(2.6)"}}, {t_pilih + .05:.2f});
"""
    sfx(k, t_pilih + .07, "ping.mp3", .3)
    return html, css, js, False


def video_kartu(idv, src, ms, D, tinggi=423):
    return (f'<div class="vd" style="height:{tinggi}px"><video id="{idv}" class="clip" data-start="0" data-duration="{D}" data-media-start="{ms}" '
            f'muted playsinline src="{src}" style="position:absolute;left:0;top:0;width:752px;height:{tinggi}px;object-fit:cover"></video></div>')


def video_jalan(idv, ms, D):
    """Rekaman jalan berpita hitam (1248x576, isi gambar x 88..1160) dipotong pas 752 px."""
    sk = 752 / 1072
    return (f'<div class="vd" style="height:{576 * sk:.0f}px"><video id="{idv}" class="clip" data-start="0" data-duration="{D}" data-media-start="{ms}" '
            f'muted playsinline src="assets/video/lewat.mp4" style="position:absolute;left:{-88 * sk:.1f}px;top:0;width:{1248 * sk:.1f}px;height:{576 * sk:.0f}px;object-fit:fill"></video></div>')


CSS_VIDEO = """.vd{position:absolute;left:14px;top:14px;width:752px;overflow:hidden;border-radius:28px;background:#000}
.bawah{position:absolute;left:0;right:0;top:450px;display:flex;justify-content:center;gap:16px}"""


def kartu_kenal(k):
    n, t0, d, D = k["id"], k["t0"], k["dur"], k["b_dur"]
    html = f"""{video_kartu(f"k{n}-v", "assets/video/curi.mp4", 0.5, D)}
      <div class="bawah"><span class="chip" id="k{n}-c0"><i class="dot" style="background:#2fbf71"></i>Orang</span>
        <span class="chip" id="k{n}-c1"><i class="dot" style="background:#2ea8e8"></i>Motor</span></div>"""
    css = CSS_VIDEO + ".dot{width:18px;height:18px;border-radius:50%;display:block}"
    js = f"""    tl.fromTo("#k{n} .bawah .chip", {{opacity:0, y:20}}, {{opacity:1, y:0, duration:.4, ease:"back.out(2)", stagger:.3}}, {t0 + d * .35:.2f});
"""
    sfx(k, t0 + d * .35 + .02, "pop.mp3", .3)
    return html, css, js, False


def kartu_aturan(k):
    n, t0, d = k["id"], k["t0"], k["dur"]
    rows = [("user", "Jongkok lama di dekat motor"), ("motorbike", "Motor didorong pergi"), ("eye-off", "Hilang di balik motor")]
    html = "".join(
        f'<div class="at-row" id="k{n}-r{i}" style="top:{36 + i * 156}px"><div class="at-ik">{ikon(ic, 44, "#b4641c")}</div>'
        f'<b>{tx}</b><div class="at-bad" id="k{n}-b{i}">{ikon("triangle-alert", 30, "#fff", 2.6)}</div></div>' for i, (ic, tx) in enumerate(rows))
    css = """.at-row{position:absolute;left:36px;right:36px;height:132px;border-radius:26px;background:#f8fafc;border:2px solid #e6edf3;display:flex;align-items:center;gap:24px;padding:0 26px}
.at-row b{font-size:32px;font-weight:700;flex:1}
.at-ik{width:80px;height:80px;border-radius:22px;background:#fdf0e3;display:flex;align-items:center;justify-content:center;flex:none}
.at-bad{width:58px;height:58px;border-radius:50%;background:#ef4a4a;display:flex;align-items:center;justify-content:center;flex:none}"""
    js = f"""    tl.fromTo("#k{n} .at-row", {{opacity:0, x:-40}}, {{opacity:1, x:0, duration:.45, ease:"power3.out", stagger:.3}}, .5);
    tl.fromTo("#k{n} .at-bad", {{opacity:0, scale:.3}}, {{opacity:1, scale:1, duration:.35, ease:"back.out(2.6)", stagger:.35}}, {t0 + d * .6:.2f});
"""
    sfx(k, t0 + d * .6 + .02, "pop.mp3", .3)
    return html, css, js, False


def kartu_alarm(k):
    n, t0, d, D = k["id"], k["t0"], k["dur"], k["b_dur"]
    t_alarm = round(t0 + .5, 2)
    ms = max(0.0, round(18.62 - t_alarm, 2))
    html = f"""{video_kartu(f"k{n}-v", "assets/video/curi.mp4", ms, D)}
      <div class="al-toast" id="k{n}-toast">{ikon("bell", 40, "#fff", 2.4)}<div><b>Ada yang mencurigakan!</b><span>Hilang di dekat motor</span></div></div>
      <div class="bawah"><span class="chip" id="k{n}-c0">{ikon("camera", 32, TEAL)}Foto tersimpan otomatis</span></div>"""
    css = CSS_VIDEO + """.al-toast{position:absolute;left:34px;right:34px;top:34px;display:flex;gap:18px;align-items:center;background:#ef4a4a;color:#fff;
  border-radius:22px;padding:20px 24px;box-shadow:0 16px 34px rgba(150,20,20,.35)}
.al-toast b{display:block;font-size:32px;font-weight:800} .al-toast span{display:block;font-size:28px;font-weight:600;opacity:.92}"""
    js = f"""    tl.fromTo("#k{n}-toast", {{opacity:0, y:-40}}, {{opacity:1, y:0, duration:.45, ease:"back.out(1.7)"}}, {t_alarm});
    tl.fromTo("#k{n}-c0", {{opacity:0, y:20}}, {{opacity:1, y:0, duration:.4, ease:"back.out(2)"}}, {t0 + d * .65:.2f});
"""
    sfx(k, t_alarm + .02, "notification.mp3", .4)
    return html, css, js, False


def kartu_lewat(k):
    n, t0, d, D = k["id"], k["t0"], k["dur"], k["b_dur"]
    html = f"""{video_jalan(f"k{n}-v", 3, D)}
      <div class="bawah" style="top:440px"><span class="chip aman" id="k{n}-c0">{ikon("circle-check", 34, "#fff", 2.4)}Aman, tidak ditandai</span></div>"""
    css = CSS_VIDEO + ".chip.aman{background:#1f9d5c;color:#fff;border-color:#1f9d5c}"
    js = f"""    tl.fromTo("#k{n}-c0", {{opacity:0, scale:.7}}, {{opacity:1, scale:1, duration:.4, ease:"back.out(2.2)"}}, {t0 + d * .55:.2f});
"""
    sfx(k, t0 + d * .55 + .02, "pop.mp3", .3)
    return html, css, js, False


def kartu_nilai(k):
    n, t0, d = k["id"], k["t0"], k["dur"]
    t_tap = round(t0 + d * .62, 2)
    html = f"""<div class="vd" style="height:300px"><img src="assets/img/snap_curi.jpg" alt="" style="position:absolute;left:0;top:-62px;width:752px;height:423px"></div>
      <div class="nl-label">{ikon("triangle-alert", 30, "#c23b3b", 2.4)}Hilang di dekat motor</div>
      <div class="nl-btn" id="k{n}-benar" style="left:44px" data-layout-allow-overlap><span id="k{n}-bt">Benar</span><span class="nl-cek" id="k{n}-bc">{ikon("check", 34, "#fff", 3)}Benar</span></div>
      <div class="nl-btn" style="left:404px"><span>Alarm palsu</span></div>
      <div class="nl-tap" id="k{n}-tap"></div>"""
    css = CSS_VIDEO + """.nl-label{position:absolute;left:44px;top:336px;display:flex;gap:12px;align-items:center;font-size:32px;font-weight:800}
.nl-btn{position:absolute;top:404px;width:332px;height:86px;border-radius:20px;border:3px solid #d5dee8;font-size:32px;font-weight:700;overflow:hidden}
.nl-btn span{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;gap:10px}
.nl-cek{background:#ef4a4a;color:#fff}
.nl-tap{position:absolute;left:165px;top:402px;width:90px;height:90px;border-radius:50%;background:rgba(26,138,166,.35);border:4px solid #1a8aa6}"""
    js = f"""    tl.fromTo("#k{n}-bc", {{opacity:0}}, {{opacity:0}}, 0);
    tl.fromTo("#k{n}-tap", {{opacity:0, scale:1.6}}, {{opacity:1, scale:1, duration:.3, ease:"power2.out"}}, {t_tap - .3:.2f});
    tl.to("#k{n}-tap", {{opacity:0, scale:.6, duration:.25, ease:"power2.in"}}, {t_tap + .05:.2f});
    tl.to("#k{n}-bc", {{opacity:1, duration:.15}}, {t_tap + .02:.2f});
    tl.to("#k{n}-benar", {{borderColor:"#ef4a4a", duration:.15}}, {t_tap + .02:.2f});
"""
    sfx(k, t_tap + .02, "click-soft.mp3", .5)
    return html, css, js, False


def kartu_zona(k):
    n, t0, d = k["id"], k["t0"], k["dur"]
    titik = [(168, 388), (540, 388), (604, 572), (160, 572)]
    poly = " ".join(f"{x},{y}" for x, y in titik)
    kel = sum(((titik[i][0] - titik[i - 1][0]) ** 2 + (titik[i][1] - titik[i - 1][1]) ** 2) ** .5 for i in range(4))
    bul = "".join(f'<circle class="zt" cx="{x}" cy="{y}" r="12" fill="#fff" stroke="#d946ef" stroke-width="6"/>' for x, y in titik)
    t_g = round(t0 + d * .2, 2)
    html = f"""<div class="vd" style="height:405px"><img src="assets/img/jalan.jpg" alt="" style="position:absolute;inset:0;width:752px;height:405px">
        <svg viewBox="0 0 1070 576" width="752" height="405" style="position:absolute;left:0;top:0">
          <polygon id="k{n}-isi" points="{poly}" fill="rgba(217,70,239,.30)"/>
          <polygon id="k{n}-gar" points="{poly}" fill="none" stroke="#d946ef" stroke-width="7" stroke-dasharray="{kel:.0f}" stroke-dashoffset="{kel:.0f}"/>{bul}</svg>
        <div class="zn-lbl" id="k{n}-lbl">Area terlarang</div></div>
      <div class="bawah" style="top:438px"><span class="chip" id="k{n}-c0">{ikon("clock", 32, "#d946ef")}Dijaga jam 22.00 sampai 06.00</span></div>"""
    css = CSS_VIDEO + ".zn-lbl{position:absolute;left:110px;top:222px;background:#d946ef;color:#fff;font-size:28px;font-weight:800;padding:8px 18px;border-radius:12px}"
    js = f"""    tl.fromTo("#k{n} .zt", {{opacity:0, scale:0, transformOrigin:"50% 50%"}}, {{opacity:1, scale:1, duration:.25, ease:"back.out(3)", stagger:.3}}, {t_g});
    tl.fromTo("#k{n}-gar", {{attr:{{"stroke-dashoffset":{kel:.0f}}}}}, {{attr:{{"stroke-dashoffset":0}}, duration:1.2, ease:"none"}}, {t_g});
    tl.fromTo("#k{n}-isi", {{opacity:0}}, {{opacity:1, duration:.4}}, {t_g + 1.2:.2f});
    tl.fromTo("#k{n}-lbl", {{opacity:0, y:12}}, {{opacity:1, y:0, duration:.35}}, {t_g + 1.3:.2f});
    tl.fromTo("#k{n}-c0", {{opacity:0, y:20}}, {{opacity:1, y:0, duration:.4, ease:"back.out(2)"}}, {t0 + d * .3:.2f});
"""
    for i in range(4):
        sfx(k, t_g + i * .3 + .02, "click-soft.mp3", .25)
    return html, css, js, False


def kartu_hp(k):
    n, t0 = k["id"], k["t0"]
    hp = [("masuk", 20, 40), ("dash", 275, 0), ("riwayat_kartu", 530, 40)]
    html = "".join(f'<div class="hp" id="k{n}-h{i}" style="left:{x}px;top:{y}px"><img src="assets/img/{f}.png" alt=""></div>' for i, (f, x, y) in enumerate(hp))
    css = """.hp{position:absolute;width:230px;height:498px;border-radius:30px;overflow:hidden;border:6px solid #10233b;background:#fff;box-shadow:0 24px 50px rgba(16,35,59,.18)}
.hp img{width:100%;height:100%;display:block}"""
    js = f"""    tl.fromTo("#k{n} .hp", {{opacity:0, y:90}}, {{opacity:1, y:0, duration:.55, ease:"power3.out", stagger:.18}}, .45);
"""
    return html, css, js, True


def kartu_aman(k):
    n, t0, d = k["id"], k["t0"], k["dur"]
    t_angka = round(t0 + d * .4, 2)
    chips = [("lock", "Login aman"), ("shield-alert", "Anti-bot"), ("shield-check", "Anti-DDoS")]
    html = f"""<div class="am-bul" id="k{n}-bul">{ikon("shield-check", 76, "#1f9d5c", 2.2)}</div>
      <div class="am-angka" id="k{n}-angka">0/29</div>
      <div class="am-ket">uji serangan lolos</div>
      <div class="bawah" style="top:400px">{''.join(f'<span class="chip" id="k{n}-c{i}">{ikon(ic, 30, "#1f9d5c")}{tx}</span>' for i, (ic, tx) in enumerate(chips))}</div>"""
    css = CSS_VIDEO + """.am-bul{position:absolute;left:330px;top:34px;width:120px;height:120px;border-radius:50%;background:#e4f6ec;display:flex;align-items:center;justify-content:center}
.am-angka{position:absolute;left:0;right:0;top:160px;text-align:center;font-size:130px;font-weight:800;letter-spacing:-.04em;line-height:1.1}
.am-ket{position:absolute;left:0;right:0;top:318px;text-align:center;font-size:32px;font-weight:600;color:#5b6f86}"""
    js = f"""    tl.fromTo("#k{n}-bul", {{opacity:0, scale:.5}}, {{opacity:1, scale:1, duration:.5, ease:"back.out(2)"}}, .5);
    const skor{n} = {{v:0}};
    tl.fromTo(skor{n}, {{v:0}}, {{v:29, duration:1.3, ease:"power2.out", onUpdate:() => {{
      document.querySelector("#k{n}-angka").textContent = Math.round(skor{n}.v) + "/29"; }}}}, {t_angka});
    tl.fromTo("#k{n} .bawah .chip", {{opacity:0, y:20}}, {{opacity:1, y:0, duration:.4, ease:"back.out(2)", stagger:.2}}, {t_angka + 1.0:.2f});
"""
    sfx(k, t_angka + 1.3, "sparkle.mp3", .3)
    return html, css, js, False


def kartu_jual(k):
    n, t0, d = k["id"], k["t0"], k["dur"]
    t_b = round(t0 + d * .5, 2)
    html = f"""<div class="md-tile" id="k{n}-a" style="left:44px">{ikon("shopping-bag", 64, TEAL)}<b>Siap pakai</b><span>Langsung dipasang</span></div>
      <div class="md-tile" id="k{n}-b" style="left:406px">{ikon("wrench", 64, TEAL)}<b>Pesan khusus</b><span>Sesuai kebutuhanmu</span></div>"""
    css = """.md-tile{position:absolute;top:60px;width:330px;height:400px;border-radius:30px;border:3px solid #e6edf3;background:#f8fafc;
  display:flex;flex-direction:column;align-items:center;justify-content:center;gap:14px;text-align:center}
.md-tile b{font-size:38px;font-weight:800} .md-tile span{font-size:28px;color:#5b6f86;font-weight:600}"""
    js = f"""    tl.fromTo("#k{n}-a", {{opacity:0, y:40}}, {{opacity:1, y:0, duration:.45, ease:"back.out(1.8)"}}, .5);
    tl.fromTo("#k{n}-b", {{opacity:0, y:40}}, {{opacity:1, y:0, duration:.45, ease:"back.out(1.8)"}}, {t_b});
    tl.to("#k{n}-a", {{borderColor:"#1a8aa6", backgroundColor:"#e8f6fa", duration:.3}}, .9);
    tl.to("#k{n}-b", {{borderColor:"#1a8aa6", backgroundColor:"#e8f6fa", duration:.3}}, {t_b + .35:.2f});
"""
    sfx(k, .52, "pop.mp3", .3)
    sfx(k, t_b + .02, "pop.mp3", .3)
    return html, css, js, False


KARTU = {"jual": kartu_jual, "rekam": kartu_rekam, "logo": kartu_logo, "mode": kartu_mode, "kenal": kartu_kenal, "aturan": kartu_aturan,
         "alarm": kartu_alarm, "lewat": kartu_lewat, "nilai": kartu_nilai, "zona": kartu_zona, "hp": kartu_hp, "aman": kartu_aman}


def ketukan(k):
    n, D = k["id"], k["b_dur"]
    cid = f"b{n}"
    if k["kartu"] == "tutup":
        return ketukan_tutup(k)
    isi, css, js, polos = KARTU[k["kartu"]](k)
    html = f"""    <div class="tag" id="k{n}-tag"><span>{k["tag"]}</span></div>
    <div class="j" id="k{n}-j1">{k["j1"]}</div>
    <div class="j teal" id="k{n}-j2">{k["j2"]}</div>
    <div class="kartu{' polos' if polos else ''}" id="k{n}">
      {isi}
    </div>"""
    gaya = DASAR + f"""
.tag{{position:absolute;left:0;right:0;top:326px;text-align:center}}
.tag span{{display:inline-block;background:{TEAL_TUA};color:#fff;font-size:28px;font-weight:800;letter-spacing:.2em;padding:14px 34px 14px 40px;border-radius:999px}}
.j{{position:absolute;left:40px;right:40px;text-align:center;font-size:100px;font-weight:800;line-height:1;letter-spacing:-.01em;white-space:nowrap}}
#k{n}-j1{{top:446px}} #k{n}-j2{{top:552px}} .teal{{color:{TEAL}}}
.kartu{{position:absolute;left:150px;top:760px;width:780px;height:520px;border-radius:40px;background:#fff;
  border:1px solid rgba(16,35,59,.06);box-shadow:0 30px 70px rgba(16,35,59,.10)}}
.kartu.polos{{background:transparent;border:none;box-shadow:none}}
.chip{{display:inline-flex;align-items:center;gap:12px;padding:12px 24px;border-radius:999px;background:#f1f6f9;border:2px solid #e2eaf0;font-size:28px;font-weight:700;white-space:nowrap}}
{css}"""
    tlj = f"""    tl.fromTo("#k{n}-tag", {{opacity:0, scale:.8}}, {{opacity:1, scale:1, duration:.35, ease:"back.out(2)"}}, .05);
    tl.fromTo("#k{n}-j1", {{opacity:0, y:40, filter:"blur(10px)"}}, {{opacity:1, y:0, filter:"blur(0px)", duration:.5, ease:"power3.out"}}, .12);
    tl.fromTo("#k{n}-j2", {{opacity:0, y:40, filter:"blur(10px)"}}, {{opacity:1, y:0, filter:"blur(0px)", duration:.5, ease:"power3.out"}}, .22);
    tl.fromTo("#k{n}", {{opacity:0, y:50, scale:.96}}, {{opacity:1, y:0, scale:1, duration:.55, ease:"power3.out"}}, .3);
{js}    tl.to("#k{n}-tag, #k{n}-j1, #k{n}-j2", {{opacity:0, filter:"blur(10px)", duration:.3, ease:"power2.in"}}, {D - .34:.3f});
    tl.to("#k{n}", {{opacity:0, scale:.97, duration:.3, ease:"power2.in"}}, {D - .34:.3f});
"""
    if n != "01":
        sfx(k, .3, "whoosh-short.mp3", .22)
    else:   # frame pertama jadi gambar sampul: judul dan kartu sudah tampil sejak detik 0
        tlj = tlj.replace('-tag", {opacity:0, scale:.8}', '-tag", {opacity:1, scale:1}').replace('{opacity:0, y:40, filter:"blur(10px)"}', '{opacity:1, y:0, filter:"blur(0px)"}').replace('{opacity:0, y:50, scale:.96}', '{opacity:1, y:0, scale:1}')
    return cid, komposisi(cid, html, tlj, gaya)


def ketukan_tutup(k):
    n, t0, d, D = k["id"], k["t0"], k["dur"], k["b_dur"]
    cid = f"b{n}"
    teks = k["teks"]
    warna_kata = set(k["sorot"].split("|"))
    huruf = []
    for kata_i, kata in enumerate(teks.split(" ")):
        if kata_i:
            huruf.append('<span class="sp"> </span>')
        kelas = ' class="tl"' if kata.strip(".,?!") in warna_kata else ""
        huruf.extend(f'<span{kelas}>{ch}</span>' for ch in kata)
    t_ketik, lama = round(t0 + .05, 2), round(max(1.4, d * .8), 2)
    html = f"""    <img id="k{n}-logo" src="assets/img/logo.png" alt="">
    <div id="k{n}-teks">{''.join(huruf)}</div>
    <div id="k{n}-bm">{ikon(NASKAH.get("ikon_tutup", "bookmark"), 100, TEAL, 2.4)}</div>
    <div id="k{n}-gh">github.com/Khairul122</div>"""
    gaya = DASAR + f"""
#k{n}-logo{{position:absolute;left:430px;top:470px;width:220px}}
#k{n}-teks{{position:absolute;left:110px;right:110px;top:800px;text-align:center;font-size:72px;font-weight:800;line-height:1.15}}
#k{n}-teks .tl{{color:{TEAL}}}
#k{n}-bm{{position:absolute;left:490px;top:1070px}}
#k{n}-gh{{position:absolute;left:0;right:0;top:1230px;text-align:center;font-size:34px;font-weight:700;color:#5b6f86}}"""
    js = f"""    tl.fromTo("#k{n}-logo", {{opacity:0, scale:.6}}, {{opacity:1, scale:1, duration:.55, ease:"back.out(1.8)"}}, .1);
    tl.fromTo("#k{n}-teks span", {{opacity:0}}, {{opacity:1, duration:.01, stagger:{lama / len(teks):.4f}}}, {t_ketik});
    tl.fromTo("#k{n}-bm", {{opacity:0, scale:.4}}, {{opacity:1, scale:1, duration:.4, ease:"back.out(2.5)"}}, {t_ketik + lama + .1:.2f});
    tl.fromTo("#k{n}-gh", {{opacity:0}}, {{opacity:1, duration:.5}}, {t_ketik + lama + .4:.2f});
"""
    sfx(k, .1, "whoosh-short.mp3", .22)
    sfx(k, t_ketik + .457, "typing.mp3", .25)
    sfx(k, t_ketik + lama + .5 - .38, "pop.mp3", .3)
    return cid, komposisi(cid, html, js, gaya)


def komposisi(cid, html, js, gaya):
    return f"""<template>
  <style>{gaya}</style>
  <div id="root" data-composition-id="{cid}" data-width="{W}" data-height="{H}">
{html}
  </div>
  <script>
    const tl = gsap.timeline({{ paused: true }});
{js}    window.__timelines["{cid}"] = tl;
  </script>
</template>
"""


def latar():
    html = """    <div id="lt-dasar"></div>
    <div id="lt-a" class="blob" data-layout-allow-overflow></div><div id="lt-b" class="blob" data-layout-allow-overflow></div><div id="lt-c" class="blob" data-layout-allow-overflow></div>
    <div id="lt-grid"></div>"""
    gaya = DASAR + """
#lt-dasar{position:absolute;inset:0;background:#f7f9fb}
.blob{position:absolute;border-radius:50%}
#lt-a{left:-300px;top:-200px;width:1100px;height:1100px;background:radial-gradient(closest-side,rgba(46,197,232,.24),rgba(46,197,232,0))}
#lt-b{left:300px;top:1100px;width:1200px;height:1200px;background:radial-gradient(closest-side,rgba(250,186,140,.26),rgba(250,186,140,0))}
#lt-c{left:500px;top:300px;width:900px;height:900px;background:radial-gradient(closest-side,rgba(120,200,190,.16),rgba(120,200,190,0))}
#lt-grid{position:absolute;inset:0;background-image:linear-gradient(rgba(16,35,59,.05) 2px,transparent 2px),linear-gradient(90deg,rgba(16,35,59,.05) 2px,transparent 2px);background-size:60px 60px}"""
    js = f"""    tl.fromTo("#lt-a", {{x:0, y:0}}, {{x:160, y:220, duration:{TOTAL}, ease:"sine.inOut"}}, 0);
    tl.fromTo("#lt-b", {{x:0, y:0}}, {{x:-220, y:-160, duration:{TOTAL}, ease:"sine.inOut"}}, 0);
    tl.fromTo("#lt-c", {{x:0, y:0}}, {{x:-120, y:260, duration:{TOTAL}, ease:"sine.inOut"}}, 0);
"""
    return komposisi("latar", html, js, gaya)


def merek():
    html = f"""    <div id="mr-atas">KHAIRUL122</div>
    <div id="mr-bawah"><img src="assets/img/logo_256.png" alt=""><div><i data-layout-ignore>FOLLOW GITHUB</i><b>KHAIRUL122</b></div></div>"""
    gaya = DASAR + """
#mr-atas{position:absolute;right:70px;top:168px;font-size:30px;font-weight:800;letter-spacing:.02em}
#mr-bawah{position:absolute;left:70px;top:1740px;display:flex;gap:14px;align-items:center}
#mr-bawah img{width:64px;height:64px;border-radius:16px;background:#fff;padding:4px;box-shadow:0 6px 16px rgba(16,35,59,.12)}
#mr-bawah i{display:block;font-size:20px;font-weight:600;letter-spacing:.06em;color:#5b6f86}
#mr-bawah b{display:block;font-size:30px;font-weight:800}"""
    js = """    tl.fromTo("#mr-atas, #mr-bawah", {opacity:1}, {opacity:1, duration:.5}, 0);
"""
    return komposisi("merek", html, js, gaya)


import re
f_bicara = DIR / f"{SUARA}/bicara.json"
BICARA = json.load(open(f_bicara)) if f_bicara.exists() else {}


def waktu_kata(k, frac):
    """Detik (dari awal suara) saat bagian teks di posisi frac diucapkan.
    Potongan ucapan (dipisah tanda baca) dipasangkan dengan bagian bicara di WAV bila jumlahnya sama."""
    seg = BICARA.get(k["id"])
    if not seg:
        return frac * k["dur"]
    potong = [p for p in re.split(r"(?<=[.,?:!])\s+", k["ucapan"].strip()) if p]
    if len(potong) != len(seg):
        a, b = seg[0][0], seg[-1][1]
        return a + frac * (b - a)
    tot = sum(len(p) for p in potong)
    target, acc = frac * tot, 0
    for p, (a, b) in zip(potong, seg):
        if target <= acc + len(p):
            return a + (target - acc) / len(p) * (b - a)
        acc += len(p)
    return seg[-1][1]


def subtitle():
    el, js = [], []
    for i, k in enumerate(KAL):
        if k["kartu"] == "tutup":
            continue
        kata = k["teks"].split()
        sorot = k["sorot"].split()
        idx = next((j for j in range(len(kata)) if [w.strip(".,?:!") for w in kata[j:j + len(sorot)]] == [w.strip(".,?:!") for w in sorot]), None)
        tot = sum(len(w) + 1 for w in kata)
        spans, pos = [], 0
        akhir_grup = min(k["mulai"] + k["dur"] + .3, KAL[i + 1]["b_mulai"] + .25 if i + 1 < len(KAL) else 1e9)
        mulai_grup = round(k["mulai"] - .15, 3)
        for j, w in enumerate(kata):
            span = f'<span id="s{k["id"]}w{j}">{w}</span>'
            if idx is not None and j == idx:
                span = '<span class="hl">' + span
            if idx is not None and j == idx + len(sorot) - 1:
                span += '</span>'
            spans.append(span)
            t = k["mulai"] + waktu_kata(k, pos / tot)
            js.append(f'    tl.fromTo("#s{k["id"]}w{j}", {{opacity:.28}}, {{opacity:1, duration:.12}}, {round(t - .03, 3)});')
            pos += len(w) + 1
        el.append(f'    <div id="sub{k["id"]}" class="clip grp" data-start="{mulai_grup}" data-duration="{round(akhir_grup - mulai_grup, 3)}">'
                  f'<p id="sp{k["id"]}">{" ".join(spans)}</p></div>')
        js.append(f'    tl.fromTo("#sp{k["id"]}", {{opacity:0, y:16}}, {{opacity:1, y:0, duration:.2, ease:"power2.out"}}, {mulai_grup});')
        js.append(f'    tl.to("#sp{k["id"]}", {{opacity:0, duration:.18}}, {round(akhir_grup - .2, 3)});')
    gaya = DASAR + f"""
.grp{{position:absolute;left:110px;right:110px;top:1350px;text-align:center}}
.grp p{{font-size:46px;font-weight:700;line-height:1.4;color:{NAVY}}}
.grp .hl{{background:#c9edf5;border-radius:12px;padding:0 10px;box-decoration-break:clone;-webkit-box-decoration-break:clone}}"""
    return komposisi("subtitle", "\n".join(el), "\n".join(js) + "\n", gaya)


def tulis():
    comp = DIR / "compositions"
    comp.mkdir(exist_ok=True)
    for f in comp.glob("*.html"):
        f.unlink()
    host = []

    def pasang(cid, teks, mulai, dur, jalur, jenis, z):
        (comp / f"{cid}.html").write_text(terjemah(teks), encoding="utf-8")
        host.append(f'      <div id="{cid}" data-composition-id="{cid}" data-composition-src="compositions/{cid}.html" data-start="{mulai}" '
                    f'data-duration="{dur}" data-track-index="{jalur}" data-track-kind="{jenis}" data-width="{W}" data-height="{H}" style="z-index:{z}"></div>')

    pasang("latar", latar(), 0, TOTAL, 0, "graphics", 0)
    for k in KAL:
        cid, teks = ketukan(k)
        pasang(cid, teks, k["b_mulai"], k["b_dur"], 1, "graphics", 2)
    pasang("merek", merek(), 0, TOTAL, 2, "graphics", 3)
    pasang("subtitle", subtitle(), 0, TOTAL, 3, "captions", 4)

    audio, ada = [], 0
    for k in KAL:
        if (DIR / f"{SUARA}/{k['id']}.wav").exists():
            ada += 1
            audio.append(f'      <audio id="vo{k["id"]}" class="clip" src="{SUARA}/{k["id"]}.wav" data-start="{k["mulai"]}" '
                         f'data-duration="{k["dur"]}" data-track-index="4" data-volume="1"></audio>')
    musik = next((p for p in ("assets/musik.mp3", "assets/musik.wav") if (DIR / p).exists()), None)
    if musik:
        audio.append(f'      <audio id="musik" class="clip" src="{musik}" data-start="0" data-duration="{TOTAL}" data-track-index="5" '
                     f'data-volume="{(0.11 if BAHASA == "en" else 0.13) if ada else 0.45}" data-fade-in="1" data-fade-out="2.5"></audio>')
    for i, (t0, f, vol) in enumerate(sorted(SFX)):
        audio.append(f'      <audio id="sfx{i:02d}" class="clip" src="assets/sfx/{f}" data-start="{t0}" data-duration="{panjang_audio(DIR / "assets/sfx" / f)}" '
                     f'data-track-index="{10 + i}" data-volume="{vol}"></audio>')
    index = f"""<!doctype html>
<html lang="id">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width={W}, height={H}" />
    <script src="assets/vendor/gsap.min.js"></script>
    <style>
      * {{ margin: 0; padding: 0; box-sizing: border-box; }}
      html, body {{ width: {W}px; height: {H}px; overflow: hidden; background: #f7f9fb; }}
      #root {{ position: relative; width: {W}px; height: {H}px; background: #f7f9fb; }}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="{TOTAL}" data-width="{W}" data-height="{H}">
{chr(10).join(host)}
{chr(10).join(audio)}
    </div>
    <script>
      window.__timelines = window.__timelines || {{}};
      window.__timelines["main"] = gsap.timeline({{ paused: true }});
    </script>
  </body>
</html>
"""
    (DIR / "index.html").write_text(index, encoding="utf-8")
    print(json.dumps({"total_s": TOTAL, "suara": f"{ada}/{len(KAL)}", "musik": musik,
                      "ketukan": {k["id"]: [k["b_mulai"], k["b_dur"]] for k in KAL}}))


tulis()
