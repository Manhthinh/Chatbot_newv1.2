# src/cv_processing/extract_cv_info.py

from __future__ import annotations

import ast
import csv
import io
import json
import os
import re
import sys
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Dict, List

import fitz  # PyMuPDF
from docx import Document


if sys.platform == "win32" and hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")


BASE_DIR = Path(__file__).resolve().parents[2]
SKILL_CATALOG_PATH = BASE_DIR / "data" / "skill_catalog.json"
RESUME_DATA_PATH = BASE_DIR / "data" / "raw" / "resume_data.csv"

SKILL_VOCAB = [
    "python", "sql", "excel", "power bi", "powerbi", "tableau",
    "pandas", "numpy", "machine learning", "deep learning",
    "pytorch", "tensorflow", "scikit-learn", "sklearn",
    "spark", "hadoop", "airflow", "etl", "nlp", "computer vision",
    "statistics", "data visualization", "dashboard", "dashboarding",
    "git", "docker", "linux", "mysql", "postgresql", "postgres",
    "mongodb", "aws", "azure", "gcp", "llm", "rag", "langchain",
    "streamlit", "flask", "fastapi", "power query",
    "google sheets", "seo", "canva", "figma", "axure", "bpmn",
    "erd", "use case", "amazon ppc", "facebook ads", "tiktok ads"
]

HEURISTIC_SKILL_ALIASES = {
    "Excel": ["excel", "google sheets", "spreadsheet", "spreadsheets"],
    "Power BI": ["power bi", "powerbi"],
    "Tableau": ["tableau"],
    "Python": ["python"],
    "SQL": ["sql", "mysql", "postgres", "postgresql", "rdbms", "nosql"],
    "Statistics": ["statistics", "statistical", "thống kê", "xac suat thong ke"],
    "Data Visualization": ["dashboard", "visualization", "visualize data", "data visualization", "reporting"],
    "Machine Learning": ["machine learning", "ml engineer", "predictive modeling"],
    "Deep Learning": ["deep learning"],
    "NLP": ["nlp", "natural language processing"],
    "Computer Vision": ["computer vision", "machine vision", "camera ai"],
    "Docker": ["docker"],
    "ETL": ["etl", "data pipeline", "data warehouse"],
    "Airflow": ["airflow", "apache airflow"],
    "Spark": ["spark", "apache spark"],
    "Hadoop": ["hadoop"],
    "AWS": ["aws", "amazon web services"],
    "Azure": ["azure"],
    "GCP": ["gcp", "google cloud"],
    "Git": ["git", "github", "gitlab"],
    "Figma": ["figma"],
    "Canva": ["canva"],
    "SEO": ["seo", "listing optimisation", "listing optimization"],
}

CONTEXTUAL_SKILL_RULES = {
    "Excel": ["google sheets", "spreadsheet", "bao cao", "report", "reporting"],
    "Data Visualization": ["dashboard", "visualize", "visualization", "report", "insight"],
    "Statistics": ["data science", "thống kê", "statistics", "toán", "mathematics"],
    "SEO": ["seo", "listing optimisation", "listing optimization"],
    "Canva": ["canva"],
}


ROLE_KEYWORDS = {
    "Data Analyst": [
        "data analyst",
        "bi analyst",
        "business intelligence",
        "power bi",
        "tableau",
        "dashboard",
        "data analysis",
        "phan tich du lieu",
        "reporting",
    ],
    "Data Engineer": [
        "data engineer",
        "etl",
        "data pipeline",
        "data warehouse",
        "airflow",
        "spark",
        "database",
    ],
    "AI Engineer": [
        "ai engineer",
        "machine learning engineer",
        "ml engineer",
        "model deployment",
        "llm",
        "tri tue nhan tao",
    ],
    "AI Researcher": [
        "ai researcher",
        "research scientist",
        "research assistant",
        "paper",
        "experiment"
    ],
    "Data Scientist": [
        "data scientist",
        "machine learning",
        "predictive modeling",
        "statistical modeling",
        "data science",
        "khoa hoc du lieu",
    ],
    "Business Analyst": [
        "business analyst",
        "business analysis",
        "requirement gathering",
        "stakeholder",
        "bpmn",
        "uml",
        "use case",
        "erd",
    ],
    "Data Governance Specialist": [
        "data governance",
        "data quality",
        "metadata",
        "data security"
    ],
}
EDUCATION_KEYWORDS = [
    "university", "college", "đại học", "cao đẳng", "bachelor", "master",
    "cử nhân", "thạc sĩ", "khoa học dữ liệu", "data science", "computer science",
    "information technology", "công nghệ thông tin"
]

