from .base_agent import BaseAgent


class CreativeDirectorAgent(BaseAgent):
    def __init__(self):
        super().__init__()
        self.agent_name = "creative_director"
        self.role_prompt = """당신은 광고 크리에이티브 디렉터입니다.

전문 영역:
- 광고 핵심 메시지 및 카피 방향 제안
- 타겟 페르소나 정의 (연령/관심사/고민/욕구)
- 채널별 광고 소재 형식 추천 (이미지/영상/카피 길이)
- 브랜드 톤앤매너 설정
- 경쟁사 대비 차별화 메시지

출력 구조:
### 타겟 페르소나
### 핵심 메시지 (USP)
### 헤드라인 카피 예시 (3개)
### 채널별 소재 형식 추천
### 브랜드 톤앤매너"""


def analyze(brief: str, category: str = "", budget_range: str = "") -> str:
    return CreativeDirectorAgent().analyze(brief, category, budget_range)
