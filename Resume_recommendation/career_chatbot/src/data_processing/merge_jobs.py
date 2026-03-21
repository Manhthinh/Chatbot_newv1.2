from __future__ import annotations

import io
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any

import pandas as pd


if sys.platform == "win32" and hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")


SCRIPT_DIR = Path(__file__).resolve().parent
SRC_DIR = SCRIPT_DIR.parent
BASE_DIR = SRC_DIR.parent
REPO_ROOT = BASE_DIR.parent.parent

READY_PATH = REPO_ROOT / "outputs_preprocessing_v2" / "artifacts" / "jobs_chatbot_ready_v2.parquet"
SECTIONS_PATH = REPO_ROOT / "outputs_preprocessing_v2" / "artifacts" / "jobs_chatbot_sections_v2.parquet"
OUTPUT_PATH = BASE_DIR / "data" / "processed" / "jobs_merged_cleaned.csv"

ROLE_MAP = {
    "data_analytics": "Data Analyst",
    "data_engineering": "Data Engineer",
    "ai_engineering": "AI Engineer",
    "ai_research": "AI Researcher",
    "data_science_ml": "Data Scientist",
    "data_governance_quality": "Data Governance Specialist",
    "product_project_ba": "Business Analyst",
    "software_engineering": "Software Engineer",
    "data_labeling": "Data Labeling",
}

TEXT_COLUMNS = [
    "title",
    "detail_title",
    "company",
    "company_name_full",
    "salary_list",
    "detail_salary",
    "detail_location",
    "detail_experience",
    "tags",
    "job_level",
    "education_level",
    "employment_type",
    "desc_mota",
    "desc_yeucau",
    "desc_quyenloi",
    "company_field",
    "company_description",
]


def is_missing_value(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, (list, tuple, dict, set)):
        return False
    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False


def clean_text(text: Any) -> str:
    if is_missing_value(text):
        return ""

    if isinstance(text, list):
        text = "\n".join(clean_text(item) for item in text if clean_text(item))
    elif isinstance(text, dict):
        text = "\n".join(f"{key}: {clean_text(value)}" for key, value in text.items() if clean_text(value))
    else:
        text = str(text)

    text = re.sub(r"<[^>]+>", " ", text)
    text = text.replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def normalize_lookup(text: Any) -> str:
    cleaned = clean_text(text).lower()
    normalized = unicodedata.normalize("NFD", cleaned)
    normalized = "".join(char for char in normalized if unicodedata.category(char) != "Mn")
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def normalize_tags(tag_value: Any) -> str:
    if is_missing_value(tag_value):
        return ""

    if isinstance(tag_value, (list, tuple, set)):
        chunks = [clean_text(item) for item in tag_value if clean_text(item)]
    else:
        chunks = re.split(r"[,;/|]", clean_text(tag_value))
        chunks = [chunk.strip() for chunk in chunks if chunk.strip()]

    seen = set()
    result = []
    for item in chunks:
        lowered = item.lower()
        if lowered not in seen:
            seen.add(lowered)
            result.append(item)
    return ", ".join(result)


