"""
토론 엔진 모듈
- 5개 에이전트의 의견을 수집하여 토론을 시뮬레이션
- 합의 지점과 충돌 지점을 식별하고 최종 합의안을 도출
- 토큰 효율을 위해 충돌 지점에만 집중하는 방식 채택
"""

import anthropic
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import ANTHROPIC_API_KEY, MODEL, AGENT_DISPLAY_NAMES

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

DEBATE_SYSTEM = """당신은 광고 전략 회의의 중재자입니다.
5명의 전문가(전략 디렉터, SNS 전문가, 검색광고 전문가, 데이터 분석가, 크리에이티브 디렉터) 의견을 검토하고 합의를 이끌어냅니다.

원칙:
- 합리적인 의견은 적극 채택
- 충돌 시 근거가 더 강한 쪽을 지지
- 최종 전략은 실제로 실행 가능한 수준으로 구체적으로 작성
- 한국어, Markdown 형식으로 출력"""


def run_debate(brief: str, agent_opinions: dict) -> str:
    """
    에이전트 의견들을 토론시켜 최종 합의안을 반환.

    agent_opinions: {agent_name: opinion_text, ...}
    """
    # 에이전트 의견을 읽기 좋게 포맷
    opinions_block = ""
    for name, opinion in agent_opinions.items():
        display = AGENT_DISPLAY_NAMES.get(name, name)
        opinions_block += f"\n\n---\n## {display} 의견\n{opinion}"

    prompt = f"""## 원본 광고 브리프
{brief}

{opinions_block}

---

## 토론 진행 요청

아래 순서로 작성해주세요:

### ✅ 주요 합의 사항
모든 (또는 대부분) 에이전트가 동의하는 내용

### ⚡ 의견 충돌 지점
에이전트 간 다른 의견이 있는 부분과 각 근거

### 🔨 충돌 해결
각 충돌에 대한 합리적 결론과 선택 이유

### 📋 최종 합의 전략
실행 가능한 수준의 최종 광고 전략
- 채널별 예산 배분 (%)
- 채널별 광고 형식
- 핵심 메시지
- 주요 KPI 목표치
- 실행 타임라인 (주차별)

### ⚠️ 사용자 결정 필요 사항
에이전트들이 합의하지 못했거나, 사용자의 추가 정보가 필요한 항목"""

    for attempt in range(3):
        try:
            response = client.messages.create(
                model=MODEL,
                max_tokens=3000,
                system=DEBATE_SYSTEM,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text
        except anthropic.APIStatusError as e:
            if e.status_code == 529 and attempt < 2:
                time.sleep(10 * (attempt + 1))
                continue
            raise
