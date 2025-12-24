"""
Gemini AI processor module for AuraMail.

VERSION: HYBRID (Hard Rules + AI + Safety Valve)

🛡️ Zero Trust Strategy:
- Hard Rules: Instant classification for known patterns (socials, newsletters, marketing)
- AI Analysis: Fallback for complex cases
- Safety Valve: Corrects AI mistakes (e.g., security alerts with unsubscribe buttons)
"""
import sys
import json
import time
import threading
from google import genai
from google.genai import types
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_message,
)
import logging
from redis import Redis
from config import GEMINI_API_KEY, REDIS_URL

# Налаштування логування
logger = logging.getLogger(__name__)

# Redis-based Global Rate Limiter для Gemini API
redis_client = Redis.from_url(REDIS_URL)
MAX_CALLS_PER_MINUTE = 30
GEMINI_RATE_LIMIT_KEY = 'gemini:rate_limit:calls'
GEMINI_SEMAPHORE = threading.Semaphore(1)
_last_request_time = threading.Lock()
_last_request_timestamp = 0

# Fix encoding for Windows console
if sys.platform == 'win32':
    try:
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8')
            sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass


def check_gemini_rate_limit():
    """Перевіряє глобальний rate limit для Gemini API."""
    try:
        now = int(time.time())
        unique_id = f"{now}:{threading.current_thread().ident}:{time.time()}"
        cutoff_time = now - 60
        redis_client.zremrangebyscore(GEMINI_RATE_LIMIT_KEY, 0, cutoff_time)
        current_calls = redis_client.zcard(GEMINI_RATE_LIMIT_KEY)
        
        if current_calls < MAX_CALLS_PER_MINUTE:
            redis_client.zadd(GEMINI_RATE_LIMIT_KEY, {unique_id: now})
            redis_client.expire(GEMINI_RATE_LIMIT_KEY, 120)
            print(f"✅ Rate limit check: {current_calls + 1}/{MAX_CALLS_PER_MINUTE} calls allowed")
            return True
        else:
            print(f"❌ Rate limit check: {current_calls}/{MAX_CALLS_PER_MINUTE} calls - LIMIT REACHED")
            return False
    except Exception as e:
        print(f"⚠️ Redis rate limiter error: {e}, allowing request (fallback)")
        return True


# --- 1. ЗАЛІЗНІ ПРАВИЛА (HARD RULES) ---
# Ці правила спрацьовують МИТТЄВО, економлячи час та гарантуючи точність.
HARD_RULES = {
    # --- СОЦМЕРЕЖІ (SOCIAL) ---
    "facebook": ("SOCIAL", "ARCHIVE", "AuraMail/Social"),
    "instagram": ("SOCIAL", "ARCHIVE", "AuraMail/Social"),
    "linkedin": ("SOCIAL", "ARCHIVE", "AuraMail/Social"),
    "twitter": ("SOCIAL", "ARCHIVE", "AuraMail/Social"),
    "tiktok": ("SOCIAL", "ARCHIVE", "AuraMail/Social"),
    "pinterest": ("SOCIAL", "ARCHIVE", "AuraMail/Social"),
    "friend request": ("SOCIAL", "ARCHIVE", "AuraMail/Social"),
    "новий друг": ("SOCIAL", "ARCHIVE", "AuraMail/Social"),
    
    # --- МАРКЕТИНГ ТА ПРОМО (ARCHIVE) ---
    "vbet": ("MARKETING", "ARCHIVE", "AuraMail/Promotions"),
    "casino": ("MARKETING", "ARCHIVE", "AuraMail/Promotions"),
    "free spin": ("MARKETING", "ARCHIVE", "AuraMail/Promotions"),
    "discount": ("MARKETING", "ARCHIVE", "AuraMail/Promotions"),
    "sale": ("MARKETING", "ARCHIVE", "AuraMail/Promotions"),
    "black friday": ("MARKETING", "ARCHIVE", "AuraMail/Promotions"),
    "знижка": ("MARKETING", "ARCHIVE", "AuraMail/Promotions"),
    "акція": ("MARKETING", "ARCHIVE", "AuraMail/Promotions"),
    
    # --- РОЗСИЛКИ ТА ІНФО (NEWSLETTER) ---
    "newsletter": ("NEWSLETTER", "ARCHIVE", "AuraMail/Newsletter"),
    "digest": ("NEWSLETTER", "ARCHIVE", "AuraMail/Newsletter"),
    "weekly update": ("NEWSLETTER", "ARCHIVE", "AuraMail/Newsletter"),
    "no-reply": ("NEWSLETTER", "ARCHIVE", "AuraMail/Newsletter"),
    "noreply": ("NEWSLETTER", "ARCHIVE", "AuraMail/Newsletter"),
    "manychat": ("NEWSLETTER", "ARCHIVE", "AuraMail/Newsletter"),
    "moneychat": ("NEWSLETTER", "ARCHIVE", "AuraMail/Newsletter"),
    
    # --- БЕЗПЕКА (Тільки точні фрази) ---
    "your verification code": ("SECURITY", "MOVE", "AuraMail/Security Alerts"),
    "google verification": ("SECURITY", "MOVE", "AuraMail/Security Alerts"),
    "password reset": ("SECURITY", "MOVE", "AuraMail/Security Alerts"),
    "apple id code": ("SECURITY", "MOVE", "AuraMail/Security Alerts"),
}


