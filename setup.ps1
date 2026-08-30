# setup.ps1 — Setup cepat farcaster-yapper di Windows (PowerShell)
# Jalankan:  .\setup.ps1   (dari folder repo ini)
# Setelah jalan, edit .env lalu:  python scripts/cast_generator.py "keyword"

$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $repo

Write-Output "== farcaster-yapper setup =="

# 1. virtual env
if (-not (Test-Path .venv)) {
    python -m venv .venv
    Write-Output "[ok] venv dibuat"
} else {
    Write-Output "[skip] venv sudah ada"
}

# 2. activate + install deps
& ".\.venv\Scripts\Activate.ps1"
pip install -r requirements.txt 2>&1 | Select-Object -Last 3

# 3. .env dari template (jangan timpa kalau sudah ada)
if (-not (Test-Path .env)) {
    Copy-Item .env.example .env
    Write-Output "[ok] .env dibuat dari .env.example — ISI LLM_API_KEY sekarang"
    Write-Output "      Buka .env di editor, ganti sk-xxx...xxxx dengan key lo."
} else {
    Write-Output "[skip] .env sudah ada"
}

Write-Output ""
Write-Output "Cara jalanin (setelah isi .env):"
Write-Output "  .\.venv\Scripts\Activate.ps1"
Write-Output "  python scripts/cast_generator.py `"restaking di ethereum`" --lang id"
