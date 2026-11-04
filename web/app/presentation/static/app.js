// Bagian bersama semua halaman: dialog pemberitahuan, token keamanan, status kamera, lencana, dan notifikasi.
(function () {
  var csrf = (document.querySelector('meta[name="csrf-token"]') || {}).content || "";

  // ---------- token CSRF untuk setiap fetch yang mengubah data ----------
  var fetchAsli = window.fetch.bind(window);
  window.fetch = function (url, opsi) {
    opsi = opsi || {};
    var metode = (opsi.method || "GET").toUpperCase();
    if (metode !== "GET" && metode !== "HEAD") {
      var h = new Headers(opsi.headers || {});
      h.set("X-CSRF-Token", csrf);
      opsi.headers = h;
    }
    return fetchAsli(url, opsi).then(function (r) {
      if (r.status === 401) {   // sesi berakhir: ke halaman masuk
        r.clone().json().then(function (d) { window.location.href = d.masuk || "/masuk"; }).catch(function () {});
      }
      return r;
    });
  };
  window.csrfToken = csrf;

  // ---------- dialog ----------
  var dlg = document.getElementById("dialog");
  var IKON = { sukses: "#i-circle-check", galat: "#i-triangle-alert", info: "#i-info", konfirmasi: "#i-circle-alert",
               bahaya: "#i-triangle-alert" };
  var JUDUL = { sukses: "Berhasil", galat: "Gagal", info: "Informasi", konfirmasi: "Konfirmasi", bahaya: "Perhatian" };
  var antre = [], aktif = null;

  function tampilBerikut() {
    if (aktif || !antre.length || !dlg) return;
    aktif = antre.shift();
    var o = aktif.opsi;
    dlg.dataset.jenis = o.jenis;
    document.getElementById("dialog-ikon").setAttribute("href", IKON[o.jenis] || IKON.info);
    document.getElementById("dialog-judul").textContent = o.judul || JUDUL[o.jenis] || "";
    document.getElementById("dialog-pesan").textContent = o.pesan || "";
    var ok = document.getElementById("dialog-ok"), batal = document.getElementById("dialog-batal");
    ok.textContent = o.tombolYa || (o.jenis === "konfirmasi" ? "Ya, lanjutkan" : "Oke");
    ok.className = "btn " + (o.jenis === "konfirmasi" && o.bahaya ? "btn-bahaya" : "btn-utama");
    batal.classList.toggle("hidden", o.jenis !== "konfirmasi");
    batal.textContent = o.tombolTidak || "Batal";
    if (typeof dlg.showModal === "function") dlg.showModal(); else dlg.setAttribute("open", "");
    (o.jenis === "konfirmasi" ? batal : ok).focus();
    if (o.otomatis) aktif.waktu = setTimeout(function () { tutup(true); }, o.otomatis);
  }
  function tutup(hasil) {
    if (!aktif) return;
    clearTimeout(aktif.waktu);
    var selesai = aktif.selesai;
    aktif = null;
    if (dlg.open) dlg.close();
    selesai(hasil);
    setTimeout(tampilBerikut, 120);
  }
  if (dlg) {
    document.getElementById("dialog-ok").addEventListener("click", function () { tutup(true); });
    document.getElementById("dialog-batal").addEventListener("click", function () { tutup(false); });
    dlg.addEventListener("cancel", function (e) { e.preventDefault(); tutup(false); });   // tombol Esc
    dlg.addEventListener("click", function (e) { if (e.target === dlg) tutup(false); }); // klik di luar kotak
  }
  // window.dialog({jenis: "sukses"|"galat"|"info"|"konfirmasi", judul, pesan, otomatis: ms}) -> Promise<boolean>
  window.dialog = function (opsi) {
    return new Promise(function (selesai) {
      if (!dlg) { window.alert((opsi.judul ? opsi.judul + "\n" : "") + (opsi.pesan || "")); selesai(true); return; }
      antre.push({ opsi: opsi, selesai: selesai });
      tampilBerikut();
    });
  };
  window.konfirmasi = function (pesan, opsi) {
    opsi = opsi || {};
    return window.dialog({ jenis: "konfirmasi", pesan: pesan, judul: opsi.judul, tombolYa: opsi.tombolYa, bahaya: opsi.bahaya });
  };
  // pesan dari server (mulai sesi, berhasil, gagal, masuk, keluar)
  var dataPesan = document.getElementById("pesan-server");
  if (dataPesan) {
    try {
      JSON.parse(dataPesan.textContent || "[]").forEach(function (p) {
        var jenis = p[0] === "sukses" ? "sukses" : p[0] === "galat" ? "galat" : "info";
        window.dialog({ jenis: jenis, pesan: p[1], otomatis: jenis === "sukses" ? 3500 : 0 });
      });
    } catch (e) { /* data pesan rusak: abaikan */ }
  }

  // ---------- tombol tampilkan sandi ----------
  document.querySelectorAll("[data-lihat]").forEach(function (b) {
    b.addEventListener("click", function () {
      var input = document.getElementById(b.dataset.lihat);
      var lihat = input.type === "password";
      input.type = lihat ? "text" : "password";
      b.setAttribute("aria-pressed", String(lihat));
      b.setAttribute("aria-label", lihat ? "Sembunyikan sandi" : "Tampilkan sandi");
      b.querySelector("use").setAttribute("href", lihat ? "#i-eye-off" : "#i-eye");
    });
  });
  // tombol kirim dinonaktifkan sesaat agar formulir tidak terkirim dua kali
  document.querySelectorAll("form[method=post]").forEach(function (f) {
    f.addEventListener("submit", function (e) {
      if (e.defaultPrevented) return;
      var t = e.submitter;
      if (t && !t.classList.contains("btn-kecil")) setTimeout(function () { t.disabled = true; }, 0);
    });
  });

  // ---------- status kamera di menu samping ----------
  var siaran = document.getElementById("status-kamera");
  window.keadaanKamera = function (s) {
    if (!s.berjalan) return "siap";
    return s.frame > 0 ? "memantau" : "menyiapkan";
  };
  if (siaran) {
    var judul = document.getElementById("siaran-judul");
    var sumber = document.getElementById("siaran-sumber");
    var refresh = function () {
      fetch("/api/status", { cache: "no-store" })
        .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
        .then(function (s) {
          var k = window.keadaanKamera(s);
          siaran.dataset.keadaan = k;
          judul.textContent = k === "memantau" ? "Sedang memantau" : k === "menyiapkan" ? "Menyiapkan kamera…" : "Kamera tidak aktif";
          sumber.textContent = s.berjalan ? (s.sumber || "") : "Buka Kamera untuk memulai";
          document.dispatchEvent(new CustomEvent("status-kamera", { detail: s }));
        })
        .catch(function () {
          siaran.dataset.keadaan = "putus";
          judul.textContent = "Server tidak terjangkau";
          sumber.textContent = "Pastikan web masih berjalan";
        });
    };
    refresh();
    setInterval(refresh, document.getElementById("video") ? 1000 : 2000);
  }

  // ---------- lencana jumlah peringatan yang belum dinilai ----------
  var lencana = document.getElementById("nav-belum");
  if (lencana) {
    var belum = function () {
      fetch("/api/belum-dinilai", { cache: "no-store" })
        .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
        .then(function (d) {
          lencana.textContent = d.jumlah > 99 ? "99+" : String(d.jumlah);
          lencana.classList.toggle("hidden", !d.jumlah);
          lencana.setAttribute("aria-label", d.jumlah + " peringatan belum dinilai");
        })
        .catch(function () {});
    };
    belum();
    setInterval(belum, 10000);
    document.addEventListener("penilaian-berubah", belum);
  }

  // ---------- notifikasi peringatan deteksi (tidak menutup tayangan) ----------
  var wadah = document.getElementById("toast");
  window.toast = function (judulToast, teks, jenis, opsi) {
    if (!wadah) return;
    opsi = opsi || {};
    var t = document.createElement(opsi.tautan ? "a" : "div");
    t.className = "toast toast-" + (jenis || "info");
    if (opsi.tautan) t.href = opsi.tautan;
    if (opsi.gambar) {
      var img = document.createElement("img");
      img.src = opsi.gambar;
      img.alt = "";
      t.appendChild(img);
    }
    var isi = document.createElement("span");
    var b = document.createElement("strong");
    b.textContent = judulToast;
    isi.appendChild(b);
    if (teks) {
      var p = document.createElement("small");
      p.textContent = teks;
      isi.appendChild(p);
    }
    t.appendChild(isi);
    wadah.appendChild(t);
    setTimeout(function () { t.classList.add("keluar"); }, opsi.lama || 6000);
    setTimeout(function () { t.remove(); }, (opsi.lama || 6000) + 400);
  };

  // penilaian cepat lewat API, dipakai halaman Kamera dan Riwayat
  window.nilaiPeringatan = function (id, penilaian) {
    return fetch("/api/peringatan/" + id + "/nilai", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ penilaian: penilaian })
    }).then(function (r) {
      return r.json().then(function (d) {
        if (!r.ok) throw new Error(d.galat || "Penilaian gagal disimpan.");
        document.dispatchEvent(new CustomEvent("penilaian-berubah"));
        return d;
      });
    });
  };
})();