# --- 2. AI СХЕМА ---
CLASSIFICATION_SCHEMA = types.Schema(
    type=types.Type.OBJECT,
    description="JSON-об'єкт для класифікації та керування листом.",
    properties={
        "category": types.Schema(
            type=types.Type.STRING,
            description="Основна категорія листа (наприклад, PERSONAL, BILLS_INVOICES, MARKETING, SUBSCRIPTION, SPAM, SOCIAL, NEWSLETTER, SECURITY)."
        ),
        "label_name": types.Schema(
            type=types.Type.STRING,
            description="Ім'я мітки, яку потрібно призначити листу. Використовуй формат 'AuraMail/Category' (наприклад, AuraMail/Important, AuraMail/Bills)."
        ),
        "action": types.Schema(
            type=types.Type.STRING,
            enum=["MOVE", "ARCHIVE", "NO_ACTION"],
            description="Обов'язкова дія: MOVE (перемістити до мітки), ARCHIVE (видалити INBOX мітку), NO_ACTION (залишити у INBOX)."
        ),
        "urgency": types.Schema(
            type=types.Type.STRING,
            enum=["HIGH", "MEDIUM", "LOW"],
            description="Рівень терміновості: HIGH, MEDIUM, LOW."
        ),
        "description": types.Schema(
            type=types.Type.STRING,
            description="Короткий, однореченнєвий опис листа, чому він отримав таку класифікацію."
        ),
        "extracted_entities": types.Schema(
            type=types.Type.OBJECT,
            description="Ключові структуровані дані, витягнуті з листа.",
            properties={
                "due_date": types.Schema(type=types.Type.STRING, description="Кінцевий термін у форматі YYYY-MM-DD."),
                "amount": types.Schema(type=types.Type.STRING, description="Сума з валютою (наприклад, '1500 USD', '€50.99')."),
                "company_name": types.Schema(type=types.Type.STRING, description="Назва компанії або сервісу.")
            }
        )
    },
    required=["category", "action", "urgency", "description"]
)


CLASSIFICATION_SYSTEM_PROMPT = """
Ти — AuraMail Classifier. Твоє завдання — чітко розділяти листи на категорії.

КАТЕГОРІЇ:

1. **SOCIAL**: Сповіщення від соцмереж (Facebook, LinkedIn, Instagram). Дія: ARCHIVE.

2. **NEWSLETTER**: Інформаційні розсилки, дайджести, новини сервісів. Дія: ARCHIVE.

3. **MARKETING**: Реклама, продажі, знижки. Дія: ARCHIVE.

4. **BILLS_INVOICES**: Рахунки, оплати, чеки. Дія: MOVE (AuraMail/Bills).

5. **SECURITY**: ТІЛЬКИ коди доступу (2FA) та скидання пароля. Дія: MOVE (AuraMail/Security Alerts).

6. **IMPORTANT**: Особисті листи від людей або робочі запити. Дія: MOVE (AuraMail/Important).

7. **PERSONAL**: Особисті листи від друзів, родини. Дія: MOVE (AuraMail/Personal).

8. **ACTION_REQUIRED**: Листи, що вимагають дії. Дія: MOVE (AuraMail/Action Required).

ПРАВИЛО БЕЗПЕКИ:

Якщо лист виглядає як Security Alert, але містить кнопку "Unsubscribe" або "Відписатися" — це МАРКЕТИНГ або НОВИНИ (NEWSLETTER). Це НЕ Security.

МІТКИ (label_name):
- Використовуй ієрархічний формат 'AuraMail/Category' для кращої організації
- Приклади: AuraMail/Important, AuraMail/Action Required, AuraMail/Personal, AuraMail/Bills
- Для категорій SPAM/DANGER використовуй: AuraMail/Security Alerts
"""


