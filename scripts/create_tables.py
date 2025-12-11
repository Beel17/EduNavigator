"""Create database tables from SQLAlchemy models.

Usage:
    python scripts/create_tables.py

Requires:
    - DATABASE_URL env var pointing to the target database.
"""

import os
import sys

from database.session import engine
from database import models


def main() -> None:
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("DATABASE_URL is not set. Please export it before running.")
        sys.exit(1)

    models.Base.metadata.create_all(bind=engine)
    print("Tables created successfully.")


if __name__ == "__main__":
    main()