def infer_role_name(job_family: str, title: str) -> str:
    family = normalize_lookup(job_family)
    lowered_title = normalize_lookup(title)

    if family in ROLE_MAP and family != "data_science_ml":
        return ROLE_MAP[family]

    if family == "data_science_ml":
        if "research" in lowered_title:
            return "AI Researcher"
        if "scientist" in lowered_title:
            return "Data Scientist"
        return "AI Engineer"

    if family == "other":
        if "data governance" in lowered_title or "quan tri du lieu" in lowered_title:
            return "Data Governance Specialist"
        if "data scientist" in lowered_title or "khoa hoc du lieu" in lowered_title:
            return "Data Scientist"
        if "data analyst" in lowered_title or "phan tich du lieu" in lowered_title:
            return "Data Analyst"
        if "business analyst" in lowered_title or "fp a analyst" in lowered_title:
            return "Business Analyst"
        if "data engineer" in lowered_title:
            return "Data Engineer"
        if "ai quantitative researcher" in lowered_title or ("research" in lowered_title and "ai" in lowered_title):
            return "AI Researcher"
        if any(
            keyword in lowered_title
            for keyword in [
                "ai engineer",
                "ai developer",
                "ai expert",
                "ai platform",
                "ai system",
                "ai automation",
                "ai generative",
                "agentic ai",
                "prompt engineering",
                "prompt engineer",
                "aiops",
            ]
        ):
            return "AI Engineer"
        if any(
            keyword in lowered_title
            for keyword in [
                "du lieu",
                "data executive",
                "data management",
                "data specialist",
            ]
        ):
            return "Data Specialist"
        if any(
            keyword in lowered_title
            for keyword in [
                "van hanh",
                "operations",
                "ke hoach",
                "planning",
            ]
        ):
            return "Operations Specialist"

    if "data analyst" in lowered_title:
        return "Data Analyst"
    if "business analyst" in lowered_title or "analyst" in lowered_title or "phan tich du lieu" in lowered_title:
        return "Business Analyst" if "business analyst" in lowered_title or "fp a analyst" in lowered_title else "Data Analyst"
    if "data engineer" in lowered_title:
        return "Data Engineer"
    if "data governance" in lowered_title:
        return "Data Governance Specialist"
    if "data scientist" in lowered_title or "scientist" in lowered_title or "khoa hoc du lieu" in lowered_title:
        return "Data Scientist"
    if "ai engineer" in lowered_title:
        return "AI Engineer"
    if any(
        keyword in lowered_title
        for keyword in [
            "ai developer",
            "ai expert",
            "ai platform",
            "ai system",
            "ai automation",
            "ai generative",
            "prompt engineering",
            "prompt engineer",
            "aiops",
        ]
    ):
        return "AI Engineer"
    if "research" in lowered_title and "ai" in lowered_title:
        return "AI Researcher"
    if "project manager" in lowered_title:
        return "Project Manager"
    if "software engineer" in lowered_title:
        return "Software Engineer"
    if any(
        keyword in lowered_title
        for keyword in [
            "label",
            "gan nhan",
            "nhap lieu",
            "xu ly du lieu",
            "ngon ngu du lieu",
            "scan va nhap lieu",
        ]
    ):
        return "Data Labeling"
    if any(
        keyword in lowered_title
        for keyword in [
            "database",
            "dba",
            "data integration",
        ]
    ):
        return "Data Engineer"
    if any(
        keyword in lowered_title
        for keyword in [
            "data science",
            "khoa hoc du lieu",
            "science analysis",
        ]
    ):
        return "Data Scientist"
    if any(
        keyword in lowered_title
        for keyword in [
            "tri tue nhan tao",
            "su dung ai",
            "ung dung ai",
            "ai solution",
            "ai marketing",
            "ai artist",
            "machine vision",
            "computer vision",
        ]
    ):
        return "AI Specialist"
    if any(
        keyword in lowered_title
        for keyword in [
            "data",
            "du lieu",
            "thong ke",
        ]
    ):
        return "Data Specialist"
    if any(
        keyword in lowered_title
        for keyword in [
            "van hanh",
            "operations",
            "ke hoach",
            "planning",
        ]
    ):
        return "Operations Specialist"
    return "Unknown"


def build_section_lookup(sections_df: pd.DataFrame) -> pd.DataFrame:
    if sections_df.empty:
        return pd.DataFrame(columns=["job_url", "desc_mota", "desc_yeucau", "desc_quyenloi"])

    working_df = sections_df.copy()
    working_df["chunk_text"] = working_df["chunk_text"].apply(clean_text)

    grouped_rows = []
    for job_url, group in working_df.groupby("job_url", dropna=False):
        description_chunks = group.loc[group["section_type"] == "description", "chunk_text"].tolist()
        requirement_chunks = group.loc[group["section_type"] == "requirements", "chunk_text"].tolist()
        benefit_chunks = group.loc[group["section_type"] == "benefits", "chunk_text"].tolist()

        grouped_rows.append(
            {
                "job_url": clean_text(job_url),
                "desc_mota_sections": "\n".join(chunk for chunk in description_chunks if chunk),
                "desc_yeucau_sections": "\n".join(chunk for chunk in requirement_chunks if chunk),
                "desc_quyenloi_sections": "\n".join(chunk for chunk in benefit_chunks if chunk),
            }
        )

    return pd.DataFrame(grouped_rows)


def build_job_text(row: pd.Series) -> str:
    parts = [
        f"Role: {row.get('source_role', '')}",
        f"Title: {row.get('title', '')}",
        f"Detail title: {row.get('detail_title', '')}",
        f"Company: {row.get('company_name_full', '') or row.get('company', '')}",
        f"Location: {row.get('detail_location', '')}",
        f"Experience: {row.get('detail_experience', '')}",
        f"Salary: {row.get('salary_list', '') or row.get('detail_salary', '')}",
        f"Tags: {row.get('tags', '')}",
        f"Job level: {row.get('job_level', '')}",
        f"Education: {row.get('education_level', '')}",
        f"Employment type: {row.get('employment_type', '')}",
        f"Description: {row.get('desc_mota', '')}",
        f"Requirements: {row.get('desc_yeucau', '')}",
        f"Benefits: {row.get('desc_quyenloi', '')}",
        f"Company field: {row.get('company_field', '')}",
        f"Company description: {row.get('company_description', '')}",
    ]
    return "\n".join(part for part in parts if part.split(": ", 1)[1].strip())


