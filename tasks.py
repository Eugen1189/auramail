# tasks.py

import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from google.oauth2.credentials import Credentials

from utils.gmail_api import build_google_services, get_message_content, process_message_action, integrate_with_calendar
from utils.gemini_processor import classify_email_with_gemini, get_gemini_client
from utils.db_logger import log_action, init_progress, update_progress, complete_progress, save_report
from config import SCOPES, MAX_MESSAGES_TO_PROCESS, FOLDERS_TO_PROCESS

def create_app_for_worker():
    """
    Create Flask app instance for worker context.
    Lazy import to avoid circular dependency.
    """
    from server import app
    return app


def run_task_in_context(task_function, *args, **kwargs):
    """
    Wrapper function that creates Flask app context before executing task.
    Use this when enqueueing tasks that need Flask context (DB access, cache, etc.).
    """
    app = create_app_for_worker()
    with app.app_context():
        return task_function(*args, **kwargs)


# СЕРІАЛЬНА ОБРОБКА (1 потік) - для мінімального навантаження на Gemini API
# Зменшено до 1 потоку для зменшення навантаження до мінімуму
# Це допоможе уникнути 429 помилок навіть при вичерпанні квоти
MAX_WORKERS = 1  # Серіальна обробка: 1 потік = мінімальне навантаження


def process_single_email_task(msg, credentials_json, gemini_client, label_cache):
    """
    Функція для обробки ОДНОГО листа.
    ВАЖЛИВО: Ми створюємо service всередині функції, щоб уникнути конфліктів SSL.
    Потрібен Flask app context для доступу до бази даних.
    Створюємо контекст для кожного потоку окремо.
    """
    app = create_app_for_worker()
    with app.app_context():
        return _process_single_email_task_impl(msg, credentials_json, gemini_client, label_cache)


def _process_single_email_task_impl(msg, credentials_json, gemini_client, label_cache):
    """
    Implementation of single email processing.
    Must be called within Flask app context.
    """
    msg_id = msg.get('id', 'unknown')
    try:
        # 1. СТВОРЕННЯ SERVICE ДЛЯ ЦЬОГО ПОТОКУ (Thread-safe fix)
        creds = Credentials.from_authorized_user_info(json.loads(credentials_json), SCOPES)
        local_service, local_calendar_service = build_google_services(creds)
        
        # 2. Отримання контенту
        content_res = get_message_content(local_service, msg_id)
        content, subject = content_res if isinstance(content_res, tuple) else (content_res, "Unknown")
        
        # 3. Аналіз через AI
        classification = classify_email_with_gemini(gemini_client, content)
        
        if isinstance(classification, dict) and 'error' in classification:
            error_msg = classification['error']
            print(f"⚠️ AI Classification Error for {msg_id}: {error_msg}")
            return {'status': 'error', 'msg_id': msg_id, 'error': f"AI Classification Error: {error_msg}"}

        category = classification.get('category', 'REVIEW')
        action = classification.get('action', 'NO_ACTION')
        
        # 4. Виконання дії в Gmail
        action_status = process_message_action(local_service, msg_id, classification, label_cache)
        
        # Перевірка на помилки в action_status
        if action_status.startswith("ERROR"):
            error_msg = action_status
            print(f"⚠️ Gmail Action Error for {msg_id} ({category}): {error_msg}")
            # Все одно логуємо дію, але повертаємо помилку
            log_action(msg_id, classification, action_status, subject)
            return {'status': 'error', 'msg_id': msg_id, 'error': error_msg}
        
        # 5. Логування та Календар
        log_action(msg_id, classification, action_status, subject)
        integrate_with_calendar(local_calendar_service, classification, content)
        
        return {
            'status': 'success',
            'category': category,
            'action_status': action_status
        }

    except Exception as e:
        import traceback
        error_msg = str(e)
        error_traceback = traceback.format_exc()
        msg_id = msg.get('id', 'unknown')
        
        # Детальне логування помилки
        print(f"\n❌ ERROR processing email {msg_id}:")
        print(f"   Error: {error_msg}")
        print(f"   Traceback:\n{error_traceback}")
        
        return {
            'status': 'error', 
            'msg_id': msg_id, 
            'error': error_msg,
            'traceback': error_traceback
        }


def background_sort_task(credentials_json):
    """
    Основна функція (Worker), яка запускає паралельні потоки.
    This function is called by run_task_in_context wrapper, so Flask app context is already set.
    """
    return _background_sort_task_impl(credentials_json)


