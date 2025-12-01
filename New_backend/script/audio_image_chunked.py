#!/usr/bin/env python3
"""
audio_image_chunked.py (updated)

Changes made:
 - Avoid chunking for files shorter than 8 hours (WAV detection). If WAV and duration < 8h, the file is encoded as a single image.
 - Fixed SHA field name mismatch (header now includes "sha256").
 - Added an 8-byte sentinel after ciphertext (AIMGEND1) to reliably detect end of encrypted payload inside the image and avoid trimming valid zero bytes.
 - More robust ciphertext extraction: looks for sentinel first, falls back to conservative trimming.
 - Some small logging improvements.

Notes:
 - Duration detection currently uses the builtin wave module (works for uncompressed WAV files). For other formats (mp3, flac, m4a) we cannot reliably detect duration without external libs (ffprobe/pydub).
 - Sentinel is appended unencrypted after ciphertext; probability of accidental collision is low but non-zero.

Usage: same as original script.
"""

import argparse
import os
import sys
import math
import json
import time
import binascii
import hashlib
import wave
from pathlib import Path
from typing import Optional, List, Tuple

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes

from PIL import Image
import numpy as np

# Try optional zstd
try:
    import zstandard as zstd
    HAVE_ZSTD = True
except Exception:
    HAVE_ZSTD = False

# -------------------- Config --------------------
HEADER_LEN = 1024         # bytes reserved at start of embedded payload for header JSON
MAX_WIDTH = 8192          # max image width (pixels); adjust if you want wider/narrower images
AESGCM_TAG_LEN = 16
DEFAULT_MAX_CHUNK_BYTES = 50 * 1024 * 1024  # 50 MB raw audio per image by default
PIXEL_BYTES = 3  # RGB -> 3 bytes/pixel
EIGHT_HOURS_SECONDS = 8 * 3600
SENTINEL = b'AIMGEND1'  # 8-byte sentinel appended after ciphertext to mark end (un-encrypted)
# ------------------------------------------------

# -------------------- Crypto helpers --------------------
def get_master_key(master_hex: Optional[str]) -> bytes:
    if master_hex:
        return binascii.unhexlify(master_hex)
    env = os.environ.get("AICARRIER_MASTER_KEY_HEX")
    if env:
        return binascii.unhexlify(env)
    raise RuntimeError("Master key required. Set env AICARRIER_MASTER_KEY_HEX or pass --master HEX")


def derive_user_key(master_key: bytes, user_id: str) -> bytes:
    hk = HKDF(algorithm=hashes.SHA256(), length=32, salt=None, info=b"AUDIO-IMG-V1")
    return hk.derive(master_key + user_id.encode("utf8"))


