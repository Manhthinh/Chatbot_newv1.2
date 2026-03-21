from __future__ import annotations

import argparse
import ast
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

if sys.platform == "win32":
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")


BASE_DIR = Path(__file__).resolve().parents[2]
REPO_ROOT = BASE_DIR.parents[1]
DEFAULT_OUTPUT_PATH = BASE_DIR / "data" / "processed" / "gap_analysis_result.json"
DEFAULT_CV_JSON = BASE_DIR / "data" / "processed" / "resume_extracted.json"
DEFAULT_JOBS_READY = REPO_ROOT / "outputs_preprocessing_v2" / "artifacts" / "jobs_chatbot_ready_v2.parquet"
DEFAULT_JOBS_SECTIONS = REPO_ROOT / "outputs_preprocessing_v2" / "artifacts" / "jobs_chatbot_sections_v2.parquet"


ROLE_ALIASES = {
    "sql": "SQL",
    "excel": "Excel",
    "power bi": "Power BI",
    "powerbi": "Power BI",
    "tableau": "Tableau",
    "python": "Python",
    "pandas": "Pandas",
    "numpy": "NumPy",
    "statistics": "Statistics",
    "machine learning": "Machine Learning",
    "deep learning": "Deep Learning",
    "pytorch": "PyTorch",
    "tensorflow": "TensorFlow",
    "scikit-learn": "Scikit-learn",
    "sklearn": "Scikit-learn",
    "spark": "Spark",
    "airflow": "Airflow",
    "etl": "ETL",
    "data warehouse": "Data Warehouse",
    "nlp": "NLP",
    "computer vision": "Computer Vision",
    "dashboard": "Dashboarding",
    "data visualization": "Data Visualization",
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
    "data governance": "Data Governance",
    "business analysis": "Business Analysis",
    "project management": "Project Management",
    "ai": "AI",
}


ROLE_KEYWORD_HINTS = {
    "Data Analyst": ["sql", "excel", "power bi", "tableau", "statistics", "dashboard", "analysis"],
    "Data Engineer": ["python", "sql", "etl", "airflow", "spark", "data warehouse", "pipeline"],
    "AI Engineer": ["python", "machine learning", "deep learning", "pytorch", "tensorflow", "llm", "rag"],
    "AI Researcher": ["machine learning", "deep learning", "research", "experiment", "paper", "statistics"],
    "Data Scientist": ["python", "machine learning", "statistics", "pandas", "numpy", "modeling"],
    "Data Governance Specialist": ["data governance", "sql", "etl", "data warehouse", "metadata"],
    "Business Analyst": ["business analysis", "excel", "sql", "dashboard", "reporting"],
}


def resolve_path(path: str) -> Path:
    p = Path(path)
    if p.exists():
        return p

    p_from_base = BASE_DIR / path
    if p_from_base.exists():
        return p_from_base

    return p


def load_json(path: Path) -> Dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def normalize_skill(skill: str) -> str:
    s = str(skill).strip().lower()
    return ROLE_ALIASES.get(s, skill.strip())


def normalize_skill_list(skills: List[str]) -> List[str]:
    result = []
    seen = set()
    for skill in skills:
        normalized = normalize_skill(skill)
        key = normalized.lower()
        if key and key not in seen:
            seen.add(key)
            result.append(normalized)
    return result


def normalize_text(text: str) -> str:
    return " ".join(str(text).strip().lower().split())


def safe_parse_experience(value: Any) -> int:
    try:
        if value is None:
            return 0
        text = str(value).strip().lower()
        if text in ["unknown", "", "none", "null", "nan"]:
            return 0
        return int(float(text))
    except Exception:
        return 0


def parse_list_field(value: Any) -> List[str]:
    if value is None:
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
                raw_items = parsed if isinstance(parsed, list) else [stripped]
            except (ValueError, SyntaxError):
                raw_items = [part.strip() for part in stripped.split(",")]
        else:
            raw_items = [part.strip() for part in stripped.split(",")]
    else:
        raw_items = [value]

    cleaned = []
    seen = set()
    for item in raw_items:
        text = str(item).strip()
        if not text:
            continue
        normalized = normalize_skill(text)
        key = normalized.lower()
        if key not in seen:
            seen.add(key)
            cleaned.append(normalized)
    return cleaned


