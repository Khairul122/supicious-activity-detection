// Halaman Kamera: langkah pilih sumber dan mode, tayangan, umpan peringatan sesi, dan bunyi peringatan.
(function () {
  var halaman = document.getElementById("kamera");
  var video = document.getElementById("video");
  var empty = document.getElementById("video-empty");
  var modeSelect = document.getElementById("mode");
  var ubinMode = document.querySelectorAll("[data-mode]");
  var ringkas = document.getElementById("ringkas-pilihan");
  var NAMA_SUMBER = { webcam: "webcam", stream: "kamera CCTV", berkas: "rekaman" };
  var NAMA_MODE = { otomatis: "Otomatis", umum: "Umum", parkir: "Parkiran motor" };

  function $(id) { return document.getElementById(id); }
  function text(id, v) { $(id).textContent = v; }
  function pad(n) { return String(n).padStart(2, "0"); }
  function durasi(s) { s = Math.floor(s || 0); return pad(Math.floor(s / 3600)) + ":" + pad(Math.floor(s % 3600 / 60)) + ":" + pad(s % 60); }
  function jenisDipilih() { return document.querySelector('input[name="jenis"]:checked').value; }

  // ---------- langkah 1 dan 2 ----------
  function perbaruiRingkas() {
    var jenis = jenisDipilih();
    var nilai = ($("nilai_" + jenis) || {}).value || "";
    var sumber = jenis === "webcam" ? "webcam " + (nilai || "0") :
      jenis === "stream" ? (nilai ? "kamera CCTV" : "kamera CCTV (isi alamatnya dulu)") :
      (nilai ? "rekaman " + nilai : "rekaman (unggah video dulu)");
    ringkas.textContent = "Akan memantau " + sumber + (modeSelect.value === "otomatis"
      ? ". Mode dipilih otomatis dari gambar." : " dengan mode " + (NAMA_MODE[modeSelect.value] || "Umum") + ".");
  }
  function tampilkanIsian() {
    var jenis = jenisDipilih();
    document.querySelectorAll("[data-jenis]").forEach(function (f) {
      f.classList.toggle("hidden", f.dataset.jenis !== jenis);
    });
    perbaruiRingkas();
  }
  document.querySelectorAll('input[name="jenis"]').forEach(function (r) { r.addEventListener("change", tampilkanIsian); });
  ["nilai_webcam", "nilai_stream", "nilai_berkas"].forEach(function (id) {
    $(id).addEventListener("input", perbaruiRingkas);
    $(id).addEventListener("change", perbaruiRingkas);
  });
  tampilkanIsian();

  function sinkronMode() {
    ubinMode.forEach(function (b) { b.setAttribute("aria-checked", String(b.dataset.mode === modeSelect.value)); });
    perbaruiRingkas();
  }
  ubinMode.forEach(function (b) {
    b.addEventListener("click", function () {
      if (b.disabled) return;
      modeSelect.value = b.dataset.mode;
      modeSelect.dispatchEvent(new Event("change"));
    });
    b.addEventListener("keydown", function (e) {   // panah kiri/kanan berpindah pilihan, seperti radio
      if (e.key !== "ArrowRight" && e.key !== "ArrowLeft") return;
      var aktif = Array.prototype.filter.call(ubinMode, function (x) { return !x.disabled; });
      var i = aktif.indexOf(b) + (e.key === "ArrowRight" ? 1 : -1);
      var lain = aktif[(i + aktif.length) % aktif.length];
      if (lain && lain !== b) { lain.focus(); lain.click(); }
    });
  });
  modeSelect.addEventListener("change", sinkronMode);
  modeSelect.addEventListener("mode-sinkron", sinkronMode);
  sinkronMode();

  // ---------- unggah video dengan kemajuan ----------
  var inputUnggah = $("berkas-unggah");
  var progres = $("unggah-progres");
  inputUnggah.addEventListener("change", function () {
    var berkas = inputUnggah.files[0];
    if (!berkas) return;
    if (berkas.size > 500 * 1024 * 1024) {
      window.dialog({ jenis: "galat", judul: "Video terlalu besar", pesan: "Ukuran " + berkas.name + " melebihi 500 MB. Potong videonya atau pilih berkas lain." });
      inputUnggah.value = "";
      return;
    }
    var xhr = new XMLHttpRequest();
    xhr.open("POST", $("form-unggah").action);
    xhr.setRequestHeader("X-CSRF-Token", window.csrfToken);
    progres.classList.remove("hidden");
    xhr.upload.onprogress = function (e) {
      if (!e.lengthComputable) return;
      var persen = Math.round(100 * e.loaded / e.total);
      progres.firstElementChild.style.width = persen + "%";
      progres.setAttribute("aria-valuenow", persen);
      text("unggah-info", "Mengunggah " + berkas.name + ": " + persen + "%");
    };
    xhr.onload = function () { window.location.href = xhr.responseURL || window.location.href; };
    xhr.onerror = function () {
      progres.classList.add("hidden");
      text("unggah-info", "mp4, avi, mov, mkv, atau mpg. Maksimal 500 MB.");
      window.dialog({ jenis: "galat", judul: "Unggahan gagal", pesan: "Unggahan terputus. Periksa koneksi ke server lalu coba lagi." });
    };
    var data = new FormData();
    data.append("video", berkas);
    xhr.send(data);
  });

  // ---------- bunyi peringatan ----------
  var tombolBunyi = $("btn-bunyi");
  var bunyiAktif = false;
  try { bunyiAktif = localStorage.getItem("sad-bunyi") === "1"; } catch (e) { /* penyimpanan tidak tersedia */ }
  var audio = null;
  function aturTombolBunyi() {
    tombolBunyi.setAttribute("aria-pressed", String(bunyiAktif));
    tombolBunyi.title = bunyiAktif ? "Bunyi peringatan menyala. Klik untuk mematikan." : "Bunyi peringatan mati. Klik untuk menyalakan.";
    tombolBunyi.querySelector("use").setAttribute("href", bunyiAktif ? "#i-volume-2" : "#i-volume-x");
  }
  function bunyi() {
    if (!bunyiAktif) return;
    try {
      audio = audio || new (window.AudioContext || window.webkitAudioContext)();
      [0, 0.22].forEach(function (mulai, i) {
        var o = audio.createOscillator(), g = audio.createGain();
        o.frequency.value = i ? 660 : 880;
        g.gain.setValueAtTime(0.0001, audio.currentTime + mulai);
        g.gain.exponentialRampToValueAtTime(0.25, audio.currentTime + mulai + 0.02);
        g.gain.exponentialRampToValueAtTime(0.0001, audio.currentTime + mulai + 0.18);
        o.connect(g).connect(audio.destination);
        o.start(audio.currentTime + mulai);
        o.stop(audio.currentTime + mulai + 0.2);
      });
    } catch (e) { /* peramban tanpa Web Audio */ }
  }
  tombolBunyi.addEventListener("click", function () {
    bunyiAktif = !bunyiAktif;
    try { localStorage.setItem("sad-bunyi", bunyiAktif ? "1" : "0"); } catch (e) { /* abaikan */ }
    aturTombolBunyi();
    if (bunyiAktif) bunyi();   // contoh bunyi sekaligus membuka izin audio peramban
  });
  aturTombolBunyi();

  // ---------- umpan peringatan sesi ----------
  var umpan = $("umpan");
  var sesiUmpan = null, jumlahUmpan = -1, dikenal = null;

  function tombolNilai(p, nilai, label, kelas) {
    var b = document.createElement("button");
    b.type = "button";
    b.className = "btn btn-kecil " + kelas;
    b.textContent = label;
    b.setAttribute("aria-pressed", String(p.penilaian === nilai));
    b.addEventListener("click", function () {
      var baru = p.penilaian === nilai ? "" : nilai;
      window.nilaiPeringatan(p.id, baru).then(function () {
        p.penilaian = baru || null;
        b.parentNode.querySelectorAll("button").forEach(function (x) {
          x.setAttribute("aria-pressed", String(x === b && !!baru));
        });
      }).catch(function (e) { window.dialog({ jenis: "galat", judul: "Penilaian gagal", pesan: e.message }); });
    });
    return b;
  }

  function kartuUmpan(p) {
    var li = document.createElement("li");
    li.className = "umpan-item";
    var a = document.createElement("a");
    a.href = "/riwayat?sesi=" + p.sesi_id;
    a.className = "umpan-foto";
    var img = document.createElement("img");
    img.src = p.snapshot;
    img.alt = "Snapshot peringatan ID " + p.id_orang;
    img.loading = "lazy";
    a.appendChild(img);
    var tag = document.createElement("span");
    tag.className = "tag tag-k-" + (p.kategori || "lain");
    tag.textContent = p.kategori_label;
    a.appendChild(tag);
    li.appendChild(a);
    var isi = document.createElement("div");
    isi.className = "umpan-isi";
    var atas = document.createElement("div");
    atas.className = "umpan-atas";
    atas.innerHTML = "<strong></strong><span></span>";
    atas.firstChild.textContent = "ID " + p.id_orang;
    atas.lastChild.textContent = p.jam;
    isi.appendChild(atas);
    var alasan = document.createElement("p");
    alasan.textContent = p.alasan;
    isi.appendChild(alasan);
    var aksi = document.createElement("div");
    aksi.className = "nilai-aksi";
    aksi.appendChild(tombolNilai(p, "benar", "Benar", "btn-benar"));
    aksi.appendChild(tombolNilai(p, "alarm_palsu", "Alarm palsu", "btn-palsu"));
    isi.appendChild(aksi);
    li.appendChild(isi);
    return li;
  }

  function muatUmpan(sesi, umumkan) {
    fetch("/api/peringatan?limit=8&sesi=" + sesi, { cache: "no-store" })
      .then(function (r) { return r.json(); })
      .then(function (daftar) {
        if (dikenal && umumkan) {
          daftar.filter(function (p) { return !dikenal[p.id]; }).reverse().forEach(function (p) {
            window.toast("Peringatan baru: " + p.kategori_label, "ID " + p.id_orang + " pada " + p.jam + ". " + p.alasan,
              "bahaya", { gambar: p.snapshot, lama: 9000 });
            bunyi();
          });
        }
        dikenal = {};
        daftar.forEach(function (p) { dikenal[p.id] = true; });
        umpan.innerHTML = "";
        if (!daftar.length) {
          umpan.innerHTML = '<li class="kosong">Belum ada peringatan di sesi ini. Peringatan baru muncul di sini, dan berbunyi bila tombol bunyi di atas video menyala.</li>';
          return;
        }
        daftar.forEach(function (p) { umpan.appendChild(kartuUmpan(p)); });
      })
      .catch(function () { /* coba lagi pada status berikutnya */ });
  }

  // ---------- status kamera ----------
  var wasRunning = false;
  var modeDiumumkan = null, modeSesiAwal = null;
  document.addEventListener("editor-zona-tutup", function () { wasRunning = false; });

  document.addEventListener("status-kamera", function (e) {
    var s = e.detail;
    var keadaan = window.keadaanKamera(s);
    halaman.dataset.keadaan = keadaan;
    var editorAktif = window.zonaEditorAktif && window.zonaEditorAktif();
    var tampil = keadaan === "memantau" && !editorAktif;   // tayangan muncul setelah gambar pertama siap
    if (tampil && !wasRunning) video.src = video.dataset.src + "?t=" + Date.now();
    if (!tampil && wasRunning) video.removeAttribute("src");
    wasRunning = tampil;
    video.classList.toggle("hidden", !tampil);
    empty.classList.toggle("hidden", tampil || editorAktif);
    $("spinner").classList.toggle("hidden", !s.berjalan);
    $("empty-ikon").classList.toggle("hidden", !!s.berjalan);
    text("empty-title", s.berjalan ? (s.tahap || "Menyiapkan…") : "Kamera belum menyala");
    text("empty-text", s.berjalan ? "Kamera dan model sedang disiapkan. Biasanya beberapa detik." :
      "Pilih sumber video dan mode deteksi, lalu tekan Mulai pemantauan.");

    // bilah monitor
    var rekaman = s.jenis === "berkas";
    text("label-siaran-teks", keadaan === "memantau" ? (rekaman ? "Memutar rekaman" : "Langsung") :
      keadaan === "menyiapkan" ? "Menyiapkan" : "Tidak aktif");
    text("cam-sumber", s.berjalan ? (s.sumber || "") : "Belum ada sumber");
    var sus = s.orang.filter(function (o) { return o.kelas === "suspicious"; }).length;
    text("m-orang", s.orang.length);
    text("m-sus", sus);
    $("m-sus-wadah").classList.toggle("menyala", sus > 0);
    var parkir = s.mode === "parkir" && s.berjalan;
    $("m-motor-wadah").classList.toggle("hidden", !parkir);
    text("m-motor", parkir ? s.motor : 0);
    text("m-fps", s.berjalan ? s.fps.toFixed(1) + " fps" : "-");

    // panel sesi
    $("btn-mulai").disabled = s.berjalan;
    $("btn-hentikan").disabled = !s.berjalan;
    text("sesi-keadaan", keadaan === "memantau" ? "Sedang memantau" : keadaan === "menyiapkan" ? "Menyiapkan" : "Selesai");
    text("st-sesi", s.sesi_id || "-");
    text("st-durasi", durasi(s.durasi_sesi));
    text("st-peringatan", s.peringatan_sesi);
    $("st-peringatan").classList.toggle("sesi-nilai-bahaya", s.peringatan_sesi > 0);
    text("st-sumber", s.sumber || "-");
    text("st-mode-teks", s.mode_label || "-");
    text("st-mode-alasan", s.mode_alasan ? " karena " + s.mode_alasan : "");
    // umumkan hasil mode otomatis sekali per sesi
    if (s.mode_otomatis && s.mode !== "otomatis" && s.sesi_id && s.sesi_id !== modeDiumumkan) {
      modeDiumumkan = s.sesi_id;
      if (modeSesiAwal === s.sesi_id) {
        window.dialog({ jenis: "info", judul: "Mode otomatis: " + (NAMA_MODE[s.mode] || s.mode),
          pesan: "Dipilih karena " + s.mode_alasan + ". Bila kurang tepat, hentikan sesi lalu pilih mode di langkah 2.", otomatis: 6000 });
      }
    }
    if (s.mode_otomatis && s.mode === "otomatis" && s.sesi_id) modeSesiAwal = s.sesi_id;
    text("st-fps", s.berjalan ? s.fps.toFixed(1) + " fps" : "-");
    text("st-dilewati", s.dilewati || 0);
    text("st-perangkat", s.perangkat);
    text("st-motor", parkir ? s.motor + " (" + s.motor_parkir + " terparkir)" : "-");
    var galat = $("st-galat");
    galat.textContent = s.galat || "";
    galat.classList.toggle("hidden", !s.galat);

    // orang di layar
    var daftar = $("tbl-orang");
    daftar.innerHTML = "";
    if (!s.orang.length) {
      daftar.innerHTML = '<li class="kosong">' + (s.berjalan ? "Tidak ada orang di layar saat ini." : "Belum ada orang terdeteksi.") + "</li>";
    }
    s.orang.slice().sort(function (a, b) { return (b.kelas === "suspicious") - (a.kelas === "suspicious"); })
      .forEach(function (o) {
        var li = document.createElement("li");
        li.className = "orang orang-" + o.kelas;
        li.title = o.alasan || "";
        li.innerHTML = "<strong></strong><span></span><small></small>";
        li.children[0].textContent = "ID " + o.id;
        li.children[1].textContent = o.kelas === "suspicious" ? "Mencurigakan" : "Aman";
        li.children[2].textContent = o.durasi.toFixed(0) + " detik";
        daftar.appendChild(li);
      });

    text("judul-umpan-teks", s.berjalan ? "Peringatan sesi ini" : "Peringatan sesi terakhir");
    // umpan peringatan: muat ulang saat sesi berganti atau jumlah peringatan bertambah
    if (s.sesi_id) {
      $("umpan-semua").href = "/riwayat?sesi=" + s.sesi_id;
      if (s.sesi_id !== sesiUmpan) {
        sesiUmpan = s.sesi_id;
        jumlahUmpan = s.peringatan_sesi;
        dikenal = null;
        muatUmpan(s.sesi_id, false);
      } else if (s.peringatan_sesi !== jumlahUmpan) {
        jumlahUmpan = s.peringatan_sesi;
        muatUmpan(s.sesi_id, true);
      }
    }
  });
})();