# Retry стратегія для Gemini API
RETRY_ATTEMPTS = 2
@retry(
    stop=stop_after_attempt(RETRY_ATTEMPTS),
    wait=wait_exponential(multiplier=3, min=5, max=60),
    retry=retry_if_exception_message(match=r'(?i).*429.*|.*RESOURCE_EXHAUSTED.*|.*Resource has been exhausted.*'),
    before_sleep=lambda retry_state: print(f"⚠️ [Tenacity] Retrying Gemini API call (attempt {retry_state.attempt_number}/{RETRY_ATTEMPTS}) after rate limit error"),
    reraise=True
)
def _call_gemini_api(client: genai.Client, prompt: str, config):
    """Внутрішня функція для виклику Gemini API з retry механізмом."""
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[prompt],
            config=config
        )
        return response
    except Exception as e:
        error_str = str(e)
        if '429' in error_str or 'RESOURCE_EXHAUSTED' in error_str.upper():
            print(f"⚠️ Rate limit error (429) detected, tenacity will retry: {error_str[:150]}")
        raise


def get_gemini_client():
    """Initializes and returns Gemini client."""
    if not GEMINI_API_KEY:
        return None
    
    clean_key = GEMINI_API_KEY.strip().strip('"').strip("'").strip()
    
    if not clean_key.startswith("AIza"):
        return None
    
    try:
        return genai.Client(api_key=clean_key)
    except Exception:
        return None