def _background_sort_task_impl(credentials_json):
    """
    Implementation of background sort task.
    Must be called within Flask app context.
    """
    try:
        print(f"\n{'='*60}")
        print(f"[Worker] TASK RECEIVED - Starting SERIAL sorting ({MAX_WORKERS} thread)")
        print(f"{'='*60}\n")
        start_time = time.time()
        
        # Для збору списку листів можна використати один сервіс (це один потік)
        creds_obj = Credentials.from_authorized_user_info(json.loads(credentials_json), SCOPES)
        main_service, _ = build_google_services(creds_obj)
        
        stats = {
            'total_processed': 0, 'important': 0, 'action_required': 0,
            'newsletter': 0, 'social': 0, 'review': 0, 'deleted': 0, 'errors': 0
        }
        
        # 1. Збір листів (послідовно)
        all_messages = []
        for folder_id in FOLDERS_TO_PROCESS:
            try:
                next_page_token = None
                while True:
                    results = main_service.users().messages().list(
                        userId='me', labelIds=[folder_id], pageToken=next_page_token, maxResults=50
                    ).execute()
                    msgs = results.get('messages', [])
                    all_messages.extend(msgs)
                    if not msgs or len(all_messages) >= MAX_MESSAGES_TO_PROCESS * 1.5:
                        break
                    next_page_token = results.get('nextPageToken')
                    if not next_page_token: break
            except Exception as e:
                print(f"⚠️ Помилка папки {folder_id}: {e}")

        unique_messages = list({msg['id']: msg for msg in all_messages}.values())
        if len(unique_messages) > MAX_MESSAGES_TO_PROCESS:
            unique_messages = unique_messages[:MAX_MESSAGES_TO_PROCESS]
        
        total_messages = len(unique_messages)
        init_progress(total=total_messages)
        
        # Кешування міток
        label_cache = {}
        try:
            response = main_service.users().labels().list(userId='me').execute()
            for label in response.get('labels', []):
                label_cache[label['name']] = label['id']
        except: pass

        # Gemini клієнт зазвичай thread-safe, його можна передавати
        gemini_client = get_gemini_client()

        # 🔥 ЗАПУСК ПАРАЛЕЛЬНОЇ ОБРОБКИ
        completed_count = 0
        
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            # ПЕРЕДАЄМО credentials_json, А НЕ service
            future_to_msg = {
                executor.submit(
                    process_single_email_task, 
                    msg, 
                    credentials_json,  # <--- Передаємо рядок JSON, щоб створити сервіс всередині
                    gemini_client, 
                    label_cache
                ): msg for msg in unique_messages
            }

            for future in as_completed(future_to_msg):
                completed_count += 1
                try:
                    result = future.result()
                except Exception as e:
                    import traceback
                    print(f"\n❌ CRITICAL: Exception in future.result() for email:")
                    print(f"   Error: {str(e)}")
                    print(f"   Traceback:\n{traceback.format_exc()}")
                    stats['errors'] += 1
                    update_progress(completed_count, stats, f"Помилка обробки {completed_count}/{total_messages}")
                    continue
                
                update_progress(completed_count, stats, f"Оброблено {completed_count}/{total_messages}")

                if result['status'] == 'success':
                    cat = result['category']
                    act = result['action_status']
                    
                    print(f"✅ [{completed_count}/{total_messages}] Success: {cat} -> {act}")
                    
                    if act == "DELETED":
                        stats['deleted'] += 1
                    elif "MOVED" in act or "ARCHIVED" in act:
                        mapping = {
                            "IMPORTANT": 'important', "ACTION_REQUIRED": 'action_required',
                            "NEWSLETTER": 'newsletter', "SOCIAL": 'social', "REVIEW": 'review'
                        }
                        key = mapping.get(cat, 'review')
                        stats[key] = stats.get(key, 0) + 1
                    else:
                        print(f"⚠️ [{completed_count}/{total_messages}] Unknown action: {act} for category: {cat}")
                        stats['errors'] += 1
                else:
                    # Детальне логування помилки
                    error_msg = result.get('error', 'Unknown error')
                    msg_id = result.get('msg_id', 'unknown')
                    print(f"\n❌ [{completed_count}/{total_messages}] Error for msg {msg_id}: {error_msg}")
                    if 'traceback' in result:
                        print(f"   Full traceback:\n{result['traceback']}")
                    stats['errors'] += 1

        complete_progress(stats)
        
        # Save report to database instead of JSON file
        save_report(stats)
            
        elapsed = time.time() - start_time
        print(f"✅ [Worker] Завершено за {elapsed:.2f} сек.")
        return stats

    except Exception as e:
        print(f"🔥 Worker Critical Error: {e}")
        return None


