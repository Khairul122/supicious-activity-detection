"""Presentation tier: keamanan HTTP.

- Wajib masuk: semua halaman dan API butuh session yang sah, kecuali halaman masuk, pengaturan awal, dan berkas statis.
- Session: cookie bertanda tangan (HttpOnly, SameSite=Lax), batas diam 8 jam, kunci rahasia tetap di storage/.
- CSRF: setiap POST/DELETE wajib membawa token session (kolom csrf_token atau header X-CSRF-Token).
- Pembatas permintaan per alamat IP (jendela geser) untuk semua permintaan, percobaan masuk, dan unggahan;
  jumlah tayangan video bersamaan per IP juga dibatasi. Ini meredam banjir permintaan dan tebak sandi dari
  satu sumber. Serangan DDoS skala jaringan tetap harus ditahan di firewall atau router.
- Header: Content-Security-Policy dengan nonce, X-Frame-Options, nosniff, Referrer-Policy, Permissions-Policy, noindex.
"""
import hmac
import secrets
import threading
import time
from collections import deque
from datetime import timedelta
from urllib.parse import urlsplit

from flask import abort, g, jsonify, redirect, request, session, url_for

from .. import log

logger = log.get("keamanan")

DIAM_MAKS_S = 8 * 3600          # keluar otomatis setelah 8 jam tanpa aktivitas
TETAP_MASUK_HARI = 30           # "Tetap masuk": cookie bertahan 30 hari (tetap kena batas diam)
BATAS_UMUM = (600, 60)          # 600 permintaan per 60 detik per IP (halaman Kamera memeriksa status tiap detik)
BATAS_MASUK = (10, 600)         # 10 percobaan masuk per 10 menit per IP
BATAS_UNGGAH = (20, 3600)       # 20 unggahan video per jam per IP
TAYANGAN_MAKS = 4               # tayangan video bersamaan per IP
TERBUKA = {"static", "auth.masuk", "auth.pengaturan_awal", "auth.robots", "auth.favicon"}


class RateLimiter:
    """Jendela geser per kunci. Aman untuk banyak thread; kunci lama dibuang agar memori tidak tumbuh."""

    def __init__(self, jumlah, detik):
        self.jumlah, self.detik = jumlah, detik
        self._catatan = {}
        self._kunci = threading.Lock()
        self._bersih = time.monotonic()

    def izinkan(self, kunci, sekarang=None):
        sekarang = time.monotonic() if sekarang is None else sekarang
        with self._kunci:
            if sekarang - self._bersih > self.detik:
                for k in [k for k, q in self._catatan.items() if not q or sekarang - q[-1] > self.detik]:
                    del self._catatan[k]
                self._bersih = sekarang
            q = self._catatan.setdefault(kunci, deque())
            while q and sekarang - q[0] > self.detik:
                q.popleft()
            if len(q) >= self.jumlah:
                return False
            q.append(sekarang)
            return True

    def tunggu(self, kunci, sekarang=None):
        """Detik sampai permintaan berikutnya diizinkan."""
        sekarang = time.monotonic() if sekarang is None else sekarang
        with self._kunci:
            q = self._catatan.get(kunci)
            return max(0.0, self.detik - (sekarang - q[0])) if q else 0.0


class PenghitungTayangan:
    def __init__(self, maks):
        self.maks, self._n, self._kunci = maks, {}, threading.Lock()

    def ambil(self, ip):
        with self._kunci:
            if self._n.get(ip, 0) >= self.maks:
                return False
            self._n[ip] = self._n.get(ip, 0) + 1
            return True

    def lepas(self, ip):
        with self._kunci:
            self._n[ip] = max(0, self._n.get(ip, 1) - 1)


def alamat_aman(tujuan, cadangan="/"):
    """Hanya jalur lokal (mencegah pengalihan ke situs lain)."""
    if not tujuan or not tujuan.startswith("/") or tujuan.startswith("//") or "\\" in tujuan:
        return cadangan
    bagian = urlsplit(tujuan)
    return tujuan if not bagian.scheme and not bagian.netloc else cadangan


def token_csrf():
    if "csrf" not in session:
        session["csrf"] = secrets.token_urlsafe(32)
    return session["csrf"]


def kunci_rahasia(folder):
    """Kunci session tetap antar-restart (disimpan sekali di storage), agar petugas tidak keluar tiap web dimulai ulang."""
    folder.mkdir(parents=True, exist_ok=True)
    berkas = folder / ".kunci_session"
    if berkas.is_file() and len(berkas.read_text().strip()) >= 64:
        return berkas.read_text().strip()
    kunci = secrets.token_hex(32)
    berkas.write_text(kunci)
    return kunci


