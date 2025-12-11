from database.session import SessionLocal
from database import models

session = SessionLocal()
try:
    counts = {
        "documents": session.query(models.Document).count(),
        "opportunities": session.query(models.Opportunity).count(),
        "changes": session.query(models.Change).count(),
    }
    for table, count in counts.items():
        print(f"{table}: {count}")
finally:
    session.close()
