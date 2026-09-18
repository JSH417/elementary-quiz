"""
curriculum_study_engine.py
2022 개정 초·중등학교 교육과정 총론 및 창의적 체험활동 (빈칸 문제 26페이지)
- 마스킹 모드 (인터랙티브 클릭 가리기 / 확인)
- 빈칸 만들기 & 풀기 모드 (실전 자가 테스트 및 유연 자동 채점)
- 정답 보기 모드 (원문 정독 및 핵심어 하이라이트)
- 전단원 검색 및 랜덤 모의고사
"""

import streamlit as st
import json
import os
import re
import random

DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "curriculum_2022_chongron.json")

@st.cache_data
def load_curriculum_data():
    """Load the 2022 revised curriculum chongron JSON dataset."""
    if not os.path.exists(DATA_PATH):
        return []
    try:
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        st.error(f"데이터 로드 실패: {e}")
        return []

def normalize_text(text: str) -> str:
    """Normalize text for flexible grading (remove whitespace, dots, middots, punctuation, etc.)."""
    if not text:
        return ""
    # Retain Korean syllables, alphanumeric characters and %
    cleaned = re.sub(r"[^가-힣0-9a-zA-Z%]", "", text).lower()
    return cleaned

def check_blank_answer(user_input: str, correct_answer: str) -> bool:
    """
    Check if the user answer matches the official answer with flexible allowances.
    Supports exact match, normalized match, and common variations.
    """
    if not user_input or not user_input.strip():
        return False
    
    u_norm = normalize_text(user_input)
    c_norm = normalize_text(correct_answer)
    
    if u_norm == c_norm:
        return True
    
    # Handle slash separated answers (e.g. "자치·적응 / 동아리")
    if "/" in correct_answer:
        parts = [normalize_text(p) for p in correct_answer.split("/")]
        if u_norm in parts:
            return True
            
    # Handle comma separated lists
    if "," in correct_answer:
        parts = [normalize_text(p) for p in correct_answer.split(",")]
        if u_norm in parts:
            return True
            
    # Substring inclusion for long descriptive terms if > 85% match
    if len(c_norm) >= 6 and (u_norm in c_norm or c_norm in u_norm):
        overlap = min(len(u_norm), len(c_norm)) / max(len(u_norm), len(c_norm))
        if overlap >= 0.85:
            return True

    return False

def render_masking_text(text: str, blanks: dict, show_all: bool = False, item_id: str = "") -> str:
    """
    Render passage text with interactive masking HTML.
    When show_all is False, blanks are rendered as clickable <details><summary> pills.
    When show_all is True, blanks are rendered with high-contrast highlighted text.
    """
    formatted = text
    for num, answer in blanks.items():
        pattern = re.compile(rf"\(\s*{re.escape(num)}\s*\)")
        
        if show_all:
            replacement = (
                f'<span style="background-color:#DCFCE7; color:#14532D; padding:2px 8px; '
                f'border-radius:6px; font-weight:800; border:1.5px solid #86EFAC; display:inline-block; margin:0 2px;">'
                f'{num} {answer}</span>'
            )
        else:
            replacement = (
                f'<details style="display:inline-block; vertical-align:middle; margin:2px 3px;">'
                f'<summary style="cursor:pointer; display:inline-block; background-color:#EFF6FF; color:#1D4ED8; '
                f'border:1.5px solid #93C5FD; border-radius:14px; padding:2px 10px; font-size:0.85rem; '
                f'font-weight:700; user-select:none; outline:none;" title="클릭하여 정답 확인/숨기기">'
                f'[{num} ❓ 정답확인]</summary>'
                f'<span style="background-color:#FEF3C7; color:#92400E; border:1.5px solid #FCD34D; '
                f'border-radius:6px; padding:2px 8px; font-weight:800; font-size:0.9rem; margin-left:4px;">'
                f'{num} {answer}</span>'
                f'</details>'
            )
        
        if pattern.search(formatted):
            formatted = pattern.sub(replacement, formatted)
        else:
            formatted = formatted.replace(num, replacement)
            
    return formatted