PROJECT_HINT_KEYWORDS = [
    "project", "dự án", "dashboard", "amazon", "tiktok", "facebook ads",
    "ppc", "seo", "brand", "platform", "seller centre", "seller center"
]


def normalize_lookup(text: str) -> str:
    text = text or ""
    text = unicodedata.normalize("NFD", text.lower())
    text = "".join(char for char in text if unicodedata.category(char) != "Mn")
    text = text.replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def has_phrase(text: str, phrase: str) -> bool:
    normalized_text = f" {normalize_lookup(text)} "
    normalized_phrase = f" {normalize_lookup(phrase)} "
    return normalized_phrase in normalized_text


def merge_broken_lines(lines: List[str]) -> List[str]:
    merged: List[str] = []
    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue

        if not merged:
            merged.append(line)
            continue

        is_continuation = (
            len(line) < 80
            and not re.match(r"^\d+[.)]\s*", line)
            and line[:1].islower()
        ) or line.startswith(("(", ",", ".", ":", ";", "-", "/"))

        if is_continuation:
            merged[-1] = f"{merged[-1]} {line}".strip()
        else:
            merged.append(line)

    return merged


def read_pdf(file_path: str) -> str:
    doc = fitz.open(file_path)
    pages = [page.get_text() for page in doc]
    return "\n".join(pages)


def read_docx(file_path: str) -> str:
    doc = Document(file_path)
    paragraphs = [p.text for p in doc.paragraphs]
    return "\n".join(paragraphs)


def read_txt(file_path: str) -> str:
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


def resolve_cv_path(file_path: str) -> Path:
    path = Path(file_path)
    if path.exists() and path.is_file():
        return path

    if path.exists() and path.is_dir():
        siblings = sorted(path.parent.glob(f"{path.name}*.pdf"))
        for sibling in siblings:
            if sibling.is_file():
                return sibling
        raise FileNotFoundError(f"'{file_path}' exists but is not a readable file.")

    if not path.suffix:
        for candidate in [path.with_suffix(".pdf"), path.with_suffix(".docx"), path.with_suffix(".txt")]:
            if candidate.exists() and candidate.is_file():
                return candidate

    raise FileNotFoundError(f"CV file not found: {file_path}")


def load_cv_text(file_path: str) -> str:
    resolved_path = resolve_cv_path(file_path)
    ext = resolved_path.suffix.lower()
    if ext == ".pdf":
        return read_pdf(str(resolved_path))
    if ext == ".docx":
        return read_docx(str(resolved_path))
    if ext == ".txt":
        return read_txt(str(resolved_path))
    raise ValueError(f"Unsupported CV format: {ext}")


def normalize_text(text: str) -> str:
    text = text.replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def extract_email(text: str) -> str:
    match = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)
    return match.group(0) if match else ""


def extract_phone(text: str) -> str:
    match = re.search(r"(\+?\d[\d\s\-().]{8,}\d)", text)
    return match.group(0).strip() if match else ""

def parse_list_literal(raw_value: str) -> List[str]:
    if not raw_value:
        return []

    text = str(raw_value).strip()
    if not text:
        return []

    try:
        parsed = ast.literal_eval(text)
    except (ValueError, SyntaxError):
        return []

    if not isinstance(parsed, list):
        return []

    result = []
    for item in parsed:
        if item is None:
            continue
        cleaned = str(item).strip()
        if cleaned:
            result.append(cleaned)
    return result


