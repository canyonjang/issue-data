import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import time

# 페이지 설정
st.set_page_config(page_title="수업 발표 참여 시스템", layout="wide")

# CSS를 사용하여 상단 'Running' 상태 바를 완전히 숨깁니다.
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    div[data-testid="stStatusWidget"] {display: none !important;}
    </style>
    """, unsafe_allow_html=True)

# 1. 구글 시트 연결 설정
conn = st.connection("gsheets", type=GSheetsConnection)

# 2. 사이드바: 정보 입력 및 이슈 선택
st.sidebar.header("📋 수업 정보 입력")
current_issue = st.sidebar.selectbox("이번 주 이슈 선택", ["이슈1", "이슈2", "이슈3", "이슈4", "이슈5"])
name = st.sidebar.text_input("이름")
student_id = st.sidebar.text_input("학번")

# 3. 데이터 업데이트 및 화면 표시 (Fragment 사용)
# 이 안의 내용은 지정된 시간마다 돌지만 화면 전체를 흐리게 만들지 않습니다.
@st.fragment(run_every="10s")
def display_content():
    # 데이터 읽기 (해당 주차 시트에서 가져오기)
    try:
        issue_df = conn.read(worksheet=current_issue, ttl=0)
    except Exception:
        issue_df = pd.DataFrame()

    tab1, tab2, tab3 = st.tabs(["🗳️ 투표 및 질문 제출", "📊 투표 결과", "❓ 질문 모아보기"])

    # --- Tab 1: 투표 및 질문 제출 ---
    with tab1:
        st.header(f"[{current_issue}] 발표 참여 및 질문")
        
        col1, col2 = st.columns(2)
        with col1:
            pre_vote = st.radio("1. 발표 전 나의 입장", ["입장A", "입장B"], key=f"pre_{current_issue}")
        with col2:
            post_vote = st.radio("2. 발표 후 나의 입장", ["입장A", "입장B"], key=f"post_{current_issue}")
        
        st.divider()
        st.subheader("3. 질문 던지기 (최대 3개)")
        
        questions_to_submit = []
        for i in range(1, 4):
            with st.expander(f"질문 {i} 작성", expanded=(i==1)):
                q_target = st.selectbox(f"질문 {i} 대상", ["입장A", "입장B"], key=f"target_{i}_{current_issue}")
                q_type = st.selectbox(f"질문 {i} 유형", ["사실", "추론", "비판"], key=f"type_{i}_{current_issue}")
                q_content = st.text_area(f"질문 {i} 내용", key=f"content_{i}_{current_issue}")
                
                if q_content.strip():
                    questions_to_submit.append({"대상": q_target, "유형": q_type, "내용": q_content})

        if st.button("내용 제출하기", key="submit_btn"):
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
                    # A. 해당 주차 시트에 저장
                    try:
                        current_sheet_data = conn.read(worksheet=current_issue, ttl=0)
                        updated_issue_df = pd.concat([current_sheet_data, new_df], ignore_index=True)
                    except:
                        updated_issue_df = new_df
                    conn.update(worksheet=current_issue, data=updated_issue_df)

                    # B. '전체데이터' 시트에 누적 저장
                    try:
                        total_sheet_data = conn.read(worksheet="전체데이터", ttl=0)
                        updated_total_df = pd.concat([total_sheet_data, new_df], ignore_index=True)
                    except:
                        updated_total_df = new_df
                    conn.update(worksheet="전체데이터", data=updated_total_df)

                    st.success("제출 완료!")
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"저장 중 오류 발생: {e}")

    # --- Tab 2: 투표 결과 ---
    with tab2:
        st.header(f"📊 {current_issue} 실시간 투표 현황")
        if not issue_df.empty:
            unique_votes = issue_df.drop_duplicates(subset=["이름", "학번"])
            
            c1, c2 = st.columns(2)
            with c1:
                st.subheader("발표 전")
                pre_a = unique_votes[unique_votes["사전투표"] == "입장A"]["이름"].tolist()
                pre_b = unique_votes[unique_votes["사전투표"] == "입장B"]["이름"].tolist()
                st.write(f"**입장A:** {', '.join(pre_a)}")
                st.write(f"**입장B:** {', '.join(pre_b)}")
            with c2:
                st.subheader("발표 후")
                post_a = unique_votes[unique_votes["사후투표"] == "입장A"]["이름"].tolist()
                post_b = unique_votes[unique_votes["사후투표"] == "입장B"]["이름"].tolist()
                st.write(f"**입장A:** {', '.join(post_a)}")
                st.write(f"**입장B:** {', '.join(post_b)}")

            st.divider()
            st.subheader("🔄 입장이 바뀐 학생")
            def highlight_changes(row):
                return ['background-color: #FFD700; color: black'] * len(row) if row["사전투표"] != row["사후투표"] else [''] * len(row)
            
            display_df = unique_votes[["이름", "학번", "사전투표", "사후투표"]]
            st.dataframe(display_df.style.apply(highlight_changes, axis=1), use_container_width=True)
        else:
            st.info(f"[{current_issue}] 시트에 아직 데이터가 없습니다.")

    # --- Tab 3: 질문 모아보기 ---
    with tab3:
        st.header(f"❓ {current_issue} 질문 리스트")
        if not issue_df.empty:
            for side in ["입장A", "입장B"]:
                st.subheader(f"📍 {side}를 향한 질문")
                side_df = issue_df[issue_df["대상입장"] == side]
                col_f, col_i, col_c = st.columns(3)
                with col_f:
                    st.info("사실 질문")
                    for q in side_df[side_df["질문유형"] == "사실"]["질문내용"]: st.write(f"- {q}")
                with col_i:
                    st.warning("추론 질문")
                    for q in side_df[side_df["질문유형"] == "추론"]["질문내용"]: st.write(f"- {q}")
                with col_c:
                    st.error("비판 질문")
                    for q in side_df[side_df["질문유형"] == "비판"]["질문내용"]: st.write(f"- {q}")
        else:
            st.info(f"[{current_issue}] 시트에 등록된 질문이 없습니다.")

# 함수 실행
display_content()

# 자동 업데이트 안내
st.sidebar.divider()
st.sidebar.caption("🔄 10초마다 화면이 깜빡임 없이 업데이트됩니다.")
