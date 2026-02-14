#!/usr/bin/env python3
"""
게임 자동 패치 도구
- BepInEx 자동 다운로드 및 설치
- XUnity.AutoTranslator 자동 설치
- AutoTranslatorConfig.ini 자동 설정
- 한글 폰트 자동 적용
"""

import json
import os
import sys
import shutil
import zipfile
import io
import re
import time
from pathlib import Path

try:
    import requests
except ImportError:
    print("[오류] requests 라이브러리가 필요합니다.")
    print("  pip install requests")
    sys.exit(1)

# ============================================================
# 상수
# ============================================================
SCRIPT_DIR = Path(__file__).parent.resolve()
CONFIG_PATH = SCRIPT_DIR / "config.json"

BEPINEX_RELEASES_API = "https://api.github.com/repos/BepInEx/BepInEx/releases/latest"
BEPINEX_PRERELEASE_API = "https://api.github.com/repos/BepInEx/BepInEx/releases"
XUNITY_RELEASES_API = "https://api.github.com/repos/bbepis/XUnity.AutoTranslator/releases/latest"

# ============================================================
# 유틸리티
# ============================================================
def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")


def pause():
    if os.name == "nt":
        os.system("pause")
    else:
        input("\nEnter를 눌러 계속...")


def print_header(title):
    print("=" * 55)
    print(f"  {title}")
    print("=" * 55)


def detect_game_type(game_path):
    """
    게임 폴더를 분석하여 Unity 빌드 타입을 판별.
    반환: (engine_type, arch) 예: ("il2cpp", "x64"), ("mono", "x86")
    """
    game_path = Path(game_path)

    has_game_assembly = (game_path / "GameAssembly.dll").exists()
    has_mono_folder = (game_path / "MonoBleedingEdge").exists()
    has_managed = any(game_path.glob("*_Data/Managed/Assembly-CSharp.dll"))
    has_crash64 = (game_path / "UnityCrashHandler64.exe").exists()
    has_crash32 = (game_path / "UnityCrashHandler32.exe").exists()

    # 64bit EXE 확인 (폴백)
    exe_files = list(game_path.glob("*.exe"))
    arch = "x64"  # 기본값
    if has_crash64:
        arch = "x64"
    elif has_crash32:
        arch = "x86"

    if has_game_assembly:
        engine = "il2cpp"
    elif has_mono_folder or has_managed:
        engine = "mono"
    else:
        engine = "unknown"

    return engine, arch


def find_game_exe(game_path):
    """게임 메인 실행 파일 찾기."""
    game_path = Path(game_path)
    exes = [f for f in game_path.glob("*.exe")
            if "UnityCrashHandler" not in f.name
            and "unins" not in f.name.lower()
            and "unity" not in f.name.lower()]
    if len(exes) == 1:
        return exes[0]
    elif len(exes) > 1:
        print("\n게임 실행 파일이 여러 개 발견됨:")
        for i, exe in enumerate(exes):
            print(f"  [{i+1}] {exe.name}")
        while True:
            choice = input(f"선택 (1-{len(exes)}): ").strip()
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(exes):
                    return exes[idx]
            except ValueError:
                pass
            print("잘못된 입력입니다.")
    return None


def download_with_progress(url, desc="다운로드"):
    """URL에서 파일 다운로드 (진행 표시)."""
    resp = requests.get(url, stream=True, timeout=30)
    resp.raise_for_status()
    total = int(resp.headers.get("content-length", 0))
    downloaded = 0
    chunks = []

    for chunk in resp.iter_content(chunk_size=8192):
        chunks.append(chunk)
        downloaded += len(chunk)
        if total > 0:
            pct = downloaded * 100 / total
            bar = "#" * int(pct / 5) + "-" * (20 - int(pct / 5))
            print(f"\r  {desc}: [{bar}] {pct:.0f}%", end="", flush=True)
        else:
            print(f"\r  {desc}: {downloaded / 1024:.0f} KB", end="", flush=True)

    print()
    return b"".join(chunks)


