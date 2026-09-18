"""
content_framework_engine.py
2022 개정 초등학교 교육과정 내용 체계표 단계별 마스터 연습장 [상·중·하 종합본]
수록 과목 (총 7개 핵심 과목, 35개 영역, 629개 조항):
- 국어 · 도덕 · 실과 · 음악 · 미술 · 체육 · 통합교과 (바른 생활, 슬기로운 생활, 즐거운 생활)
- 상 · 중 · 하 3단계 난이도 지원
- 마스킹 모드 (클릭 가리기 / 확인)
- 빈칸 문제 풀기 & 자동 채점 모드
- 정답 보기 모드 (공식 원문 정답 대조표)
- 전과목 랜덤 모의고사 & 키워드 검색
"""

import streamlit as st
import json
import os
import re
import random
import difflib

DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "curriculum_2022_content_framework.json")

@st.cache_data
def load_content_framework_data():
    """Load the 2022 content framework JSON dataset."""
    if not os.path.exists(DATA_PATH):
        return []
    try:
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        st.error(f"내용체계표 데이터 로드 실패: {e}")
        return []

def normalize_text(text: str) -> str:
    """Normalize text for flexible evaluation."""
    if not text:
        return ""
    # Retain Korean syllables, alphanumeric characters
    return re.sub(r"[^가-힣0-9a-zA-Z]", "", text).lower()

def check_answer(user_input: str, correct_answer: str, is_sang: bool = False) -> bool:
    """
    Check if user answer matches official answer.
    Supports flexible normalization and fuzzy similarity for long sentences.
    """
    if not user_input or not user_input.strip():
        return False
        
    u_norm = normalize_text(user_input)
    c_norm = normalize_text(correct_answer)
    
    if u_norm == c_norm:
        return True
        
    # Handle slash separated options
    if "/" in correct_answer:
        parts = [normalize_text(p) for p in correct_answer.split("/")]
        if u_norm in parts:
            return True
            
    # Substring inclusion
    if len(c_norm) >= 5 and (u_norm in c_norm or c_norm in u_norm):
        ratio = min(len(u_norm), len(c_norm)) / max(len(u_norm), len(c_norm))
        if ratio >= 0.8:
            return True
            
    # For Sang difficulty (full sentence recall)
    if is_sang:
        sim = difflib.SequenceMatcher(None, u_norm, c_norm).ratio()
        if sim >= 0.75:
            return True
            
    return False

def render_masked_text(text: str, blanks_dict: dict, show_all: bool = False) -> str:
    """
    Replace blanks with clickable <details><summary> or highlighted answers.
    """
    formatted = text
    # In text, blanks are represented as ( ______ ) or similar
    # We replace each occurrence sequentially with the corresponding blank answer
    blank_values = list(blanks_dict.values())
    
    def replacer(match):
        nonlocal blank_values
        if not blank_values:
            ans = "정답"
        else:
            ans = blank_values.pop(0)
            
        if show_all:
            return (
                f'<span style="background-color:#DCFCE7; color:#14532D; padding:2px 8px; '
                f'border-radius:6px; font-weight:800; border:1.5px solid #86EFAC; display:inline-block; margin:0 2px;">'
                f'{ans}</span>'
            )
        else:
            return (
                f'<details style="display:inline-block; vertical-align:middle; margin:2px 3px;">'
                f'<summary style="cursor:pointer; display:inline-block; background-color:#EFF6FF; color:#1D4ED8; '
                f'border:1.5px solid #93C5FD; border-radius:14px; padding:2px 10px; font-size:0.85rem; '
                f'font-weight:700; user-select:none; outline:none;" title="클릭하여 정답 확인/숨기기">'
                f'[❓ 정답확인]</summary>'
                f'<span style="background-color:#FEF3C7; color:#92400E; border:1.5px solid #FCD34D; '
                f'border-radius:6px; padding:2px 8px; font-weight:800; font-size:0.9rem; margin-left:4px;">'
                f'{ans}</span>'
                f'</details>'
            )

    formatted = re.sub(r'\(\s*_+?\s*\)', replacer, formatted)
    return formatted

