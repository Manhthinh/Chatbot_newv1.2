
from __future__ import annotations

import argparse
import io
import json
import os
import re
import subprocess
import sys
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Any

import requests


if sys.platform == "win32" and hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")


CHATBOT_DIR = Path(__file__).resolve().parent
SRC_DIR = CHATBOT_DIR.parent
BASE_DIR = SRC_DIR.parent
REPO_ROOT = BASE_DIR.parent.parent

DEFAULT_GAP_RESULT_PATH = BASE_DIR / "data" / "processed" / "resume_pdf_smoke_gap.json"

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
OLLAMA_CHAT_URL = f"{OLLAMA_HOST}/api/chat"
OLLAMA_TAGS_URL = f"{OLLAMA_HOST}/api/tags"
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "90"))
ENABLE_LLAMA_CPP_FALLBACK = os.getenv("ENABLE_LLAMA_CPP_FALLBACK", "0") == "1"

OLLAMA_MODEL_PREFERENCE = [
    "llama3.1:8b",
    "llama3.2:3b",
    "llama3.2:1b",
    "llama3:latest",
    "gemma3:4b",
    "gemma3:1b",
]

FAST_MODEL_PREFERENCE = [
    "gemma3:1b",
    "llama3.2:1b",
    "llama3.2:3b",
    "gemma3:4b",
    "llama3.1:8b",
]

THINKING_MODEL_PREFERENCE = [
    "llama3.1:8b",
    "llama3.2:3b",
    "gemma3:4b",
    "llama3.2:1b",
    "gemma3:1b",
]

MODE_CONFIGS = {
    "fast": {
        "max_jobs": 2,
        "max_sections": 1,
        "temperature": 0.1,
        "num_predict": 140,
        "timeout": 35,
        "model_preference": FAST_MODEL_PREFERENCE,
    },
    "thinking": {
        "max_jobs": 3,
        "max_sections": 2,
        "temperature": 0.2,
        "num_predict": 260,
        "timeout": OLLAMA_TIMEOUT,
        "model_preference": THINKING_MODEL_PREFERENCE,
    },
}

CURRENT_MODE = "auto"


def is_fast_mode() -> bool:
    return CURRENT_MODE == "fast"


def is_thinking_mode() -> bool:
    return CURRENT_MODE == "thinking"


def trim_to_top_lines(text: str, max_lines: int) -> str:
    lines = [line.rstrip() for line in text.splitlines() if line.strip()]
    return "\n".join(lines[:max_lines])


def llm_rewrite_from_base(base_answer: str, instruction: str) -> str:
    if not is_thinking_mode():
        return base_answer
    try:
        prompt = (
            "Bạn là chatbot tư vấn nghề nghiệp.\n"
            "Hãy viết lại câu trả lời sau bằng tiếng Việt tự nhiên, súc tích nhưng có chiều sâu hơn.\n"
            "Không bịa thêm dữ kiện ngoài phần đã có.\n"
            "Giữ đúng bối cảnh CV và job match.\n"
            f"{instruction}\n\n"
            "Câu trả lời gốc:\n"
            f"{base_answer}"
        )
        rewritten = ask_ollama(prompt)
        if isinstance(rewritten, str) and rewritten.strip():
            return rewritten.strip()
    except Exception:
        return base_answer
    return base_answer


def extract_question_from_call(args, kwargs) -> str:
    for value in list(args) + list(kwargs.values()):
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def extract_gap_result_from_call(args, kwargs) -> dict:
    for value in list(args) + list(kwargs.values()):
        if isinstance(value, dict) and ("top_job_matches" in value or "top_role_result" in value):
            return value
    return {}


def derive_company_name(job: dict) -> str:
    url = str(job.get("job_url") or "")
    if "/brand/" in url:
        slug = url.split("/brand/", 1)[1].split("/", 1)[0]
        slug = slug.replace("-", " ").replace("_", " ").strip()
        return " ".join(part.capitalize() for part in slug.split())
    title = str(job.get("job_title") or "").strip()
    if " tại " in title.lower():
        tail = title.lower().split(" tại ", 1)[1]
        return " ".join(part.capitalize() for part in tail.split())
    return ""


def format_missing_skills(job: dict, limit: int = 4) -> str:
    missing = job.get("missing_skills") or []
    return pretty_join(missing[:limit]) or "ít khoảng trống kỹ năng lớn"


def answer_company_jobs_query(question: str, gap_result: dict) -> str:
    jobs = gap_result.get("top_job_matches") or []
    if not jobs:
        return "Mình chưa có đủ dữ liệu job match để liệt kê theo doanh nghiệp cho CV này."
    practical_jobs = rank_practical_jobs(jobs)[:6]
    normalized_question = normalize_text(question)
    matches = []
    for job in practical_jobs:
        company = derive_company_name(job)
        if company and normalize_text(company) in normalized_question:
            matches.append((company, job))

    if matches:
        company_name = matches[0][0]
        company_jobs = [job for company, job in matches if company == company_name][:3]
        lines = [f"Dựa trên các job đang match với CV hiện tại, {company_name} có những vị trí gần bạn hơn như:"]
        for idx, job in enumerate(company_jobs, start=1):
            title = job.get("job_title") or "Job chưa rõ tên"
            exp = job.get("experience_min_years")
            exp_text = f"{int(exp)} năm" if isinstance(exp, (int, float)) and float(exp).is_integer() else f"{exp} năm"
            lines.append(
                f"{idx}. {title}: khoảng {exp_text} kinh nghiệm; thiếu chính {format_missing_skills(job)}."
            )
        best_job = company_jobs[0]
        lines.append(
            f"Nếu xét để apply sớm, bạn nên ưu tiên '{best_job.get('job_title')}' trong nhóm này."
        )
        return "\n".join(lines)

    grouped = []
    seen_companies = set()
    for job in practical_jobs:
        company = derive_company_name(job)
        if not company or company in seen_companies:
            continue
        seen_companies.add(company)
        grouped.append((company, job))
        if len(grouped) >= 3:
            break

    if not grouped:
        return "Mình có thể so job theo CV hiện tại, nhưng dữ liệu doanh nghiệp sạch trong nhóm job này còn hạn chế."

    lines = ["Trong nhóm job đang gần CV hiện tại, một số doanh nghiệp có vị trí đáng xem là:"]
    for idx, (company, job) in enumerate(grouped, start=1):
        lines.append(
            f"{idx}. {company}: nổi bật là '{job.get('job_title')}', yêu cầu gần nhất quanh {format_missing_skills(job)}."
        )
    lines.append("Nếu bạn muốn, mình có thể so tiếp CV này hợp với doanh nghiệp nào hơn trong nhóm trên.")
    return "\n".join(lines)


def answer_job_market_query(question: str, gap_result: dict) -> str:
    jobs = gap_result.get("top_job_matches") or []
    role = (gap_result.get("top_role_result") or {}).get("role_name") or gap_result.get("target_role_from_cv") or "vai trò hiện tại"
    if not jobs:
        return "Mình chưa có đủ dữ liệu job match để tóm tắt tình hình việc làm cho CV này."

    practical_jobs = rank_practical_jobs(jobs)[:5]
    skill_counts = {}
    location_counts = {}
    for job in practical_jobs:
        for skill in (job.get("required_skills") or []) + (job.get("preferred_skills") or []):
            skill_counts[skill] = skill_counts.get(skill, 0) + 1
        location = job.get("location")
        if location:
            location_counts[location] = location_counts.get(location, 0) + 1

    top_skills = [skill for skill, _ in sorted(skill_counts.items(), key=lambda item: (-item[1], item[0]))[:4]]
    top_locations = [loc for loc, _ in sorted(location_counts.items(), key=lambda item: (-item[1], item[0]))[:2]]
    best_titles = [job.get("job_title") for job in practical_jobs[:3] if job.get("job_title")]

    lines = [
        f"Dựa trên dữ liệu job hiện có trong hệ thống, hướng {role} vẫn là nhóm gần nhất với CV hiện tại của bạn.",
        f"Ở lớp job thực tế hơn để apply sớm, các vị trí nổi bật đang là: {pretty_join(best_titles)}.",
    ]
    if top_skills:
        lines.append(f"Các kỹ năng xuất hiện nhiều nhất quanh nhóm này là: {pretty_join(top_skills)}.")
    if top_locations:
        lines.append(f"Khu vực xuất hiện nhiều hơn trong nhóm job gần bạn là: {pretty_join(top_locations)}.")
    lines.append("Nếu muốn đọc theo thị trường hiện tại, mình đang kết luận trong phạm vi dữ liệu job đã có trong hệ thống, chưa phải dữ liệu realtime toàn thị trường.")
    return "\n".join(lines)

