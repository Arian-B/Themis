import os
import sys
import uuid
import psycopg
from dotenv import load_dotenv

load_dotenv('.env')
db_url = os.environ.get('DATABASE_URL')

tenant_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, "tenant_saas"))

with psycopg.connect(db_url, application_name="themis-seed") as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM audit_log WHERE tenant_id = %s", (tenant_id,))
        count = cur.fetchone()[0]
        print(f"Total audit_log rows for this tenant: {count}")
        
        cur.execute("SELECT action, details FROM audit_log WHERE tenant_id = %s ORDER BY created_at DESC LIMIT 3", (tenant_id,))
        rows = cur.fetchall()
        print(f"Last 3 rows:")
        for row in rows:
            print(row)
