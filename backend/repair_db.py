from app.database import SessionLocal
from app.utils.stats import refresh_run_stats
from app.models.run import Run

def repair_data():
    db = SessionLocal()
    try:
        print("Starting database repair...")
        runs = db.query(Run).all()
        for run in runs:
            print(f"Repairing Run: {run.id}...")
            refresh_run_stats(run.id, db)
        print("Repair completed successfully!")
    except Exception as e:
        print(f"Repair failed: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    repair_data()
