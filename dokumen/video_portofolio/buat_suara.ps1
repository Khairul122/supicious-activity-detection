# Membuat suara narasi video portofolio dengan VoiceStudio (localhost:3900).
# Hasil: folder suara\01.wav, 02.wav, ... dan suara\durasi.json
# Jalankan lewat "Buat suara narasi.cmd" (Indonesia) atau "Buat suara narasi EN.cmd" (Inggris), atau:
#   powershell -ExecutionPolicy Bypass -File buat_suara.ps1 [-BerkasNaskah naskah_en.json] [-FolderSuara suara_en] [-Ulang]
param(
    [string]$Alamat = "http://localhost:3900",
    [string]$BerkasNaskah = "naskah.json",
    [string]$FolderSuara = "suara",
    [switch]$Ulang
)
$ErrorActionPreference = "Stop"
$folder = Split-Path -Parent $MyInvocation.MyCommand.Path
$keluar = Join-Path $folder $FolderSuara
New-Item -ItemType Directory -Force -Path $keluar | Out-Null

function Durasi-Wav([string]$jalur) {
    $b = [System.IO.File]::ReadAllBytes($jalur)
    if ($b.Length -lt 44 -or [System.Text.Encoding]::ASCII.GetString($b, 0, 4) -ne "RIFF") { return -1 }
    $byteRate = [BitConverter]::ToInt32($b, 28)
    $i = 12
    while ($i -lt $b.Length - 8) {
        $nama = [System.Text.Encoding]::ASCII.GetString($b, $i, 4)
        $ukuran = [BitConverter]::ToInt32($b, $i + 4)
        if ($nama -eq "data") { return [math]::Round($ukuran / $byteRate, 3) }
        $i += 8 + $ukuran
    }
    return -1
}

Write-Host "1. Memeriksa VoiceStudio di $Alamat ..."
try {
    Invoke-WebRequest -UseBasicParsing -Uri "$Alamat/health" -TimeoutSec 10 | Out-Null
} catch {
    Write-Host "   VoiceStudio belum berjalan. Buka aplikasi VoiceStudio, tunggu model OmniVoice siap, lalu jalankan skrip ini lagi." -ForegroundColor Red
    exit 1
}
Write-Host "   VoiceStudio siap." -ForegroundColor Green

$naskah = Get-Content -Raw -Encoding UTF8 (Join-Path $folder $BerkasNaskah) | ConvertFrom-Json
$s = $naskah.suara
$durasi = [ordered]@{}
$total = 0.0
Write-Host "2. Membuat $($naskah.kalimat.Count) potong suara ..."
foreach ($k in $naskah.kalimat) {
    $wav = Join-Path $keluar ("{0}.wav" -f $k.id)
    if ((Test-Path $wav) -and -not $Ulang -and (Durasi-Wav $wav) -gt 0.3) {
        Write-Host ("   {0} sudah ada, dilewati" -f $k.id)
    } else {
        $isi = [ordered]@{
            model = $s.model; input = $k.ucapan; voice = $s.voice; instruct = $s.instruct
            language = $s.language; response_format = "wav"; speed = [double]$s.speed
            seed = [int]$s.seed; num_step = [int]$s.num_step
        }
        $json = $isi | ConvertTo-Json -Compress
        $bytes = [System.Text.Encoding]::UTF8.GetBytes($json)
        $sementara = "$wav.tmp"
        $coba = 0
        while ($true) {
            try {
                Invoke-WebRequest -UseBasicParsing -Method Post -Uri "$Alamat/v1/audio/speech" `
                    -ContentType "application/json; charset=utf-8" -Body $bytes -OutFile $sementara -TimeoutSec 600
                break
            } catch {
                $coba++
                if ($coba -ge 3) { Write-Host "   Gagal pada kalimat $($k.id): $($_.Exception.Message)" -ForegroundColor Red; exit 1 }
                Write-Host "   Kalimat $($k.id) gagal, mencoba lagi ($coba) ..." -ForegroundColor Yellow
                Start-Sleep -Seconds 5
            }
        }
        if ((Durasi-Wav $sementara) -le 0.3) { Write-Host "   File kalimat $($k.id) rusak atau kosong." -ForegroundColor Red; exit 1 }
        Move-Item -Force $sementara $wav
    }
    $d = Durasi-Wav $wav
    $durasi[$k.id] = $d
    $total += $d
    Write-Host ("   {0}  {1,6:N2} detik  {2}" -f $k.id, $d, $k.teks)
}
$durasi | ConvertTo-Json | Set-Content -Encoding UTF8 (Join-Path $keluar "durasi.json")
Write-Host ("3. Selesai. Total suara {0:N1} detik. File ada di folder: {1}" -f $total, $keluar) -ForegroundColor Green
Write-Host "   Dengarkan beberapa file. Jika ada yang kurang pas, hapus file itu lalu jalankan skrip lagi."
Write-Host "   Setelah itu kabari Claude bahwa suara sudah siap."