def parse_profile(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return {}
        try:
            parsed = ast.literal_eval(stripped)
            return parsed if isinstance(parsed, dict) else {}
        except (ValueError, SyntaxError):
            return {}
    return {}


def infer_role_name(job_title: str, job_family: str) -> str:
    title = normalize_text(job_title)
    family = normalize_text(job_family)

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


def compute_role_alignment(cv_info: Dict, role_name: str, job_title: str) -> float:
    target_role = normalize_text(cv_info.get("target_role", ""))
    if target_role and target_role != "unknown" and target_role == normalize_text(role_name):
        return 1.0

    text_parts = []
    text_parts.extend(cv_info.get("skills", []))
    text_parts.extend(cv_info.get("projects", []))
    text_parts.extend(cv_info.get("education_signals", []))
    text_parts.append(cv_info.get("raw_text_preview", ""))
    text_parts.append(job_title)
    joined = " ".join(normalize_text(x) for x in text_parts if x)

    hints = ROLE_KEYWORD_HINTS.get(role_name, [])
    if not hints:
        return 0.2

    hits = sum(1 for hint in hints if normalize_text(hint) in joined)
    if hits == 0:
        return 0.2 if target_role == "unknown" else 0.0
    return min(hits / max(len(hints), 1) + 0.15, 1.0)


def compute_experience_score(cv_experience_years: Any, min_years: Any) -> float:
    cv_years = safe_parse_experience(cv_experience_years)
    required_years = safe_parse_experience(min_years)

    if required_years == 0:
        return 1.0 if cv_years >= 0 else 0.6
    if cv_years >= required_years:
        return 1.0
    if cv_years + 1 >= required_years:
        return 0.7
    if cv_years > 0:
        return 0.45
    return 0.25


def build_section_index(sections_df: pd.DataFrame) -> Dict[str, List[Dict[str, Any]]]:
    index: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for _, row in sections_df.iterrows():
        job_url = str(row.get("job_url", "")).strip()
        if not job_url:
            continue
        index[job_url].append(
            {
                "section_type": str(row.get("section_type", "")),
                "chunk_order": int(row.get("chunk_order", 0)),
                "chunk_text": str(row.get("chunk_text", "")),
                "importance_weight": float(row.get("importance_weight", 0.0)),
            }
        )

    for job_url in index:
        index[job_url].sort(key=lambda item: (-(item["importance_weight"]), item["chunk_order"]))
    return index


def select_relevant_sections(
    sections: List[Dict[str, Any]],
    cv_skills_norm: set[str],
    target_role: str,
    limit: int = 3,
) -> List[Dict[str, Any]]:
    scored = []
    target_role_norm = normalize_text(target_role)
    for item in sections:
        text_norm = normalize_text(item["chunk_text"])
        skill_hits = sum(1 for skill in cv_skills_norm if skill in text_norm)
        role_hit = 1 if target_role_norm and target_role_norm != "unknown" and target_role_norm in text_norm else 0
        section_bonus = 0.0
        if item["section_type"] == "requirements":
            section_bonus = 1.0
        elif item["section_type"] == "description":
            section_bonus = 0.5

        score = item["importance_weight"] + skill_hits * 1.5 + role_hit + section_bonus
        scored.append({**item, "score": score})

    scored.sort(key=lambda item: (-item["score"], item["chunk_order"]))
    return scored[:limit]


def build_development_plan(missing_skills: List[str], matched_jobs: List[Dict[str, Any]]) -> List[str]:
    plan = []
    for skill in missing_skills[:4]:
        plan.append(f"Học hoặc củng cố {skill}")

    for job in matched_jobs[:2]:
        if len(plan) >= 5:
            break
        title = job.get("job_title", "")
        if title:
            plan.append(f"Đọc kỹ JD '{title}' và làm 1 mini-project bám theo yêu cầu chính")

    return plan[:5]


def match_cv_to_jobs(cv_info: Dict, ready_df: pd.DataFrame, sections_df: pd.DataFrame) -> Dict[str, Any]:
    cv_skills = normalize_skill_list(cv_info.get("skills", []))
    cv_skills_norm = {skill.lower() for skill in cv_skills}
    target_role = str(cv_info.get("target_role", "Unknown")).strip() or "Unknown"
    target_role_norm = normalize_text(target_role)
    section_index = build_section_index(sections_df)

    job_matches = []
    role_buckets: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

    for _, row in ready_df.iterrows():
        profile = parse_profile(row.get("job_chatbot_profile"))
        job_title = str(row.get("job_title_display", "")).strip()
        job_family = str(row.get("job_family", "")).strip()
        job_role = infer_role_name(job_title, job_family)
        if job_role == "Other":
            continue

        required_skills = parse_list_field(row.get("skills_required"))
        preferred_skills = parse_list_field(row.get("skills_preferred"))
        if profile:
            required_skills = required_skills or parse_list_field(profile.get("skills_required"))
            preferred_skills = preferred_skills or parse_list_field(profile.get("skills_preferred"))

        all_job_skills = normalize_skill_list(required_skills + preferred_skills)
        all_job_skill_norm = {skill.lower() for skill in all_job_skills}
        matched_skills = [skill for skill in all_job_skills if skill.lower() in cv_skills_norm]
        missing_skills = [skill for skill in all_job_skills if skill.lower() not in cv_skills_norm]

        required_coverage = len([skill for skill in required_skills if normalize_skill(skill).lower() in cv_skills_norm]) / max(len(required_skills), 1) if required_skills else 0.0
        preferred_coverage = len([skill for skill in preferred_skills if normalize_skill(skill).lower() in cv_skills_norm]) / max(len(preferred_skills), 1) if preferred_skills else 0.0
        all_coverage = len(matched_skills) / max(len(all_job_skills), 1) if all_job_skills else 0.0
        role_alignment = compute_role_alignment(cv_info, job_role, job_title)
        experience_score = compute_experience_score(
            cv_info.get("experience_years", "Unknown"),
            profile.get("experience_min_years"),
        )

        final_score = (
            0.45 * required_coverage
            + 0.2 * preferred_coverage
            + 0.2 * role_alignment
            + 0.15 * experience_score
        )

        if not all_job_skills:
            final_score = max(final_score, 0.25 * role_alignment + 0.1 * experience_score)

        score_pct = round(final_score * 100, 2)

        job_url = str(row.get("job_url", "")).strip()
        relevant_sections = select_relevant_sections(
            section_index.get(job_url, []),
            cv_skills_norm,
            target_role_norm,
            limit=3,
        )

        job_result = {
            "job_title": job_title,
            "role_name": job_role,
            "job_family": job_family,
            "job_url": job_url,
            "location": str(row.get("location_norm", "unknown")),
            "work_mode": str(row.get("work_mode", "unknown")),
            "score": score_pct,
            "required_skills": required_skills,
            "preferred_skills": preferred_skills,
            "matched_skills": matched_skills,
            "missing_skills": missing_skills,
            "experience_min_years": profile.get("experience_min_years", 0),
            "education_level_norm": profile.get("education_level_norm", ""),
            "job_text_chatbot": str(row.get("job_text_chatbot", "")),
            "relevant_sections": relevant_sections,
        }

        job_matches.append(job_result)
        role_buckets[job_role].append(job_result)

    job_matches.sort(key=lambda item: item["score"], reverse=True)

    role_ranking = []
    for role_name, jobs in role_buckets.items():
        sorted_jobs = sorted(jobs, key=lambda item: item["score"], reverse=True)
        top_jobs = sorted_jobs[:3]
        matched_counter = Counter()
        missing_counter = Counter()
        for job in top_jobs:
            matched_counter.update(job["matched_skills"])
            missing_counter.update(job["missing_skills"])

        role_ranking.append(
            {
                "role_name": role_name,
                "role": role_name,
                "score": round(sum(job["score"] for job in top_jobs) / max(len(top_jobs), 1), 2),
                "skill_overlap_score": round(sum(len(job["matched_skills"]) / max(len(job["required_skills"]) + len(job["preferred_skills"]), 1) for job in top_jobs) / max(len(top_jobs), 1), 4),
                "keyword_match_score": round(sum(compute_role_alignment(cv_info, role_name, job["job_title"]) for job in top_jobs) / max(len(top_jobs), 1), 4),
                "experience_score": round(sum(compute_experience_score(cv_info.get("experience_years", "Unknown"), job["experience_min_years"]) for job in top_jobs) / max(len(top_jobs), 1), 4),
                "target_role_match_score": 1.0 if normalize_text(role_name) == target_role_norm and target_role_norm != "unknown" else 0.0,
                "matched_skills": [skill for skill, _ in matched_counter.most_common(8)],
                "missing_skills": [skill for skill, _ in missing_counter.most_common(12)],
                "recommended_next_skills": [skill for skill, _ in missing_counter.most_common(8)],
                "top_jobs": [job["job_title"] for job in top_jobs],
            }
        )

    role_ranking.sort(key=lambda item: item["score"], reverse=True)

    top_jobs = job_matches[:5]
    top_role = role_ranking[0] if role_ranking else {
        "role_name": target_role,
        "role": target_role,
        "score": 0.0,
        "matched_skills": [],
        "missing_skills": [],
        "recommended_next_skills": [],
    }

    top_score = float(top_role.get("score", 0.0))
    if top_score >= 65:
        domain_fit = "high"
    elif top_score >= 40:
        domain_fit = "medium"
    else:
        domain_fit = "low"

    strengths_counter = Counter()
    missing_counter = Counter()
    for job in top_jobs[:3]:
        strengths_counter.update(job["matched_skills"])
    for job in top_jobs[:5]:
        missing_counter.update(job["missing_skills"])

    strengths = [skill for skill, _ in strengths_counter.most_common(8)]
    missing_skills = [skill for skill, _ in missing_counter.most_common(10)]
    best_fit_roles = [item["role_name"] for item in role_ranking[:3]]

    matched_sections = []
    for job in top_jobs[:2]:
        for section in job["relevant_sections"]:
            matched_sections.append(
                {
                    "job_title": job["job_title"],
                    "role_name": job["role_name"],
                    "section_type": section["section_type"],
                    "chunk_text": section["chunk_text"],
                    "score": round(section["score"], 3),
                }
            )

    result = {
        "target_role_from_cv": target_role,
        "domain_fit": domain_fit,
        "best_fit_roles": best_fit_roles,
        "strengths": strengths,
        "missing_skills": missing_skills,
        "development_plan": build_development_plan(missing_skills, top_jobs),
        "top_role_result": top_role,
        "role_ranking": role_ranking[:5],
        "top_job_matches": top_jobs,
        "matched_job_sections": matched_sections[:6],
        "cv_skill_count": len(cv_skills),
    }
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--cv_json",
        default=str(DEFAULT_CV_JSON),
        help=f"Path to extracted CV JSON (default: {DEFAULT_CV_JSON})",
    )
    parser.add_argument(
        "--jobs_ready_path",
        default=str(DEFAULT_JOBS_READY),
        help="Path to jobs_chatbot_ready_v2.parquet",
    )
    parser.add_argument(
        "--jobs_sections_path",
        default=str(DEFAULT_JOBS_SECTIONS),
        help="Path to jobs_chatbot_sections_v2.parquet",
    )
    parser.add_argument(
        "--output_path",
        default=str(DEFAULT_OUTPUT_PATH),
        help="Path to save result JSON",
    )
    args = parser.parse_args()

    cv_json_path = resolve_path(args.cv_json)
    jobs_ready_path = resolve_path(args.jobs_ready_path)
    jobs_sections_path = resolve_path(args.jobs_sections_path)
    output_path = resolve_path(args.output_path)

    cv_info = load_json(cv_json_path)
    ready_df = pd.read_parquet(jobs_ready_path)
    sections_df = pd.read_parquet(jobs_sections_path)

    result = match_cv_to_jobs(cv_info, ready_df, sections_df)

    print(json.dumps(result, ensure_ascii=False, indent=2))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\nSaved gap analysis result to: {output_path}")


if __name__ == "__main__":
    main()
