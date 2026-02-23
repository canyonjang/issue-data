import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# 페이지 설정
st.set_page_config(page_title="수업 발표 참여 시스템", layout="wide")

# 1. 구글 시트 연결 설정
# (주의: .streamlit/secrets.toml 파일에 구글 시트 인증 정보가 설정되어 있어야 합니다)
conn = st.connection("gsheets", type=GSheetsConnection)

# 2. 사이드바: 정보 입력 및 이슈 선택
st.sidebar.header("📋 수업 정보 입력")
current_issue = st.sidebar.selectbox("이번 주 이슈 선택", ["이슈1", "이슈2", "이슈3", "이슈4", "이슈5"])
name = st.sidebar.text_input("이름")
student_id = st.sidebar.text_input("학번")

# 3. 탭 구성
tab1, tab2, tab3 = st.tabs(["🗳️ 투표 및 질문 제출", "📊 투표 결과", "❓ 질문 모아보기"])

# --- Tab 1: 투표 및 질문 제출 ---
with tab1:
    st.header(f"[{current_issue}] 발표 참여 및 질문")
    
    col1, col2 = st.columns(2)
    with col1:
        pre_vote = st.radio("1. 발표 전 나의 입장", ["입장A", "입장B"], help="발표를 듣기 전의 생각을 선택하세요.")
    with col2:
        post_vote = st.radio("2. 발표 후 나의 입장", ["입장A", "입장B"], help="발표를 듣고 난 후의 생각을 선택하세요.")
    
    st.divider()
    st.subheader("3. 질문 던지기 (최대 3개)")
    st.info("💡 1개 이상의 질문을 반드시 작성해야 합니다.")
    
    # 질문 입력을 위한 3개의 섹션
    questions_to_submit = []
    
    for i in range(1, 4):
        with st.expander(f"질문 {i} 작성", expanded=(i==1)):
            q_target = st.selectbox(f"질문 {i} 대상", ["입장A", "입장B"], key=f"target_{i}")
            q_type = st.selectbox(f"질문 {i} 유형", ["사실", "추론", "비판"], key=f"type_{i}")
            q_content = st.text_area(f"질문 {i} 내용", placeholder="질문 내용을 입력하세요...", key=f"content_{i}")
            
            if q_content.strip():
                questions_to_submit.append({
                    "대상": q_target,
                    "유형": q_type,
                    "내용": q_content
                })

    # 제출 버튼
    if st.button("내용 제출하기"):
        if not name or not student_id:
            st.error("이름과 학번을 입력해주세요.")
        elif len(questions_to_submit) == 0:
            st.error("최소 1개 이상의 질문을 작성해야 합니다.")
        else:
            try:
                # 시트에서 기존 데이터 읽기
                existing_data = conn.read(worksheet="Sheet1")
                
                # 새 데이터 행 생성 (질문 개수만큼 생성)
                new_rows = []
                for q in questions_to_submit:
                    new_rows.append({
                        "주차(Issue)": current_issue,
                        "이름": name,
                        "학번": student_id,
                        "사전투표": pre_vote,
                        "사후투표": post_vote,
                        "질문유형": q["유형"],
                        "질문내용": q["내용"],
                        "대상입장": q["대상"]
                    })
                
                new_df = pd.DataFrame(new_rows)
                updated_df = pd.concat([existing_data, new_df], ignore_index=True)
                
                # 시트 업데이트
                conn.update(worksheet="Sheet1", data=updated_df)
                st.success(f"성공적으로 제출되었습니다! (제출된 질문: {len(questions_to_submit)}개)")
                st.balloons()
            except Exception as e:
                st.error(f"오류가 발생했습니다: {e}")

# --- 데이터 전처리 (결과 및 질문 보기를 위해) ---
try:
    all_df = conn.read(worksheet="Sheet1")
    # 현재 이슈에 해당하는 데이터만 필터링
    issue_df = all_df[all_df["주차(Issue)"] == current_issue]
except:
    issue_df = pd.DataFrame()

# --- Tab 2: 투표 결과 ---
with tab2:
    st.header(f"📊 {current_issue} 실시간 투표 현황")
    
    if not issue_df.empty:
        # 한 학생이 여러 질문을 해도 투표는 1번만 집계되도록 중복 제거
        unique_votes = issue_df.drop_duplicates(subset=["이름", "학번"])
        
        col_pre, col_post = st.columns(2)
        
        with col_pre:
            st.subheader("발표 전 명단")
            pre_a = unique_votes[unique_votes["사전투표"] == "입장A"]["이름"].tolist()
            pre_b = unique_votes[unique_votes["사전투표"] == "입장B"]["이름"].tolist()
            st.write(f"**입장A ({len(pre_a)}명):** {', '.join(pre_a)}")
            st.write(f"**입장B ({len(pre_b)}명):** {', '.join(pre_b)}")

        with col_post:
            st.subheader("발표 후 명단")
            post_a = unique_votes[unique_votes["사후투표"] == "입장A"]["이름"].tolist()
            post_b = unique_votes[unique_votes["사후투표"] == "입장B"]["이름"].tolist()
            st.write(f"**입장A ({len(post_a)}명):** {', '.join(post_a)}")
            st.write(f"**입장B ({len(post_b)}명):** {', '.join(post_b)}")

        st.divider()
        st.subheader("🔄 입장이 바뀐 학생")
        
        # 입장 변화 감지 함수
        def highlight_changes(row):
            if row["사전투표"] != row["사후투표"]:
                return ['background-color: #FFD700; color: black; font-weight: bold'] * len(row)
            return [''] * len(row)

        changed_df = unique_votes[unique_votes["사전투표"] != unique_votes["사후투표"]]
        if not changed_df.empty:
            st.write(f"총 {len(changed_df)}명의 생각이 바뀌었습니다.")
            display_df = unique_votes[["이름", "학번", "사전투표", "사후투표"]]
            st.dataframe(display_df.style.apply(highlight_changes, axis=1), use_container_width=True)
        else:
            st.write("아직 입장이 바뀐 학생이 없습니다.")
    else:
        st.info("데이터가 없습니다.")

# --- Tab 3: 질문 모아보기 ---
with tab3:
    st.header(f"❓ {current_issue} 질문 리스트")
    
    if not issue_df.empty:
        for side in ["입장A", "입장B"]:
            st.subheader(f"📍 {side}를 향한 질문")
            side_df = issue_df[issue_df["대상입장"] == side]
            
            col_f, col_i, col_c = st.columns(3)
            
            with col_f:
                st.info("**사실 질문**")
                for _, row in side_df[side_df["질문유형"] == "사실"].iterrows():
                    st.markdown(f"- {row['질문내용']} `({row['이름']})` ")
            
            with col_i:
                st.warning("**추론 질문**")
                for _, row in side_df[side_df["질문유형"] == "추론"].iterrows():
                    st.markdown(f"- {row['질문내용']} `({row['이름']})` ")
            
            with col_c:
                st.error("**비판 질문**")
                for _, row in side_df[side_df["질문유형"] == "비판"].iterrows():
                    st.markdown(f"- {row['질문내용']} `({row['이름']})` ")
            st.divider()
    else:
        st.info("등록된 질문이 없습니다.")