def render_full_answer_text(text: str, blanks: dict) -> str:
    """
    Render passage with all blanks filled in and clearly highlighted for read-through memorization.
    """
    formatted = text
    for num, answer in blanks.items():
        pattern = re.compile(rf"\(\s*{re.escape(num)}\s*\)")
        replacement = (
            f'<mark style="background-color:#FEF08A; color:#854D0E; padding:2px 7px; '
            f'border-radius:4px; font-weight:700; border:1px solid #FDE047;">'
            f'{num} {answer}</mark>'
        )
        if pattern.search(formatted):
            formatted = pattern.sub(replacement, formatted)
        else:
            formatted = formatted.replace(num, replacement)
    return formatted

def render_chongron_master_ui():
    """Main entry point for 2022 Chongron & Changche Master UI."""
    data = load_curriculum_data()
    if not data:
        st.error("2022 개정 총론 및 창체 데이터셋(`curriculum_2022_chongron.json`)을 찾을 수 없습니다.")
        return

    # Total stats calculation
    total_sections = len(data)
    total_items = sum(len(sec.get("items", [])) for sec in data)
    total_blanks = sum(len(it.get("blanks", {})) for sec in data for it in sec.get("items", []))

    st.markdown("""
    <div style="background: linear-gradient(135deg, #1E3A8A 0%, #3B82F6 100%); padding: 22px 26px; border-radius: 12px; color: white; margin-bottom: 20px;">
        <div style="font-size: 1.85rem; font-weight: 800; margin-bottom: 6px;">
            📑 2022 개정 교육과정 총론 & 창의적 체험활동 빈칸 마스터
        </div>
        <div style="font-size: 0.98rem; opacity: 0.92; line-height: 1.5;">
            26페이지 전문(총론 1~17p, 창체 18~26p) 완벽 수록 • <b>총 363개 핵심 빈칸</b> 수록<br>
            원하는 모드(마스킹 모드 / 빈칸 문제 풀기 / 정답 보기)를 선택하여 실전 임용 1차 시험을 완벽 대비하세요!
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Top Metric Bar
    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    with col_m1:
        st.metric("총 페이지 수", "26 페이지 (전문)", help="총론 1~17p, 창체 18~26p")
    with col_m2:
        st.metric("수록 단원 및 절", f"{total_sections} 개 섹션")
    with col_m3:
        st.metric("총 세부 문항", f"{total_items} 개 조항")
    with col_m4:
        st.metric("총 빈칸 수", f"{total_blanks} 개 핵심어")

    # Main Navigation Mode Tabs
    mode_tab1, mode_tab2, mode_tab3, mode_tab4, mode_tab5 = st.tabs([
        "🔒 1. 마스킹 모드 (클릭 가리기/확인)",
        "📝 2. 빈칸 문제 풀기 (실전 채점)",
        "📖 3. 정답 보기 (원문 정독 & 암기)",
        "🎲 4. 실전 랜덤 모의고사 (10~30제)",
        "🔍 5. 전단원 키워드 통합 검색"
    ])

    # =========================================================================
    # TAB 1: 마스킹 모드 (클릭 가리기/확인)
    # =========================================================================
    with mode_tab1:
        st.markdown("### 🔒 인터랙티브 마스킹 모드")
        st.caption("빈칸 번호의 `[❓ 정답확인]` 버튼을 클릭하면 즉시 해당 단어가 펼쳐집니다. 스스로 떠올려본 후 확인해보세요!")
        
        f_col1, f_col2, f_col3 = st.columns([1.2, 2.2, 1.2])
        with f_col1:
            subj_filter = st.selectbox(
                "영역 선택",
                ["전체 (총론 + 창체)", "📘 교육과정 총론 (1~17p)", "📙 창의적 체험활동 (18~26p)"],
                key="mask_subj_filter"
            )
        
        filtered_sections = []
        for sec in data:
            if "총론" in subj_filter and sec["subject"] != "총론":
                continue
            if "창의적" in subj_filter and sec["subject"] != "창의적 체험활동":
                continue
            filtered_sections.append(sec)

        sec_titles = [f"P.{s['page']} [{s['subject']}] {s['title']}" for s in filtered_sections]
        with f_col2:
            selected_title = st.selectbox("학습할 페이지 / 단원 선택", sec_titles, key="mask_sec_select")
            
        with f_col3:
            st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
            reveal_all = st.checkbox("👁️ 전체 정답 펼치기", value=False, key="mask_reveal_all")

        selected_sec = next((s for s in filtered_sections if f"P.{s['page']} [{s['subject']}] {s['title']}" == selected_title), filtered_sections[0])

        st.markdown("---")
        st.markdown(f"#### 📌 [P.{selected_sec['page']}] {selected_sec['chapter']} > {selected_sec['title']}")

        for idx, item in enumerate(selected_sec.get("items", [])):
            sub_t = item.get("sub_title", f"문항 {idx+1}")
            blanks = item.get("blanks", {})
            raw_text = item.get("text", "")
            
            with st.container():
                st.markdown(f"**🔹 {sub_t}** ({len(blanks)}개 빈칸)")
                
                masked_html = render_masking_text(raw_text, blanks, show_all=reveal_all, item_id=item.get("id", f"item_{idx}"))
                st.markdown(f"""
                <div style="background-color: #F8FAFC; border-left: 4px solid #3B82F6; padding: 14px 18px; border-radius: 0 8px 8px 0; margin-bottom: 12px; font-size: 0.98rem; line-height: 1.9;">
                    {masked_html}
                </div>
                """, unsafe_allow_html=True)
                
                with st.expander(f"📋 '{sub_t}' 정답 일람표 보기"):
                    ans_cols = st.columns(min(len(blanks), 4) if blanks else 1)
                    for b_idx, (b_num, b_ans) in enumerate(blanks.items()):
                        with ans_cols[b_idx % len(ans_cols)]:
                            st.info(f"**{b_num}** : {b_ans}")

    # =========================================================================
    # TAB 2: 빈칸 문제 풀기 (실전 채점 모드)
    # =========================================================================
    with mode_tab2:
        st.markdown("### 📝 빈칸 문제 풀기 & 자동 채점 모드")
        st.caption("지문의 빈칸에 들어갈 올바른 교육과정 용어를 직접 입력하고, 자동 채점 버튼을 눌러 점수와 오답을 확인하세요.")

        q_col1, q_col2 = st.columns([1.2, 2.8])
        with q_col1:
            q_subj_filter = st.selectbox(
                "영역 선택",
                ["전체 (총론 + 창체)", "📘 교육과정 총론 (1~17p)", "📙 창의적 체험활동 (18~26p)"],
                key="quiz_subj_filter"
            )
        
        q_filtered_sections = []
        for sec in data:
            if "총론" in q_subj_filter and sec["subject"] != "총론":
                continue
            if "창의적" in q_subj_filter and sec["subject"] != "창의적 체험활동":
                continue
            q_filtered_sections.append(sec)

        q_sec_titles = [f"P.{s['page']} [{s['subject']}] {s['title']}" for s in q_filtered_sections]
        with q_col2:
            q_selected_title = st.selectbox("문제 풀 단원 선택", q_sec_titles, key="quiz_sec_select")

        q_selected_sec = next((s for s in q_filtered_sections if f"P.{s['page']} [{s['subject']}] {s['title']}" == q_selected_title), q_filtered_sections[0])
        
        st.markdown("---")
        st.markdown(f"#### ✍️ [P.{q_selected_sec['page']}] {q_selected_sec['chapter']} > {q_selected_sec['title']}")

        form_key = f"form_quiz_{q_selected_sec['page']}_{hash(q_selected_sec['title'])}"
        with st.form(key=form_key):
            user_responses = {}
            total_sec_blanks = 0

            for idx, item in enumerate(q_selected_sec.get("items", [])):
                sub_t = item.get("sub_title", f"문항 {idx+1}")
                blanks = item.get("blanks", {})
                raw_text = item.get("text", "")
                item_id = item.get("id", f"it_{idx}")
                
                st.markdown(f"##### 📌 {sub_t}")
                
                display_text = raw_text
                for b_num in blanks.keys():
                    pattern = re.compile(rf"\(\s*{re.escape(b_num)}\s*\)")
                    replacement = f"<b style='color:#1E40AF; background:#DBEAFE; padding:1px 6px; border-radius:4px;'>({b_num} _______)</b>"
                    display_text = pattern.sub(replacement, display_text)
                    
                st.markdown(f"""
                <div style="background-color: #F1F5F9; border-left: 4px solid #0284C7; padding: 12px 16px; border-radius: 0 8px 8px 0; margin-bottom: 12px; font-size: 0.95rem; line-height: 1.8;">
                    {display_text}
                </div>
                """, unsafe_allow_html=True)
                
                cols = st.columns(min(len(blanks), 4) if blanks else 1)
                for b_idx, (b_num, b_ans) in enumerate(blanks.items()):
                    total_sec_blanks += 1
                    input_key = f"ans_{item_id}_{b_num}"
                    with cols[b_idx % len(cols)]:
                        user_responses[input_key] = {
                            "user_val": st.text_input(f"{b_num} 빈칸 답안:", key=input_key, placeholder="정답 입력"),
                            "correct_val": b_ans,
                            "b_num": b_num,
                            "sub_title": sub_t
                        }
                st.markdown("<hr style='margin: 10px 0; border: none; border-top: 1px dashed #CBD5E1;'>", unsafe_allow_html=True)

            btn_submit = st.form_submit_button("📝 답안 제출 및 자동 채점하기", type="primary", use_container_width=True)

        if btn_submit:
            correct_count = 0
            results = []
            for k, info in user_responses.items():
                u_val = info["user_val"]
                c_val = info["correct_val"]
                is_correct = check_blank_answer(u_val, c_val)
                if is_correct:
                    correct_count += 1
                results.append({
                    "b_num": info["b_num"],
                    "sub_title": info["sub_title"],
                    "user_val": u_val if u_val.strip() else "(미입력)",
                    "correct_val": c_val,
                    "is_correct": is_correct
                })

            score_pct = (correct_count / total_sec_blanks * 100) if total_sec_blanks > 0 else 0
            st.session_state[f"has_graded_cse_{form_key}"] = True
            st.session_state[f"score_cse_{form_key}"] = (correct_count, total_sec_blanks, score_pct)
            st.session_state[f"results_cse_{form_key}"] = results

        if st.session_state.get(f"has_graded_cse_{form_key}", False):
            correct_count, total_sec_blanks, score_pct = st.session_state[f"score_cse_{form_key}"]
            results = st.session_state[f"results_cse_{form_key}"]
            st.markdown("---")
            if score_pct == 100:
                st.balloons()
                st.success(f"🎉 **완벽합니다! 만점입니다!** ({correct_count} / {total_sec_blanks}개 정답, 정답률 100%)")
            elif score_pct >= 70:
                st.success(f"👏 **우수한 성적입니다!** ({correct_count} / {total_sec_blanks}개 정답, 정답률 {score_pct:.1f}%)")
            else:
                st.warning(f"✍️ **채점 완료:** {correct_count} / {total_sec_blanks}개 정답 (정답률 {score_pct:.1f}%)")

            c_cse_view, c_cse_reset = st.columns([2, 1])
            is_viewing_cse = st.session_state.get(f"show_detail_cse_{form_key}", False)
            with c_cse_view:
                lbl = "🙈 채점 결과 가리기" if is_viewing_cse else "🔍 세부 채점 결과 및 정답 확인하기 (버튼 클릭)"
                if st.button(lbl, key=f"btn_cse_toggle_{form_key}", use_container_width=True, type="secondary"):
                    st.session_state[f"show_detail_cse_{form_key}"] = not is_viewing_cse
                    st.rerun()
            with c_cse_reset:
                if st.button("🔄 채점 닫기 / 다시 풀기", key=f"btn_cse_reset_{form_key}", use_container_width=True):
                    st.session_state[f"has_graded_cse_{form_key}"] = False
                    st.session_state[f"show_detail_cse_{form_key}"] = False
                    st.rerun()

            if st.session_state.get(f"show_detail_cse_{form_key}", False):
                st.markdown("#### 📊 채점 결과 세부 분석 및 정답 대조표")
                for r in results:
                    status_icon = "✅ 정답" if r["is_correct"] else "❌ 오답"
                    bg_color = "#F0FDF4" if r["is_correct"] else "#FEF2F2"
                    border_color = "#86EFAC" if r["is_correct"] else "#FCA5A5"
                    st.markdown(f"""
                    <div style="background-color: {bg_color}; border: 1px solid {border_color}; border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
                        <b>{r['b_num']}</b> [{r['sub_title']}] : {status_icon}<br>
                        <span style="font-size: 0.9rem;">
                        • 내 입력: <code>{r['user_val']}</code> &nbsp;|&nbsp; 
                        • 정답: <strong style="color: #15803D;">{r['correct_val']}</strong>
                        </span>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.caption("🔒 바로 아래 정답이 노출되지 않도록 가려두었습니다. 확인하시려면 위 **[🔍 세부 채점 결과 및 정답 확인하기]** 버튼을 눌러주세요.")


    # =========================================================================
    # TAB 3: 정답 보기 (원문 정독 & 암기 모드)
    # =========================================================================
    with mode_tab3:
        st.markdown("### 📖 정답 보기 & 원문 정독 암기 모드")
        st.caption("모든 빈칸이 노란색 형광펜으로 채워진 완성된 원문을 정독하며 전체 문맥과 핵심 키워드를 한눈에 암기하세요.")

        ans_f1, ans_f2 = st.columns([1.2, 2.8])
        with ans_f1:
            ans_subj_filter = st.selectbox(
                "영역 선택",
                ["전체 (총론 + 창체)", "📘 교육과정 총론 (1~17p)", "📙 창의적 체험활동 (18~26p)"],
                key="ans_subj_filter"
            )
        
        ans_filtered_sections = []
        for sec in data:
            if "총론" in ans_subj_filter and sec["subject"] != "총론":
                continue
            if "창의적" in ans_subj_filter and sec["subject"] != "창의적 체험활동":
                continue
            ans_filtered_sections.append(sec)

        ans_sec_titles = [f"P.{s['page']} [{s['subject']}] {s['title']}" for s in ans_filtered_sections]
        with ans_f2:
            ans_selected_title = st.selectbox("정독할 단원 선택", ans_sec_titles, key="ans_sec_select")

        ans_selected_sec = next((s for s in ans_filtered_sections if f"P.{s['page']} [{s['subject']}] {s['title']}" == ans_selected_title), ans_filtered_sections[0])

        st.markdown("---")
        st.markdown(f"#### 📜 [P.{ans_selected_sec['page']}] {ans_selected_sec['chapter']} > {ans_selected_sec['title']}")

        for idx, item in enumerate(ans_selected_sec.get("items", [])):
            sub_t = item.get("sub_title", f"문항 {idx+1}")
            blanks = item.get("blanks", {})
            raw_text = item.get("text", "")
            
            st.markdown(f"##### 📌 {sub_t}")
            full_ans_html = render_full_answer_text(raw_text, blanks)
            
            st.markdown(f"""
            <div style="background-color: #FEFCE8; border-left: 4px solid #EAB308; padding: 14px 18px; border-radius: 0 8px 8px 0; margin-bottom: 12px; font-size: 0.98rem; line-height: 2.0;">
                {full_ans_html}
            </div>
            """, unsafe_allow_html=True)

            with st.expander(f"📋 {sub_t} 정답 키워드 요약 리스트"):
                st.table([{"빈칸 번호": k, "핵심 정답 용어": v} for k, v in blanks.items()])

    # =========================================================================
    # TAB 4: 실전 랜덤 모의고사 (10~30제)
    # =========================================================================
    with mode_tab4:
        st.markdown("### 🎲 전범위 실전 랜덤 빈칸 모의고사")
        st.caption("총론 1~17p 및 창체 18~26p의 363개 빈칸 중 무작위로 추출하여 실전처럼 테스트합니다.")

        m_col1, m_col2, m_col3 = st.columns([1.5, 1.5, 2])
        with m_col1:
            mock_scope = st.selectbox(
                "모의고사 출제 범위",
                ["전체 (총론 + 창체 363제)", "총론 집중 (1~17p)", "창체 집중 (18~26p)"],
                key="mock_scope"
            )
        with m_col2:
            mock_count = st.selectbox("출제 문항 수", [5, 10, 15, 20, 30], index=1, key="mock_count")
        with m_col3:
            st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
            new_mock_btn = st.button("🎲 새로운 모의고사 생성", type="primary", use_container_width=True)

        all_pool = []
        for sec in data:
            if "총론 집중" in mock_scope and sec["subject"] != "총론":
                continue
            if "창체 집중" in mock_scope and sec["subject"] != "창의적 체험활동":
                continue
            for it in sec.get("items", []):
                for b_num, b_ans in it.get("blanks", {}).items():
                    all_pool.append({
                        "page": sec["page"],
                        "subject": sec["subject"],
                        "chapter": sec["chapter"],
                        "section_title": sec["title"],
                        "sub_title": it.get("sub_title", ""),
                        "text": it.get("text", ""),
                        "b_num": b_num,
                        "b_ans": b_ans,
                        "item_id": it.get("id", "")
                    })

        mock_session_key = "current_mock_questions"
        if new_mock_btn or mock_session_key not in st.session_state:
            sample_size = min(mock_count, len(all_pool))
            st.session_state[mock_session_key] = random.sample(all_pool, sample_size)
            st.session_state["mock_submitted"] = False

        mock_questions = st.session_state[mock_session_key]

        st.markdown(f"#### 🎯 무작위 추출 실전 모의고사 ({len(mock_questions)}문항)")
        
        with st.form(key="mock_quiz_form"):
            mock_user_answers = {}
            for q_idx, mq in enumerate(mock_questions):
                st.markdown(f"**[{q_idx+1}번] P.{mq['page']} [{mq['subject']}] {mq['section_title']} - {mq['sub_title']}**")
                
                q_text = mq["text"]
                pattern = re.compile(rf"\(\s*{re.escape(mq['b_num'])}\s*\)")
                q_text = pattern.sub(f"<b style='color:#DC2626; background:#FEE2E2; padding:2px 8px; border-radius:4px; font-size:1.05rem;'>▶ [{mq['b_num']} 빈칸] ◀</b>", q_text)
                
                st.markdown(f"""
                <div style="background-color: #F8FAFC; border: 1px solid #E2E8F0; padding: 10px 14px; border-radius: 6px; margin-bottom: 8px; font-size: 0.93rem; line-height: 1.7;">
                    {q_text}
                </div>
                """, unsafe_allow_html=True)
                
                col_in, col_space = st.columns([2, 1])
                with col_in:
                    mock_user_answers[f"mock_{q_idx}"] = st.text_input(
                        f"[{q_idx+1}번] 빈칸 {mq['b_num']}의 정답:",
                        key=f"mock_in_{q_idx}",
                        placeholder="정답 입력"
                    )
                st.markdown("<hr style='margin: 8px 0; border: none; border-top: 1px dashed #E2E8F0;'>", unsafe_allow_html=True)

            mock_submit = st.form_submit_button("🏁 모의고사 제출 및 채점하기", type="primary", use_container_width=True)

        if mock_submit:
            st.session_state["mock_submitted"] = True
            m_correct = 0
            m_results = []
            
            for q_idx, mq in enumerate(mock_questions):
                u_ans = mock_user_answers.get(f"mock_{q_idx}", "")
                c_ans = mq["b_ans"]
                is_c = check_blank_answer(u_ans, c_ans)
                if is_c:
                    m_correct += 1
                m_results.append({
                    "q_idx": q_idx + 1,
                    "target": f"{mq['sub_title']} ({mq['b_num']})",
                    "page": mq["page"],
                    "user_ans": u_ans if u_ans.strip() else "(미입력)",
                    "c_ans": c_ans,
                    "is_c": is_c
                })

            m_score = (m_correct / len(mock_questions) * 100) if mock_questions else 0
            st.markdown("---")
            if m_score >= 80:
                st.balloons()
                st.success(f"🏆 **대단합니다! {len(mock_questions)}문항 중 {m_correct}문항 정답!** (성적: {m_score:.1f}점)")
            else:
                st.info(f"📊 **채점 결과:** {len(mock_questions)}문항 중 **{m_correct}문항 정답** (정답률: {m_score:.1f}%)")

            for res in m_results:
                badge = "✅ 정답" if res["is_c"] else "❌ 오답"
                card_bg = "#F0FDF4" if res["is_c"] else "#FEF2F2"
                card_border = "#86EFAC" if res["is_c"] else "#FCA5A5"
                st.markdown(f"""
                <div style="background-color: {card_bg}; border: 1px solid {card_border}; border-radius: 6px; padding: 8px 12px; margin-bottom: 6px;">
                    <b>{res['q_idx']}번 [{badge}]</b> P.{res['page']} {res['target']}<br>
                    • 입력한 답: <code>{res['user_ans']}</code> &nbsp;|&nbsp;
                    • 실제 정답: <strong style="color: #15803D;">{res['c_ans']}</strong>
                </div>
                """, unsafe_allow_html=True)

    # =========================================================================
    # TAB 5: 전단원 키워드 통합 검색
    # =========================================================================
    with mode_tab5:
        st.markdown("### 🔍 2022 개정 총론 & 창체 전단원 키워드 검색기")
        st.caption("궁금한 교육과정 핵심 용어(예: 학교자율시간, 진로연계교육, 동아리활동, 기초학력, 20% 등)를 입력하면 26페이지 전편에서 실시간 검색합니다.")

        search_keyword = st.text_input("검색할 단어 입력:", placeholder="예: 학교자율시간, 진로연계교육, 입학초기적응, 봉사활동 등", key="curriculum_search_kw")

        if search_keyword and search_keyword.strip():
            kw = search_keyword.strip()
            found_items = []

            for sec in data:
                for it in sec.get("items", []):
                    in_text = kw in it.get("text", "")
                    in_title = kw in it.get("sub_title", "")
                    in_blanks = any(kw in v for v in it.get("blanks", {}).values())
                    
                    if in_text or in_title or in_blanks:
                        found_items.append({
                            "page": sec["page"],
                            "subject": sec["subject"],
                            "chapter": sec["chapter"],
                            "section_title": sec["title"],
                            "sub_title": it.get("sub_title", ""),
                            "text": it.get("text", ""),
                            "blanks": it.get("blanks", {})
                        })

            st.markdown(f"**총 `{len(found_items)}건`의 관련 교육과정 조항이 검색되었습니다.**")
            
            for f_idx, fi in enumerate(found_items):
                st.markdown(f"##### 🔎 [{f_idx+1}] [P.{fi['page']}] {fi['chapter']} > {fi['sub_title']}")
                
                h_text = fi["text"]
                for b_num, b_ans in fi["blanks"].items():
                    pattern = re.compile(rf"\(\s*{re.escape(b_num)}\s*\)")
                    h_text = pattern.sub(f"<span style='background:#E0E7FF; color:#3730A3; padding:1px 5px; border-radius:3px;'>({b_num} {b_ans})</span>", h_text)
                
                h_kw_pattern = re.compile(re.escape(kw), re.IGNORECASE)
                h_text = h_kw_pattern.sub(f"<mark style='background:#FDE047; color:#000; font-weight:bold; padding:2px 4px;'>{kw}</mark>", h_text)

                st.markdown(f"""
                <div style="background-color: #F8FAFC; border-left: 4px solid #6366F1; padding: 12px 16px; border-radius: 0 8px 8px 0; margin-bottom: 12px; font-size: 0.93rem; line-height: 1.8;">
                    {h_text}
                </div>
                """, unsafe_allow_html=True)
                
                tags = " ".join([f"`{k}: {v}`" for k, v in fi["blanks"].items()])
                st.caption(f"📌 관련 빈칸 정답: {tags}")
                st.markdown("<hr style='margin: 8px 0; border: none; border-top: 1px solid #E2E8F0;'>", unsafe_allow_html=True)
        else:
            st.info("💡 상단 검색창에 검색하고 싶은 교육과정 단어를 입력해보세요. (예: `기초학력`, `시·도 교육청`, `20%`, `디지털 소양`)")
