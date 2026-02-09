#!/usr/bin/env python3
"""
Gemini Unity Game Translator
- Flask 기반 로컬 번역 서버
- XUnity.AutoTranslator의 CustomEndpoint와 연동
- Google Gemini API를 사용하여 중국어 → 한국어 번역
"""

import json
import os
import sys
import time
import hashlib
import threading
from pathlib import Path

from flask import Flask, request, jsonify
import requests

# ============================================================
# 설정 로드
# ============================================================
CONFIG_PATH = Path(__file__).parent / "config.json"

DEFAULT_CONFIG = {
    "api_key": "",
    "model": "gemini-2.0-flash",
    "source_lang": "zh",
    "target_lang": "ko",
    "port": 5000,
    "host": "127.0.0.1",
    "cache_file": "translation_cache.json",
    "max_retries": 3,
    "retry_delay": 1.0,
    "batch_size": 10,
    "system_prompt": (
        "You are a professional game translator. "
        "Translate the following Chinese text to natural Korean. "
        "Keep proper nouns, item names, and game-specific terms as-is or transliterate them. "
        "Do not add explanations. Return ONLY the translated text. "
        "Maintain the original formatting, line breaks, and special characters like {0}, [color], etc."
    ),
}

LANG_NAMES = {
    "zh": "Chinese",
    "ko": "Korean",
    "ja": "Japanese",
    "en": "English",
}


def load_config():
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            user_cfg = json.load(f)
        cfg = {**DEFAULT_CONFIG, **user_cfg}
    else:
        cfg = DEFAULT_CONFIG.copy()
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
        print(f"[INFO] 설정 파일 생성됨: {CONFIG_PATH}")
        print("[INFO] config.json 을 열어 api_key 를 입력하세요.")
    return cfg


config = load_config()

# ============================================================
# 번역 캐시
# ============================================================
cache_lock = threading.Lock()
CACHE_PATH = Path(__file__).parent / config["cache_file"]


def load_cache():
    if CACHE_PATH.exists():
        with open(CACHE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_cache(cache):
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)


translation_cache = load_cache()

# 주기적 캐시 저장 (30초마다)
_dirty = False


def mark_dirty():
    global _dirty
    _dirty = True


def cache_saver():
    global _dirty
    while True:
        time.sleep(30)
        if _dirty:
            with cache_lock:
                save_cache(translation_cache)
                _dirty = False


saver_thread = threading.Thread(target=cache_saver, daemon=True)
saver_thread.start()

# ============================================================
# Gemini API 호출
# ============================================================
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


def call_gemini(text, src_lang=None, tgt_lang=None):
    """Gemini API를 호출하여 텍스트를 번역합니다."""
    api_key = config["api_key"]
    if not api_key:
        return None, "API 키가 설정되지 않았습니다. config.json을 확인하세요."

    model = config["model"]
    src = LANG_NAMES.get(src_lang or config["source_lang"], config["source_lang"])
    tgt = LANG_NAMES.get(tgt_lang or config["target_lang"], config["target_lang"])

    url = GEMINI_API_URL.format(model=model) + f"?key={api_key}"

    prompt = (
        f"{config['system_prompt']}\n\n"
        f"Source ({src}):\n{text}\n\n"
        f"Translation ({tgt}):"
    )

    payload = {
        "contents": [
            {
                "parts": [{"text": prompt}]
            }
        ],
        "generationConfig": {
            "temperature": 0.3,
            "maxOutputTokens": 2048,
        },
    }

    headers = {"Content-Type": "application/json"}

    for attempt in range(config["max_retries"]):
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts:
                        return parts[0].get("text", "").strip(), None
                return None, "Gemini 응답에서 번역 텍스트를 찾을 수 없습니다."
            elif resp.status_code == 429:
                wait = config["retry_delay"] * (2 ** attempt)
                print(f"[WARN] Rate limit. {wait}초 후 재시도... ({attempt+1}/{config['max_retries']})")
                time.sleep(wait)
                continue
            else:
                return None, f"Gemini API 오류 [{resp.status_code}]: {resp.text[:200]}"
        except requests.exceptions.Timeout:
            print(f"[WARN] 타임아웃. 재시도... ({attempt+1}/{config['max_retries']})")
            time.sleep(config["retry_delay"])
        except requests.exceptions.RequestException as e:
            return None, f"네트워크 오류: {str(e)}"

    return None, "최대 재시도 횟수를 초과했습니다."


