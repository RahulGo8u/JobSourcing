from pprint import pprint

from app.repositories import (
    get_search_profile,
    get_enabled_job_sources,
)

if __name__ == "__main__":
    print("\n=== Search Profile ===")
    pprint(get_search_profile())

    print("\n=== Enabled Job Sources ===")
    pprint(get_enabled_job_sources())
