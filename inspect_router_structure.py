from pathlib import Path

path = Path(r"Resume_recommendation/career_chatbot/src/chatbot/chat_router.py")
text = path.read_text(encoding="utf-8")

targets = [
    "def classify_intent",
    "def answer_company_or_job_fit",
    "def answer_skill_deep_dive",
    "def answer_skills_overview",
    "def answer_role_fit",
    "def answer_hr_it",
    "if focus ==",
    "if intent ==",
    "company_or_job_fit",
    "general_question",
]

for target in targets:
    print("=" * 20, target, "=" * 20)
    idx = text.find(target)
    if idx == -1:
        print("NOT FOUND")
        continue
    start = max(0, idx - 250)
    end = min(len(text), idx + 600)
    print(text[start:end])
    print()
