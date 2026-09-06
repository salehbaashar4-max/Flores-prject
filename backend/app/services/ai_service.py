"""Flores hydrogeological analysis engine.

Answers in Arabic or Bahasa Indonesia, whichever the user is writing in.

The important part is what happens before the model is called: when a message
names a place, the place is geocoded and real values are pulled for that exact
coordinate — bedrock unit, elevation, slope, rainfall, nearby no-drill areas —
and handed to the model as facts it must not contradict. When no provider
answers, the measured data is returned as-is; there are no canned essays here,
because a fluent answer about the wrong village is worse than no answer.
"""
import anthropic
import re
import requests
from typing import Dict, Any, Optional, List

from app.config import settings


# ============================================================
# REAL AI PROVIDER LAYER
# Priority: chatanywhere -> Gemini -> OpenRouter -> Anthropic
# ============================================================
GEMINI_URL_TMPL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

# Tried in order; first the account can serve wins.
GEMINI_MODELS_FALLBACK = [
    "gemini-3.6-flash",
    "gemini-2.5-flash",
    "gemini-flash-latest",
]


def _call_gemini(system_prompt: str, messages: List[Dict[str, str]]) -> Optional[str]:
    """Call Google's Gemini API. Returns text or None on failure.

    `messages` use OpenAI-style roles (user/assistant); mapped to Gemini roles (user/model).
    """
    api_key = settings.gemini_api_key
    if not api_key:
        return None

    models = []
    if settings.gemini_model:
        models.append(settings.gemini_model)
    models.extend(m for m in GEMINI_MODELS_FALLBACK if m not in models)

    contents = []
    for m in messages:
        role = "model" if m.get("role") == "assistant" else "user"
        contents.append({"role": role, "parts": [{"text": m.get("content", "")}]})

    body = {
        "systemInstruction": {"parts": [{"text": system_prompt}]},
        "contents": contents,
        "generationConfig": {"maxOutputTokens": 3000, "temperature": 0.7},
    }

    for model in models:
        try:
            resp = requests.post(
                GEMINI_URL_TMPL.format(model=model),
                params={"key": api_key},
                headers={"Content-Type": "application/json"},
                json=body,
                timeout=60,
            )
            if resp.status_code != 200:
                print(f"Gemini model {model} returned {resp.status_code}: {resp.text[:200]}")
                continue
            data = resp.json()
            candidates = data.get("candidates", [])
            if not candidates:
                print(f"Gemini model {model} returned no candidates: {str(data)[:200]}")
                continue
            parts = candidates[0].get("content", {}).get("parts", [])
            text = "".join(p.get("text", "") for p in parts).strip()
            if text:
                return text
        except Exception as e:
            print(f"Gemini model {model} error: {e}")
            continue
    return None


# ------------------------------------------------------------
# Generic OpenAI-compatible chat caller (OpenRouter, chatanywhere, ...)
# ------------------------------------------------------------
def _call_openai_compatible(
    label: str,
    base_url: str,
    api_key: str,
    models: List[str],
    system_prompt: str,
    messages: List[Dict[str, str]],
    extra_headers: Optional[Dict[str, str]] = None,
) -> Optional[str]:
    """POST to an OpenAI-compatible /chat/completions endpoint. Returns text or None."""
    if not api_key:
        return None

    url = base_url.rstrip("/") + "/chat/completions"
    payload_messages = [{"role": "system", "content": system_prompt}] + messages
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    if extra_headers:
        headers.update(extra_headers)

    for model in models:
        try:
            resp = requests.post(
                url,
                headers=headers,
                json={"model": model, "messages": payload_messages, "max_tokens": 3000},
                timeout=60,
            )
            if resp.status_code != 200:
                print(f"{label} model {model} returned {resp.status_code}: {resp.text[:200]}")
                continue
            data = resp.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content")
            if content:
                return content.strip()
        except Exception as e:
            print(f"{label} model {model} error: {e}")
            continue
    return None


# ------------------------------------------------------------
# chatanywhere free gateway — primary OpenAI-compatible provider
# https://github.com/chatanywhere/GPT_API_free
# ------------------------------------------------------------
CHATANYWHERE_MODELS_FALLBACK = [
    "gpt-4o-mini",
    "gpt-3.5-turbo",
    "deepseek-v3",
]


