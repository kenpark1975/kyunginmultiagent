"""
에이전트 메모리 관리 모듈
- 각 에이전트의 캠페인 경험을 JSON 파일로 저장/로드
- 다음 분석 시 유사 경험을 프롬프트에 주입하여 학습 효과 구현
"""

import json
import os
from datetime import datetime

MEMORY_DIR = os.path.join(os.path.dirname(__file__), "agent_memories")


def _filepath(agent_name: str) -> str:
    return os.path.join(MEMORY_DIR, f"{agent_name}.json")


def _empty_memory(agent_name: str) -> dict:
    return {
        "agent_name": agent_name,
        "created": datetime.now().isoformat(),
        "total_campaigns": 0,
        "success_count": 0,
        "experiences": [],
    }


def load_memory(agent_name: str) -> dict:
    """에이전트 메모리 파일 로드. 없으면 빈 메모리 반환."""
    path = _filepath(agent_name)
    if not os.path.exists(path):
        return _empty_memory(agent_name)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_memory(agent_name: str, memory: dict):
    """에이전트 메모리를 JSON 파일로 저장."""
    os.makedirs(MEMORY_DIR, exist_ok=True)
    with open(_filepath(agent_name), "w", encoding="utf-8") as f:
        json.dump(memory, f, ensure_ascii=False, indent=2)


def add_experience(agent_name: str, campaign_data: dict, outcome: str):
    """
    캠페인 경험을 에이전트 메모리에 추가.

    outcome: "성공" | "보통" | "실패"
    campaign_data keys: summary, category, budget_range, channels, learnings
    """
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
    """
    현재 캠페인과 유사한 과거 경험을 텍스트로 반환.
    프롬프트에 주입하기 위한 용도 — 토큰을 최소화하기 위해 최대 5개만 반환.
    """
    memory = load_memory(agent_name)
    experiences = memory.get("experiences", [])

    if not experiences:
        return "아직 축적된 경험 데이터가 없습니다."

    # 같은 카테고리 또는 같은 예산 규모 우선 필터링
    relevant = [
        e for e in experiences
        if e.get("category") == category or e.get("budget_range") == budget_range
    ]
    if not relevant:
        relevant = experiences  # 없으면 전체에서 최근 것 사용

    # 최신 5개만 사용
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