def render_highlighted_full_text(full_text: str, blanks_list: list) -> str:
    """Highlight blanks inside the full text."""
    highlighted = full_text
    for b in sorted(blanks_list, key=len, reverse=True):
        if b and b in highlighted:
            replacement = (
                f'<mark style="background-color:#FEF08A; color:#854D0E; padding:2px 6px; '
                f'border-radius:4px; font-weight:700; border:1px solid #FDE047;">'
                f'{b}</mark>'
            )
            highlighted = highlighted.replace(b, replacement, 1)
    return highlighted

def render_content_framework_ui():
    """Main UI entry point for 2022 Content Framework Master."""
    data = load_content_framework_data()
    if not data:
        st.error("내용체계표 데이터셋(`curriculum_2022_content_framework.json`)을 찾을 수 없습니다.")
        return

    # Total counts
    all_subjects = sorted(list(set(d["subject"] for d in data)))
    total_domains = len(data)
    total_items = sum(len(d.get("items", [])) for d in data)

    st.markdown("""
    <div style="background: linear-gradient(135deg, #065F46 0%, #10B981 100%); padding: 22px 26px; border-radius: 12px; color: white; margin-bottom: 20px;">
        <div style="font-size: 1.85rem; font-weight: 800; margin-bottom: 6px;">
            📋 2022 개정 초등 내용 체계표 단계별 마스터 [상·중·하 종합본]
        </div>
        <div style="font-size: 0.98rem; opacity: 0.92; line-height: 1.5;">
            <b>7개 전과목(국·도·실·음·미·체·통) · 35개 영역 · 629개 전체 조항 수록</b><br>
            초기 1개 핵심어 빈칸(하) ➡️ 실전 복합 빈칸(중) ➡️ 100% 백지 통인출(상) 3단계 커리큘럼 완성!
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Top Metric Bar
    cm1, cm2, cm3, cm4 = st.columns(4)
    with cm1:
        st.metric("수록 교과목", f"{len(all_subjects)}개 과목", help="국어, 도덕, 실과, 음악, 미술, 체육, 통합교과")
    with cm2:
        st.metric("수록 영역", f"{total_domains}개 영역")
    with cm3:
        st.metric("총 세부 항목", f"{total_items}개 조항")
    with cm4:
        st.metric("난이도 지원", "상 · 중 · 하 3단계", help="하(기초), 중(심화), 상(통인출)")

    # Difficulty Level Control Pill
    st.markdown("### 🎚️ 1. 학습 난이도(STEP) 선택")
    difficulty = st.radio(
        "도전할 난이도 레벨을 선택하세요:",
        [
            "🟢 STEP 1 [하 난이도] : 필수 핵심어 1개 빈칸 (초기 회독 & 빠른 개념 안착)",
            "🟡 STEP 2 [중 난이도] : 핵심어 + 기능 서술어 복합 빈칸 (실전 키워드 인출)",
            "🔴 STEP 3 [상 난이도] : 100% 백지 통빈칸 인출 (실전 통암기)"
        ],
        index=0,
        horizontal=True
    )
    diff_level = "ha" if "하 난이도" in difficulty else ("jung" if "중 난이도" in difficulty else "sang")

    st.markdown("---")

    # Main Navigation Mode Tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🔒 1. 마스킹 모드 (클릭 가리기/확인)",
        "📝 2. 빈칸 문제 풀기 (실전 자동 채점)",
        "📖 3. 정답 보기 (완전판 공식 원문)",
        "🎲 4. 7개 과목 실전 랜덤 모의고사",
        "🔍 5. 7개 과목 전단원 키워드 검색"
    ])

    # =========================================================================
    # TAB 1: 마스킹 모드 (클릭 가리기/확인)
    # =========================================================================
    with tab1:
        st.markdown("### 🔒 인터랙티브 마스킹 모드")
        st.caption("선택하신 난이도의 빈칸이 `[❓ 정답확인]` 버튼으로 가려져 있습니다. 클릭하면 그 자리에서 즉시 단어가 열립니다.")

        c_sub, c_dom, c_rev = st.columns([1.2, 2.3, 1.1])
        with c_sub:
            sel_subject = st.selectbox("과목 선택", ["전체"] + all_subjects, key="mask_naepyo_subj")

        filtered_domains = [d for d in data if sel_subject == "전체" or d["subject"] == sel_subject]
        domain_titles = [f"[{d['subject']}] {d['domain_name']} ({len(d.get('items', []))}항목)" for d in filtered_domains]
        with c_dom:
            sel_domain_title = st.selectbox("학습할 영역 선택", domain_titles, key="mask_naepyo_domain")

        with c_rev:
            st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
            reveal_all = st.checkbox("👁️ 전체 정답 열기", value=False, key="mask_naepyo_rev_all")

        # Get active domain
        active_domain = next(
            (d for d in filtered_domains if f"[{d['subject']}] {d['domain_name']} ({len(d.get('items', []))}항목)" == sel_domain_title),
            filtered_domains[0]
        )

        st.markdown(f"#### 📌 [{active_domain['subject']}] {active_domain['domain_name']}")

        # Group by category (지식·이해 / 과정·기능 / 가치·태도)
        categories = ["지식·이해", "과정·기능", "가치·태도"]
        for cat in categories:
            cat_items = [it for it in active_domain.get("items", []) if it.get("category") == cat]
            if not cat_items:
                continue

            st.markdown(f"##### 🏷️ {cat} ({len(cat_items)}개 항목)")
            
            for it in cat_items:
                if diff_level == "ha":
                    target_text = it.get("text_ha", "")
                    target_blanks = it.get("blanks_ha", {})
                elif diff_level == "jung":
                    target_text = it.get("text_jung", "")
                    target_blanks = it.get("blanks_jung", {})
                else:
                    target_text = it.get("full_text", "")
                    target_blanks = {"①": it.get("full_text", "")}

                if diff_level == "sang":
                    if reveal_all:
                        display_html = f"<span style='background:#DCFCE7; color:#14532D; font-weight:800; padding:3px 8px; border-radius:6px; border:1px solid #86EFAC;'>{it.get('full_text')}</span>"
                    else:
                        display_html = (
                            f"<details style='display:inline-block; vertical-align:middle; margin:2px;'>"
                            f"<summary style='cursor:pointer; background:#EFF6FF; color:#1D4ED8; border:1.5px solid #93C5FD; border-radius:14px; padding:3px 12px; font-size:0.88rem; font-weight:700;'>[❓ 문장 통인출 확인]</summary>"
                            f"<span style='background:#FEF3C7; color:#92400E; border:1px solid #FCD34D; border-radius:6px; padding:3px 8px; font-weight:800; margin-left:6px;'>{it.get('full_text')}</span>"
                            f"</details>"
                        )
                else:
                    display_html = render_masked_text(target_text, target_blanks, show_all=reveal_all)

                st.markdown(f"""
                <div style="background-color: #F8FAFC; border-left: 4px solid #10B981; padding: 12px 16px; border-radius: 0 8px 8px 0; margin-bottom: 8px; font-size: 0.95rem; line-height: 1.8;">
                    <b>{it['item_num']}.</b> {display_html}
                </div>
                """, unsafe_allow_html=True)

    # =========================================================================
    # TAB 2: 빈칸 문제 풀기 (실전 자동 채점)
    # =========================================================================
    with tab2:
        st.markdown("### 📝 빈칸 문제 풀기 & 실시간 자동 채점 모드")
        st.caption("선택하신 난이도 조건에 맞추어 빈칸(또는 통문장)을 직접 타이핑하고, 자동 채점 버튼을 눌러 점수를 확인하세요.")

        qc_sub, qc_dom = st.columns([1.2, 2.8])
        with qc_sub:
            q_subject = st.selectbox("문제 풀 과목 선택", ["전체"] + all_subjects, key="quiz_naepyo_subj")

        q_domains = [d for d in data if q_subject == "전체" or d["subject"] == q_subject]
        q_titles = [f"[{d['subject']}] {d['domain_name']} ({len(d.get('items', []))}항목)" for d in q_domains]
        with qc_dom:
            q_domain_title = st.selectbox("문제 풀 영역 선택", q_titles, key="quiz_naepyo_dom")

        q_active_domain = next(
            (d for d in q_domains if f"[{d['subject']}] {d['domain_name']} ({len(d.get('items', []))}항목)" == q_domain_title),
            q_domains[0]
        )

        st.markdown(f"#### ✍️ [{q_active_domain['subject']}] {q_active_domain['domain_name']} ({difficulty.split(':')[0].strip()})")

        form_key = f"quiz_form_{q_active_domain['domain_id']}_{diff_level}"
        with st.form(key=form_key):
            user_inputs = {}
            total_blanks_count = 0

            for cat in ["지식·이해", "과정·기능", "가치·태도"]:
                c_items = [it for it in q_active_domain.get("items", []) if it.get("category") == cat]
                if not c_items:
                    continue

                st.markdown(f"##### 📌 {cat}")
                
                for it in c_items:
                    it_id = it["item_id"]
                    
                    if diff_level == "ha":
                        display_text = it.get("text_ha", "")
                        blanks_map = it.get("blanks_ha", {})
                    elif diff_level == "jung":
                        display_text = it.get("text_jung", "")
                        blanks_map = it.get("blanks_jung", {})
                    else:
                        display_text = "__________________________________________________"
                        blanks_map = {"통문장": it.get("full_text", "")}

                    # Render blank placeholder
                    if diff_level != "sang":
                        b_idx_c = 0
                        def placeholder_replacer(match):
                            nonlocal b_idx_c
                            b_idx_c += 1
                            return f"<b style='color:#047857; background:#D1FAE5; padding:1px 6px; border-radius:4px;'>[빈칸 {b_idx_c} ______]</b>"
                        prompt_html = re.sub(r'\(\s*_+?\s*\)', placeholder_replacer, display_text)
                    else:
                        prompt_html = "<b style='color:#DC2626;'>[100% 백지 통인출] 공식 원문 문장을 처음부터 끝까지 작성하세요.</b>"

                    st.markdown(f"""
                    <div style="background-color: #F1F5F9; border-left: 4px solid #059669; padding: 10px 14px; border-radius: 0 6px 6px 0; margin-bottom: 8px; font-size: 0.93rem; line-height: 1.7;">
                        <b>{it['item_num']}.</b> {prompt_html}
                    </div>
                    """, unsafe_allow_html=True)

                    # Input fields
                    if diff_level == "sang":
                        total_blanks_count += 1
                        inp_k = f"in_{it_id}_sang"
                        user_inputs[inp_k] = {
                            "user_val": st.text_input(f"{it['item_num']}번 전체 문장 입력:", key=inp_k, placeholder="공식 원문 문장 입력"),
                            "correct_val": it.get("full_text", ""),
                            "label": f"{it['item_num']}번 통문장",
                            "is_sang": True
                        }
                    else:
                        cols = st.columns(min(len(blanks_map), 4) if blanks_map else 1)
                        for b_i, (b_k, b_ans) in enumerate(blanks_map.items()):
                            total_blanks_count += 1
                            inp_k = f"in_{it_id}_{b_k}"
                            with cols[b_i % len(cols)]:
                                user_inputs[inp_k] = {
                                    "user_val": st.text_input(f"{it['item_num']}번 빈칸 {b_i+1}:", key=inp_k, placeholder="정답 단어 입력"),
                                    "correct_val": b_ans,
                                    "label": f"{it['item_num']}번 빈칸 {b_i+1}",
                                    "is_sang": False
                                }
                    st.markdown("<hr style='margin: 6px 0; border: none; border-top: 1px dashed #CBD5E1;'>", unsafe_allow_html=True)

            btn_grade = st.form_submit_button("📝 답안 제출 및 자동 채점하기", type="primary", use_container_width=True)

        if btn_grade:
            correct_cnt = 0
            results = []
            for k, info in user_inputs.items():
                u_val = info["user_val"]
                c_val = info["correct_val"]
                is_sang = info.get("is_sang", False)
                is_c = check_answer(u_val, c_val, is_sang=is_sang)
                if is_c:
                    correct_cnt += 1
                results.append({
                    "label": info["label"],
                    "user_val": u_val if u_val.strip() else "(미입력)",
                    "correct_val": c_val,
                    "is_c": is_c
                })

            score_rate = (correct_cnt / total_blanks_count * 100) if total_blanks_count > 0 else 0
            st.session_state[f"has_graded_{form_key}"] = True
            st.session_state[f"score_{form_key}"] = (correct_cnt, total_blanks_count, score_rate)
            st.session_state[f"results_{form_key}"] = results

        if st.session_state.get(f"has_graded_{form_key}", False):
            correct_cnt, total_blanks_count, score_rate = st.session_state[f"score_{form_key}"]
            results = st.session_state[f"results_{form_key}"]
            st.markdown("---")
            if score_rate == 100:
                st.balloons()
                st.success(f"🎉 **만점입니다! 축하합니다!** ({correct_cnt} / {total_blanks_count}개 정답, 정답률 100%)")
            elif score_rate >= 75:
                st.success(f"👏 **우수한 성적입니다!** ({correct_cnt} / {total_blanks_count}개 정답, 정답률 {score_rate:.1f}%)")
            else:
                st.info(f"📊 **채점 완료:** {correct_cnt} / {total_blanks_count}개 정답 (정답률 {score_rate:.1f}%)")

            col_btn_view, col_btn_reset = st.columns([2, 1])
            is_viewing = st.session_state.get(f"show_detail_{form_key}", False)
            with col_btn_view:
                toggle_label = "🙈 세부 채점 결과 및 정답 가리기" if is_viewing else "🔍 세부 채점 결과 및 정답 확인하기 (버튼 클릭)"
                if st.button(toggle_label, key=f"btn_toggle_{form_key}", use_container_width=True, type="secondary"):
                    st.session_state[f"show_detail_{form_key}"] = not is_viewing
                    st.rerun()
            with col_btn_reset:
                if st.button("🔄 채점 닫기 / 다시 풀기", key=f"btn_reset_{form_key}", use_container_width=True):
                    st.session_state[f"has_graded_{form_key}"] = False
                    st.session_state[f"show_detail_{form_key}"] = False
                    st.rerun()

            if st.session_state.get(f"show_detail_{form_key}", False):
                st.markdown("#### 📊 채점 세부 피드백 및 정답 대조표")
                for r in results:
                    b_icon = "✅ 정답" if r["is_c"] else "❌ 오답"
                    bg = "#F0FDF4" if r["is_c"] else "#FEF2F2"
                    bd = "#86EFAC" if r["is_c"] else "#FCA5A5"
                    st.markdown(f"""
                    <div style="background-color: {bg}; border: 1px solid {bd}; border-radius: 6px; padding: 8px 12px; margin-bottom: 6px;">
                        <b>{r['label']}</b> : {b_icon}<br>
                        • 내 입력: <code>{r['user_val']}</code> &nbsp;|&nbsp;
                        • 실제 정답: <strong style="color: #15803D;">{r['correct_val']}</strong>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.caption("🔒 바로 아래 정답이 노출되지 않도록 가려두었습니다. 확인하시려면 위 **[🔍 세부 채점 결과 및 정답 확인하기]** 버튼을 눌러주세요.")


    # =========================================================================
    # TAB 3: 정답 보기 (완전판 공식 원문)
    # =========================================================================
    with tab3:
        st.markdown("### 📖 정답 보기 & 완전판 공식 원문 대조표")
        st.caption("2022 개정 교육과정 고시 원문 그대로 100% 수록된 완전판 원문 정답지입니다. 노란색 형광펜으로 핵심 키워드를 확인하며 통암기하세요.")

        as_sub, as_dom = st.columns([1.2, 2.8])
        with as_sub:
            a_subject = st.selectbox("원문 볼 과목 선택", ["전체"] + all_subjects, key="ans_naepyo_subj")

        a_domains = [d for d in data if a_subject == "전체" or d["subject"] == a_subject]
        a_titles = [f"[{d['subject']}] {d['domain_name']} ({len(d.get('items', []))}항목)" for d in a_domains]
        with as_dom:
            a_domain_title = st.selectbox("원문 볼 영역 선택", a_titles, key="ans_naepyo_dom")

        a_active_domain = next(
            (d for d in a_domains if f"[{d['subject']}] {d['domain_name']} ({len(d.get('items', []))}항목)" == a_domain_title),
            a_domains[0]
        )

        st.markdown(f"#### 📜 [{a_active_domain['subject']}] {a_active_domain['domain_name']} 공식 원문")

        for cat in ["지식·이해", "과정·기능", "가치·태도"]:
            c_items = [it for it in a_active_domain.get("items", []) if it.get("category") == cat]
            if not c_items:
                continue

            st.markdown(f"##### 🏷️ {cat}")
            
            for it in c_items:
                # Get blanks list from ha and jung to highlight
                blanks_to_hl = list(it.get("blanks_ha", {}).values()) + list(it.get("blanks_jung", {}).values())
                hl_text = render_highlighted_full_text(it.get("full_text", ""), blanks_to_hl)
                
                st.markdown(f"""
                <div style="background-color: #FEFCE8; border-left: 4px solid #EAB308; padding: 10px 14px; border-radius: 0 6px 6px 0; margin-bottom: 6px; font-size: 0.95rem; line-height: 1.8;">
                    <b>{it['item_num']}.</b> {hl_text}
                </div>
                """, unsafe_allow_html=True)

            with st.expander(f"📋 {cat} 정답 키워드 요약표"):
                st.table([
                    {
                        "항목 번호": f"{it['item_num']}번",
                        "하 난이도 빈칸": ", ".join(it.get("blanks_ha", {}).values()),
                        "중 난이도 빈칸": ", ".join(it.get("blanks_jung", {}).values()),
                        "공식 원문": it.get("full_text", "")
                    }
                    for it in c_items
                ])

    # =========================================================================
    # TAB 4: 7개 과목 실전 랜덤 모의고사
    # =========================================================================
    with tab4:
        st.markdown("### 🎲 7개 과목 전범위 실전 랜덤 빈칸 모의고사")
        st.caption("국·도·실·음·미·체·통 629개 전체 항목 중 무작위로 추출하여 실전처럼 테스트합니다.")

        mc1, mc2, mc3 = st.columns([1.5, 1.2, 1.5])
        with mc1:
            m_subj = st.selectbox("모의고사 출제 교과", ["전과목 (7개 전과목)"] + all_subjects, key="mock_naepyo_s")
        with mc2:
            m_count = st.selectbox("출제 문항 수", [5, 10, 15, 20, 30], index=1, key="mock_naepyo_c")
        with mc3:
            st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
            btn_new_mock = st.button("🎲 새로운 모의고사 생성", type="primary", use_container_width=True, key="btn_mock_gen")

        # Candidate pool
        candidate_pool = []
        for d in data:
            if m_subj != "전과목 (7개 전과목)" and d["subject"] != m_subj:
                continue
            for it in d.get("items", []):
                candidate_pool.append({
                    "subject": d["subject"],
                    "domain": d["domain_name"],
                    "category": it["category"],
                    "full_text": it["full_text"],
                    "text_ha": it.get("text_ha", ""),
                    "blanks_ha": it.get("blanks_ha", {}),
                    "text_jung": it.get("text_jung", ""),
                    "blanks_jung": it.get("blanks_jung", {}),
                    "item_id": it["item_id"]
                })

        mock_key = f"current_naepyo_mock_{diff_level}"
        if btn_new_mock or mock_key not in st.session_state:
            sample_size = min(m_count, len(candidate_pool))
            st.session_state[mock_key] = random.sample(candidate_pool, sample_size)
            st.session_state["mock_naepyo_submitted"] = False

        mock_list = st.session_state[mock_key]

        st.markdown(f"#### 🎯 실전 무작위 모의고사 ({len(mock_list)}문항 - {difficulty.split(':')[0].strip()})")

        with st.form(key="mock_naepyo_form"):
            mock_answers = {}
            for q_idx, mq in enumerate(mock_list):
                st.markdown(f"**[{q_idx+1}번] [{mq['subject']}] {mq['domain']} > {mq['category']}**")
                
                if diff_level == "ha":
                    p_text = mq["text_ha"]
                    b_dict = mq["blanks_ha"]
                elif diff_level == "jung":
                    p_text = mq["text_jung"]
                    b_dict = mq["blanks_jung"]
                else:
                    p_text = "__________________________________________________"
                    b_dict = {"통문장": mq["full_text"]}

                if diff_level != "sang":
                    p_text = re.sub(r'\(\s*_+?\s*\)', "<b style='color:#DC2626; background:#FEE2E2; padding:2px 6px; border-radius:4px;'>▶ [빈칸] ◀</b>", p_text)
                else:
                    p_text = "<b style='color:#DC2626;'>[100% 백지 통인출] 해당 항목의 공식 원문 문장을 처음부터 끝까지 작성하세요.</b>"

                st.markdown(f"""
                <div style="background-color: #F8FAFC; border: 1px solid #CBD5E1; padding: 8px 12px; border-radius: 6px; margin-bottom: 6px; font-size: 0.92rem; line-height: 1.7;">
                    {p_text}
                </div>
                """, unsafe_allow_html=True)

                if diff_level == "sang":
                    mock_answers[f"mock_ans_{q_idx}"] = {
                        "user_val": st.text_input(f"[{q_idx+1}번] 문장 전체 입력:", key=f"m_in_{q_idx}", placeholder="공식 원문 입력"),
                        "correct_val": mq["full_text"],
                        "target": f"{mq['subject']} {mq['domain']}",
                        "is_sang": True
                    }
                else:
                    cols = st.columns(min(len(b_dict), 3) if b_dict else 1)
                    for b_i, (bk, bv) in enumerate(b_dict.items()):
                        m_key = f"mock_ans_{q_idx}_{b_i}"
                        with cols[b_i % len(cols)]:
                            mock_answers[m_key] = {
                                "user_val": st.text_input(f"[{q_idx+1}번] 빈칸 {b_i+1} 정답:", key=f"m_in_{q_idx}_{b_i}", placeholder="정답 입력"),
                                "correct_val": bv,
                                "target": f"{mq['subject']} {mq['domain']}",
                                "is_sang": False
                            }
                st.markdown("<hr style='margin: 6px 0; border: none; border-top: 1px dashed #E2E8F0;'>", unsafe_allow_html=True)

            mock_submit_btn = st.form_submit_button("🏁 모의고사 제출 및 채점", type="primary", use_container_width=True)

        if mock_submit_btn:
            m_correct = 0
            m_results = []
            for k, info in mock_answers.items():
                u = info["user_val"]
                c = info["correct_val"]
                is_s = info.get("is_sang", False)
                is_c = check_answer(u, c, is_sang=is_s)
                if is_c:
                    m_correct += 1
                m_results.append({
                    "target": info["target"],
                    "user_val": u if u.strip() else "(미입력)",
                    "correct_val": c,
                    "is_c": is_c
                })

            total_m_items = len(mock_answers)
            m_score = (m_correct / total_m_items * 100) if total_m_items > 0 else 0
            st.session_state["mock_cfe_graded"] = True
            st.session_state["mock_cfe_score"] = (m_correct, total_m_items, m_score)
            st.session_state["mock_cfe_results"] = m_results

        if st.session_state.get("mock_cfe_graded", False):
            m_correct, total_m_items, m_score = st.session_state["mock_cfe_score"]
            m_results = st.session_state["mock_cfe_results"]
            st.markdown("---")
            if m_score >= 80:
                st.balloons()
                st.success(f"🏆 **합격권 점수입니다!** ({m_correct} / {total_m_items}개 정답, {m_score:.1f}점)")
            else:
                st.info(f"📊 **채점 완료:** {m_correct} / {total_m_items}개 정답 ({m_score:.1f}점)")

            m_viewing = st.session_state.get("mock_cfe_show_detail", False)
            c_m1, c_m2 = st.columns([2, 1])
            with c_m1:
                lbl = "🙈 모의고사 정답 가리기" if m_viewing else "🔍 모의고사 상세 채점표 및 정답 확인하기 (버튼 클릭)"
                if st.button(lbl, key="btn_mock_toggle_cfe", use_container_width=True, type="secondary"):
                    st.session_state["mock_cfe_show_detail"] = not m_viewing
                    st.rerun()
            with c_m2:
                if st.button("🔄 모의고사 채점 닫기", key="btn_mock_reset_cfe", use_container_width=True):
                    st.session_state["mock_cfe_graded"] = False
                    st.session_state["mock_cfe_show_detail"] = False
                    st.rerun()

            if st.session_state.get("mock_cfe_show_detail", False):
                st.markdown("#### 📊 모의고사 세부 채점 결과")
                for mr in m_results:
                    badge = "✅ 정답" if mr["is_c"] else "❌ 오답"
                    bg = "#F0FDF4" if mr["is_c"] else "#FEF2F2"
                    bd = "#86EFAC" if mr["is_c"] else "#FCA5A5"
                    st.markdown(f"""
                    <div style="background-color: {bg}; border: 1px solid {bd}; border-radius: 6px; padding: 6px 10px; margin-bottom: 4px; font-size: 0.9rem;">
                        <b>[{badge}]</b> {mr['target']}<br>
                        • 입력: <code>{mr['user_val']}</code> &nbsp;|&nbsp; 
                        • 정답: <strong style="color: #15803D;">{mr['correct_val']}</strong>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.caption("🔒 채점 및 정답이 바로 노출되지 않도록 가려두었습니다. 확인하시려면 위 **[🔍 모의고사 상세 채점표 및 정답 확인하기]** 버튼을 눌러주세요.")


    # =========================================================================
    # TAB 5: 7개 과목 전단원 키워드 검색
    # =========================================================================
    with tab5:
        st.markdown("### 🔍 7개 과목 전단원 내용체계표 키워드 검색기")
        st.caption("궁금한 교육과정 단어(예: 메나리토리, 타당한지, 준법, 지속가능, 디지털, 알고리즘, 생태전환 등)를 검색하면 629개 전항목에서 실시간으로 찾아줍니다.")

        kw_search = st.text_input("검색할 단어 입력:", placeholder="예: 디지털, 알고리즘, 생태전환, 도덕적, 메나리토리 등", key="naepyo_kw_in")

        if kw_search and kw_search.strip():
            kw = kw_search.strip()
            found = []
            for d in data:
                for it in d.get("items", []):
                    full = it.get("full_text", "")
                    if kw in full or kw in it.get("text_ha", "") or kw in it.get("text_jung", ""):
                        found.append({
                            "subject": d["subject"],
                            "domain": d["domain_name"],
                            "category": it["category"],
                            "item_num": it["item_num"],
                            "full_text": full
                        })

            st.markdown(f"**총 `{len(found)}건`의 관련 내용체계표 항목이 검색되었습니다.**")
            
            for f_i, fi in enumerate(found):
                st.markdown(f"##### 🔎 [{f_i+1}] [{fi['subject']}] {fi['domain']} > {fi['category']} ({fi['item_num']}번)")
                
                h_text = fi["full_text"]
                kw_pat = re.compile(re.escape(kw), re.IGNORECASE)
                h_text = kw_pat.sub(f"<mark style='background:#FDE047; color:#000; font-weight:bold; padding:2px 4px;'>{kw}</mark>", h_text)

                st.markdown(f"""
                <div style="background-color: #F8FAFC; border-left: 4px solid #10B981; padding: 10px 14px; border-radius: 0 6px 6px 0; margin-bottom: 8px; font-size: 0.93rem; line-height: 1.8;">
                    {h_text}
                </div>
                """, unsafe_allow_html=True)
                st.markdown("<hr style='margin: 4px 0; border: none; border-top: 1px solid #E2E8F0;'>", unsafe_allow_html=True)
        else:
            st.info("💡 상단 검색창에 검색하고 싶은 교육과정 단어를 입력해보세요. (예: `알고리즘`, `생태전환`, `도덕적`, `메나리토리`, `타당한지`)")
