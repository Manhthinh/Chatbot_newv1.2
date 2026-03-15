import argparse
import json
from pathlib import Path

import requests


OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "llama3.1:8b"


def load_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def ask_ollama(prompt: str) -> str:
    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False,
    }
    response = requests.post(OLLAMA_URL, json=payload, timeout=120)
    response.raise_for_status()
    data = response.json()
    return data.get("response", "").strip()


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
            "Hiện chưa gọi được mô hình LLM. "
            "Bạn hãy bật Ollama rồi thử lại để mình trả lời câu hỏi kiến thức chung tự nhiên hơn."
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
        print(f"[Warning] Không gọi được Ollama: {e}")
        answer = fallback_answer(intent, args.question, gap_result)

    print("\n===== INTENT =====")
    print(intent)
    print("\n===== ANSWER =====\n")
    print(answer)


if __name__ == "__main__":
    main()