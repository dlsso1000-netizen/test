import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import time
import drivers

# --- 페이지 설정 ---
st.set_page_config(page_title="Pro Roasting Logger", layout="wide")
st.title("Pro Roasting Logger (Hardware Ver.)")

# --- 세션 데이터 초기화 ---
if 'data' not in st.session_state:
    st.session_state.data = pd.DataFrame(columns=['Time_Min', 'BT', 'ET', 'Event', 'RoR'])
if 'driver' not in st.session_state:
    st.session_state.driver = None
if 'is_connected' not in st.session_state:
    st.session_state.is_connected = False
if 'logging_active' not in st.session_state:
    st.session_state.logging_active = False
if 'start_time' not in st.session_state:
    st.session_state.start_time = None

# --- 사이드바: 하드웨어 및 컨트롤 ---
with st.sidebar:
    st.header("하드웨어 연결")

    # 장비 선택
    device_list = [
        "Simulation (가상)", "Easyster (Modbus)", "Proaster (Modbus)",
        "Center 306 (USB)", "Probat (WebSocket)"
    ]
    selected_device = st.selectbox("로스터기 모델", device_list)
    port_input = st.text_input("Port (예: COM3)", "COM3")

    # 연결/해제 버튼
    col_conn1, col_conn2 = st.columns(2)
    with col_conn1:
        if st.button("장비 연결"):
            try:
                st.session_state.driver = drivers.get_driver(selected_device, {'port': port_input})
                st.session_state.driver.connect()
                st.session_state.is_connected = True
                st.success("연결됨!")
            except Exception as e:
                st.error(f"실패: {e}")
    with col_conn2:
        if st.button("연결 해제"):
            st.session_state.is_connected = False
            st.session_state.logging_active = False
            st.info("해제됨")

    st.markdown("---")
    st.header("로스팅 제어")

    # 로스팅 시작/정지 버튼
    if st.session_state.is_connected:
        if st.button("로스팅 시작 (기록)" if not st.session_state.logging_active else "로스팅 종료"):
            if not st.session_state.logging_active:
                # 시작
                st.session_state.logging_active = True
                st.session_state.start_time = time.time()
                # 새 로스팅 시작 시 데이터 초기화 (원하면 이 줄을 지워서 이어쓰기 가능)
                st.session_state.data = pd.DataFrame(columns=['Time_Min', 'BT', 'ET', 'Event', 'RoR'])
            else:
                # 종료
                st.session_state.logging_active = False
    else:
        st.warning("먼저 장비를 연결해주세요.")

    # 이벤트 버튼
    st.markdown("### 이벤트 마킹")
    event_col1, event_col2 = st.columns(2)
    with event_col1:
        if st.button("Turning Point"): st.session_state.last_event = "TP"
        if st.button("Yellowing"): st.session_state.last_event = "Yellow"
        if st.button("1st Crack"): st.session_state.last_event = "1C"
    with event_col2:
        if st.button("2nd Crack"): st.session_state.last_event = "2C"
        if st.button("Drop (배출)"):
            st.session_state.last_event = "Drop"
            st.session_state.logging_active = False

# --- 로직 처리 (데이터 수집) ---
if st.session_state.is_connected and st.session_state.logging_active:
    # 1. 드라이버에서 온도 읽기
    bt, et = st.session_state.driver.read_temps()

    # 2. 시간 계산
    elapsed_time = time.time() - st.session_state.start_time
    current_min = elapsed_time / 60.0

    # 3. RoR 계산
    ror = 0.0
    if len(st.session_state.data) > 0:
        last_bt = st.session_state.data.iloc[-1]['BT']
        last_time = st.session_state.data.iloc[-1]['Time_Min']
        if current_min - last_time > 0:
            ror = (bt - last_bt) / (current_min - last_time)
            # RoR이 너무 튀지 않게 약간의 보정 (선택 사항)
            if ror > 30: ror = 0
            if ror < -10: ror = 0

    # 4. 이벤트 체크
    event_txt = ""
    if 'last_event' in st.session_state:
        event_txt = st.session_state.last_event
        del st.session_state.last_event

    # 5. 데이터 추가
    new_row = pd.DataFrame([{
        'Time_Min': current_min,
        'BT': bt,
        'ET': et,
        'RoR': ror,
        'Event': event_txt
    }])
    st.session_state.data = pd.concat([st.session_state.data, new_row], ignore_index=True)

# --- 화면 그리기 (여기가 중요! 데이터 수집 후 바로 그립니다) ---
placeholder = st.empty()

with placeholder.container():
    if not st.session_state.data.empty:
        # 최신 데이터 가져오기
        curr_bt = st.session_state.data.iloc[-1]['BT']
        curr_et = st.session_state.data.iloc[-1]['ET']
        curr_ror = st.session_state.data.iloc[-1]['RoR']
        curr_time = st.session_state.data.iloc[-1]['Time_Min']

        m, s = divmod(curr_time * 60, 60)

        # 1. 숫자 대시보드
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("시간", f"{int(m):02d}:{int(s):02d}")
        col2.metric("BT (원두)", f"{curr_bt:.1f} C")
        col3.metric("ET (배기)", f"{curr_et:.1f} C")
        col4.metric("RoR", f"{curr_ror:.1f}")

        # 2. 그래프 그리기
        df = st.session_state.data
        fig = make_subplots(specs=[[{"secondary_y": True}]])

        # BT 라인
        fig.add_trace(go.Scatter(x=df['Time_Min'], y=df['BT'], name='BT', line=dict(color='#D32F2F', width=3)), secondary_y=False)
        # ET 라인
        fig.add_trace(go.Scatter(x=df['Time_Min'], y=df['ET'], name='ET', line=dict(color='#1976D2', width=2, dash='dot')), secondary_y=False)
        # RoR 라인 (오른쪽 축)
        fig.add_trace(go.Scatter(x=df['Time_Min'], y=df['RoR'], name='RoR', line=dict(color='#FFA000', width=1), fill='tozeroy', opacity=0.2), secondary_y=True)

        # 이벤트 마커
        events = df[df['Event'] != ""]
        if not events.empty:
            fig.add_trace(go.Scatter(
                x=events['Time_Min'], y=events['BT'], mode='markers+text',
                text=events['Event'], textposition="top center",
                marker=dict(size=12, color='green', symbol='star')
            ), secondary_y=False)

        fig.update_layout(title="Real-time Roasting Curve", height=600, hovermode="x unified")
        fig.update_yaxes(title_text="Temperature (C)", secondary_y=False, range=[0, 300])
        fig.update_yaxes(title_text="RoR", secondary_y=True, range=[0, 30])

        st.plotly_chart(fig, use_container_width=True)

    else:
        st.info("왼쪽 사이드바에서 '장비 연결' 후 '로스팅 시작'을 눌러주세요.")

# --- 자동 새로고침 (맨 마지막에 실행) ---
if st.session_state.is_connected and st.session_state.logging_active:
    time.sleep(1) # 1초 간격
    st.rerun()

# --- 데이터 저장 버튼 ---
if not st.session_state.data.empty:
    csv = st.session_state.data.to_csv(index=False).encode('utf-8')
    st.download_button("CSV로 저장", csv, "roasting_log.csv", "text/csv")
