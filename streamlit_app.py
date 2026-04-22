"""
광고집행 멀티에이전트 의사결정 시스템
메인 Streamlit 앱
"""

import streamlit as st
import json
import os
from datetime import datetime

import sys
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from agents import strategy_director, sns_specialist, search_specialist, data_analyst, creative_director
from core.debate_engine import run_debate
from core.report_generator import generate_report
from memory.memory_manager import load_memory, add_experience
from config import AGENT_NAMES, AGENT_DISPLAY_NAMES, CATEGORIES, BUDGET_RANGES, ANTHROPIC_API_KEY
from products.product_manager import (
    get_product_list, load_product, save_product,
    add_performance_record, get_profile_summary, delete_product
)

from firebase_client import get_db

AGENT_MODULES = {
    "strategy_director": strategy_director,
    "sns_specialist":    sns_specialist,
    "search_specialist": search_specialist,
    "data_analyst":      data_analyst,
    "creative_director": creative_director,
}

TAB_LABELS = [
    "🎯 전략 디렉터", "📱 SNS 전문가", "🔍 검색광고 전문가",
    "📊 데이터 분석가", "🎨 크리에이티브 디렉터",
]

BRIEF_GUIDE = """**📌 브리프 작성 가이드** (이 항목들을 포함하면 더 정확한 분석이 나옵니다)

| 항목 | 예시 |
|---|---|
| 제품/서비스명 | 유기농 반려견 사료 '웰독' |
| 캠페인 목표 | 브랜드 인지도 상승 + 온라인 구매 전환 |
| 예산 | 월 300만원 |
| 기간 | 1개월 |
| 타겟 | 30~40대 반려견 보호자, 건강에 관심 있는 여성 |
| 현재 상황 | 신규 브랜드, 경쟁사 대비 가격 20% 높음 |
| 운영 데이터 | 지난달 ROAS 2.1, 인스타 CTR 1.2%, 네이버 CPC 800원 |"""

st.set_page_config(
    page_title="광고 멀티에이전트 시스템",
    page_icon="📢",
    layout="wide",
    initial_sidebar_state="expanded",
)

if not ANTHROPIC_API_KEY or ANTHROPIC_API_KEY == "여기에_API_키_붙여넣기":
    st.error("⚠️ API 키가 설정되지 않았습니다. `.env` 파일을 확인해주세요.")
    st.stop()

# ─── 히스토리 유틸 ────────────────────────────────────────
def save_history(brief, category, budget_range, agent_opinions, debate_result, final_report, product_name=""):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    doc_id = ts
    record = {
        "date": datetime.now().isoformat(),
        "date_display": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "brief": brief,
        "brief_preview": brief[:60].replace("\n", " "),
        "category": category,
        "budget_range": budget_range,
        "product_name": product_name,
        "agent_opinions": agent_opinions,
        "debate_result": debate_result,
        "final_report": final_report,
        "outcome": None,
        "learnings": "",
        "_filename": doc_id,
    }
    try:
        db = get_db()
        db.collection("ad_campaigns").document(doc_id).set(record)
    except Exception:
        pass
    return doc_id

def load_history_list():
    try:
        db = get_db()
        docs = db.collection("ad_campaigns").order_by("date", direction="DESCENDING").limit(50).stream()
        return [d.to_dict() for d in docs]
    except Exception:
        return []

def update_history_outcome(doc_id, outcome, learnings):
    try:
        db = get_db()
        db.collection("ad_campaigns").document(doc_id).update({"outcome": outcome, "learnings": learnings})
    except Exception:
        pass

def update_history_opinions(doc_id, agent_opinions, debate_result, final_report):
    try:
        db = get_db()
        db.collection("ad_campaigns").document(doc_id).update({
            "agent_opinions": agent_opinions,
            "debate_result": debate_result,
            "final_report": final_report,
        })
    except Exception:
        pass

def extract_summary(debate_result: str) -> str:
    """토론 결과에서 최종 합의 부분만 추출."""
    lines = debate_result.split("\n")
    summary_lines = []
    capture = False
    for line in lines:
        if "최종 합의" in line or "합의된" in line or "📋" in line:
            capture = True
        if capture:
            summary_lines.append(line)
    return "\n".join(summary_lines) if summary_lines else debate_result

