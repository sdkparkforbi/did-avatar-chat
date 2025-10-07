import streamlit as st
import streamlit.components.v1 as components
from openai import OpenAI
import base64
import json

# =============================================================================
# 설정
# =============================================================================

st.set_page_config(page_title="AI 교사", page_icon="🤖", layout="wide")

DID_KEY_RAW = st.secrets["DID_API_KEY"]
DID_KEY = base64.b64encode(DID_KEY_RAW.encode()).decode() if ':' in DID_KEY_RAW else DID_KEY_RAW
OPENAI_KEY = st.secrets["OPENAI_API_KEY"]

if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'image_base64' not in st.session_state:
    st.session_state.image_base64 = None
if 'screen_objects' not in st.session_state:
    st.session_state.screen_objects = []

# =============================================================================
# 함수
# =============================================================================

def encode_image(image_file):
    return base64.b64encode(image_file.read()).decode('utf-8')

def ask_gpt(user_text, image_base64=None):
    client = OpenAI(api_key=OPENAI_KEY)
    
    system_msg = "당신은 친절한 AI 교사입니다."
    if st.session_state.screen_objects:
        objects = ", ".join(st.session_state.screen_objects)
        system_msg += f"\n화면 객체: {objects}"
    
    if image_base64:
        messages = [
            {"role": "system", "content": system_msg},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": user_text},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}}
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
    
    response = client.chat.completions.create(model=model, messages=messages, max_tokens=500)
    return response.choices[0].message.content

# =============================================================================
# D-ID WebRTC (수정됨)
# =============================================================================

def create_webrtc_component():
    objects_json = json.dumps(st.session_state.screen_objects)
    image = st.session_state.image_base64 or ""
    
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body { margin: 0; padding: 20px; background: #f5f5f5; font-family: Arial; }
            #container { text-align: center; background: white; border-radius: 10px; padding: 20px; }
            video { width: 100%; max-width: 640px; border-radius: 10px; background: #000; }
            .status { margin-top: 10px; padding: 10px; background: #e3f2fd; border-radius: 5px; font-size: 14px; }
            .error { background: #ffebee; color: #c62828; }
            .success { background: #e8f5e9; color: #2e7d32; }
            button { padding: 12px 24px; margin: 5px; background: #2196F3; color: white; border: none; border-radius: 5px; cursor: pointer; font-size: 14px; }
            button:disabled { background: #ccc; }
        </style>
    </head>
    <body>
        <div id="container">
            <h3>Emma 아바타</h3>
            <video id="video" autoplay playsinline></video>
            <div class="status" id="status">준비</div>
            <div>
                <button id="connect" onclick="connect()">연결</button>
                <button id="disconnect" onclick="disconnect()" disabled>종료</button>
            </div>
        </div>

        <script>
            const API_KEY = '""" + DID_KEY + """';
            let pc, streamId, sessionId, agentId;
            
            function status(msg, type = '') {
                const el = document.getElementById('status');
                el.textContent = msg;
                el.className = 'status ' + type;
                console.log(msg);
            }
            
            // Agent 상태 확인 (추가)
            async function waitForAgent(agentId, maxAttempts = 30) {
                for (let i = 0; i < maxAttempts; i++) {
                    const res = await fetch(`https://api.d-id.com/agents/${agentId}`, {
                        headers: { 'Authorization': `Basic ${API_KEY}` }
                    });
                    const data = await res.json();
                    console.log(`Agent 상태 (시도 ${i+1}):`, data.status);
                    
                    if (data.status === 'ready' || data.status === 'done') {
                        console.log('Agent 준비 완료!');
                        return true;
                    }
                    
                    await new Promise(resolve => setTimeout(resolve, 1000));
                }
                throw new Error('Agent 준비 시간 초과');
            }
            
            async function connect() {
                try {
                    document.getElementById('connect').disabled = true;
                    status('연결 시작...');
                    
                    // 1. Agent 생성
                    console.log('Agent 생성 요청...');
                    let res = await fetch('https://api.d-id.com/agents', {
                        method: 'POST',
                        headers: { 
                            'Authorization': `Basic ${API_KEY}`, 
                            'Content-Type': 'application/json' 
                        },
                        body: JSON.stringify({
                            presenter: {
                                type: 'talk',
                                voice: { type: 'microsoft', voice_id: 'ko-KR-SunHiNeural' },
                                thumbnail: 'https://create-images-results.d-id.com/DefaultPresenters/Emma_f/thumbnail.jpeg',
                                source_url: 'https://create-images-results.d-id.com/DefaultPresenters/Emma_f/image.png'
                            },
                            preview_name: 'Emma'
                        })
                    });
                    
                    if (!res.ok) {
                        const error = await res.json();
                        throw new Error(`Agent 생성 실패: ${JSON.stringify(error)}`);
                    }
                    
                    const agentData = await res.json();
                    agentId = agentData.id;
                    console.log('Agent ID:', agentId);
                    status('Agent 생성 완료, 준비 대기 중...');
                    
                    // 2. Agent 준비 대기 (추가)
                    await waitForAgent(agentId);
                    status('Agent 준비 완료!');
                    
                    // 3. 스트림 생성
                    console.log('스트림 생성 요청...');
                    res = await fetch(`https://api.d-id.com/agents/${agentId}/streams`, {
                        method: 'POST',
                        headers: { 
                            'Authorization': `Basic ${API_KEY}`, 
                            'Content-Type': 'application/json' 
                        },
                        body: JSON.stringify({
                            source_url: 'https://create-images-results.d-id.com/DefaultPresenters/Emma_f/image.png'
                        })
                    });
                    
                    if (!res.ok) {
                        const error = await res.json();
                        throw new Error(`스트림 생성 실패: ${JSON.stringify(error)}`);
                    }
                    
                    const streamData = await res.json();
                    streamId = streamData.id;
                    sessionId = streamData.session_id;
                    console.log('스트림 ID:', streamId);
                    console.log('세션 ID:', sessionId);
                    status('스트림 생성 완료');
                    
                    // 4. WebRTC 설정
                    console.log('WebRTC 시작...');
                    pc = new RTCPeerConnection({ 
                        iceServers: [
                            { urls: 'stun:stun.l.google.com:19302' },
                            { urls: 'stun:stun1.l.google.com:19302' }
                        ]
                    });
                    
                    pc.ontrack = (e) => {
                        console.log('비디오 트랙 수신!');
                        document.getElementById('video').srcObject = e.streams[0];
                        status('연결 완료!', 'success');
                    };
                    
                    pc.oniceconnectionstatechange = () => {
                        console.log('ICE:', pc.iceConnectionState);
                    };
                    
                    pc.onicecandidate = async (e) => {
                        if (e.candidate) {
                            console.log('ICE candidate:', e.candidate.candidate.substring(0, 50) + '...');
                            await fetch(`https://api.d-id.com/agents/${agentId}/streams/${streamId}/ice`, {
                                method: 'POST',
                                headers: { 
                                    'Authorization': `Basic ${API_KEY}`, 
                                    'Content-Type': 'application/json' 
                                },
                                body: JSON.stringify({
                                    candidate: e.candidate.candidate,
                                    sdpMLineIndex: e.candidate.sdpMLineIndex,
                                    session_id: sessionId
                                })
                            });
                        }
                    };
                    
                    // 5. SDP Offer
                    console.log('SDP Offer 요청...');
                    res = await fetch(`https://api.d-id.com/agents/${agentId}/streams/${streamId}/sdp`, {
                        method: 'POST',
                        headers: { 
                            'Authorization': `Basic ${API_KEY}`, 
                            'Content-Type': 'application/json' 
                        },
                        body: JSON.stringify({ 
                            session_id: sessionId
                        })
                    });
                    
                    if (!res.ok) {
                        const error = await res.json();
                        throw new Error(`SDP Offer 실패: ${JSON.stringify(error)}`);
                    }
                    
                    const { sdp, type } = await res.json();
                    console.log('SDP Offer 수신, 타입:', type);
                    console.log('SDP 내용 (처음 100자):', sdp.substring(0, 100));
                    
                    await pc.setRemoteDescription({ type, sdp });
                    console.log('RemoteDescription 설정 완료');
                    
                    // 6. SDP Answer
                    const answer = await pc.createAnswer();
                    await pc.setLocalDescription(answer);
                    console.log('SDP Answer 생성');
                    
                    await fetch(`https://api.d-id.com/agents/${agentId}/streams/${streamId}/sdp`, {
                        method: 'PATCH',
                        headers: { 
                            'Authorization': `Basic ${API_KEY}`, 
                            'Content-Type': 'application/json' 
                        },
                        body: JSON.stringify({
                            answer: { type: answer.type, sdp: answer.sdp },
                            session_id: sessionId
                        })
                    });
                    console.log('SDP Answer 전송 완료');
                    
                    document.getElementById('disconnect').disabled = false;
                    status('비디오 연결 대기 중...');
                    
                } catch (error) {
                    console.error('오류:', error);
                    status('오류: ' + error.message, 'error');
                    document.getElementById('connect').disabled = false;
                }
            }
            
            function disconnect() {
                if (pc) {
                    pc.close();
                    pc = null;
                }
                document.getElementById('video').srcObject = null;
                document.getElementById('connect').disabled = false;
                document.getElementById('disconnect').disabled = true;
                status('종료됨');
            }
        </script>
    </body>
    </html>
    """
    return html

# =============================================================================
# UI
# =============================================================================

st.title("🤖 AI 교사 + 실시간 음성")

col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("학습 자료")
    
    uploaded = st.file_uploader("이미지", type=['jpg', 'jpeg', 'png'])
    if uploaded:
        uploaded.seek(0)
        st.session_state.image_base64 = encode_image(uploaded)
        uploaded.seek(0)
        st.image(uploaded, use_container_width=True)
    
    st.markdown("---")
    
    obj = st.text_input("객체 추가")
    if st.button("추가") and obj:
        st.session_state.screen_objects.append(obj)
        st.rerun()
    
    for o in st.session_state.screen_objects:
        st.write(f"• {o}")

with col2:
    st.subheader("Emma 아바타")
    components.html(create_webrtc_component(), height=650)

st.markdown("---")
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

user_input = st.chat_input("테스트...")
if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    response = ask_gpt(user_input, st.session_state.image_base64)
    st.session_state.messages.append({"role": "assistant", "content": response})
    st.rerun()
