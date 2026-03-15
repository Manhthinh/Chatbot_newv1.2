import argparse
import json
import os
import subprocess
from pathlib import Path
import sys

# FIX ENCODING TIẾNG VIỆT
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
try:
    import requests
    _HAS_REQUESTS = True
except ImportError:  # pragma: no cover
    requests = None  # type: ignore
    _HAS_REQUESTS = False


# For Ollama (preferred if running locally)
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "llama3:latest"

# For llama.cpp (fallback / alternative)
BASE_DIR = Path(__file__).resolve().parents[2]
LLAMA_CPP_BIN = os.getenv("LLAMA_CPP_BIN", "main")
LLAMA_CPP_MODEL = os.getenv("LLAMA_CPP_MODEL", "")


def load_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def ask_ollama(prompt: str) -> str:
    if not _HAS_REQUESTS:
        raise RuntimeError("Requests library unavailable, cannot call Ollama.")

    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False,
    }
    response = requests.post(OLLAMA_URL, json=payload, timeout=120)
    response.raise_for_status()
    data = response.json()
    return data.get("response", "").strip()


def get_llama_cpp_model_path() -> str:
    """Resolve the llama.cpp model path.

    Order of precedence:
    1) Environment variable LLAMA_CPP_MODEL
    2) Common paths under the repo (models/ or llama/)
    """
    if LLAMA_CPP_MODEL:
        return LLAMA_CPP_MODEL

    candidates = [
        BASE_DIR / "models" / "ggml-model.bin",
        BASE_DIR / "models" / "llama.bin",
        BASE_DIR / "llama" / "ggml-model.bin",
        BASE_DIR / "llama" / "llama.bin",
    ]

    for p in candidates:
        if p.exists():
            return str(p)

    raise FileNotFoundError(
        "No llama.cpp model found. Set LLAMA_CPP_MODEL env var or place a ggml model under 'models/' or 'llama/' in the repo."
    )


