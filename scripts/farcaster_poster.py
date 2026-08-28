#!/usr/bin/env python3
"""
farcaster_poster.py — (OPSIONAL) Posting cast ke Farcaster lewat Neynar API.

Ini TERPISAH dari generator. Default project cuma GENERATE cast; posting otomatis
harus kamu aktifkan sendiri karena butuh signer_uuid + API key Neynar (berbayar/limit).

ENV yang dibutuhkan:
    NEYNAR_API_KEY     API key dari https://neynar.com
    NEYNAR_SIGNER_UUID signer_uuid akun Farcaster kamu (dari Neynar managed signers)

Contoh:
    echo "gm farcaster" | python scripts/farcaster_poster.py
    python scripts/farcaster_poster.py --text "cast dari script"
    python scripts/farcaster_poster.py --dry-run --text "cek dulu tanpa posting"

SAFETY: pakai --dry-run untuk melihat payload tanpa benar-benar memposting.
Jangan pernah commit NEYNAR_API_KEY / SIGNER_UUID ke repo.
"""
import argparse
import json
import os
import sys
import urllib.request
import urllib.error
import urllib.parse

NEYNAR_API_KEY = os.getenv("NEYNAR_API_KEY", "")
SIGNER_UUID = os.getenv("NEYNAR_SIGNER_UUID", "")
NEYNAR_USERNAME = os.getenv("NEYNAR_USERNAME", "")
CAST_ENDPOINT = "https://api.neynar.com/v2/farcaster/cast"
USER_BY_USERNAME_ENDPOINT = "https://api.neynar.com/v2/farcaster/user/by_username"
MAX_CAST_LEN = 320


def _neynar_headers() -> dict:
    return {
        "Content-Type": "application/json",
        "api_key": NEYNAR_API_KEY,    # header Neynar v2 (lama)
        "x-api-key": NEYNAR_API_KEY,  # header versi baru
    }


def resolve_username(username: str, timeout: int = 20) -> dict:
    """Resolve @username Farcaster -> info user (fid, dll) via Neynar.

    CATATAN: ini hanya untuk verifikasi identitas / menampilkan 'posting sebagai siapa'.
    Posting cast tetap butuh signer_uuid — username saja TIDAK bisa memposting.
    """
    username = username.lstrip("@").strip()
    if not username:
        return {}
    if not NEYNAR_API_KEY:
        sys.exit("ERROR: NEYNAR_API_KEY dibutuhkan untuk resolve username.")
    qs = urllib.parse.urlencode({"username": username})
    req = urllib.request.Request(
        f"{USER_BY_USERNAME_ENDPOINT}?{qs}",
        headers=_neynar_headers(),
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.load(r)
    except urllib.error.HTTPError as e:
        sys.exit(f"ERROR resolve username '{username}' HTTP {e.code}: {e.read().decode()[:200]}")
    except Exception as e:
        sys.exit(f"ERROR resolve username '{username}': {e}")
    user = data.get("user", data)
    return {
        "fid": user.get("fid"),
        "username": user.get("username"),
        "display_name": user.get("display_name"),
        "follower_count": user.get("follower_count"),
    }


def post_cast(text: str, dry_run: bool = False, username: str = "", timeout: int = 30) -> dict:
    text = text.strip()
    if not text:
        sys.exit("ERROR: teks cast kosong.")
    if len(text) > MAX_CAST_LEN:
        sys.exit(f"ERROR: cast {len(text)} char > {MAX_CAST_LEN} (batas Farcaster).")

    # Opsional: resolve username -> tampilkan akan posting sebagai siapa
    identity = {}
    uname = username or NEYNAR_USERNAME
    if uname:
        identity = resolve_username(uname)

    payload = {"signer_uuid": SIGNER_UUID, "text": text}

    if dry_run:
        out = {"dry_run": True, "would_post": payload}
        if identity:
            out["posting_as"] = identity
        return out

    if not NEYNAR_API_KEY or not SIGNER_UUID:
        sys.exit("ERROR: set NEYNAR_API_KEY dan NEYNAR_SIGNER_UUID dulu. "
                 "(username saja tidak cukup untuk memposting.)")

    req = urllib.request.Request(
        CAST_ENDPOINT,
        data=json.dumps(payload).encode(),
        headers=_neynar_headers(),
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            result = json.load(r)
    except urllib.error.HTTPError as e:
        sys.exit(f"ERROR HTTP {e.code}: {e.read().decode()[:300]}")
    except Exception as e:
        sys.exit(f"ERROR posting ke Neynar: {e}")
    if identity:
        result["posting_as"] = identity
    return result


def main():
    ap = argparse.ArgumentParser(description="Post 1 cast ke Farcaster via Neynar.")
    ap.add_argument("--text", help="Teks cast. Jika kosong, dibaca dari stdin.")
    ap.add_argument("--username", "-u", default="",
                    help="(Opsional) username Farcaster untuk verifikasi identitas / "
                         "resolve FID. TIDAK menggantikan signer_uuid untuk posting.")
    ap.add_argument("--whoami", action="store_true",
                    help="Hanya resolve username -> FID lalu keluar (tanpa posting).")
    ap.add_argument("--dry-run", action="store_true", help="Tampilkan payload tanpa posting.")
    args = ap.parse_args()

    # Mode whoami: cukup resolve username, tidak butuh teks
    if args.whoami:
        uname = args.username or NEYNAR_USERNAME
        if not uname:
            sys.exit("ERROR: --whoami butuh --username atau NEYNAR_USERNAME.")
        print(json.dumps(resolve_username(uname), ensure_ascii=False, indent=2))
        return

    text = args.text if args.text else sys.stdin.read()
    result = post_cast(text, dry_run=args.dry_run, username=args.username)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
