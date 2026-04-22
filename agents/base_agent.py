"""
모든 에이전트가 공통으로 상속하는 베이스 클래스.
나중에 AI 공급자(ChatGPT, Gemini 등)를 에이전트별로 교체할 때
이 파일만 수정하면 됩니다.
"""

import anthropic
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from config import ANTHROPIC_API_KEY, MODEL, MAX_TOKENS, AGENT_PERSONAS
from memory.memory_manager import get_relevant_experiences


class BaseAgent:
    """
    광고 에이전트 베이스 클래스.

    하위 클래스에서 정의해야 하는 것:
      - self.agent_name  (예: "sns_specialist")
      - self.role_prompt (역할 설명 시스템 프롬프트)
    """

    def __init__(self):
        self.client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        self.agent_name = ""
        self.role_prompt = ""

    def _build_system_prompt(self) -> str:
        persona = AGENT_PERSONAS.get(self.agent_name, "")
        return f"{self.role_prompt}\n\n## 나의 성격과 관점\n{persona}\n\n출력 언어: 한국어\n출력 형식: Markdown (헤더, 불릿 포인트 활용)\n핵심만 간결하게 작성하세요."

    def analyze(self, brief: str, category: str = "", budget_range: str = "") -> str:
        """브리프를 분석하고 해당 에이전트 관점의 의견을 반환."""

        past = get_relevant_experiences(self.agent_name, category, budget_range)

        prompt = f"""## 광고 브리프
{brief}

## 카테고리: {category} | 예산 규모: {budget_range}

## 나의 과거 유사 캠페인 경험
{past}

---
위 브리프를 분석하여 나의 전문 영역에서 의견을 제시해주세요.
"""

        # 서버 과부하 시 최대 3회 자동 재시도
        for attempt in range(3):
            try:
                response = self.client.messages.create(
                    model=MODEL,
                    max_tokens=MAX_TOKENS,
                    system=self._build_system_prompt(),
                    messages=[{"role": "user", "content": prompt}],
                )
                return response.content[0].text
            except anthropic.APIStatusError as e:
                if e.status_code == 529 and attempt < 2:
                    time.sleep(10 * (attempt + 1))  # 10초, 20초 대기 후 재시도
                    continue
                raise
