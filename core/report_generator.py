"""
최종 보고서 생성 모듈
- 토론 결과를 깔끔한 Markdown 보고서로 포맷팅
- 나중에 PDF 출력 기능 추가 시 이 파일을 확장
"""

from datetime import datetime


def generate_report(brief: str, debate_result: str, category: str, budget_range: str) -> str:
    """최종 광고 전략 보고서를 Markdown 형식으로 생성."""

    now = datetime.now().strftime("%Y년 %m월 %d일 %H:%M")

    report = f"""# 📢 광고 전략 보고서
> 생성일시: {now} | 카테고리: {category} | 예산 규모: {budget_range}

---

## 📝 원본 브리프
{brief}

---

## 🤖 멀티에이전트 토론 결과

{debate_result}

---
*본 보고서는 AI 멀티에이전트 시스템이 생성했습니다. 최종 결정은 반드시 사람이 검토 후 내려주세요.*
"""
    return report