def call_gemini_batch(texts, src_lang=None, tgt_lang=None):
    """여러 텍스트를 한 번에 번역합니다."""
    api_key = config["api_key"]
    if not api_key:
        return None, "API 키가 설정되지 않았습니다."

    model = config["model"]
    src = LANG_NAMES.get(src_lang or config["source_lang"], config["source_lang"])
    tgt = LANG_NAMES.get(tgt_lang or config["target_lang"], config["target_lang"])

    url = GEMINI_API_URL.format(model=model) + f"?key={api_key}"

    numbered = "\n".join(f"[{i}] {t}" for i, t in enumerate(texts))
    prompt = (
        f"{config['system_prompt']}\n\n"
        f"Translate each numbered line from {src} to {tgt}. "
        f"Keep the [number] prefix. Return ONLY the translated lines.\n\n"
        f"{numbered}"
    )

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.3,
            "maxOutputTokens": 4096,
        },
    }

    for attempt in range(config["max_retries"]):
        try:
            resp = requests.post(
                url, json=payload, headers={"Content-Type": "application/json"}, timeout=60
            )
            if resp.status_code == 200:
                data = resp.json()
                candidates = data.get("candidates", [])
                if not candidates:
                    return None, "응답 없음"
                raw = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                results = {}
                for line in raw.strip().split("\n"):
                    line = line.strip()
                    if line.startswith("[") and "]" in line:
                        idx_str = line[1:line.index("]")]
                        try:
                            idx = int(idx_str)
                            translated = line[line.index("]") + 1:].strip()
                            results[idx] = translated
                        except ValueError:
                            continue
                return [results.get(i, texts[i]) for i in range(len(texts))], None
            elif resp.status_code == 429:
                wait = config["retry_delay"] * (2 ** attempt)
                print(f"[WARN] Rate limit. {wait}초 후 재시도...")
                time.sleep(wait)
                continue
            else:
                return None, f"API 오류 [{resp.status_code}]"
        except requests.exceptions.RequestException as e:
            return None, str(e)

    return None, "최대 재시도 초과"


def translate_text(text, src_lang=None, tgt_lang=None):
    """캐시를 확인하고, 없으면 Gemini로 번역합니다."""
    if not text or not text.strip():
        return text, None

    cache_key = f"{src_lang or config['source_lang']}:{tgt_lang or config['target_lang']}:{text}"

    with cache_lock:
        if cache_key in translation_cache:
            return translation_cache[cache_key], None

    translated, err = call_gemini(text, src_lang, tgt_lang)
    if err:
        return None, err

    with cache_lock:
        translation_cache[cache_key] = translated
        mark_dirty()

    return translated, None


# ============================================================
# Flask 앱
# ============================================================
app = Flask(__name__)


@app.route("/", methods=["GET"])
def index():
    return jsonify({
        "status": "running",
        "service": "Gemini Unity Game Translator",
        "model": config["model"],
        "source": config["source_lang"],
        "target": config["target_lang"],
        "cached": len(translation_cache),
    })


@app.route("/translate", methods=["GET", "POST"])
def translate_endpoint():
    """
    XUnity.AutoTranslator CustomEndpoint 호환 엔드포인트.

    GET  /translate?text=...&from=zh&to=ko
    POST /translate  body: {"text": "...", "from": "zh", "to": "ko"}
    """
    if request.method == "GET":
        text = request.args.get("text", "")
        src = request.args.get("from", config["source_lang"])
        tgt = request.args.get("to", config["target_lang"])
    else:
        data = request.get_json(silent=True) or {}
        text = data.get("text", request.form.get("text", ""))
        src = data.get("from", request.form.get("from", config["source_lang"]))
        tgt = data.get("to", request.form.get("to", config["target_lang"]))

    if not text:
        return jsonify({"error": "text 파라미터가 필요합니다."}), 400

    translated, err = translate_text(text, src, tgt)
    if err:
        print(f"[ERROR] {err}")
        return jsonify({"error": err}), 500

    print(f"[번역] {text[:40]}... → {translated[:40]}...")
    return translated


