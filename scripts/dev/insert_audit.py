import os
import sys
import uuid
import psycopg
from dotenv import load_dotenv

load_dotenv('.env')
db_url = os.environ.get('DATABASE_URL')

tenant_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, "tenant_saas"))
flag_id = str(uuid.uuid4())

with psycopg.connect(db_url, application_name="themis-seed") as conn:
    with conn.cursor() as cur:
        # Insert tenant if not exists
        cur.execute("""
            INSERT INTO tenants (id, name, slug, created_at, updated_at) 
            VALUES (%s, 'SaaS Tenant', 'saas-tenant', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ON CONFLICT (id) DO NOTHING;
        """, (tenant_id,))
        
        # Insert audit log
        cur.execute("""
            INSERT INTO audit_log (tenant_id, action, resource_type, resource_id, details, created_at)
            VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
            RETURNING *;
        """, (tenant_id, "flag.overridden", "flag", flag_id, '{"human_override": "accepted", "flag_index": 0, "concern": "The clause limits ability..."}'))
        
        row = cur.fetchone()
        print(f"Audit log row inserted:\n{row}")
        
    conn.commit()