SKILL_FOCUS_ALIASES = {
    "Excel": ["excel", "google sheets", "spreadsheet"],
    "SQL": ["sql", "mysql", "postgres", "postgresql", "query"],
    "Python": ["python"],
    "Power BI": ["power bi", "powerbi", "bi"],
    "Tableau": ["tableau"],
    "Looker": ["looker"],
    "Statistics": ["statistics", "thong ke"],
    "Machine Learning": ["machine learning", "ml"],
    "NLP": ["nlp"],
    "Computer Vision": ["computer vision"],
}

SKILL_GUIDES = {
    "Excel": {
        "level": "Đủ để ứng tuyển Data Analyst đầu vào là phải làm được báo cáo, xử lý dữ liệu và kiểm tra số liệu độc lập.",
        "learn": [
            "Pivot Table/Pivot Chart để tổng hợp dữ liệu nhanh",
            "XLOOKUP hoặc VLOOKUP, INDEX-MATCH để nối bảng",
            "SUMIFS, COUNTIFS, IF để tính KPI và đối soát số liệu",
            "Làm sạch dữ liệu: Text to Columns, Remove Duplicates, lọc lỗi",
            "Dashboard/reporting cơ bản và trình bày số liệu dễ đọc",
        ],
    },
    "SQL": {
        "level": "Đủ để ứng tuyển là viết được truy vấn lấy dữ liệu, lọc, join và group dữ liệu phục vụ báo cáo.",
        "learn": [
            "SELECT, WHERE, ORDER BY, LIMIT",
            "JOIN giữa nhiều bảng",
            "GROUP BY, HAVING, SUM, COUNT, AVG",
            "CASE WHEN để tạo logic nghiệp vụ",
            "CTE/window functions ở mức cơ bản đến trung bình",
        ],
    },
    "Python": {
        "level": "Đủ để ứng tuyển Data Analyst là dùng được Python để làm sạch dữ liệu, phân tích cơ bản và xuất báo cáo.",
        "learn": [
            "Pandas, NumPy cơ bản",
            "Đọc/ghi CSV, Excel",
            "Làm sạch dữ liệu, merge/groupby",
            "EDA cơ bản và biểu đồ đơn giản",
            "Notebook workflow và trình bày kết quả",
        ],
    },
    "Power BI": {
        "level": "Đủ để ứng tuyển là biết kết nối dữ liệu, tạo dashboard và xây KPI cơ bản.",
        "learn": [
            "Kết nối nhiều nguồn dữ liệu",
            "Power Query cơ bản để clean dữ liệu",
            "Model quan hệ bảng",
            "DAX cơ bản: SUM, CALCULATE, measure",
            "Dashboard theo KPI và filter drill-down",
        ],
    },
    "Tableau": {
        "level": "Đủ để ứng tuyển là tạo được dashboard trực quan và kể chuyện bằng dữ liệu.",
        "learn": [
            "Dimension/Measure và calculated field",
            "Filter, parameter, highlight action",
            "Biểu đồ phù hợp cho từng loại insight",
            "Dashboard layout rõ ràng",
            "Storytelling và giải thích insight",
        ],
    },
    "Statistics": {
        "level": "Đủ để ứng tuyển là hiểu ý nghĩa chỉ số, biết đọc phân phối và giải thích insight định lượng.",
        "learn": [
            "Mean, median, variance, standard deviation",
            "Phân phối dữ liệu và outlier",
            "Correlation vs causation",
            "A/B test và kiểm định cơ bản",
            "Diễn giải số liệu thành insight kinh doanh",
        ],
    },
}

HR_SHORTLIST_KEYWORDS = [
    "shortlist",
    "nen shortlist",
    "co nen shortlist",
    "co nen cho vao vong",
    "co nen qua vong",
    "screen in",
]
HR_SCREENING_KEYWORDS = [
    "screening",
    "vong screening",
    "nen hoi gi",
    "can hoi gi",
    "phong van",
    "interview",
]
HR_SUMMARY_KEYWORDS = [
    "tom tat ung vien",
    "candidate summary",
    "danh gia ung vien",
    "nhan xet ung vien",
]
HR_ONBOARDING_KEYWORDS = [
    "onboarding",
    "ke hoach onboard",
    "onboard",
    "30-60-90",
]


def normalize_text(text: str) -> str:
    text = text or ""
    text = unicodedata.normalize("NFD", text.lower())
    text = "".join(char for char in text if unicodedata.category(char) != "Mn")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def pretty_join(items: list[str], limit: int | None = None) -> str:
    cleaned = []
    seen = set()
    for item in items:
        value = str(item or "").strip()
        if not value:
            continue
        key = normalize_text(value)
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(value)

    if limit is not None:
        cleaned = cleaned[:limit]

    if not cleaned:
        return "không rõ"
    if len(cleaned) == 1:
        return cleaned[0]
    if len(cleaned) == 2:
        return f"{cleaned[0]} và {cleaned[1]}"
    return f"{', '.join(cleaned[:-1])} và {cleaned[-1]}"


def resolve_path(path_text: str | None) -> Path | None:
    if not path_text:
        return None

    raw_path = Path(path_text)
    candidates = []

    if raw_path.is_absolute():
        candidates.append(raw_path)
    else:
        candidates.extend(
            [
                Path.cwd() / raw_path,
                REPO_ROOT / raw_path,
                BASE_DIR / raw_path,
                BASE_DIR / "data" / "processed" / raw_path,
            ]
        )

    seen = set()
    for candidate in candidates:
        candidate = candidate.resolve(strict=False)
        if candidate in seen:
            continue
        seen.add(candidate)
        if candidate.exists():
            return candidate
    return None

def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, dict):
        raise ValueError(f"File JSON không hợp lệ: {path}")
    return data



def classify_intent(question: str) -> str:
    norm = normalize_text(question)
    mentioned_skill = detect_skill_name(question)

    hr_keywords = [
        "ung vien",
        "candidate",
        "shortlist",
        "screening",
        "interview",
        "phong van",
        "hiring",
        "tuyen dung",
        "recruiter",
        "hr",
        "onboard",
        "offer",
    ]
    cv_keywords = [
        "cv",
        "resume",
        "ho so",
        "phu hop voi role nao",
        "phu hop voi vi tri nao",
        "fit role",
        "diem manh",
        "diem yeu",
        "khoang trong ky nang",
        "missing skill",
        "gap skill",
    ]
    career_keywords = [
        "nen hoc gi",
        "roadmap",
        "lo trinh",
        "can cai thien gi",
        "can hoc gi",
        "hoc gi",
        "can toi muc nao",
        "muc nao la du",
        "apply",
        "ung tuyen",
        "de theo",
        "phat trien su nghiep",
        "ke hoach hoc",
        "3 thang",
        "6 thang",
        "nang cap ho so",
    ]

    if any(keyword in norm for keyword in hr_keywords):
        return "hr_it"
    if mentioned_skill and any(
        keyword in norm
        for keyword in [
            "hoc",
            "can",
            "muc",
            "du",
            "apply",
            "ung tuyen",
            "ky nang",
            "skill",
        ]
    ):
        return "career_advice"
    if any(keyword in norm for keyword in cv_keywords):
        return "cv_analysis"
    if any(keyword in norm for keyword in career_keywords):
        return "career_advice"
    return "general_question"

def resolve_mode(question: str, intent: str, requested_mode: str) -> str:
    if requested_mode in {"fast", "thinking"}:
        return requested_mode

    if should_prefer_fast_auto(question, intent):
        return "fast"

    if intent in {"cv_analysis", "career_advice"}:
        return "thinking"
    return "fast"

def wants_expanded_answer(question: str) -> bool:
    norm = normalize_text(question)
    expansion_keywords = [
        "chi tiet",
        "phan tich sau",
        "giai thich ky",
        "noi ro hon",
        "mo rong",
        "deep dive",
        "chi tiet hon",
    ]
    return any(keyword in norm for keyword in expansion_keywords)


def should_prefer_fast_auto(question: str, intent: str) -> bool:
    if intent in {"general_question", "hr_it"}:
        return True

    norm = normalize_text(question)
    short_question = len(norm.split()) <= 12
    if short_question and not wants_expanded_answer(question):
        return True

    quick_keywords = [
        "tom tat",
        "ngan gon",
        "quick",
        "nhanh",
        "vi tri nao nhat",
        "nen hoc them ky nang gi",
        "phu hop voi vi tri nao nhat",
    ]
    return any(keyword in norm for keyword in quick_keywords)


