from __future__ import annotations

import ast
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[2]
REPO_ROOT = BASE_DIR.parents[1]
INPUT_READY_PATH = REPO_ROOT / "outputs_preprocessing_v2" / "artifacts" / "jobs_chatbot_ready_v2.parquet"
INPUT_SECTIONS_PATH = REPO_ROOT / "outputs_preprocessing_v2" / "artifacts" / "jobs_chatbot_sections_v2.parquet"
OUTPUT_PATH = BASE_DIR / "data" / "role_profiles" / "role_profiles.json"

TOP_KEYWORDS = 30

STOPWORDS = {
    "và", "là", "có", "cho", "trong", "với", "các", "một", "được", "tại",
    "the", "and", "for", "with", "from", "you", "your", "our", "will",
    "yêu", "cầu", "mô", "tả", "quyền", "lợi", "kinh", "nghiệm", "việc",
    "công", "ty", "ứng", "viên", "khả", "năng", "làm", "năm", "job",
    "company", "work", "team", "experience", "skills", "data",
    "requirements", "responsibilities", "benefits", "preferred", "title",
}

KNOWN_SKILLS = {
    "python": "Python",
    "sql": "SQL",
    "excel": "Excel",
    "power bi": "Power BI",
    "powerbi": "Power BI",
    "tableau": "Tableau",
    "pandas": "Pandas",
    "numpy": "NumPy",
    "machine learning": "Machine Learning",
    "deep learning": "Deep Learning",
    "pytorch": "PyTorch",
    "tensorflow": "TensorFlow",
    "scikit-learn": "Scikit-learn",
    "sklearn": "Scikit-learn",
    "spark": "Spark",
    "airflow": "Airflow",
    "etl": "ETL",
    "nlp": "NLP",
    "computer vision": "Computer Vision",
    "statistics": "Statistics",
    "statistical analysis": "Statistics",
    "data visualization": "Data Visualization",
    "dashboard": "Dashboarding",
    "dashboarding": "Dashboarding",
    "git": "Git",
    "docker": "Docker",
    "linux": "Linux",
    "mysql": "MySQL",
    "postgresql": "PostgreSQL",
    "postgres": "PostgreSQL",
    "mongodb": "MongoDB",
    "aws": "AWS",
    "azure": "Azure",
    "gcp": "GCP",
    "llm": "LLM",
    "rag": "RAG",
    "langchain": "LangChain",
    "streamlit": "Streamlit",
    "flask": "Flask",
    "fastapi": "FastAPI",
    "data analysis": "Data Analysis",
    "analysis": "Data Analysis",
    "annotation": "Annotation",
    "data labeling": "Data Labeling",
    "quality control": "Quality Control",
    "research": "Research",
    "experiment": "Experiment Design",
    "paper reading": "Paper Reading",
    "data warehouse": "Data Warehouse",
    "cloud": "Cloud Computing",
    "cloud computing": "Cloud Computing",
    "data governance": "Data Governance",
    "governance": "Data Governance",
    "business analysis": "Business Analysis",
    "project management": "Project Management",
    "ai": "AI",
}

ROLE_DEFAULT_SKILLS = {
    "Data Analyst": ["SQL", "Excel", "Power BI", "Python", "Statistics", "Dashboarding"],
    "Data Engineer": ["Python", "SQL", "ETL", "Airflow", "Spark", "Data Warehouse"],
    "AI Engineer": ["Python", "Machine Learning", "Deep Learning", "PyTorch", "TensorFlow", "LLM"],
    "AI Researcher": ["Research", "Paper Reading", "Experiment Design", "Machine Learning", "Deep Learning", "Statistics"],
    "Data Scientist": ["Python", "Machine Learning", "Statistics", "Pandas", "NumPy"],
    "Data Governance Specialist": ["Data Governance", "SQL", "ETL", "Data Warehouse", "Data Visualization"],
    "Business Analyst": ["Excel", "SQL", "Business Analysis", "Data Visualization", "Dashboarding"],
}


