"""
Gemini AI processor module for AuraMail.
Handles all Gemini AI interaction logic (schema, prompt, classification).
"""
import sys
import json
import time
import threading
import re
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

# Налаштування логування для tenacity
logger = logging.getLogger(__name__)

# Redis-based Global Rate Limiter для Gemini API
# Використовуємо sliding window counter для обмеження кількості запитів на хвилину
redis_client = Redis.from_url(REDIS_URL)
MAX_CALLS_PER_MINUTE = 30  # Консервативний ліміт: 30 запитів/хвилину (нижче порогу 35/хв, де виникають 429, при ліміті 1,000 RPM для gemini-2.5-flash)
GEMINI_RATE_LIMIT_KEY = 'gemini:rate_limit:calls'  # Ключ для зберігання timestamp'ів у Redis

# Thread-safe rate limiting: максимум одночасних запитів до Gemini API
GEMINI_SEMAPHORE = threading.Semaphore(1)  # Критично: тільки 1 одночасний запит
_last_request_time = threading.Lock()
_last_request_timestamp = 0


def check_gemini_rate_limit():
    """
    Перевіряє, чи не перевищено глобальний rate limit для Gemini API.
    Використовує Redis sliding window counter з точністю до секунди.
    
    Returns:
        bool: True якщо запит дозволено, False якщо ліміт перевищено
    """
    try:
        now = int(time.time())
        unique_id = f"{now}:{threading.current_thread().ident}:{time.time()}"  # Унікальний ID для цього запиту
        
        # Видаляємо старі записи (більше 60 секунд назад)
        cutoff_time = now - 60
        redis_client.zremrangebyscore(GEMINI_RATE_LIMIT_KEY, 0, cutoff_time)
        
        # Перевіряємо поточну кількість викликів за останню хвилину
        current_calls = redis_client.zcard(GEMINI_RATE_LIMIT_KEY)
        
        if current_calls < MAX_CALLS_PER_MINUTE:
            # Додаємо поточний виклик з timestamp як score
            redis_client.zadd(GEMINI_RATE_LIMIT_KEY, {unique_id: now})
            # Встановлюємо TTL для автоматичного очищення (2 хвилини)
            redis_client.expire(GEMINI_RATE_LIMIT_KEY, 120)
            print(f"✅ Rate limit check: {current_calls + 1}/{MAX_CALLS_PER_MINUTE} calls allowed")
            return True  # Дозволено
        else:
            print(f"❌ Rate limit check: {current_calls}/{MAX_CALLS_PER_MINUTE} calls - LIMIT REACHED")
            return False  # Заборонено - ліміт перевищено
    except Exception as e:
        # Якщо Redis недоступний, дозволяємо запит (fallback)
        print(f"⚠️ Redis rate limiter error: {e}, allowing request (fallback)")
        return True

# Fix encoding for Windows console (handle Unicode characters)
if sys.platform == 'win32':
    try:
        # Set UTF-8 encoding for stdout/stderr on Windows
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8')
            sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass  # If reconfiguration fails, continue anyway


