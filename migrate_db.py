import sqlite3
import sys
from datetime import datetime

# Paths
old_db = sys.argv[1]
new_db = "backend/leadgen.db"

print(f"Migriere Daten von {old_db} nach {new_db}...")

# Connect to both databases
old_conn = sqlite3.connect(old_db)
new_conn = sqlite3.connect(new_db)

old_cursor = old_conn.cursor()
new_cursor = new_conn.cursor()

try:
    # Get all runs from old database
    old_cursor.execute("SELECT * FROM runs")
    old_runs = old_cursor.fetchall()

    # Get column names from old database
    old_cursor.execute("PRAGMA table_info(runs)")
    old_columns = [col[1] for col in old_cursor.fetchall()]

    print(f"✅ Gefunden: {len(old_runs)} Runs in der alten Datenbank")
    print(f"Alte Spalten: {old_columns}")

    # Migrate runs
    for run in old_runs:
        run_dict = dict(zip(old_columns, run))

        # Add default values for new columns
        if 'selected_providers' not in run_dict:
            run_dict['selected_providers'] = '[]'
        if 'provider_limits' not in run_dict:
            run_dict['provider_limits'] = '{}'
        if 'total_emails' not in run_dict:
            run_dict['total_emails'] = 0
        if 'total_websites' not in run_dict:
            run_dict['total_websites'] = 0

        # Insert into new database
        new_cursor.execute("""
            INSERT INTO runs (
                id, status, location, category, require_approval, dry_run,
                total_leads, selected_providers, provider_limits, total_emails,
                total_websites, error_message, created_at, updated_at, completed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            run_dict.get('id'),
            run_dict.get('status'),
            run_dict.get('location'),
            run_dict.get('category'),
            run_dict.get('require_approval', 0),
            run_dict.get('dry_run', 0),
            run_dict.get('total_leads', 0),
            run_dict.get('selected_providers', '[]'),
            run_dict.get('provider_limits', '{}'),
            run_dict.get('total_emails', 0),
            run_dict.get('total_websites', 0),
            run_dict.get('error_message'),
            run_dict.get('created_at'),
            run_dict.get('updated_at'),
            run_dict.get('completed_at')
        ))

    # Migrate leads
    old_cursor.execute("SELECT COUNT(*) FROM leads")
    lead_count = old_cursor.fetchone()[0]

    if lead_count > 0:
        print(f"✅ Migriere {lead_count} Leads...")
        old_cursor.execute("SELECT * FROM leads")
        old_cursor.execute("PRAGMA table_info(leads)")
        lead_columns = [col[1] for col in old_cursor.fetchall()]

        old_cursor.execute("SELECT * FROM leads")
        for lead in old_cursor.fetchall():
            lead_dict = dict(zip(lead_columns, lead))

            new_cursor.execute("""
                INSERT INTO leads (
                    id, run_id, business_name, address, website, email, phone,
                    latitude, longitude, confidence_score, sources, enrichment_data,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                lead_dict.get('id'),
                lead_dict.get('run_id'),
                lead_dict.get('business_name'),
                lead_dict.get('address'),
                lead_dict.get('website'),
                lead_dict.get('email'),
                lead_dict.get('phone'),
                lead_dict.get('latitude'),
                lead_dict.get('longitude'),
                lead_dict.get('confidence_score', 0.0),
                lead_dict.get('sources', '[]'),
                lead_dict.get('enrichment_data', '{}'),
                lead_dict.get('created_at'),
                lead_dict.get('updated_at')
            ))

    # Migrate logs
    old_cursor.execute("SELECT COUNT(*) FROM logs")
    log_count = old_cursor.fetchone()[0]

    if log_count > 0:
        print(f"✅ Migriere {log_count} Logs...")
        old_cursor.execute("SELECT * FROM logs")
        old_cursor.execute("PRAGMA table_info(logs)")
        log_columns = [col[1] for col in old_cursor.fetchall()]

        old_cursor.execute("SELECT * FROM logs")
        for log in old_cursor.fetchall():
            log_dict = dict(zip(log_columns, log))

            new_cursor.execute("""
                INSERT INTO logs (
                    id, run_id, lead_id, level, message, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                log_dict.get('id'),
                log_dict.get('run_id'),
                log_dict.get('lead_id'),
                log_dict.get('level'),
                log_dict.get('message'),
                log_dict.get('created_at')
            ))

    # Commit changes
    new_conn.commit()

    print(f"\n✅ Migration erfolgreich!")
    print(f"   - {len(old_runs)} Runs migriert")
    print(f"   - {lead_count} Leads migriert")
    print(f"   - {log_count} Logs migriert")

except Exception as e:
    print(f"❌ Fehler bei der Migration: {e}")
    import traceback
    traceback.print_exc()
    new_conn.rollback()
    sys.exit(1)
finally:
    old_conn.close()
    new_conn.close()

print("\n✅ Datenbank erfolgreich migriert!")