def clean_text(text: str) -> str:
    if pd.isna(text):
        return ""
    text = str(text).lower()
    text = re.sub(r"<[^>]+>", " ", text)
    text = text.replace("\xa0", " ")
    text = re.sub(r"[^a-zA-ZÀ-ỹ0-9+#./ ]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def tokenize(text: str) -> List[str]:
    text = clean_text(text)
    tokens = text.split()
    return [t for t in tokens if len(t) > 1 and t not in STOPWORDS]


def normalize_tag_to_skill(tag: str) -> str:
    key = clean_text(tag)
    return KNOWN_SKILLS.get(key, "")


def infer_recommended_next_skills(common_skills: List[str], role_name: str) -> List[str]:
    defaults = ROLE_DEFAULT_SKILLS.get(role_name, [])
    result = []
    seen = set()

    for item in common_skills + defaults:
        k = item.lower()
        if k not in seen:
            seen.add(k)
            result.append(item)

    return result[:8]


def normalize_list(value: Any) -> List[str]:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return []

    if isinstance(value, list):
        raw_items = value
    elif hasattr(value, "tolist"):
        raw_items = value.tolist()
    elif isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return []
        if stripped.startswith("[") and stripped.endswith("]"):
            try:
                parsed = ast.literal_eval(stripped)
                if isinstance(parsed, list):
                    raw_items = parsed
                else:
                    raw_items = [stripped]
            except (ValueError, SyntaxError):
                raw_items = re.split(r"[,;/|]", stripped)
        else:
            raw_items = re.split(r"[,;/|]", stripped)
    else:
        raw_items = [value]

    result = []
    seen = set()
    for item in raw_items:
        if item is None:
            continue
        text = str(item).strip()
        if not text:
            continue
        skill = normalize_tag_to_skill(text) or text
        key = skill.lower()
        if key not in seen:
            seen.add(key)
            result.append(skill)
    return result


def infer_role_name(job_title: str, job_family: str) -> str:
    title = clean_text(job_title)
    family = clean_text(job_family)

    if "research" in title:
        return "AI Researcher"
    if "data scientist" in title:
        return "Data Scientist"
    if any(x in title for x in ["ai engineer", "ml engineer", "machine learning engineer", "llm engineer"]):
        return "AI Engineer"
    if "data engineer" in title:
        return "Data Engineer"
    if "analytics engineer" in title:
        return "Data Analyst"
    if "data governance" in title or "governance" in family:
        return "Data Governance Specialist"
    if "business analyst" in title or family == "product_project_ba":
        return "Business Analyst"
    if "data analyst" in title or family == "data_analytics":
        return "Data Analyst"

    family_map = {
        "data_engineering": "Data Engineer",
        "data_science_ml": "Data Scientist",
        "data_governance_quality": "Data Governance Specialist",
        "product_project_ba": "Business Analyst",
        "data_analytics": "Data Analyst",
    }
    if family in family_map:
        return family_map[family]

    if "analyst" in title:
        return "Data Analyst"
    if "engineer" in title:
        return "Data Engineer"

    return "Other"


def format_experience_pattern(value: Any) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return ""

    if number <= 0:
        return "0 năm"
    if number.is_integer():
        return f"{int(number)} năm"
    return f"{number:.1f} năm"


def build_role_profiles_from_artifacts(
    jobs_ready_path: Path = INPUT_READY_PATH,
    jobs_sections_path: Path = INPUT_SECTIONS_PATH,
) -> Dict[str, Dict]:
    ready_df = pd.read_parquet(jobs_ready_path)
    sections_df = pd.read_parquet(jobs_sections_path)

    role_stats: Dict[str, Dict[str, Any]] = defaultdict(
        lambda: {
            "job_count": 0,
            "skill_counter": Counter(),
            "keyword_counter": Counter(),
            "experience_counter": Counter(),
        }
    )

    for _, row in ready_df.iterrows():
        role_name = infer_role_name(
            row.get("job_title_display", ""),
            row.get("job_family", ""),
        )
        if role_name == "Other":
            continue

        stats = role_stats[role_name]
        stats["job_count"] += 1

        skills = normalize_list(row.get("skills_required")) + normalize_list(row.get("skills_preferred"))
        profile = row.get("job_chatbot_profile", {})
        if isinstance(profile, dict):
            skills += normalize_list(profile.get("skills_required"))
            skills += normalize_list(profile.get("skills_preferred"))

            exp_text = format_experience_pattern(profile.get("experience_min_years"))
            if exp_text:
                stats["experience_counter"][exp_text] += 1

        for skill in skills:
            normalized = normalize_tag_to_skill(skill) or skill
            stats["skill_counter"][normalized] += 1

    for _, row in sections_df.iterrows():
        role_name = infer_role_name(
            row.get("job_title_display", ""),
            row.get("job_family", ""),
        )
        if role_name == "Other":
            continue

        chunk_text = row.get("chunk_text", "")
        for token in tokenize(chunk_text):
            if token not in KNOWN_SKILLS:
                role_stats[role_name]["keyword_counter"][token] += 1

    role_profiles: Dict[str, Dict] = {}
    for role_name, stats in role_stats.items():
        common_skills = [skill for skill, _ in stats["skill_counter"].most_common()]
        if not common_skills:
            common_skills = ROLE_DEFAULT_SKILLS.get(role_name, [])

        common_keywords = [kw for kw, _ in stats["keyword_counter"].most_common(TOP_KEYWORDS)]
        common_experience = [exp for exp, _ in stats["experience_counter"].most_common(5)]

        role_profiles[role_name] = {
            "role_name": role_name,
            "job_count": int(stats["job_count"]),
            "common_skills": common_skills,
            "common_keywords": common_keywords,
            "common_experience_patterns": common_experience,
            "recommended_next_skills": infer_recommended_next_skills(common_skills, role_name),
        }

    return dict(sorted(role_profiles.items()))


def save_role_profiles(role_profiles: Dict[str, Dict], output_path: Path = OUTPUT_PATH) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(role_profiles, f, ensure_ascii=False, indent=2)


def main() -> None:
    print("Reading ready artifact from:", INPUT_READY_PATH)
    print("Reading section artifact from:", INPUT_SECTIONS_PATH)
    print("Writing output to:", OUTPUT_PATH)

    role_profiles = build_role_profiles_from_artifacts()
    save_role_profiles(role_profiles, OUTPUT_PATH)

    print(f"Saved role profiles to: {OUTPUT_PATH}")
    print(json.dumps(role_profiles, ensure_ascii=True, indent=2)[:3000])


if __name__ == "__main__":
    main()