def classify_email_with_gemini(client: genai.Client, email_content: str) -> dict:
    """
    Classifies email using Hybrid approach: Hard Rules → AI → Safety Valve.
    
    Args:
        client: Initialized Gemini client instance
        email_content: Email content (Subject and Snippet).
    
    Returns:
        Python dictionary with classification data.
    """
    
    # Нормалізація тексту
    try:
        content_str = str(email_content).lower()
        original_content = str(email_content)
    except Exception:
        return {
            "category": "REVIEW",
            "label_name": "AuraMail/AI_REVIEW",
            "action": "NO_ACTION",
            "urgency": "LOW",
            "description": "Помилка декодування вмісту",
            "extracted_entities": {},
            "error": "Decoding error"
        }
    
    # --- ЕТАП 1: ПЕРЕВІРКА ЗАЛІЗНИХ ПРАВИЛ (HARD RULES) ---
    for keyword, rule in HARD_RULES.items():
        if keyword in content_str:
            cat, act, lbl = rule
            
            # Виняток: Якщо правило каже SECURITY, але є ознаки розсилки — ігноруємо правило
            if cat == "SECURITY" and ("unsubscribe" in content_str or "відписатися" in content_str):
                continue
                
            print(f"🛡️ Hard Rule matched: '{keyword}' → {cat}/{act}")
            return {
                "category": cat,
                "label_name": lbl,
                "action": act,
                "urgency": "LOW",
                "description": f"Автоматично визначено за ключовим словом: '{keyword}'",
                "extracted_entities": {}
            }
    
    # --- ЕТАП 2: AI АНАЛІЗ (Якщо правила не спрацювали) ---
    if not client:
        return {
            "category": "REVIEW",
            "label_name": "AuraMail/AI_REVIEW",
            "action": "NO_ACTION",
            "urgency": "MEDIUM",
            "description": "GEMINI_API_KEY не встановлено",
            "extracted_entities": {},
            "error": "No API Key"
        }
    
    # Глобальний Redis Rate Limiter
    print(f"🔍 [Rate Limiter] Checking rate limit before API call...")
    max_wait_iterations = 120
    wait_iteration = 0
    while wait_iteration < max_wait_iterations:
        rate_limit_result = check_gemini_rate_limit()
        if rate_limit_result:
            print(f"✅ [Rate Limiter] Request allowed, proceeding with API call...")
            break
        else:
            wait_time = 2.0
            wait_iteration += 1
            print(f"⏳ [Rate Limiter] Global rate limit reached ({MAX_CALLS_PER_MINUTE}/min), waiting {wait_time}s (iteration {wait_iteration}/{max_wait_iterations})...")
            time.sleep(wait_time)
    
    if wait_iteration >= max_wait_iterations:
        return {
            "category": "REVIEW",
            "label_name": "AuraMail/AI_REVIEW",
            "action": "NO_ACTION",
            "urgency": "MEDIUM",
            "description": "Класифікація не вдалася через тривале очікування rate limit.",
            "extracted_entities": {},
            "error": f"Rate limit timeout after {max_wait_iterations * 2} seconds"
        }
    
    # Thread-safe rate limiting
    GEMINI_SEMAPHORE.acquire()
    try:
        global _last_request_timestamp
        with _last_request_time:
            current_time = time.time()
            time_since_last = current_time - _last_request_timestamp
            min_delay = 0.5
            if time_since_last < min_delay:
                time.sleep(min_delay - time_since_last)
            _last_request_timestamp = time.time()
        
        prompt = f"{CLASSIFICATION_SYSTEM_PROMPT}\n\n--- ТЕКСТ ЛИСТА ---\n{original_content[:3000]}"
        
        # Configure generation settings
        try:
            config = types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=CLASSIFICATION_SCHEMA,
                temperature=0.0  # Робимо AI максимально логічним
            )
        except (AttributeError, TypeError):
            # Fallback: if types.Schema is not supported
            json_schema_dict = {
                "type": "object",
                "properties": {
                    "category": {"type": "string"},
                    "label_name": {"type": "string"},
                    "action": {"type": "string", "enum": ["MOVE", "ARCHIVE", "NO_ACTION"]},
                    "urgency": {"type": "string", "enum": ["HIGH", "MEDIUM", "LOW"]},
                    "description": {"type": "string"},
                    "extracted_entities": {
                        "type": "object",
                        "properties": {
                            "due_date": {"type": "string"},
                            "amount": {"type": "string"},
                            "company_name": {"type": "string"}
                        }
                    }
                },
                "required": ["category", "action", "urgency", "description"]
            }
            config = types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=json_schema_dict,
                temperature=0.0
            )
        
        # Call Gemini API з retry механізмом
        try:
            response = _call_gemini_api(client, prompt, config)
        except Exception as e:
            error_str = str(e)
            error_type = type(e).__name__
            
            if '429' in error_str or 'RESOURCE_EXHAUSTED' in error_str.upper():
                print(f"❌ [Gemini API] Rate limit (429) after {RETRY_ATTEMPTS} retries")
            else:
                print(f"❌ [Gemini API] Failed after all retries [{error_type}]: {error_str[:200]}")
            
            return {
                "category": "REVIEW",
                "label_name": "AuraMail/AI_REVIEW",
                "action": "NO_ACTION",
                "urgency": "MEDIUM",
                "description": f"Класифікація не вдалася - {error_type}: {error_str[:100]}",
                "extracted_entities": {},
                "error": f"{error_type}: {error_str[:150]}"
            }
        
        # Парсинг відповіді
        try:
            text = response.text.strip()
            if text.startswith("```json"):
                text = text[7:-3].strip()
            elif text.startswith("```"):
                text = text[3:-3].strip()
            
            result = json.loads(text)
            
            # Ensure extracted_entities is always present
            if 'extracted_entities' not in result:
                result['extracted_entities'] = {}
            
            # --- ЕТАП 3: ЗАПОБІЖНИЙ КЛАПАН (SAFETY VALVE) ---
            # Виправляємо помилки AI, якщо вони сталися
            category = result.get('category', 'REVIEW')
            
            # 1. Захист від псевдо-безпеки
            is_security_alert = category in ['SECURITY', 'IMPORTANT']
            has_unsubscribe = "unsubscribe" in content_str or "відписатися" in content_str
            
            if is_security_alert and has_unsubscribe:
                print(f"🛡️ SAFETY: Змінено SECURITY -> NEWSLETTER (є 'unsubscribe')")
                result['category'] = 'NEWSLETTER'
                result['label_name'] = 'AuraMail/Newsletter'
                result['action'] = 'ARCHIVE'
                result['description'] = "Це розсилка (є кнопка відписки), а не повідомлення безпеки."
            
            # 2. Захист соцмереж (якщо AI пропустив)
            if "facebook" in content_str or "linkedin" in content_str or "instagram" in content_str:
                if category == "IMPORTANT":  # Соцмережі рідко бувають "IMPORTANT"
                    print(f"🛡️ SAFETY: Змінено IMPORTANT -> SOCIAL (виявлено соцмережу)")
                    result['category'] = 'SOCIAL'
                    result['label_name'] = 'AuraMail/Social'
                    result['action'] = 'ARCHIVE'
            
            # 3. Захист від маркетингу (якщо AI пропустив)
            if "discount" in content_str or "sale" in content_str or "знижка" in content_str or "акція" in content_str:
                if category not in ['MARKETING', 'PROMOTIONS']:
                    print(f"🛡️ SAFETY: Змінено {category} -> MARKETING (виявлено маркетинг)")
                    result['category'] = 'MARKETING'
                    result['label_name'] = 'AuraMail/Promotions'
                    result['action'] = 'ARCHIVE'
            
            return result
            
        except json.JSONDecodeError as e:
            return {
                "category": "REVIEW",
                "label_name": "AuraMail/AI_REVIEW",
                "action": "NO_ACTION",
                "urgency": "MEDIUM",
                "description": "Класифікація не вдалася через помилку парсингу JSON.",
                "extracted_entities": {},
                "error": f"JSON parse error: {str(e)}"
            }
        except Exception as e:
            return {
                "category": "REVIEW",
                "label_name": "AuraMail/AI_REVIEW",
                "action": "NO_ACTION",
                "urgency": "MEDIUM",
                "description": f"System Error: {str(e)}",
                "extracted_entities": {},
                "error": str(e)
            }
    finally:
        GEMINI_SEMAPHORE.release()