# ─── 세션 상태 초기화 ─────────────────────────────────────
defaults = {
    "view_history": None, "analysis_done": False,
    "agent_opinions": {}, "debate_result": "", "final_report": "",
    "saved_filename": "", "current_brief": "",
    "current_cat": "", "current_budget": "",
    "selected_agents": AGENT_NAMES, "current_product": "",
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ─── 사이드바 ─────────────────────────────────────────────
with st.sidebar:
    page = st.radio("페이지 선택", ["📝 새 분석", "📦 제품 관리", "📂 분석 기록"], label_visibility="collapsed")
    st.markdown("---")

    if page == "📝 새 분석":
        st.header("🤖 에이전트 현황")
        st.caption("캠페인을 분석할수록 경험치가 쌓입니다")
        for name in AGENT_NAMES:
            memory = load_memory(name)
            total = memory.get("total_campaigns", 0)
            success = memory.get("success_count", 0)
            with st.expander(AGENT_DISPLAY_NAMES[name]):
                c1, c2 = st.columns(2)
                c1.metric("경험 캠페인", total)
                if total > 0:
                    c2.metric("채택률", f"{round(success/total*100)}%")
                else:
                    c2.caption("아직 경험 없음")
        st.markdown("---")
        st.caption("💡 피드백을 저장할수록\n에이전트가 더 똑똑해집니다")

    elif page == "📦 제품 관리":
        st.header("📦 제품 목록")
        product_list = get_product_list()
        if not product_list:
            st.caption("등록된 제품이 없습니다.")
        else:
            for pname in product_list:
                if st.button(pname, key=f"prod_{pname}", use_container_width=True):
                    st.session_state["editing_product"] = pname

    else:
        st.header("📂 분석 기록")
        history_list = load_history_list()
        if not history_list:
            st.caption("아직 저장된 기록이 없습니다.")
        else:
            st.caption(f"총 {len(history_list)}건")
            for rec in history_list:
                icon = {"성공": "✅", "보통": "🔧", "실패": "❌", None: "⏳"}.get(rec.get("outcome"), "⏳")
                label = f"{icon} {rec.get('date_display','')[:10]}\n{rec.get('brief_preview','')[:30]}..."
                if st.button(label, key=rec["_filename"], use_container_width=True):
                    st.session_state.view_history = rec["_filename"]


# ══════════════════════════════════════════════════════════
# 📦 제품 관리
# ══════════════════════════════════════════════════════════
if page == "📦 제품 관리":
    st.title("📦 제품 프로필 관리")
    st.markdown("제품별 실적 데이터를 저장해두면, 분석 시 자동으로 에이전트에게 전달됩니다.")
    st.markdown("---")

    col_new, col_edit = st.columns([1, 2])

    with col_new:
        st.subheader("새 제품 등록")
        new_product_name = st.text_input("제품/브랜드명", placeholder="예: 웰독")
        if st.button("➕ 등록", type="primary"):
            if new_product_name.strip():
                profile = load_product(new_product_name.strip())
                save_product(profile)
                st.session_state["editing_product"] = new_product_name.strip()
                st.success(f"'{new_product_name}' 등록 완료!")
                st.rerun()
            else:
                st.warning("제품명을 입력해주세요.")

    with col_edit:
        editing = st.session_state.get("editing_product", "")
        product_list = get_product_list()

        if not editing and product_list:
            editing = product_list[0]
            st.session_state["editing_product"] = editing

        if editing:
            profile = load_product(editing)
            st.subheader(f"✏️ {editing} 프로필 편집")

            profile["description"] = st.text_area(
                "제품 설명",
                value=profile.get("description", ""),
                placeholder="예: 국산 유기농 원료 100%, 알러지 프리 반려견 사료",
                height=80,
            )
            profile["insights"] = st.text_area(
                "누적 인사이트 (분석 때마다 쌓이는 내용)",
                value=profile.get("insights", ""),
                placeholder="예: 인스타 릴스 효과 좋음. 30대 여성 반응 높음. 네이버 검색량 월 5000.",
                height=100,
            )

            save_col, del_col = st.columns([3, 1])
            with save_col:
                if st.button("💾 기본정보 저장", type="secondary", use_container_width=True):
                    save_product(profile)
                    st.success("저장되었습니다!")
            with del_col:
                if st.button("🗑️ 삭제", type="secondary", use_container_width=True):
                    st.session_state["confirm_delete"] = editing

            if st.session_state.get("confirm_delete") == editing:
                st.warning(f"**'{editing}' 프로필을 정말 삭제할까요?** 실적 데이터까지 모두 사라집니다.")
                cc1, cc2 = st.columns(2)
                with cc1:
                    if st.button("✅ 네, 삭제합니다", type="primary", use_container_width=True):
                        delete_product(editing)
                        st.session_state.pop("confirm_delete", None)
                        st.session_state.pop("editing_product", None)
                        st.success(f"'{editing}' 삭제 완료!")
                        st.rerun()
                with cc2:
                    if st.button("❌ 취소", use_container_width=True):
                        st.session_state.pop("confirm_delete", None)
                        st.rerun()

            st.markdown("---")
            st.subheader("📊 실적 데이터 추가")
            st.caption("주별 실적을 입력하면 다음 분석부터 자동으로 반영됩니다.")

            now = datetime.now()
            cur_year, cur_week, _ = now.isocalendar()

            # 1행: 연도 / 주차 / 채널명
            r1c1, r1c2, r1c3 = st.columns(3)
            with r1c1:
                p_year = st.number_input("📅 연도", value=int(cur_year), min_value=2020, max_value=2030, step=1)
            with r1c2:
                p_week = st.number_input(f"📅 주차 (현재: {int(cur_week)}주)", value=int(cur_week), min_value=1, max_value=53, step=1)
            with r1c3:
                p_channel = st.text_input("📢 채널명", placeholder="인스타그램 / 네이버 / 쿠팡 / 전체")

            # 선택된 주차 날짜 범위 안내
            try:
                from datetime import timedelta
                import datetime as dt_module
                week_start = dt_module.datetime.strptime(f"{int(p_year)}-W{int(p_week):02d}-1", "%G-W%V-%u")
                week_end = week_start + timedelta(days=6)
                st.caption(f"입력 기간: {week_start.strftime('%m/%d')} ~ {week_end.strftime('%m/%d')} ({int(p_year)}년 {int(p_week)}주차)")
            except Exception:
                pass

            # 2행: ROAS / CTR / CPA
            r2c1, r2c2, r2c3 = st.columns(3)
            with r2c1:
                p_roas = st.number_input("ROAS", min_value=0.0, step=0.1, format="%.2f")
            with r2c2:
                p_ctr  = st.number_input("CTR (%)", min_value=0.0, step=0.01, format="%.2f")
            with r2c3:
                p_cpa  = st.number_input("CPA (원)", min_value=0, step=100)

            # 3행: CPC / 전환율 / 메모
            r3c1, r3c2, r3c3 = st.columns(3)
            with r3c1:
                p_cpc  = st.number_input("CPC (원)", min_value=0, step=10)
            with r3c2:
                p_cvr  = st.number_input("전환율 (%)", min_value=0.0, step=0.01, format="%.2f")
            with r3c3:
                p_notes = st.text_input("메모", placeholder="예: 릴스 효과 좋음")

            if st.button("➕ 실적 데이터 추가", type="primary"):
                if not any([p_roas > 0, p_cpc > 0, p_ctr > 0, p_cvr > 0, p_cpa > 0]):
                    st.warning("최소 하나 이상의 수치를 입력해주세요.")
                    st.stop()
                record = {
                    "date": f"{int(p_year)}-W{int(p_week):02d}",
                    "channel": p_channel.strip() if p_channel else None,
                    "roas": p_roas if p_roas > 0 else None,
                    "cpc": p_cpc if p_cpc > 0 else None,
                    "ctr": p_ctr if p_ctr > 0 else None,
                    "cvr": p_cvr if p_cvr > 0 else None,
                    "cpa": p_cpa if p_cpa > 0 else None,
                    "notes": p_notes if p_notes else None,
                }
                prof = load_product(editing)
                prof["performance_history"].append(record)
                prof["performance_history"] = prof["performance_history"][-48:]
                save_product(prof)
                st.success("실적 데이터가 추가되었습니다!")
                st.rerun()

            # 기존 실적 데이터 표시
            history = profile.get("performance_history", [])
            if history:
                st.markdown("---")
                st.subheader("📈 실적 히스토리")
                for rec in reversed(history[-8:]):
                    ch_label = rec.get("channel") or "전체"
                    with st.expander(f"📅 {rec.get('date', '')} | {ch_label}"):
                        cols = st.columns(3)
                        if rec.get("roas"):    cols[0].metric("ROAS", rec["roas"])
                        if rec.get("cpc"):     cols[1].metric("CPC", f"{rec['cpc']}원")
                        if rec.get("ctr"):     cols[2].metric("CTR", f"{rec['ctr']}%")
                        if rec.get("cvr"):     cols[0].metric("전환율", f"{rec['cvr']}%")
                        if rec.get("cpa"):     cols[1].metric("CPA", f"{rec['cpa']}원")
                        if rec.get("notes"):   st.caption(f"메모: {rec['notes']}")
        else:
            st.info("왼쪽에서 제품을 선택하거나 새 제품을 등록해주세요.")


# ══════════════════════════════════════════════════════════
# 📂 분석 기록 보기
# ══════════════════════════════════════════════════════════
elif page == "📂 분석 기록":
    if st.session_state.view_history:
        try:
            db = get_db()
            doc = db.collection("ad_campaigns").document(st.session_state.view_history).get()
            rec = doc.to_dict() if doc.exists else {}

            st.title("📂 분석 기록 상세보기")
            st.caption(f"분석일시: {rec.get('date_display','')} | 카테고리: {rec.get('category','')} | 예산: {rec.get('budget_range','')}")
            if st.button("← 목록으로"):
                st.session_state.view_history = None
                st.rerun()

            st.markdown("---")
            view_tabs = st.tabs(["📋 최종 합의", "🤖 에이전트별 분석", "📝 원본 브리프"])

            with view_tabs[0]:
                st.markdown(rec.get("debate_result", ""))
                if rec.get("final_report"):
                    st.download_button("📥 보고서 다운로드",
                        data=rec["final_report"].encode("utf-8"),
                        file_name=f"광고전략_{rec.get('date_display','')[:10]}.md",
                        mime="text/markdown")

            with view_tabs[1]:
                opinion_tabs = st.tabs(TAB_LABELS)
                for i, key in enumerate(AGENT_NAMES):
                    with opinion_tabs[i]:
                        st.markdown(rec.get("agent_opinions", {}).get(key, "기록 없음"))

            with view_tabs[2]:
                st.text(rec.get("brief", ""))

            st.markdown("---")
            if not rec.get("outcome"):
                st.subheader("💬 피드백 남기기")
                outcome = st.radio("평가", ["✅ 채택 (좋음)", "🔧 일부 수정 후 채택", "❌ 참고만 함"])

                # 실적 데이터 입력 (제품 프로필 연동)
                product_name = rec.get("product_name", "")
                if product_name:
                    st.markdown(f"**📊 '{product_name}' 실적 데이터 업데이트** (선택사항)")
                    fc1, fc2, fc3 = st.columns(3)
                    with fc1:
                        fb_roas = st.number_input("ROAS", min_value=0.0, step=0.1, format="%.2f", key="fb_roas")
                        fb_cpc  = st.number_input("CPC (원)", min_value=0, step=10, key="fb_cpc")
                    with fc2:
                        fb_ctr  = st.number_input("CTR (%)", min_value=0.0, step=0.01, format="%.2f", key="fb_ctr")
                        fb_cvr  = st.number_input("전환율 (%)", min_value=0.0, step=0.01, format="%.2f", key="fb_cvr")
                    with fc3:
                        fb_cpa  = st.number_input("CPA (원)", min_value=0, step=100, key="fb_cpa")
                        fb_channels = st.text_input("채널명", placeholder="예: 인스타그램 / 네이버 / 전체", key="fb_channels")

                learnings = st.text_area("결과 메모", placeholder="실제 캠페인 결과나 느낀 점을 입력하세요")

                if st.button("💾 피드백 저장", type="primary"):
                    omap = {"✅ 채택 (좋음)": "성공", "🔧 일부 수정 후 채택": "보통", "❌ 참고만 함": "실패"}
                    update_history_outcome(st.session_state.view_history, omap[outcome], learnings)
                    for name in AGENT_NAMES:
                        add_experience(name, {
                            "summary": rec["brief"][:120],
                            "category": rec.get("category",""),
                            "budget_range": rec.get("budget_range",""),
                            "channels": [], "learnings": learnings
                        }, omap[outcome])
                    # 제품 실적 데이터 저장
                    if product_name and (fb_roas > 0 or fb_cpc > 0 or fb_ctr > 0):
                        perf_record = {
                            "roas": fb_roas if fb_roas > 0 else None,
                            "cpc": fb_cpc if fb_cpc > 0 else None,
                            "ctr": fb_ctr if fb_ctr > 0 else None,
                            "cvr": fb_cvr if fb_cvr > 0 else None,
                            "cpa": fb_cpa if fb_cpa > 0 else None,
                            "channel": fb_channels.strip() if fb_channels else None,
                            "notes": learnings[:100] if learnings else None,
                        }
                        add_performance_record(product_name, perf_record)
                        # 인사이트 누적
                        if learnings:
                            profile = load_product(product_name)
                            existing = profile.get("insights", "")
                            new_insight = f"[{datetime.now().strftime('%Y-%m')}] {learnings[:150]}"
                            profile["insights"] = f"{existing}\n{new_insight}".strip() if existing else new_insight
                            save_product(profile)
                    st.success("✅ 저장되었습니다!")
                    st.balloons()
            else:
                icon = {"성공": "✅", "보통": "🔧", "실패": "❌"}.get(rec["outcome"], "")
                st.info(f"평가: {icon} {rec['outcome']} | 메모: {rec.get('learnings','없음')}")

        except Exception as e:
            st.error(f"기록을 불러올 수 없습니다: {e}")
    else:
        st.title("📂 분석 기록")
        history_list = load_history_list()
        if not history_list:
            st.info("아직 저장된 분석 기록이 없습니다. 새 분석을 실행해보세요!")
        else:
            st.caption(f"총 {len(history_list)}건 | 왼쪽 목록에서 항목을 클릭하세요.")
            for rec in history_list:
                icon = {"성공": "✅", "보통": "🔧", "실패": "❌", None: "⏳"}.get(rec.get("outcome"), "⏳")
                with st.expander(f"{icon} {rec.get('date_display','')} | {rec.get('category','')} | {rec.get('brief_preview','')}"):
                    st.caption(f"예산: {rec.get('budget_range','')} | 평가: {rec.get('outcome','미평가')}")
                    if st.button("상세보기", key=f"detail_{rec['_filename']}"):
                        st.session_state.view_history = rec["_filename"]
                        st.rerun()


# ══════════════════════════════════════════════════════════
# 📝 새 분석
# ══════════════════════════════════════════════════════════
else:
    st.title("📢 광고집행 멀티에이전트 시스템")
    st.markdown("광고 브리프를 입력하면 5명의 AI 전문가가 분석하고 토론하여 최적의 전략을 제안합니다.")
    st.markdown("---")

    st.header("1️⃣ 광고 브리프 입력")

    with st.expander("📌 브리프 작성 가이드 (항상 참고 가능)", expanded=True):
        st.markdown(BRIEF_GUIDE)

    st.markdown("")

    with st.form("brief_form"):

        # ── 제품 프로필 선택 ──────────────────────────────
        product_list = get_product_list()
        product_options = ["선택 안 함 (일회성 분석)"] + product_list + ["➕ 새 제품 등록"]

        selected_product_option = st.selectbox(
            "📦 제품 프로필 선택 (등록된 제품은 실적 데이터가 자동으로 포함됩니다)",
            product_options,
        )

        brief = st.text_area(
            "광고 브리프 입력",
            height=200,
            placeholder="위 가이드를 참고하여 자유롭게 입력하세요.",
        )

        # 파일 첨부
        st.markdown("**📎 운영 데이터 파일 첨부** (선택사항 — txt, csv)")
        uploaded_file = st.file_uploader(
            "실적 데이터 파일 업로드",
            type=["txt", "csv"],
            label_visibility="collapsed",
        )

        col1, col2 = st.columns(2)
        with col1:
            category = st.selectbox("제품/서비스 카테고리", CATEGORIES)
        with col2:
            budget_range = st.selectbox("월 예산 규모", BUDGET_RANGES)

        st.markdown("**참여할 에이전트 선택** (원하는 것만 체크)")
        agent_cols = st.columns(5)
        selected_agents = []
        for i, name in enumerate(AGENT_NAMES):
            with agent_cols[i]:
                checked = st.checkbox(
                    AGENT_DISPLAY_NAMES[name].split(" ", 1)[-1],
                    value=True, key=f"chk_{name}"
                )
                if checked:
                    selected_agents.append(name)

        submitted = st.form_submit_button("🚀 에이전트 분석 시작", type="primary", use_container_width=True)

    # 새 제품 등록 안내
    if selected_product_option == "➕ 새 제품 등록":
        st.info("👉 왼쪽 사이드바에서 **📦 제품 관리** 탭으로 이동하여 제품을 등록해주세요.")

    # 선택된 제품 프로필 미리보기
    product_name = ""
    if selected_product_option not in ["선택 안 함 (일회성 분석)", "➕ 새 제품 등록"]:
        product_name = selected_product_option
        profile_summary = get_profile_summary(product_name)
        if profile_summary:
            with st.expander(f"📦 '{product_name}' 프로필 미리보기", expanded=False):
                st.markdown(profile_summary)

    # ── 분석 실행 ─────────────────────────────────────────
    if submitted:
        if not brief.strip():
            st.error("브리프를 입력해주세요.")
            st.stop()
        if not selected_agents:
            st.error("에이전트를 1명 이상 선택해주세요.")
            st.stop()

        # 브리프 조합: 기본 브리프 + 제품 프로필 + 파일 첨부
        final_brief = brief

        if product_name:
            profile_text = get_profile_summary(product_name)
            if profile_text:
                final_brief += f"\n\n{profile_text}"

        if uploaded_file is not None:
            try:
                file_content = uploaded_file.read().decode("utf-8")
            except Exception:
                try:
                    uploaded_file.seek(0)
                    file_content = uploaded_file.read().decode("cp949")
                except Exception:
                    file_content = ""
            if file_content:
                final_brief += f"\n\n## 첨부 데이터 ({uploaded_file.name})\n{file_content}"
                st.info(f"📎 '{uploaded_file.name}' 파일이 포함되었습니다.")

        st.session_state.analysis_done   = False
        st.session_state.agent_opinions  = {}
        st.session_state.current_brief   = final_brief
        st.session_state.current_cat     = category
        st.session_state.current_budget  = budget_range
        st.session_state.selected_agents = selected_agents
        st.session_state.current_product = product_name

        st.markdown("---")
        st.header("2️⃣ 에이전트 독립 분석")
        if product_name:
            st.info(f"📦 '{product_name}' 프로필 데이터가 포함된 상태로 분석합니다.")
        else:
            st.info(f"선택된 {len(selected_agents)}명의 에이전트가 분석합니다. 잠시 기다려주세요...")

        sel_labels = [TAB_LABELS[AGENT_NAMES.index(n)] for n in selected_agents]
        tabs = st.tabs(sel_labels)
        for i, name in enumerate(selected_agents):
            with tabs[i]:
                with st.spinner(f"{AGENT_DISPLAY_NAMES[name]} 분석 중..."):
                    try:
                        opinion = AGENT_MODULES[name].analyze(final_brief, category, budget_range)
                        st.markdown(opinion)
                        st.session_state.agent_opinions[name] = opinion
                    except Exception as e:
                        st.error(f"분석 중 오류: {e}")
                        st.session_state.agent_opinions[name] = f"[오류: {e}]"

        if len(selected_agents) >= 2:
            st.markdown("---")
            st.header("3️⃣ 에이전트 토론 및 합의")
            with st.spinner("토론 진행 중..."):
                try:
                    debate_result = run_debate(final_brief, st.session_state.agent_opinions)
                    final_report  = generate_report(final_brief, debate_result, category, budget_range)
                    st.session_state.debate_result = debate_result
                    st.session_state.final_report  = final_report
                    st.session_state.analysis_done = True
                except Exception as e:
                    st.error(f"토론 중 오류: {e}")
                    st.stop()

            result_tabs = st.tabs(["📋 최종 합의 (요약)", "📄 전체 토론 내용"])
            with result_tabs[0]:
                st.markdown(extract_summary(debate_result))
            with result_tabs[1]:
                st.markdown(debate_result)
        else:
            only_opinion = list(st.session_state.agent_opinions.values())[0]
            final_report = generate_report(final_brief, only_opinion, category, budget_range)
            st.session_state.debate_result = only_opinion
            st.session_state.final_report  = final_report
            st.session_state.analysis_done = True

        saved_path = save_history(
            final_brief, category, budget_range,
            st.session_state.agent_opinions,
            st.session_state.debate_result,
            st.session_state.final_report,
            product_name,
        )
        st.session_state.saved_filename = os.path.basename(saved_path)
        st.success("📂 분석 결과가 자동 저장되었습니다.")

    # ── 분석 완료 후 UI ───────────────────────────────────
    if st.session_state.analysis_done:
        brief        = st.session_state.current_brief
        category     = st.session_state.current_cat
        budget_range = st.session_state.current_budget
        product_name = st.session_state.current_product

        st.markdown("---")
        st.header("🔄 에이전트별 심층 분석 요청")
        st.caption("특정 에이전트에게 추가 요청을 보내 더 깊이 분석하게 할 수 있습니다.")

        active_agents = st.session_state.get("selected_agents", AGENT_NAMES)
        sel_labels = [TAB_LABELS[AGENT_NAMES.index(n)] for n in active_agents]
        tabs = st.tabs(sel_labels)
        for i, name in enumerate(active_agents):
            with tabs[i]:
                st.markdown(st.session_state.agent_opinions.get(name, ""))
                st.markdown("---")
                add_req = st.text_area(
                    "이 에이전트에게 추가 요청",
                    key=f"req_{name}",
                    placeholder="예: 예산을 50% 줄였을 때 전략 / 20대 타겟으로 수정 / 더 구체적인 수치로",
                    height=80,
                )
                if st.button(f"🔄 {AGENT_DISPLAY_NAMES[name]} 재분석", key=f"btn_{name}", type="secondary"):
                    if not add_req.strip():
                        st.warning("추가 요청 내용을 입력해주세요.")
                    else:
                        with st.spinner(f"{AGENT_DISPLAY_NAMES[name]} 재분석 중..."):
                            try:
                                new_brief = f"{brief}\n\n## 추가 요청\n{add_req}"
                                new_opinion = AGENT_MODULES[name].analyze(new_brief, category, budget_range)
                                st.session_state.agent_opinions[name] = new_opinion
                                st.success("✅ 재분석 완료!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"재분석 중 오류: {e}")

        st.markdown("---")
        st.header("🔄 전체 에이전트 동시 재분석")
        all_req = st.text_area(
            "전체 에이전트에게 추가 지시",
            key="req_all",
            placeholder="예: 예산을 200만원으로 줄여서 다시 분석 / 타겟을 50대 남성으로 변경",
            height=80,
        )
        if st.button("🚀 전체 재분석 + 토론 재실행", type="primary", use_container_width=True):
            if not all_req.strip():
                st.warning("추가 지시 내용을 입력해주세요.")
            else:
                new_brief = f"{brief}\n\n## 추가 지시 (전체)\n{all_req}"
                new_opinions = {}
                rtabs = st.tabs([TAB_LABELS[AGENT_NAMES.index(n)] for n in active_agents])
                for i, name in enumerate(active_agents):
                    with rtabs[i]:
                        with st.spinner(f"{AGENT_DISPLAY_NAMES[name]} 재분석 중..."):
                            try:
                                op = AGENT_MODULES[name].analyze(new_brief, category, budget_range)
                                st.markdown(op)
                                new_opinions[name] = op
                            except Exception as e:
                                st.error(f"오류: {e}")
                                new_opinions[name] = f"[오류: {e}]"
                st.session_state.agent_opinions = new_opinions
                with st.spinner("토론 진행 중..."):
                    try:
                        new_debate = run_debate(new_brief, new_opinions)
                        new_report = generate_report(new_brief, new_debate, category, budget_range)
                        st.session_state.debate_result = new_debate
                        st.session_state.final_report  = new_report
                    except Exception as e:
                        st.error(f"토론 오류: {e}")
                        st.stop()

                result_tabs = st.tabs(["📋 최종 합의 (요약)", "📄 전체 토론 내용"])
                with result_tabs[0]:
                    st.markdown(extract_summary(new_debate))
                with result_tabs[1]:
                    st.markdown(new_debate)

                if st.session_state.saved_filename:
                    update_history_opinions(st.session_state.saved_filename, new_opinions, new_debate, new_report)
                    st.success("📂 재분석 결과가 기존 기록에 업데이트되었습니다.")

        # ── 보고서 다운로드 + 피드백 ──────────────────────
        st.markdown("---")
        st.header("4️⃣ 최종 결정 및 피드백")
        st.download_button(
            label="📥 전략 보고서 다운로드 (.md)",
            data=st.session_state.final_report.encode("utf-8"),
            file_name=f"광고전략_{datetime.now().strftime('%Y%m%d_%H%M')}.md",
            mime="text/markdown",
            use_container_width=True,
        )

        st.markdown("### 이 전략을 어떻게 평가하시나요?")
        col1, col2 = st.columns([1, 2])
        with col1:
            outcome = st.radio("평가", ["✅ 채택 (좋음)", "🔧 일부 수정 후 채택", "❌ 참고만 함"], label_visibility="collapsed")
        with col2:
            learnings = st.text_area(
                "캠페인 진행 후 결과 메모",
                placeholder="예: 인스타그램 릴스 ROAS 3.2 달성. 네이버 파워링크 클릭률 예상보다 낮았음.",
                height=100,
            )

        # 피드백 저장 시 실적 데이터도 함께 저장
        if product_name:
            st.markdown(f"**📊 '{product_name}' 실적 데이터 업데이트** (선택사항)")
            pc1, pc2, pc3 = st.columns(3)
            with pc1:
                p_roas = st.number_input("ROAS", min_value=0.0, step=0.1, format="%.2f", key="p_roas")
                p_cpc  = st.number_input("CPC (원)", min_value=0, step=10, key="p_cpc")
            with pc2:
                p_ctr  = st.number_input("CTR (%)", min_value=0.0, step=0.01, format="%.2f", key="p_ctr")
                p_cvr  = st.number_input("전환율 (%)", min_value=0.0, step=0.01, format="%.2f", key="p_cvr")
            with pc3:
                p_cpa  = st.number_input("CPA (원)", min_value=0, step=100, key="p_cpa")
                p_ch   = st.text_input("채널명", placeholder="예: 인스타그램 / 네이버 / 전체", key="p_ch")

        if st.button("💾 피드백 저장 (에이전트 학습)", type="secondary", use_container_width=True):
            omap = {"✅ 채택 (좋음)": "성공", "🔧 일부 수정 후 채택": "보통", "❌ 참고만 함": "실패"}
            if st.session_state.saved_filename:
                update_history_outcome(st.session_state.saved_filename, omap[outcome], learnings)
            for name in AGENT_NAMES:
                add_experience(name, {
                    "summary": brief[:120], "category": category,
                    "budget_range": budget_range, "channels": [], "learnings": learnings,
                }, omap[outcome])

            # 제품 프로필에 실적 + 인사이트 저장
            if product_name:
                if p_roas > 0 or p_cpc > 0 or p_ctr > 0:
                    add_performance_record(product_name, {
                        "roas": p_roas if p_roas > 0 else None,
                        "cpc": p_cpc if p_cpc > 0 else None,
                        "ctr": p_ctr if p_ctr > 0 else None,
                        "cvr": p_cvr if p_cvr > 0 else None,
                        "cpa": p_cpa if p_cpa > 0 else None,
                        "channel": p_ch.strip() if p_ch else None,
                        "notes": learnings[:100] if learnings else None,
                    })
                if learnings:
                    prof = load_product(product_name)
                    existing = prof.get("insights", "")
                    new_insight = f"[{datetime.now().strftime('%Y-%m')}] {learnings[:150]}"
                    prof["insights"] = f"{existing}\n{new_insight}".strip() if existing else new_insight
                    save_product(prof)

            st.success("✅ 에이전트 메모리 + 제품 프로필에 저장되었습니다!")
            st.balloons()
