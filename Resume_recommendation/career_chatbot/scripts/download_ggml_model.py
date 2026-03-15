"""Download a ggml model from Hugging Face into the repo.

Usage:
  python scripts/download_ggml_model.py

By default it downloads:
  TheBloke/vicuna-7B-1.1-HF-GGML/vicuna-7B-1.1.ggmlv3.q4_0.bin

And saves it as:
  career_chatbot/models/ggml-model.bin
"""

import os
from pathlib import Path

from huggingface_hub import hf_hub_download


def main() -> None:
    out = Path(__file__).resolve().parents[1] / "models" / "ggml-model.bin"
    out.parent.mkdir(parents=True, exist_ok=True)

    repo_id = "TheBloke/vicuna-7B-1.1-HF-GGML"
    filename = "vicuna-7B-1.1.ggmlv3.q4_0.bin"

    token = (
        os.getenv("HUGGINGFACE_TOKEN")
        or os.getenv("HF_TOKEN")
        or os.getenv("HUGGINGFACE_HUB_TOKEN")
    )

    if token:
        print("Using Hugging Face token from environment.")
    else:
        print(
            "No Hugging Face token found in environment. "
            "You may need to run 'python -m huggingface_hub login' first."
        )

    print("Downloading model from", repo_id, "file", filename)
    path = hf_hub_download(
        repo_id=repo_id,
        filename=filename,
        cache_dir=str(out.parent),
        token=token or None,
    )
    print("Downloaded to cache:", path)

    out.write_bytes(Path(path).read_bytes())
    print("Model saved as", out.resolve())


if __name__ == "__main__":
    main()
