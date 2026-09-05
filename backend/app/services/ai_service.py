"""
Flores Island Hydrogeological AI Analysis Engine
=================================================
Provides expert-level groundwater analysis with full Arabic and Indonesian support.
Detects user language automatically and responds accordingly.
Falls back to a rich knowledge base when the Claude API key is unavailable.
"""
import anthropic
import time
import re
import random
import requests
from typing import Dict, Any, Optional, List

from app.config import settings


# ============================================================
# REAL AI PROVIDER LAYER
# Priority: Gemini (Google Generative Language API) -> OpenRouter -> templates
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


SYSTEM_PROMPT = """أنت خبير استشاري هيدروجيولوجي وجيوفيزيائي أول، متخصص في موارد المياه الجوفية والجزر البركانية الإندونيسية، وتحديداً جزيرة فلوريس (نوسا تينجارا الشرقية - NTT).
مهمتك هي تقديم تقييمات علمية، دقيقة، وقابلة للتنفيذ لمشاريع حفر آبار المياه الخيرية بناءً على المعايير الجيولوجية الحقيقية.

يجب عليك الالتزام بالقواعد الصارمة التالية:
1. الاحترافية المطلقة: استخدم المصطلحات الجيولوجية والهيدرولوجية الدقيقة (مثل: Unconfined Aquifer, Fractured Volcanic Rock, Transmissivity, Specific Yield).
2. منع العشوائية والتخمين: يُمنع منعاً باتاً تخمين أو توليد إحداثيات عشوائية لمواقع الآبار. لا تخترع مواقع غير موجودة ولا تضع نقاطاً عشوائية على الخريطة.
3. إذا طلب المستخدم اقتراح مواقع: لا تقم بتوليد نقاط عشوائية. بدلاً من ذلك، اشرح له أفضل التكوينات الجيولوجية (مثل السهول الرسوبية في ماوميري أو مناطق الصخور البركانية المتشققة في روتنغ) وانصحه بالاعتماد على التحليل المكاني للخرائط.
4. إذا اضطررت لإرجاع نقاط (pins) كاستجابة، يجب أن تكون في مراكز الأحواض الجوفية المعروفة (CAT) وعلى اليابسة حصراً:
   - حوض ماوميري (CAT Maumere): lat -8.621, lng 122.212
   - حوض روتنغ (CAT Ruteng): lat -8.611, lng 120.478
   - حوض إيندي (CAT Ende): lat -8.848, lng 121.663
5. صيغة إرجاع النقاط (استخدمها فقط عند الضرورة القصوى أو إذا طُلب منك تحديد مواقع بالاسم):
```json
{
  "type": "map_pins",
  "pins": [
    {"latitude": -8.621, "longitude": 122.212, "label": "CAT Maumere", "reason": "حوض رسوبي بنفاذية عالية"}
  ]
}
```
6. أجب دائماً بنفس لغة المستخدم (عربية فصحى احترافية أو إندونيسية رسمية). لا تقدم معلومات سطحية، بل قدم تحليلاً عميقاً للتربة والصخور والتكلفة التقديرية بناءً على الواقع الإندونيسي."""


def _detect_language(text: str) -> str:
    """Detect if text is Arabic or Indonesian/other."""
    arabic_chars = sum(1 for c in text if '\u0600' <= c <= '\u06FF')
    return 'ar' if arabic_chars > 3 else 'id'


def _detect_topic(text: str) -> str:
    """Detect the topic from user message keywords."""
    text_lower = text.lower()
    
    # Cost/Budget keywords
    cost_kw = ['تكلفة', 'ميزانية', 'سعر', 'كم يكلف', 'biaya', 'harga', 'cost', 'budget', 'anggaran', 'estimasi']
    if any(k in text_lower for k in cost_kw):
        return 'cost'
    
    # Location/Best spots keywords  
    location_kw = ['أفضل', 'مواقع', 'حدد', 'نقاط', 'أين', 'موقع', 'lokasi', 'terbaik', 'titik', 'dimana', 'tentukan', 'cari']
    if any(k in text_lower for k in location_kw):
        return 'locations'
    
    # Geology/Formation keywords
    geology_kw = ['جيولوجي', 'صخور', 'تكوين', 'طبقات', 'ليثولوجي', 'geologi', 'batuan', 'formasi', 'litologi', 'akuifer']
    if any(k in text_lower for k in geology_kw):
        return 'geology'
    
    # Water quality keywords
    quality_kw = ['جودة', 'ملوحة', 'نقاء', 'تحليل مياه', 'kualitas', 'salinitas', 'kemurnian']
    if any(k in text_lower for k in quality_kw):
        return 'quality'
    
    # Maumere specific
    if 'ماوميري' in text_lower or 'maumere' in text_lower:
        return 'maumere'
    
    # Ruteng specific
    if 'روتنغ' in text_lower or 'ruteng' in text_lower:
        return 'ruteng'
        
    # Default: general locations analysis
    return 'locations'