def detect_response_focus(question: str, intent: str) -> str:
    norm = normalize_text(question)
    mentioned_skill = detect_skill_name(question)

    skill_keywords = [
        "ky nang gi",
        "ky nang nao",
        "nen hoc them ky nang gi",
        "can hoc them gi",
        "can hoc gi",
        "hoc gi trong",
        "can toi muc nao",
        "can biet gi",
        "muc nao la du",
        "missing skill",
        "khoang trong ky nang",
        "thieu ky nang gi",
    ]
    roadmap_keywords = [
        "roadmap",
        "lo trinh",
        "ke hoach hoc",
        "hoc trong",
        "2 thang",
        "3 thang",
        "6 thang",
    ]
    job_keywords = [
        "job",
        "jd",
        "cong viec",
        "vi tri",
        "yeu cau gi",
        "doi hoi gi",
        "ung tuyen",
    ]
    company_keywords = [
        "cong ty nao",
        "company nao",
        "hop voi cong ty nao",
        "nen dang ky vao cong ty nao",
        "hop voi cong ty nao hon",
        "cong ty nao hon",
    ]
    compare_job_keywords = [
        "job nao hon",
        "job title nao hon",
        "hop voi job nao hon",
        "hop voi job title nao hon",
        "nen apply job nao",
        "hop voi job title nao",
    ]
    role_keywords = [
        "phu hop voi role nao",
        "phu hop voi vi tri nao",
        "role nao",
        "vi tri nao nhat",
    ]

    if mentioned_skill and any(
        keyword in norm
        for keyword in [
            "hoc",
            "can",
            "muc",
            "du",
            "apply",
            "ung tuyen",
            "skill",
            "ky nang",
        ]
    ):
        return "skill_deep_dive"

    if intent == "career_advice":
        if mentioned_skill and any(
            keyword in norm
            for keyword in [
                "hoc",
                "can",
                "muc",
                "du",
                "gioi",
                "biet",
                "skill",
                "ky nang",
            ]
        ):
            return "skill_deep_dive"
        if any(keyword in norm for keyword in company_keywords):
            return "company_or_job_fit"
        if any(keyword in norm for keyword in compare_job_keywords):
            return "company_or_job_fit"
        if any(keyword in norm for keyword in roadmap_keywords):
            return "roadmap"
        if any(keyword in norm for keyword in skill_keywords):
            return "skill_deep_dive" if mentioned_skill else "skills_only"
        if any(keyword in norm for keyword in job_keywords):
            return "jobs_only"
        return "roadmap"

    if intent == "cv_analysis":
        if mentioned_skill and any(
            keyword in norm
            for keyword in [
                "hoc",
                "can",
                "muc",
                "du",
                "biet",
                "skill",
                "ky nang",
            ]
        ):
            return "skill_deep_dive"
        if any(keyword in norm for keyword in company_keywords):
            return "company_or_job_fit"
        if any(keyword in norm for keyword in compare_job_keywords):
            return "company_or_job_fit"
        if any(keyword in norm for keyword in role_keywords):
            return "role_fit"
        if any(keyword in norm for keyword in skill_keywords):
            return "skill_deep_dive" if mentioned_skill else "skills_only"
        if any(keyword in norm for keyword in job_keywords):
            return "jobs_only"
        return "role_fit"

    return "general"


@lru_cache(maxsize=1)
def available_ollama_models() -> list[str]:
    response = requests.get(OLLAMA_TAGS_URL, timeout=15)
    response.raise_for_status()
    data = response.json()
    models = data.get("models", [])
    names = [item.get("name", "") for item in models if item.get("name")]
    return names


def pick_ollama_model(model_preferences: list[str] | None = None) -> str:
    preferred = os.getenv("OLLAMA_MODEL")
    names = available_ollama_models()
    preferences = model_preferences or OLLAMA_MODEL_PREFERENCE

    if preferred:
        if preferred in names:
            return preferred
        raise RuntimeError(
            f"OLLAMA_MODEL='{preferred}' không tồn tại trên host {OLLAMA_HOST}. "
            f"Models hiện có: {', '.join(names) if names else '(trống)'}"
        )

    for candidate in preferences:
        if candidate in names:
            return candidate

    if names:
        return names[0]

    raise RuntimeError(f"Không tìm thấy model Ollama nào trên {OLLAMA_HOST}")


def detect_skill_name(question: str) -> str | None:
    norm = normalize_text(question)
    for canonical_skill, aliases in SKILL_FOCUS_ALIASES.items():
        for alias in aliases:
            if alias in norm:
                return canonical_skill
    return None


def derive_company_name_from_job(job: dict[str, Any]) -> str | None:
    job_url = str(job.get("job_url") or "").strip()
    if not job_url:
        return None

    match = re.search(r"/brand/([^/]+)/", job_url)
    if not match:
        return None

    slug = match.group(1).replace("-", " ").strip()
    if not slug:
        return None
    words = [word.upper() if word.isupper() else word.capitalize() for word in slug.split()]
    return " ".join(words)


def find_jobs_for_skill(gap_result: dict[str, Any], skill_name: str, max_jobs: int = 2) -> list[dict[str, Any]]:
    normalized_skill = normalize_text(skill_name)
    matched_jobs = []
    for job in gap_result.get("top_job_matches") or []:
        combined_skills = (
            (job.get("required_skills") or [])
            + (job.get("preferred_skills") or [])
            + (job.get("missing_skills") or [])
            + (job.get("matched_skills") or [])
        )
        combined_text = " ".join(str(item) for item in combined_skills)
        section_text = " ".join((section.get("chunk_text") or "") for section in (job.get("relevant_sections") or []))
        if normalized_skill in normalize_text(combined_text) or normalized_skill in normalize_text(section_text):
            matched_jobs.append(job)
    return matched_jobs[:max_jobs]


def rank_practical_jobs(jobs: list[dict[str, Any]], limit: int = 3) -> list[dict[str, Any]]:
    def practicality_key(job: dict[str, Any]) -> tuple[float, int, int, float]:
        experience_years = float(job.get("experience_min_years") or 0)
        missing_count = len(job.get("missing_skills") or [])
        matched_count = len(job.get("matched_skills") or [])
        score = job_score_value(job)
        return (
            experience_years,
            missing_count,
            -matched_count,
            -score,
        )

    ranked = sorted(jobs, key=practicality_key)
    return ranked[:limit]


def answer_skill_deep_dive(question: str, gap_result: dict[str, Any]) -> str | None:
    skill_name = detect_skill_name(question)
    if not skill_name:
        return None

    guide = SKILL_GUIDES.get(skill_name)
    if not guide:
        return None

    top_role = gap_result.get("top_role_result") or {}
    missing_skills = {normalize_text(skill) for skill in (gap_result.get("missing_skills") or [])}
    matched_skills = {normalize_text(skill) for skill in (gap_result.get("strengths") or [])}
    relevant_jobs = find_jobs_for_skill(gap_result, skill_name)

    if normalize_text(skill_name) in missing_skills:
        current_status = f"{skill_name} hiện là kỹ năng còn thiếu trong hướng đi {top_role.get('role', 'mục tiêu hiện tại')}."
    elif normalize_text(skill_name) in matched_skills:
        current_status = f"{skill_name} là một điểm mạnh hiện có, nhưng bạn vẫn nên nâng lên mức dùng được cho công việc thực tế."
    else:
        current_status = f"{skill_name} chưa phải tín hiệu mạnh trong CV hiện tại, nhưng vẫn đáng học nếu bạn muốn theo hướng dữ liệu."

    expanded = wants_expanded_answer(question) or any(
        keyword in normalize_text(question)
        for keyword in ["lo trinh", "4 tuan", "8 tuan", "chi tiet", "cu the hon", "tung buoc"]
    )

    if relevant_jobs:
        primary_job_title = relevant_jobs[0].get("job_title") or "job đang match gần nhất"
        primary_company = derive_company_name_from_job(relevant_jobs[0])
    else:
        primary_job_title = "job Data Analyst gần nhất"
        primary_company = None

    lines = [
        f"Với {skill_name}, mức nên có hiện tại là: {guide['level']}",
        current_status,
    ]

    if expanded:
        lines.append("Nếu học để apply thực tế, bạn nên đi theo thứ tự này:")
        for index, item in enumerate(guide["learn"][:5], start=1):
            lines.append(f"{index}. {item}")

        if relevant_jobs:
            lines.append("Trong các job đang match, kỹ năng này xuất hiện rõ ở:")
            for job in relevant_jobs:
                title = job.get("job_title") or "Không rõ job"
                required = pretty_join(job.get("required_skills") or [], limit=5)
                preferred = pretty_join(job.get("preferred_skills") or [], limit=5)
                lines.append(f"- {title}: yêu cầu chính là {required}; kỹ năng ưu tiên thêm là {preferred}.")
        else:
            lines.append("Trong các job đang match gần nhất chưa có job nào nhấn mạnh skill này một cách trực tiếp.")

        if primary_company:
            lines.append(
                f"Nếu muốn đi sâu hơn đúng bối cảnh job hiện tại, bạn có thể hỏi tiếp kiểu: "
                f"'{skill_name} cần tới mức nào để apply {primary_job_title} tại {primary_company}?' "
                f"hoặc 'Cho tôi lộ trình học {skill_name} trong 4 tuần theo context {primary_job_title} tại {primary_company}'."
            )
        else:
            lines.append(
                f"Nếu muốn đi sâu hơn đúng bối cảnh job hiện tại, bạn có thể hỏi tiếp kiểu: "
                f"'{skill_name} cần tới mức nào để apply {primary_job_title}?' "
                f"hoặc 'Cho tôi lộ trình học {skill_name} trong 4 tuần theo context {primary_job_title}'."
            )
    else:
        short_learn = pretty_join(guide["learn"][:3], limit=3)
        if relevant_jobs:
            lines.append(
                f"Nếu học để apply, bạn chỉ cần ưu tiên 3 phần trước: {short_learn}."
            )
            lines.append(
                f"Trong ngữ cảnh job hiện tại, {skill_name} đang nổi bật nhất ở {primary_job_title}."
            )
        else:
            lines.append(f"Nếu học để apply, bạn chỉ cần ưu tiên 3 phần trước: {short_learn}.")

        if primary_company:
            lines.append(
                f"Nếu muốn, bạn có thể hỏi tiếp kiểu: '{skill_name} cần tới mức nào để apply {primary_job_title} tại {primary_company}?'"
            )
        else:
            lines.append(
                f"Nếu muốn, bạn có thể hỏi tiếp kiểu: '{skill_name} cần tới mức nào để apply {primary_job_title}?'"
            )
    return "\n".join(lines)


