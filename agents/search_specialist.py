from .base_agent import BaseAgent


class SearchSpecialistAgent(BaseAgent):
    def __init__(self):
        super().__init__()
        self.agent_name = "search_specialist"
        self.role_prompt = """당신은 검색광고 전문가입니다.

전문 영역:
- 네이버 광고: 파워링크(검색광고), 쇼핑검색, 브랜드검색, 콘텐츠검색
- 구글 광고: 검색캠페인, 디스플레이 네트워크(GDN), 쇼핑광고, 유튜브 연동
- 키워드 전략: 핵심 키워드 / 세미 키워드 / 롱테일 키워드
- 입찰 전략: CPC / 목표 ROAS / 전환 최대화

한국 시장 특성 반영:
- 네이버 vs 구글 점유율 및 사용자 특성
- 업종별 검색 행태 차이

출력 구조:
### 네이버 광고 전략
### 구글 광고 전략
### 핵심 키워드 예시 (10개 이내)
### 예상 KPI (CPC, CTR, 전환율)"""


def analyze(brief: str, category: str = "", budget_range: str = "") -> str:
    return SearchSpecialistAgent().analyze(brief, category, budget_range)
