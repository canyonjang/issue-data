import streamlit as st
from supabase import create_client, Client
import pandas as pd
import time
from datetime import datetime, timedelta  # 시간 계산을 위한 라이브러리 추가

# ==========================================
# [교수님 설정 구역]
# ==========================================
CURRENT_ISSUE_NAME = "이슈1" 
PROFESSOR_PASSWORD = "3383"
# ==========================================

# 1. 페이지 설정 및 CSS
st.set_page_config(page_title="수업 발표 참여 시스템 (KST 버전)", layout="wide")
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
st.sidebar.info(f"현재 진행 중인 이슈: **{CURRENT_ISSUE_NAME}**")
name = st.sidebar.text_input("이름")
student_id = st.sidebar.text_input("학번")

st.sidebar.divider()
st.sidebar.header("🔒 교수님 전용 메뉴")
input_pw = st.sidebar.text_input("비밀번호 입력", type="password")

# 4. 메인 탭 구성
tab1, tab2, tab3 = st.tabs(["🗳️ 투표 및 질문 제출", "📊 투표 결과", "❓ 질문 모아보기"])

# --- Tab 1: 제출 (한국 시간 포함) ---
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
            st.caption(f"현재 글자 수: {len(q_content)} / 150자")
            
            if q_content.strip():
                # 한국 시간(KST) 생성: UTC+9
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
                    "created_at_kst": created_at_kst  # 한국 시간 필드 추가
                })

    if st.button("내용 제출하기"):
        if not (name and student_id and questions_to_submit):
            st.error("모든 정보를 입력해주세요.")
        else:
            try:
                supabase.table("class_responses").insert(questions_to_submit).execute()
                st.success("성공적으로 제출되었습니다!")
                time.sleep(3)
                st.rerun()
            except Exception as e:
                st.error(f"저장 오류: {e}")

# --- 교수님 전용 로직 ---
if input_pw == PROFESSOR_PASSWORD:
    if st.sidebar.button("🔄 실시간 데이터 새로고침"):
        st.cache_data.clear()
        st.success("최신 데이터를 불러왔습니다.")

    try:
        response = supabase.table("issue question").select("*").eq("issue_name", CURRENT_ISSUE_NAME).execute()
        issue_df = pd.DataFrame(response.data)
    except:
        issue_df = pd.DataFrame()

    with tab2:
        st.header(f"📊 {CURRENT_ISSUE_NAME} 투표 현황")
        if not issue_df.empty:
            uv = issue_df.drop_duplicates(subset=["student_name", "student_id"])
            st.write(f"총 참여 인원: {len(uv)}명")
            # 데이터프레임 표시 시 한국 시간 컬럼 포함 가능
            st.dataframe(uv[["created_at_kst", "student_name", "student_id", "pre_vote", "post_vote"]], use_container_width=True)

    with tab3:
        st.header(f"❓ {CURRENT_ISSUE_NAME} 질문 리스트")
        if not issue_df.empty:
            for side in ["입장 A1", "입장 A2", "입장 B1", "입장 B2"]:
                st.subheader(f"📍 {side}를 향한 질문")
                s_df = issue_df[issue_df["q_target"] == side]
                if s_df.empty: st.caption("질문 없음")
                else:
                    cf, ci, cc = st.columns(3)
                    # 질문 내용과 함께 제출 시간(KST)을 작게 표시 가능
                    with cf:
                        st.info("사실")
                        for _, q in s_df[s_df["q_type"] == "사실"].iterrows():
                            st.write(f"- {q['q_content']} ({q['student_name']} / {q['created_at_kst'][11:16]})")
                    with ci:
                        st.warning("추론")
                        for _, q in s_df[s_df["q_type"] == "추론"].iterrows():
                            st.write(f"- {q['q_content']} ({q['student_name']} / {q['created_at_kst'][11:16]})")
                    with cc:
                        st.error("비판")
                        for _, q in s_df[s_df["q_type"] == "비판"].iterrows():
                            st.write(f"- {q['q_content']} ({q['student_name']} / {q['created_at_kst'][11:16]})")
