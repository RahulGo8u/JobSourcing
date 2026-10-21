
import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

database_url = os.getenv("DATABASE_URL")

if not database_url:
    raise RuntimeError("DATABASE_URL is missing from .env")

engine = create_engine(database_url, pool_pre_ping=True)

with engine.connect() as connection:
    result = connection.execute(
        text("SELECT current_database(), current_timestamp")
    )
    database_name, server_time = result.one()

    print("Database connection successful!")
    print(f"Database: {database_name}")
    print(f"Server time: {server_time}")

    result = connection.execute(
        text("SELECT COUNT(*) FROM search_profiles")
    )
    print(f"Search profiles: {result.scalar_one()}")

engine.dispose()