# --- Follow-up Detection (unchanged) ---
FOLLOWUP_SYSTEM_PROMPT = """
You are a concise assistant that decides if an outgoing email expects a reply and, if yes, by what date.

Return JSON with:
- expects_reply: boolean (true if the sender expects a response)
- expected_reply_date: string in YYYY-MM-DD if a date/deadline is mentioned; otherwise empty string
- confidence: string HIGH|MEDIUM|LOW explaining certainty

Rules:
- Be conservative: expects_reply=true only when the email clearly asks for confirmation, answer, or next steps.
- expected_reply_date: extract explicit dates/deadlines; if none, leave empty.
- Keep output minimal JSON only.
"""

FOLLOWUP_SCHEMA = types.Schema(
    type=types.Type.OBJECT,
    description="Follow-up expectation detection for outgoing email.",
    properties={
        "expects_reply": types.Schema(type=types.Type.BOOLEAN, description="True if the sender expects a reply."),
        "expected_reply_date": types.Schema(type=types.Type.STRING, description="Date by which a reply is expected (YYYY-MM-DD) or empty string."),
        "confidence": types.Schema(type=types.Type.STRING, enum=["HIGH", "MEDIUM", "LOW"], description="Confidence level for the decision.")
    },
    required=["expects_reply", "expected_reply_date", "confidence"]
)


def detect_expected_reply_with_gemini(client: genai.Client, email_content: str) -> dict:
    """Lightweight detector for outgoing emails to decide if a reply is expected and by when."""
    if not client:
        return {
            "expects_reply": False,
            "expected_reply_date": "",
            "confidence": "LOW",
            "error": "GEMINI_API_KEY not configured"
        }
    
    # Normalize content
    try:
        if isinstance(email_content, bytes):
            email_content = email_content.decode('utf-8', errors='replace')
        elif not isinstance(email_content, str):
            email_content = str(email_content)
        email_content = email_content.encode('utf-8', errors='replace').decode('utf-8')
    except Exception:
        email_content = str(email_content)
    
    prompt = f"{FOLLOWUP_SYSTEM_PROMPT}\n\n--- Outgoing Email ---\n{email_content}"
    
    # Rate limiting reuse
    print("🔍 [Follow-up] Checking rate limit before API call...")
    wait_iteration = 0
    max_wait_iterations = 60
    while wait_iteration < max_wait_iterations:
        if check_gemini_rate_limit():
            break
        wait_iteration += 1
        time.sleep(1.5)
    if wait_iteration >= max_wait_iterations:
        return {
            "expects_reply": False,
            "expected_reply_date": "",
            "confidence": "LOW",
            "error": "Rate limit timeout"
        }
    
    GEMINI_SEMAPHORE.acquire()
    try:
        try:
            config = types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=FOLLOWUP_SCHEMA,
                temperature=0.2
            )
        except Exception:
            config = {"response_mime_type": "application/json"}
        
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[prompt],
            config=config
        )
        raw = response.text if hasattr(response, "text") else str(response)
        try:
            parsed = json.loads(raw)
            return {
                "expects_reply": bool(parsed.get("expects_reply", False)),
                "expected_reply_date": parsed.get("expected_reply_date") or "",
                "confidence": parsed.get("confidence", "LOW")
            }
        except Exception:
            return {
                "expects_reply": False,
                "expected_reply_date": "",
                "confidence": "LOW",
                "error": "Failed to parse Gemini response"
            }
    except Exception as e:
        return {
            "expects_reply": False,
            "expected_reply_date": "",
            "confidence": "LOW",
            "error": str(e)
        }
    finally:
        GEMINI_SEMAPHORE.release()


