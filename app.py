"""
=============================================================================
능동형 AI 교사 + D-ID 실시간 음성 대화
=============================================================================
"""

import streamlit as st
import streamlit.components.v1 as components
from openai import OpenAI
import base64
import requests
import json

# =============================================================================
# 1. 기본 설정
# =============================================================================

st.set_page_config(
    page_title="AI 교사 + 음성",
    page_icon="🤖",
    layout="wide"
)

# =============================================================================
# 2. API 키 (개선된 처리)
# =============================================================================

try:
    # D-ID API 키 처리
    DID_KEY_RAW = st.secrets["DID_API_KEY"]
    
    # 이미 Base64 인코딩되어 있는지 확인
    if ':' in DID_KEY_RAW:
        # Raw 형식 (email:key) → Base64 인코딩 필요
        DID_KEY_ENCODED = base64.b64encode(DID_KEY_RAW.encode()).decode()
    else:
        # 이미 인코딩된 형식
        DID_KEY_ENCODED = DID_KEY_RAW
    
    OPENAI_KEY = st.secrets["OPENAI_API_KEY"]
    
    st.sidebar.success("✅ API 키 로드 완료")
    
except Exception as e:
    st.error(f"API 키 오류: {str(e)}")
    st.stop()

# =============================================================================
# 3. 세션 상태
# =============================================================================

if 'messages' not in st.session_state:
    st.session_state.messages = []

if 'current_image' not in st.session_state:
    st.session_state.current_image = None

if 'image_base64' not in st.session_state:
    st.session_state.image_base64 = None

if 'screen_objects' not in st.session_state:
    st.session_state.screen_objects = []

# =============================================================================
# 4. 함수들
# =============================================================================

def encode_image(image_file):
    """이미지를 base64로 인코딩"""
    return base64.b64encode(image_file.read()).decode('utf-8')

def ask_gpt_with_image(user_text, image_base64=None):
    """GPT에게 질문 (이미지 포함 가능)"""
    client = OpenAI(api_key=OPENAI_KEY)
    
    system_msg = "당신은 정직하고 친절한 AI 교사입니다."
    
    if st.session_state.screen_objects:
        objects_text = ", ".join(st.session_state.screen_objects)
        system_msg += f"\n\n현재 화면에 보이는 객체: {objects_text}"
    
    if image_base64:
        messages = [
            {"role": "system", "content": system_msg},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": user_text},
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
        model = "gpt-4o"
    else:
        messages = [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_text}
        ]
        model = "gpt-4o-mini"
    
    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=500
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"오류: {str(e)}"

# =============================================================================
# 5. D-ID WebRTC HTML/JavaScript (수정됨)
# =============================================================================

