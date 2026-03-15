#!/usr/bin/env python
"""
Interactive Chatbot Testing Script
Hướng dẫn test chatbot với giao diện tương tác

Sử dụng: python test_chatbot_interactive.py
"""

import json
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
cv_samples_dir = BASE_DIR / "data" / "raw" / "cv_samples"
processed_dir = BASE_DIR / "data" / "processed"


def print_header(text):
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}\n")


def print_section(text):
    print(f"\n--- {text} ---\n")


def check_requirements():
    """Kiểm tra các thư viện cần thiết"""
    print_header("1️⃣ KIỂM TRA YÊU CẦU")

    required = ["requests", "pandas", "fitz"]
    missing = []

    for pkg in required:
        try:
            __import__(pkg if pkg != "fitz" else "pymupdf")
            print(f"✓ {pkg}")
        except ImportError:
            print(f"✗ {pkg} - THIẾU")
            missing.append(pkg)

    if missing:
        print(f"\n⚠️ Thiếu packages: {', '.join(missing)}")
        print("Chạy: pip install -r requirements.txt")
        return False

    print("\n✓ Tất cả yêu cầu thỏa mãn")
    return True


def list_cv_samples():
    """Liệt kê các file CV sample"""
    print_header("2️⃣ SẴN CÓ CV SAMPLES")

    samples = []
    if cv_samples_dir.exists():
        txt_files = list(cv_samples_dir.glob("*.txt"))
        pdf_files = list(cv_samples_dir.glob("*.pdf"))

        for i, f in enumerate(txt_files, 1):
            print(f"{i}. {f.name} (TXT)")
            samples.append(("txt", f))

        for i, f in enumerate(pdf_files, len(txt_files) + 1):
            print(f"{i}. {f.name} (PDF)")
            samples.append(("pdf", f))

    return samples


def extract_cv_step(samples):
    """Bước 1: Extract CV"""
    print_header("3️⃣ BƯỚC 1: TRÍCH XUẤT CV (Extract CV Info)")

    if not samples:
        print("❌ Không tìm thấy file CV sample")
        return None

    print("\nChọn file CV để trích xuất:")
    for i, (fmt, path) in enumerate(samples, 1):
        print(f"  {i}. {path.name} ({fmt.upper()})")
    print("  0. Bỏ qua")

    choice = input("\nLựa chọn (0-{}): ".format(len(samples))).strip()

    try:
        idx = int(choice) - 1
        if idx == -1:
            return None
        if 0 <= idx < len(samples):
            fmt, cv_path = samples[idx]
            print(f"\n✓ Đã chọn: {cv_path.name}")

            # Chạy extract
            output_file = processed_dir / f"test_extracted_{Path(cv_path).stem}.json"

            cmd = [
                "python",
                "src/cv_processing/extract_cv_info.py",
                f"--{fmt}", str(cv_path),
                "--output", str(output_file)
            ]

            print(f"\n▶ Chạy: {' '.join(cmd)}")
            result = subprocess.run(cmd, cwd=BASE_DIR, capture_output=True, text=True)

            if result.returncode == 0:
                print(f"\n✓ Extracted thành công: {output_file.name}")

                # Hiển thị thông tin
                with open(output_file) as f:
                    data = json.load(f)
                    print(f"  - Title: {data.get('title', 'N/A')}")
                    print(f"  - Skills: {len(data.get('skills', []))} items")
                    print(f"  - Experience: {len(data.get('experience', []))} items")

                return str(output_file)
            else:
                print(f"\n❌ Lỗi: {result.stderr}")
                return None
    except (ValueError, IndexError):
        print("❌ Lựa chọn không hợp lệ")
        return None


