import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import time

# 1. 페이지 설정 및 CSS
st.set_page_config(page_title="수업 발표 참여 시스템", layout="wide")

# 상단 Running 표시 및 화면 흐림 방지 CSS
st.markdown("""
    <style>
    div[data-testid="stStatusWidget"] {display: none !important;}
    div[data-testid="stAppViewBlockContainer"] {opacity: 1 !important;}
    </style>
    """, unsafe_allow_html=True)

# 2. 구글 시트 연결
conn = st.connection("gsheets", type=GSheetsConnection)

# 3. 사이드바 설정 (이슈 선택 시 탭 초기화 방지를 위해 최상단 위치)
st.sidebar.header("📋 수업 정보 입력")
current_issue = st.sidebar.selectbox("이번 주 이슈 선택", ["이슈1", "이슈2", "이슈3", "이슈4", "이슈5"])
name = st.sidebar.text_input("이름")
student_id = st.sidebar.text_input("학번")

# 4. 메인 탭 구성 (함수 밖으로 빼서 새로고침 시에도 탭 유지)
tab1, tab2, tab3 = st.tabs(["🗳️ 투표 및 질문 제출", "📊 투표 결과", "❓ 질문 모아보기"])

# --- Tab 1: 투표 및 질문 제출 (새로고침 영향을 받지 않도록 fragment 밖으로 구성) ---
with tab1:
    st.header(f"[{current_issue}] 발표 참여 및 질문")
    
    col1, col2 = st.columns(2)
    with col1:
        pre_vote = st.radio("1. 발표 전 나의 입장", ["입장A", "입장B"], key=f"pre_{current_issue}")
    with col2:
        post_vote = st.radio("2. 발표 후 나의 입장", ["입장A", "입장B"], key=f"post_{current_issue}")
    
    st.divider()
    st.subheader("3. 질문 던지기 (최대 3개)")
    
    # 입력 중 내용이 날아가지 않도록 Form 사용 또는 일반 위젯 배치
    questions_to_submit = []
    for i in range(1, 4):
        with st.expander(f"질문 {i} 작성", expanded=(i==1)):
            q_target = st.selectbox(f"질문 {i} 대상", ["입장A", "입장B"], key=f"target_{i}_{current_issue}")
            q_type = st.selectbox(f"질문 {i} 유형", ["사실", "추론", "비판"], key=f"type_{i}_{current_issue}")
            q_content = st.text_area(f"질문 {i} 내용", key=f"content_{i}_{current_issue}")
            
            if q_content.strip():
                questions_to_submit.append({"대상": q_target, "유형": q_type, "내용": q_content})

    if st.button("내용 제출하기"):
        if not name or not student_id:
            st.error("이름과 학번을 입력해주세요.")
        elif len(questions_to_submit) == 0:
            st.error("최소 1개 이상의 질문을 작성해야 합니다.")
        else:
            new_rows = []
            for q in questions_to_submit:
                new_rows.append({
                    "주차(Issue)": current_issue, "이름": name, "학번": student_id,
                    "사전투표": pre_vote, "사후투표": post_vote,
                    "질문유형": q["유형"], "질문내용": q["내용"], "대상입장": q["대상"]
                })
            new_df = pd.DataFrame(new_rows)
            try:
                # 이슈 시트 저장
                try:
                    curr_data = conn.read(worksheet=current_issue, ttl=0)
                    upd_issue = pd.concat([curr_data, new_df], ignore_index=True)
                except: upd_issue = new_df
                conn.update(worksheet=current_issue, data=upd_issue)
                
                # 전체 시트 저장
                try:
                    total_data = conn.read(worksheet="전체데이터", ttl=0)
                    upd_total = pd.concat([total_data, new_df], ignore_index=True)
                except: upd_total = new_df
                conn.update(worksheet="전체데이터", data=upd_total)

                st.success("제출 완료!")
                time.sleep(1)
                st.rerun() # 제출 후에는 전체 갱신
            except Exception as e:
                st.error(f"저장 오류: {e}")

# --- Tab 2 & 3: 결과 및 질문 (10초마다 부분 새로고침 적용) ---
@st.fragment(run_every="10s")
def sync_results():
    try:
        # 실시간 데이터 로드
        issue_df = conn.read(worksheet=current_issue, ttl=0)
    except Exception:
        issue_df = pd.DataFrame()

    with tab2:
        st.header(f"📊 {current_issue} 실시간 투표 현황")
        if not issue_df.empty:
            unique_votes = issue_df.drop_duplicates(subset=["이름", "학번"])
            c1, c2 = st.columns(2)
            with c1:
                st.subheader("발표 전")
                st.write(f"**입장A:** {', '.join(unique_votes[unique_votes['사전투표'] == '입장A']['이름'])}")
                st.write(f"**입장B:** {', '.join(unique_votes[unique_votes['사전투표'] == '입장B']['이름'])}")
            with c2:
                st.subheader("발표 후")
                st.write(f"**입장A:** {', '.join(unique_votes[unique_votes['사후투표'] == '입장A']['이름'])}")
                st.write(f"**입장B:** {', '.join(unique_votes[unique_votes['사후투표'] == '입장B']['이름'])}")

            st.divider()
            st.subheader("🔄 입장이 바뀐 학생")
            def highlight(row):
                return ['background-color: #FFD700; color: black'] * len(row) if row["사전투표"] != row["사후투표"] else [''] * len(row)
            st.dataframe(unique_votes[["이름", "학번", "사전투표", "사후투표"]].style.apply(highlight, axis=1), use_container_width=True)
        else:
            st.info("실시간 데이터를 불러오는 중입니다...")

    with tab3:
        st.header(f"❓ {current_issue} 질문 리스트")
        if not issue_df.empty:
            for side in ["입장A", "입장B"]:
                st.subheader(f"📍 {side}를 향한 질문")
                s_df = issue_df[issue_df["대상입장"] == side]
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
        else:
            st.info("등록된 질문이 없습니다.")

# 부분 새로고침 함수 실행
sync_results()

st.sidebar.divider()
st.sidebar.caption("🔄 결과 탭은 10초마다 자동 업데이트됩니다.")