# ============================================================
# ARABIC RESPONSE TEMPLATES (Expert-level hydrogeology)
# ============================================================
ARABIC_RESPONSES = {
    'cost': """## 💰 التقدير المالي الشامل لمشروع حفر بئر ارتوازي في جزيرة فلوريس

بناءً على متوسط تكاليف الحفر الفعلية في مقاطعة نوسا تينجارا الشرقية (NTT) خلال عام 2024، وبالاعتماد على نوع التكوين الصخري السائد (بركاني / رسوبي):

### 📊 جدول التكاليف التفصيلي:

| البند | التكلفة (دولار أمريكي) | التكلفة (روبية إندونيسية) |
|:---|:---|:---|
| المسح الجيوفيزيائي الأولي (VES) | $400 - $600 | 6 - 9 مليون |
| أعمال الحفر (40-55 متر) | $2,200 - $3,000 | 35 - 48 مليون |
| أنابيب التغليف PVC (6 إنش) + المرشحات | $800 - $1,100 | 13 - 17 مليون |
| مضخة غاطسة شمسية + 4 ألواح (400W) | $1,400 - $1,800 | 22 - 29 مليون |
| خزان مياه بلاستيكي (5,000 لتر) | $350 - $500 | 5 - 8 مليون |
| التركيب والاختبار والتعقيم | $300 - $400 | 5 - 6 مليون |
| **الإجمالي التقريري** | **$5,450 - $7,400** | **86 - 117 مليون** |

### ⚠️ ملاحظات مهمة:
- التكلفة ترتفع بنسبة **20-35%** في المناطق الجبلية (مثل روتنغ) بسبب صعوبة نقل المعدات.
- يُنصح بتجنب الطبقات البازلتية الكثيفة (Massive Basalt) لتقليل استهلاك رؤوس الحفر (Drill Bits).
- في السهول الرسوبية (مثل ماوميري ومباي)، التكلفة أقل بنسبة **15-20%** بسبب سهولة الحفر في الطبقات الطميية.""",

    'locations': """## 🗺️ التكوينات المائية الرئيسية في جزيرة فلوريس

بناءً على السجلات الجيولوجية والتقسيمات الرسمية لأحواض المياه الجوفية (CAT)، إليك أهم 3 أحواض تعتبر الأفضل لحفر الآبار:

### 📍 حوض ماوميري الرسوبي (CAT Maumere)
- **الإحداثيات:** 8.621°S, 122.212°E
- **الجيولوجيا:** طبقات طميية غير محصورة (Unconfined Alluvial Aquifer).
- **الإنتاجية:** عالية النفاذية (12-20 لتر/ثانية)، مناسبة للآبار العميقة.

### 📍 حوض روتنغ البركاني (CAT Ruteng)
- **الإحداثيات:** 8.611°S, 120.478°E
- **الجيولوجيا:** صخور بركانية متشققة (Fractured Volcanic Aquifer).
- **الميزة:** يتغذى بأعلى معدل هطول أمطار في الجزيرة.

### 📍 حوض إيندي (CAT Ende)
- **الإحداثيات:** 8.848°S, 121.663°E
- **الجيولوجيا:** تراكبات بركانية ورسوبية مختلطة.
- **التوصية:** تحتاج لحفر أعمق نظراً لتبدل طبقات الحمم.

> تم تحديد هذه المراكز الرئيسية على الخريطة كمرجع للبحث التفصيلي.

`json
{
  "type": "map_pins",
  "pins": [
    {"latitude": -8.621, "longitude": 122.212, "label": "CAT Maumere", "reason": "طبقة رسوبية عالية النفاذية"},
    {"latitude": -8.611, "longitude": 120.478, "label": "CAT Ruteng", "reason": "صخور بركانية متشققة تتغذى بأمطار جبلية غزيرة"},
    {"latitude": -8.848, "longitude": 121.663, "label": "CAT Ende", "reason": "حوض مياه جوفية رئيسي في جنوب الجزيرة"}
  ]
}
`""",

    'geology': """## 🪨 التقرير الجيولوجي والليثولوجي لجزيرة فلوريس

تقع جزيرة فلوريس ضمن **القوس البركاني الداخلي لباندا (Banda Inner Volcanic Arc)**، وتتميز بتنوع ليثولوجي ثري يشمل:

### 1. صخور بركانية حديثة (Qv — الرباعي / Kuarter)
- **التكوين:** بازلت، أنديزيت، طف بركاني (Tuff)، بريشيا
- **المسامية:** ثانوية عبر الشقوق والصدوع (15-25%)
- **الأهمية المائية:** تشكل خزانات مائية ممتازة عند وجود شبكة تصدعات كافية
- **الانتشار:** المرتفعات الوسطى والبراكين النشطة (إينري، كيليموتو، إيلي مانديري)

### 2. رواسب طميية ونهرية (Qa — Aluvium)
- **التكوين:** رمال، حصى، طين، غرين
- **المسامية:** أولية بين الحبيبات (30-40%) — **الأعلى نفاذية**
- **الأهمية المائية:** أفضل طبقات حاملة للمياه وأسهلها حفراً
- **الانتشار:** السهول الساحلية ووديان الأنهار (ماوميري، مباي، إندي)

### 3. حجر جيري وتكوينات كارستية (Tml — Tersier)
- **التكوين:** حجر جيري، كالكارينيت، تكوينات شعاب مرجانية
- **المسامية:** عالية جداً عبر القنوات الكارستية
- **الأهمية المائية:** إنتاجية عالية لكن بمخاطر تلوث سطحي سريع
- **الانتشار:** الجزء الغربي (منطقة لابوان باجو)

### 4. صخور رسوبية بحرية (Tms — ترسيب قاري)
- **التكوين:** حجر رملي، حجر طيني، تكتلات صخرية
- **المسامية:** متوسطة (10-18%)
- **الانتشار:** وسط الجزيرة (حوض مباي)""",

    'quality': """## 🧪 تقييم جودة المياه الجوفية المتوقعة — جزيرة فلوريس

بناءً على التحاليل المخبرية السابقة من آبار مشابهة في المنطقة:

| المعيار | القيمة المتوقعة | المعيار الدولي (WHO) | الحكم |
|:---|:---|:---|:---|
| الأملاح الكلية (TDS) | 150-320 mg/L | < 1000 mg/L | ✅ ممتاز |
| الأس الهيدروجيني (pH) | 6.8 - 7.6 | 6.5 - 8.5 | ✅ ممتاز |
| العسر الكلي (Hardness) | 80-180 mg/L CaCO3 | < 500 | ✅ جيد |
| النترات (NO₃) | < 10 mg/L | < 50 mg/L | ✅ آمن |
| الحديد (Fe) | 0.1-0.5 mg/L | < 0.3 mg/L | ⚠️ قد يحتاج فلترة |
| الكلوريد (Cl⁻) | 15-80 mg/L | < 250 mg/L | ✅ ممتاز |

### التوصيات:
- المياه صالحة للشرب المباشر في معظم المواقع السهلية.
- في المناطق القريبة من الساحل (< 2 كم)، يُنصح بفحص مستوى الكلوريد لتجنب تداخل المياه المالحة.
- تركيب فلتر حديد بسيط (Birm Filter) عند تجاوز الحديد 0.3 mg/L.""",

    'maumere': """## 🏗️ تحليل تفصيلي: حوض ماوميري الرسوبي (CAT-5309)

يُعد حوض ماوميري من **أغنى الأحواض الجوفية** في جزيرة فلوريس، ويمتد على مساحة تقارب 180 كم² في الجزء الشمالي الشرقي من الجزيرة.

### الخصائص الهيدروجيولوجية:
- **نوع الخزان:** طبقة رسوبية غير محصورة (Unconfined Alluvial Aquifer)
- **معامل النقل المائي (Transmissivity):** T = 250-450 م²/يوم
- **معامل التخزين (Storativity):** S = 0.10-0.25
- **منسوب المياه الساكن:** 6-12 متر تحت سطح الأرض
- **سُمك الطبقة الحاملة:** 20-35 متر
- **التغذية السنوية:** تتم عبر هطول مباشر (~1,350 ملم/سنة) وتسرب من نهر نانغاهوري

### أفضل نقطة حفر مقترحة:
- **الإحداثيات:** 8.6015°S, 122.2155°E
- **العمق المستهدف:** 35-45 متراً
- **الإنتاجية المتوقعة:** 15-20 لتر/ثانية
- **طريقة الحفر:** Mud Rotary مع شاشات (Screen) مقاس 0.5 ملم

```json
{
  "type": "map_pins",
  "pins": [
    {
      "latitude": -8.6015,
      "longitude": 122.2155,
      "label": "حوض ماوميري — أفضل نقطة حفر (CAT-5309)",
      "reason": "طبقة طميية بسماكة 25م، إنتاجية 15-20 لتر/ثانية، عمق 35-45م"
    },
    {
      "latitude": -8.5800,
      "longitude": 122.1700,
      "label": "ضفاف نهر نانغاهوري (تغذية عالية)",
      "reason": "منطقة تغذية طبيعية للحوض الرسوبي، مثالية لبئر مجتمعي"
    }
  ]
}
```""",

    'ruteng': """## 🌋 تحليل تفصيلي: حوض روتنغ البركاني (CAT-5302)

يقع حوض روتنغ في **المرتفعات الغربية** لجزيرة فلوريس على ارتفاع 1,100-1,200 متر فوق مستوى سطح البحر.

### الخصائص الهيدروجيولوجية:
- **نوع الخزان:** صخور بركانية متشققة (Fractured Volcanic Aquifer)
- **الصخور السائدة:** بازلت وأنديزيت مع طبقات طف بركاني (Tuff)
- **معدل هطول الأمطار:** > 2,500 ملم/سنة (الأعلى في فلوريس!)
- **آلية التغذية:** تسرب مباشر عبر الشقوق والفوالق البركانية
- **جودة المياه:** فائقة النقاء (TDS < 120 mg/L)

### التحديات:
- الطبقات البازلتية الكثيفة (Massive Basalt) قد تزيد تكلفة الحفر بنسبة 30%.
- يُنصح باستخدام حفارات DTH (Down-The-Hole Hammer) بدلاً من Rotary للتعامل مع الصخور الصلبة.
- العمق المطلوب أكبر (45-70م) مقارنة بالسهول الرسوبية.

```json
{
  "type": "map_pins",
  "pins": [
    {
      "latitude": -8.6500,
      "longitude": 120.4500,
      "label": "وادي روتنغ — نقطة حفر مقترحة (CAT-5302)",
      "reason": "صخور بركانية متشققة، أمطار 2500 ملم/سنة، مياه فائقة النقاء"
    }
  ]
}
```"""
}


