"""
=============================================================================
D-ID 아바타 + OpenAI GPT 대화 앱
- D-ID: 아바타 화면, 음성
- OpenAI: 대화 생성
- 화면 객체 인식 가능
=============================================================================
"""

import streamlit as st
import requests
from openai import OpenAI

# =============================================================================
# 1. 기본 설정
# =============================================================================

st.set_page_config(page_title="아바타 채팅", page_icon="🤖")
st.title("🤖 D-ID 아바타 대화")

# =============================================================================
# 2. API 키 가져오기
# =============================================================================

# Streamlit Cloud의 Secrets에서 API 키 가져오기
try:
    DID_KEY = st.secrets["DID_API_KEY"]
    OPENAI_KEY = st.secrets["OPENAI_API_KEY"]
except:
    st.error("⚠️ API 키를 설정하세요 (Streamlit Cloud Secrets)")
    st.stop()

# =============================================================================
# 3. 데이터 저장 공간
# =============================================================================

# 처음 실행시 초기화
if 'messages' not in st.session_state:
    st.session_state.messages = []  # 대화 기록

if 'objects' not in st.session_state:
    st.session_state.objects = []  # 화면 객체들

# =============================================================================
# 4. OpenAI GPT 함수
# =============================================================================

def ask_gpt(user_text):
    """
    사용자 질문 → GPT에게 물어보기
    화면 객체 정보도 함께 전달
    """
    client = OpenAI(api_key=OPENAI_KEY)
    
    # 시스템 메시지 만들기
    system_msg = "당신은 친절한 AI입니다."
    
    # 화면에 객체가 있으면 알려주기
    if st.session_state.objects:
        objects_text = ", ".join(st.session_state.objects)
        system_msg += f"\n\n【화면 정보】"
        system_msg += f"\n현재 화면에 보이는 객체: {objects_text}"
        system_msg += f"\n\n【중요 규칙】"
        system_msg += f"\n1. 위치 정보(왼쪽, 오른쪽, 위, 아래)는 제공되지 않았으므로 절대 언급하지 마세요."
        system_msg += f"\n2. 리스트에 있는 객체만 정확히 말하세요."
        system_msg += f"\n3. 없는 정보는 만들어내지 마세요."
    else:
        system_msg += "\n\n현재 화면에 객체가 없습니다."
    
    # GPT에게 질문하기
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_text}
        ]
    )
    
    return response.choices[0].message.content

# =============================================================================
# 5. 사이드바 - 화면 객체 관리
# =============================================================================

st.sidebar.header("🖼️ 화면 객체")
st.sidebar.caption("화면에 있는 물건을 추가하세요")

# 객체 추가
new_object = st.sidebar.text_input("객체 이름 (예: 사과)")
if st.sidebar.button("➕ 추가"):
    if new_object:
        st.session_state.objects.append(new_object)

# 현재 객체 보여주기
if st.session_state.objects:
    for obj in st.session_state.objects:
        st.sidebar.write(f"• {obj}")
else:
    st.sidebar.info("객체 없음")

# 전체 삭제
if st.sidebar.button("🗑️ 모두 삭제"):
    st.session_state.objects = []
    st.rerun()

# =============================================================================
# 6. 대화 화면
# =============================================================================

# 이전 대화 보여주기
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# =============================================================================
# 7. 사용자 입력 받기
# =============================================================================

user_input = st.chat_input("메시지를 입력하세요...")

if user_input:
    # 1. 사용자 메시지 저장 & 표시
    st.session_state.messages.append({
        "role": "user",
        "content": user_input
    })
    
    with st.chat_message("user"):
        st.write(user_input)
    
    # 2. GPT에게 물어보기
    with st.chat_message("assistant"):
        with st.spinner("생각 중..."):
            answer = ask_gpt(user_input)
        st.write(answer)
    
    # 3. AI 답변 저장
    st.session_state.messages.append({
        "role": "assistant",
        "content": answer
    })
    
    st.rerun()

# =============================================================================
# 8. 안내 메시지
# =============================================================================

st.markdown("---")
st.info("""
💡 **사용 방법:**
1. 왼쪽에서 화면 객체 추가 (예: 사과, 귤)
2. 아래에서 대화 시작
3. GPT가 화면 객체를 인식합니다!

📌 **D-ID 아바타 연결은 다음 단계에서 추가됩니다.**
""")

# =============================================================================
# 끝
# =============================================================================