# --- JSON SCHEMA DECLARATION FOR GEMINI (WITH ENTITY EXTRACTION) ---
# This object represents the structure we require from Gemini
CLASSIFICATION_SCHEMA = types.Schema(
    type=types.Type.OBJECT,
    description="JSON-об'єкт для класифікації та керування листом.",
    properties={
        "category": types.Schema(
            type=types.Type.STRING,
            description="Основна категорія листа (наприклад, PERSONAL, BILLS_INVOICES, MARKETING, SUBSCRIPTION, SPAM)."
        ),
        "label_name": types.Schema(
            type=types.Type.STRING,
            description="Ім'я мітки, яку потрібно призначити листу. Починається з 'AI_' (наприклад, AI_BILLS, AI_PROJECT_X)."
        ),
        "action": types.Schema(
            type=types.Type.STRING,
            enum=["MOVE", "ARCHIVE", "NO_ACTION"],
            description="Обов'язкова дія, яку потрібно виконати з листом: MOVE (перемістити до мітки), ARCHIVE (видалити INBOX мітку - лист залишається доступним у All Mail), NO_ACTION (залишити у INBOX)."
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
        # --- Entity Extraction ---
        "extracted_entities": types.Schema(
            type=types.Type.OBJECT,
            description="Ключові структуровані дані, витягнуті з листа. Заповнюється лише якщо дані присутні.",
            properties={
                "due_date": types.Schema(
                    type=types.Type.STRING,
                    description="Кінцевий термін, дата оплати або дата події. Використовуйте формат YYYY-MM-DD."
                ),
                "amount": types.Schema(
                    type=types.Type.STRING,
                    description="Сума рахунку, платежу або ціни. Наприклад: '1500 USD', '€50.99', '12500 UAH'."
                ),
                "company_name": types.Schema(
                    type=types.Type.STRING,
                    description="Назва компанії або сервісу, що надіслала лист, якщо це не очевидно з адреси відправника."
                ),
                "location": types.Schema(
                    type=types.Type.STRING,
                    description="Адреса зустрічі, доставки або місця події."
                )
            }
        )
    },
    required=["category", "action", "urgency", "description"]
)


# --- Aggressive System Prompt ---
CLASSIFICATION_SYSTEM_PROMPT = """
Ти — високоточний Mail Organizer AI, що виконує агресивне фільтрування пошти.

Твоє завдання — проаналізувати вміст листа (тема та сніпет), визначити його категорію, терміновість, необхідну дію та витягнути ключові сутності.

СУВОРЕ ПРАВИЛО:

1. Якщо лист є рекламною розсилкою, маркетинговим матеріалом, нерелевантною підпискою або спамом, він повинен мати категорію 'DELETE' та дію 'DELETE'.

2. Якщо лист не вимагає відповіді або уваги (наприклад, сповіщення соцмереж, загальні новини), він повинен бути 'ARCHIVE'.

3. Лише особисті, робочі запити або фінансові рахунки можуть бути 'IMPORTANT' або 'ACTION_REQUIRED'.

КАТЕГОРІЇ ТА ДІЇ:

Категорії (category):
- ARCHIVE: Рекламні розсилки, маркетингові матеріали, спам, нерелевантні підписки, сповіщення соцмереж, загальні новини, автоматичні звіти, які не потребують уваги (листи залишаються доступними у All Mail)
- IMPORTANT: Особисті листи, робочі запити, важливі повідомлення
- ACTION_REQUIRED: Фінансові рахунки, термінові запити, дії, що потребують відповіді
- PERSONAL: Особисті листи від друзів, родини
- BILLS_INVOICES: Рахунки, інвойси, фінансові документи
- MARKETING: Маркетингові матеріали (мають бути ARCHIVE)
- SUBSCRIPTION: Підписки на новини, розсилки (мають бути ARCHIVE)
- SPAM: Спам (мають бути ARCHIVE)
- NEWSLETTER: Розсилки новин (мають бути ARCHIVE)
- SOCIAL: Сповіщення соцмереж (мають бути ARCHIVE)
- REVIEW: Листи, що потребують ручного перегляду

Дії (action):
- ARCHIVE: Прибрати з INBOX (лист залишається доступним у All Mail - використовується для спаму, маркетингу, нерелевантних розсилок, сповіщень соцмереж, автоматичних звітів, неважливих листів)
- MOVE: Перемістити до мітки (для важливих листів, що потребують уваги)
- NO_ACTION: Залишити у INBOX (тільки для листів, що точно потребують ручного перегляду)

Терміновість (urgency):
- HIGH: Термінові листи з крайніми термінами, запити від керівництва, повідомлення безпеки, фінансові рахунки з терміном
- MEDIUM: Важливі листи, але не вимагають негайної дії
- LOW: Розсилки, соціальні мережі, неважливі листи

Мітки (label_name):
- Завжди починай з префіксу 'AI_'
- Створюй описові назви міток, наприклад: AI_BILLS, AI_PROJECT_X, AI_PERSONAL, AI_IMPORTANT
- Для дії MOVE обов'язково вкажи label_name
- Для дії ARCHIVE label_name може бути порожнім або відсутнім

ВИТЯГ СУТНОСТЕЙ (extracted_entities):

Ти повинен проаналізувати вміст листа та, якщо це можливо, заповнити об'єкт 'extracted_entities'. Витягуй:

1. **due_date**: Кінцевий термін у форматі YYYY-MM-DD.
   Приклади: '2026-01-20', '2025-12-31'

2. **amount**: Сума з валютою (наприклад, '1500 USD', '€50.99', '12500 UAH').
   Завжди включай валюту, якщо вона вказана в листі.

3. **company_name**: Назва компанії або сервісу, що надіслала лист.
   Витягуй тільки якщо це не очевидно з адреси відправника.

4. **location**: Місце зустрічі, доставки або події.
   Включай повну адресу або назву місця, якщо вона є в листі.

**ВАЖЛИВО:** Якщо будь-яке поле в 'extracted_entities' відсутнє в листі, **залиш його порожнім** (`""`).
Не вигадуй дані, яких немає в оригінальному листі.

ПРАВИЛА:
- Повертай ТІЛЬКИ валідний JSON без додаткового тексту
- Обов'язково заповнюй поля category, action, urgency та description
- Поле label_name обов'язкове для дії MOVE
- Заповнюй extracted_entities, якщо в листі є відповідна інформація
- Будь АГРЕСИВНИМ у архівуванні спаму та маркетингу: використовуй ARCHIVE для реклами та нерелевантних розсилок
- Продукт не видаляє листи назавжди - всі листи залишаються доступними у All Mail, лише прибираються з INBOX
"""

# --- Lightweight Prompt for Follow-up Detection (outgoing emails) ---
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
        "expects_reply": types.Schema(
            type=types.Type.BOOLEAN,
            description="True if the sender expects a reply."
        ),
        "expected_reply_date": types.Schema(
            type=types.Type.STRING,
            description="Date by which a reply is expected (YYYY-MM-DD) or empty string."
        ),
        "confidence": types.Schema(
            type=types.Type.STRING,
            enum=["HIGH", "MEDIUM", "LOW"],
            description="Confidence level for the decision."
        )
    },
    required=["expects_reply", "expected_reply_date", "confidence"]
)