def build_merged_jobs() -> pd.DataFrame:
    if not READY_PATH.exists():
        raise FileNotFoundError(f"Không tìm thấy file parquet: {READY_PATH}")
    if not SECTIONS_PATH.exists():
        raise FileNotFoundError(f"Không tìm thấy file parquet: {SECTIONS_PATH}")

    ready_df = pd.read_parquet(READY_PATH)
    sections_df = pd.read_parquet(SECTIONS_PATH)
    section_lookup = build_section_lookup(sections_df)

    merged = ready_df.merge(section_lookup, on="job_url", how="left")

    result = pd.DataFrame()
    result["title"] = merged["job_title_display"].apply(clean_text)
    result["detail_title"] = merged["job_title_canonical"].apply(clean_text)
    result["company"] = ""
    result["company_name_full"] = ""
    result["salary_list"] = ""
    result["detail_salary"] = ""
    result["detail_location"] = merged["location_norm"].apply(clean_text)
    result["detail_experience"] = ""
    result["tags"] = merged["skills_extracted"].apply(normalize_tags)
    result["job_level"] = ""
    result["education_level"] = ""
    result["employment_type"] = merged["work_mode"].apply(clean_text)
    result["desc_mota"] = merged["description_clean_struct"].apply(clean_text)
    result["desc_yeucau"] = merged["requirements_clean_struct"].apply(clean_text)
    result["desc_quyenloi"] = merged["benefits_clean_struct"].apply(clean_text)
    result["company_field"] = merged["job_family"].apply(clean_text)
    result["company_description"] = merged["job_chatbot_profile"].apply(clean_text)
    result["job_url"] = merged["job_url"].apply(clean_text)
    result["deadline"] = merged["deadline_date"].apply(clean_text)
    result["source_file"] = "jobs_chatbot_ready_v2.parquet"
    result["source_role"] = merged.apply(
        lambda row: infer_role_name(row.get("job_family", ""), row.get("job_title_display", "")),
        axis=1,
    )

    # Nếu các trường struct sạch bị trống, fallback sang sections parquet.
    result["desc_mota"] = result["desc_mota"].mask(
        result["desc_mota"].str.len() == 0,
        merged["desc_mota_sections"].fillna("").apply(clean_text),
    )
    result["desc_yeucau"] = result["desc_yeucau"].mask(
        result["desc_yeucau"].str.len() == 0,
        merged["desc_yeucau_sections"].fillna("").apply(clean_text),
    )
    result["desc_quyenloi"] = result["desc_quyenloi"].mask(
        result["desc_quyenloi"].str.len() == 0,
        merged["desc_quyenloi_sections"].fillna("").apply(clean_text),
    )

    for column in TEXT_COLUMNS + ["job_url", "deadline", "source_file", "source_role"]:
        result[column] = result[column].apply(clean_text)

    result = result[
        (result["title"].str.len() > 0)
        | (result["desc_yeucau"].str.len() > 0)
        | (result["desc_mota"].str.len() > 0)
    ].copy()

    result["dedup_key"] = (
        result["title"].str.lower().fillna("")
        + "||"
        + result["company_name_full"].str.lower().fillna("")
        + "||"
        + result["detail_location"].str.lower().fillna("")
    )
    result = result.drop_duplicates(subset=["dedup_key"]).drop(columns=["dedup_key"])

    result["job_text"] = merged["job_text_chatbot"].apply(clean_text)
    empty_job_text_mask = result["job_text"].str.len() == 0
    if empty_job_text_mask.any():
        result.loc[empty_job_text_mask, "job_text"] = result.loc[empty_job_text_mask].apply(build_job_text, axis=1)

    return result


def main() -> None:
    merged = build_merged_jobs()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(OUTPUT_PATH, index=False, encoding="utf-8-sig")

    print(f"Đã đọc dữ liệu từ: {READY_PATH}")
    print(f"Đã dùng sections từ: {SECTIONS_PATH}")
    print(f"Số dòng sau khi gộp: {len(merged)}")
    print("Phân bố role:")
    print(merged["source_role"].value_counts(dropna=False))
    print(f"Đã lưu về: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