def answer_company_or_job_fit(question: str, gap_result: dict[str, Any]) -> str:
    candidate_jobs = (gap_result.get("top_job_matches") or [])[:6]
    if not candidate_jobs:
        return "Chưa có dữ liệu job match đủ rõ để kết luận bạn hợp với job hoặc công ty nào hơn."

    top_role = gap_result.get("top_role_result") or {}
    recommended_skills = ", ".join((top_role.get("recommended_next_skills") or [])[:4]) or "các kỹ năng còn thiếu"
    best_score_job = candidate_jobs[0]
    practical_jobs = rank_practical_jobs(candidate_jobs, limit=3)
    practical_job = practical_jobs[0] if practical_jobs else best_score_job

    jobs_with_company = []
    for job in practical_jobs:
        company_name = derive_company_name_from_job(job)
        jobs_with_company.append((job, company_name))

    lines = []
    has_company_signal = any(company_name for _, company_name in jobs_with_company)

    if has_company_signal:
        lines.append("Mình kết luận chắc nhất ở mức job fit. Phần company fit chỉ nên xem là định hướng thêm, vì không phải job nào cũng có tên công ty sạch trong dữ liệu.")
    else:
        lines.append("Dữ liệu hiện tại mạnh ở mức job/JD hơn là company, nên mình sẽ ưu tiên trả lời theo job fit để thực tế hơn.")

    practical_company = derive_company_name_from_job(practical_job) if practical_job else None
    if practical_company:
        lines.append(
            f"Nếu mục tiêu là apply thực tế sớm, job title hợp lý hơn hiện tại là '{practical_job.get('job_title', 'Không rõ')}' tại {practical_company}."
        )
    else:
        lines.append(
            f"Nếu mục tiêu là apply thực tế sớm, job title hợp lý hơn hiện tại là '{practical_job.get('job_title', 'Không rõ')}'."
        )
    lines.append(
        f"Nếu chỉ nhìn theo điểm match cao nhất, job đang đứng đầu là '{best_score_job.get('job_title', 'Không rõ')}' "
        f"(điểm: {job_score_value(best_score_job):.1f})."
    )
    if practical_job.get("job_title") != best_score_job.get("job_title"):
        lines.append(
            f"Nếu xét theo khả năng apply sớm, '{practical_job.get('job_title', 'Không rõ')}' hợp hơn "
            f"vì yêu cầu kinh nghiệm khoảng {practical_job.get('experience_min_years', 0)} năm và gần với trạng thái hiện tại hơn."
        )
    else:
        lines.append(
            f"Nếu xét theo khả năng apply sớm, '{practical_job.get('job_title', 'Không rõ')}' cũng là lựa chọn hợp lý hơn trong nhóm này."
        )

    for index, (job, company_name) in enumerate(jobs_with_company[:2], start=1):
        title = job.get("job_title") or "Không rõ job"
        missing = pretty_join(job.get("missing_skills") or [], limit=5)
        matched = pretty_join(job.get("matched_skills") or [], limit=4)
        experience_years = float(job.get("experience_min_years") or 0)
        line = f"{index}. {title}"
        if company_name:
            line += f" tại {company_name}"
        line += (
            f": hợp hơn nếu bạn muốn đi đúng context của job này; hiện đã khớp {matched}, "
            f"còn thiếu chủ yếu {missing}, và job này yêu cầu khoảng {experience_years:g} năm kinh nghiệm."
        )
        lines.append(line)

    if jobs_with_company:
        lines.append("Nếu xét theo độ thực tế để apply, 3 job nên ưu tiên nhìn trước là:")
        for index, (job, company_name) in enumerate(jobs_with_company, start=1):
            title = job.get("job_title") or "Không rõ job"
            experience_years = float(job.get("experience_min_years") or 0)
            missing = pretty_join(job.get("missing_skills") or [], limit=4)
            line = f"{index}. {title}"
            if company_name:
                line += f" tại {company_name}"
            line += f" - yêu cầu khoảng {experience_years:g} năm kinh nghiệm, còn thiếu chủ yếu {missing}."
            lines.append(line)

    lines.append(f"Nếu muốn tăng khả năng apply thực tế hơn, bạn nên ưu tiên bù trước: {recommended_skills}.")

    first_job_title = jobs_with_company[0][0].get("job_title") or "job đầu tiên"
    second_job_title = jobs_with_company[1][0].get("job_title") if len(jobs_with_company) > 1 else "job thứ hai"
    first_company = jobs_with_company[0][1]
    second_company = jobs_with_company[1][1] if len(jobs_with_company) > 1 else None

    if first_company and second_company:
        lines.append(
            f"Nếu muốn, bạn có thể hỏi tiếp kiểu: 'So sánh kỹ hơn giữa {first_job_title} tại {first_company} "
            f"và {second_job_title} tại {second_company}' hoặc 'CV tôi hợp với {first_job_title} tại {first_company} hơn ở điểm nào?'."
        )
    else:
        lines.append(
            f"Nếu muốn, bạn có thể hỏi tiếp kiểu: 'So sánh kỹ hơn giữa {first_job_title} và {second_job_title}' "
            f"hoặc 'CV tôi hợp với {first_job_title} hơn ở điểm nào?'."
        )
    return "\n".join(lines)


def answer_skills_overview(gap_result: dict[str, Any]) -> str:
    top_role = gap_result.get("top_role_result") or {}
    strengths = pretty_join(gap_result.get("strengths") or [], limit=5)
    missing_skills = pretty_join(gap_result.get("missing_skills") or [], limit=6)
    recommended = pretty_join((top_role.get("recommended_next_skills") or []), limit=5)
    if recommended == "không rõ":
        recommended = missing_skills

    lines = [
        f"Ở thời điểm hiện tại, điểm mạnh nổi bật của bạn là {strengths}.",
        f"Nếu đi theo hướng {top_role.get('role', 'mục tiêu hiện tại')}, khoảng trống kỹ năng lớn nhất đang là {missing_skills}.",
        f"Thứ tự nên ưu tiên học trước là: {recommended}.",
    ]

    top_jobs = sorted(
        (gap_result.get("top_job_matches") or [])[:4],
        key=lambda job: (
            float(job.get("experience_min_years") or 0),
            -job_score_value(job),
        ),
    )[:3]
    if top_jobs:
        lines.append("Trong các job title đang match gần nhất, yêu cầu kỹ năng nổi bật là:")
        for job in top_jobs:
            title = job.get("job_title") or "Không rõ job"
            required = pretty_join(job.get("required_skills") or [], limit=5)
            preferred = pretty_join(job.get("preferred_skills") or [], limit=5)
            lines.append(f"- {title}: yêu cầu chính là {required}; ưu tiên thêm là {preferred}.")

    return "\n".join(lines)


def answer_role_fit(gap_result: dict[str, Any]) -> str:
    top_role = gap_result.get("top_role_result") or {}
    top_jobs = (gap_result.get("top_job_matches") or [])[:4]
    if not top_role:
        return "Chưa có đủ dữ liệu để kết luận vai trò phù hợp nhất từ CV hiện tại."

    practical_jobs = sorted(
        top_jobs,
        key=lambda job: (
            float(job.get("experience_min_years") or 0),
            -job_score_value(job),
        ),
    ) if top_jobs else []
    practical_job = practical_jobs[0] if practical_jobs else None
    alternative_job = practical_jobs[1] if len(practical_jobs) > 1 else None

    missing_skills = pretty_join((top_role.get("recommended_next_skills") or []), limit=5)
    lines = [
        f"Vai trò phù hợp nhất hiện tại là {top_role.get('role', 'Không rõ')} (điểm: {top_role.get('score', 'N/A')}).",
    ]

    matched_skills = pretty_join((top_role.get("matched_skills") or []), limit=4)
    lines.append(f"Lý do chính là CV hiện gần nhất với nhóm vai trò này và đã khớp {matched_skills}.")
    lines.append(f"Để apply tốt hơn, bạn nên ưu tiên bù trước: {missing_skills}.")

    if practical_job:
        lines.append(
            f"Nếu xét theo độ thực tế để apply sớm, job nên ưu tiên xem trước là '{practical_job.get('job_title', 'Không rõ')}' "
            f"vì yêu cầu khoảng {float(practical_job.get('experience_min_years') or 0):g} năm kinh nghiệm."
        )
    if alternative_job:
        lines.append(
            f"Ngoài ra, bạn cũng có thể cân nhắc thêm '{alternative_job.get('job_title', 'Không rõ')}' như một phương án gần kề tiếp theo."
        )

    return "\n".join(lines)