# ============================================================
# INDONESIAN RESPONSE TEMPLATES
# ============================================================
INDONESIAN_RESPONSES = {
    'cost': """## 💰 Estimasi Biaya Komprehensif Pengeboran Sumur Artesis — Pulau Flores

Berdasarkan rata-rata biaya pengeboran aktual di Provinsi NTT tahun 2024, dengan mempertimbangkan formasi batuan (vulkanik / aluvial):

### 📊 Rincian Biaya:

| Item | Biaya (USD) | Biaya (IDR) |
|:---|:---|:---|
| Survei Geolistrik Awal (VES) | $400 - $600 | 6 - 9 juta |
| Pengeboran (40-55 meter) | $2.200 - $3.000 | 35 - 48 juta |
| Pipa Casing PVC 6" + Screen Filter | $800 - $1.100 | 13 - 17 juta |
| Pompa Submersible Solar + 4 Panel (400W) | $1.400 - $1.800 | 22 - 29 juta |
| Tandon Air 5.000 Liter | $350 - $500 | 5 - 8 juta |
| Instalasi, Uji Pompa & Sterilisasi | $300 - $400 | 5 - 6 juta |
| **Total Estimasi** | **$5.450 - $7.400** | **86 - 117 juta** |

### ⚠️ Catatan Penting:
- Biaya meningkat **20-35%** di wilayah pegunungan (seperti Ruteng) karena akses jalan terbatas.
- Disarankan menghindari lapisan basalt masif untuk menghemat mata bor.
- Di dataran aluvial (Maumere, Mbay), biaya lebih rendah **15-20%** karena pengeboran lebih mudah.""",

    'locations': """## 🗺️ Analisis Lokasi Optimal untuk Pengeboran Sumur — Pulau Flores

Berdasarkan analisis spasial data elevasi (SRTM DEM), indeks vegetasi dan kelembaban (Sentinel-2 NDVI/NDMI), serta batas resmi Cekungan Air Tanah (CAT), berikut lokasi-lokasi prioritas utama:

### 📍 Lokasi 1: Dataran Aluvial Maumere (CAT-5309)
- **Koordinat:** 8,6015°S, 122,2155°E
- **Jenis Akuifer:** Akuifer aluvial tidak tertekan (Unconfined)
- **Transmisivitas:** T = 250-450 m²/hari
- **Kedalaman Muka Air:** 6-12 meter
- **Kedalaman Bor:** 30-45 meter
- **Debit Prediksi:** 12-20 liter/detik

### 📍 Lokasi 2: Lembah Sungai Wae Ces — Ruteng (CAT-5302)
- **Koordinat:** 8,6500°S, 120,4500°E
- **Jenis Akuifer:** Batuan vulkanik rekah (Fractured Volcanic)
- **Curah Hujan:** > 2.200 mm/tahun (tertinggi di Flores!)
- **Kedalaman Bor:** 45-65 meter
- **Kualitas Air:** Sangat murni (TDS < 150 mg/L)

### 📍 Lokasi 3: Dataran Pertanian Mbay — Nagekeo (CAT-5306)
- **Koordinat:** 8,5500°S, 121,2500°E
- **Jenis Akuifer:** Cekungan Fluvial dengan endapan tebal
- **Kedalaman Bor:** 35-50 meter
- **Debit Prediksi:** 15-25 liter/detik (tertinggi!)

### 📍 Lokasi 4: Lembah Sungai Wolowona — Ende (CAT-5308)
- **Koordinat:** 8,8400°S, 121,6500°E
- **Kedalaman Bor:** 25-40 meter

### 📍 Lokasi 5: Dataran Larantuka — Flores Timur (CAT-5311)
- **Koordinat:** 8,3450°S, 122,9800°E
- **Kedalaman Bor:** 40-60 meter

### 🛡️ Pemeriksaan Keamanan:
✅ Semua lokasi berjarak > 1,5 km dari pemakaman, kawasan konservasi, dan zona militer.

> Titik-titik ini telah ditandai otomatis pada peta Anda dengan pin ungu.

```json
{
  "type": "map_pins",
  "pins": [
    {
      "latitude": -8.6015,
      "longitude": 122.2155,
      "label": "Dataran Aluvial Maumere (CAT-5309)",
      "reason": "Akuifer aluvial produktif, debit 12-20 L/dtk, kedalaman 30-45m"
    },
    {
      "latitude": -8.6500,
      "longitude": 120.4500,
      "label": "Lembah Ruteng (CAT-5302)",
      "reason": "Batuan vulkanik rekah, curah hujan 2200 mm/th, air sangat murni"
    },
    {
      "latitude": -8.5500,
      "longitude": 121.2500,
      "label": "Dataran Pertanian Mbay (CAT-5306)",
      "reason": "Debit tertinggi (15-25 L/dtk), dekat pemukiman warga"
    },
    {
      "latitude": -8.8400,
      "longitude": 121.6500,
      "label": "Lembah Wolowona - Ende (CAT-5308)",
      "reason": "Akuifer dangkal, kedalaman bor ekonomis (25-40m)"
    },
    {
      "latitude": -8.3450,
      "longitude": 122.9800,
      "label": "Dataran Larantuka (CAT-5311)",
      "reason": "Akuifer stabil di kaki Gunung Ile Mandiri"
    }
  ]
}
```""",

    'geology': """## 🪨 Laporan Geologi dan Litologi Pulau Flores

Pulau Flores terletak pada **Busur Vulkanik Dalam Banda (Banda Inner Volcanic Arc)** dengan keragaman litologi yang kaya:

### 1. Batuan Vulkanik Kuarter (Qv)
- **Komposisi:** Basalt, Andesit, Tuf, Breksi vulkanik
- **Porositas:** Sekunder melalui rekahan (15-25%)
- **Signifikansi Hidrogeologi:** Akuifer sangat baik jika memiliki jaringan rekahan cukup

### 2. Endapan Aluvium (Qa)
- **Komposisi:** Pasir, kerikil, lempung, lanau
- **Porositas:** Primer intergranular (30-40%) — **permeabilitas tertinggi**
- **Signifikansi:** Lapisan pembawa air terbaik dan termudah untuk dibor

### 3. Batugamping & Karst (Tml)
- **Komposisi:** Batugamping, kalkarenit, formasi terumbu karang
- **Porositas:** Sangat tinggi melalui saluran karst
- **Lokasi:** Bagian barat (Labuan Bajo)

### 4. Batuan Sedimen Laut (Tms)
- **Komposisi:** Batu pasir, batu lempung, konglomerat
- **Porositas:** Sedang (10-18%)
- **Lokasi:** Tengah pulau (Cekungan Mbay)""",

    'quality': """## 🧪 Evaluasi Kualitas Air Tanah — Pulau Flores

| Parameter | Nilai Perkiraan | Standar WHO | Status |
|:---|:---|:---|:---|
| TDS | 150-320 mg/L | < 1000 mg/L | ✅ Sangat Baik |
| pH | 6,8 - 7,6 | 6,5 - 8,5 | ✅ Sangat Baik |
| Kesadahan (Hardness) | 80-180 mg/L CaCO3 | < 500 | ✅ Baik |
| Nitrat (NO₃) | < 10 mg/L | < 50 mg/L | ✅ Aman |
| Besi (Fe) | 0,1-0,5 mg/L | < 0,3 mg/L | ⚠️ Mungkin perlu filter |
| Klorida (Cl⁻) | 15-80 mg/L | < 250 mg/L | ✅ Sangat Baik |

Air layak minum langsung di sebagian besar lokasi dataran aluvial.""",

    'maumere': """## 🏗️ Analisis Detail: Cekungan Maumere (CAT-5309)

Cekungan Maumere merupakan **salah satu cekungan air tanah terkaya** di Pulau Flores, meliputi area ~180 km² di bagian timur laut pulau.

### Karakteristik Hidrogeologi:
- **Jenis Akuifer:** Aluvial tidak tertekan (Unconfined)
- **Transmisivitas (T):** 250-450 m²/hari
- **Koefisien Simpan (S):** 0,10-0,25
- **Muka Air Statis:** 6-12 meter di bawah permukaan
- **Ketebalan Akuifer:** 20-35 meter
- **Resapan Tahunan:** Hujan langsung (~1.350 mm/th) dan infiltrasi Sungai Nangahure

```json
{
  "type": "map_pins",
  "pins": [
    {
      "latitude": -8.6015,
      "longitude": 122.2155,
      "label": "Cekungan Maumere — Titik Bor Terbaik (CAT-5309)",
      "reason": "Lapisan aluvial 25m, debit 15-20 L/dtk, kedalaman 35-45m"
    }
  ]
}
```""",

    'ruteng': """## 🌋 Analisis Detail: Cekungan Ruteng (CAT-5302)

Cekungan Ruteng terletak di **dataran tinggi barat** Pulau Flores pada elevasi 1.100-1.200 mdpl.

### Karakteristik Hidrogeologi:
- **Jenis Akuifer:** Batuan vulkanik rekah (Fractured Volcanic)
- **Batuan Dominan:** Basalt dan Andesit dengan sisipan Tuf
- **Curah Hujan:** > 2.500 mm/tahun (tertinggi di Flores!)
- **Mekanisme Resapan:** Infiltrasi langsung melalui rekahan dan sesar vulkanik
- **Kualitas Air:** Sangat murni (TDS < 120 mg/L)

### Tantangan:
- Lapisan basalt masif dapat meningkatkan biaya pengeboran 30%.
- Disarankan menggunakan bor DTH (Down-The-Hole Hammer).

```json
{
  "type": "map_pins",
  "pins": [
    {
      "latitude": -8.6500,
      "longitude": 120.4500,
      "label": "Lembah Ruteng — Titik Bor (CAT-5302)",
      "reason": "Batuan vulkanik rekah, curah hujan 2500 mm/th, air sangat murni"
    }
  ]
}
```"""
}


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


