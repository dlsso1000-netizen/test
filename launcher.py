"""
Pro Roasting Logger - EXE 런처
PyInstaller로 패키징할 때 사용하는 런처 스크립트
"""
import os
import sys

def get_base_path():
    """PyInstaller로 빌드된 경우와 일반 실행 경우 모두 지원"""
    if getattr(sys, 'frozen', False):
        # PyInstaller로 빌드된 exe 실행 시
        return sys._MEIPASS
    else:
        # 일반 Python 스크립트 실행 시
        return os.path.dirname(os.path.abspath(__file__))


def setup_environment():
    """실행 환경 설정"""
    base_path = get_base_path()

    # 환경 변수 설정 (Streamlit이 필요로 하는 설정들)
    os.environ['STREAMLIT_SERVER_HEADLESS'] = 'true'
    os.environ['STREAMLIT_SERVER_PORT'] = '8501'
    os.environ['STREAMLIT_BROWSER_GATHER_USAGE_STATS'] = 'false'
    os.environ['STREAMLIT_GLOBAL_DEVELOPMENT_MODE'] = 'false'

    # 임시 디렉토리 설정 (exe 실행 시 필요)
    if getattr(sys, 'frozen', False):
        # Windows에서 사용자별 임시 폴더 사용
        temp_dir = os.path.join(os.environ.get('TEMP', os.environ.get('TMP', '.')), 'RoastingLogger')
        os.makedirs(temp_dir, exist_ok=True)
        os.environ['STREAMLIT_SERVER_FILE_WATCHER_TYPE'] = 'none'

    return base_path


def main():
    """메인 실행 함수"""
    base_path = setup_environment()

    # Streamlit CLI 임포트
    from streamlit.web import cli as stcli

    # 메인 스크립트 경로
    script_path = os.path.join(base_path, 'roasting_log.py')

    # 스크립트 파일 존재 확인
    if not os.path.exists(script_path):
        print(f"오류: 스크립트 파일을 찾을 수 없습니다: {script_path}")
        print(f"현재 base_path: {base_path}")
        print(f"디렉토리 내용: {os.listdir(base_path)}")
        input("아무 키나 누르세요...")
        sys.exit(1)

    # sys.argv 설정 (Streamlit CLI가 필요로 함)
    sys.argv = [
        "streamlit",
        "run",
        script_path,
        "--global.developmentMode=false",
        "--server.headless=true",
        "--browser.gatherUsageStats=false",
        "--server.fileWatcherType=none",
    ]

    try:
        sys.exit(stcli.main())
    except Exception as e:
        print(f"실행 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        input("아무 키나 누르세요...")
        sys.exit(1)


if __name__ == "__main__":
    main()
