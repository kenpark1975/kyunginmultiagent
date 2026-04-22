import os
from dotenv import load_dotenv

load_dotenv()

# ─── API 설정 ────────────────────────────────────────────
def _get_api_key():
    try:
        import streamlit as st
        return st.secrets["ANTHROPIC_API_KEY"]
    except Exception:
        return os.getenv("ANTHROPIC_API_KEY")

ANTHROPIC_API_KEY = _get_api_key()
MODEL = "claude-sonnet-4-5"
MAX_TOKENS = 2000

# ─── 에이전트 목록 ────────────────────────────────────────
AGENT_NAMES = [
    "strategy_director",
    "sns_specialist",
    "search_specialist",
    "data_analyst",
    "creative_director",
]

AGENT_DISPLAY_NAMES = {
    "strategy_director": "🎯 전략 디렉터",
    "sns_specialist":    "📱 SNS 전문가",
    "search_specialist": "🔍 검색광고 전문가",
    "data_analyst":      "📊 데이터 분석가",
    "creative_director": "🎨 크리에이티브 디렉터",
}

AGENT_PERSONAS = {
    "strategy_director": "보수적이고 리스크를 중시하며 데이터 기반으로 판단합니다. 전체 예산 배분과 캠페인 방향성을 책임집니다.",
    "sns_specialist":    "트렌드 지향적이고 바이럴을 중시하며 감성적입니다. 숫자보다 콘텐츠 공감력을 더 중요하게 생각합니다.",
    "search_specialist": "ROI에 집착하며 수치 중심으로 사고합니다. 감성적 접근보다 클릭률과 전환율로 모든 것을 판단합니다.",
    "data_analyst":      "매우 비판적이고 회의적입니다. 근거 없는 주장을 싫어하며 수치로만 말합니다. 낙관적 예측을 경계합니다.",
    "creative_director": "창의적이고 파격적인 제안을 선호합니다. 브랜드 아이덴티티와 스토리텔링을 가장 중요하게 생각합니다.",
}

CATEGORIES = [
    "반려동물", "식품/음료", "패션/뷰티", "IT/앱", "교육",
    "부동산", "금융", "의료/건강", "여행", "생활용품", "생활가전", "기타",
]

BUDGET_RANGES = [
    "100만원 미만",
    "100~300만원",
    "300~500만원",
    "500만원~1,000만원",
    "1,000만원~3,000만원",
    "3,000만원~5,000만원",
    "5,000만원~1억원",
    "1억원 이상",
]
