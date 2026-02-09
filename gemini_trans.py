#!/usr/bin/env python3
"""
Gemini Unity Game Translator (통합 버전)
- Flask 기반 로컬 번역 서버
- XUnity.AutoTranslator의 CustomEndpoint와 연동
- Google Gemini API를 사용하여 게임 텍스트 번역
- 다중 API 키 로테이션 지원
- 대화 컨텍스트 기반 일관된 번역
- 파일 기반 번역 캐시
"""

import json
import sys
import time
import threading
import logging
from pathlib import Path
from collections import deque

from flask import Flask, request, jsonify
import requests

# ============================================================
# 설정 로드
# ============================================================
CONFIG_PATH = Path(__file__).parent / "config.json"

DEFAULT_CONFIG = {
    "api_keys": [],
    "model": "gemini-2.0-flash",
    "source_lang": "zh",
    "target_lang": "ko",
    "port": 5000,
    "host": "127.0.0.1",
    "cache_file": "translation_cache.json",
    "max_retries": 3,
    "retry_delay": 1.0,
    "batch_size": 10,
    "context_turns": 2,
    "max_history": 20,
    "max_consecutive_key_failures": 3,
    "temperature": 0.4,
    "max_output_tokens": 1024,
    "safety_off": True,
    "system_prompt": (
        "You are a professional game translator. "
        "Translate the following text to natural, fluent Korean. "
        "Keep proper nouns, item names, and game-specific terms as-is or transliterate them. "
        "Do not add explanations. Return ONLY the translated text. "
        "Maintain the original formatting, line breaks, and special characters "
        "like {0}, {1}, [color], <b>, etc. "
        "Accurately preserve punctuation nuances: ellipses, dashes, exclamation marks, "
        "and other typographical elements that convey tone and emotion."
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
        # api_key(단일) → api_keys(배열) 호환
        if "api_key" in user_cfg and "api_keys" not in user_cfg:
            key = user_cfg.pop("api_key")
            if key:
                user_cfg["api_keys"] = [key]
        cfg = {**DEFAULT_CONFIG, **user_cfg}
    else:
        cfg = DEFAULT_CONFIG.copy()
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
        print(f"[INFO] 설정 파일 생성됨: {CONFIG_PATH}")
        print("[INFO] config.json 을 열어 api_keys 를 입력하세요.")
    return cfg


config = load_config()

# ============================================================
# 로깅 설정
# ============================================================
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("GeminiTranslator")

# ============================================================
# Flask 앱
# ============================================================
app = Flask(__name__)

# ============================================================
# 번역 캐시 (파일 기반 영구 저장)
# ============================================================
cache_lock = threading.Lock()
CACHE_PATH = Path(__file__).parent / config["cache_file"]


def load_cache():
    if CACHE_PATH.exists():
        try:
            with open(CACHE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            logger.warning("캐시 파일 손상. 새 캐시로 시작합니다.")
            return {}
    return {}


def save_cache(cache):
    try:
        with open(CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(cache, f, indent=2, ensure_ascii=False)
    except IOError as e:
        logger.error(f"캐시 저장 실패: {e}")


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
# 다중 API 키 관리
# ============================================================
current_key_index = 0
key_failure_counts = [0] * len(config["api_keys"]) if config["api_keys"] else []


def get_valid_keys():
    """유효한 API 키 목록 반환."""
    return [k for k in config["api_keys"] if k and len(k) > 10]


def get_current_api_key():
    """현재 사용할 API 키와 인덱스 반환. 유효한 키 없으면 (None, -1)."""
    global current_key_index
    valid = get_valid_keys()
    if not valid:
        return None, -1

    keys = config["api_keys"]
    # 현재 인덱스가 유효한 키를 가리키는지 확인
    if 0 <= current_key_index < len(keys) and keys[current_key_index] in valid:
        return keys[current_key_index], current_key_index

    # 첫 번째 유효한 키로 리셋
    for i, k in enumerate(keys):
        if k in valid:
            current_key_index = i
            if i < len(key_failure_counts):
                key_failure_counts[i] = 0
            return k, i

    return None, -1


def rotate_api_key(failed_index):
    """실패한 키에서 다음 유효한 키로 전환. 성공 여부 반환."""
    global current_key_index
    valid = get_valid_keys()
    if len(valid) <= 1:
        # 키가 하나뿐이면 로테이션 불가, 실패 카운트만 리셋
        if 0 <= failed_index < len(key_failure_counts):
            key_failure_counts[failed_index] = 0
        return False

    keys = config["api_keys"]
    next_idx = (failed_index + 1) % len(keys)
    for _ in range(len(keys)):
        if keys[next_idx] in valid and next_idx != failed_index:
            current_key_index = next_idx
            if next_idx < len(key_failure_counts):
                key_failure_counts[next_idx] = 0
            logger.info(f"API 키 전환: Index {failed_index} → {next_idx} ({keys[next_idx][:8]}...)")
            return True
        next_idx = (next_idx + 1) % len(keys)

    return False


# ============================================================
# 대화 컨텍스트 (번역 일관성 향상)
# ============================================================
conversation_history = deque(maxlen=config["max_history"])

# ============================================================
# HTTP 세션 (커넥션 풀링)
# ============================================================
http_session = requests.Session()

# ============================================================
# Gemini API 호출
# ============================================================
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


def build_safety_settings():
    """Safety settings 구성."""
    if config.get("safety_off"):
        return [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
        ]
    return []


def build_context_messages():
    """이전 번역 기록에서 컨텍스트 메시지 생성."""
    turns = config.get("context_turns", 0)
    if turns <= 0 or not conversation_history:
        return []
    messages_count = turns * 2
    return list(conversation_history)[-messages_count:]


def call_gemini_single(text, src_lang=None, tgt_lang=None):
    """
    단일 텍스트를 Gemini API로 번역.
    다중 키 로테이션 + 재시도 로직 포함.
    """
    global key_failure_counts

    src_code = src_lang or config["source_lang"]
    tgt_code = tgt_lang or config["target_lang"]
    src = LANG_NAMES.get(src_code, src_code)
    tgt = LANG_NAMES.get(tgt_code, tgt_code)
    model = config["model"]

    prompt = (
        f"{config['system_prompt']}\n\n"
        f"Source ({src}):\n{text}\n\n"
        f"Translation ({tgt}):"
    )

    context_messages = build_context_messages()
    api_contents = context_messages + [{"role": "user", "parts": [{"text": prompt}]}]

    request_body = {
        "contents": api_contents,
        "generationConfig": {
            "temperature": config.get("temperature", 0.4),
            "maxOutputTokens": config.get("max_output_tokens", 1024),
        },
    }
    safety = build_safety_settings()
    if safety:
        request_body["safetySettings"] = safety

    text_preview = text[:60] + "..." if len(text) > 60 else text
    tried_keys = set()

    for attempt in range(config["max_retries"] + 1):
        api_key, key_idx = get_current_api_key()
        if not api_key:
            return None, "사용 가능한 유효한 API 키가 없습니다."

        # 모든 키를 다 시도했으면 중단
        tried_keys.add(key_idx)
        if len(tried_keys) > len(get_valid_keys()) and attempt > 0:
            break

        url = GEMINI_API_URL.format(model=model) + f"?key={api_key}"
        key_display = api_key[:8] + "..."

        try:
            resp = http_session.post(
                url,
                headers={"Content-Type": "application/json"},
                json=request_body,
                timeout=20,
            )
            resp.raise_for_status()
            data = resp.json()

            # 프롬프트 차단 확인
            prompt_feedback = data.get("promptFeedback", {})
            if prompt_feedback.get("blockReason"):
                reason = prompt_feedback["blockReason"]
                logger.warning(f"프롬프트 차단 ({reason}), Key: {key_display}")
                _handle_key_failure(key_idx)
                continue

            candidates = data.get("candidates", [])
            if not candidates:
                return None, "API 응답에 candidates 없음"

            candidate = candidates[0]
            finish_reason = candidate.get("finishReason", "")

            # Safety/금지 콘텐츠 차단
            if finish_reason in ("SAFETY", "PROHIBITED_CONTENT"):
                logger.warning(f"콘텐츠 차단 ({finish_reason}), Key: {key_display}")
                _handle_key_failure(key_idx)
                continue

            # 정상 응답 추출
            parts = candidate.get("content", {}).get("parts", [])
            if parts and parts[0].get("text"):
                translated = parts[0]["text"].strip()
                # 성공 시 실패 카운트 리셋
                if 0 <= key_idx < len(key_failure_counts):
                    key_failure_counts[key_idx] = 0
                # 대화 히스토리에 추가
                conversation_history.append({"role": "user", "parts": [{"text": text}]})
                conversation_history.append({"role": "model", "parts": [{"text": translated}]})
                logger.info(f"[번역] {text_preview} → {translated[:50]}...")
                return translated, None

            # 비정상 종료
            if finish_reason and finish_reason not in ("STOP", "MAX_TOKENS"):
                logger.warning(f"비정상 종료: {finish_reason}")
                return None, f"API 비정상 종료: {finish_reason}"

            return None, "API 응답에서 번역 텍스트를 찾을 수 없습니다."

        except requests.exceptions.Timeout:
            logger.warning(f"타임아웃 (Key: {key_display}, 시도: {attempt+1})")
            time.sleep(config["retry_delay"])
            continue

        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response is not None else None
            if status == 429:
                logger.warning(f"Rate limit (429), Key: {key_display}")
                if 0 <= key_idx < len(key_failure_counts):
                    key_failure_counts[key_idx] = config["max_consecutive_key_failures"]
                if rotate_api_key(key_idx):
                    continue
                time.sleep(config["retry_delay"] * (2 ** attempt))
                continue
            elif status == 400:
                error_body = ""
                try:
                    error_body = e.response.text[:300]
                except Exception:
                    pass
                return None, f"잘못된 요청 (400): {error_body}"
            else:
                logger.warning(f"HTTP 오류 ({status}), Key: {key_display}")
                _handle_key_failure(key_idx)
                time.sleep(config["retry_delay"])
                continue

        except requests.exceptions.RequestException as e:
            logger.warning(f"네트워크 오류: {e}")
            time.sleep(config["retry_delay"])
            continue

    return None, "최대 재시도 횟수 초과"


def _handle_key_failure(key_idx):
    """키 실패 처리: 카운트 증가 및 필요 시 로테이션."""
    if 0 <= key_idx < len(key_failure_counts):
        key_failure_counts[key_idx] += 1
        if key_failure_counts[key_idx] >= config["max_consecutive_key_failures"]:
            rotate_api_key(key_idx)


def call_gemini_batch(texts, src_lang=None, tgt_lang=None):
    """여러 텍스트를 한 번에 번역."""
    src_code = src_lang or config["source_lang"]
    tgt_code = tgt_lang or config["target_lang"]
    src = LANG_NAMES.get(src_code, src_code)
    tgt = LANG_NAMES.get(tgt_code, tgt_code)
    model = config["model"]

    api_key, key_idx = get_current_api_key()
    if not api_key:
        return None, "사용 가능한 API 키 없음"

    url = GEMINI_API_URL.format(model=model) + f"?key={api_key}"

    numbered = "\n".join(f"[{i}] {t}" for i, t in enumerate(texts))
    prompt = (
        f"{config['system_prompt']}\n\n"
        f"Translate each numbered line from {src} to {tgt}. "
        f"Keep the [number] prefix. Return ONLY the translated lines.\n\n"
        f"{numbered}"
    )

    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": config.get("temperature", 0.4),
            "maxOutputTokens": config.get("max_output_tokens", 1024) * 2,
        },
    }
    safety = build_safety_settings()
    if safety:
        payload["safetySettings"] = safety

    for attempt in range(config["max_retries"]):
        try:
            resp = http_session.post(
                url,
                headers={"Content-Type": "application/json"},
                json=payload,
                timeout=60,
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
                logger.warning(f"Rate limit (배치). {wait}초 후 재시도...")
                time.sleep(wait)
                continue
            else:
                return None, f"API 오류 [{resp.status_code}]"
        except requests.exceptions.RequestException as e:
            return None, str(e)

    return None, "최대 재시도 초과"


def translate_text(text, src_lang=None, tgt_lang=None):
    """캐시 확인 후 Gemini로 번역."""
    if not text or not text.strip():
        return text, None

    src = src_lang or config["source_lang"]
    tgt = tgt_lang or config["target_lang"]
    cache_key = f"{src}:{tgt}:{text}"

    with cache_lock:
        if cache_key in translation_cache:
            return translation_cache[cache_key], None

    translated, err = call_gemini_single(text, src_lang, tgt_lang)
    if err:
        return None, err

    with cache_lock:
        translation_cache[cache_key] = translated
        mark_dirty()

    return translated, None


# ============================================================
# Flask 라우트
# ============================================================

@app.route("/", methods=["GET"])
def index():
    return jsonify({
        "status": "running",
        "service": "Gemini Unity Game Translator",
        "model": config["model"],
        "source": config["source_lang"],
        "target": config["target_lang"],
        "cached": len(translation_cache),
        "api_keys": len(get_valid_keys()),
        "context_turns": config["context_turns"],
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
        logger.error(f"번역 실패: {err}")
        return jsonify({"error": err}), 500

    # XUnity.AutoTranslator는 plain text 응답을 기대
    return translated


@app.route("/batch", methods=["POST"])
def batch_endpoint():
    """여러 텍스트를 한 번에 번역."""
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
                for j, t in zip(batch_idx, batch):
                    single, single_err = translate_text(t, src, tgt)
                    results[j] = single if not single_err else t
            else:
                for j, tr in zip(batch_idx, translated_list):
                    results[j] = tr
                    orig_text = batch[batch_idx.index(j) - start] if (j - start) < len(batch) else uncached[uncached_indices.index(j)]
                    c_key = f"{src}:{tgt}:{orig_text}"
                    with cache_lock:
                        translation_cache[c_key] = tr
                        mark_dirty()

    return jsonify({"translations": results})


@app.route("/cache/stats", methods=["GET"])
def cache_stats():
    with cache_lock:
        return jsonify({
            "total_entries": len(translation_cache),
            "cache_file": str(CACHE_PATH),
        })


@app.route("/cache/clear", methods=["POST"])
def cache_clear():
    with cache_lock:
        translation_cache.clear()
        save_cache(translation_cache)
    return jsonify({"message": "캐시가 초기화되었습니다."})


@app.route("/cache/save", methods=["POST"])
def cache_save_now():
    with cache_lock:
        save_cache(translation_cache)
    return jsonify({"message": "캐시가 저장되었습니다."})


@app.route("/history/clear", methods=["POST"])
def history_clear():
    """대화 컨텍스트 초기화."""
    conversation_history.clear()
    return jsonify({"message": "대화 히스토리가 초기화되었습니다."})


# ============================================================
# 메인 실행
# ============================================================
def verify_api_keys():
    """API 키 유효성 확인."""
    valid = get_valid_keys()
    if not valid:
        print("=" * 55)
        print("  [오류] API 키가 설정되지 않았습니다!")
        print(f"  config.json 의 api_keys 배열에 키를 입력하세요.")
        print(f"  경로: {CONFIG_PATH}")
        print("=" * 55)
        return False

    print(f"[INFO] API 키 {len(valid)}개 확인 중...")
    model = config["model"]

    for i, key in enumerate(valid):
        url = GEMINI_API_URL.format(model=model) + f"?key={key}"
        payload = {
            "contents": [{"parts": [{"text": "Say OK"}]}],
            "generationConfig": {"maxOutputTokens": 10},
        }
        try:
            resp = http_session.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=10)
            if resp.status_code == 200:
                print(f"  [OK] 키 {i+1}: {key[:8]}... 정상")
            else:
                print(f"  [경고] 키 {i+1}: {key[:8]}... 응답코드 {resp.status_code}")
        except Exception as e:
            print(f"  [오류] 키 {i+1}: {key[:8]}... 연결 실패 ({e})")

    return True


if __name__ == "__main__":
    print("=" * 55)
    print("  Gemini Unity Game Translator (통합 버전)")
    print(f"  모델: {config['model']}")
    print(f"  번역: {config['source_lang']} → {config['target_lang']}")
    print(f"  API 키: {len(get_valid_keys())}개")
    print(f"  캐시: {len(translation_cache)}개 항목")
    print(f"  컨텍스트: 최근 {config['context_turns']}턴 사용")
    print(f"  Safety 해제: {'예' if config.get('safety_off') else '아니오'}")
    print("=" * 55)

    if not verify_api_keys():
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