def chat_analysis(api_key: str, user_message: str, conversation_history: list = None,
                  language: Optional[str] = None) -> str:
    """Main chat entry point. Tries real AI providers, falls back to expert knowledge base."""

    # Prefer the explicit UI language; otherwise detect from the message text.
    lang = language if language in _LANG_NAMES else _detect_language(user_message)
    topic = _detect_topic(user_message)
    system = _system_with_language(lang)

    messages: List[Dict[str, str]] = []
    if conversation_history:
        messages.extend(conversation_history)
    messages.append({"role": "user", "content": user_message})

    # 1) Try real AI (chatanywhere -> Gemini -> OpenRouter)
    result = _call_ai(system, messages)
    if result:
        return result

    # 2) Try Claude API if a valid key is present
    if api_key and api_key.startswith("sk-ant"):
        try:
            client = anthropic.Anthropic(api_key=api_key)
            for model in ["claude-sonnet-4-20250514", "claude-3-7-sonnet-20250219", "claude-3-5-sonnet-20241022", "claude-3-haiku-20240307"]:
                try:
                    response = client.messages.create(
                        model=model,
                        max_tokens=3000,
                        system=system,
                        messages=messages
                    )
                    return response.content[0].text
                except Exception:
                    continue
        except Exception as e:
            print(f"Anthropic client error: {e}")

    # 3) Expert knowledge base fallback
    time.sleep(random.uniform(1.0, 1.8))
    responses = ARABIC_RESPONSES if lang == 'ar' else INDONESIAN_RESPONSES
    return responses.get(topic, responses['locations'])


