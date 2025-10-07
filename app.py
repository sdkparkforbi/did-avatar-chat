import streamlit as st
import streamlit.components.v1 as components
from openai import OpenAI
import base64
import json

# =============================================================================
# 설정
# =============================================================================

st.set_page_config(page_title="AI 교사", page_icon="🤖", layout="wide")

# API 키
DID_KEY_RAW = st.secrets["DID_API_KEY"]
DID_KEY = base64.b64encode(DID_KEY_RAW.encode()).decode() if ':' in DID_KEY_RAW else DID_KEY_RAW
OPENAI_KEY = st.secrets["OPENAI_API_KEY"]

# 세션 상태
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
# D-ID WebRTC
# =============================================================================

def create_webrtc_component():
    objects_json = json.dumps(st.session_state.screen_objects)
    image = st.session_state.image_base64 or ""
    
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body { margin: 0; padding: 20px; background: #f5f5f5; }
            #container { text-align: center; background: white; border-radius: 10px; padding: 20px; }
            video { width: 100%; max-width: 640px; border-radius: 10px; background: #000; }
            .status { margin-top: 10px; padding: 10px; background: #e3f2fd; border-radius: 5px; }
            button { padding: 12px 24px; margin: 5px; background: #2196F3; color: white; border: none; border-radius: 5px; cursor: pointer; }
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
            const OBJECTS = """ + objects_json + """;
            let pc, streamId, sessionId, agentId;
            
            function status(msg) {
                document.getElementById('status').textContent = msg;
            }
            
            async function connect() {
                document.getElementById('connect').disabled = true;
                status('연결 중...');
                
                // Agent 생성
                let res = await fetch('https://api.d-id.com/agents', {
                    method: 'POST',
                    headers: { 'Authorization': `Basic ${API_KEY}`, 'Content-Type': 'application/json' },
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
                agentId = (await res.json()).id;
                status('Agent 생성 완료');
                
                // 스트림 생성
                res = await fetch(`https://api.d-id.com/agents/${agentId}/streams`, {
                    method: 'POST',
                    headers: { 'Authorization': `Basic ${API_KEY}`, 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        source_url: 'https://create-images-results.d-id.com/DefaultPresenters/Emma_f/image.png'
                    })
                });
                let data = await res.json();
                streamId = data.id;
                sessionId = data.session_id;
                status('스트림 생성 완료');
                
                // WebRTC 설정
                pc = new RTCPeerConnection({ iceServers: [{ urls: 'stun:stun.l.google.com:19302' }] });
                
                pc.ontrack = (e) => {
                    document.getElementById('video').srcObject = e.streams[0];
                    status('연결 완료!');
                };
                
                pc.onicecandidate = async (e) => {
                    if (e.candidate) {
                        await fetch(`https://api.d-id.com/agents/${agentId}/streams/${streamId}/ice`, {
                            method: 'POST',
                            headers: { 'Authorization': `Basic ${API_KEY}`, 'Content-Type': 'application/json' },
                            body: JSON.stringify({
                                candidate: e.candidate.candidate,
                                sdpMLineIndex: e.candidate.sdpMLineIndex,
                                session_id: sessionId
                            })
                        });
                    }
                };
                
                // SDP 교환
                res = await fetch(`https://api.d-id.com/agents/${agentId}/streams/${streamId}/sdp`, {
                    method: 'POST',
                    headers: { 'Authorization': `Basic ${API_KEY}`, 'Content-Type': 'application/json' },
                    body: JSON.stringify({ session_id: sessionId })
                });
                let { sdp, type } = await res.json();
                await pc.setRemoteDescription({ type, sdp });
                
                let answer = await pc.createAnswer();
                await pc.setLocalDescription(answer);
                
                await fetch(`https://api.d-id.com/agents/${agentId}/streams/${streamId}/sdp`, {
                    method: 'PATCH',
                    headers: { 'Authorization': `Basic ${API_KEY}`, 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        answer: { type: answer.type, sdp: answer.sdp },
                        session_id: sessionId
                    })
                });
                
                document.getElementById('disconnect').disabled = false;
            }
            
            function disconnect() {
                if (pc) pc.close();
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

# 왼쪽: 이미지 & 객체
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

# 오른쪽: D-ID
with col2:
    st.subheader("Emma 아바타")
    components.html(create_webrtc_component(), height=650)

# 텍스트 테스트
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
