#!/bin/bash
echo "================================================"
echo "  Gemini Unity Game Translator - 설치 스크립트"
echo "================================================"
echo

# Python 확인
if ! command -v python3 &> /dev/null; then
    echo "[오류] Python3가 설치되어 있지 않습니다."
    echo "  sudo apt install python3 python3-pip  (Ubuntu/Debian)"
    echo "  brew install python3                   (macOS)"
    exit 1
fi

echo "[1/3] Python 확인 완료"
python3 --version

# pip 패키지 설치
echo
echo "[2/3] 필요한 패키지 설치 중..."
pip3 install flask requests
if [ $? -ne 0 ]; then
    echo "[오류] 패키지 설치에 실패했습니다."
    exit 1
fi

echo
echo "[3/3] 설치 완료!"
echo
echo "================================================"
echo "  다음 단계:"
echo "  1. config.json 을 열어 api_key 를 입력하세요."
echo "     (Google AI Studio: https://aistudio.google.com/apikey)"
echo "  2. python3 gemini_trans.py 를 실행하세요."
echo "  3. 게임 폴더에 BepInEx + XUnity.AutoTranslator 를 설치하세요."
echo "  4. bepinex_config/AutoTranslatorConfig.ini 를"
echo "     게임폴더/BepInEx/config/ 에 복사하세요."
echo "================================================"
