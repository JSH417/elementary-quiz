import streamlit as st
import re
import difflib
import json
import os

# Music modules
from question_generator import get_filtered_questions, QUESTION_POOL
from ai_engine import (
    generate_ai_questions,
    evaluate_with_ai,
    get_supported_models,
    test_api_connection
)

# Math modules
from math_question_generator import get_filtered_math_questions, MATH_QUESTION_POOL
from math_ai_engine import (
    generate_math_ai_questions,
    evaluate_math_with_ai
)

st.set_page_config(
    page_title="초등 임용 스마트 문제은행 & AI 무한 생성기",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.1rem;
        font-weight: 700;
        color: #1E3A8A;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.0rem;
        color: #4B5563;
        margin-bottom: 1.2rem;
    }
    .badge-a {
        background-color: #EF4444; color: white; padding: 3px 8px; border-radius: 6px; font-weight: 600; font-size: 0.78rem;
    }
    .badge-b {
        background-color: #F59E0B; color: white; padding: 3px 8px; border-radius: 6px; font-weight: 600; font-size: 0.78rem;
    }
    .badge-c {
        background-color: #10B981; color: white; padding: 3px 8px; border-radius: 6px; font-weight: 600; font-size: 0.78rem;
    }
    .badge-d {
        background-color: #6B7280; color: white; padding: 3px 8px; border-radius: 6px; font-weight: 600; font-size: 0.78rem;
    }
    .dialogue-box {
        background-color: #F0FDF4;
        border-left: 4px solid #10B981;
        padding: 14px 18px;
        margin: 12px 0;
        border-radius: 0 8px 8px 0;
        font-size: 0.95rem;
        line-height: 1.65;
    }
    .ai-box {
        background-color: #FAF5FF;
        border: 1.5px solid #D8B4FE;
        border-radius: 8px;
        padding: 14px;
        margin: 10px 0;
    }
    .rubric-pass {
        color: #059669; font-weight: 600;
    }
    .rubric-fail {
        color: #DC2626; font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# Local regex evaluator fallback with strict score counting and Korean synonym support
def evaluate_answer_local(user_ans, correct_ans, keywords, criteria_list):
    if not user_ans or not user_ans.strip():
        return {
            "score_ratio": 0.0,
            "similarity": 0.0,
            "passed_keywords": [],
            "missing_keywords": keywords,
            "criteria_results": [(c, False) for c, _ in criteria_list],
            "critique": "답안이 입력되지 않았습니다."
        }
    
    clean_user = re.sub(r"[\s.,()'\"`]+", "", user_ans).lower()
    
    # Keyword check
    passed_kw = []
    missing_kw = []
    for kw in keywords:
        clean_kw = re.sub(r"[\s.,()'\"`]+", "", kw).lower()
        if clean_kw in clean_user:
            passed_kw.append(kw)
        else:
            missing_kw.append(kw)
            
    # Criteria evaluation with Korean synonym & particle flexibility
    crit_res = []
    for desc, req_kws in criteria_list:
        passed = False
        for rk in req_kws:
            pattern = re.sub(r"[\s.,()'\"`]+", "", rk).lower()
            if pattern in clean_user:
                passed = True
                break
            if re.search(rk, user_ans, re.IGNORECASE):
                passed = True
                break
            # Check synonyms for "같다 / 일치 / 동일"
            if any(syn in clean_user for syn in ["동일", "일치", "같아", "같다", "같음"]) and any(syn in pattern for syn in ["동일", "일치", "같아", "같다", "같음"]):
                passed = True
                break
        crit_res.append((desc, passed))
        
    # Strictly count only criteria where passed is True!
    pass_count = sum(1 for _, p in crit_res if p)
    total_crit = len(crit_res)
    score_ratio = (pass_count / total_crit) if total_crit > 0 else 0.0
    
    sim = difflib.SequenceMatcher(None, user_ans.strip(), correct_ans.strip()).ratio()
    combined_sim = min(1.0, (score_ratio * 0.7) + (sim * 0.3)) if score_ratio > 0 else 0.0
    
    return {
        "score_ratio": score_ratio,
        "similarity": round(combined_sim * 100, 1),
        "passed_keywords": passed_kw,
        "missing_keywords": missing_kw,
        "criteria_results": crit_res,
        "critique": "로컬 규칙 기반 키워드 채점이 완료되었습니다."
    }

# Read API key from st.secrets or environment
ENV_API_KEY = ""
try:
    if hasattr(st, "secrets") and "GEMINI_API_KEY" in st.secrets:
        ENV_API_KEY = st.secrets["GEMINI_API_KEY"]
except Exception:
    pass

if not ENV_API_KEY:
    ENV_API_KEY = os.environ.get("GEMINI_API_KEY", "")

# Sidebar
with st.sidebar:
    st.image("https://img.icons8.com/color/96/education.png", width=64)
    st.title("임용 시험관 센터")
    
    st.markdown("### 📚 학습 과목 선택")
    subject_choice = st.radio(
        "출제 및 분석 과목:",
        ["📐 초등 수학 (1682p 각론완성)", "🎵 초등 음악 (498p 각론완성)"],
        index=0
    )
    is_math = "수학" in subject_choice
    
    st.markdown("---")
    st.markdown("### 🔑 AI 실시간 무한 생성 설정")
    api_key_input = st.text_input(
        "Google Gemini API Key:",
        value=ENV_API_KEY,
        type="password",
        help="Google AI Studio (aistudio.google.com)에서 발급받은 API 키를 입력하세요."
    )
    
    selected_model = None
    if api_key_input:
        if "cached_key" not in st.session_state or st.session_state.get("cached_key") != api_key_input.strip():
            st.session_state["cached_key"] = api_key_input.strip()
            with st.spinner("사용 가능한 최신 AI 모델 탐색 중..."):
                st.session_state["discovered_models"] = get_supported_models(api_key_input)
        
        available_models = st.session_state.get("discovered_models", ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"])
        
        selected_model = st.selectbox(
            "🤖 적용할 Gemini AI 모델:",
            available_models,
            index=0,
            help="사용자의 API 키에서 지원하는 최적의 AI 모델입니다."
        )
        
        col_btn_test, col_btn_status = st.columns([1, 1])
        with col_btn_test:
            if st.button("⚡ 연결 테스트", use_container_width=True):
                with st.spinner("모델 응답 확인 중..."):
                    ok, msg, m_used = test_api_connection(api_key_input, selected_model)
                    if ok:
                        st.success(f"✅ {msg}")
                    else:
                        st.error(f"❌ {msg}")
        with col_btn_status:
            st.caption(f"🟢 **무한 창작 활성**\n({selected_model})")
    else:
        st.info("🟡 기본 문제은행 모드")
        st.caption("API 키 입력 시 AI 무한 생성 모드로 즉시 전환됩니다.")
        
    st.markdown("---")
    menu = st.radio("메뉴를 선택하세요", [
        "🎯 나만의 맞춤형 문제 출제기",
        "📊 14개년 기출 & ABCD 매트릭스",
        "📖 각론 및 기본이론 지도 사전"
    ])
    st.markdown("---")
    st.markdown("**📌 데이터베이스 탑재 현황:**")
    if is_math:
        st.caption("• 2013~2026 수학 14개년 기출 DB")
        st.caption("• 2022 개정 수학과 5대 교과 역량")
        st.caption("• 1682p 수학 C 각론완성 전단원")
    else:
        st.caption("• 2013~2026 음악 14개년 기출 DB")
        st.caption("• 2022 개정 음악과 교육과정 체계")
        st.caption("• 498p 음악 C 각론완성 69개 제재곡")

# Session State for generated quiz
subject_key = "math" if is_math else "music"
quiz_session_key = f"current_quiz_{subject_key}"

if quiz_session_key not in st.session_state:
    if is_math:
        st.session_state[quiz_session_key] = get_filtered_math_questions("전체 (랜덤 혼합)", "전체", "전체", 3)
    else:
        st.session_state[quiz_session_key] = get_filtered_questions("전체 (랜덤 혼합)", "전체", "전체", 3)

# =========================================================================
# MENU 1: 맞춤형 문제 출제기
# =========================================================================
if menu == "🎯 나만의 맞춤형 문제 출제기":
    subj_name = "초등 수학" if is_math else "초등 음악"
    doc_info = "1,682페이지 각론과 14개년 기출 빅데이터" if is_math else "498페이지 각론과 14개년 기출 빅데이터"
    
    st.markdown(f"<div class='main-header'>🎯 {subj_name} 맞춤형 문제 출제 & AI 자동 채점기</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='sub-header'>{doc_info}에 근거하여 <b>문제 형태(개념 빈칸만 / 완전 서술형만 / 실전 세트)</b>와 <b>중요도(ABCD)</b>를 선택하여 문제를 생성하세요.</div>", unsafe_allow_html=True)

    # Configuration Card
    with st.expander("⚙️ [문제 구성 설정 패널] - 원하는 출제 옵션을 선택하세요", expanded=True):
        c1, c2, c3, c4 = st.columns(4)
        
        with c1:
            q_type_choice = st.selectbox(
                "1. 문제 형태 선택",
                ["전체 (랜덤 혼합)", "개념 빈칸 채우기 (단답형)", "완전 서술형", "실전 기출 대문항 세트"]
            )
        with c2:
            tier_choice = st.selectbox(
                "2. 중요도(ABCD) 등급",
                ["전체", "A등급 (초빈출)", "B등급 (유력 출제)", "C등급 (세부 각론)", "D등급 (교육과정)"]
            )
        with c3:
            if is_math:
                domain_choice = st.selectbox(
                    "3. 세부 영역 선택",
                    ["전체", "수와 연산", "도형과 측정", "변화와 관계", "자료와 가능성", "수학 교육론"]
                )
            else:
                domain_choice = st.selectbox(
                    "3. 세부 영역 선택",
                    ["전체", "국악", "서양음악", "교육과정"]
                )
        with c4:
            count_choice = st.slider("4. 출제 문항 수", min_value=1, max_value=6, value=3)

        col_btn1, col_btn2 = st.columns([2, 1])
        with col_btn1:
            gen_btn = st.button("🎲 위 조건으로 새로운 문제 세트 생성하기", use_container_width=True, type="primary")
        with col_btn2:
            if api_key_input:
                st.caption(f"✨ **Gemini AI ({selected_model}) 무한 창작**")
            else:
                st.caption("📦 **엄선된 각론 DB에서 랜덤 인출**")

        if gen_btn:
            st.session_state["quiz_submitted"] = False
            if api_key_input:
                model_label = selected_model or "Gemini"
                target_book = "1682p 수학 각론" if is_math else "498p 음악 각론"
                with st.spinner(f"🤖 Gemini AI({model_label})가 {target_book}과 기출 분석을 바탕으로 완전히 새로운 문제를 실시간 창작 중입니다... (약 3~5초)"):
                    try:
                        if is_math:
                            ai_quiz, used_m = generate_math_ai_questions(api_key_input, q_type_choice, tier_choice, domain_choice, count_choice, selected_model)
                        else:
                            ai_quiz, used_m = generate_ai_questions(api_key_input, q_type_choice, tier_choice, domain_choice, count_choice, selected_model)
                            
                        st.session_state[quiz_session_key] = ai_quiz
                        st.session_state["is_ai_generated"] = True
                        st.session_state["used_model"] = used_m
                        st.session_state["last_gen_error"] = None
                        st.rerun()
                    except Exception as e:
                        st.session_state["last_gen_error"] = str(e)
                        st.session_state["is_ai_generated"] = False
                        if is_math:
                            st.session_state[quiz_session_key] = get_filtered_math_questions(q_type_choice, tier_choice, domain_choice, count_choice)
                        else:
                            st.session_state[quiz_session_key] = get_filtered_questions(q_type_choice, tier_choice, domain_choice, count_choice)
                        st.rerun()
            else:
                st.session_state["is_ai_generated"] = False
                st.session_state["last_gen_error"] = None
                if is_math:
                    st.session_state[quiz_session_key] = get_filtered_math_questions(q_type_choice, tier_choice, domain_choice, count_choice)
                else:
                    st.session_state[quiz_session_key] = get_filtered_questions(q_type_choice, tier_choice, domain_choice, count_choice)
                st.rerun()

    # Show generation status banner
    if st.session_state.get("last_gen_error"):
        st.error(f"⚠️ **AI 실시간 생성 오류**:\n\n```\n{st.session_state['last_gen_error']}\n```\n\n*일시적으로 기본 문제은행에서 문제를 로드했습니다. 사이드바의 API 키 또는 모델을 확인해 주세요.*")
    
    quiz = st.session_state[quiz_session_key]

    if not quiz:
        st.warning("⚠️ 선택하신 조건에 해당하는 문항이 문제 풀에 없습니다. 다른 조건을 선택해 주세요.")
    else:
        if st.session_state.get("is_ai_generated", False):
            used_m = st.session_state.get("used_model", selected_model or "Gemini")
            st.markdown(f"✨ <span style='background-color:#E0E7FF; color:#3730A3; padding:5px 12px; border-radius:6px; font-weight:700;'>🤖 Gemini AI [{used_m}] 실시간 무한 창작 모드 작동 중 — 매번 완전히 새로운 미기출 변형 문제</span>", unsafe_allow_html=True)
        else:
            st.markdown("📦 <span style='background-color:#FEF3C7; color:#92400E; padding:5px 12px; border-radius:6px; font-weight:700;'>기본 각론 문제은행 모드 (사이드바에 Gemini API 키를 넣으시면 AI 무한 창작 모드로 전환됩니다)</span>", unsafe_allow_html=True)

        st.markdown("---")

        # Question Presentation Form
        with st.form("exam_paper_form"):
            user_inputs = {}

            for idx, item in enumerate(quiz):
                q_num = idx + 1
                tier_badge = "badge-a" if "A등급" in item.get("tier", "") else ("badge-b" if "B등급" in item.get("tier", "") else ("badge-c" if "C등급" in item.get("tier", "") else "badge-d"))
                
                st.markdown(f"##### [문항 {q_num}] {item['type']} <span class='{tier_badge}'>{item.get('tier','A등급')}</span> · {item.get('domain','공통')}", unsafe_allow_html=True)
                
                # Check if it's a SET question
                if item["type"] == "실전 기출 대문항 세트" and item.get("sub_questions"):
                    st.markdown(f"**[대문항: {item['title']} - {item['points']}점]**")
                    if item.get("dialogue"):
                        st.markdown(f"<div class='dialogue-box'>{item['dialogue']}</div>", unsafe_allow_html=True)
                    
                    user_inputs[item["id"]] = {}
                    for sub in item["sub_questions"]:
                        sub_key = f"{item['id']}_{sub['sub_no']}_{idx}"
                        st.markdown(f"**{sub['sub_no']}** {sub['question']}")
                        if sub["type"] == "서술형":
                            ans = st.text_area(f"답안 입력 ({sub['sub_no']}):", key=sub_key, height=75)
                        else:
                            ans = st.text_input(f"답안 입력 ({sub['sub_no']}):", key=sub_key)
                        user_inputs[item["id"]][sub["sub_no"]] = ans
                else:
                    st.markdown(f"**[발문]** {item['question']}")
                    key = f"q_single_{item['id']}_{idx}"
                    if item["type"] == "완전 서술형":
                        ans = st.text_area(f"문항 {q_num} 답안 입력 ({item['points']}점):", key=key, height=90)
                    else:
                        ans = st.text_input(f"문항 {q_num} 답안 입력 ({item['points']}점):", key=key)
                    user_inputs[item["id"]] = ans

                st.markdown("---")

            submit = st.form_submit_button("💯 답안 일괄 제출 및 실시간 채점하기", use_container_width=True, type="primary")

        # Evaluation & Feedback
        if submit:
            st.markdown("## 📋 실시간 채점 결과 및 루브릭 첨삭 리포트")
            
            total_earned = 0.0
            max_possible = sum(item["points"] for item in quiz)
            
            for idx, item in enumerate(quiz):
                q_num = idx + 1
                st.markdown(f"### [문항 {q_num}] {item['title']} ({item['type']})")
                
                if item["type"] == "실전 기출 대문항 세트" and item.get("sub_questions"):
                    set_inputs = user_inputs.get(item["id"], {})
                    sub_earned_total = 0.0
                    
                    for sub in item["sub_questions"]:
                        u_ans = set_inputs.get(sub["sub_no"], "")
                        
                        ai_done = False
                        if api_key_input and sub["type"] == "서술형":
                            try:
                                with st.spinner(f"소문항 {sub['sub_no']} AI 채점관({selected_model})이 심층 분석 중..."):
                                    if is_math:
                                        ai_eval = evaluate_math_with_ai(api_key_input, sub["question"], sub["answer"], sub["rubric"], u_ans, sub["points"], selected_model)
                                    else:
                                        ai_eval = evaluate_with_ai(api_key_input, sub["question"], sub["answer"], sub["rubric"], u_ans, sub["points"], selected_model)
                                        
                                    sub_earned = ai_eval["score"]
                                    sub_earned_total += sub_earned
                                    ai_done = True
                                    
                                    with st.expander(f"소문항 {sub['sub_no']} ({sub_earned}/{sub['points']}점) - AI 정밀 첨삭", expanded=True):
                                        c1, c2 = st.columns([1, 1])
                                        c1.info(f"**수험생 답안:** {u_ans if u_ans else '(미입력)'}")
                                        c2.success(f"**공식 모범답안:** {sub['answer']}")
                                        st.markdown(f"<div class='ai-box'><b>🧑‍🏫 AI 채점관 총평:</b><br>{ai_eval['critique']}</div>", unsafe_allow_html=True)
                            except Exception as e:
                                st.warning(f"AI 채점 중 일시적 오류로 규칙 기반 채점으로 전환: {e}")
                                ai_done = False

                        if not ai_done:
                            eval_res = evaluate_answer_local(u_ans, sub["answer"], sub["keywords"], sub["rubric"])
                            sub_earned = round(eval_res["score_ratio"] * sub["points"], 1)
                            sub_earned_total += sub_earned
                            
                            with st.expander(f"소문항 {sub['sub_no']} ({sub_earned}/{sub['points']}점)", expanded=True):
                                c1, c2 = st.columns([1, 1])
                                c1.info(f"**수험생 답안:** {u_ans if u_ans else '(미입력)'}")
                                c2.success(f"**공식 모범답안:** {sub['answer']}")
                                for crit, passed in eval_res["criteria_results"]:
                                    if passed:
                                        st.markdown(f"• <span class='rubric-pass'>[충족 +배점]</span> {crit}", unsafe_allow_html=True)
                                    else:
                                        st.markdown(f"• <span class='rubric-fail'>[미흡 -감점]</span> {crit}", unsafe_allow_html=True)
                                        
                    total_earned += sub_earned_total
                else:
                    u_ans = user_inputs.get(item["id"], "")
                    ai_done = False
                    
                    if api_key_input and item["type"] == "완전 서술형":
                        try:
                            with st.spinner(f"문항 {q_num} AI 채점관({selected_model})이 심층 분석 중..."):
                                if is_math:
                                    ai_eval = evaluate_math_with_ai(api_key_input, item["question"], item["answer"], item["rubric"], u_ans, item["points"], selected_model)
                                else:
                                    ai_eval = evaluate_with_ai(api_key_input, item["question"], item["answer"], item["rubric"], u_ans, item["points"], selected_model)
                                    
                                earned = ai_eval["score"]
                                total_earned += earned
                                ai_done = True
                                
                                with st.expander(f"문항 {q_num} 채점 결과 ({earned}/{item['points']}점) - AI 정밀 첨삭", expanded=True):
                                    c1, c2 = st.columns([1, 1])
                                    c1.info(f"**수험생 답안:** {u_ans if u_ans else '(미입력)'}")
                                    c2.success(f"**공식 모범답안:** {item['answer']}")
                                    st.markdown(f"<div class='ai-box'><b>🧑‍🏫 AI 채점관 총평:</b><br>{ai_eval['critique']}</div>", unsafe_allow_html=True)
                        except Exception as e:
                            st.warning(f"AI 채점 중 일시적 오류로 규칙 기반 채점으로 전환: {e}")
                            ai_done = False

                    if not ai_done:
                        eval_res = evaluate_answer_local(u_ans, item["answer"], item["keywords"], item["rubric"])
                        earned = round(eval_res["score_ratio"] * item["points"], 1)
                        total_earned += earned
                        
                        with st.expander(f"문항 {q_num} 채점 결과 ({earned}/{item['points']}점)", expanded=True):
                            c1, c2 = st.columns([1, 1])
                            c1.info(f"**수험생 답안:** {u_ans if u_ans else '(미입력)'}")
                            c2.success(f"**공식 모범답안:** {item['answer']}")
                            for crit, passed in eval_res["criteria_results"]:
                                if passed:
                                    st.markdown(f"• <span class='rubric-pass'>[충족 +배점]</span> {crit}", unsafe_allow_html=True)
                                else:
                                    st.markdown(f"• <span class='rubric-fail'>[미흡 -감점]</span> {crit}", unsafe_allow_html=True)

                st.markdown("---")

            # Final Score Summary
            pct = int((total_earned / max_possible) * 100) if max_possible > 0 else 0
            col_m1, col_m2, col_m3 = st.columns([1, 1, 2])
            col_m1.metric("총 획득 점수", f"{total_earned} / {max_possible} 점")
            col_m2.metric("정답 달성률", f"{pct}%")
            if pct >= 80:
                col_m3.success("🎉 최상위 합격권 점수입니다! 수학적 개념과 원리가 완벽하게 인출되었습니다.")
            elif pct >= 60:
                col_m3.warning("⚠️ 양호합니다. 누락된 세부 루브릭 조건(단위비율, 조작활동, 자릿값 등)을 보완해 보세요.")
            else:
                col_m3.error("🚨 핵심 수학 개념어 암기와 조건부 서술 훈련이 더 필요합니다.")

# =========================================================================
# MENU 2: 14개년 기출 & ABCD 매트릭스
# =========================================================================
elif menu == "📊 14개년 기출 & ABCD 매트릭스":
    subj_name = "수학" if is_math else "음악"
    st.markdown(f"<div class='main-header'>📊 14개년 초등 {subj_name} 기출 빅데이터 & ABCD 중요도 매트릭스</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='sub-header'>2013~2026학년도 14개년 초등 {subj_name} 기출문제 전수 분석 및 지도서 각론 출제 빈도 매핑입니다.</div>", unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("분석 대상 기출", "최근 14개년 (2013-2026)")
    if is_math:
        col2.metric("지도서 각론 출제 비율", "75% (압도적 비중)")
        col3.metric("교육론 및 교육과정 비율", "25%")
        col4.metric("분석된 각론 단원", "1~6학년 전단원 (1682p)")
    else:
        col2.metric("지도서 각론 출제 비율", "80% (압도적)")
        col3.metric("교육과정 성취기준 비율", "20%")
        col4.metric("분석된 각론 제재곡", "69곡 (498p 전수)")

    st.markdown("---")
    tab1, tab2, tab3, tab4 = st.tabs(["🔥 A등급 (초빈출)", "⭐ B등급 (유력 출제)", "📌 C등급 (세부 각론)", "📑 D등급 (교육과정)"])

    if is_math:
        with tab1:
            st.error("### 🔴 A등급: 14개년 중 3회 이상 출제 or 격년 주기 필수 출제")
            st.markdown(r"""
            - **분수의 나눗셈 조작 지도**: 이중수직선 모델에서 단위비율(1에 해당하는 양) 결정 원리, 역수 곱셈 유도($4 \div 2/3 = 4 \times 3 \div 2$)
            - **소수의 나눗셈 자릿값 이동**: 자연수÷자연수에서 몫이 소수인 경우, $3 \div 4 = 0.75$를 $0.01$이 $300$개인 수로 변환 지도
            - **원의 넓이 지도**: 직사각형 등적변형($\text{가로}=\text{원주의 } 1/2$, $\text{세로}=\text{반지름}$, $S=\pi r^2$ 유도)
            - **입체도형 전개도와 겨냥도**: 원기둥 옆면 가로=밑면 원주, 각기둥 구성요소($V=2n, F=n+2, E=3n$)
            - **비와 비율**: 뺄셈 비교(절대적 차이) vs 나눗셈 비교(상대적 비), 기준량과 비교하는 양
            - **4대 교수학습 모형**: 원리 탐구 학습 모형(원리의 조작적 탐구), 개념 형성 학습 모형, 귀납 추론, 문제 해결
            """)

        with tab2:
            st.warning("### 🟡 B등급: 14개년 중 1~2회 출제, 2~3년 주기 순환 출제")
            st.markdown("""
            - **사각형의 분류 및 포함 관계**: 사다리꼴 ⊂ 평행사변형 ⊂ 직사각형/마름모 ⊂ 정사각형(외연과 내포의 관계)
            - **합동과 대칭**: 선대칭도형(대칭축은 대응점 연결선분 수직이등분), 점대칭도형(대칭의 중심은 선분 이등분)
            - **나눗셈의 두 가지 상황**: 포함제(나누는 수가 묶음의 크기) vs 등분제(나누는 수가 묶음의 수)
            - **자료와 가능성**: 꺾은선그래프 물결선(필요 없는 구간 생략, 변화 폭 뚜렷), 평균(고르게 하기/재분배)
            - **수학교육학자 이론**: 브루너 EIS(활동적-영상적-기호적), 디에네스 4대 원리, 반힐레 기하사고 수준, 스켐프의 이해, 폴리아 4단계
            """)

        with tab3:
            st.success("### 🟢 C등급: 미기출 심층 세부 각론 (불의타 대비)")
            st.markdown(r"""
            - **1~2학년군 수와 연산**: 수 모형 조작(일모형 10개 ↔ 십모형 1개), 가르기와 모으기, 10이 되는 더하기
            - **측정 영역의 단위 지도**: 직접 비교 $\to$ 간접 비교 $\to$ 임의 단위 $\to$ 표준 단위 도입 계통
            - **시각과 시간**: 시각(시점) vs 시간(시간의 양/구간), 들이와 무게 단위 관계($1\text{L}=1000\text{mL}, 1\text{kg}=1000\text{g}$)
            - **어림하기**: 올림, 버림, 반올림의 실생활 적용 상황 판단, 규칙 배열과 대응 관계 식 세우기
            """)

        with tab4:
            st.info("### ⚪ D등급: 2022 개정 수학과 교육과정 체계")
            st.markdown("""
            - **5대 교과 역량**: 문제해결, 추론, 의사소통, 연결, 정보처리
            - **내용 체계 4대 영역**: 수와 연산, 변화와 관계, 도형과 측정, 자료와 가능성 (구 '규칙성' $\to$ '변화와 관계' 개편)
            - **공학 도구 활용**: 알지오매스, 계산기 등 디지털 도구를 활용한 수학적 개념 탐구 및 정당화
            - **과정 중심 평가**: 관찰평가, 구술평가, 포트폴리오, 프로젝트 평가 및 학습 피드백
            """)
    else:
        with tab1:
            st.error("### 🔴 A등급: 14개년 중 3회 이상 출제 or 3개년 연속 출제")
            st.markdown("""
            - **메나리토리 및 긴자진 형식**: <쾌지나칭칭나네>, <강강술래> (하행 시 '솔' 경과음, 한배 느린 것 선행)
            - **육자배기토리 및 시김새**: <진도아리랑>, <거문도뱃노래> (미 떠는 소리, 시 꺾는 소리)
            - **경토리 민요 및 장구 타법**: <도라지타령>, <늴리리야> (굿거리 기덕/더러러러, 세마치 덩에 세, 북편 손치기)
            - **단소/소금 운지 및 정간보**: 임, 남, 황, 태, 중 기본 5음, 1공/6공 지공 운지법, 정간 1박 3등분
            - **다장조/바장조 주요 3화음**: I, IV, V 화음 구성음 우리말 음이름, 버금딸림화음 바-라-도
            """)

        with tab2:
            st.warning("### 🟡 B등급: 14개년 중 1~2회 출제, 2~3년 주기 순환 출제")
            st.markdown("""
            - **종묘제례악 및 제례 절차**: <보태평>(문덕, 드오), <정대업>(무덕, 지부학) 시작 및 끝 구호
            - **수제천 및 아악/당악**: 연음형식(피리가 쉬고 대금/해금이 가락을 이어받음), 처용무 반주음악
            - **기악 합주 및 판소리 3대 요소**: 사물놀이(야외 풍물) vs 삼현육각(실내 궁중음악), 아니리/발림/추임새
            - **기악 가창 및 6/8박자 지휘**: 점4분음표 2박 지휘법, 스타카토/페르마타/테누토 주법 기호
            """)

        with tab3:
            st.success("### 🟢 C등급: 미기출 심층 각론 악곡 (불의타 대비)")
            st.markdown("""
            - **지역별 향토 민요**: 제주 <너영나영>, <멸치후리는소리>, 남도 <둥당이타령>, 경기 <풍년가>
            - **세계 민요 및 다문화 악기**: 인도네시아 안클룽(가믈란), 아프리카 젬베, 페루 차랑고, 스위스 요들
            - **서양 음악사 시대별 특징**: 바로크(바흐, 헨델, 쳄발로), 고전(하이든, 모차르트, 소나타형식), 낭만(슈베르트 예술가곡)
            """)

        with tab4:
            st.info("### ⚪ D등급: 2022 개정 음악과 교육과정 체계")
            st.markdown("""
            - **핵심 아이디어**: 음악적 소통을 통해 자아를 실현하고 공동체 문화 발전에 기여함
            - **3대 영역**: 감상, 표현, 생활화 (구 교육과정 '이해' 영역이 각 영역으로 통합 흡수)
            - **신설 성취기준 키워드**: 디지털 기술을 활용한 음악 창작, 음악과 신체 표현의 융합, 생애 음악 활동
            """)

# =========================================================================
# MENU 3: 각론 및 기본이론 지도 사전
# =========================================================================
elif menu == "📖 각론 및 기본이론 지도 사전":
    subj_name = "초등 수학 (1682p)" if is_math else "초등 음악 (498p)"
    st.markdown(f"<div class='main-header'>📖 {subj_name} 각론 완성 디지털 지도 사전</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='sub-header'>교재에 수록된 핵심 단원, 조작 활동, 중요도 등급 및 지도서 유의점을 검색하고 열람하세요.</div>", unsafe_allow_html=True)

    if is_math:
        search_kw = st.text_input("🔍 수학 개념 또는 단원명 검색 (예: 분수의 나눗셈, 원의 넓이, 이중수직선, 사각형):")
        matrix_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "math_gaknon_matrix.json")
        if os.path.exists(matrix_file):
            with open(matrix_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            raw_items = []
            for tier_name, items in data.get("abcd_gaknon_matrix", {}).items():
                for item in items:
                    tier_str = "A" if "A_" in tier_name else ("B" if "B_" in tier_name else ("C" if "C_" in tier_name else "D"))
                    item["tier"] = tier_str
                    raw_items.append(item)
                    
            if search_kw:
                filtered = [it for it in raw_items if search_kw.lower() in it.get("topic", "").lower() or search_kw.lower() in it.get("core_concept", "").lower() or search_kw.lower() in it.get("key_points", "").lower()]
            else:
                filtered = raw_items

            st.caption(f"총 {len(filtered)}개의 핵심 지도서 각론 항목이 조회되었습니다.")

            for it in filtered:
                tier_badge = "badge-a" if it["tier"] == "A" else ("badge-b" if it["tier"] == "B" else ("badge-c" if it["tier"] == "C" else "badge-d"))
                with st.container():
                    st.markdown(f"#### 📐 {it['topic']} <span class='{tier_badge}'>{it['tier']}등급</span> · {it.get('domain', '수학')}", unsafe_allow_html=True)
                    st.markdown(f"• **지도서 수록 페이지:** {it.get('page_range', '각론완성')}")
                    st.markdown(f"• **핵심 조작 원리:** {it.get('core_concept', '')}")
                    st.markdown(f"• **상세 분석 및 지도 유의점:** {it.get('key_points', '')}")
                    st.markdown("---")
    else:
        search_kw = st.text_input("🔍 제재곡 이름 또는 핵심 개념 검색 (예: 강강술래, 메나리토리, 화음):")
        matrix_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "music_gaknon_matrix.json")
        if os.path.exists(matrix_file):
            with open(matrix_file, "r", encoding="utf-8") as f:
                matrix_data = json.load(f)

            songs = matrix_data.get("all_indexed_songs", [])
            if search_kw:
                filtered_songs = [s for s in songs if search_kw.lower() in s["song"].lower() or search_kw.lower() in s["key_concepts"].lower()]
            else:
                filtered_songs = songs

            st.caption(f"총 {len(filtered_songs)}개의 제재곡이 조회되었습니다.")

            for s in filtered_songs:
                tier_badge = "badge-a" if s["tier"] == "A" else ("badge-b" if s["tier"] == "B" else "badge-c")
                with st.container():
                    st.markdown(f"#### 🎵 {s['song']} <span class='{tier_badge}'>{s['tier']}등급</span>", unsafe_allow_html=True)
                    st.markdown(f"• **교재 수록 페이지:** {s['page_range']}")
                    st.markdown(f"• **출제 핵심 개념:** {s['key_concepts']}")
                    st.markdown(f"• **상세 분석:** {s['notes']}")
                    st.markdown("---")