def create_did_webrtc_component(did_key_encoded, openai_key):
    """D-ID WebRTC 컴포넌트 생성"""
    
    screen_objects_json = json.dumps(st.session_state.screen_objects)
    image_base64 = st.session_state.image_base64 or ""
    
    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ margin: 0; padding: 20px; background: #f5f5f5; }}
            #video-container {{ 
                text-align: center; 
                background: white;
                border-radius: 10px;
                padding: 20px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            }}
            video {{ 
                width: 100%; 
                max-width: 640px; 
                border-radius: 10px;
                background: #000;
            }}
            .status {{
                margin-top: 10px;
                padding: 10px;
                background: #e3f2fd;
                border-radius: 5px;
                font-size: 14px;
            }}
            .controls {{
                margin-top: 20px;
            }}
            button {{
                padding: 12px 24px;
                margin: 5px;
                background: #2196F3;
                color: white;
                border: none;
                border-radius: 5px;
                cursor: pointer;
                font-size: 16px;
            }}
            button:hover {{ background: #1976D2; }}
            button:disabled {{ background: #ccc; cursor: not-allowed; }}
            .error {{ background: #ffebee; color: #c62828; }}
        </style>
    </head>
    <body>
        <div id="video-container">
            <h3>D-ID 아바타</h3>
            <video id="video-element" autoplay playsinline></video>
            <div class="status" id="status">준비 중...</div>
            
            <div class="controls">
                <button id="connect-btn" onclick="connectDID()">연결 시작</button>
                <button id="disconnect-btn" onclick="disconnectDID()" disabled>연결 종료</button>
            </div>
        </div>

        <script>
            // API 키 (이미 Base64 인코딩된 상태)
            const DID_API_KEY_ENCODED = '{did_key_encoded}';
            const OPENAI_API_KEY = '{openai_key}';
            const SCREEN_OBJECTS = {screen_objects_json};
            const IMAGE_BASE64 = '{image_base64}';
            
            let peerConnection;
            let streamId;
            let sessionId;
            let agentId;
            
            function updateStatus(message, isError = false) {{
                const statusEl = document.getElementById('status');
                statusEl.textContent = message;
                statusEl.className = isError ? 'status error' : 'status';
                console.log(message);
            }}
            
            // D-ID Agent 생성
            async function createAgent() {{
                updateStatus('Agent 생성 중...');
                
                try {{
                    const response = await fetch('https://api.d-id.com/agents', {{
                        method: 'POST',
                        headers: {{
                            'Authorization': `Basic ${{DID_API_KEY_ENCODED}}`,
                            'Content-Type': 'application/json'
                        }},
                        body: JSON.stringify({{
                            presenter: {{
                                type: 'talk',
                                voice: {{
                                    type: 'microsoft',
                                    voice_id: 'ko-KR-SunHiNeural'
                                }},
                                source_url: 'https://create-images-results.d-id.com/DefaultPresenters/Emma_f/v1_image.jpeg'
                            }},
                            preview_name: 'Emma'
                        }})
                    }});
                    
                    if (!response.ok) {{
                        const errorData = await response.json();
                        throw new Error(`Agent 생성 실패: ${{response.status}} - ${{JSON.stringify(errorData)}}`);
                    }}
                    
                    const data = await response.json();
                    console.log('Agent 생성 성공:', data);
                    return data.id;
                    
                }} catch (error) {{
                    console.error('Agent 생성 오류:', error);
                    throw error;
                }}
            }}
            
            // D-ID 스트림 생성
            async function createStream(agentId) {{
                updateStatus('스트림 생성 중...');
                
                try {{
                    const response = await fetch(`https://api.d-id.com/agents/${{agentId}}/streams`, {{
                        method: 'POST',
                        headers: {{
                            'Authorization': `Basic ${{DID_API_KEY_ENCODED}}`,
                            'Content-Type': 'application/json'
                        }},
                        body: JSON.stringify({{
                            source_url: 'https://create-images-results.d-id.com/DefaultPresenters/Emma_f/v1_image.jpeg'
                        }})
                    }});
                    
                    if (!response.ok) {{
                        const errorData = await response.json();
                        throw new Error(`스트림 생성 실패: ${{response.status}} - ${{JSON.stringify(errorData)}}`);
                    }}
                    
                    const data = await response.json();
                    console.log('스트림 생성 성공:', data);
                    
                    streamId = data.id;
                    sessionId = data.session_id;
                    
                    return data;
                    
                }} catch (error) {{
                    console.error('스트림 생성 오류:', error);
                    throw error;
                }}
            }}
            
            // WebRTC 연결
            async function setupWebRTC() {{
                updateStatus('WebRTC 연결 중...');
                
                try {{
                    peerConnection = new RTCPeerConnection({{
                        iceServers: [
                            {{ urls: 'stun:stun.l.google.com:19302' }},
                            {{ urls: 'stun:stun1.l.google.com:19302' }}
                        ]
                    }});
                    
                    // Track 수신
                    peerConnection.ontrack = (event) => {{
                        console.log('Track 수신:', event);
                        const videoElement = document.getElementById('video-element');
                        videoElement.srcObject = event.streams[0];
                        updateStatus('✅ 연결 완료! 아바타 준비됨');
                    }};
                    
                    // 연결 상태 모니터링
                    peerConnection.onconnectionstatechange = () => {{
                        console.log('Connection state:', peerConnection.connectionState);
                        if (peerConnection.connectionState === 'connected') {{
                            updateStatus('✅ WebRTC 연결됨');
                        }}
                    }};
                    
                    // ICE candidate 처리
                    peerConnection.onicecandidate = async (event) => {{
                        if (event.candidate) {{
                            console.log('ICE candidate:', event.candidate);
                            
                            await fetch(`https://api.d-id.com/agents/${{agentId}}/streams/${{streamId}}/ice`, {{
                                method: 'POST',
                                headers: {{
                                    'Authorization': `Basic ${{DID_API_KEY_ENCODED}}`,
                                    'Content-Type': 'application/json'
                                }},
                                body: JSON.stringify({{
                                    candidate: event.candidate.candidate,
                                    sdpMLineIndex: event.candidate.sdpMLineIndex,
                                    session_id: sessionId
                                }})
                            }});
                        }}
                    }};
                    
                    // SDP Offer 받기
                    const sdpResponse = await fetch(`https://api.d-id.com/agents/${{agentId}}/streams/${{streamId}}/sdp`, {{
                        method: 'POST',
                        headers: {{
                            'Authorization': `Basic ${{DID_API_KEY_ENCODED}}`,
                            'Content-Type': 'application/json'
                        }},
                        body: JSON.stringify({{
                            session_id: sessionId
                        }})
                    }});
                    
                    if (!sdpResponse.ok) {{
                        throw new Error('SDP Offer 실패');
                    }}
                    
                    const {{ sdp, type }} = await sdpResponse.json();
                    console.log('SDP Offer 수신');
                    
                    await peerConnection.setRemoteDescription({{ type, sdp }});
                    
                    // Answer 생성
                    const answer = await peerConnection.createAnswer();
                    await peerConnection.setLocalDescription(answer);
                    console.log('SDP Answer 생성');
                    
                    // Answer 전송
                    await fetch(`https://api.d-id.com/agents/${{agentId}}/streams/${{streamId}}/sdp`, {{
                        method: 'PATCH',
                        headers: {{
                            'Authorization': `Basic ${{DID_API_KEY_ENCODED}}`,
                            'Content-Type': 'application/json'
                        }},
                        body: JSON.stringify({{
                            answer: {{
                                type: answer.type,
                                sdp: answer.sdp
                            }},
                            session_id: sessionId
                        }})
                    }});
                    
                    console.log('SDP Answer 전송 완료');
                    
                }} catch (error) {{
                    console.error('WebRTC 설정 오류:', error);
                    throw error;
                }}
            }}
            
            // 연결 시작
            async function connectDID() {{
                try {{
                    document.getElementById('connect-btn').disabled = true;
                    updateStatus('연결 시작...');
                    
                    // 1. Agent 생성
                    agentId = await createAgent();
                    updateStatus(`Agent 생성 완료 (ID: ${{agentId.substring(0, 8)}}...)`);
                    
                    // 2. 스트림 생성
                    await createStream(agentId);
                    updateStatus('스트림 생성 완료');
                    
                    // 3. WebRTC 연결
                    await setupWebRTC();
                    
                    document.getElementById('disconnect-btn').disabled = false;
                    updateStatus('✅ 모든 연결 완료!');
                    
                }} catch (error) {{
                    console.error('연결 오류:', error);
                    updateStatus('오류: ' + error.message, true);
                    document.getElementById('connect-btn').disabled = false;
                }}
            }}
            
            // 연결 종료
            function disconnectDID() {{
                if (peerConnection) {{
                    peerConnection.close();
                    peerConnection = null;
                }}
                
                const videoElement = document.getElementById('video-element');
                if (videoElement.srcObject) {{
                    videoElement.srcObject.getTracks().forEach(track => track.stop());
                    videoElement.srcObject = null;
                }}
                
                updateStatus('연결 종료됨');
                document.getElementById('connect-btn').disabled = false;
                document.getElementById('disconnect-btn').disabled = true;
            }}
        </script>
    </body>
    </html>
    """
    
    return html_code

# =============================================================================
# 6. UI - 레이아웃
# =============================================================================

st.title("🤖 AI 교사 + 실시간 음성")

# 사이드바 정보
with st.sidebar:
    st.header("ℹ️ 정보")
    st.write(f"D-ID 키 형식: {'Raw' if ':' in DID_KEY_RAW else 'Encoded'}")
    st.write(f"인코딩된 키 길이: {len(DID_KEY_ENCODED)}")

# 2열 레이아웃
col1, col2 = st.columns([1, 1])

# 왼쪽: 이미지 & 객체
with col1:
    st.subheader("📚 학습 이미지")
    
    uploaded_file = st.file_uploader("이미지 업로드", type=['jpg', 'jpeg', 'png'])
    
    if uploaded_file:
        st.session_state.current_image = uploaded_file
        uploaded_file.seek(0)
        st.session_state.image_base64 = encode_image(uploaded_file)
        uploaded_file.seek(0)
        st.image(uploaded_file, use_container_width=True)
    
    st.markdown("---")
    
    st.subheader("🖼️ 화면 객체")
    new_object = st.text_input("객체 추가")
    if st.button("➕ 추가"):
        if new_object:
            st.session_state.screen_objects.append(new_object)
            st.rerun()
    
    if st.session_state.screen_objects:
        for obj in st.session_state.screen_objects:
            st.write(f"• {obj}")
    else:
        st.info("객체를 추가하세요")

# 오른쪽: D-ID 아바타
with col2:
    st.subheader("🎭 D-ID 실시간 아바타")
    
    # WebRTC 컴포넌트 표시
    webrtc_html = create_did_webrtc_component(DID_KEY_ENCODED, OPENAI_KEY)
    components.html(webrtc_html, height=650)

# =============================================================================
# 7. 텍스트 대화 (임시 테스트)
# =============================================================================

st.markdown("---")
st.subheader("💬 텍스트 대화 (테스트용)")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

user_input = st.chat_input("테스트 메시지...")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    
    with st.spinner("응답 생성 중..."):
        response = ask_gpt_with_image(user_input, st.session_state.image_base64)
    
    st.session_state.messages.append({"role": "assistant", "content": response})
    st.rerun()

# =============================================================================
# 8. 디버그 정보
# =============================================================================

with st.expander("🔧 디버그 정보"):
    st.code(f"""
D-ID API Key (처음 10자): {DID_KEY_ENCODED[:10]}...
OpenAI API Key (처음 10자): {OPENAI_KEY[:10]}...
화면 객체: {st.session_state.screen_objects}
이미지: {'있음' if st.session_state.image_base64 else '없음'}
    """)
    
    st.markdown("""
    ### 테스트 순서:
    1. 사이드바에서 API 키 형식 확인
    2. "연결 시작" 버튼 클릭
    3. 브라우저 콘솔 확인 (F12)
    4. 오류 메시지 확인
    """)