# ============================================================
# BepInEx 설치
# ============================================================
def get_bepinex_download_url(engine_type, arch):
    """
    GitHub API에서 적합한 BepInEx 릴리즈 URL 가져오기.

    실제 릴리즈 파일명 형식:
      - 안정판 (5.x, Mono용): BepInEx_win_x64_5.4.23.5.zip
      - 프리릴리즈 (6.x, IL2CPP용): BepInEx-Unity.IL2CPP-win-x64-6.0.0-be.x.zip

    Mono 게임 → 최신 안정판 (5.x)
    IL2CPP 게임 → 프리릴리즈 (6.x) 에서 다운로드
    """
    arch_str = arch  # "x64" or "x86"

    try:
        if engine_type == "il2cpp":
            # IL2CPP → 프리릴리즈(6.x)에서 찾기
            print("  [INFO] IL2CPP 게임 → BepInEx 6.x (프리릴리즈) 검색 중...")
            resp = requests.get(BEPINEX_PRERELEASE_API, timeout=15)
            resp.raise_for_status()
            releases = resp.json()

            for release in releases:
                for asset in release.get("assets", []):
                    name = asset["name"]
                    name_lower = name.lower()
                    # 패턴: BepInEx-Unity.IL2CPP-win-x64-...zip
                    # 또는: BepInEx_Unity.IL2CPP_win_x64_...zip
                    if name_lower.endswith(".zip") and "il2cpp" in name_lower and "win" in name_lower and arch_str in name_lower:
                        return asset["browser_download_url"], release["tag_name"]

            # IL2CPP 전용을 못 찾으면, 안정판에서 일반 Windows 빌드 시도
            print("  [INFO] IL2CPP 전용 빌드를 찾지 못해 안정판으로 시도...")

        # Mono 또는 IL2CPP 폴백 → 안정판 (5.x)
        resp = requests.get(BEPINEX_RELEASES_API, timeout=15)
        resp.raise_for_status()
        release = resp.json()

        # 실제 파일명: BepInEx_win_x64_5.4.23.5.zip
        for asset in release.get("assets", []):
            name = asset["name"]
            name_lower = name.lower()
            if name_lower.endswith(".zip") and "win" in name_lower and arch_str in name_lower:
                # patcher 등 제외
                if "patcher" not in name_lower:
                    return asset["browser_download_url"], release["tag_name"]

    except Exception as e:
        print(f"  [경고] GitHub API 실패: {e}")

    return None, None


def install_bepinex(game_path, engine_type, arch):
    """BepInEx를 게임 폴더에 설치."""
    game_path = Path(game_path)
    bepinex_dir = game_path / "BepInEx"

    if bepinex_dir.exists():
        print(f"  [INFO] BepInEx가 이미 설치되어 있습니다: {bepinex_dir}")
        choice = input("  다시 설치하시겠습니까? (y/N): ").strip().lower()
        if choice != "y":
            return True

    print(f"\n  게임 타입: {engine_type.upper()} {arch}")
    print(f"  BepInEx 다운로드 중...")

    url, version = get_bepinex_download_url(engine_type, arch)
    if not url:
        print("  [오류] 적합한 BepInEx 릴리즈를 찾을 수 없습니다.")
        print(f"  수동으로 다운로드하세요: https://github.com/BepInEx/BepInEx/releases")
        return False

    print(f"  버전: {version}")
    data = download_with_progress(url, "BepInEx")

    # 압축 해제
    print("  압축 해제 중...")
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        zf.extractall(game_path)

    print("  [OK] BepInEx 설치 완료!")
    print("  [INFO] 게임을 한 번 실행하여 BepInEx 초기화를 완료하세요.")
    return True