def _ditolak(pesan, kode):
    if request.path.startswith("/api/") or request.accept_mimetypes.best == "application/json":
        return jsonify({"galat": pesan}), kode
    return pesan, kode, {"Content-Type": "text/plain; charset=utf-8"}


def pasang(app, auth_service, secure_cookie=False):
    app.config.update(
        SESSION_COOKIE_NAME="sad_sesi", SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=secure_cookie, PERMANENT_SESSION_LIFETIME=timedelta(days=TETAP_MASUK_HARI))
    umum, masuk, unggah = RateLimiter(*BATAS_UMUM), RateLimiter(*BATAS_MASUK), RateLimiter(*BATAS_UNGGAH)
    app.extensions["batas_masuk"] = masuk
    app.extensions["tayangan"] = PenghitungTayangan(TAYANGAN_MAKS)

    @app.before_request
    def periksa():
        g.csp_nonce = secrets.token_urlsafe(16)
        ip = request.remote_addr or "-"
        if request.endpoint != "static" and not umum.izinkan(ip):
            logger.warning("Terlalu banyak permintaan dari %s (%s %s)", ip, request.method, request.path)
            return _ditolak("Terlalu banyak permintaan. Tunggu sebentar lalu coba lagi.", 429)
        if request.method == "POST" and request.endpoint == "kamera.unggah" and not unggah.izinkan(ip):
            return _ditolak("Batas unggahan tercapai. Coba lagi nanti.", 429)

        # CSRF untuk semua permintaan yang mengubah data
        if request.method in ("POST", "PUT", "PATCH", "DELETE"):
            asal = request.headers.get("Origin") or request.headers.get("Referer")
            if asal and urlsplit(asal).netloc != request.host:
                logger.warning("Permintaan lintas situs ditolak dari %s: %s", ip, asal)
                abort(403)
            dikirim = request.headers.get("X-CSRF-Token") or request.form.get("csrf_token", "")
            if not dikirim or not hmac.compare_digest(str(dikirim), session.get("csrf", "")):
                logger.warning("Token CSRF tidak sah dari %s (%s %s)", ip, request.method, request.path)
                return _ditolak("Sesi formulir kedaluwarsa. Muat ulang halaman lalu coba lagi.", 400)

        # wajib masuk
        if request.endpoint in TERBUKA:
            return None
        g.pengguna = None
        if "uid" in session:
            if time.time() - session.get("aktif", 0) > DIAM_MAKS_S:
                session.clear()
                session["pesan_keluar"] = "Anda keluar otomatis karena tidak aktif lebih dari 8 jam."
            else:
                g.pengguna = auth_service.pengguna_sesi(session["uid"], session.get("versi"))
                if g.pengguna is None:
                    session.clear()
                elif request.endpoint not in ("api.status", "api.belum_dinilai", "kamera.stream"):
                    session["aktif"] = time.time()   # pemeriksaan otomatis tidak memperpanjang sesi
        if g.pengguna is None:
            if auth_service.perlu_pengaturan_awal():
                tujuan = url_for("auth.pengaturan_awal")
            else:
                tujuan = url_for("auth.masuk", lanjut=request.full_path if request.method == "GET" else None)
            if request.path.startswith("/api/") or request.endpoint == "kamera.stream":
                return jsonify({"galat": "Sesi berakhir. Silakan masuk lagi.", "masuk": tujuan}), 401
            return redirect(tujuan)
        return None

    @app.after_request
    def header(resp):
        nonce = getattr(g, "csp_nonce", "")
        resp.headers.setdefault("Content-Security-Policy", "; ".join([
            "default-src 'self'", f"script-src 'self' 'nonce-{nonce}'", "style-src 'self' 'unsafe-inline'",
            "img-src 'self' data: blob:", "font-src 'self'", "connect-src 'self'", "media-src 'self' blob:",
            "object-src 'none'", "base-uri 'none'", "form-action 'self'", "frame-ancestors 'none'"]))
        resp.headers.setdefault("X-Frame-Options", "DENY")
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("Referrer-Policy", "same-origin")
        resp.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=(), payment=()")
        resp.headers.setdefault("X-Robots-Tag", "noindex, nofollow")
        resp.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
        if request.endpoint != "static" and resp.mimetype == "text/html":
            resp.headers["Cache-Control"] = "no-store"
        resp.headers.pop("Server", None)
        return resp

    @app.context_processor
    def konteks():
        return {"csrf_token": token_csrf, "csp_nonce": lambda: getattr(g, "csp_nonce", ""),
                "pengguna": getattr(g, "pengguna", None)}
