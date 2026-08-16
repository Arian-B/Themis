"""
agents/critic_agent.py — Agent 7: Critic Feedback Agent
"""
import os
import sys
import json
import logging
from pathlib import Path
import psycopg

ROOT = Path(__file__).parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

from langchain_core.messages import HumanMessage, SystemMessage
from utils.llm_provider import get_complex_reasoning_llm
from schemas.feedback import CriticFeedback

logger = logging.getLogger(__name__)

_CRITIC_PROMPT = """\
You are an expert legal tech AI critic.
You will be provided with a historical risk flag that was evaluated by a human lawyer.
Your job is to analyze the human's decision and extract a generalizable lesson for future agent models.

Flag Concern: {concern}
Human Decision: {decision} (accepted = useful, rejected = false positive)

Did the human find this flag useful?
What is the generalizable lesson here?

Respond ONLY with a JSON object exactly matching this schema:
{{
  "was_flag_useful": true/false,
  "lesson": "<Your lesson>"
}}
"""

def run_critic():
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        logger.error("No DATABASE_URL set.")
        return

    llm = get_complex_reasoning_llm(temperature=0.0)

    with psycopg.connect(db_url, application_name="themis-critic") as conn:
        with conn.cursor() as cur:
            # Fetch all flag overrides not yet in critic_lessons
            cur.execute("""
                SELECT id, resource_id, details 
                FROM audit_log 
                WHERE action = 'flag.overridden'
                AND resource_id NOT IN (SELECT flag_id FROM critic_lessons)
            """)
            rows = cur.fetchall()
            
            for row in rows:
                audit_id, flag_id, details = row
                if isinstance(details, str):
                    details = json.loads(details)
                    
                concern = details.get("concern", "Unknown concern")
                decision = details.get("human_override", "Unknown")
                
                prompt = _CRITIC_PROMPT.format(concern=concern, decision=decision)
                try:
                    resp = llm.invoke([HumanMessage(content=prompt)])
                except Exception as e:
                    logger.error(f"LLM failure: {e}")
                    continue
                    
                text = resp.content if hasattr(resp, "content") else str(resp)
                
                clean = text.strip()
                if clean.startswith("```"):
                    lines = clean.split("\n")
                    clean = "\n".join(lines[1:-1]) if len(lines) > 2 else clean
                
                try:
                    data = json.loads(clean)
                except Exception as e:
                    logger.error(f"Failed to parse LLM response for audit {audit_id}: {e}\nResponse: {text}")
                    continue
                    
                was_flag_useful = data.get("was_flag_useful", True)
                lesson = data.get("lesson", "")
                
                cur.execute("""
                    INSERT INTO critic_lessons (flag_id, human_decision, was_flag_useful, lesson)
                    VALUES (%s, %s, %s, %s)
                """, (flag_id, decision, was_flag_useful, lesson))
                
                logger.info(f"Inserted critic lesson for flag {flag_id}")
                
        conn.commit()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_critic()
