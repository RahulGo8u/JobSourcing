
from pprint import pprint

from app.sources.himalayas import fetch_jobs, normalize_job

if __name__ == "__main__":
    jobs = fetch_jobs(limit=3)

    for raw_job in jobs:
        pprint(normalize_job(raw_job))
        print("\n" + "=" * 60)
