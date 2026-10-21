
from collections import Counter

from app.repositories import get_enabled_job_sources, save_source_job
from app.sources.himalayas import fetch_jobs, normalize_job


if __name__ == "__main__":
    sources = get_enabled_job_sources()
    source = next(
        (s for s in sources if s["name"] == "Himalayas"),
        None,
    )

    if not source:
        raise RuntimeError("Himalayas source is not enabled.")

    raw_jobs = fetch_jobs(limit=50)
    results = Counter()

    for raw_job in raw_jobs:
        normalized = normalize_job(raw_job)
        result = save_source_job(source["id"], normalized)
        results[result] += 1

    print(f"Fetched: {len(raw_jobs)}")
    print(f"Inserted: {results['inserted']}")
    print(f"Updated: {results['updated']}")
    print(f"Skipped: {results['skipped']}")