def answer_specialized_focus(question: str, intent: str, gap_result: dict[str, Any] | None) -> str | None:
    if not gap_result or intent not in {"cv_analysis", "career_advice"}:
        return None

    focus = detect_response_focus(question, intent)
    if focus == "skill_deep_dive":
        return answer_skill_deep_dive(question, gap_result)
    if focus == "skills_only":
        return answer_skills_overview(gap_result)
    if focus == "company_or_job_fit":
        return answer_company_or_job_fit(question, gap_result)
    if focus == "role_fit":
        return answer_role_fit(gap_result)
    return None


def build_gap_snapshot(gap_result: dict[str, Any]) -> str:
    top_role = gap_result.get("top_role_result") or {}
    best_roles = gap_result.get("best_fit_roles") or []
    strengths = gap_result.get("strengths") or []
    missing_skills = gap_result.get("missing_skills") or []
    development_plan = gap_result.get("development_plan") or []

    lines = [
        f"Vai trò mục tiêu từ CV: {gap_result.get('target_role_from_cv', 'Không rõ')}",
        f"Mức độ phù hợp lĩnh vực: {gap_result.get('domain_fit', 'Không rõ')}",
        f"Nhóm vai trò phù hợp nhất: {', '.join(best_roles[:3]) if best_roles else 'Không rõ'}",
        f"Vai trò nổi bật nhất: {top_role.get('role', 'Không rõ')} (điểm: {top_role.get('score', 'N/A')})",
        f"Điểm mạnh hiện có: {', '.join(strengths[:6]) if strengths else 'Chưa xác định'}",
        f"Kỹ năng còn thiếu: {', '.join(missing_skills[:8]) if missing_skills else 'Không rõ'}",
    ]

    if development_plan:
        lines.append(f"Kế hoạch phát triển: {' | '.join(development_plan[:4])}")

    return "\n".join(lines)


def job_score_value(job: dict[str, Any]) -> float:
    raw_score = job.get("match_score", job.get("score", 0)) or 0
    try:
        return float(raw_score)
    except (TypeError, ValueError):
        return 0.0


def compact_text(text: str, limit: int = 180) -> str:
    text = re.sub(r"\s+", " ", (text or "").strip())
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def build_relevant_job_summaries(gap_result: dict[str, Any], max_jobs: int = 3, max_sections: int = 2) -> str:
    job_matches = gap_result.get("top_job_matches") or []
    if not job_matches:
        return ""

    lines: list[str] = []
    for index, job in enumerate(job_matches[:max_jobs], start=1):
        title = job.get("job_title") or job.get("title") or "Không rõ vai trò"
        location = job.get("location") or "Không rõ địa điểm"
        family = job.get("job_family") or "Không rõ nhóm vai trò"
        score = job.get("match_score") or job.get("score") or "N/A"
        matched_skills = pretty_join(job.get("matched_skills") or [], limit=4)
        missing_skills = pretty_join(job.get("missing_skills") or [], limit=4)
        required_skills = pretty_join(job.get("required_skills") or [], limit=4)
        preferred_skills = pretty_join(job.get("preferred_skills") or [], limit=4)

        lines.extend(
            [
                f"Công việc {index}: {title}",
                f"- Địa điểm: {location}",
                f"- Nhóm nghề: {family}",
                f"- Điểm khớp: {score}",
                f"- Kỹ năng đã khớp: {matched_skills}",
                f"- Kỹ năng còn thiếu: {missing_skills}",
                f"- Kỹ năng yêu cầu: {required_skills}",
                f"- Kỹ năng ưu tiên: {preferred_skills}",
            ]
        )

        sections = job.get("relevant_sections") or []
        for section in sections[:max_sections]:
            section_type = section.get("section_type") or "mục"
            chunk_text = (section.get("chunk_text") or "").strip()
            if chunk_text:
                lines.append(f"- {section_type}: {compact_text(chunk_text)}")

    extra_sections = gap_result.get("matched_job_sections") or []
    if extra_sections:
        lines.append("Các đoạn JD liên quan:")
        for section in extra_sections[:2]:
            title = section.get("job_title") or "Không rõ vai trò"
            section_type = section.get("section_type") or "mục"
            text = (section.get("chunk_text") or "").strip()
            if text:
                lines.append(f"- {title} [{section_type}]: {compact_text(text)}")

    return "\n".join(lines)


def trim_history(history: list[dict[str, str]] | None, max_messages: int = 6) -> list[dict[str, str]]:
    if not history:
        return []
    filtered = [item for item in history if item.get("role") in {"user", "assistant"} and item.get("content")]
    return filtered[-max_messages:]


def detect_skill_name_from_history(history: list[dict[str, str]] | None) -> str | None:
    if not history:
        return None
    for item in reversed(history):
        if item.get("role") != "user":
            continue
        skill_name = detect_skill_name(item.get("content", ""))
        if skill_name:
            return skill_name
    return None


def detect_job_title_from_history(history: list[dict[str, str]] | None, gap_result: dict[str, Any] | None) -> str | None:
    if not history or not gap_result:
        return None

    job_titles = [job.get("job_title") for job in (gap_result.get("top_job_matches") or []) if job.get("job_title")]
    normalized_map = {normalize_text(title): title for title in job_titles}

    for item in reversed(history):
        content = normalize_text(item.get("content", ""))
        for normalized_title, original_title in normalized_map.items():
            if normalized_title and normalized_title in content:
                return original_title
    return None


def enrich_question_with_history(question: str, history: list[dict[str, str]] | None, gap_result: dict[str, Any] | None) -> str:
    norm = normalize_text(question)
    enriched_parts = [question]

    followup_markers = [
        "job do",
        "job nay",
        "cong ty do",
        "cong ty nay",
        "skill do",
        "ky nang do",
        "cai nay",
        "the con",
        "job ay",
    ]

    if any(marker in norm for marker in followup_markers):
        last_job_title = detect_job_title_from_history(history, gap_result)
        if last_job_title:
            enriched_parts.append(f"Ngữ cảnh job đang nói tới: {last_job_title}.")

        last_skill_name = detect_skill_name_from_history(history)
        if last_skill_name and last_skill_name.lower() not in norm:
            enriched_parts.append(f"Ngữ cảnh kỹ năng đang nói tới: {last_skill_name}.")

    return "\n".join(enriched_parts)