@lru_cache(maxsize=1)
def load_resume_dataset_skill_aliases() -> Dict[str, List[str]]:
    if not RESUME_DATA_PATH.exists():
        return {}

    with open(SKILL_CATALOG_PATH, "r", encoding="utf-8") as f:
        base_catalog: Dict[str, List[str]] = json.load(f)

    base_alias_lookup: Dict[str, str] = {}
    for canonical_skill, aliases in base_catalog.items():
        base_alias_lookup[canonical_skill.lower()] = canonical_skill
        for alias in aliases:
            base_alias_lookup[alias.lower()] = canonical_skill

    alias_map: Dict[str, set[str]] = {}
    with open(RESUME_DATA_PATH, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            for skill in parse_list_literal(row.get("skills", "")):
                cleaned_skill = skill.strip()
                key = cleaned_skill.lower()
                if not key or len(key) > 40:
                    continue

                canonical = base_alias_lookup.get(key)
                if not canonical:
                    normalized = key.replace("-", " ").replace("_", " ")
                    if normalized in base_alias_lookup:
                        canonical = base_alias_lookup[normalized]
                    elif normalized in SKILL_VOCAB:
                        canonical = cleaned_skill

                if not canonical:
                    continue

                alias_map.setdefault(canonical, set()).add(key)

    return {
        canonical: sorted(list(aliases | {canonical.lower()}))
        for canonical, aliases in alias_map.items()
    }


def load_skill_catalog() -> Dict[str, List[str]]:
    with open(SKILL_CATALOG_PATH, "r", encoding="utf-8") as f:
        catalog: Dict[str, List[str]] = json.load(f)

    for canonical_skill, aliases in load_resume_dataset_skill_aliases().items():
        if canonical_skill in catalog:
            merged = set(catalog[canonical_skill])
            merged.update(aliases)
            catalog[canonical_skill] = sorted(merged)
        else:
            catalog[canonical_skill] = aliases

    for canonical_skill, aliases in HEURISTIC_SKILL_ALIASES.items():
        existing_aliases = set(catalog.get(canonical_skill, []))
        existing_aliases.update(aliases)
        existing_aliases.add(canonical_skill.lower())
        catalog[canonical_skill] = sorted(existing_aliases)

    return catalog


def extract_skills(text: str, skill_catalog: Dict[str, List[str]]) -> List[str]:
    normalized_text = normalize_lookup(text)
    found = []

    for canonical_skill, aliases in skill_catalog.items():
        for alias in aliases:
            normalized_alias = normalize_lookup(alias)
            pattern = r"(?<!\w)" + re.escape(normalized_alias) + r"(?!\w)"
            if re.search(pattern, normalized_text):
                found.append(canonical_skill)
                break

    unique = []
    seen = set()
    for item in found:
        key = item.lower()
        if key not in seen:
            seen.add(key)
            unique.append(item)

    return unique


def infer_contextual_skills(raw_text: str, cleaned_text: str, detected_skills: List[str]) -> List[str]:
    combined_text = f"{raw_text}\n{cleaned_text}"
    normalized_text = normalize_lookup(combined_text)
    found = list(detected_skills)
    seen = {skill.lower() for skill in detected_skills}

    for canonical_skill, phrases in CONTEXTUAL_SKILL_RULES.items():
        if canonical_skill.lower() in seen:
            continue

        hits = 0
        for phrase in phrases:
            if f" {normalize_lookup(phrase)} " in f" {normalized_text} ":
                hits += 1

        if hits >= 1:
            seen.add(canonical_skill.lower())
            found.append(canonical_skill)

    return found


def guess_target_role(text: str, skills: List[str]) -> str:
    lowered = normalize_lookup(text)
    role_scores = {}
    normalized_skills = {normalize_lookup(skill) for skill in skills}

    for role, keywords in ROLE_KEYWORDS.items():
        score = 0
        for kw in keywords:
            if kw in lowered:
                score += 2
        if role == "Data Analyst":
            score += sum(1 for skill in ["sql", "excel", "power bi", "tableau", "data visualization", "statistics"] if skill in normalized_skills)
        if role == "Data Engineer":
            score += sum(1 for skill in ["sql", "etl", "airflow", "spark", "hadoop"] if skill in normalized_skills)
        if role == "AI Engineer":
            score += sum(1 for skill in ["python", "machine learning", "llm", "nlp", "computer vision"] if skill in normalized_skills)
        if role == "Data Scientist":
            score += sum(1 for skill in ["python", "statistics", "machine learning", "data visualization"] if skill in normalized_skills)
        role_scores[role] = score

    best_role = max(role_scores, key=role_scores.get)
    best_score = role_scores[best_role]

    # Nếu không có tín hiệu đủ mạnh thì trả Unknown
    if best_score < 2:
        return "Unknown"

    return best_role


def extract_education_signals(text: str) -> List[str]:
    lowered = normalize_lookup(text)
    found = [kw for kw in EDUCATION_KEYWORDS if normalize_lookup(kw) in lowered]
    # loại trùng
    result = []
    seen = set()
    for item in found:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def guess_experience_years(text: str) -> str:
    lowered = normalize_lookup(text)
    
    # tìm pattern dạng 1 year / 2 years / 3 năm
    patterns = [
        r"(\d+)\+?\s*(?:years|year)",
        r"(\d+)\+?\s*năm",
    ]
    values = []
    for pattern in patterns:
        matches = re.findall(pattern, lowered)
        for m in matches:
            try:
                values.append(int(m))
            except ValueError:
                pass

    if values:
        return str(max(values))

    # heuristic cơ bản
    if any(x in lowered for x in ["intern", "fresher", "sinh viên", "new graduate", "recent graduate"]):
        return "0"

    return "Unknown"


def summarize_projects(text: str) -> List[str]:
    lines = merge_broken_lines([line.strip() for line in text.splitlines() if line.strip()])
    result = []

    project_keywords = [normalize_lookup(keyword) for keyword in PROJECT_HINT_KEYWORDS]
    noisy_keywords = ["project management", "managed projects", "scheduling"]

    for line in lines:
        lowered = normalize_lookup(line)

        if any(k in lowered for k in noisy_keywords):
            continue

        if any(k in lowered for k in project_keywords):
            if 15 <= len(line) <= 180:
                result.append(line)
                continue

        if re.match(r"^\d+[.)]\s*", line) and 20 <= len(line) <= 220:
            result.append(line)
            continue

        if any(brand in lowered for brand in ["amazon", "tiktok", "facebook", "helium10", "seller centre", "seller center"]):
            if 20 <= len(line) <= 220:
                result.append(line)

    unique = []
    seen = set()
    for item in result:
        key = item.lower()
        if key not in seen:
            seen.add(key)
            unique.append(item)

    return unique[:5]


def extract_relevant_skill_text(raw_text: str) -> str:
    """
    Ưu tiên lấy text từ các section có khả năng chứa skill.
    Nếu không tìm thấy, fallback về toàn văn bản.
    """
    text = raw_text.replace("\r", "\n")
    lowered = text.lower()

    section_keywords = [
        "skills", "technical skills", "core competencies",
        "kỹ năng", "công cụ", "technologies", "tools", "skill", "competencies"
    ]

    lines = text.splitlines()
    selected_lines = []

    capture = False
    for line in lines:
        line_clean = line.strip()
        line_lower = line_clean.lower()

        if any(normalize_lookup(k) in normalize_lookup(line_lower) for k in section_keywords):
            capture = True
            selected_lines.append(line_clean)
            continue

        # dừng khi gặp section mới khá rõ
        if capture and any(
            x in line_lower for x in [
                "experience", "education", "summary", "about me",
                "work history", "projects", "certifications",
                "học vấn", "kinh nghiệm", "dự án"
            ]
        ):
            capture = False

        if capture and line_clean:
            selected_lines.append(line_clean)

    if selected_lines:
        return "\n".join(selected_lines)

    return raw_text


def extract_cv_info(file_path: str) -> Dict:
    resolved_path = resolve_cv_path(file_path)
    raw_text = load_cv_text(str(resolved_path))
    cleaned_text = normalize_text(raw_text)

    skill_catalog = load_skill_catalog()
    skill_text = extract_relevant_skill_text(raw_text)
    skills_from_sections = extract_skills(skill_text, skill_catalog)
    skills_from_full_text = extract_skills(raw_text, skill_catalog)
    merged_skills = []
    seen_skills = set()
    for skill in skills_from_sections + skills_from_full_text:
        key = normalize_lookup(skill)
        if key not in seen_skills:
            seen_skills.add(key)
            merged_skills.append(skill)
    skills = infer_contextual_skills(raw_text, cleaned_text, merged_skills)
    target_role = guess_target_role(cleaned_text, skills)
    education_signals = extract_education_signals(cleaned_text)
    experience_years = guess_experience_years(cleaned_text)
    projects = summarize_projects(raw_text)

    result = {
        "file_name": resolved_path.name,
        "email": extract_email(cleaned_text),
        "phone": extract_phone(cleaned_text),
        "skills": skills,
        "target_role": target_role,
        "experience_years": experience_years,
        "education_signals": education_signals,
        "projects": projects,
        "raw_text_preview": cleaned_text[:1000],
    }
    return result


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--cv_path", required=True, help="Path to CV file (.pdf, .docx, .txt)")
    parser.add_argument("--output_path", default="", help="Optional path to save extracted JSON")
    args = parser.parse_args()

    result = extract_cv_info(args.cv_path)

    print(json.dumps(result, ensure_ascii=False, indent=2))

    if args.output_path:
        with open(args.output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"Saved JSON to: {args.output_path}")


if __name__ == "__main__":
    main()
