from app.database import SessionLocal
from app.models import Lead, Email, Run
from sqlalchemy import func

def check_counts():
    db = SessionLocal()
    try:
        # Get all runs
        runs = db.query(Run).all()
        for run in runs:
            print(f"\nRun: {run.id} ({run.category} in {run.location})")
            print(f"Stored Stats: Leads={run.total_leads}, Drafts={run.total_drafts}, Sent={run.total_sent}")

            # Count leads that have a Drafted/Approved email
            drafted_count = db.query(func.count(func.distinct(Lead.id))).join(Email).filter(
                Lead.run_id == run.id,
                Email.status.in_(["DRAFTED", "APPROVED"])
            ).scalar()

            # Count leads that have a Sent/SFDX email
            sent_count = db.query(func.count(func.distinct(Lead.id))).join(Email).filter(
                Lead.run_id == run.id,
                Email.status.in_(["SENT", "SFDX"])
            ).scalar()

            print(f"Calculated (Distinct Leads): Drafts={drafted_count}, Sent={sent_count}")

            # Find leads with duplicates
            duplicates = db.query(Email.lead_id, func.count(Email.id)).join(Lead).filter(
                Lead.run_id == run.id
            ).group_by(Email.lead_id).having(func.count(Email.id) > 1).all()

            if duplicates:
                print(f"Found {len(duplicates)} leads with multiple emails!")

    finally:
        db.close()

if __name__ == "__main__":
    check_counts()