def build_chat_messages(
    question: str,
    intent: str,
    gap_result: dict[str, Any] | None,
    mode: str,
    history: list[dict[str, str]] | None = None,
) -> list[dict[str, str]]:
    mode_config = MODE_CONFIGS[mode]
    expanded = wants_expanded_answer(question)
    focus = detect_response_focus(question, intent)
    gap_snapshot = build_gap_snapshot(gap_result) if gap_result else ""
    market_context = build_relevant_job_summaries(
        gap_result or {},
        max_jobs=mode_config["max_jobs"],
        max_sections=mode_config["max_sections"],
    )

    system_map = {
        "cv_analysis": (
            "Bạn là cố vấn nghề nghiệp CNTT. Hãy phân tích CV dựa trên kết quả match "
            "CV với job thật. Nếu đã có top jobs và missing skills, hãy giải thích rõ vai trò "
            "phù hợp, điểm mạnh, khoảng trống kỹ năng, và đưa ra gợi ý thực tế bằng tiếng Việt có dấu. "
            "Mặc định trả lời gọn, tự nhiên, như một cố vấn nghề nghiệp đang chat trực tiếp; chỉ 3-4 ý chính và chỉ đào sâu nếu người dùng hỏi kỹ hơn. "
            "Không dùng giọng máy móc, không liệt kê dư thừa, và không khẳng định quá mức khi dữ liệu chưa đủ chắc."
        ),
        "career_advice": (
            "Bạn là cố vấn phát triển sự nghiệp CNTT. Hãy đưa ra lời khuyên thực tế, ưu tiên "
            "các yêu cầu trong job descriptions thật, và viết ngắn gọn, rõ ràng, bằng tiếng Việt có dấu. "
            "Mặc định trả lời vừa đủ, tự nhiên, giàu tính tư vấn; chỉ mở rộng khi người dùng hỏi tiếp. "
            "Không liệt kê dài dòng nếu người dùng chỉ hỏi một ý cụ thể."
        ),
        "general_question": (
            "Bạn là trợ lý hỏi đáp nghề nghiệp CNTT. Trả lời ngắn gọn, rõ ràng, dễ hiểu và tự nhiên bằng tiếng Việt có dấu."
        ),
    }
    system_prompt = system_map.get(intent, system_map["general_question"])

    messages = [{"role": "system", "content": system_prompt}]
    if gap_snapshot:
        messages.append({"role": "system", "content": f"Tóm tắt kết quả match CV:\n{gap_snapshot}"})
    if market_context:
        messages.append({"role": "system", "content": f"Tóm tắt job và các phần JD liên quan:\n{market_context}"})
    if history:
        messages.extend(trim_history(history))
    if intent == "cv_analysis":
        if focus == "skill_deep_dive":
            skill_name = detect_skill_name(question) or "kỹ năng đang hỏi"
            user_prompt = (
                f"Câu hỏi: {question}\n"
                f"Chỉ tập trung trả lời sâu về {skill_name}. Hãy nêu: mức cần có, nên học những phần nào, "
                "và gắn với đúng context của các job title đang match. Không lan sang job khác nếu không cần."
            )
        elif focus == "skills_only":
            if expanded:
                user_prompt = (
                    f"Câu hỏi: {question}\n"
                    "Chỉ tập trung trả lời về kỹ năng. Hãy nêu: 1) kỹ năng đã có 2) kỹ năng còn thiếu "
                    "3) 3-5 kỹ năng nên ưu tiên học trước 4) vì sao nên ưu tiên các kỹ năng đó. "
                    "Không liệt kê job nếu người dùng không hỏi."
                )
            else:
                user_prompt = (
                    f"Câu hỏi: {question}\n"
                    "Chỉ trả lời về kỹ năng. Hãy nêu thật ngắn: 1) kỹ năng đã có 2) kỹ năng còn thiếu "
                    "3) 3-5 kỹ năng nên học trước. Không nói về job nếu người dùng không hỏi."
                )
        elif focus == "jobs_only":
            user_prompt = (
                f"Câu hỏi: {question}\n"
                "Chỉ tập trung vào job/JD liên quan. Hãy nêu 1-2 job phù hợp nhất và các yêu cầu chính của chúng. "
                "Không mở rộng sang roadmap nếu người dùng không hỏi."
            )
        elif expanded:
            user_prompt = (
                f"Câu hỏi: {question}\n"
                "Hãy trả lời theo 4 mục rõ ràng: 1) Vai trò phù hợp nhất 2) Vì sao phù hợp/chưa phù hợp "
                "3) Kỹ năng còn thiếu 4) 2 job gần nhất đang đòi hỏi gì. Có thể giải thích kỹ hơn một chút."
            )
        else:
            user_prompt = (
                f"Câu hỏi: {question}\n"
                "Hãy trả lời rất gọn theo 4 mục: 1) Vai trò phù hợp nhất 2) Vì sao 3) Kỹ năng còn thiếu "
                "4) 1-2 job gần nhất đang đòi hỏi gì. Mỗi mục chỉ 1-2 câu."
            )
    elif intent == "career_advice":
        if focus == "skill_deep_dive":
            skill_name = detect_skill_name(question) or "kỹ năng đang hỏi"
            user_prompt = (
                f"Câu hỏi: {question}\n"
                f"Chỉ tập trung vào {skill_name}. Hãy trả lời ngắn gọn: cần tới mức nào, học gì trước, "
                "và skill này xuất hiện ở job title nào đang match."
            )
        elif focus == "skills_only":
            user_prompt = (
                f"Câu hỏi: {question}\n"
                "Chỉ tập trung vào kỹ năng nên học tiếp. Hãy trả lời ngắn gọn: 1) 3-5 kỹ năng ưu tiên "
                "2) học cái nào trước 3) vì sao. Không nói về job nếu người dùng không hỏi."
            )
        elif focus == "company_or_job_fit":
            user_prompt = (
                f"Câu hỏi: {question}\n"
                "Hãy tập trung so sánh job/company fit theo đúng context của job title đang match. "
                "Nếu dữ liệu công ty chưa đủ rõ, phải nói rõ rằng kết luận chắc hơn ở mức job fit."
            )
        elif focus == "jobs_only":
            user_prompt = (
                f"Câu hỏi: {question}\n"
                "Chỉ tập trung vào job nên ứng tuyển. Hãy nêu 1-2 job phù hợp nhất và lý do ngắn gọn. "
                "Không mở rộng sang roadmap nếu người dùng không hỏi."
            )
        elif expanded:
            user_prompt = (
                f"Câu hỏi: {question}\n"
                "Hãy trả lời theo 4 mục rõ ràng: 1) Mục tiêu gần 2) 3-5 kỹ năng ưu tiên "
                "3) Gợi ý học trong 4-8 tuần 4) Nên ứng tuyển những job nào trước. Có thể giải thích sâu hơn một chút."
            )
        else:
            user_prompt = (
                f"Câu hỏi: {question}\n"
                "Hãy trả lời ngắn gọn theo 4 mục: 1) Mục tiêu gần 2) 3 kỹ năng ưu tiên "
                "3) Gợi ý học ngắn hạn 4) Nên ứng tuyển job nào trước. Mỗi mục chỉ 1-2 câu."
            )
    else:
        user_prompt = (
            f"{question}\n"
            "Trả lời ngắn gọn, đi thẳng vào ý chính. Nếu cần thêm chi tiết, mình sẽ hỏi tiếp."
        )
    messages.append({"role": "user", "content": user_prompt})
    return messages


def ask_ollama_once(messages: list[dict[str, str]], model_name: str, temperature: float, num_predict: int, timeout: int) -> str:
    payload = {
        "model": model_name,
        "messages": messages,
        "stream": False,
        "keep_alive": "15m",
        "options": {
            "temperature": temperature,
            "num_predict": num_predict,
        },
    }
    response = requests.post(OLLAMA_CHAT_URL, json=payload, timeout=timeout)
    response.raise_for_status()
    data = response.json()
    message = data.get("message") or {}
    content = message.get("content", "").strip()
    if not content:
        raise RuntimeError("Ollama không trả về nội dung hợp lệ.")
    return content


def ask_ollama(
    question: str,
    intent: str,
    gap_result: dict[str, Any] | None,
    mode: str,
    history: list[dict[str, str]] | None = None,
) -> str:
    requested_mode = mode
    attempt_modes = [requested_mode]
    if requested_mode == "thinking":
        attempt_modes.append("fast")

    collected_errors: list[str] = []

    for attempt_mode in attempt_modes:
        mode_config = MODE_CONFIGS[attempt_mode]
        try:
            model_name = pick_ollama_model(mode_config["model_preference"])
        except Exception as exc:
            collected_errors.append(f"{attempt_mode}/model: {exc}")
            continue

        messages = build_chat_messages(question, intent, gap_result, attempt_mode, history=history)
        try:
            return ask_ollama_once(
                messages=messages,
                model_name=model_name,
                temperature=mode_config["temperature"],
                num_predict=mode_config["num_predict"],
                timeout=mode_config["timeout"],
            )
        except requests.exceptions.ReadTimeout as exc:
            collected_errors.append(
                f"{attempt_mode}/timeout(model={model_name}, timeout={mode_config['timeout']}s): {exc}"
            )
        except requests.exceptions.ConnectionError as exc:
            collected_errors.append(f"{attempt_mode}/connection(model={model_name}): {exc}")
        except Exception as exc:
            collected_errors.append(f"{attempt_mode}/other(model={model_name}): {exc}")

    raise RuntimeError(" | ".join(collected_errors))


def flatten_messages_to_prompt(messages: list[dict[str, str]]) -> str:
    prompt_lines = []
    for message in messages:
        role = message.get("role", "user").upper()
        content = message.get("content", "").strip()
        if content:
            prompt_lines.append(f"{role}:\n{content}")
    prompt_lines.append("ASSISTANT:")
    return "\n\n".join(prompt_lines)