def get_gemini_client():
    """
    Initializes and returns Gemini client.
    
    Returns:
        genai.Client instance or None if GEMINI_API_KEY is not set or invalid
    """
    if not GEMINI_API_KEY:
        return None
    
    # Additional cleaning (in case config.py didn't clean it properly)
    clean_key = GEMINI_API_KEY.strip().strip('"').strip("'").strip()
    
    # Validate key format (Gemini API keys typically start with "AIza")
    if not clean_key.startswith("AIza"):
        return None
    
    try:
        return genai.Client(api_key=clean_key)
    except Exception:
        return None


# Retry стратегія для Gemini API (429 помилки)
# ЗМІНЕНО: Зменшено до 2 спроб, оскільки глобальний rate limiter має запобігати 429
# Якщо 429 все одно виникає, це означає вичерпання RPD квоти (Requests Per Day)
RETRY_ATTEMPTS = 2  # Зменшено до 2 спроб
@retry(
    stop=stop_after_attempt(RETRY_ATTEMPTS),  # Максимум 2 спроби
    wait=wait_exponential(multiplier=3, min=5, max=60),  # Exponential backoff: 5s, 15s, max 60s
    retry=retry_if_exception_message(match=r'(?i).*429.*|.*RESOURCE_EXHAUSTED.*|.*Resource has been exhausted.*'),
    before_sleep=lambda retry_state: print(f"⚠️ [Tenacity] Retrying Gemini API call (attempt {retry_state.attempt_number}/{RETRY_ATTEMPTS}) after rate limit error"),
    reraise=True  # Піднімаємо виняток після всіх спроб
)
def _call_gemini_api(client: genai.Client, prompt: str, config):
    """Внутрішня функція для виклику Gemini API з retry механізмом через tenacity."""
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[prompt],
            config=config
        )
        return response
    except Exception as e:
        # Логування помилки перед retry
        error_str = str(e)
        if '429' in error_str or 'RESOURCE_EXHAUSTED' in error_str.upper():
            print(f"⚠️ Rate limit error (429) detected, tenacity will retry: {error_str[:150]}")
        raise  # Піднімаємо виняток для tenacity


