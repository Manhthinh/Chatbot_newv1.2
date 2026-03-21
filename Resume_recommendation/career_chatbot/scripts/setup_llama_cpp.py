"""Helper script to verify/prepare llama.cpp support for the chatbot.

This script does NOT automatically build llama.cpp, but it can:
- verify that a llama.cpp executable ("llama-cli"/"main") is on PATH
- check for an existing GGUF/GGML model in the repo (under `models/` or `llama/`)
- optionally download a model file if you pass --download-url

Usage:
  python scripts/setup_llama_cpp.py
  python scripts/setup_llama_cpp.py --download-url https://example.com/model.gguf

If you have a model file already, set the environment variable:
  setx LLAMA_CPP_MODEL "C:\\path\\to\\model.gguf"  (Windows)
  export LLAMA_CPP_MODEL=/path/to/model.gguf      (Linux/macOS)

Then rerun the chatbot.
"""

import argparse
import os
import shutil
import sys
from pathlib import Path


def locate_llama_binary() -> str | None:
    # Newer llama.cpp builds usually expose `llama-cli`; older ones used `main`.
    for name in ["llama-cli.exe", "llama-cli", "main.exe", "main"]:
        path = shutil.which(name)
        if not path:
            continue

        # On Windows, `shutil.which("main")` can accidentally resolve to `main.cpl`.
        # Accept only executables or extensionless binaries.
        ext = Path(path).suffix.lower()
        if ext and ext != ".exe":
            continue

        return path
    return None


def locate_existing_model(base_dir: Path) -> Path | None:
    candidates = [
        base_dir / "models",
        base_dir / "llama",
        base_dir / "llama.cpp" / "models",
    ]

    for d in candidates:
        if not d.exists():
            continue
        for ext in ["*.gguf", "*.bin", "*.ggml"]:
            for p in d.glob(ext):
                return p
    return None


def download_model(url: str, dest: Path) -> None:
    import urllib.request

    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"Downloading model from {url} to {dest} ...")

    def _progress(blocks, block_size, total_size):
        if total_size <= 0:
            return
        done = blocks * block_size
        pct = min(done / total_size * 100, 100)
        print(f"\r{pct:5.1f}% ({done // (1024*1024)} MiB of {total_size // (1024*1024)} MiB)", end="")

    urllib.request.urlretrieve(url, dest, reporthook=_progress)
    print("\nDownload complete.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Check/setup llama.cpp + model for the chatbot.")
    parser.add_argument("--download-url", help="Optional URL to download a GGUF/GGML model file.")
    parser.add_argument(
        "--model-dest",
        help="Optional destination path for downloaded model (default: career_chatbot/models/model.gguf).",
    )
    args = parser.parse_args()

    base_dir = Path(__file__).resolve().parents[2]
    print(f"Repo base: {base_dir}")

    llama_bin = locate_llama_binary()
    if llama_bin:
        print(f"Found llama.cpp binary: {llama_bin}")
    else:
        print("WARNING: Could not find llama.cpp binary (llama-cli/main) on PATH.")
        print("  - Build llama.cpp: https://github.com/ggerganov/llama.cpp")
        print("  - Put the built 'llama-cli' (or 'main' for older releases) on your PATH.")

    model_path = locate_existing_model(base_dir)
    if model_path:
        print(f"Found model file: {model_path}")
    else:
        print("WARNING: No GGUF/GGML model file found under 'models/' or 'llama/'.")
        if args.download_url:
            dest = Path(args.model_dest) if args.model_dest else base_dir / "models" / "model.gguf"
            download_model(args.download_url, dest)
            print(f"Downloaded model to {dest}")
        else:
            print("  - Place a GGUF/GGML model file (e.g., mistral-7b-instruct.Q4_K_M.gguf) under 'career_chatbot/models/'")
            print("  - Or set LLAMA_CPP_MODEL to point to it:")
            print("      setx LLAMA_CPP_MODEL \"C:\\path\\to\\model.gguf\"  (Windows)")
            print("      export LLAMA_CPP_MODEL=/path/to/model.gguf  (Linux/macOS)")

    print("\nAfter you have a llama.cpp binary + model, rerun the chatbot script.")


if __name__ == "__main__":
    main()
