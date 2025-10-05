"""
=============================================================================
능동형 AI 교사 - 이미지 기반 대화형 학습 앱
=============================================================================
기능:
- AI가 먼저 이미지를 보고 질문합니다
- 학생(사용자)이 답변합니다
- AI가 답변을 평가하고 피드백을 제공합니다
- 격려하고 칭찬하며 가르칩니다

작성일: 2025
=============================================================================
"""

import streamlit as st
from openai import OpenAI
import base64

# =============================================================================
# 1. 기본 설정
# =============================================================================

st.set_page_config(
    page_title="AI 교사",
    page_icon="👨‍🏫",
    layout="wide"
)

st.title("👨‍🏫 능동형 AI 교사")
st.caption("AI가 질문하고, 여러분이 답하는 대화형 학습")

# =============================================================================
# 2. API 키 가져오기
# =============================================================================

try:
    DID_KEY = st.secrets["DID_API_KEY"]
    OPENAI_KEY = st.secrets["OPENAI_API_KEY"]
except:
    st.error("⚠️ API 키를 설정하세요 (Streamlit Cloud Secrets)")
    st.stop()

# =============================================================================
# 3. 데이터 저장 공간
# =============================================================================

# 대화 기록
if 'messages' not in st.session_state:
    st.session_state.messages = []

# 현재 이미지
if 'current_image' not in st.session_state:
    st.session_state.current_image = None

# 이미지 데이터 (base64)
if 'image_base64' not in st.session_state:
    st.session_state.image_base64 = None

# 이미지 이름 (새 이미지 감지용)
if 'current_image_name' not in st.session_state:
    st.session_state.current_image_name = None

# AI 질문 대기 상태
if 'waiting_for_answer' not in st.session_state:
    st.session_state.waiting_for_answer = False

# =============================================================================
# 4. 이미지 처리 함수
# =============================================================================

def encode_image(image_file):
    """
    업로드된 이미지를 base64로 인코딩
    GPT Vision API 전송용 형식으로 변환
    
    Args:
        image_file: 업로드된 파일 객체
        
    Returns:
        str: base64 인코딩된 이미지 문자열
    """
    return base64.b64encode(image_file.read()).decode('utf-8')

# =============================================================================
# 5. OpenAI GPT 함수 (능동형 교사 모드)
# =============================================================================

def generate_first_question(image_base64):
    """
    이미지를 보고 AI가 첫 번째 질문을 생성합니다
    
    Args:
        image_base64: base64 인코딩된 이미지
        
    Returns:
        str: AI의 질문
    """
    client = OpenAI(api_key=OPENAI_KEY)
    
    system_msg = """당신은 친절하고 호기심 많은 AI 교사입니다.

【역할】
학생들의 관찰력과 사고력을 키우는 질문을 합니다.

【질문 스타일】
- 개방형 질문 (예: "무엇이 보이나요?")
- 흥미를 유발하는 질문
- 쉬운 질문부터 시작

【주의사항】
- 질문 1개만 하세요
- 친근하게 이모지 사용
- 답을 유도하지 마세요
"""
    
    messages = [
        {"role": "system", "content": system_msg},
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": "이 이미지를 보고 학생에게 관찰을 유도하는 질문을 1개 해주세요."
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{image_base64}",
                        "detail": "auto"
                    }
                }
            ]
        }
    ]
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            max_tokens=200
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"❌ 오류: {str(e)}"


def give_feedback(user_answer, image_base64, conversation_history):
    """
    학생의 답변을 평가하고 피드백을 제공합니다
    
    Args:
        user_answer: 학생의 답변
        image_base64: 이미지 데이터
        conversation_history: 이전 대화 기록
        
    Returns:
        str: AI의 피드백
    """
    client = OpenAI(api_key=OPENAI_KEY)
    
    system_msg = """당신은 격려를 잘하는 AI 교사입니다.

【피드백 원칙】
1. 긍정적으로 시작: 항상 칭찬부터
2. 정확성 확인: 답변이 맞는지 평가
3. 추가 정보 제공: 더 알려줄 것 공유
4. 다음 질문: 자연스럽게 다음 질문으로 이어가기

【피드백 방법】
- 정답: "맞아요! 👍", "정확해요! ✨", "잘 관찰했어요! 🎯"
- 부분 정답: "좋은 관찰이에요! 그런데..."
- 오답: "흥미로운 생각이네요. 다시 한번 보면..."

【주의사항】
- 따뜻하고 격려하는 톤
- 구체적인 피드백
- 다음 질문은 자연스럽게
"""
    
    # 메시지 구성
    messages = [{"role": "system", "content": system_msg}]
    
    # 이전 대화 기록 추가
    for msg in conversation_history:
        if msg["role"] == "assistant":
            # AI 메시지
            messages.append({
                "role": "assistant",
                "content": msg["content"]
            })
        else:
            # 사용자 메시지 (이미지 포함)
            messages.append({
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": msg["content"]
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_base64}"
                        }
                    }
                ]
            })
    
    # 현재 답변 추가
    messages.append({
        "role": "user",
        "content": [
            {
                "type": "text",
                "text": user_answer
            },
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{image_base64}"
                }
            }
        ]
    })
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            max_tokens=500
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"❌ 오류: {str(e)}"

# =============================================================================
# 6. 사이드바 - 이미지 업로드
# =============================================================================

st.sidebar.header("🖼️ 학습 자료")