def sha256_hex(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

# -------------------- IO & packing helpers --------------------
def ceil_div(a:int,b:int)->int:
    return -(-a//b)


def bytes_to_image_pixels(payload: bytes, max_width: int = MAX_WIDTH) -> Tuple[np.ndarray,int,int]:
    """
    Pack payload bytes into RGB image pixels (3 bytes per pixel).
    Returns (arr, width, height) where arr is HxWx3 uint8 numpy array.
    """
    total_bytes = len(payload)
    pixels_needed = ceil_div(total_bytes, PIXEL_BYTES)
    width = int(min(max_width, math.ceil(math.sqrt(pixels_needed))))
    height = int(ceil_div(pixels_needed, width))
    arr = np.zeros((height, width, 3), dtype=np.uint8)
    # fill sequentially
    idx = 0
    for y in range(height):
        for x in range(width):
            if idx < total_bytes:
                b0 = payload[idx]; idx += 1
            else:
                b0 = 0
            if idx < total_bytes:
                b1 = payload[idx]; idx += 1
            else:
                b1 = 0
            if idx < total_bytes:
                b2 = payload[idx]; idx += 1
            else:
                b2 = 0
            arr[y,x,0] = b0
            arr[y,x,1] = b1
            arr[y,x,2] = b2
    return arr, width, height


def image_pixels_to_bytes(img_path: Path, expected_payload_len: Optional[int]=None) -> bytes:
    """
    Read an RGB image and convert the pixel bytes back to a bytes buffer (row-major R,G,B).
    If expected_payload_len is provided, slice exactly that many bytes from the flattened pixel stream.
    """
    img = Image.open(img_path).convert("RGB")
    arr = np.asarray(img, dtype=np.uint8)
    flat = arr.reshape(-1,3).astype(np.uint8).flatten().tobytes()
    if expected_payload_len is not None:
        if len(flat) < expected_payload_len:
            raise RuntimeError(f"Image payload too small: need {expected_payload_len} bytes, got {len(flat)}")
        return flat[:expected_payload_len]
    return flat

# -------------------- Duration helper (WAV only) --------------------
def get_wav_duration_seconds(path: Path) -> Optional[float]:
    try:
        with wave.open(str(path), 'rb') as wf:
            frames = wf.getnframes()
            rate = wf.getframerate()
            return frames / float(rate)
    except Exception:
        return None

# -------------------- Chunking / Encode pipeline --------------------
def build_payload_for_chunk(chunk_bytes: bytes, master_hex: Optional[str], user_id: str,
                            orig_filename: str, chunk_index:int, total_chunks:int, compress:bool=True) -> Tuple[bytes, dict]:
    """
    Build payload bytes for one chunk:
      4-byte header length + header_json (padded to HEADER_LEN) + nonce (12) + ciphertext + SENTINEL
    Returns: payload_bytes, header_metadata (dict)
    """
    master = get_master_key(master_hex)
    user_key = derive_user_key(master, user_id)
    aesgcm = AESGCM(user_key)
    nonce = os.urandom(12)

    header = {
        "magic":"AUDIO-IMG-V1",
        "version":1,
        "user_id": user_id,
        "orig_filename": orig_filename,
        "orig_chunk_index": chunk_index,
        "orig_total_chunks": total_chunks,
        "orig_chunk_size": len(chunk_bytes),
        "ts": int(time.time()),
    }

    # optional compression
    compressed_flag = False
    payload_plain = chunk_bytes
    if compress and HAVE_ZSTD:
        cctx = zstd.ZstdCompressor(level=3)
        compressed = cctx.compress(chunk_bytes)
        if len(compressed) < len(chunk_bytes):
            payload_plain = compressed
            compressed_flag = True

    header["compressed"] = bool(compressed_flag)
    # include sha256 of plaintext chunk for verification
    header["sha256"] = sha256_hex(chunk_bytes)

    header_json = json.dumps(header, separators=(",", ":"), sort_keys=True).encode("utf8")

    # encrypt: AAD = header_json
    ciphertext = aesgcm.encrypt(nonce, payload_plain, header_json)  # includes tag
    # build final payload: 4-byte hdrlen + hdr_json padded to HEADER_LEN + nonce (12) + ciphertext + sentinel
    payload = bytearray()
    payload.extend(len(header_json).to_bytes(4,"little"))
    payload.extend(header_json)
    if len(payload) < HEADER_LEN:
        payload.extend(b'\x00'*(HEADER_LEN - len(payload)))
    payload.extend(nonce)
    payload.extend(ciphertext)
    payload.extend(SENTINEL)

    metadata = {
        "chunk_index": chunk_index,
        "total_chunks": total_chunks,
        "header_json_len": len(header_json),
        "payload_len": len(payload),
        "sha256": header["sha256"],
        "compressed": compressed_flag,
    }
    return bytes(payload), metadata


def encode_streamed(input_file: Path, out_dir: Path, user_id: str,
                    max_chunk_bytes: int = DEFAULT_MAX_CHUNK_BYTES,
                    master_hex: Optional[str]=None, compress: bool=True):
    """
    Stream input_file, split into raw chunks (max_chunk_bytes), and for each chunk:
      - optionally compress,
      - encrypt,
      - pack into image and save as PNG.
    Output filenames: {basename}_part{index:04d}_of_{total:04d}.png
    Returns list of generated image paths.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    file_size = input_file.stat().st_size

    # Try to detect duration for WAV files and avoid chunking if under 8 hours
    duration = get_wav_duration_seconds(input_file) if input_file.suffix.lower() == ".wav" else None
    if duration is not None:
        print(f"[+] Detected WAV duration: {duration:.1f}s")
        if duration < EIGHT_HOURS_SECONDS:
            print("[+] Duration < 8 hours: encoding as single chunk (no split)")
            total_chunks = 1
            chunks = [input_file.read_bytes()]
        else:
            total_chunks = ceil_div(file_size, max_chunk_bytes)
            chunks = None
    else:
        total_chunks = ceil_div(file_size, max_chunk_bytes)
        chunks = None

    base = input_file.stem
    generated = []

    if chunks is not None:
        # already loaded single chunk
        for idx, chunk in enumerate(chunks):
            payload, meta = build_payload_for_chunk(chunk, master_hex, user_id, input_file.name, idx, total_chunks, compress=compress)
            arr, w, h = bytes_to_image_pixels(payload, max_width=MAX_WIDTH)
            img = Image.fromarray(arr, mode="RGB")
            out_name = out_dir / f"{base}_part{idx+1:04d}_of_{total_chunks:04d}.png"
            img.save(out_name, format="PNG", compress_level=9)
            print(f"    -> wrote image: {out_name}  (payload {len(payload)} bytes, image {w}x{h})")
            generated.append(out_name)
    else:
        with input_file.open("rb") as f:
            for idx in range(total_chunks):
                print(f"[+] Reading chunk {idx+1}/{total_chunks} ...")
                chunk = f.read(max_chunk_bytes)
                payload, meta = build_payload_for_chunk(chunk, master_hex, user_id, input_file.name, idx, total_chunks, compress=compress)
                # pack into pixels
                arr, w, h = bytes_to_image_pixels(payload, max_width=MAX_WIDTH)
                img = Image.fromarray(arr, mode="RGB")
                out_name = out_dir / f"{base}_part{idx+1:04d}_of_{total_chunks:04d}.png"
                img.save(out_name, format="PNG", compress_level=9)
                print(f"    -> wrote image: {out_name}  (payload {len(payload)} bytes, image {w}x{h})")
                generated.append(out_name)
    print(f"[+] Done. Generated {len(generated)} images in {out_dir}")
    return generated

# -------------------- Decode pipeline --------------------
def decode_images_to_file(indir: Path, out_file: Path, user_id: str, master_hex: Optional[str]=None):
    """
    Find all image files in indir that match pattern *_partXXXX_of_YYYY.png,
    sort by part index, extract payload bytes, decrypt each chunk and write to out_file in order.
    """
    # find png/tiff files
    imgs = sorted([p for p in Path(indir).iterdir() if p.suffix.lower() in (".png",".tiff",".tif")])
    if not imgs:
        raise RuntimeError("No PNG/TIFF images found in input directory")

    parts = []
    for p in imgs:
        try:
            flat = image_pixels_to_bytes(p, expected_payload_len=None)
            if len(flat) < HEADER_LEN:
                print(f"[!] skipping {p} (payload too small)")
                continue
            hdr_len = int.from_bytes(flat[0:4], "little")
            if hdr_len <=0 or hdr_len > HEADER_LEN:
                print(f"[!] skipping {p} (invalid header length {hdr_len})")
                continue
            header_json = flat[4:4+hdr_len]
            header = json.loads(header_json.decode('utf8'))
            if header.get("magic") != "AUDIO-IMG-V1":
                continue
            parts.append((p, header, flat))
        except Exception as e:
            print(f"[!] warning: could not parse {p}: {e}")
            continue

    if not parts:
        raise RuntimeError("No valid audio-image files found in directory")

    # Sort parts by chunk index
    parts_sorted = sorted(parts, key=lambda x: x[1]["orig_chunk_index"]) if parts else []
    total_expected = parts_sorted[0][1]["orig_total_chunks"]
    if len(parts_sorted) != total_expected:
        print(f"[!] Warning: found {len(parts_sorted)} chunks but header says total {total_expected}. Will proceed if indexes cover 0..total-1")

    out_file = Path(out_file)
    with out_file.open("wb") as outf:
        for (p, header, flat) in parts_sorted:
            print(f"[+] Decoding chunk {header['orig_chunk_index']+1}/{header['orig_total_chunks']} from {p.name}")
            rem = flat[HEADER_LEN:]
            if len(rem) < 12:
                raise RuntimeError(f"Insufficient payload after header in {p}")
            nonce = rem[0:12]
            # try to find sentinel to determine ciphertext boundary
            sentinel_idx = rem.find(SENTINEL)
            if sentinel_idx != -1:
                ciphertext = rem[12:sentinel_idx]
            else:
                # fallback: trim trailing zeros conservatively
                last_nonzero = len(rem) - 1
                while last_nonzero >= 12 and rem[last_nonzero] == 0:
                    last_nonzero -= 1
                ciphertext = rem[12:last_nonzero+1] if last_nonzero >= 12 else rem[12:]

            master = get_master_key(master_hex)
            user_key = derive_user_key(master, user_id)
            aesgcm = AESGCM(user_key)
            header_json = flat[4:4 + int.from_bytes(flat[0:4],"little")]
            try:
                plaintext = aesgcm.decrypt(nonce, bytes(ciphertext), header_json)
            except Exception as e:
                raise RuntimeError(f"Decryption failed for chunk {header['orig_chunk_index']}: {e}")
            if header.get("compressed", False):
                if not HAVE_ZSTD:
                    raise RuntimeError("Chunk is compressed but python zstandard not available for decompression")
                dctx = zstd.ZstdDecompressor()
                plaintext = dctx.decompress(plaintext)
            # verify sha
            if sha256_hex(plaintext) != header.get("sha256"):
                raise RuntimeError(f"SHA mismatch for chunk {header['orig_chunk_index']}")
            # write
            outf.write(plaintext)
            print(f"    wrote {len(plaintext)} bytes")
    print(f"[+] Reconstructed audio to {out_file} (size {out_file.stat().st_size} bytes)")

# -------------------- CLI --------------------
def build_cli():
    p = argparse.ArgumentParser(prog="audio_image_chunked")
    sub = p.add_subparsers(dest="cmd", required=True)

    enc = sub.add_parser("encode")
    enc.add_argument("--input","-i", required=True, help="Input audio file")
    enc.add_argument("--outdir","-o", required=True, help="Output directory for images")
    enc.add_argument("--user","-u", required=True, help="User id (binds key)")
    enc.add_argument("--max-chunk-bytes", type=int, default=DEFAULT_MAX_CHUNK_BYTES, help="Max raw audio bytes per image (default 50MB)")
    enc.add_argument("--master","-m", required=False, help="Master key hex (optional; prefer env var)")
    enc.add_argument("--no-compress", action="store_true", help="Disable zstd compression for chunks")
    enc.add_argument("--delete", action="store_true", help="Delete source audio after successful encode")

    dec = sub.add_parser("decode")
    dec.add_argument("--indir","-i", required=True, help="Input directory containing images produced by encode")
    dec.add_argument("--out","-o", required=True, help="Recovered output audio file")
    dec.add_argument("--user","-u", required=True, help="User id used for encryption")
    dec.add_argument("--master","-m", required=False, help="Master key hex (optional; prefer env var)")

    return p


def main(argv=None):
    p = build_cli()
    args = p.parse_args(argv)

    if args.cmd == "encode":
        in_file = Path(args.input)
        out_dir = Path(args.outdir)
        compress = not bool(args.no_compress)
        images = encode_streamed(in_file, out_dir, args.user, max_chunk_bytes=args.max_chunk_bytes, master_hex=args.master, compress=compress)
        if args.delete:
            try:
                in_file.unlink()
                print("[*] Deleted source file.")
            except Exception as e:
                print("[!] Could not delete source:", e)

    elif args.cmd == "decode":
        decode_images_to_file(Path(args.indir), Path(args.out), args.user, master_hex=args.master)

    else:
        p.print_help()

if __name__ == "__main__":
    main()