# ============================================================
# XUnity.AutoTranslator 설치
# ============================================================
def get_xunity_download_url(engine_type="mono"):
    """
    XUnity.AutoTranslator 최신 릴리즈 URL.

    실제 파일명:
      - Mono용: XUnity.AutoTranslator-BepInEx-5.5.1.zip
      - IL2CPP용: XUnity.AutoTranslator-BepInEx-IL2CPP-5.5.1.zip
    """
    try:
        resp = requests.get(XUNITY_RELEASES_API, timeout=15)
        resp.raise_for_status()
        release = resp.json()

        if engine_type == "il2cpp":
            # IL2CPP용 먼저 찾기
            for asset in release.get("assets", []):
                name = asset["name"]
                if name.endswith(".zip") and "BepInEx-IL2CPP" in name and "ResourceRedirector" not in name:
                    return asset["browser_download_url"], release["tag_name"]

        # Mono용 또는 폴백
        for asset in release.get("assets", []):
            name = asset["name"]
            if name.endswith(".zip") and "BepInEx" in name and "IL2CPP" not in name and "ResourceRedirector" not in name:
                return asset["browser_download_url"], release["tag_name"]

    except Exception as e:
        print(f"  [경고] GitHub API 실패: {e}")

    return None, None


def install_xunity(game_path, engine_type="mono"):
    """XUnity.AutoTranslator를 BepInEx/plugins에 설치."""
    game_path = Path(game_path)
    plugins_dir = game_path / "BepInEx" / "plugins"

    if not plugins_dir.exists():
        print("  [경고] BepInEx/plugins 폴더가 없습니다.")
        print("  먼저 BepInEx를 설치하고 게임을 한 번 실행하세요.")
        plugins_dir.mkdir(parents=True, exist_ok=True)
        print(f"  [INFO] 폴더 생성함: {plugins_dir}")

    # 이미 설치 확인
    existing = list(plugins_dir.glob("*AutoTranslator*")) + list(plugins_dir.glob("*XUnity*"))
    if existing:
        print(f"  [INFO] XUnity.AutoTranslator가 이미 설치되어 있습니다.")
        choice = input("  다시 설치하시겠습니까? (y/N): ").strip().lower()
        if choice != "y":
            return True

    print(f"\n  XUnity.AutoTranslator 다운로드 중... ({engine_type.upper()}용)")
    url, version = get_xunity_download_url(engine_type)
    if not url:
        print("  [오류] 다운로드 URL을 찾을 수 없습니다.")
        print(f"  수동 다운로드: https://github.com/bbepis/XUnity.AutoTranslator/releases")
        return False

    print(f"  버전: {version}")
    data = download_with_progress(url, "XUnity.AutoTranslator")

    print("  압축 해제 중...")
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        zf.extractall(game_path)

    print("  [OK] XUnity.AutoTranslator 설치 완료!")
    return True


# ============================================================
# AutoTranslator 설정
# ============================================================
def configure_autotranslator(game_path, source_lang="zh"):
    """AutoTranslatorConfig.ini를 게임에 맞게 설정."""
    game_path = Path(game_path)
    config_dir = game_path / "BepInEx" / "config"
    config_dir.mkdir(parents=True, exist_ok=True)

    config_file = config_dir / "AutoTranslatorConfig.ini"

    # 번역 서버 포트 읽기
    port = 5000
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                srv_cfg = json.load(f)
            port = srv_cfg.get("port", 5000)
        except Exception:
            pass

    ini_content = f""";; ============================================================
;; XUnity.AutoTranslator 설정 (Gemini 번역 서버 연동)
;; 자동 생성됨 - game_patcher.py
;; ============================================================

[Service]
Endpoint=CustomEndpoint

[Custom]
Url=http://127.0.0.1:{port}/translate

[General]
FromLanguage={source_lang}
ToLanguage=ko

[Behaviour]
Delay=0
MaxTranslationsBeforeSlowdown=50
MaxTranslationsQueuedPerEndpoint=100

[TextFrameworks]
EnableUGUI=True
EnableTextMeshPro=True
EnableNGUI=True
EnableIMGUI=False

[Files]
OutputFile=Translation/_AutoGeneratedTranslations.txt

[Texture]
EnableTextureTranslation=False
EnableTextureDumping=False

[Font]
OverrideFont=
OverrideFontSize=0
"""

    with open(config_file, "w", encoding="utf-8") as f:
        f.write(ini_content)

    print(f"  [OK] 설정 파일 생성: {config_file}")
    return config_file


