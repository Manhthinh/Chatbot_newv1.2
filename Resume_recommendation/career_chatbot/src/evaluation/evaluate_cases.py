import argparse
import json
import subprocess
import sys
from pathlib import Path

if sys.platform == "win32":
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")


BASE_DIR = Path(__file__).resolve().parents[2]
REPO_ROOT = BASE_DIR.parents[1]
PROCESSED_DIR = BASE_DIR / "data" / "processed"
DEFAULT_CV_PATH = BASE_DIR / "data" / "raw" / "cv_samples" / "Resume.pdf"
DEFAULT_RESUME_DATA = BASE_DIR / "data" / "raw" / "resume_data.csv"
DEFAULT_JOBS_READY = REPO_ROOT / "outputs_preprocessing_v2" / "artifacts" / "jobs_chatbot_ready_v2.parquet"
DEFAULT_JOBS_SECTIONS = REPO_ROOT / "outputs_preprocessing_v2" / "artifacts" / "jobs_chatbot_sections_v2.parquet"


def resolve_cv_path(path: Path) -> Path:
    if path.exists() and path.is_file():
        return path
    if path.exists() and path.is_dir():
        siblings = sorted(path.parent.glob(f"{path.name}*.pdf"))
        for sibling in siblings:
            if sibling.is_file():
                return sibling
    siblings = sorted(path.parent.glob(f"{path.name}*.pdf"))
    for sibling in siblings:
        if sibling.is_file():
            return sibling
    raise FileNotFoundError(f"Không tìm thấy file CV hợp lệ tại: {path}")


def run_command(command: list[str]) -> str:
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    if result.returncode != 0:
        print("Lỗi khi chạy lệnh:")
        print(" ".join(command))
        print(result.stderr)
        raise RuntimeError("Command failed")

    return result.stdout


def load_json(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cv_path", default=str(DEFAULT_CV_PATH), help="Path tới CV sample")
    parser.add_argument("--resume_data_path", default=str(DEFAULT_RESUME_DATA), help="Path tới resume_data.csv")
    parser.add_argument("--jobs_ready_path", default=str(DEFAULT_JOBS_READY), help="Path tới jobs_chatbot_ready_v2.parquet")
    parser.add_argument("--jobs_sections_path", default=str(DEFAULT_JOBS_SECTIONS), help="Path tới jobs_chatbot_sections_v2.parquet")
    parser.add_argument("--case_name", default="resume_pdf_smoke", help="Tên case để đặt tên output")
    args = parser.parse_args()

    cv_path = resolve_cv_path(Path(args.cv_path))
    resume_data_path = Path(args.resume_data_path)
    jobs_ready_path = Path(args.jobs_ready_path)
    jobs_sections_path = Path(args.jobs_sections_path)

    extracted_path = PROCESSED_DIR / f"{args.case_name}_extracted.json"
    gap_path = PROCESSED_DIR / f"{args.case_name}_gap.json"

    if extracted_path.exists():
        extracted_path.unlink()
    if gap_path.exists():
        gap_path.unlink()

    print("=" * 60)
    print("PIPELINE SMOKE TEST")
    print(f"CV path: {cv_path}")
    print(f"resume_data.csv: {resume_data_path} | exists={resume_data_path.exists()}")
    print(f"jobs_ready_path: {jobs_ready_path} | exists={jobs_ready_path.exists()}")
    print(f"jobs_sections_path: {jobs_sections_path} | exists={jobs_sections_path.exists()}")

    run_command([
        "python",
        str(BASE_DIR / "src" / "cv_processing" / "extract_cv_info.py"),
        "--cv_path", str(cv_path),
        "--output_path", str(extracted_path),
    ])

    if not extracted_path.exists():
        raise RuntimeError("Không tạo được file extracted.")

    run_command([
        "python",
        str(BASE_DIR / "src" / "matching" / "gap_analysis.py"),
        "--cv_json", str(extracted_path),
        "--jobs_ready_path", str(jobs_ready_path),
        "--jobs_sections_path", str(jobs_sections_path),
        "--output_path", str(gap_path),
    ])

    if not gap_path.exists():
        raise RuntimeError("Không tạo được file gap analysis.")

    extracted = load_json(extracted_path)
    gap_result = load_json(gap_path)

    print("\n----- EXTRACTED CV INFO -----")
    print(json.dumps(extracted, ensure_ascii=False, indent=2))

    print("\n----- GAP ANALYSIS RESULT -----")
    print(json.dumps(gap_result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
