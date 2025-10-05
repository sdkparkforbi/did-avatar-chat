"""
=============================================================================
D-ID 아바타 + OpenAI GPT 대화 앱 (이미지 인식 포함)
- 이미지 업로드 가능
- GPT-4o Vision으로 이미지 분석
- 이미지 보면서 대화
=============================================================================
"""

import streamlit as st
import requests
from openai import OpenAI
import base64
from io import BytesIO

# =============================================================================
# 1. 기본 설정
# =============================================================================

st.set_page_config(page_title="아바타 채팅", page_icon="🤖", layout="wide")
st.title("🤖 AI 비전 아바타 대화")

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

if 'messages' not in st.session_state:
    st.session_state.messages = []  # 대화 기록

if 'objects' not in st.session_state:
    st.session_state.objects = []  # 수동 추가 객체

if 'current_image' not in st.session_state:
    st.session_state.current_image = None  # 현재 이미지

if 'image_base64' not in st.session_state:
    st.session_state.image_base64 = None  # 이미지 데이터 (GPT 전송용)

# =============================================================================
# 4. 이미지 처리 함수
# =============================================================================

def encode_image(image_file):
    """
    업로드된 이미지를 base64로 인코딩
    GPT Vision API에 전송하기 위한 형식으로 변환
    """
    return base64.b64encode(image_file.read()).decode('utf-8')

# =============================================================================
# 5. OpenAI GPT 함수 (이미지 지원)
# =============================================================================

def ask_gpt_with_image(user_text, image_base64=None):
    """
    사용자 질문 → GPT에게 물어보기
    이미지가 있으면 함께 전달
    
    Args:
        user_text: 사용자 질문
        image_base64: 이미지 데이터 (있으면)
    """
    client = OpenAI(api_key=OPENAI_KEY)
    
    # 시스템 메시지
    system_msg = "당신은 정직하고 친절한 AI 어시스턴트입니다."
    
    # 수동 추가 객체 정보
    if st.session_state.objects:
        objects_text = ", ".join(st.session_state.objects)
        system_msg += f"\n\n추가 정보: 화면에 {objects_text}도 있습니다."
    
    # 메시지 구성
    if image_base64:
        # 이미지가 있을 때 - GPT-4o Vision 사용
        messages = [
            {"role": "system", "content": system_msg},
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": user_text
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_base64}",
                            "detail": "auto"  # 자동으로 적절한 해상도 선택
                        }
                    }
                ]
            }
        ]
        model = "gpt-4o"  # Vision 지원 모델
        
    else:
        # 이미지 없을 때 - 일반 GPT
        messages = [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_text}
        ]
        model = "gpt-4o-mini"  # 저렴한 모델
    
    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=500
        )
        return response.choices[0].message.content
        
    except Exception as e:
        return f"❌ 오류 발생: {str(e)}"

# =============================================================================
# 6. 사이드바 - 이미지 업로드
# =============================================================================

st.sidebar.header("🖼️ 이미지 업로드")

uploaded_file = st.sidebar.file_uploader(
    "이미지를 선택하세요",
    type=['jpg', 'jpeg', 'png'],
    help="JPG, PNG 형식 지원"
)

if uploaded_file is not None:
    # 이미지 저장
    st.session_state.current_image = uploaded_file
    
    # Base64 인코딩 (GPT에 전송하기 위해)
    uploaded_file.seek(0)  # 파일 포인터 처음으로
    st.session_state.image_base64 = encode_image(uploaded_file)
    
    # 이미지 미리보기
    uploaded_file.seek(0)
    st.sidebar.image(uploaded_file, caption="업로드된 이미지", use_container_width=True)
    st.sidebar.success("✅ 이미지 로드됨")
    
    # 이미지 분석 버튼
    if st.sidebar.button("🔍 이미지 분석하기"):
        with st.spinner("이미지 분석 중..."):
            analysis = ask_gpt_with_image(
                "이 이미지에 무엇이 보이나요? 자세히 설명해주세요.",
                st.session_state.image_base64
            )
            st.sidebar.write("**분석 결과:**")
            st.sidebar.info(analysis)