@app.route("/batch", methods=["POST"])
def batch_endpoint():
    """여러 텍스트를 한 번에 번역합니다."""
    data = request.get_json(silent=True) or {}
    texts = data.get("texts", [])
    src = data.get("from", config["source_lang"])
    tgt = data.get("to", config["target_lang"])

    if not texts:
        return jsonify({"error": "texts 배열이 필요합니다."}), 400

    results = []
    uncached = []
    uncached_indices = []

    for i, text in enumerate(texts):
        cache_key = f"{src}:{tgt}:{text}"
        with cache_lock:
            if cache_key in translation_cache:
                results.append(translation_cache[cache_key])
            else:
                results.append(None)
                uncached.append(text)
                uncached_indices.append(i)

    if uncached:
        batch_size = config["batch_size"]
        for start in range(0, len(uncached), batch_size):
            batch = uncached[start:start + batch_size]
            batch_idx = uncached_indices[start:start + batch_size]
            translated_list, err = call_gemini_batch(batch, src, tgt)
            if err:
                # 배치 실패 시 개별 번역으로 폴백
                for j, t in zip(batch_idx, batch):
                    single, single_err = translate_text(t, src, tgt)
                    results[j] = single if not single_err else t
            else:
                for j, tr in zip(batch_idx, translated_list):
                    results[j] = tr
                    cache_key = f"{src}:{tgt}:{uncached[uncached_indices.index(j)]}"
                    with cache_lock:
                        translation_cache[cache_key] = tr
                        mark_dirty()

    return jsonify({"translations": results})


@app.route("/cache/stats", methods=["GET"])
def cache_stats():
    """캐시 통계를 반환합니다."""
    with cache_lock:
        return jsonify({
            "total_entries": len(translation_cache),
            "cache_file": str(CACHE_PATH),
        })


@app.route("/cache/clear", methods=["POST"])
def cache_clear():
    """캐시를 초기화합니다."""
    with cache_lock:
        translation_cache.clear()
        save_cache(translation_cache)
    return jsonify({"message": "캐시가 초기화되었습니다."})


@app.route("/cache/save", methods=["POST"])
def cache_save_endpoint():
    """캐시를 즉시 저장합니다."""
    with cache_lock:
        save_cache(translation_cache)
    return jsonify({"message": "캐시가 저장되었습니다."})


# ============================================================
# 메인 실행
# ============================================================
def verify_api_key():
    """API 키가 유효한지 간단히 확인합니다."""
    if not config["api_key"]:
        print("=" * 50)
        print("[오류] API 키가 설정되지 않았습니다!")
        print(f"  config.json 파일을 열어 api_key 를 입력하세요.")
        print(f"  경로: {CONFIG_PATH}")
        print("=" * 50)
        return False

    print("[INFO] API 키 확인 중...")
    url = GEMINI_API_URL.format(model=config["model"]) + f"?key={config['api_key']}"
    payload = {
        "contents": [{"parts": [{"text": "Say OK"}]}],
        "generationConfig": {"maxOutputTokens": 10},
    }
    try:
        resp = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=10)
        if resp.status_code == 200:
            print("[OK] API 키가 정상적으로 확인되었습니다.")
            return True
        else:
            print(f"[오류] API 키 확인 실패: {resp.status_code}")
            print(f"  응답: {resp.text[:200]}")
            return False
    except Exception as e:
        print(f"[오류] API 연결 실패: {e}")
        return False


if __name__ == "__main__":
    print("=" * 50)
    print("  Gemini Unity Game Translator")
    print(f"  모델: {config['model']}")
    print(f"  번역: {config['source_lang']} → {config['target_lang']}")
    print(f"  캐시: {len(translation_cache)}개 항목")
    print("=" * 50)

    if not verify_api_key():
        sys.exit(1)

    print(f"\n[서버 시작] http://{config['host']}:{config['port']}")
    print("[INFO] 게임 플레이 중 이 창을 닫지 마세요!")
    print("[INFO] Ctrl+C 로 종료합니다.\n")

    try:
        app.run(host=config["host"], port=config["port"], debug=False, threaded=True)
    except KeyboardInterrupt:
        print("\n[INFO] 서버 종료 중...")
        with cache_lock:
            save_cache(translation_cache)
        print("[INFO] 캐시 저장 완료. 종료.")