def ask_llama_cpp(prompt: str) -> str:
    model_path = get_llama_cpp_model_path()

    cmd = [
        LLAMA_CPP_BIN,
        "-m",
        model_path,
        "--prompt",
        prompt,
        "--n_predict",
        "512",
        "--temp",
        "0.7",
        "--top_k",
        "40",
        "--top_p",
        "0.95",
        "--repeat_last_n",
        "64",
        "--repeat_penalty",
        "1.1",
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    result.check_returncode()

    output = result.stdout.strip()
    # Remove the input prompt from the output if llama.cpp echoes it back
    if prompt and output.startswith(prompt):
        output = output[len(prompt) :].strip()
    return output


def classify_question(question: str) -> str:
    q = question.lower()

    cv_keywords = [
        "cv", "resume", "hồ sơ", "thiếu gì", "thiếu kỹ năng",
        "phù hợp nghề", "hợp nghề nào", "điểm mạnh", "điểm yếu",
        "dựa trên cv", "dựa trên hồ sơ", "gap", "ứng tuyển"
    ]

    career_keywords = [
        "nên học gì", "roadmap", "lộ trình", "nên phát triển gì",
        "nên làm project gì", "phát triển kỹ năng", "3 tháng", "6 tháng",
        "để trở thành", "để theo", "định hướng nghề nghiệp"
    ]

    for kw in cv_keywords:
        if kw in q:
            return "cv_analysis"

    for kw in career_keywords:
        if kw in q:
            return "career_advice"

    return "general_question"


def build_cv_prompt(gap_result: dict, user_question: str) -> str:
    return f"""
Bạn là chatbot tư vấn nghề nghiệp và phân tích CV cho nhóm ngành Data/AI.

Hãy trả lời bằng tiếng Việt, rõ ràng, bám sát dữ liệu.
Không bịa thông tin ngoài dữ liệu được cung cấp.

Bắt buộc trả lời theo 5 mục:
1. Mức độ phù hợp
2. Điểm mạnh hiện tại
3. Điểm còn thiếu
4. Kỹ năng nên phát triển tiếp
5. Hành động đề xuất trong 1–3 tháng

Dữ liệu phân tích CV:
{json.dumps(gap_result, ensure_ascii=False, indent=2)}

Câu hỏi người dùng:
{user_question}
""".strip()


def build_career_prompt(gap_result: dict, user_question: str) -> str:
    return f"""
Bạn là chatbot tư vấn nghề nghiệp Data/AI.

Hãy dựa trên dữ liệu phân tích CV để tư vấn thực tế, dễ hiểu, ngắn gọn.
Ưu tiên:
- kỹ năng nên học trước
- role phù hợp hơn
- project nên làm
- hành động cụ thể trong 1–3 tháng

Dữ liệu phân tích:
{json.dumps(gap_result, ensure_ascii=False, indent=2)}

Câu hỏi:
{user_question}
""".strip()


def build_general_prompt(user_question: str) -> str:
    return f"""
Bạn là trợ lý tư vấn nghề nghiệp trong lĩnh vực Data/AI.

Hãy trả lời bằng tiếng Việt, dễ hiểu, chính xác, súc tích.
Nếu câu hỏi là kiến thức nền, hãy giải thích theo kiểu cho người mới học.

Câu hỏi:
{user_question}
""".strip()


def fallback_answer(intent: str, user_question: str, gap_result: dict | None = None) -> str:
    if intent == "general_question":
        return (
            "Hiện chưa gọi được mô hình LLM (Ollama/llama.cpp). "
            "Bạn hãy bật Ollama hoặc đảm bảo llama.cpp được cài và model đặt đúng, rồi thử lại."
        )

    roles = gap_result.get("best_fit_roles", []) if gap_result else []
    missing = gap_result.get("missing_skills", []) if gap_result else []
    strengths = gap_result.get("strengths", []) if gap_result else []

    lines = []
    lines.append("Mình đang ở chế độ dự phòng nên sẽ trả lời ngắn gọn hơn.\n")

    if roles:
        lines.append(f"Role phù hợp nhất hiện tại: {roles[0]}")

    if strengths:
        lines.append("Điểm mạnh:")
        for s in strengths[:5]:
            lines.append(f"- {s}")

    if missing:
        lines.append("Điểm còn thiếu:")
        for m in missing[:5]:
            lines.append(f"- {m}")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--question", required=True, help="User question")
    parser.add_argument("--gap_result", default="", help="Optional path to gap analysis result JSON")
    args = parser.parse_args()

    intent = classify_question(args.question)
    gap_result = None

    if args.gap_result:
        gap_path = Path(args.gap_result)
        if gap_path.exists():
            gap_result = load_json(str(gap_path))

    if intent == "cv_analysis":
        if not gap_result:
            raise ValueError("Câu hỏi dạng cv_analysis cần --gap_result")
        prompt = build_cv_prompt(gap_result, args.question)

    elif intent == "career_advice":
        if not gap_result:
            raise ValueError("Câu hỏi dạng career_advice cần --gap_result")
        prompt = build_career_prompt(gap_result, args.question)

    else:
        prompt = build_general_prompt(args.question)

    try:
        answer = ask_ollama(prompt)
        if not answer:
            answer = fallback_answer(intent, args.question, gap_result)
    except Exception as e:
        print(f"[Warning] Ollama call failed: {e}")
        try:
            answer = ask_llama_cpp(prompt)
            if not answer:
                answer = fallback_answer(intent, args.question, gap_result)
        except Exception as e2:
            print(f"[Warning] llama.cpp call failed: {e2}")
            answer = fallback_answer(intent, args.question, gap_result)

    print("\n===== INTENT =====")
    print(intent)
    print("\n===== ANSWER =====\n")
    print(answer)


if __name__ == "__main__":
    main()