else:
    st.session_state.current_image = None
    st.session_state.image_base64 = None
    st.sidebar.info("이미지를 업로드하세요")

st.sidebar.markdown("---")

# =============================================================================
# 7. 사이드바 - 추가 객체 관리
# =============================================================================

st.sidebar.subheader("➕ 추가 객체")
st.sidebar.caption("텍스트로 객체 추가 (선택사항)")

new_object = st.sidebar.text_input("객체 이름 입력")
if st.sidebar.button("추가"):
    if new_object:
        st.session_state.objects.append(new_object)
        st.sidebar.success(f"✅ '{new_object}' 추가됨")

# 현재 객체 목록
if st.session_state.objects:
    st.sidebar.write("**추가된 객체:**")
    for obj in st.session_state.objects:
        st.sidebar.write(f"• {obj}")
    
    if st.sidebar.button("🗑️ 객체 전체 삭제"):
        st.session_state.objects = []
        st.rerun()

st.sidebar.markdown("---")

# 대화 초기화
if st.sidebar.button("💬 대화 초기화"):
    st.session_state.messages = []
    st.rerun()

# =============================================================================
# 8. 메인 화면 - 레이아웃
# =============================================================================

# 2열 레이아웃
col1, col2 = st.columns([1, 1])

# 왼쪽: 이미지 표시
with col1:
    st.subheader("🖼️ 이미지")
    if st.session_state.current_image:
        st.session_state.current_image.seek(0)
        st.image(st.session_state.current_image, use_container_width=True)
    else:
        st.info("왼쪽 사이드바에서 이미지를 업로드하세요")

# 오른쪽: 대화
with col2:
    st.subheader("💬 대화")
    
    # 이전 대화 표시
    chat_container = st.container(height=400)
    with chat_container:
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])

st.markdown("---")

# =============================================================================
# 9. 사용자 입력
# =============================================================================

user_input = st.chat_input("메시지를 입력하세요...")

if user_input:
    # 사용자 메시지 추가
    st.session_state.messages.append({
        "role": "user",
        "content": user_input
    })
    
    # GPT 응답 받기 (이미지 포함 여부에 따라)
    with st.spinner("🤔 생각 중..."):
        if st.session_state.image_base64:
            # 이미지가 있으면 함께 전송
            answer = ask_gpt_with_image(
                user_input,
                st.session_state.image_base64
            )
        else:
            # 이미지 없으면 텍스트만
            answer = ask_gpt_with_image(user_input, None)
    
    # AI 응답 추가
    st.session_state.messages.append({
        "role": "assistant",
        "content": answer
    })
    
    st.rerun()

# =============================================================================
# 10. 사용 안내
# =============================================================================

st.markdown("---")

with st.expander("📖 사용 방법"):
    st.markdown("""
    ### 🎯 기능
    
    1. **이미지 업로드**
       - 왼쪽 사이드바에서 이미지 선택
       - JPG, PNG 지원
    
    2. **이미지 분석**
       - "🔍 이미지 분석하기" 버튼 클릭
       - AI가 자동으로 이미지 설명
    
    3. **이미지 대화**
       - 채팅창에서 질문
       - "이게 뭐야?"
       - "색깔이 어때?"
       - "몇 개 보여?"
    
    4. **추가 객체**
       - 텍스트로 추가 정보 입력 가능
    
    ---
    
    ### 💡 예시 질문
    
    - "이미지에 뭐가 보여?"
    - "이 과일 이름이 뭐야?"
    - "색깔을 설명해줘"
    - "신선해 보여?"
    - "몇 개나 있어?"
    
    ---
    
    ### 💰 비용 참고
    
    - 이미지 있을 때: GPT-4o (고급 모델)
    - 이미지 없을 때: GPT-4o-mini (저렴)
    """)

# =============================================================================
# 끝
# =============================================================================