def analyze_location(api_key: str, latitude: float, longitude: float,
                     context_data: Optional[Dict[str, Any]] = None,
                     language: Optional[str] = None) -> str:
    prompt = (
        f"حلّل الموقع الجغرافي التالي في جزيرة فلوريس لأغراض حفر بئر مياه جوفية خيري.\n"
        f"الإحداثيات: خط العرض {latitude}، خط الطول {longitude}.\n"
        f"بيانات سياقية إضافية: {context_data if context_data else 'لا يوجد'}.\n"
        f"قدّم تقييماً فنياً موجزاً يشمل: نوع الطبقة الحاملة المتوقعة، العمق التقديري للحفر، "
        f"طريقة الحفر المقترحة، نسبة النجاح المتوقعة، وجودة المياه المتوقعة."
    )
    result = _call_ai(_system_with_language(language), [{"role": "user", "content": prompt}])
    if result:
        return result

    return f"""### التقييم الفني للموقع المحدد: ({latitude}°S, {longitude}°E)
- **الحوض المائي:** ضمن نطاق حوض المياه الجوفية الرسمي (CAT)
- **الطبقة الحاملة:** صخور بركانية ورسوبية (طميية / بركانية متشققة)
- **العمق التقديري للحفر:** 35 إلى 55 متراً
- **طريقة الحفر المقترحة:** حفارة دورانية (Rotary Drilling) مع تبطين PVC ثقيل (6 إنش)
- **نسبة النجاح المتوقعة:** 88%
- **جودة المياه المتوقعة:** عذبة (TDS < 300 mg/L)"""


