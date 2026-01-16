"""
Pro Roasting Logger - EXE 런처 (Native Window 버전)
pywebview를 사용하여 브라우저 없이 앱 창으로 실행
"""
import os
import sys
import threading
import time
import socket


def get_base_path():
    """PyInstaller로 빌드된 경우와 일반 실행 경우 모두 지원"""
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    else:
        return os.path.dirname(os.path.abspath(__file__))


def find_free_port():
    """사용 가능한 포트 찾기"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        return s.getsockname()[1]


def wait_for_server(port, timeout=30):
    """서버가 시작될 때까지 대기"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect(('localhost', port))
                return True
        except ConnectionRefusedError:
            time.sleep(0.5)
    return False


def run_streamlit(port, script_path):
    """Streamlit 서버 실행"""
    os.environ['STREAMLIT_SERVER_HEADLESS'] = 'true'
    os.environ['STREAMLIT_SERVER_PORT'] = str(port)
    os.environ['STREAMLIT_BROWSER_GATHER_USAGE_STATS'] = 'false'
    os.environ['STREAMLIT_GLOBAL_DEVELOPMENT_MODE'] = 'false'
    os.environ['STREAMLIT_SERVER_FILE_WATCHER_TYPE'] = 'none'

    from streamlit.web import cli as stcli

    sys.argv = [
        "streamlit",
        "run",
        script_path,
        f"--server.port={port}",
        "--global.developmentMode=false",
        "--server.headless=true",
        "--browser.gatherUsageStats=false",
        "--server.fileWatcherType=none",
    ]

    stcli.main()


def main():
    """메인 실행 함수"""
    base_path = get_base_path()
    script_path = os.path.join(base_path, 'roasting_log.py')

    # 스크립트 파일 존재 확인
    if not os.path.exists(script_path):
        print(f"오류: 스크립트 파일을 찾을 수 없습니다: {script_path}")
        input("아무 키나 누르세요...")
        sys.exit(1)

    # 포트 설정
    port = 8501

    # Streamlit 서버를 별도 스레드에서 실행
    server_thread = threading.Thread(target=run_streamlit, args=(port, script_path), daemon=True)
    server_thread.start()

    # 서버 시작 대기
    print("서버 시작 중...")
    if not wait_for_server(port):
        print("서버 시작 시간 초과")
        input("아무 키나 누르세요...")
        sys.exit(1)

    print("앱 창 열기...")

    try:
        import webview

        # 네이티브 창으로 앱 열기
        window = webview.create_window(
            'Pro Roasting Logger',
            f'http://localhost:{port}',
            width=1400,
            height=900,
            resizable=True,
            min_size=(800, 600)
        )

        webview.start()

    except ImportError:
        # pywebview가 없으면 브라우저로 대체
        print("pywebview가 설치되지 않아 브라우저로 엽니다.")
        import webbrowser
        webbrowser.open(f'http://localhost:{port}')

        # 서버 유지
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
    except Exception as e:
        print(f"오류 발생: {e}")
        import traceback
        traceback.print_exc()
        input("아무 키나 누르세요...")
        sys.exit(1)


if __name__ == "__main__":
    main()
