"""
제품 프로필 관리 모듈
- 제품/브랜드별 실적 데이터를 JSON으로 저장
- 분석 시 자동으로 에이전트 프롬프트에 주입
"""

import json
import os
from datetime import datetime

PRODUCTS_DIR = os.path.join(os.path.dirname(__file__))


def _filepath(product_name: str) -> str:
    safe_name = product_name.replace("/", "_").replace("\\", "_")
    return os.path.join(PRODUCTS_DIR, f"{safe_name}.json")


def get_product_list() -> list:
    """저장된 제품 목록 반환."""
    files = [f for f in os.listdir(PRODUCTS_DIR) if f.endswith(".json") and f != "__init__.json"]
    names = []
    for f in files:
        try:
            with open(os.path.join(PRODUCTS_DIR, f), encoding="utf-8") as fp:
                data = json.load(fp)
                names.append(data.get("name", f.replace(".json", "")))
        except Exception:
            pass
    return sorted(names)


def load_product(product_name: str) -> dict:
    """제품 프로필 로드. 없으면 빈 프로필 반환."""
    path = _filepath(product_name)
    if not os.path.exists(path):
        return _empty_profile(product_name)
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_product(profile: dict):
    """제품 프로필 저장."""
    os.makedirs(PRODUCTS_DIR, exist_ok=True)
    profile["updated"] = datetime.now().strftime("%Y-%m-%d")
    path = _filepath(profile["name"])
    with open(path, "w", encoding="utf-8") as f:
        json.dump(profile, f, ensure_ascii=False, indent=2)


def delete_product(product_name: str) -> bool:
    """제품 프로필 삭제. 성공하면 True 반환."""
    path = _filepath(product_name)
    if os.path.exists(path):
        os.remove(path)
        return True
    return False


def add_performance_record(product_name: str, record: dict):
    """월별 실적 데이터 추가."""
    profile = load_product(product_name)
    record["date"] = datetime.now().strftime("%G-W%V")
    profile["performance_history"].append(record)
    # 최대 48주치 보관 (약 1년)
    profile["performance_history"] = profile["performance_history"][-48:]
    save_product(profile)


def get_profile_summary(product_name: str) -> str:
    """
    에이전트 프롬프트에 주입할 제품 프로필 요약 텍스트 반환.
    토큰 효율을 위해 최근 3개월 데이터만 사용.
    채널별로 그룹핑하여 표시.
    """
    profile = load_product(product_name)
    if not profile.get("name"):
        return ""

    lines = [f"## 제품 프로필: {profile['name']}"]

    if profile.get("description"):
        lines.append(f"- 제품 설명: {profile['description']}")

    if profile.get("insights"):
        lines.append(f"- 누적 인사이트: {profile['insights']}")

    history = profile.get("performance_history", [])
    if history:
        lines.append("\n### 최근 실적 데이터 (최근 4주, 채널별)")

        # 최근 레코드 (채널별로 여러 개일 수 있으므로 넉넉하게 가져옴)
        recent = history[-24:]

        # 날짜 기준 최근 4개 고유 날짜 추출
        seen_dates = []
        for rec in reversed(recent):
            d = rec.get("date", "")
            if d and d not in seen_dates:
                seen_dates.append(d)
            if len(seen_dates) >= 4:
                break
        seen_dates = list(reversed(seen_dates))

        # 날짜별 채널별 표시
        for date in seen_dates:
            date_recs = [r for r in recent if r.get("date") == date]
            for rec in date_recs:
                channel = rec.get("channel", "") or "전체"
                parts = [f"[{date} | {channel}]"]
                if rec.get("roas"):     parts.append(f"ROAS {rec['roas']}")
                if rec.get("cpc"):      parts.append(f"CPC {rec['cpc']}원")
                if rec.get("ctr"):      parts.append(f"CTR {rec['ctr']}%")
                if rec.get("cvr"):      parts.append(f"전환율 {rec['cvr']}%")
                if rec.get("cpa"):      parts.append(f"CPA {rec['cpa']}원")
                if rec.get("notes"):    parts.append(f"메모: {rec['notes']}")
                lines.append(" | ".join(parts))
    else:
        lines.append("- 아직 실적 데이터 없음")

    return "\n".join(lines)


def _empty_profile(product_name: str) -> dict:
    return {
        "name": product_name,
        "category": "",
        "description": "",
        "created": datetime.now().strftime("%Y-%m-%d"),
        "updated": datetime.now().strftime("%Y-%m-%d"),
        "insights": "",
        "performance_history": [],
    }
