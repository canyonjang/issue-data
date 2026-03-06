import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import time

# ==========================================
# [교수님 설정 구역]
# ==========================================
CURRENT_ISSUE_NAME = "이슈1"  # 새로운 이슈 사용 시 이 부분만 수정하세요 (이슈2, 이슈3 등)
PROFESSOR_PASSWORD = "3383"   # 교수님 전용 비밀번호
# ==========================================

# 1. 페이지 설정 및 CSS
st.set_page_config(page_title="수업 발표 참여 시스템", layout="wide")

st.markdown("""
    <style>
    div[data-testid="stStatusWidget"] {display: none !important;}
    div[data-testid="stAppViewBlockContainer"] {opacity: 1 !important;}
    </style>
    """, unsafe_allow_html=True)

# 2. 구글 시트 연결
conn = st.connection("gsheets", type=GSheetsConnection)

# 3. 사이드바 설정 (정보 입력 및 비밀번호)
st.sidebar.header("📋 수업 참여 정보")
st.sidebar.info(f"현재 진행 중인 이슈: **{CURRENT_ISSUE_NAME}**")
name = st.sidebar.text_input("이름")
student_id = st.sidebar.text_input("학번")

st.sidebar.divider()
st.sidebar.header("🔒 교수님 전용 메뉴")
input_pw = st.sidebar.text_input("비밀번호 입력", type="password", help="비밀번호를 입력해야 결과 탭이 활성화됩니다.")

# 4. 메인 탭 구성
tab1, tab2, tab3 = st.tabs(["🗳️ 투표 및 질문 제출", "📊 투표 결과", "❓ 질문 모아보기"])

# --- Tab 1: 투표 및 질문 제출 ---
with tab1:
    st.header(f"[{CURRENT_ISSUE_NAME}] 발표 참여 및 질문")
    col1, col2 = st.columns(2)
    with col1:
        pre_vote = st.radio("1. 발표 전 나의 입장", ["입장A", "입장B"], key="pre")
    with col2:
        post_vote = st.radio("2. 발표 후 나의 입장", ["입장A", "입장B"], key="post")
    
    st.divider()
    st.subheader("3. 질문 던지기 (최대 3개)")
    st.info("💡 각 질문은 최대 150자까지 작성 가능하며, 최소 1개 이상의 질문을 반드시 작성해야 합니다.")
    
    questions_to_submit = []
    for i in range(1, 4):
        with st.expander(f"질문 {i} 작성", expanded=(i==1)):
            # 1. 질문 대상 세분화 (A1, A2, B1, B2)
            q_target = st.selectbox(f"질문 {i} 대상", ["입장 A1", "입장 A2", "입장 B1", "입장 B2"], key=f"target_{i}")
            q_type = st.selectbox(f"질문 {i} 유형", ["사실", "추론", "비판"], key=f"type_{i}")
            
            # 2. 글자 수 제한 및 캡션 반영
            q_content = st.text_area(f"질문 {i} 내용", key=f"content_{i}", max_chars=150, placeholder="질문을 150자 이내로 입력하세요...")
            st.caption(f"현재 글자 수: {len(q_content)} / 150자")
            
            if q_content.strip():
                questions_to_submit.append({"대상": q_target, "유형": q_type, "내용": q_content})

    if st.button("내용 제출하기"):
        if not (name and student_id and questions_to_submit):
            st.error("이름, 학번, 질문 내용을 모두 입력해주세요.")
        else:
            new_rows = []
            for q in questions_to_submit:
                new_rows.append({
                    "주차(Issue)": CURRENT_ISSUE_NAME, "이름": name, "학번": student_id,
                    "사전투표": pre_vote, "사후투표": post_vote,
                    "질문유형": q["유형"], "질문내용": q["내용"], "대상입장": q["대상"]
                })
            new_df = pd.DataFrame(new_rows)
            
            try:
                # 데이터 저장 (이슈 시트 + 전체 시트)
                for sheet in [CURRENT_ISSUE_NAME, "전체데이터"]:
                    try:
                        old = conn.read(worksheet=sheet, ttl=0)
                        updated = pd.concat([old, new_df], ignore_index=True)
                    except: updated = new_df
                    conn.update(worksheet=sheet, data=updated)
                st.success("성공적으로 제출되었습니다!")
                time.sleep(3)
                st.rerun()
            except Exception as e:
                st.error(f"저장 오류: {e}")