uploaded_file = st.sidebar.file_uploader(
    "이미지를 업로드하세요",
    type=['jpg', 'jpeg', 'png'],
    help="AI가 이미지를 보고 질문합니다"
)

if uploaded_file is not None:
    # 새 이미지인지 확인
    is_new_image = (
        st.session_state.current_image_name != uploaded_file.name
    )
    
    if is_new_image:
        # 새 이미지 처리
        st.session_state.current_image = uploaded_file
        st.session_state.current_image_name = uploaded_file.name
        
        # Base64 인코딩
        uploaded_file.seek(0)
        st.session_state.image_base64 = encode_image(uploaded_file)
        
        # 대화 초기화
        st.session_state.messages = []
        
        # AI가 첫 질문 생성
        with st.spinner("🤔 AI가 질문을 준비 중..."):
            uploaded_file.seek(0)
            first_question = generate_first_question(
                st.session_state.image_base64
            )
            
            # AI 질문을 대화에 추가
            st.session_state.messages.append({
                "role": "assistant",
                "content": first_question
            })
            
            st.session_state.waiting_for_answer = True
    
    # 이미지 미리보기
    uploaded_file.seek(0)
    st.sidebar.image(
        uploaded_file,
        caption="학습 이미지",
        use_container_width=True
    )
    st.sidebar.success("✅ 이미지 로드됨")

else:
    st.session_state.current_image = None
    st.session_state.image_base64 = None
    st.session_state.current_image_name = None
    st.sidebar.info("📤 이미지를 업로드하세요")

st.sidebar.markdown("---")

# 대화 초기화 버튼
if st.sidebar.button("🔄 새로운 대화 시작"):
    st.session_state.messages = []
    st.session_state.waiting_for_answer = False
    
    # 이미지가 있으면 새 질문 생성
    if st.session_state.image_base64:
        with st.spinner("🤔 새로운 질문 준비 중..."):
            new_question = generate_first_question(
                st.session_state.image_base64
            )
            st.session_state.messages.append({
                "role": "assistant",
                "content": new_question
            })
            st.session_state.waiting_for_answer = True
    st.rerun()

st.sidebar.markdown("---")

# 통계 표시
st.sidebar.subheader("📊 학습 현황")
total_qa = len([m for m in st.session_state.messages if m["role"] == "user"])
st.sidebar.metric("질문/답변 수", total_qa)

# =============================================================================
# 7. 메인 화면 - 레이아웃
# =============================================================================

# 2열 레이아웃
col1, col2 = st.columns([1, 1])

# 왼쪽: 이미지 표시
with col1:
    st.subheader("🖼️ 학습 이미지")
    if st.session_state.current_image:
        st.session_state.current_image.seek(0)
        st.image(
            st.session_state.current_image,
            use_container_width=True
        )
    else:
        st.info("👈 왼쪽 사이드바에서 이미지를 업로드하세요")
        st.markdown("""
        ### 📚 사용 방법
        
        1. **이미지 업로드**
           - 왼쪽 사이드바에서 이미지 선택
        
        2. **AI 질문 확인**
           - AI가 자동으로 질문합니다
        
        3. **답변 입력**
           - 오른쪽 채팅창에서 답변
        
        4. **피드백 받기**
           - AI가 평가하고 다음 질문
        """)

# 오른쪽: 대화
with col2:
    st.subheader("💬 대화형 학습")
    
    # 대화 기록 표시
    chat_container = st.container(height=400)
    with chat_container:
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])
    
    # 안내 메시지
    if not st.session_state.messages:
        st.info("👈 이미지를 업로드하면 AI가 질문을 시작합니다")

st.markdown("---")

# =============================================================================
# 8. 사용자 입력 처리
# =============================================================================

# 입력창 활성화 조건
can_input = (
    st.session_state.image_base64 is not None and
    len(st.session_state.messages) > 0
)

if can_input:
    user_input = st.chat_input("답변을 입력하세요...")
    
    if user_input:
        # 사용자 답변 추가
        st.session_state.messages.append({
            "role": "user",
            "content": user_input
        })
        
        # AI 피드백 생성
        with st.spinner("🤔 피드백 준비 중..."):
            feedback = give_feedback(
                user_input,
                st.session_state.image_base64,
                st.session_state.messages
            )
        
        # AI 피드백 추가
        st.session_state.messages.append({
            "role": "assistant",
            "content": feedback
        })
        
        st.rerun()

# =============================================================================
# 9. 도움말
# =============================================================================

st.markdown("---")

with st.expander("💡 교육 팁"):
    st.markdown("""
    ### 👨‍🏫 이렇게 활용하세요
    
    **학생용:**
    - 이미지를 자세히 관찰하세요
    - 솔직하게 답변하세요
    - AI의 피드백을 읽고 배우세요
    
    **교사용:**
    - 다양한 이미지로 학습 자료 제공
    - 학생의 관찰력 향상에 활용
    - 대화형 학습 경험 제공
    
    ---
    
    ### 🎯 학습 효과
    
    - ✅ 관찰력 향상
    - ✅ 사고력 발달
    - ✅ 즉각적 피드백
    - ✅ 자기주도 학습
    - ✅ 흥미 유발
    
    ---
    
    ### 💬 AI 질문 예시
    
    - "이 이미지에서 무엇이 보이나요?"
    - "몇 개나 보이나요?"
    - "색깔이 어떤가요?"
    - "신선해 보이나요?"
    - "어떤 느낌이 드나요?"
    """)

# =============================================================================
# 끝
# =============================================================================