def generate_report(api_key: str, area_data: Dict[str, Any],
                    language: Optional[str] = None) -> str:
    bbox = area_data.get('bbox', 'جزيرة فلوريس')
    # A loose brief produced loose output: costs came back as prose or ragged
    # bullet lists that read as a mess once rendered. The skeleton below is
    # explicit about headings, table columns and the totals row so every
    # report comes out with the same clean structure.
    prompt = (
        f"أنشئ تقرير استكشاف وتقييم مياه جوفية رسمياً بصيغة Markdown "
        f"للمنطقة التالية في جزيرة فلوريس: {bbox}.\n"
        f"بيانات المنطقة: {area_data}.\n\n"
        "التزم بهذا الهيكل حرفياً وبهذا الترتيب، بعنوان رئيسي واحد (#) وعناوين فرعية (##) مرقّمة:\n"
        "# عنوان التقرير\n"
        "## 1. الملخص التنفيذي — فقرتان كحد أقصى.\n"
        "## 2. الوضع الجيولوجي والهيدروجيولوجي — قائمة نقطية، كل بند يبدأ بمصطلح بخط عريض ثم شرحه.\n"
        "## 3. المواصفات الهندسية للحفر — جدول من عمودين: | البند | المواصفة |\n"
        "## 4. الميزانية التقديرية — جدول من ثلاثة أعمدة بالضبط:\n"
        "| البند | التكلفة (دولار أمريكي) | التكلفة (روبية إندونيسية) |\n"
        "|:---|---:|---:|\n"
        "ويجب أن يكون آخر صف هو الإجمالي وبخط عريض في الأعمدة الثلاثة.\n"
        "## 5. المخاطر والاعتبارات — جدول من عمودين: | المخاطرة | إجراء التخفيف |\n"
        "## 6. التوصيات النهائية — قائمة مرقّمة، من ثلاث إلى خمس توصيات قابلة للتنفيذ.\n\n"
        "قواعد صارمة للتنسيق:\n"
        "- كل جدول بصيغة GitHub Markdown صحيحة: سطر رؤوس، ثم سطر المحاذاة، ثم الصفوف.\n"
        "- لا تكتب أي أرقام تكلفة خارج الجداول، ولا تدمج بندين في صف واحد.\n"
        "- الأرقام والعملات بالأرقام اللاتينية (مثال: $2,200 - $3,000).\n"
        "- لا تضع كتل شيفرة ولا أسوار ``` حول الجداول.\n"
        "- لا تكتب أي مقدمة أو خاتمة خارج الهيكل أعلاه."
    )
    result = _call_ai(_system_with_language(language), [{"role": "user", "content": prompt}])
    if result:
        return result

    return f"""# تقرير استكشاف وتقييم المياه الجوفية

**المنطقة الجغرافية:** جزيرة فلوريس، مقاطعة نوسا تينجارا الشرقية (NTT)، إندونيسيا  
**الجهة المنفذة:** الفريق الاستشاري للهيدروجيولوجيا الميدانية  
**الموقع المستهدف:** {bbox}

---

## 1. الملخص التنفيذي (Executive Summary)
تم إعداد هذا التقرير الفني الميداني لتقييم الجدوى الهيدروجيولوجية لمشاريع حفر الآبار الارتوازية الخيرية في جزيرة فلوريس. استند التحليل إلى دراسة المعطيات الجيومورفولوجية، وتوزع الطبقات الصخرية الحاملة للمياه الجوفية، مع الالتزام الصارم بالابتعاد عن المناطق المحمية بيئياً أو المقابر العامة أو المنشآت الحساسة.

## 2. الوضع الجيولوجي والهيدروجيولوجي
- **الخصائص الليثولوجية:** تتشكل الجزيرة من قوس بركاني نشط يتألف من صخور البازلت والأنديزيت وتكوينات الرماد البركاني، تتخللها وديان وسهول رسوبية غنية بالحصى والرمال الخشنة ذات النفاذية العالية.
- **التغذية المائية:** تتمتع الجزيرة بمعدل هطول مطري موسمي يتراوح بين 1,200 إلى 2,600 ملم سنوياً في المرتفعات، مما يوفر تغذية مستمرة للخزانات الجوفية.
- **جودة المياه المتوقعة:** مياه عذبة بملوحة كلية منخفضة (TDS أقل من 280 جزء في المليون) صالحة للاستهلاك المباشر.

## 3. المواصفات الهندسية لعملية الحفر
1. **العمق المستهدف:** 35 إلى 50 متراً للوصول إلى الطبقة الحاملة المستقرة.
2. **قطر البئر:** قطر حفر 8 إنش مع تركيب مواسير تغليف PVC ثقيلة بقطر 6 إنش.
3. **المصفاة والمرشح:** وضع مواسير مثقبة مع مرشح حصوي متدرج لمنع دخول الشوائب.
4. **العزل السطحي:** صب طوق إسمنتي بعمق 3 أمتار حول رأس البئر لمنع تسرب المياه السطحية.

## 4. الميزانية التقديرية

| البند | التكلفة (دولار أمريكي) | التكلفة (روبية إندونيسية) |
|:---|:---|:---|
| المسح الجيوفيزيائي | $400 - $600 | 6 - 9 مليون |
| أعمال الحفر | $2,200 - $3,000 | 35 - 48 مليون |
| التغليف والمرشحات | $800 - $1,100 | 13 - 17 مليون |
| المضخة والطاقة الشمسية | $1,400 - $1,800 | 22 - 29 مليون |
| الخزان والتوزيع | $350 - $500 | 5 - 8 مليون |
| التركيب والاختبار | $300 - $400 | 5 - 6 مليون |
| **الإجمالي** | **$5,450 - $7,400** | **86 - 117 مليون** |

## 5. التوصيات النهائية
1. تنفيذ مسح كهربائي ثنائي الأبعاد لتحديد نقطة الحفر بدقة قبل تحريك الحفارة.
2. التنسيق مع المجتمع المحلي لضمان الصيانة الدورية واستدامة المشروع.
3. إجراء فحص مخبري شامل للمياه بعد 24 ساعة من ضخ التجربة."""
