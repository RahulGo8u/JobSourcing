
import requests

API_URL = "https://himalayas.app/jobs/api"


def fetch_jobs(limit=20):
    """Fetch recent job listings from the Himalayas public jobs API."""

    response = requests.get(
        API_URL,
        params={"limit": limit},
        timeout=30,
        headers={"User-Agent": "JobSourcing/1.0"},
    )
    response.raise_for_status()

    data = response.json()

    if isinstance(data, list):
        jobs = data
    elif isinstance(data, dict):
        jobs = data.get("jobs", [])
    else:
        jobs = []

    return jobs


from datetime import datetime, timezone
from html.parser import HTMLParser


class HTMLTextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)

    def get_text(self):
        return " ".join(" ".join(self.parts).split())


def clean_html(value):
    if not value:
        return ""

    parser = HTMLTextExtractor()
    parser.feed(value)
    return parser.get_text()


def unix_to_datetime(value):
    if not value:
        return None

    return datetime.fromtimestamp(
        int(value), tz=timezone.utc
    )


def normalize_job(job):
    """Convert a raw Himalayas listing into our standard job format."""

    description = clean_html(job.get("description", ""))
    excerpt = clean_html(job.get("excerpt", ""))

    searchable_text = (
        f"{job.get('title', '')} {excerpt} {description}"
    ).lower()

    return {
        "source_job_id": job.get("guid") or job.get("applicationLink"),
        "listing_url": job.get("guid") or job.get("applicationLink"),
        "apply_url": job.get("applicationLink"),
        "title": job.get("title"),
        "company": job.get("companyName"),
        "description": description or excerpt,
        "location": ", ".join(job.get("locationRestrictions") or []),
        "work_mode": (
            "Remote" if "remote" in searchable_text else None
        ),
        "employment_type": job.get("employmentType"),
        "salary_min": job.get("minSalary"),
        "salary_max": job.get("maxSalary"),
        "salary_currency": job.get("currency"),
        "posted_at": unix_to_datetime(job.get("pubDate")),
        "expires_at": unix_to_datetime(job.get("expiryDate")),
        "categories": job.get("categories") or [],
        "raw_data": job,
    }
