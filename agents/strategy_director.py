from .base_agent import BaseAgent


class StrategyDirectorAgent(BaseAgent):
    def __init__(self):
        super().__init__()
        self.agent_name = "strategy_director"
        self.role_prompt = """당신은 광고 전략 디렉터입니다.

전문 영역:
- 전체 캠페인 방향성 및 목표 설정
- 채널별 예산 배분 큰 그림
- 브랜드 포지셔닝 전략
- 캠페인 기간 및 단계별 로드맵
- 경쟁사 대비 차별화 전략

출력 구조:
### 캠페인 핵심 방향
### 예산 배분 (채널별 %)
### 단계별 실행 로드맵
### 리스크 및 주의사항"""


def analyze(brief: str, category: str = "", budget_range: str = "") -> str:
    return StrategyDirectorAgent().analyze(brief, category, budget_range)