# --- 교수님 인증 확인 로직 ---
if input_pw == PROFESSOR_PASSWORD:
    if st.sidebar.button("🔄 실시간 데이터 새로고침"):
        st.cache_data.clear() 
        st.success("최신 데이터를 성공적으로 불러왔습니다.")

    try:
        issue_df = conn.read(worksheet=CURRENT_ISSUE_NAME, ttl=0)
    except:
        issue_df = pd.DataFrame()

    # --- Tab 2: 투표 결과 ---
    with tab2:
        st.header(f"📊 {CURRENT_ISSUE_NAME} 실시간 투표 현황")
        if not issue_df.empty:
            uv = issue_df.drop_duplicates(subset=["이름", "학번"])
            c1, c2 = st.columns(2)
            with c1:
                st.subheader("발표 전 명단")
                st.write(f"**입장A:** {', '.join(uv[uv['사전투표'] == '입장A']['이름'])}")
                st.write(f"**입장B:** {', '.join(uv[uv['사전투표'] == '입장B']['이름'])}")
            with c2:
                st.subheader("발표 후 명단")
                st.write(f"**입장A:** {', '.join(uv[uv['사후투표'] == '입장A']['이름'])}")
                st.write(f"**입장B:** {', '.join(uv[uv['사후투표'] == '입장B']['이름'])}")
            
            st.divider()
            st.subheader("🔄 입장이 바뀐 학생 (강조)")
            def highlight(row):
                return ['background-color: #FFD700; color: black'] * len(row) if row["사전투표"] != row["사후투표"] else [''] * len(row)
            st.dataframe(uv[["이름", "학번", "사전투표", "사후투표"]].style.apply(highlight, axis=1), use_container_width=True)
        else:
            st.info("표시할 투표 데이터가 없습니다. 새로고침 버튼을 눌러보세요.")

    # --- Tab 3: 질문 모아보기 ---
    with tab3:
        st.header(f"❓ {CURRENT_ISSUE_NAME} 질문 리스트")
        if not issue_df.empty:
            # 세분화된 대상 리스트 순회
            for side in ["입장 A1", "입장 A2", "입장 B1", "입장 B2"]:
                st.subheader(f"📍 {side}를 향한 질문")
                s_df = issue_df[issue_df["대상입장"] == side]
                
                if s_df.empty:
                    st.caption("해당 발표자에게 접수된 질문이 없습니다.")
                else:
                    cf, ci, cc = st.columns(3)
                    with cf:
                        st.info("사실 질문")
                        for q in s_df[s_df["질문유형"] == "사실"]["질문내용"]: st.write(f"- {q}")
                    with ci:
                        st.warning("추론 질문")
                        for q in s_df[s_df["질문유형"] == "추론"]["질문내용"]: st.write(f"- {q}")
                    with cc:
                        st.error("비판 질문")
                        for q in s_df[s_df["질문유형"] == "비판"]["질문내용"]: st.write(f"- {q}")
                st.divider()
        else:
            st.info("표시할 질문 데이터가 없습니다. 새로고침 버튼을 눌러보세요.")

else:
    with tab2:
        st.warning("🔒 교수님 비밀번호를 입력해야 결과를 볼 수 있습니다.")
    with tab3:
        st.warning("🔒 교수님 비밀번호를 입력해야 질문 리스트를 볼 수 있습니다.")