def classify_email_with_gemini(client: genai.Client, email_content: str) -> dict:
    """
    Classifies email using Gemini, requiring JSON output according to schema.
    
    Args:
        client: Initialized Gemini client instance
        email_content: Email content (Subject and Snippet).
    
    Returns:
        Python dictionary with classification data containing:
        - category: Email category
        - label_name: Gmail label name
        - action: Action (MOVE, ARCHIVE, NO_ACTION)
        - urgency: Urgency level (HIGH, MEDIUM, LOW)
        - description: Classification description from AI
        - extracted_entities: Dictionary with extracted entities:
            - due_date: Date in YYYY-MM-DD format (if present)
            - amount: Amount with currency (if present)
            - company_name: Company name (if present)
            - location: Address/place (if present)
    
    Example:
        >>> client = get_gemini_client()
        >>> result = classify_email_with_gemini(client, "Subject: Invoice...")
        >>> due_date = result.get('extracted_entities', {}).get('due_date')
        >>> amount = result.get('extracted_entities', {}).get('amount')
    """
    
    # Check for Gemini client availability
    if not client:
        return {
            "category": "REVIEW",
            "label_name": "AI_REVIEW",
            "action": "ARCHIVE",
            "urgency": "MEDIUM",
            "description": "GEMINI_API_KEY не встановлено",
            "extracted_entities": {},
            "error": "GEMINI_API_KEY не встановлено"
        }
    
    # Ensure email_content is properly encoded as UTF-8 string
    # Handle any encoding issues by normalizing the content
    try:
        if isinstance(email_content, bytes):
            # Якщо це bytes, декодуємо як UTF-8
            email_content = email_content.decode('utf-8', errors='replace')
        elif not isinstance(email_content, str):
            # Якщо це не рядок, перетворюємо на рядок
            email_content = str(email_content)
        
        # Нормалізуємо Unicode символи (вирішує проблеми з кодуванням)
        # Використовуємо 'replace' для безпечного оброблення проблемних символів
        email_content = email_content.encode('utf-8', errors='replace').decode('utf-8')
        
    except UnicodeEncodeError:
        try:
            email_content = str(email_content).encode('utf-8', errors='replace').decode('utf-8')
        except Exception:
            email_content = str(email_content).encode('ascii', errors='replace').decode('ascii')
    except Exception:
        email_content = str(email_content).encode('ascii', errors='replace').decode('ascii')
    
    # Create prompt with system instruction and email content
    try:
        prompt = f"{CLASSIFICATION_SYSTEM_PROMPT}\n\n--- Вміст Листа ---\n{email_content}"
        prompt = prompt.encode('utf-8', errors='replace').decode('utf-8')
    except Exception:
        prompt = f"Subject: {email_content[:100] if len(email_content) > 100 else email_content}"
    
    # Глобальний Redis Rate Limiter: чекаємо, поки не дозволено запит
    print(f"🔍 [Rate Limiter] Checking rate limit before API call...")
    max_wait_iterations = 120  # Максимум 4 хвилини очікування (120 × 2s)
    wait_iteration = 0
    while wait_iteration < max_wait_iterations:
        rate_limit_result = check_gemini_rate_limit()
        if rate_limit_result:
            print(f"✅ [Rate Limiter] Request allowed, proceeding with API call...")
            break  # Ліміт не перевищено, можна робити запит
        else:
            # Ліміт перевищено, чекаємо і перевіряємо знову
            wait_time = 2.0  # 2 секунди між перевірками
            wait_iteration += 1
            print(f"⏳ [Rate Limiter] Global rate limit reached ({MAX_CALLS_PER_MINUTE}/min), waiting {wait_time}s (iteration {wait_iteration}/{max_wait_iterations})...")
            time.sleep(wait_time)
    
    if wait_iteration >= max_wait_iterations:
        # Якщо довго чекали і не дістали дозволу, повертаємо помилку
        print(f"❌ [Rate Limiter] Timeout after {max_wait_iterations * 2} seconds, skipping API call")
        return {
            "category": "REVIEW",
            "label_name": "AI_REVIEW",
            "action": "ARCHIVE",
            "urgency": "MEDIUM",
            "description": "Класифікація не вдалася через тривале очікування rate limit.",
            "extracted_entities": {},
            "error": f"Rate limit timeout after {max_wait_iterations * 2} seconds"
        }
    
    # Thread-safe rate limiting: максимум 1 одночасний запит
    GEMINI_SEMAPHORE.acquire()
    try:
        # Невелика затримка між запитами для стабільності
        global _last_request_timestamp
        with _last_request_time:
            current_time = time.time()
            time_since_last = current_time - _last_request_timestamp
            min_delay = 0.5  # Мінімальна затримка 0.5 секунди між запитами
            if time_since_last < min_delay:
                time.sleep(min_delay - time_since_last)
            _last_request_timestamp = time.time()
        
        # CRITICAL OPTIMIZATION: Prompt Caching
        # Cache the system prompt to reduce token costs for repeated prompts
        from utils.prompt_cache import create_cached_content, get_cached_prompt_hash
        prompt_hash = get_cached_prompt_hash(CLASSIFICATION_SYSTEM_PROMPT)
        cached_content_id = create_cached_content(client, CLASSIFICATION_SYSTEM_PROMPT)
        
        # Configure generation settings using types.Schema
        try:
            config = types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=CLASSIFICATION_SCHEMA,
                temperature=0.3,
                # Note: cached_content parameter would be used here if Gemini API supports it
                # For now, we use in-memory caching via prompt_cache module
            )
        except (AttributeError, TypeError):
            # Fallback: if types.Schema is not supported, use regular dictionary
            json_schema_dict = {
                "type": "object",
                "description": "JSON-об'єкт для класифікації та керування листом.",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Основна категорія листа (наприклад, PERSONAL, BILLS_INVOICES, MARKETING, SUBSCRIPTION, SPAM)."
                    },
                    "label_name": {
                        "type": "string",
                        "description": "Ім'я мітки, яку потрібно призначити листу. Починається з 'AI_' (наприклад, AI_BILLS, AI_PROJECT_X)."
                    },
                    "action": {
                        "type": "string",
                        "enum": ["MOVE", "ARCHIVE", "NO_ACTION"],
                        "description": "Обов'язкова дія, яку потрібно виконати з листом: MOVE (перемістити до мітки), ARCHIVE (видалити INBOX мітку - лист залишається доступним у All Mail), NO_ACTION (залишити у INBOX)."
                    },
                    "urgency": {
                        "type": "string",
                        "enum": ["HIGH", "MEDIUM", "LOW"],
                        "description": "Рівень терміновості: HIGH, MEDIUM, LOW."
                    },
                    "description": {
                        "type": "string",
                        "description": "Короткий, однореченнєвий опис листа, чому він отримав таку класифікацію."
                    },
                    "extracted_entities": {
                        "type": "object",
                        "description": "Ключові структуровані дані, витягнуті з листа. Заповнюється лише якщо дані присутні.",
                        "properties": {
                            "due_date": {
                                "type": "string",
                                "description": "Кінцевий термін, дата оплати або дата події. Використовуйте формат YYYY-MM-DD."
                            },
                            "amount": {
                                "type": "string",
                                "description": "Сума рахунку, платежу або ціни. Наприклад: '1500 USD', '€50.99', '12500 UAH'."
                            },
                            "company_name": {
                                "type": "string",
                                "description": "Назва компанії або сервісу, що надіслала лист, якщо це не очевидно з адреси відправника."
                            },
                            "location": {
                                "type": "string",
                                "description": "Адреса зустрічі, доставки або місця події."
                            }
                        }
                    }
                },
                "required": ["category", "action", "urgency", "description"]
            }
            config = types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=json_schema_dict,
                temperature=0.3
            )
        
        # Call Gemini API з retry механізмом через tenacity
        try:
            response = _call_gemini_api(client, prompt, config)
        except Exception as e:
            # Якщо всі retry не вдалися, повертаємо помилку
            error_str = str(e)
            error_type = type(e).__name__
            
            # Перевіряємо, чи це 429 помилка (може означати вичерпання RPD квоти)
            if '429' in error_str or 'RESOURCE_EXHAUSTED' in error_str.upper():
                print(f"❌ [Gemini API] Rate limit (429) after {RETRY_ATTEMPTS} retries - возможно вичерпана денна квота (RPD)")
            else:
                print(f"❌ [Gemini API] Failed after all retries [{error_type}]: {error_str[:200]}")
            
            # Детальне логування причини відмови Gemini
            error_details = {
                "error_type": error_type,
                "error_message": error_str[:500],  # Зберігаємо більше контексту
                "email_subject": email_content[:100] if email_content else "Unknown",
                "email_length": len(email_content) if email_content else 0
            }
            
            # Логуємо детальну інформацію про помилку
            print(f"❌ [Gemini Classification] Помилка класифікації:")
            print(f"   Тип помилки: {error_type}")
            print(f"   Повідомлення: {error_str[:300]}")
            print(f"   Довжина листа: {len(email_content) if email_content else 0} символів")
            if '429' in error_str or 'RESOURCE_EXHAUSTED' in error_str.upper():
                print(f"   ⚠️ Причина: Rate limit досягнуто або денна квота вичерпана")
            elif 'INVALID_ARGUMENT' in error_str.upper() or '400' in error_str:
                print(f"   ⚠️ Причина: Невірний формат запиту або занадто довгий контент")
            elif 'PERMISSION_DENIED' in error_str.upper() or '403' in error_str:
                print(f"   ⚠️ Причина: Проблеми з API ключем або дозволами")
            else:
                print(f"   ⚠️ Причина: Невідома помилка API")
            
            return {
                "category": "REVIEW",
                "label_name": "AI_REVIEW",
                "action": "ARCHIVE",
                "urgency": "MEDIUM",
                "description": f"Класифікація не вдалася - {error_type}: {error_str[:100]}",
                "extracted_entities": {},
                "error": f"{error_type}: {error_str[:150]}",
                "error_details": error_details  # Додаємо деталі для логування
            }
        
        # Успішний запит, обробляємо response
        # ⚠️ КРИТИЧНЕ МІСЦЕ: Обробка відповіді від Gemini
        try:
            # Отримати текст відповіді
            response_text = response.text
            
            # Переконатися, що це рядок Python (str) з UTF-8
            if not isinstance(response_text, str):
                response_text = str(response_text)
            
            # Нормалізувати Unicode (вирішує проблеми з кодуванням)
            response_text = response_text.encode('utf-8', errors='replace').decode('utf-8')
            
            # Parse response (model guarantees JSON)
            json_result = json.loads(response_text)
            
            # Ensure extracted_entities is always present (even if empty)
            if 'extracted_entities' not in json_result:
                json_result['extracted_entities'] = {}
            
            return json_result
            
        except UnicodeEncodeError as unicode_err:
            # Try safe decoding
            try:
                if 'response_text' in locals():
                    safe_text = response_text.encode('utf-8', errors='replace').decode('utf-8')
                    json_result = json.loads(safe_text)
                    if 'extracted_entities' not in json_result:
                        json_result['extracted_entities'] = {}
                    return json_result
                else:
                    raise unicode_err
            except Exception:
                return {
                    "category": "REVIEW",
                    "label_name": "AI_REVIEW",
                    "action": "ARCHIVE",
                    "urgency": "MEDIUM",
                    "description": "Класифікація не вдалася через помилку кодування.",
                    "extracted_entities": {},
                    "error": f"UnicodeEncodeError: {str(unicode_err)}"
                }
        except json.JSONDecodeError as e:
            # Return safe default value on error
            return {
                "category": "REVIEW",
                "label_name": "AI_REVIEW",
                "action": "ARCHIVE",
                "urgency": "MEDIUM",
                "description": "Класифікація не вдалася, лист архівовано.",
                "extracted_entities": {},
                "error": f"JSON parse error: {str(e)}"
            }
    finally:
        GEMINI_SEMAPHORE.release()


