import os, psycopg
from dotenv import load_dotenv

load_dotenv()
db_url = os.environ.get('DATABASE_URL')
conn = psycopg.connect(db_url)
cur = conn.cursor()
cur.execute("SELECT flag_id, human_decision, was_flag_useful, lesson FROM critic_lessons")
rows = cur.fetchall()
for r in rows:
    print(f"Flag: {r[0]}")
    print(f"Useful: {r[2]}")
    print(f"Lesson: {r[3]}")
    print("-" * 40)