def _call_chatanywhere(system_prompt: str, messages: List[Dict[str, str]]) -> Optional[str]:
    if not settings.chatanywhere_api_key:
        return None
    models = []
    if settings.chatanywhere_model:
        models.append(settings.chatanywhere_model)
    models.extend(m for m in CHATANYWHERE_MODELS_FALLBACK if m not in models)
    return _call_openai_compatible(
        "chatanywhere",
        settings.chatanywhere_base_url,
        settings.chatanywhere_api_key,
        models,
        system_prompt,
        messages,
    )


# ------------------------------------------------------------
# OpenRouter — OpenAI-compatible provider
# ------------------------------------------------------------
OPENROUTER_MODELS_FALLBACK = [
    "google/gemini-2.0-flash-001",
    "google/gemini-flash-1.5",
    "meta-llama/llama-3.3-70b-instruct",
    "openai/gpt-4o-mini",
]


def _call_openrouter(system_prompt: str, messages: List[Dict[str, str]]) -> Optional[str]:
    if not settings.openrouter_api_key:
        return None
    models = []
    if settings.openrouter_model:
        models.append(settings.openrouter_model)
    models.extend(m for m in OPENROUTER_MODELS_FALLBACK if m not in models)
    return _call_openai_compatible(
        "OpenRouter",
        "https://openrouter.ai/api/v1",
        settings.openrouter_api_key,
        models,
        system_prompt,
        messages,
        extra_headers={
            "HTTP-Referer": "http://localhost:5173",
            "X-Title": "Flores Groundwater Dashboard",
        },
    )


def _call_ai(system_prompt: str, messages: List[Dict[str, str]]) -> Optional[str]:
    """Try real AI providers in priority order. Returns text or None if all fail."""
    for provider in (_call_chatanywhere, _call_gemini, _call_openrouter):
        result = provider(system_prompt, messages)
        if result:
            return result
    return None


def _has_real_ai() -> bool:
    return settings.ai_available


SYSTEM_PROMPT = """أنت خبير استشاري هيدروجيولوجي وجيوفيزيائي أول، متخصص في موارد المياه الجوفية في جزيرة فلوريس والجزر المجاورة — ليمباتا، أدونارا، سولور، كومودو ورينشا — ضمن مقاطعة نوسا تينجارا الشرقية (NTT) الإندونيسية. مهمتك تقييم مواقع حفر آبار المياه الخيرية تقييماً علمياً قابلاً للتنفيذ.

قواعد لا تُكسر:

1. البيانات قبل الرأي. إذا وصلك في الرسالة قسم «بيانات ميدانية مقيسة»، فهو مصدرك الأول: اقتبس أرقامه كما هي وابنِ تحليلك عليها. ولا تكتب «من المحتمل» أو «غالباً» عن شيء موجود فيه أصلاً.

2. الصدق حين لا تعرف. إن لم تصلك بيانات عن المكان، قل صراحةً إنك تستنتج من جيولوجيا المنطقة المحيطة، واذكر ما الذي يلزم قياسه ميدانياً لحسم الأمر. لا تخترع أرقاماً ولا إحداثيات ولا أسماء تكوينات جيولوجية.

3. المكان المسؤول عنه هو المكان المسؤول. إذا سأل المستخدم عن قرية أو مسجد أو موقع بعينه فأجب عنه هو، ولا تنزلق إلى ماوميري أو روتنغ لمجرد أنهما الأشهر.

4. لغة خبير حقيقي. استخدم المصطلحات الدقيقة (Unconfined Aquifer، Fractured Volcanic Aquifer، Transmissivity، Specific Yield، Weathering Profile) واشرح كلاً منها بإيجاز عند أول ورود.

5. الشكل: Markdown نظيف — فقرات قصيرة، قوائم عند التعداد، عنوان فرعي عند الحاجة فقط. لا تُثقل النص بالتعليم الغامق: النجمتان لكلمة أو كلمتين فعلاً مهمتين، لا لكل سطر.

6. أجب بلغة المستخدم: عربية فصحى احترافية أو Bahasa Indonesia."""


def _detect_language(text: str) -> str:
    """Detect if text is Arabic or Indonesian/other."""
    arabic_chars = sum(1 for c in text if '\u0600' <= c <= '\u06FF')
    return 'ar' if arabic_chars > 3 else 'id'


