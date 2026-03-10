import streamlit as st
from supabase import create_client, Client
import pandas as pd
import time
from datetime import datetime, timedelta

# ==========================================
# [교수님 설정 구역]
# ==========================================
CURRENT_ISSUE_NAME = "이슈1" 
PROFESSOR_PASSWORD = "3383"
# ==========================================

# 1. 페이지 설정 및 CSS
st.set_page_config(page_title="수업 발표 참여 시스템", layout="wide")
st.markdown("""
    <style>
    div[data-testid="stStatusWidget"] {display: none !important;}
    div[data-testid="stAppViewBlockContainer"] {opacity: 1 !important;}
    </style>
    """, unsafe_allow_html=True)

# 2. 수파베이스 연결
@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_connection()

# 3. 사이드바 설정
st.sidebar.header("📋 수업 참여 정보")
st.sidebar.info(f"현재 이슈: **{CURRENT_ISSUE_NAME}**")
name = st.sidebar.text_input("이름")
student_id = st.sidebar.text_input("학번")

st.sidebar.divider()
st.sidebar.header("🔒 교수님 전용 메뉴")
input_pw = st.sidebar.text_input("비밀번호 입력", type="password")

# 4. 메인 탭 구성
tab1, tab2, tab3 = st.tabs(["🗳️ 투표 및 질문 제출", "📊 투표 결과", "❓ 질문 모아보기"])

# --- Tab 1: 투표 및 질문 제출 ---
with tab1:
    st.header(f"[{CURRENT_ISSUE_NAME}] 발표 참여 및 질문")
    col1, col2 = st.columns(2)
    with col1: pre_vote = st.radio("1. 발표 전 나의 입장", ["입장A", "입장B"], key="pre")
    with col2: post_vote = st.radio("2. 발표 후 나의 입장", ["입장A", "입장B"], key="post")
    
    st.divider()
    st.subheader("3. 질문 던지기 (최대 3개)")
    
    questions_to_submit = []
    for i in range(1, 4):
        with st.expander(f"질문 {i} 작성", expanded=(i==1)):
            q_target = st.selectbox(f"질문 {i} 대상", ["입장 A1", "입장 A2", "입장 B1", "입장 B2"], key=f"target_{i}")
            q_type = st.selectbox(f"질문 {i} 유형", ["사실", "추론", "비판"], key=f"type_{i}")
            q_content = st.text_area(f"질문 {i} 내용", key=f"content_{i}", max_chars=150)
            
            if q_content.strip():
                kst_now = datetime.utcnow() + timedelta(hours=9)
                created_at_kst = kst_now.strftime("%Y-%m-%d %H:%M:%S")

                questions_to_submit.append({
                    "issue_name": CURRENT_ISSUE_NAME,
                    "student_name": name,
                    "student_id": student_id,
                    "pre_vote": pre_vote,
                    "post_vote": post_vote,
                    "q_target": q_target,
                    "q_type": q_type,
                    "q_content": q_content,
                    "created_at_kst": created_at_kst
                })

    if st.button("내용 제출하기"):
        if not (name and student_id and questions_to_submit):
            st.error("이름, 학번, 질문 내용을 모두 입력해주세요.")
        else:
            try:
                # 테이블 이름 반영: class_responses
                supabase.table("class_responses").insert(questions_to_submit).execute()
                st.success("성공적으로 제출되었습니다!")
                time.sleep(2)
                st.rerun()
            except Exception as e:
                st.error(f"저장 오류: {e}")

# --- 교수님 전용 로직 ---
if input_pw == PROFESSOR_PASSWORD:
    if st.sidebar.button("🔄 실시간 데이터 새로고침"):
        st.cache_data.clear()
        st.success("최신 데이터를 불러왔습니다.")

    try:
        response = supabase.table("class_responses").select("*").eq("issue_name", CURRENT_ISSUE_NAME).execute()
        issue_df = pd.DataFrame(response.data)
    except:
        issue_df = pd.DataFrame()

    # --- Tab 2: 투표 결과 ---
    with tab2:
        st.header(f"📊 {CURRENT_ISSUE_NAME} 실시간 투표 현황")
        if not issue_df.empty:
            uv = issue_df.drop_duplicates(subset=["student_name", "student_id"])
            
            c1, c2 = st.columns(2)
            with c1:
                st.subheader("발표 전 명단")
                st.write(f"**입장A:** {', '.join(uv[uv['pre_vote'] == '입장A']['student_name'])}")
                st.write(f"**입장B:** {', '.join(uv[uv['pre_vote'] == '입장B']['student_name'])}")
            with c2:
                st.subheader("발표 후 명단")
                st.write(f"**입장A:** {', '.join(uv[uv['post_vote'] == '입장A']['student_name'])}")
                st.write(f"**입장B:** {', '.join(uv[uv['post_vote'] == '입장B']['student_name'])}")
            
            st.divider()
            st.subheader("🔄 입장이 바뀐 학생 (강조)")
            def highlight(row):
                return ['background-color: #FFD700; color: black'] * len(row) if row["pre_vote"] != row["post_vote"] else [''] * len(row)
            
            display_df = uv[["student_name", "student_id", "pre_vote", "post_vote"]].rename(
                columns={"student_name": "이름", "student_id": "학번", "pre_vote": "사전투표", "post_vote": "사후투표"}
            )
            st.dataframe(display_df.style.apply(highlight, axis=1), use_container_width=True)
        else:
            st.info("데이터가 없습니다.")

    # --- Tab 3: 질문 모아보기 ---
    with tab3:
        st.header(f"❓ {CURRENT_ISSUE_NAME} 질문 리스트")
        if not issue_df.empty:
            for side in ["입장 A1", "입장 A2", "입장 B1", "입장 B2"]:
                st.subheader(f"📍 {side}를 향한 질문")
                s_df = issue_df[issue_df["q_target"] == side]
                
                if s_df.empty:
                    st.caption("질문 없음")
                else:
                    cf, ci, cc = st.columns(3)
                    with cf:
                        st.info("사실 질문")
                        for q in s_df[s_df["q_type"] == "사실"]["q_content"]: st.write(f"- {q}")
                    with ci:
                        st.warning("추론 질문")
                        for q in s_df[s_df["q_type"] == "추론"]["q_content"]: st.write(f"- {q}")
                    with cc:
                        st.error("비판 질문")
                        for q in s_df[s_df["q_type"] == "비판"]["q_content"]: st.write(f"- {q}")
                st.divider()

else:
    with tab2: st.warning("🔒 교수님 비밀번호를 입력해주세요.")
    with tab3: st.warning("🔒 교수님 비밀번호를 입력해주세요.")