# ============================================================
# 폰트 설정
# ============================================================
def setup_font(game_path, config_ini_path):
    """한글 폰트 설정."""
    game_path = Path(game_path)
    fonts_dir = SCRIPT_DIR / "fonts"

    # 번역 도구 폴더에 폰트가 있는지 확인
    font_files = []
    if fonts_dir.exists():
        font_files = list(fonts_dir.glob("*.ttf")) + list(fonts_dir.glob("*.otf"))

    if not font_files:
        print("\n  [INFO] fonts/ 폴더에 한글 폰트 파일이 없습니다.")
        print("  한글이 깨지면 .ttf 폰트를 fonts/ 폴더에 넣고 다시 패치하세요.")
        return

    print("\n  사용 가능한 폰트:")
    for i, f in enumerate(font_files):
        print(f"    [{i+1}] {f.name}")
    print(f"    [0] 폰트 설정 건너뛰기")

    choice = input(f"  선택 (0-{len(font_files)}): ").strip()
    try:
        idx = int(choice)
        if idx == 0:
            return
        if 1 <= idx <= len(font_files):
            selected_font = font_files[idx - 1]
            # 게임 폴더에 폰트 복사
            dest = game_path / selected_font.name
            shutil.copy2(selected_font, dest)
            print(f"  [OK] 폰트 복사: {dest}")

            # config.ini에 폰트 이름 설정
            font_name = selected_font.stem
            if config_ini_path and Path(config_ini_path).exists():
                content = Path(config_ini_path).read_text(encoding="utf-8")
                content = content.replace("OverrideFont=", f"OverrideFont={font_name}")
                Path(config_ini_path).write_text(content, encoding="utf-8")
                print(f"  [OK] 폰트 설정 적용: {font_name}")
    except (ValueError, IndexError):
        print("  건너뜁니다.")