def gap_analysis_step(extracted_file):
    """Bước 2: Gap Analysis"""
    print_header("4️⃣ BƯỚC 2: PHÂN TÍCH KHOẢNG CÁCH (Gap Analysis)")

    if not extracted_file:
        # Kiểm tra các file gap analysis đã có
        gap_files = list(processed_dir.glob("*gap*.json"))
        if gap_files:
            print("Các file Gap Analysis đã có sẵn:")
            for i, f in enumerate(gap_files, 1):
                print(f"  {i}. {f.name}")
            print("  0. Tạo mới từ file extracted")

            choice = input("\nLựa chọn: ").strip()
            try:
                idx = int(choice) - 1
                if idx == -1:
                    print("❌ Cần file extracted trước")
                    return None
                if 0 <= idx < len(gap_files):
                    return str(gap_files[idx])
            except (ValueError, IndexError):
                return None
        else:
            print("❌ Cần file extracted trước")
            return None

    print(f"ℹ️ File extracted: {Path(extracted_file).name}")

    output_file = processed_dir / f"test_gap_{Path(extracted_file).stem}.json"

    cmd = [
        "python",
        "src/matching/gap_analysis.py",
        "--cv_json", str(extracted_file),
        "--output", str(output_file)
    ]

    print(f"\n▶ Chạy: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=BASE_DIR, capture_output=True, text=True)

    if result.returncode == 0:
        print(f"\n✓ Gap Analysis thành công: {output_file.name}")

        # Hiển thị thông tin
        with open(output_file) as f:
            gap = json.load(f)
            print(f"\n📊 Kết quả phân tích:")
            print(f"  - Domain Fit: {gap.get('domain_fit')}")
            print(f"  - Best Fit Roles: {gap.get('best_fit_roles', [])}")
            if gap.get('top_role_result'):
                tr = gap['top_role_result']
                print(f"  - Top Role: {tr.get('role')} (Score: {tr.get('score')})")

        return str(output_file)
    else:
        print(f"\n❌ Lỗi: {result.stderr}")
        return None


def chatbot_step(gap_analysis_file):
    """Bước 3: Test Chatbot"""
    print_header("5️⃣ BƯỚC 3: TEST CHATBOT (Chat Router)")

    if not gap_analysis_file:
        print("❌ Cần file gap analysis trước")
        return

    # Các câu hỏi mẫu
    sample_questions = {
        "1": ("CV Analysis", "CV của tôi phù hợp với vị trí nào nhất?"),
        "2": ("Career Advice", "Nên học gì để trở thành Data Engineer?"),
        "3": ("Career Advice", "Trong 3 tháng tôi nên làm gì?"),
        "4": ("General", "Machine Learning là gì?"),
        "5": ("CV Analysis", "Tôi thiếu kỹ năng gì?"),
        "6": ("General", "SQL khác gì NoSQL?"),
        "7": ("Custom", ""),
    }

    print("📝 Chọn câu hỏi test:")
    for k, (typ, q) in sample_questions.items():
        if k == "7":
            print(f"  {k}. Tự nhập câu hỏi")
        else:
            print(f"  {k}. ({typ}) {q}")
    print("  0. Bỏ qua")

    choice = input("\nLựa chọn: ").strip()

    if choice == "0":
        return

    if choice in sample_questions:
        typ, question = sample_questions[choice]

        if choice == "7":
            question = input("\nNhập câu hỏi của bạn: ").strip()
            if not question:
                print("❌ Câu hỏi không được để trống")
                return

        print(f"\n📌 Câu hỏi: {question}")
        print(f"📊 File gap analysis: {Path(gap_analysis_file).name}")

        cmd = [
            "python",
            "src/chatbot/chat_router.py",
            "--question", question,
            "--gap_result", str(gap_analysis_file)
        ]

        print(f"\n▶ Chạy chatbot...\n")
        result = subprocess.run(cmd, cwd=BASE_DIR, capture_output=True, text=True)

        if result.returncode == 0:
            print(result.stdout)
        else:
            print(f"❌ Lỗi: {result.stderr}")


def batch_test():
    """Test toàn bộ pipeline"""
    print_header("🔄 BATCH TEST - TOÀN BỘ PIPELINE")

    print("Chế độ này sẽ chạy toàn bộ pipeline từ Extract → Gap Analysis → Chatbot\n")

    samples = list(cv_samples_dir.glob("*.txt"))[:1]  # Lấy file txt đầu tiên

    if not samples:
        print("❌ Không tìm thấy file CV TXT sample")
        return

    cv_file = samples[0]
    print(f"1. Sử dụng CV: {cv_file.name}")

    # Extract
    extracted_file = processed_dir / f"batch_extracted.json"
    cmd = ["python", "src/cv_processing/extract_cv_info.py", "--txt", str(cv_file), "--output", str(extracted_file)]
    print(f"\n2. Extract CV... ", end="", flush=True)
    result = subprocess.run(cmd, cwd=BASE_DIR, capture_output=True, text=True)
    print("✓" if result.returncode == 0 else "❌")

    if result.returncode != 0:
        print(f"   Lỗi: {result.stderr}")
        return

    # Gap Analysis
    gap_file = processed_dir / f"batch_gap.json"
    cmd = ["python", "src/matching/gap_analysis.py", "--cv_json", str(extracted_file), "--output", str(gap_file)]
    print(f"3. Gap Analysis... ", end="", flush=True)
    result = subprocess.run(cmd, cwd=BASE_DIR, capture_output=True, text=True)
    print("✓" if result.returncode == 0 else "❌")

    if result.returncode != 0:
        print(f"   Lỗi: {result.stderr}")
        return

    # Chatbot Questions
    questions = [
        "CV của tôi phù hợp với vị trí nào nhất?",
        "Tôi nên học gì trong 3 tháng tới?",
    ]

    for i, q in enumerate(questions, 1):
        print(f"\n4.{i} Chatbot Query: {q}")
        cmd = ["python", "src/chatbot/chat_router.py", "--question", q, "--gap_result", str(gap_file)]
        result = subprocess.run(cmd, cwd=BASE_DIR, capture_output=True, text=True)
        if result.returncode == 0:
            lines = result.stdout.split("\n")
            # In các dòng quan trọng
            for line in lines[-30:]:
                if line.strip():
                    print(f"   {line}")
        else:
            print(f"   ❌ Lỗi: {result.stderr}")


def main():
    """Main menu"""
    print("\n" + "="*60)
    print("  🤖 INTERACTIVE CHATBOT TESTING TOOL")
    print("="*60)

    print("\nMục đích: Test từng bước hoặc toàn bộ pipeline của hệ thống")
    print("Công nghệ: Extract CV → Gap Analysis → Chatbot\n")

    # Kiểm tra yêu cầu
    if not check_requirements():
        return

    while True:
        print("\n" + "-"*60)
        print("CHỌN CHẾ ĐỘ TEST:\n")
        print("  1. ▶️ Test từng bước (Step by step)")
        print("  2. 🔄 Batch test (Toàn bộ pipeline)")
        print("  3. 📋 Hiển thị CV samples")
        print("  0. ❌ Thoát\n")

        choice = input("Lựa chọn (0-3): ").strip()

        if choice == "1":
            # Step by step
            samples = list_cv_samples()
            extracted = extract_cv_step(samples)
            gap_file = gap_analysis_step(extracted)
            chatbot_step(gap_file)

        elif choice == "2":
            batch_test()

        elif choice == "3":
            print_header("SẴN CÓ CV SAMPLES")
            list_cv_samples()

        elif choice == "0":
            print("\n👋 Tạm biệt!\n")
            break

        else:
            print("\n❌ Lựa chọn không hợp lệ")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⏹️ Đã dừng")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Lỗi: {e}")
        import traceback
        traceback.print_exc()
