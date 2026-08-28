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
    python scripts/cast_generator.py "airdrop season" --json > casts.json

Output: teks (default) atau JSON (--json). Tidak memposting apa pun — murni generate.
"""
import argparse
import json
import os
import sys
import urllib.request
import urllib.error

BASE_URL = os.getenv("LLM_BASE_URL", "https://api.justwoker.icu/v1").rstrip("/")
API_KEY = os.getenv("LLM_API_KEY", "")
MODEL = os.getenv("LLM_MODEL", "claude-opus-4-8")

MAX_CAST_LEN = 320  # batas karakter Farcaster

TONES = {
    "default": "santai tapi berbobot, khas builder crypto yang paham teknis",
    "degen": "energik, playful, sedikit meme-y, khas degen CT tapi tetap ada insight",
    "thoughtful": "reflektif, thread-leader, memancing diskusi, tanpa hype kosong",
    "educational": "menjelaskan 1 konsep dengan analogi sederhana, ramah pemula",
}


def build_prompt(keyword: str, count: int, tone: str, lang: str) -> str:
    tone_desc = TONES.get(tone, TONES["default"])
    lang_line = "Bahasa Indonesia" if lang == "id" else "English"
    return f"""Kamu adalah seorang yapper Farcaster berpengalaman. Buatkan {count} cast (post) ORIGINAL
dari keyword/topik berikut. Setiap cast HARUS:
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


def call_llm(prompt: str, timeout: int = 60) -> str:
    if not API_KEY:
        sys.exit("ERROR: LLM_API_KEY belum di-set (export LLM_API_KEY=sk-...).")
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.9,
        "max_tokens": 1200,
    }
    req = urllib.request.Request(
        f"{BASE_URL}/chat/completions",
        data=json.dumps(payload).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {API_KEY}",
            "User-Agent": "farcaster-yapper/1.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.load(r)
    except urllib.error.HTTPError as e:
        sys.exit(f"ERROR HTTP {e.code}: {e.read().decode()[:200]}")
    except Exception as e:
        sys.exit(f"ERROR memanggil LLM: {e}")
    return data["choices"][0]["message"]["content"]


def parse_casts(raw: str) -> list:
    """Ambil array casts dari respons LLM, toleran terhadap teks pembungkus."""
    raw = raw.strip()
    # buang code fence kalau ada
    if raw.startswith("```"):
        raw = raw.split("```", 2)[1] if raw.count("```") >= 2 else raw.strip("`")
        if raw.lstrip().startswith("json"):
            raw = raw.lstrip()[4:]
    # cari objek JSON pertama
    start = raw.find("{")
    end = raw.rfind("}")
    if start != -1 and end != -1:
        try:
            obj = json.loads(raw[start:end + 1])
            casts = obj.get("casts", [])
            if isinstance(casts, list) and casts:
                return [c.strip() for c in casts if isinstance(c, str) and c.strip()]
        except json.JSONDecodeError:
            pass
    # fallback: pisah per baris non-kosong
    return [ln.strip("-• ").strip() for ln in raw.splitlines() if ln.strip()]


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

    # enforce batas panjang: potong yang kepanjangan (jaga-jaga)
    clean = []
    for c in casts:
        if len(c) > MAX_CAST_LEN:
            c = c[:MAX_CAST_LEN - 1].rstrip() + "…"
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