_LANG_NAMES = {"ar": "العربية", "id": "الإندونيسية (Bahasa Indonesia)"}


def _system_with_language(language: Optional[str]) -> str:
    """Append a hard language directive to the system prompt when a UI language is given."""
    if language in _LANG_NAMES:
        return (
            SYSTEM_PROMPT
            + f"\n\nمهم جداً: اكتب ردك بالكامل باللغة {_LANG_NAMES[language]} فقط، "
            f"بغض النظر عن اللغة التي طُرح بها السؤال."
        )
    return SYSTEM_PROMPT


PLACE_HINTS = (
    "قرية", "مسجد", "جامع", "مدرسة", "بلدة", "مدينة", "منطقة", "جزيرة", "وادي", "جبل",
    "desa", "dusun", "kampung", "kelurahan", "kecamatan", "kabupaten", "masjid",
    "mesjid", "gereja", "sekolah", "pulau", "gunung", "kota", "village", "mosque",
)


def _looks_like_place_query(text: str) -> bool:
    """Cheap gate before paying for a geocoding round trip.

    A question about cost or method needs no coordinates; a question naming a
    village or a mosque does. Short messages are treated as place names, since
    that is how people actually type them into a map.
    """
    lowered = text.lower()
    if any(h in lowered for h in PLACE_HINTS):
        return True
    words = text.split()
    if len(words) <= 6 and any(len(w) >= 4 for w in words):
        return True
    return bool(re.search(r"\b[A-Z][a-z]{3,}\b", text))


def _facts_block(place: Dict[str, Any], facts: Dict[str, Any]) -> str:
    """Render measured values as a block the model is told to obey."""
    rows = []
    if place:
        label = f" — {place['label']}" if place.get("label") else ""
        rows.append(f"المكان المطابق في OpenStreetMap: {place['name']}{label}")
        rows.append(f"التصنيف: {place.get('category', 'place')}")
    rows.append(f"الإحداثيات: {facts['latitude']}, {facts['longitude']}")

    if facts.get("bedrock_unit"):
        rows.append(
            f"الوحدة الصخرية: {facts['bedrock_unit']} | نوع الصخر: "
            f"{facts.get('lithology') or 'غير محدد'} | العمر: {facts.get('age') or 'غير محدد'}"
        )
        rows.append(f"مصدر الجيولوجيا: {facts.get('geology_source')}")
    if facts.get("elevation_m") is not None:
        rows.append(
            f"الارتفاع: {facts['elevation_m']} م فوق سطح البحر | ميل السطح: "
            f"{facts.get('slope_deg', '؟')}° ({facts.get('terrain_source')})"
        )
    if facts.get("rainfall_mm_per_year") is not None:
        rows.append(
            f"معدل الأمطار السنوي: {facts['rainfall_mm_per_year']} ملم "
            f"({facts.get('rainfall_source')})"
        )
    if facts.get("restricted_within_1500m"):
        rows.append(
            "مواقع ممنوع الحفر فيها ضمن 1.5 كم: "
            + "، ".join(facts["restricted_within_1500m"])
        )
    else:
        rows.append("لا توجد مواقع ممنوعة مسجّلة ضمن 1.5 كم من هذه النقطة.")

    body = "\n".join(f"- {r}" for r in rows)
    return (
        "=== بيانات ميدانية مقيسة (استعملها حرفياً ولا تخالفها) ===\n"
        f"{body}\n"
        "=== نهاية البيانات ==="
    )


def _ground(text: str) -> Optional[str]:
    """Resolve a place named in the message and pull real values for it."""
    if not _looks_like_place_query(text):
        return None
    try:
        from app.services.geo_service import resolve_place, site_facts
        place = resolve_place(text)
        if not place:
            return None
        facts = site_facts(place["lat"], place["lon"])
        return _facts_block(place, facts)
    except Exception as e:  # noqa: BLE001
        print(f"Grounding failed: {e}")
        return None