def detect_expected_reply_with_gemini(client: genai.Client, email_content: str) -> dict:
    """
    Lightweight detector for outgoing emails to decide if a reply is expected and by when.
    
    Returns:
        dict with:
        - expects_reply (bool)
        - expected_reply_date (str, YYYY-MM-DD or "")
        - confidence (str)
        - error (optional)
    """
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
    """
    Використовує Gemini для перетворення природної мови в Gmail Query.
    
    Використовує існуючу логіку rate limiting та retry механізми.
    
    Args:
        natural_language_text: Текст запиту користувача (наприклад, "знайди листи від Івана за вчора")
    
    Returns:
        Gmail query string (наприклад, "from:ivan after:2025/12/11")
    """
    if not natural_language_text or not natural_language_text.strip():
        return ""
    
    client = get_gemini_client()
    if not client:
        return ""
    
    # Створюємо prompt
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
            # Використовуємо існуючу функцію _call_gemini_api з retry механізмом
            response = _call_gemini_api(client, prompt, None)
            
            if not response or not hasattr(response, 'text'):
                return ""
            
            # Отримуємо текст відповіді
            query_text = response.text.strip()
            
            # Очищаємо від можливих markdown код блоків або зайвого форматування
            query_text = query_text.replace('```', '').strip()
            
            # Перевіряємо, чи це не порожній рядок або помилка
            if not query_text or len(query_text) > 500:  # Gmail queries зазвичай короткі
                return ""
            
            print(f"✅ [Voice Search] Transformed query: '{natural_language_text}' → '{query_text}'")
            return query_text
            
        except Exception as e:
            error_str = str(e)
            print(f"❌ [Voice Search] Error transforming query: {error_str[:200]}")
            return ""
