"""
에이전트 메모리 관리 모듈 — Firebase Firestore 연동
"""

import os
from datetime import datetime

def _get_db():
    from firebase_client import get_db
    return get_db()

def _empty_memory(agent_name: str) -> dict:
    return {
        "agent_name": agent_name,
        "created": datetime.now().isoformat(),
        "total_campaigns": 0,
        "success_count": 0,
        "experiences": [],
    }

def load_memory(agent_name: str) -> dict:
    try:
        db = _get_db()
        doc = db.collection("ad_agent_memories").document(agent_name).get()
        if doc.exists:
            return doc.to_dict()
    except Exception:
        pass
    return _empty_memory(agent_name)

def save_memory(agent_name: str, memory: dict):
    try:
        db = _get_db()
        db.collection("ad_agent_memories").document(agent_name).set(memory)
    except Exception:
        pass

def add_experience(agent_name: str, campaign_data: dict, outcome: str):
    memory = load_memory(agent_name)

    entry = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "summary": campaign_data.get("summary", "")[:120],
        "category": campaign_data.get("category", ""),
        "budget_range": campaign_data.get("budget_range", ""),
        "channels": campaign_data.get("channels", []),
        "outcome": outcome,
        "learnings": campaign_data.get("learnings", ""),
    }

    memory["experiences"].append(entry)
    memory["total_campaigns"] += 1
    if outcome == "성공":
        memory["success_count"] += 1

    save_memory(agent_name, memory)

def get_relevant_experiences(agent_name: str, category: str, budget_range: str) -> str:
    memory = load_memory(agent_name)
    experiences = memory.get("experiences", [])

    if not experiences:
        return "아직 축적된 경험 데이터가 없습니다."

    relevant = [
        e for e in experiences
        if e.get("category") == category or e.get("budget_range") == budget_range
    ]
    if not relevant:
        relevant = experiences

    recent = relevant[-5:]
    lines = []
    for e in recent:
        line = (
            f"[{e['date']}] {e['summary']} "
            f"| 결과: {e['outcome']} "
            f"| 교훈: {e['learnings'] or '없음'}"
        )
        lines.append(f"• {line}")

    return "\n".join(lines)