def chat_analysis(api_key: str, user_message: str, conversation_history: list = None,
                  language: Optional[str] = None) -> str:
    """Chat entry point. Grounds the question in measured data when the user
    names a place, then answers from that data instead of from memory."""

    lang = language if language in _LANG_NAMES else _detect_language(user_message)
    system = _system_with_language(lang)

    grounding = _ground(user_message)
    prompt = f"{grounding}\n\n{user_message}" if grounding else user_message

    messages: List[Dict[str, str]] = []
    if conversation_history:
        messages.extend(conversation_history)
    messages.append({"role": "user", "content": prompt})

    result = _call_ai(system, messages)
    if result:
        return result

    if api_key and api_key.startswith("sk-ant"):
        try:
            client = anthropic.Anthropic(api_key=api_key)
            for model in ["claude-sonnet-4-20250514", "claude-3-7-sonnet-20250219",
                          "claude-3-5-sonnet-20241022", "claude-3-haiku-20240307"]:
                try:
                    response = client.messages.create(
                        model=model, max_tokens=3000, system=system, messages=messages
                    )
                    return response.content[0].text
                except Exception:
                    continue
        except Exception as e:
            print(f"Anthropic client error: {e}")

    # No provider answered. Hand back the measured data if we have it and say
    # plainly that the analysis engine is down — never a canned essay.
    if grounding:
        return (
            "تعذّر الوصول إلى محرّك التحليل الآن، لكن هذه هي البيانات المقيسة "
            "للموقع الذي سألت عنه:\n\n" + grounding.replace("=== ", "").replace(" ===", "")
        )
    return (
        "تعذّر الوصول إلى محرّك التحليل الآن. أعد المحاولة بعد قليل، أو اكتب اسم "
        "المكان بدقة أكبر لأجلب لك بياناته الجيولوجية المقيسة مباشرة."
    )


def analyze_location(api_key: str, latitude: float, longitude: float,
                     context_data: Optional[Dict[str, Any]] = None,
                     language: Optional[str] = None) -> str:
    try:
        from app.services.geo_service import site_facts
        facts = site_facts(latitude, longitude)
        grounding = _facts_block({}, facts)
    except Exception as e:  # noqa: BLE001
        print(f"Site facts failed: {e}")
        grounding = ""

    prompt = (
        f"{grounding}\n\n"
        f"حلّل هذا الموقع لأغراض حفر بئر مياه جوفية خيري.\n"
        f"بيانات سياقية من الواجهة: {context_data if context_data else 'لا يوجد'}.\n"
        f"قدّم تقييماً فنياً موجزاً يشمل: نوع الطبقة الحاملة المتوقعة، العمق التقديري "
        f"للحفر، طريقة الحفر المقترحة، نسبة النجاح المتوقعة، وجودة المياه المتوقعة — "
        f"كلها مبنية على البيانات المقيسة أعلاه."
    )
    result = _call_ai(_system_with_language(language), [{"role": "user", "content": prompt}])
    if result:
        return result
    return (
        "تعذّر الوصول إلى محرّك التحليل الآن. هذه البيانات المقيسة للنقطة:\n\n"
        + grounding.replace("=== ", "").replace(" ===", "")
    )


def generate_report(api_key: str, area_data: Dict[str, Any],
                    language: Optional[str] = None) -> str:
    grounding = ""
    lat, lon = area_data.get("latitude"), area_data.get("longitude")
    if lat is not None and lon is not None:
        try:
            from app.services.geo_service import site_facts
            grounding = _facts_block({}, site_facts(float(lat), float(lon)))
        except Exception as e:  # noqa: BLE001
            print(f"Report grounding failed: {e}")

    prompt = (
        f"{grounding}\n\n"
        f"أنشئ تقرير استكشاف وتقييم مياه جوفية رسمياً ومفصلاً بصيغة Markdown "
        f"للموقع التالي: {area_data.get('bbox', 'جزيرة فلوريس')}.\n"
        f"بيانات الواجهة: {area_data}.\n"
        f"يجب أن يشمل التقرير: ملخصاً تنفيذياً، الوضع الجيولوجي والهيدروجيولوجي "
        f"مبنياً على البيانات المقيسة أعلاه، المواصفات الهندسية للحفر، ميزانية "
        f"تقديرية في جدول، وتوصيات نهائية. وضّح في كل رقم تقديري أنه تقدير."
    )
    result = _call_ai(_system_with_language(language), [{"role": "user", "content": prompt}])
    if result:
        return result
    return (
        "تعذّر الوصول إلى محرّك التحليل الآن، فلم يُنشأ التقرير. "
        + ("هذه البيانات المقيسة للموقع:\n\n" + grounding.replace("=== ", "").replace(" ===", "")
           if grounding else "أعد المحاولة بعد قليل.")
    )
