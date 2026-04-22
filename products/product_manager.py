"""
제품 프로필 관리 모듈 — Firebase Firestore 연동
"""

from datetime import datetime

def _get_db():
    from firebase_client import get_db
    return get_db()

def _safe_id(product_name: str) -> str:
    return product_name.replace("/", "_").replace("\\", "_")

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

def get_product_list() -> list:
    try:
        db = _get_db()
        docs = db.collection("ad_products").stream()
        return sorted([d.to_dict().get("name", d.id) for d in docs])
    except Exception:
        return []

def load_product(product_name: str) -> dict:
    try:
        db = _get_db()
        doc = db.collection("ad_products").document(_safe_id(product_name)).get()
        if doc.exists:
            return doc.to_dict()
    except Exception:
        pass
    return _empty_profile(product_name)

def save_product(profile: dict):
    try:
        db = _get_db()
        profile["updated"] = datetime.now().strftime("%Y-%m-%d")
        db.collection("ad_products").document(_safe_id(profile["name"])).set(profile)
    except Exception:
        pass

def delete_product(product_name: str) -> bool:
    try:
        db = _get_db()
        db.collection("ad_products").document(_safe_id(product_name)).delete()
        return True
    except Exception:
        return False

def add_performance_record(product_name: str, record: dict):
    profile = load_product(product_name)
    record["date"] = datetime.now().strftime("%G-W%V")
    profile["performance_history"].append(record)
    profile["performance_history"] = profile["performance_history"][-48:]
    save_product(profile)

def get_profile_summary(product_name: str) -> str:
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
        recent = history[-24:]
        seen_dates = []
        for rec in reversed(recent):
            d = rec.get("date", "")
            if d and d not in seen_dates:
                seen_dates.append(d)
            if len(seen_dates) >= 4:
                break
        seen_dates = list(reversed(seen_dates))
        for date in seen_dates:
            for rec in [r for r in recent if r.get("date") == date]:
                channel = rec.get("channel", "") or "전체"
                parts = [f"[{date} | {channel}]"]
                if rec.get("roas"): parts.append(f"ROAS {rec['roas']}")
                if rec.get("cpc"):  parts.append(f"CPC {rec['cpc']}원")
                if rec.get("ctr"):  parts.append(f"CTR {rec['ctr']}%")
                if rec.get("cvr"):  parts.append(f"전환율 {rec['cvr']}%")
                if rec.get("cpa"):  parts.append(f"CPA {rec['cpa']}원")
                if rec.get("notes"): parts.append(f"메모: {rec['notes']}")
                lines.append(" | ".join(parts))
    else:
        lines.append("- 아직 실적 데이터 없음")

    return "\n".join(lines)
