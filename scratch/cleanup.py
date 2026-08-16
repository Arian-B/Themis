import os, psycopg
from dotenv import load_dotenv

load_dotenv()
db_url = os.environ.get('DATABASE_URL')
conn = psycopg.connect(db_url)
cur = conn.cursor()
cur.execute("DELETE FROM critic_lessons WHERE flag_id = '7c74fba4-e0b9-4258-86de-3bde06d5197c'")
cur.execute("DELETE FROM audit_log WHERE id = 6")
conn.commit()
print('Deleted dummy flag.overridden row')