# Voice Search: System prompt for Gmail query transformation
GMAIL_QUERY_TRANSFORM_PROMPT = """
Ти — експерт, який перетворює природну мову в синтаксис пошуку Gmail API.

Твоє завдання — проаналізувати запит користувача українською або англійською мовою та перетворити його на валідний Gmail query string.

ПРАВИЛА СИНТАКСИСУ GMAIL API:
- from:email - пошук листів від конкретного відправника
- to:email - пошук листів до конкретного отримувача
- subject:text - пошук по темі листа
- has:attachment - листи з вкладеннями
- is:unread - непрочитані листи
- is:read - прочитані листи
- before:YYYY/MM/DD - листи до дати
- after:YYYY/MM/DD - листи після дати
- label:LABEL_NAME - листи з міткою
- -label:LABEL_NAME - листи без мітки

КОМБІНАЦІЇ:
- Можна комбінувати кілька критеріїв через пробіл: from:alexander is:unread
- Для більш складних запитів використовуй логічні операції

ПРИКЛАДИ ПЕРЕТВОРЕННЯ:
- "листи від Івана" → "from:ivan@example.com" або "from:Іван"
- "непрочитані листи за вчора" → "is:unread after:2025/12/11"
- "листи з вкладеннями" → "has:attachment"
- "листи про інвойси" → "subject:invoice OR subject:інвойс"
- "листи від Петра за останній тиждень" → "from:petro after:2025/12/05"

ВАЖЛИВО:
- Повертай ТІЛЬКИ Gmail query string без додаткового тексту
- Якщо не можна точно визначити email адресу, використовуй ім'я (як у прикладі)
- Для дат використовуй формат YYYY/MM/DD
- Якщо запит незрозумілий, поверни порожній рядок ""
"""


def transform_to_gmail_query(natural_language_text: str) -> str:
    """Використовує Gemini для перетворення природної мови в Gmail Query."""
    if not natural_language_text or not natural_language_text.strip():
        return ""
    
    client = get_gemini_client()
    if not client:
        return ""
    
    prompt = f"{GMAIL_QUERY_TRANSFORM_PROMPT}\n\n--- Запит користувача ---\n{natural_language_text}\n\n--- Gmail Query (тільки query, без пояснень) ---"
    
    # Використовуємо існуючу логіку rate limiting
    print(f"🔍 [Voice Search] Checking rate limit before query transformation...")
    max_wait_iterations = 120
    wait_iteration = 0
    while wait_iteration < max_wait_iterations:
        rate_limit_result = check_gemini_rate_limit()
        if rate_limit_result:
            print(f"✅ [Voice Search] Request allowed, proceeding with query transformation...")
            break
        else:
            wait_time = 2.0
            wait_iteration += 1
            print(f"⏳ [Voice Search] Rate limit reached, waiting {wait_time}s (iteration {wait_iteration}/{max_wait_iterations})...")
            time.sleep(wait_time)
    
    if wait_iteration >= max_wait_iterations:
        print(f"❌ [Voice Search] Timeout waiting for rate limit, returning empty query")
        return ""
    
    # Використовуємо semaphore для обмеження одночасних запитів
    with GEMINI_SEMAPHORE:
        try:
            response = _call_gemini_api(client, prompt, None)
            
            if not response or not hasattr(response, 'text'):
                return ""
            
            query_text = response.text.strip()
            query_text = query_text.replace('```', '').strip()
            
            if not query_text or len(query_text) > 500:
                return ""
            
            print(f"✅ [Voice Search] Transformed query: '{natural_language_text}' → '{query_text}'")
            return query_text
            
        except Exception as e:
            error_str = str(e)
            print(f"❌ [Voice Search] Error transforming query: {error_str[:200]}")
            return ""
