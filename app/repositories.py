from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os
import hashlib
import json
from datetime import datetime, timezone

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is missing from .env")

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)


def get_search_profile():
    """Return the active job-search profile and its skills."""

    with engine.connect() as connection:
        profile = connection.execute(
            text("""
                SELECT
                    id,
                    name,
                    locations,
                    work_modes,
                    employment_types,
                    posted_within_days,
                    min_relevance_score
                FROM search_profiles
                WHERE is_active = TRUE
                ORDER BY id
                LIMIT 1
            """)
        ).mappings().first()

        if not profile:
            raise RuntimeError("No active search profile found.")

        skills = connection.execute(
            text("""
                SELECT skill, priority
                FROM profile_skills
                WHERE profile_id = :profile_id
                ORDER BY priority DESC, skill
            """),
            {"profile_id": profile["id"]},
        ).mappings().all()

        return {
            "id": profile["id"],
            "name": profile["name"],
            "locations": list(profile["locations"]),
            "work_modes": list(profile["work_modes"]),
            "employment_types": list(profile["employment_types"]),
            "posted_within_days": profile["posted_within_days"],
            "min_relevance_score": profile["min_relevance_score"],
            "skills": [
                {
                    "skill": row["skill"],
                    "priority": row["priority"],
                }
                for row in skills
            ],
        }


def get_enabled_job_sources():
    """Return the job sources enabled for ingestion."""

    with engine.connect() as connection:
        rows = connection.execute(
            text("""
                SELECT id, name, base_url, config
                FROM job_sources
                WHERE is_enabled = TRUE
                ORDER BY name
            """)
        ).mappings().all()

        return [dict(row) for row in rows]

def save_source_job(source_id, job):
    """Insert or update a listing and its canonical job record."""

    listing_url = job.get("listing_url")
    source_job_id = job.get("source_job_id")

    if not listing_url:
        return "skipped"

    content_hash = hashlib.sha256(
        "|".join([
            (job.get("title") or "").strip().lower(),
            (job.get("company") or "").strip().lower(),
            (job.get("location") or "").strip().lower(),
        ]).encode("utf-8")
    ).hexdigest()

    now = datetime.now(timezone.utc)

    with engine.begin() as connection:
        existing = connection.execute(
            text("""
                SELECT id, job_id
                FROM job_source_records
                WHERE source_id = :source_id
                  AND (
                      source_job_id = CAST(:source_job_id AS TEXT)
                      OR listing_url = :listing_url
                  )
                LIMIT 1
            """),
            {
                "source_id": source_id,
                "source_job_id": source_job_id,
                "listing_url": listing_url,
            },
        ).mappings().first()

        values = {
            "title": job.get("title"),
            "company": job.get("company"),
            "description": job.get("description"),
            "location": job.get("location"),
            "work_mode": job.get("work_mode"),
            "employment_type": job.get("employment_type"),
            "salary_min": job.get("salary_min"),
            "salary_max": job.get("salary_max"),
            "salary_currency": job.get("salary_currency"),
            "posted_at": job.get("posted_at"),
            "expires_at": job.get("expires_at"),
            "content_hash": content_hash,
            "now": now,
        }

        if existing:
            job_id = existing["job_id"]

            connection.execute(
                text("""
                    UPDATE jobs SET
                        title = :title,
                        company = :company,
                        description = :description,
                        location = :location,
                        work_mode = :work_mode,
                        employment_type = :employment_type,
                        salary_min = :salary_min,
                        salary_max = :salary_max,
                        salary_currency = :salary_currency,
                        posted_at = :posted_at,
                        expires_at = :expires_at,
                        content_hash = :content_hash,
                        last_seen_at = :now,
                        updated_at = :now
                    WHERE id = :job_id
                """),
                {**values, "job_id": job_id},
            )

            connection.execute(
                text("""
                    UPDATE job_source_records SET
                        source_job_id = COALESCE(
                            source_job_id, :source_job_id
                        ),
                        apply_url = :apply_url,
                        raw_data = CAST(:raw_data AS JSONB),
                        last_seen_at = :now,
                        is_active = TRUE
                    WHERE id = :record_id
                """),
                {
                    "record_id": existing["id"],
                    "source_job_id": source_job_id,
                    "apply_url": job.get("apply_url"),
                    "raw_data": json.dumps(job.get("raw_data") or {}),
                    "now": now,
                },
            )

            return "updated"

        job_id = connection.execute(
            text("""
                INSERT INTO jobs (
                    title, company, description, location,
                    work_mode, employment_type, salary_min,
                    salary_max, salary_currency, posted_at, expires_at,
                    content_hash, first_seen_at, last_seen_at
                )
                VALUES (
                    :title, :company, :description, :location,
                    :work_mode, :employment_type, :salary_min,
                    :salary_max, :salary_currency, :posted_at, :expires_at,
                    :content_hash, :now, :now
                )
                RETURNING id
            """),
            values,
        ).scalar_one()

        connection.execute(
            text("""
                INSERT INTO job_source_records (
                    job_id, source_id, source_job_id,
                    listing_url, apply_url, raw_data,
                    first_seen_at, last_seen_at, is_active
                )
                VALUES (
                    :job_id, :source_id, :source_job_id,
                    :listing_url, :apply_url,
                    CAST(:raw_data AS JSONB),
                    :now, :now, TRUE
                )
            """),
            {
                "job_id": job_id,
                "source_id": source_id,
                "source_job_id": source_job_id,
                "listing_url": listing_url,
                "apply_url": job.get("apply_url"),
                "raw_data": json.dumps(job.get("raw_data") or {}),
                "now": now,
            },
        )

        return "inserted"