def find_llama_cpp_binary() -> Path | None:
    env_bin = resolve_path(os.getenv("LLAMA_CPP_BIN"))
    if env_bin and env_bin.exists():
        return env_bin

    candidates = [
        BASE_DIR / "llama" / "build" / "bin" / "Release" / "llama-cli.exe",
        BASE_DIR / "llama" / "build" / "bin" / "Release" / "main.exe",
        BASE_DIR / "llama" / "llama-cli.exe",
        BASE_DIR / "llama" / "main.exe",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def find_llama_cpp_model() -> Path | None:
    env_model = resolve_path(os.getenv("LLAMA_CPP_MODEL"))
    if env_model and env_model.exists():
        return env_model

    for directory in [BASE_DIR / "models", BASE_DIR / "llama" / "models"]:
        if not directory.exists():
            continue
        for pattern in ("*.gguf", "*.ggml", "*.bin"):
            matches = sorted(directory.rglob(pattern))
            if matches:
                return matches[0]
    return None


def ask_llama_cpp(messages: list[dict[str, str]]) -> str:
    binary = find_llama_cpp_binary()
    model = find_llama_cpp_model()
    if not binary or not model:
        raise RuntimeError("llama.cpp chưa sẵn sàng: thiếu binary hoặc model.")

    prompt = flatten_messages_to_prompt(messages)
    command = [
        str(binary),
        "-m",
        str(model),
        "-p",
        prompt,
        "-n",
        "512",
        "--temp",
        "0.2",
    ]
    completed = subprocess.run(
        command,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    answer = completed.stdout.strip()
    if not answer:
        raise RuntimeError("llama.cpp không trả về kết quả.")
    return answer


def hr_shortlist_answer(gap_result: dict[str, Any]) -> str:
    top_job = (gap_result.get("top_job_matches") or [{}])[0]
    title = top_job.get("job_title") or "vai trò đang xét"
    score = job_score_value(top_job)
    matched_skills = top_job.get("matched_skills") or []
    missing_skills = top_job.get("missing_skills") or []
    experience_required = float(top_job.get("experience_min_years") or 0)

    if experience_required >= 3 and len(matched_skills) <= 1:
        verdict = "Chưa nên shortlist"
    elif score >= 60 and experience_required <= 2:
        verdict = "Nên shortlist"
    elif score >= 40:
        verdict = "Có thể shortlist có điều kiện"
    else:
        verdict = "Chưa nên shortlist"

    lines = [
        f"{verdict} cho role {title}.",
        f"Độ phù hợp hiện tại: {score:.1f}.",
        f"Điểm khớp chính: {pretty_join(matched_skills, limit=5)}.",
    ]
    if experience_required:
        lines.append(f"Job này yêu cầu khoảng {experience_required:g} năm kinh nghiệm.")
    if missing_skills:
        lines.append(f"Cần xác minh thêm: {', '.join(missing_skills[:5])}.")
    return "\n".join(lines)


def hr_screening_answer(gap_result: dict[str, Any]) -> str:
    top_job = (gap_result.get("top_job_matches") or [{}])[0]
    title = top_job.get("job_title") or "vai trò đang xét"
    missing_skills = top_job.get("missing_skills") or []
    required_skills = top_job.get("required_skills") or []

    focus_skills = (missing_skills + required_skills)[:4]
    if not focus_skills:
        focus_skills = ["SQL", "phân tích dữ liệu", "giao tiếp với stakeholder"]

    questions = [
        f"1. Ở vai trò {title}, bạn đã làm dự án nào gần nhất liên quan đến {focus_skills[0]}?",
        f"2. Bạn đã sử dụng {focus_skills[1] if len(focus_skills) > 1 else focus_skills[0]} ở mức độ nào, và kết quả đo lường ra sao?",
        f"3. Nếu gặp yêu cầu gấp về {focus_skills[2] if len(focus_skills) > 2 else focus_skills[0]}, bạn sẽ tiếp cận và ưu tiên công việc như thế nào?",
        f"4. Bạn đã từng phối hợp với ai để giao kết quả liên quan đến {focus_skills[3] if len(focus_skills) > 3 else focus_skills[0]}?",
    ]
    return "Các câu hỏi screening nên hỏi:\n" + "\n".join(questions)


def hr_summary_answer(gap_result: dict[str, Any]) -> str:
    top_job = (gap_result.get("top_job_matches") or [{}])[0]
    title = top_job.get("job_title") or "vai trò đang xét"
    score = top_job.get("match_score") or top_job.get("score") or "N/A"
    strengths = gap_result.get("strengths") or []
    missing_skills = (top_job.get("missing_skills") or [])[:4]

    lines = [
        f"Ứng viên hiện gần nhất với role {title} (điểm match: {score}).",
        f"Điểm mạnh nổi bật: {', '.join(strengths[:5]) if strengths else 'chưa rõ'}.",
    ]
    if missing_skills:
        lines.append(f"Khoảng trống cần xác minh thêm: {', '.join(missing_skills)}.")
    lines.append("Khuyến nghị: đánh giá thêm ở vòng screening trước khi ra quyết định cuối.")
    return "\n".join(lines)


def hr_onboarding_answer(gap_result: dict[str, Any]) -> str:
    plan = gap_result.get("development_plan") or []
    top_job = (gap_result.get("top_job_matches") or [{}])[0]
    title = top_job.get("job_title") or "role mục tiêu"

    lines = [f"Đề xuất onboard 30 ngày đầu cho {title}:"]
    if plan:
        for index, item in enumerate(plan[:4], start=1):
            lines.append(f"{index}. {item}")
    else:
        lines.extend(
            [
                "1. Onboard hệ thống, quy trình và các stakeholder chính.",
                "2. Review yêu cầu công việc và tài liệu hiện có.",
                "3. Làm một task nhỏ để xác minh khả năng thực thi.",
                "4. Chốt kế hoạch bổ sung kỹ năng còn thiếu trong 30-60 ngày tiếp theo.",
            ]
        )
    return "\n".join(lines)


def answer_hr_rulebased(question: str, gap_result: dict[str, Any]) -> str:
    norm = normalize_text(question)
    if any(keyword in norm for keyword in HR_SHORTLIST_KEYWORDS):
        return hr_shortlist_answer(gap_result)
    if any(keyword in norm for keyword in HR_SCREENING_KEYWORDS):
        return hr_screening_answer(gap_result)
    if any(keyword in norm for keyword in HR_SUMMARY_KEYWORDS):
        return hr_summary_answer(gap_result)
    if any(keyword in norm for keyword in HR_ONBOARDING_KEYWORDS):
        return hr_onboarding_answer(gap_result)
    return hr_summary_answer(gap_result)


def fallback_answer(question: str, intent: str, gap_result: dict[str, Any] | None, errors: list[str]) -> str:
    error_text = " | ".join(errors) if errors else "Không có thông tin lỗi chi tiết."
    focus = detect_response_focus(question, intent)

    if intent == "hr_it" and gap_result:
        return answer_hr_rulebased(question, gap_result)

    if intent in {"cv_analysis", "career_advice"} and gap_result:
        if focus == "skill_deep_dive":
            specialized = answer_skill_deep_dive(question, gap_result)
            if specialized:
                return f"{specialized}\n\nLỗi hệ thống: {error_text}"

        if focus == "company_or_job_fit":
            return f"{answer_company_or_job_fit(question, gap_result)}\n\nLỗi hệ thống: {error_text}"

        if focus == "role_fit":
            return f"{answer_role_fit(gap_result)}\n\nLỗi hệ thống: {error_text}"

        summary = build_relevant_job_summaries(gap_result, max_jobs=2, max_sections=3)
        top_role = gap_result.get("top_role_result") or {}
        strengths = ", ".join((gap_result.get("strengths") or [])[:5]) or "Chưa rõ"
        missing_skills = ", ".join((gap_result.get("missing_skills") or [])[:6]) or "Không rõ"
        recommended_skills = ", ".join((top_role.get("recommended_next_skills") or [])[:5]) or missing_skills

        if focus == "skills_only":
            return (
                "Chưa gọi được LLM nên mình trả lời ngắn theo kết quả match sẵn có.\n"
                f"Kỹ năng hiện có nổi bật: {strengths}\n"
                f"Kỹ năng còn thiếu: {missing_skills}\n"
                f"Nên ưu tiên học trước: {recommended_skills}\n\n"
                f"Lỗi hệ thống: {error_text}"
            )

        if focus == "jobs_only":
            return (
                "Chưa gọi được LLM nên mình trả lời ngắn theo các job match gần nhất.\n"
                f"{summary}\n\n"
                f"Lỗi hệ thống: {error_text}"
            )

        if intent == "cv_analysis":
            return (
                "Chưa gọi được LLM nên mình trả lời ngắn theo kết quả match sẵn có.\n"
                f"{build_gap_snapshot(gap_result)}\n\n"
                f"Các job liên quan:\n{summary}\n\n"
                f"Lỗi hệ thống: {error_text}"
            )
        return (
            "Chưa gọi được LLM nên mình gợi ý ngắn theo kết quả match sẵn có.\n"
            f"{build_gap_snapshot(gap_result)}\n\n"
            "Bạn nên ưu tiên học các missing skills và đối chiếu với 1-2 job phù hợp nhất trong danh sách trên.\n\n"
            f"Lỗi hệ thống: {error_text}"
        )

    return f"Chưa gọi được mô hình để trả lời câu hỏi này. Lỗi hệ thống: {error_text}"


def load_gap_result_from_args(path_text: str | None, intent: str) -> dict[str, Any] | None:
    path = resolve_path(path_text) if path_text else None
    if path:
        return load_json(path)

    if intent in {"cv_analysis", "career_advice", "hr_it"} and DEFAULT_GAP_RESULT_PATH.exists():
        return load_json(DEFAULT_GAP_RESULT_PATH)

    return None


def generate_response(
    question: str,
    gap_result: dict[str, Any] | None,
    requested_mode: str,
    history: list[dict[str, str]] | None = None,
) -> str:
    effective_question = enrich_question_with_history(question, history, gap_result)
    intent = classify_intent(effective_question)
    mode = resolve_mode(effective_question, intent, requested_mode)

    if intent in {"cv_analysis", "career_advice", "hr_it"} and not gap_result:
        raise ValueError(
            "Câu hỏi dạng này cần kết quả pipeline trước. "
            "Hãy chạy evaluate_cases.py hoặc truyền --gap_result tới file JSON hợp lệ."
        )

    if intent == "hr_it" and gap_result:
        return answer_hr_rulebased(effective_question, gap_result)

    specialized_answer = answer_specialized_focus(effective_question, intent, gap_result)
    if specialized_answer:
        return specialized_answer

    errors: list[str] = []

    try:
        return ask_ollama(effective_question, intent, gap_result, mode, history=history)
    except Exception as exc:
        errors.append(f"Ollama: {exc}")

    if ENABLE_LLAMA_CPP_FALLBACK:
        messages = build_chat_messages(effective_question, intent, gap_result, "fast", history=history)
        try:
            return ask_llama_cpp(messages)
        except Exception as exc:
            errors.append(f"llama.cpp: {exc}")

    return fallback_answer(effective_question, intent, gap_result, errors)


def run_interactive_session(gap_result: dict[str, Any] | None, requested_mode: str) -> None:
    history: list[dict[str, str]] = []
    print("Đã vào chế độ chat liên tục. Gõ 'exit' hoặc 'quit' để thoát.")
    print("Chatbot sẽ giữ ngữ cảnh CV hiện tại và vài lượt trao đổi gần nhất trong phiên này.")

    while True:
        try:
            question = input("Bạn: ").strip()
        except EOFError:
            print("\nKết thúc phiên chat.")
            break

        if not question:
            continue
        if normalize_text(question) in {"exit", "quit"}:
            print("Kết thúc phiên chat.")
            break

        answer = generate_response(question, gap_result, requested_mode, history=history)
        print(f"Bot: {answer}")
        history.append({"role": "user", "content": question})
        history.append({"role": "assistant", "content": answer})
        history[:] = trim_history(history, max_messages=8)


def main() -> None:
    parser = argparse.ArgumentParser(description="Career chatbot router")
    parser.add_argument("--question", required=True, help="Cau hoi nguoi dung")
    parser.add_argument(
        "--mode",
        choices=["auto", "fast", "thinking"],
        default="auto",
        help="Che do tra loi. 'fast' uu tien toc do, 'thinking' uu tien phan tich, 'auto' tu chon theo intent.",
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Bat che do chat nhieu luot trong cung mot session de giu ngu canh CV va lich su hoi dap.",
    )
    parser.add_argument(
        "--gap_result",
        help="Duong dan toi output JSON cua pipeline CV -> job matching. Neu bo trong, se thu doc file mac dinh.",
    )
    args = parser.parse_args()

    question = args.question.strip()
    preload_intent = classify_intent(question)
    gap_result = load_gap_result_from_args(args.gap_result, preload_intent)

    if args.interactive:
        print(generate_response(question, gap_result, args.mode, history=[]))
        run_interactive_session(gap_result, args.mode)
        return

    print(generate_response(question, gap_result, args.mode, history=[]))


import sys

for idx, arg in enumerate(sys.argv):
    if arg == "--mode" and idx + 1 < len(sys.argv):
        CURRENT_MODE = sys.argv[idx + 1].strip().lower()
        break

_ORIGINAL_ANSWER_ROLE_FIT = answer_role_fit
_ORIGINAL_ANSWER_SKILLS_OVERVIEW = answer_skills_overview
_ORIGINAL_ANSWER_COMPANY_OR_JOB_FIT = answer_company_or_job_fit
_ORIGINAL_CLASSIFY_INTENT = classify_intent
_ORIGINAL_DETECT_FOCUS = globals().get("detect_focus")


def answer_role_fit(*args, **kwargs):
    response = _ORIGINAL_ANSWER_ROLE_FIT(*args, **kwargs)
    if is_fast_mode():
        return trim_to_top_lines(response, 4)
    if is_thinking_mode():
        extra = (
            "\n\nNếu nhìn theo hướng apply thực tế, bạn nên chia làm 2 tầng:\n"
            "1. Nhóm job dễ vào trước để lấy kinh nghiệm thực chiến.\n"
            "2. Nhóm job đòi hỏi kỹ năng đầy hơn, phù hợp để nhắm tới sau khi bù SQL, Excel, Power BI và Tableau."
        )
        return response if extra.strip() in response else response + extra
    return response


def answer_skills_overview(*args, **kwargs):
    response = _ORIGINAL_ANSWER_SKILLS_OVERVIEW(*args, **kwargs)
    if is_fast_mode():
        return trim_to_top_lines(response, 3)
    if is_thinking_mode():
        response = llm_rewrite_from_base(
            response,
            "Ưu tiên giải thích ngắn theo thứ tự học trong 1-2 tháng tới và nhắc rõ 1-2 job title gần nhất."
        )
        extra = (
            "\n\nNếu học theo thứ tự để apply sớm, mình khuyên đi theo nhịp:\n"
            "Excel -> SQL -> Power BI -> Tableau.\n"
            "Sau đó mới mở rộng sang Python để cạnh tranh tốt hơn ở các job Data Analyst rộng hơn."
        )
        return response if extra.strip() in response else response + extra
    return response


def answer_company_or_job_fit(*args, **kwargs):
    question = extract_question_from_call(args, kwargs)
    gap_result = extract_gap_result_from_call(args, kwargs)
    normalized_question = normalize_text(question)
    if any(token in normalized_question for token in ["tinh hinh viec lam", "thi truong viec lam", "job market", "dang tuyen nhieu", "co hoi viec lam"]):
        response = answer_job_market_query(question, gap_result)
    elif any(token in normalized_question for token in ["doanh nghiep", "cong ty", "dn ", "dn?", "dn nao", "techcombank", "fpt", "viettel", "vin", "transcosmos"]):
        response = answer_company_jobs_query(question, gap_result)
    else:
        response = _ORIGINAL_ANSWER_COMPANY_OR_JOB_FIT(*args, **kwargs)
    if is_fast_mode():
        return trim_to_top_lines(response, 6)
    if is_thinking_mode():
        extra = (
            "\n\nCách đọc kết quả này:\n"
            "- Job điểm cao nhất chưa chắc là job nên apply đầu tiên.\n"
            "- Nên ưu tiên job vừa sức hơn để tăng xác suất phỏng vấn.\n"
            "- Sau khi bù kỹ năng lõi, bạn mới nên đẩy sang các job nặng domain hoặc seniority hơn."
        )
        return response if extra.strip() in response else response + extra
    return response


def detect_focus(*args, **kwargs):
    question = extract_question_from_call(args, kwargs)
    normalized_question = normalize_text(question)
    if any(token in normalized_question for token in ["tinh hinh viec lam", "thi truong viec lam", "job market", "dang tuyen nhieu", "co hoi viec lam", "doanh nghiep", "cong ty", "dn nao"]):
        return "company_or_job_fit"
    if callable(_ORIGINAL_DETECT_FOCUS):
        return _ORIGINAL_DETECT_FOCUS(*args, **kwargs)
    return "general_question"


def classify_intent(*args, **kwargs):
    question = extract_question_from_call(args, kwargs)
    normalized_question = normalize_text(question)
    market_tokens = [
        "tinh hinh viec lam",
        "thi truong viec lam",
        "job market",
        "dang tuyen nhieu",
        "co hoi viec lam",
        "cong ty",
        "doanh nghiep",
        "dn nao",
        "techcombank",
        "viettel",
        "fpt",
        "vin",
        "transcosmos",
    ]
    if any(token in normalized_question for token in market_tokens):
        return "company_or_job_fit"
    return _ORIGINAL_CLASSIFY_INTENT(*args, **kwargs)


_ORIGINAL_ANSWER_SKILL_DEEP_DIVE = answer_skill_deep_dive


def answer_skill_deep_dive(*args, **kwargs):
    response = _ORIGINAL_ANSWER_SKILL_DEEP_DIVE(*args, **kwargs)
    if is_fast_mode():
        return trim_to_top_lines(response, 4)
    if is_thinking_mode():
        rewritten = llm_rewrite_from_base(
            response,
            "Hãy giải thích rõ mức độ cần có của kỹ năng, cách học ngắn hạn, và bám đúng job title đang được nhắc tới."
        )
        if rewritten != response:
            return rewritten
        return response
    return response


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"[chat_router] ERROR: {exc}")
        sys.exit(0)
