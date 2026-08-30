# 🟣 Farcaster Yapper

Generate **cast** (post Farcaster) otomatis cukup dari **satu keyword**. Kasih topik,
dapat beberapa variasi cast siap-posting (≤ 320 karakter, gaya *yapping* CT/crypto,
ada hook + insight + hashtag). Bisa dijalankan manual, terjadwal (GitHub Actions),
atau di-pipe ke auto-post lewat Neynar.

> ⚠️ **Bukan saran finansial.** Tool ini hanya bantu bikin konten. Selalu review
> cast sebelum posting. Jangan spam.

---

## ✨ Fitur

- **1 keyword → N cast.** `python scripts/cast_generator.py "restaking"`
- **Kontrol gaya** (`--tone`): `default`, `degen`, `thoughtful`, `educational`.
- **Dwibahasa** (`--lang id|en`).
- **Batas 320 karakter** dijaga otomatis.
- **Output teks atau JSON** (`--json`) untuk dipipeline.
- **Auto-post opsional** ke Farcaster via Neynar (default OFF — aman).
- **GitHub Actions** built-in: manual (isi keyword) atau terjadwal.
- **Auto-load `.env`** — jalan di Windows & Linux tanpa `export` manual (butuh `python-dotenv`, sudah di `requirements.txt`).

---

## 🚀 Cara pakai (lokal)

### Windows (PowerShell) — paling gampang

```powershell
.\setup.ps1                       # bikin venv + install dep + buat .env
# edit .env -> isi LLM_API_KEY
.\.venv\Scripts\Activate.ps1
python scripts/cast_generator.py "restaking di ethereum" --lang id
```

### Linux / macOS

```bash
cp .env.example .env
# edit .env -> isi LLM_API_KEY
python3 scripts/cast_generator.py "monad testnet"
python3 scripts/cast_generator.py "airdrop season" --count 5 --tone degen
python3 scripts/cast_generator.py "restaking di ethereum" --lang id --json > casts.json
```

> Catatan: `.env` dibaca otomatis oleh script (via `python-dotenv`). Kamu tidak
> perlu `export` variabel manual — cukup isi file `.env`.

Contoh output:

```
=== 3 CAST untuk: "monad testnet" (tone=default) ===

[1] (188 char)
Monad testnet bukan sekadar "EVM cepat". Parallel execution-nya
bikin dev gak perlu rewrite kontrak — tetap Solidity, tapi throughput
naik drastis. Ini yang bikin migrasi jadi murah. #Monad

[2] ...
```

---

## 🔁 Workflow (arsitektur)

```
        ┌─────────────┐
 keyword│  kamu ketik │
        └──────┬──────┘
               ▼
   scripts/cast_generator.py
   (prompt → LLM OpenAI-compatible)
               ▼
        casts.json / stdout        ← REVIEW di sini (default berhenti)
               ▼ (opsional, AUTO_POST=true)
   scripts/farcaster_poster.py
   (Neynar API → Farcaster)
```

**Default = berhenti di generate** (kamu review manual). Auto-post harus
diaktifkan sengaja.

### Otomatisasi via GitHub Actions

File: `.github/workflows/auto-cast.yml`

1. **Repo → Settings → Secrets and variables → Actions**, tambah:
   - `LLM_API_KEY` (wajib), `LLM_BASE_URL`, `LLM_MODEL` (opsional)
   - `NEYNAR_API_KEY`, `NEYNAR_SIGNER_UUID` (hanya jika mau auto-post)
2. **Manual run:** tab **Actions → Auto Cast → Run workflow**, isi keyword.
3. **Terjadwal:** default `0 2 * * *` (09:00 WIB). Ubah cron sesukamu.
4. Hasil selalu di-upload sebagai artifact `casts.json` + tampil di log.
5. Untuk benar-benar posting: set `AUTO_POST: "true"` di workflow **dan** isi
   secret Neynar.

---

## 🔧 Konfigurasi (ENV)

| Variabel | Wajib | Default | Fungsi |
|----------|-------|---------|--------|
| `LLM_API_KEY` | ✅ | — | API key endpoint OpenAI-compatible |
| `LLM_BASE_URL` | — | `https://api.justwoker.icu/v1` | Base URL LLM |
| `LLM_MODEL` | — | `claude-opus-4-8` | Nama model |
| `NEYNAR_API_KEY` | posting saja | — | API key Neynar |
| `NEYNAR_SIGNER_UUID` | posting saja | — | signer akun Farcaster (WAJIB buat posting) |
| `NEYNAR_USERNAME` | — | — | username FC (tanpa @) untuk verifikasi identitas / resolve FID |

> **Username vs signer_uuid:** `NEYNAR_USERNAME` cuma dipakai untuk *menunjukkan
> posting sebagai siapa* (resolve FID via `--whoami`). Untuk benar-benar
> memposting, tetap butuh `NEYNAR_SIGNER_UUID` — username saja tidak cukup
> (itu batasan protokol Farcaster: post harus ditandatangani signer).

Cek identitas tanpa posting:

```bash
python scripts/farcaster_poster.py --whoami --username jodi
# atau set NEYNAR_USERNAME=jodi di .env lalu:
python scripts/farcaster_poster.py --whoami
```

---

## 📁 Struktur

```text
farcaster-yapper/
├── scripts/
│   ├── cast_generator.py   # keyword → cast (inti)
│   └── farcaster_poster.py # (opsional) post ke Farcaster via Neynar
├── .github/workflows/
│   └── auto-cast.yml       # Actions: manual + terjadwal
├── .env.example
├── .gitignore
├── requirements.txt        # python-dotenv (auto-load .env)
├── setup.ps1               # helper setup Windows (PowerShell)
└── README.md
```

---

## 🔧 Perbaikan & robustnes

- **System role + `response_format: json_object`** — model (incl. `claude-opus-4-8`)
  patuh instruksi & balik JSON bersih, bukan teks campur.
- **Parser toleran** — tangani `deepseek-r1` `<think>` block, markdown fence,
  maupun output berupa teks biasa (fallback per-baris).
- **Auto-load `.env`** via `python-dotenv` — jalan di Windows tanpa `export`.
- **Stdin di poster di-strip** — newline gak makan batas 320 karakter.
- **Error jelas** kalau LLM gagal balik cast yang bisa di-parse.

---

## 🛡️ Catatan keamanan

- **Jangan commit `.env`** (sudah di `.gitignore`).
- Auto-post **OFF by default**. Aktifkan sadar-sadar.
- Selalu **review cast** sebelum publish — LLM bisa halu.
- Hormati aturan komunitas Farcaster; jangan spam/manipulatif.

MIT License.
