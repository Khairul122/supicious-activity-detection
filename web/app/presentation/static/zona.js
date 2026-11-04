// Halaman Cam: daftar zona per sumber dan editor poligon zona.
(function () {
  var WARNA = { santai: "rgb(40,170,90)", sensitif: "rgb(255,165,0)", terlarang: "rgb(200,40,160)" };
  var LABEL = { santai: "Santai", sensitif: "Sensitif", terlarang: "Terlarang" };
  var daftar = document.getElementById("daftar-zona");
  var labelSumber = document.getElementById("zona-sumber");
  var btnAtur = document.getElementById("btn-atur-zona");
  var editor = document.getElementById("editor-zona");
  var bar = document.getElementById("editor-bar");
  var img = document.getElementById("editor-img");
  var canvas = document.getElementById("editor-canvas");
  var info = document.getElementById("editor-info");
  var ctx = canvas.getContext("2d");
  var zonaAda = [];
  var titik = [];
  var editing = false;
  var INFO_AWAL = info.textContent;

  function sumber() {
    var jenis = document.querySelector('input[name="jenis"]:checked').value;
    var nilai = (document.getElementById("nilai_" + jenis) || {}).value || "";
    return { jenis: jenis, nilai: nilai };
  }
  function query() {
    var s = sumber();
    return "jenis=" + encodeURIComponent(s.jenis) + "&nilai=" + encodeURIComponent(s.nilai);
  }
  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text !== undefined) e.textContent = text;
    return e;
  }
  function pesan(teks, galat) {
    info.textContent = teks;
    info.classList.toggle("notice-inline", !!galat);
  }

  var modeSelect = document.getElementById("mode");
  var catatan = document.getElementById("zona-catatan");
  var CATATAN = {
    umum: "Tanpa zona, sistem memakai aturan umum: diam 20 detik atau lebih di area sempit, atau mondar-mandir. Zona berlaku per sumber video.",
    otomatis: "Mode otomatis: bila terlihat minimal 2 motor terparkir, aturan parkiran yang dipakai. Selain itu aturan umum. " +
      "Zona yang digambar berlaku untuk kedua aturan. Zona berlaku per sumber video.",
    parkir: "Mode parkiran: orang asing 15 detik atau lebih di dekat motor, jongkok 5 detik di dekat motor, berpindah ke 3 motor berbeda, " +
      "mendorong motor, atau membawa motor yang pemiliknya berpenampilan lain memicu peringatan. " +
      "Gambar zona santai di pos petugas parkir. Zona berlaku per sumber video."
  };
  function perbaruiCatatan() {
    catatan.textContent = CATATAN[modeSelect.value] || CATATAN.umum;
  }
  modeSelect.addEventListener("change", function () { perbaruiCatatan(); muatZonaTampil(); });

  function jamTeks(z) {
    return z.jam_mulai ? "aktif " + z.jam_mulai + " sampai " + z.jam_selesai : "selalu aktif";
  }

  function muatZona() {
    fetch("/api/zona?" + query(), { cache: "no-store" })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        zonaAda = data.zona || [];
        labelSumber.textContent = data.sumber || "";
        if (data.mode) modeSelect.value = (data.mode === "parkir" && !data.parkir_tersedia) ? "umum" : data.mode;
        modeSelect.dispatchEvent(new Event("mode-sinkron"));
        perbaruiCatatan();
        tampilkan(data);
      });
  }

  var dataTerakhir = null;
  function muatZonaTampil() { if (dataTerakhir) tampilkan(dataTerakhir); }

  function tampilkan(data) {
    dataTerakhir = data;
    daftar.innerHTML = "";
    if (data.galat) {
      daftar.appendChild(el("li", "kosong", data.galat));
      btnAtur.disabled = true;
      return;
    }
    btnAtur.disabled = false;
    if (!zonaAda.length) {
      var li = el("li", "anjuran");
      li.appendChild(el("strong", "", "Belum ada zona untuk sumber ini."));
      li.appendChild(el("span", "", modeSelect.value === "parkir"
        ? " Aturan parkiran berlaku di seluruh gambar. Gambar zona santai di pos petugas parkir, dan zona terlarang " +
          "berjadwal (misalnya 22:00 sampai 06:00) bila parkiran tutup pada malam hari."
        : " Sistem memakai aturan umum: diam 20 detik atau lebih, atau mondar-mandir, dicurigai di mana saja. " +
          "Gambar zona santai, sensitif, atau terlarang agar orang yang duduk atau berjalan di area umum tidak memicu peringatan."));
      daftar.appendChild(li);
    }
    zonaAda.forEach(function (z) {
      var li = el("li", "zona-item");
      var kiri = el("div");
      var warna = el("span", "zona-jenis");
      warna.style.background = WARNA[z.jenis];
      kiri.appendChild(warna);
      kiri.appendChild(el("strong", "", z.nama));
      kiri.appendChild(el("span", "zona-label", LABEL[z.jenis]));
      kiri.appendChild(el("div", "muted zona-jam", jamTeks(z)));
      var hapus = el("button", "btn btn-kecil btn-teks", "Hapus");
      hapus.type = "button";
      hapus.setAttribute("aria-label", "Hapus zona " + z.nama);
      hapus.addEventListener("click", function () {
        window.konfirmasi("Zona '" + z.nama + "' akan dihapus dari sumber ini.", { judul: "Hapus zona?", tombolYa: "Hapus", bahaya: true })
          .then(function (ya) {
            if (!ya) return;
            fetch("/api/zona/" + z.id, { method: "DELETE" }).then(function (r) {
              muatZona();
              window.dialog(r.ok ? { jenis: "sukses", pesan: "Zona '" + z.nama + "' dihapus.", otomatis: 2000 }
                                 : { jenis: "galat", pesan: "Zona gagal dihapus. Muat ulang halaman lalu coba lagi." });
            });
          });
      });
      li.appendChild(kiri);
      li.appendChild(hapus);
      daftar.appendChild(li);
    });
    gambar();
  }

  function ukurKanvas() {
    // perbesar gambar agar memenuhi panel dengan rasio aspek tetap
    var skala = Math.min(editor.clientWidth / img.naturalWidth, editor.clientHeight / img.naturalHeight);
    img.style.width = Math.round(img.naturalWidth * skala) + "px";
    img.style.height = Math.round(img.naturalHeight * skala) + "px";
    canvas.width = img.clientWidth;
    canvas.height = img.clientHeight;
    canvas.style.left = img.offsetLeft + "px";
    canvas.style.top = img.offsetTop + "px";
    gambar();
  }

  function poligon(pts, warna, isi, tutup) {
    if (!pts.length) return;
    ctx.beginPath();
    pts.forEach(function (p, i) {
      var x = p[0] * canvas.width, y = p[1] * canvas.height;
      if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
    });
    if (tutup) ctx.closePath();
    if (isi) { ctx.globalAlpha = 0.22; ctx.fillStyle = warna; ctx.fill(); ctx.globalAlpha = 1; }
    ctx.strokeStyle = warna;
    ctx.lineWidth = 2;
    ctx.stroke();
  }

  function gambar() {
    if (!editing) return;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    zonaAda.forEach(function (z) {
      poligon(z.titik, WARNA[z.jenis], true, true);
      ctx.fillStyle = WARNA[z.jenis];
      ctx.font = "600 13px 'Plus Jakarta Sans', system-ui, sans-serif";
      ctx.fillText(z.nama, z.titik[0][0] * canvas.width + 4, z.titik[0][1] * canvas.height + 14);
    });
    var warna = WARNA[document.getElementById("zona-jenis").value];
    poligon(titik, warna, titik.length >= 3, titik.length >= 3);
    titik.forEach(function (p) {
      ctx.beginPath();
      ctx.arc(p[0] * canvas.width, p[1] * canvas.height, 4, 0, Math.PI * 2);
      ctx.fillStyle = "#fff";
      ctx.fill();
      ctx.strokeStyle = warna;
      ctx.stroke();
    });
  }

  function bukaEditor() {
    pesan("Mengambil gambar dari sumber…");
    editing = true;
    titik = [];
    document.getElementById("video").classList.add("hidden");
    document.getElementById("video-empty").classList.add("hidden");
    editor.classList.remove("hidden");
    bar.classList.remove("hidden");
    btnAtur.disabled = true;
    // editor ada di atas halaman, tombolnya di bawah kolom kanan: gulir ke gambar
    var gerak = window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth";
    document.querySelector(".monitor").scrollIntoView({ block: "start", behavior: gerak });
    fetch("/kamera/pratinjau?" + query(), { cache: "no-store" })
      .then(function (r) {
        if (!r.ok) return r.text().then(function (t) { throw new Error(t); });
        return r.blob();
      })
      .then(function (blob) {
        img.onload = function () { ukurKanvas(); pesan(INFO_AWAL); };
        img.src = URL.createObjectURL(blob);
      })
      .catch(function (e) { pesan(e.message || "Gambar sumber tidak dapat diambil.", true); });
  }

  function tutupEditor() {
    editing = false;
    titik = [];
    editor.classList.add("hidden");
    bar.classList.add("hidden");
    btnAtur.disabled = false;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    document.dispatchEvent(new CustomEvent("editor-zona-tutup"));
  }

  canvas.addEventListener("click", function (e) {
    var r = canvas.getBoundingClientRect();
    var x = (e.clientX - r.left) / r.width, y = (e.clientY - r.top) / r.height;
    if (x < 0 || x > 1 || y < 0 || y > 1) return;
    titik.push([Math.round(x * 10000) / 10000, Math.round(y * 10000) / 10000]);
    pesan(titik.length < 3 ? "Titik " + titik.length + " ditambahkan. Minimal 3 titik." :
      titik.length + " titik. Beri nama dan jenis, lalu tekan Simpan zona.");
    gambar();
  });
  document.getElementById("btn-undo").addEventListener("click", function () { titik.pop(); gambar(); });
  document.getElementById("zona-jenis").addEventListener("change", gambar);
  document.getElementById("btn-tutup-editor").addEventListener("click", tutupEditor);
  document.getElementById("btn-simpan-zona").addEventListener("click", function () {
    var s = sumber();
    var body = { jenis: s.jenis, nilai: s.nilai, nama: document.getElementById("zona-nama").value,
                 jenis_zona: document.getElementById("zona-jenis").value, titik: titik,
                 jam_mulai: document.getElementById("zona-jam-mulai").value,
                 jam_selesai: document.getElementById("zona-jam-selesai").value };
    fetch("/api/zona", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) })
      .then(function (r) { return r.json().then(function (d) { return { ok: r.ok, d: d }; }); })
      .then(function (res) {
        if (!res.ok) {
          pesan(res.d.galat || "Zona gagal disimpan.", true);
          window.dialog({ jenis: "galat", judul: "Zona belum tersimpan", pesan: res.d.galat || "Zona gagal disimpan." });
          return;
        }
        window.dialog({ jenis: "sukses", pesan: "Zona '" + body.nama + "' tersimpan.", otomatis: 2000 });
        pesan("Zona '" + body.nama + "' tersimpan. Gambar zona berikutnya, atau tekan Selesai menggambar.");
        titik = [];
        document.getElementById("zona-nama").value = "";
        muatZona();
      });
  });
  btnAtur.addEventListener("click", bukaEditor);
  window.addEventListener("resize", function () { if (editing) ukurKanvas(); });

  // muat ulang daftar zona saat sumber berubah
  document.querySelectorAll('input[name="jenis"]').forEach(function (r) {
    r.addEventListener("change", function () { if (editing) tutupEditor(); muatZona(); });
  });
  ["nilai_webcam", "nilai_berkas"].forEach(function (id) {
    document.getElementById(id).addEventListener("change", function () { if (editing) tutupEditor(); muatZona(); });
  });
  var tunda;
  document.getElementById("nilai_stream").addEventListener("input", function () {
    clearTimeout(tunda);
    tunda = setTimeout(muatZona, 600);
  });
  window.zonaEditorAktif = function () { return editing; };
  muatZona();
})();
