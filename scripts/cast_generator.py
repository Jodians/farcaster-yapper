#!/usr/bin/env python3
"""
cast_generator.py — Generate Farcaster casts otomatis dari sebuah keyword.

Alur: kasih 1 keyword/topik  ->  LLM (OpenAI-compatible endpoint)  ->  N variasi cast
siap-posting (<= 320 karakter, gaya "yapping" CT/crypto-Twitter, ada hook + value + 1-2 hashtag).

Endpoint LLM dikonfigurasi lewat ENV (default: justwoker.icu, OpenAI-compatible):
    LLM_BASE_URL   (default https://api.justwoker.icu/v1)
    LLM_API_KEY    (WAJIB)
    LLM_MODEL      (default claude-opus-4-8)

Contoh:
    python scripts/cast_generator.py "restaking di ethereum"
    python scripts/cast_generator.py "monad testnet" --count 5 --tone degen
    python scripts/cast_generator.py "airdrop season" --lang id --json > casts.json

Output: teks (default) atau JSON (--json). Tidak memposting apa pun — murni generate.
"""
import argparse
import json
import os
import sys
import urllib.request
import urllib.error

# Load .env automatically (works on Windows + Linux without `export`).
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass  # dotenv optional; fall back to real env vars / manual export

BASE_URL = os.getenv("LLM_BASE_URL", "https://api.justwoker.icu/v1").rstrip("/")
API_KEY = os.getenv("LLM_API_KEY", "")
MODEL = os.getenv("LLM_MODEL", "claude-opus-4-8")

MAX_CAST_LEN = 320  # batas karakter Farcaster

TONES = {
    "default": "santai tapi berbobot, khas builder crypto yang paham teknis",
    "degen": "enerjik, playful, sedikit meme-y, khas degen CT tapi tetap ada insight",
    "thoughtful": "reflektif, thread-leader, memancing diskusi, tanpa hype kosong",
    "educational": "menjelaskan 1 konsep dengan analogi sederhana, ramah pemula",
}

SYSTEM = (
    "Kamu adalah yapper Farcaster berpengalaman di niche crypto/CT. "
    "Tugasmu HANYA membalas dalam JSON valid. Jangan pernah menambah teks di luar JSON."
)


def build_prompt(keyword: str, count: int, tone: str, lang: str) -> str:
    tone_desc = TONES.get(tone, TONES["default"])
    lang_line = "Bahasa Indonesia" if lang == "id" else "English"
    return f"""Buatkan {count} cast (post) ORIGINAL dari keyword/topik berikut. Setiap cast HARUS:
- Maksimal {MAX_CAST_LEN} karakter (WAJIB, hitung dengan cermat).
- Ditulis dalam {lang_line}.
- Gaya: {tone_desc}.
- Punya HOOK di kalimat pertama (bikin orang berhenti scroll).
- Berisi 1 insight / opini / value nyata (bukan hype kosong, bukan clickbait).
- Boleh pakai 1-2 hashtag relevan, TANPA @mention akun asli, TANPA link.
- Jangan pakai emoji berlebihan (maks 1-2).
- Setiap cast berdiri sendiri (bukan thread bersambung).

Keyword/topik: "{keyword}"

Balas HANYA dalam format JSON valid berikut (tanpa teks lain):
{{"casts": ["cast pertama", "cast kedua", ...]}}"""


def call_llm(prompt: str, timeout: int = 90) -> str:
    if not API_KEY:
        sys.exit("ERROR: LLM_API_KEY belum di-set. Isi di .env atau export LLM_API_KEY=sk-...")
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.9,
        "max_tokens": 1200,
        "response_format": {"type": "json_object"},
    }
    req = urllib.request.Request(
        f"{BASE_URL}/chat/completions",
        data=json.dumps(payload).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {API_KEY}",
            "User-Agent": "farcaster-yapper/1.1",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.load(r)
    except urllib.error.HTTPError as e:
        sys.exit(f"ERROR HTTP {e.code}: {e.read().decode()[:300]}")
    except Exception as e:
        sys.exit(f"ERROR memanggil LLM: {e}")
    return data["choices"][0]["message"]["content"]


def parse_casts(raw: str) -> list:
    """Ambil array casts dari respons LLM, toleran terhadap berbagai format."""
    if not raw:
        return []
    raw = raw.strip()

    # Tangani deepseek-r1 style <think>...</think> block di awal.
    if "<think>" in raw and "</think>" in raw:
        raw = raw.split("</think>", 1)[1].strip()
    # Tangani markdown code fence.
    if "```" in raw:
        # ambil bagian dalam fence pertama
        parts = raw.split("```")
        for p in parts:
            p = p.strip()
            if p.lower().startswith("json"):
                p = p[4:].strip()
            if p.startswith("{"):
                raw = p
                break
    # Cari objek JSON pertama.
    start = raw.find("{")
    end = raw.rfind("}")
    if start != -1 and end != -1:
        try:
            obj = json.loads(raw[start:end + 1])
            casts = obj.get("casts", [])
            if isinstance(casts, list):
                out = [c.strip() for c in casts if isinstance(c, str) and c.strip()]
                if out:
                    return out
        except json.JSONDecodeError:
            pass
    # Fallback: pisah per baris non-kosong.
    return [ln.strip("-• \n") for ln in raw.splitlines() if ln.strip() and not ln.strip().startswith("{")]


def main():
    ap = argparse.ArgumentParser(description="Generate Farcaster casts dari keyword.")
    ap.add_argument("keyword", help="Keyword/topik yang mau di-cast (bungkus pakai kutip).")
    ap.add_argument("--count", "-n", type=int, default=3, help="Jumlah cast (default 3).")
    ap.add_argument("--tone", "-t", default="default",
                    choices=list(TONES.keys()), help="Gaya penulisan.")
    ap.add_argument("--lang", "-l", default="id", choices=["id", "en"], help="Bahasa (id/en).")
    ap.add_argument("--json", action="store_true", help="Output JSON, bukan teks.")
    args = ap.parse_args()

    prompt = build_prompt(args.keyword, args.count, args.tone, args.lang)
    raw = call_llm(prompt)
    casts = parse_casts(raw)

    if not casts:
        sys.exit("ERROR: LLM tidak mengembalikan cast yang bisa di-parse. Coba lagi atau ganti model.")

    # enforce batas panjang: potong yang kepanjangan (jaga-jaga)
    clean = []
    for c in casts:
        if len(c) > MAX_CAST_LEN:
            c = c[:MAX_CAST_LEN - 1].rstrip() + "\u2026"
        clean.append(c)

    if args.json:
        print(json.dumps({"keyword": args.keyword, "tone": args.tone,
                           "lang": args.lang, "casts": clean}, ensure_ascii=False, indent=2))
    else:
        print(f"\n=== {len(clean)} CAST untuk: \"{args.keyword}\" (tone={args.tone}) ===\n")
        for i, c in enumerate(clean, 1):
            print(f"[{i}] ({len(c)} char)\n{c}\n")


if __name__ == "__main__":
    main()
