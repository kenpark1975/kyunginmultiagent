from .base_agent import BaseAgent


class DataAnalystAgent(BaseAgent):
    def __init__(self):
        super().__init__()
        self.agent_name = "data_analyst"
        self.role_prompt = """당신은 광고 데이터 분석가입니다.

전문 영역:
- 예산 대비 예상 성과 계산 (CPM, CPC, CPA, ROAS)
- KPI 목표값 설정 (업종 평균 벤치마크 기반)
- 채널별 예산 배분 효율 분석
- 리스크 시나리오 분석 (최악/보통/최선)
- 광고 피로도 및 노출 빈도 계산

출력 구조:
### 예산 시뮬레이션 (채널별 예상 지표)
### 권장 KPI 목표치
### 리스크 시나리오 (최악/보통/최선)
### 데이터 기반 주의사항"""


def analyze(brief: str, category: str = "", budget_range: str = "") -> str:
    return DataAnalystAgent().analyze(brief, category, budget_range)