# ============================================================
# 원클릭 패치
# ============================================================
def one_click_patch():
    """원클릭 게임 패치."""
    print_header("Gemini Unity Game Translator - 게임 패치")

    # 1. 게임 경로 입력
    print("\n[1] 게임 폴더 경로를 입력하세요.")
    print("    (게임 .exe 파일이 있는 폴더)")
    print("    Steam: 게임 우클릭 → 관리 → 로컬 파일 탐색\n")

    game_path = input("  경로: ").strip().strip('"').strip("'")
    if not game_path:
        print("[오류] 경로가 입력되지 않았습니다.")
        return

    game_path = Path(game_path)
    if not game_path.exists():
        print(f"[오류] 경로가 존재하지 않습니다: {game_path}")
        return

    # 2. 게임 타입 감지
    print(f"\n[2] 게임 분석 중...")
    engine, arch = detect_game_type(game_path)
    exe = find_game_exe(game_path)

    print(f"  엔진: {engine.upper() if engine != 'unknown' else '알 수 없음'}")
    print(f"  아키텍처: {arch}")
    if exe:
        print(f"  실행 파일: {exe.name}")

    if engine == "unknown":
        print("\n  [경고] Unity 게임으로 확인되지 않습니다.")
        choice = input("  계속 진행하시겠습니까? (y/N): ").strip().lower()
        if choice != "y":
            return

    # 3. 소스 언어 선택
    print(f"\n[3] 원본 언어 선택")
    print("    [1] 중국어 (간체) - zh")
    print("    [2] 일본어 - ja")
    print("    [3] 영어 - en")
    lang_choice = input("  선택 (1-3, 기본: 1): ").strip() or "1"
    lang_map = {"1": "zh", "2": "ja", "3": "en"}
    source_lang = lang_map.get(lang_choice, "zh")
    print(f"  → {source_lang} → ko")

    # 4. BepInEx 설치
    print(f"\n[4] BepInEx 설치")
    bepinex_ok = install_bepinex(game_path, engine, arch)
    if not bepinex_ok:
        print("\n  [경고] BepInEx 설치에 실패했습니다.")
        print("  수동으로 설치한 후 다시 실행하세요.")

    # 5. XUnity.AutoTranslator 설치
    print(f"\n[5] XUnity.AutoTranslator 설치")
    xunity_ok = install_xunity(game_path, engine)

    # 6. 번역 설정
    print(f"\n[6] 번역 설정 적용")
    config_ini = configure_autotranslator(game_path, source_lang)

    # 7. 폰트 설정
    print(f"\n[7] 한글 폰트 설정")
    setup_font(game_path, config_ini)

    # 8. config.json 소스 언어 업데이트
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                srv_cfg = json.load(f)
            srv_cfg["source_lang"] = source_lang
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(srv_cfg, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    # 완료
    print("\n" + "=" * 55)
    print("  패치 완료!")
    print("=" * 55)
    print(f"\n  사용 방법:")
    print(f"  1. run_server.bat 실행 (번역 서버)")
    print(f"  2. 게임 실행")
    print(f"  3. 자동으로 한국어 번역 적용!")
    if not bepinex_ok:
        print(f"\n  [주의] BepInEx 자동 설치 실패 시:")
        print(f"  https://github.com/BepInEx/BepInEx/releases")
        print(f"  에서 수동 다운로드 후 게임 폴더에 압축 해제")


# ============================================================
# 메인 메뉴
# ============================================================
def main():
    while True:
        clear_screen()
        print_header("Gemini Unity Game Translator")
        print()
        print("  [1] 게임 패치 (원클릭 설치)")
        print("  [2] 번역 서버 실행")
        print("  [3] API 키 설정")
        print("  [4] 번역 캐시 관리")
        print("  [0] 종료")
        print()

        choice = input("  선택: ").strip()

        if choice == "1":
            clear_screen()
            one_click_patch()
            pause()

        elif choice == "2":
            clear_screen()
            print_header("번역 서버 시작")
            print("\n  gemini_trans.py 를 실행합니다...\n")
            os.system(f'"{sys.executable}" "{SCRIPT_DIR / "gemini_trans.py"}"')
            pause()

        elif choice == "3":
            clear_screen()
            print_header("API 키 설정")
            print(f"\n  설정 파일: {CONFIG_PATH}")
            if CONFIG_PATH.exists():
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                current_keys = cfg.get("api_keys", [])
                print(f"  현재 키 개수: {len(current_keys)}")
                for i, k in enumerate(current_keys):
                    display = k[:12] + "..." if len(k) > 12 else k
                    print(f"    [{i+1}] {display}")

            print("\n  새 API 키를 입력하세요 (빈 줄로 완료):")
            new_keys = list(current_keys) if CONFIG_PATH.exists() else []
            while True:
                key = input("  키: ").strip()
                if not key:
                    break
                new_keys.append(key)

            if new_keys:
                if CONFIG_PATH.exists():
                    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                        cfg = json.load(f)
                else:
                    cfg = {}
                cfg["api_keys"] = new_keys
                with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                    json.dump(cfg, f, indent=2, ensure_ascii=False)
                print(f"\n  [OK] {len(new_keys)}개 키 저장됨.")
            pause()

        elif choice == "4":
            clear_screen()
            print_header("번역 캐시 관리")
            cache_path = SCRIPT_DIR / "translation_cache.json"
            if cache_path.exists():
                with open(cache_path, "r", encoding="utf-8") as f:
                    cache = json.load(f)
                size_kb = cache_path.stat().st_size / 1024
                print(f"\n  캐시 항목: {len(cache)}개")
                print(f"  파일 크기: {size_kb:.1f} KB")
                print(f"\n  [1] 캐시 초기화")
                print(f"  [0] 돌아가기")
                sub = input("\n  선택: ").strip()
                if sub == "1":
                    confirm = input("  정말 초기화? (y/N): ").strip().lower()
                    if confirm == "y":
                        with open(cache_path, "w", encoding="utf-8") as f:
                            json.dump({}, f)
                        print("  [OK] 캐시 초기화 완료.")
            else:
                print("\n  캐시 파일이 아직 없습니다. 번역 서버를 실행하면 생성됩니다.")
            pause()

        elif choice == "0":
            print("\n  종료합니다.")
            break

        else:
            continue


if __name__ == "__main__":
    main()
