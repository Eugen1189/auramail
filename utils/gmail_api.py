"""
Gmail API module for AuraMail.
Handles all Gmail interaction logic (reading, labels, moving, deleting).
"""
import json
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from config import SCOPES, LABEL_COLOR_MAP


def build_google_services(creds):
    """
    Creates Gmail and Calendar service objects.
    
    FIX: Disables discovery cache to prevent "file_cache is only supported with oauth2client<4.0.0" warnings.
    This eliminates unnecessary file I/O and speeds up service creation.
    
    Args:
        creds: Credentials object with OAuth tokens
    
    Returns:
        Tuple (gmail_service, calendar_service)
    """
    # CRITICAL FIX: Disable discovery cache to prevent file_cache warnings
    # This eliminates the "file_cache is only supported with oauth2client<4.0.0" error
    # and speeds up service creation by avoiding unnecessary file I/O
    cache_discovery = False  # Disable file-based discovery cache
    
    # 1. Create Gmail service with cache_discovery=False
    gmail_service = build('gmail', 'v1', credentials=creds, cache_discovery=cache_discovery)
    
    # 2. Create Calendar service with cache_discovery=False
    calendar_service = build('calendar', 'v3', credentials=creds, cache_discovery=cache_discovery)
    
    return gmail_service, calendar_service





def get_message_content(service, msg_id):
    """
    Gets full email content and returns it as plain text.
    Returns tuple (content_text, subject) for convenient logging.
    """
    try:
        # 'format':'full' gets all email parts, including body
        message = service.users().messages().get(userId='me', id=msg_id, format='full').execute()
        
        # Simplify getting email body (most often base64-encoded)
        payload = message.get('payload')
        headers = payload.get('headers', [])
        parts = payload.get('parts', [])
        
        snippet = message.get('snippet', 'No snippet available.')
        subject = next((header['value'] for header in headers if header['name'] == 'Subject'), 'No Subject')
        sender = next((header['value'] for header in headers if header['name'] == 'From'), 'Unknown Sender')
        date = next((header['value'] for header in headers if header['name'] == 'Date'), 'Unknown Date')
        
        # Ensure all strings are properly encoded as UTF-8
        # Handle any encoding issues by normalizing the content
        try:
            snippet = str(snippet).encode('utf-8', errors='replace').decode('utf-8')
            subject = str(subject).encode('utf-8', errors='replace').decode('utf-8')
            sender = str(sender).encode('utf-8', errors='replace').decode('utf-8')
            date = str(date).encode('utf-8', errors='replace').decode('utf-8')
        except Exception:
            # If encoding fails, use safe fallback
            snippet = str(snippet).encode('ascii', errors='replace').decode('ascii')
            subject = str(subject).encode('ascii', errors='replace').decode('ascii')
            sender = str(sender).encode('ascii', errors='replace').decode('ascii')
            date = str(date).encode('ascii', errors='replace').decode('ascii')
        
        # Отримуємо повний текст листа для кращої точності класифікації
        full_body = ""
        try:
            # Рекурсивно обходимо всі частини листа
            def extract_body(part):
                body = ""
                if part.get('body', {}).get('data'):
                    import base64
                    body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', errors='replace')
                elif part.get('body', {}).get('attachmentId'):
                    # Пропускаємо вкладення для швидкості
                    pass
                
                # Рекурсивно обробляємо вкладені частини
                for subpart in part.get('parts', []):
                    body += extract_body(subpart)
                
                return body
            
            full_body = extract_body(payload)
            # Якщо повний текст отримано, використовуємо його, инакше snippet
            if full_body and len(full_body) > len(snippet):
                content_text = f"Subject: {subject}\nFrom: {sender}\nDate: {date}\n\n{full_body}"
            else:
                content_text = f"Subject: {subject}\nFrom: {sender}\nDate: {date}\nSnippet: {snippet}"
        except Exception as body_error:
            # Якщо не вдалося отримати повний текст, використовуємо snippet
            print(f"⚠️ Не вдалося отримати повний текст листа {msg_id}: {body_error}, використовуємо snippet")
            content_text = f"Subject: {subject}\nFrom: {sender}\nDate: {date}\nSnippet: {snippet}"
        
        return content_text, subject
        
    except Exception as e:
        return f"Error reading message {msg_id}: {e}", "Error"


def get_or_create_label_id(service, label_name, label_cache, category=None):
    """
    Checks if label exists and returns its ID. If not — creates it.
    Supports hierarchical labels (e.g., "AuraMail/Category") by creating parent labels first.
    Uses cache for quick access without repeated API requests.
    
    Args:
        service: Initialized Gmail API service object
        label_name: Label name (supports hierarchy like "AuraMail/Category")
        label_cache: Dictionary for storing label IDs {"Label Name": "Label ID"}
        category: Optional category name for color mapping (e.g., 'IMPORTANT', 'BILLS_INVOICES')
    
    Returns:
        Label ID (string)
    """
    # Check cache
    if label_name in label_cache:
        return label_cache[label_name]
    
    # 1. Attempt to find label via API
    response = service.users().labels().list(userId='me').execute()
    labels = response.get('labels', [])
    # Update cache with all found labels for future requests
    for label in labels:
        if label['name'] not in label_cache:
            label_cache[label['name']] = label['id']
        if label['name'] == label_name:
            return label_cache[label_name]
    
    # 2. If label has hierarchy (contains '/'), ensure parent label exists first
    if '/' in label_name:
        parent_label = label_name.split('/')[0]
        # Recursively create parent label if it doesn't exist
        if parent_label not in label_cache:
            get_or_create_label_id(service, parent_label, label_cache, category="DEFAULT")
    
    # 3. If label not found, create it
    label_body = {
        'name': label_name,
        'labelListVisibility': 'labelShow',
        'messageListVisibility': 'show'
    }
    
    # Add color for AI labels and AuraMail labels based on category
    # Try to set color, but if it fails, create label without color
    color_added = False
    
    # Support both "AI_" prefix and "AuraMail/" hierarchy
    is_ai_label = label_name.startswith('AI_') or label_name.startswith('AuraMail/')
    
    if is_ai_label:
        # Determine category: use provided category or extract from label name
        detected_category = None
        
        if category:
            # Use provided category if available
            detected_category = category.upper() if category else None
        else:
            # Try to match label name to category
            # Format: AI_CATEGORY_NAME, AuraMail/Category, etc.
            label_upper = label_name.upper()
            for cat in LABEL_COLOR_MAP.keys():
                if cat != 'DEFAULT' and cat in label_upper:
                    detected_category = cat
                    break
        
        # Use category color or default
        # Gmail API uses color names (strings), not HEX codes
        bg_color = LABEL_COLOR_MAP.get(detected_category, LABEL_COLOR_MAP['DEFAULT'])
        
        # Set text color - Gmail API requires both textColor and backgroundColor
        # Try using standard color names first
        text_color = 'white'
        
        # Both textColor and backgroundColor are required when setting color
        # Gmail API expects color names as strings (e.g., "blue", "red", "white")
        if bg_color:
            label_body['color'] = {
                'textColor': text_color,
                'backgroundColor': bg_color
            }
            color_added = True
    
    # Try to create label with color, if that fails, create without color
    try:
        created_label = service.users().labels().create(userId='me', body=label_body).execute()
    except Exception as color_error:
        # If color setting fails, try creating label without color
        if color_added and 'color' in str(color_error).lower():
            print(f"⚠️ Warning: Failed to create label '{label_name}' with color. Trying without color...")
            # Remove color and try again
            label_body.pop('color', None)
            try:
                created_label = service.users().labels().create(userId='me', body=label_body).execute()
                print(f"✅ Label '{label_name}' created successfully without color")
            except Exception as e:
                # If it still fails, raise the original error
                raise color_error
        else:
            # Re-raise if it's not a color-related error
            raise
    
    # Save to cache
    label_cache[label_name] = created_label['id']
    return created_label['id']


def process_message_action(service, msg_id, classification_data, label_cache):
    """
    Executes smart action on email based on classification.
    
    NEW LOGIC (Smart Inbox Management):
    - Important emails (ACTION_REQUIRED, URGENT, PERSONAL, IMPORTANT) stay in INBOX with labels
    - Social/Promotions/Newsletters are archived (removed from INBOX)
    - Spam/Danger emails are moved to AuraMail/Security Alerts folder
    
    Args:
        service: Initialized Gmail API service object
        msg_id: Message ID
        classification_data: Dictionary with classification data (category, label_name, action, urgency, description)
        label_cache: Dictionary for storing label IDs {"Label Name": "Label ID"}
    
    Returns:
        String with action execution status
    """
    action = classification_data.get('action')
    category = classification_data.get('category', '').upper()
    label_name = classification_data.get('label_name')  # May be None for ARCHIVE
    
    try:
        # Legacy DELETE action support: convert to ARCHIVE to preserve data
        if action == "DELETE":
            action = "ARCHIVE"
        
        # Додаємо мітку "AuraMail_Sorted" для захисту від дублювання
        processed_label_name = "AuraMail_Sorted"
        processed_label_id = get_or_create_label_id(service, processed_label_name, label_cache, category="DEFAULT")
        
        # Define categories that should stay in INBOX (only add label, don't archive)
        INBOX_CATEGORIES = ['ACTION_REQUIRED', 'URGENT', 'PERSONAL', 'IMPORTANT', 'BILLS_INVOICES']
        
        # Define categories that should be archived (removed from INBOX)
        ARCHIVE_CATEGORIES = ['SOCIAL', 'PROMOTIONS', 'NEWSLETTER', 'MARKETING', 'SUBSCRIPTION']
        
        # Define categories that should be moved to Security Alerts
        SECURITY_CATEGORIES = ['SPAM', 'DANGER']
        
        # Define categories that need manual review (stay in INBOX with AI_REVIEW label)
        REVIEW_CATEGORIES = ['REVIEW']
        
        # Determine actual action based on category (override action if needed)
        if category in SECURITY_CATEGORIES:
            # Move Spam/Danger to Security Alerts folder
            security_label_name = "AuraMail/Security Alerts"
            security_label_id = get_or_create_label_id(service, security_label_name, label_cache, category="DANGER")
            
            modification = {
                'addLabelIds': [security_label_id, processed_label_id],
                'removeLabelIds': ['INBOX']
            }
            service.users().messages().modify(userId='me', id=msg_id, body=modification).execute()
            return f"MOVED to {security_label_name}"
        
        elif category in REVIEW_CATEGORIES:
            # Review emails: Stay in INBOX with AI_REVIEW label (Zero Trust - manual review required)
            review_label_name = "AuraMail/AI_REVIEW"
            review_label_id = get_or_create_label_id(service, review_label_name, label_cache, category="REVIEW")
            
            modification = {
                'addLabelIds': [review_label_id, processed_label_id],
                # DO NOT remove INBOX - keep review emails visible for manual check
            }
            service.users().messages().modify(userId='me', id=msg_id, body=modification).execute()
            return f"LABELED {review_label_name} (kept in INBOX for review)"
        
        elif category in INBOX_CATEGORIES:
            # Important emails: Stay in INBOX, only add label
            if not label_name:
                # Generate label name if not provided
                label_name = f"AuraMail/{category}"
            
            # Ensure parent label exists first (for hierarchy)
            parent_label_name = "AuraMail"
            parent_label_id = get_or_create_label_id(service, parent_label_name, label_cache, category="DEFAULT")
            
            # Create category label with hierarchy
            category_label_id = get_or_create_label_id(service, label_name, label_cache, category=category)
            
            modification = {
                'addLabelIds': [category_label_id, processed_label_id],
                # DO NOT remove INBOX - keep important emails visible
            }
            service.users().messages().modify(userId='me', id=msg_id, body=modification).execute()
            return f"LABELED {label_name} (kept in INBOX)"
        
        elif category in ARCHIVE_CATEGORIES or action == "ARCHIVE":
            # Archive categories: Remove from INBOX (but keep in All Mail)
            if label_name:
                # Add label before archiving (for organization)
                category_label_id = get_or_create_label_id(service, label_name, label_cache, category=category)
                modification = {
                    'addLabelIds': [category_label_id, processed_label_id],
                    'removeLabelIds': ['INBOX']
                }
            else:
                # Just archive without label
                modification = {
                    'addLabelIds': [processed_label_id],
                    'removeLabelIds': ['INBOX']
                }
            service.users().messages().modify(userId='me', id=msg_id, body=modification).execute()
            return "ARCHIVED"
        
        elif action == "MOVE":
            # Legacy MOVE action: Add label and remove from INBOX
            if not label_name:
                raise ValueError("label_name обов'язковий для дії MOVE")
            
            category_label_id = get_or_create_label_id(service, label_name, label_cache, category=category)
            
            modification = {
                'addLabelIds': [category_label_id, processed_label_id],
                'removeLabelIds': ['INBOX']
            }
            service.users().messages().modify(userId='me', id=msg_id, body=modification).execute()
            return f"MOVED to {label_name}"
            
        elif action == "NO_ACTION":
            # Only add processed label, keep in INBOX
            modification = {
                'addLabelIds': [processed_label_id]
            }
            service.users().messages().modify(userId='me', id=msg_id, body=modification).execute()
            return "NO_ACTION taken (kept in INBOX)"
            
        else:
            # Unknown action: default to keeping in INBOX with label
            if label_name:
                category_label_id = get_or_create_label_id(service, label_name, label_cache, category=category)
                modification = {
                    'addLabelIds': [category_label_id, processed_label_id]
                }
            else:
                modification = {
                    'addLabelIds': [processed_label_id]
                }
            service.users().messages().modify(userId='me', id=msg_id, body=modification).execute()
            return f"LABELED (kept in INBOX) - Unknown action: {action}"
            
    except Exception as e:
        return f"ERROR: {str(e)}"


def integrate_with_calendar(calendar_service, classification_data: dict, email_content: str):
    """
    Creates event in Google Calendar based on extracted entities.
    
    Args:
        calendar_service: Google Calendar API service object
        classification_data: Dictionary with classification data from Gemini (includes extracted_entities)
        email_content: Email content for use in event description
    
    Returns:
        String with integration status
    """
    import os
    from config import TIMEZONE
    
    try:
        entities = classification_data.get('extracted_entities', {})
        if not entities:
            return "No integration required"
        
        due_date = entities.get('due_date', '').strip()
        location = entities.get('location', '').strip()
        amount = entities.get('amount', '').strip()
        company_name = entities.get('company_name', '').strip()
        
        category = classification_data.get('category', '')
        description = classification_data.get('description', '')
        
        # Determine timezone (can be moved to environment variable)
        time_zone = TIMEZONE
        
        # 1. Create reminder for bill payment or action with deadline
        if due_date and category == "ACTION_REQUIRED":
            # Create event that lasts all day on deadline day
            summary = f"Сплатити: {company_name if company_name else 'Рахунок'}"
            if amount:
                summary += f" ({amount})"
            
            # Form event description
            event_description = f"Створено FileZen Mail Organizer.\n"
            event_description += f"Термін оплати: {due_date}\n"
            if amount:
                event_description += f"Сума: {amount}\n"
            if description:
                event_description += f"Опис: {description}\n"
            event_description += f"\nОригінальний вміст листа: {email_content[:200]}..."
            
            event_body = {
                'summary': summary,
                'description': event_description,
                'location': location if location else None,
                'start': {
                    'date': due_date,  # All-day event
                    'timeZone': time_zone,
                },
                'end': {
                    'date': due_date,  # All-day event
                    'timeZone': time_zone,
                },
                'reminders': {
                    'useDefault': False,
                    # Remind 24 hours before payment day start
                    'overrides': [{'method': 'popup', 'minutes': 24 * 60}],
                },
            }
            
            # Call Google Calendar API to create event
            if calendar_service:
                calendar_service.events().insert(calendarId='primary', body=event_body).execute()
                return f"Calendar Event created for {due_date}"
        
        # 2. Create event with location (for meetings)
        if due_date and location and category in ["IMPORTANT", "ACTION_REQUIRED"]:
            summary = f"Зустріч: {company_name if company_name else 'Важлива подія'}"
            
            event_description = f"Створено FileZen Mail Organizer.\n"
            event_description += f"Місце: {location}\n"
            if description:
                event_description += f"Опис: {description}\n"
            event_description += f"\nОригінальний вміст листа: {email_content[:200]}..."
            
            event_body = {
                'summary': summary,
                'description': event_description,
                'location': location,
                'start': {
                    'date': due_date,
                    'timeZone': time_zone,
                },
                'end': {
                    'date': due_date,
                    'timeZone': time_zone,
                },
                'reminders': {
                    'useDefault': False,
                    'overrides': [{'method': 'popup', 'minutes': 24 * 60}],
                },
            }
            
            # Call Google Calendar API to create event
            if calendar_service:
                calendar_service.events().insert(calendarId='primary', body=event_body).execute()
                return f"Calendar Event created: {summary}"
        
        # 3. Create reminder for important events without specific date
        if category == "IMPORTANT" and not due_date:
            return "Important email flagged"
        
        return "No integration required"
        
    except Exception as e:
        return f"Calendar Error: {str(e)}"


def rollback_action(gmail_service, log_entry: dict, label_cache: dict) -> str:
    """
    Executes reverse action on email based on log entry.
    
    Args:
        gmail_service: Initialized Gmail API service object
        log_entry: Dictionary with log entry containing message_id, action_taken, label_name
        label_cache: Dictionary for storing label IDs {"Label Name": "Label ID"}
    
    Returns:
        String with rollback execution status
    """
    msg_id = log_entry.get('message_id') or log_entry.get('msg_id')
    original_action = log_entry.get('action_taken')
    original_label = log_entry.get('label_name', '')
    
    if not msg_id:
        return "ERROR: Message ID not found in log entry."
    
    # Legacy DELETE action support: treat as ARCHIVE for rollback
    if original_action in ('DELETE', 'DELETED'):
        original_action = 'ARCHIVE'
    
    modification = {}
    status_msg = ""
    
    if original_action == 'ARCHIVE':
        # Reverse action: Add INBOX label
        modification = {'addLabelIds': ['INBOX']}
        status_msg = "Successfully restored from Archive (INBOX added)."
    
    elif original_action == 'MOVE':
        # Reverse action: Remove new label, add INBOX
        if not original_label:
            return "ERROR: Rollback failed, original label not found in log."
        
        label_id = get_or_create_label_id(gmail_service, original_label, label_cache)
        
        modification = {
            'addLabelIds': ['INBOX'],
            'removeLabelIds': [label_id]
        }
        status_msg = f"Successfully restored from {original_label} (INBOX added)."
    
    elif original_action == 'NO_ACTION':
        # No action was taken, nothing to rollback
        return "INFO: No action was taken, nothing to rollback."
    
    else:
        return f"ERROR: Unknown action '{original_action}' cannot be rolled back."
    
    try:
        gmail_service.users().messages().modify(userId='me', id=msg_id, body=modification).execute()
        return status_msg
    except Exception as e:
        return f"Gmail API Error during rollback: {e}"


def find_emails_by_query(service, query: str, max_results: int = 50) -> list:
    """
    Знаходить листи за Gmail query string.
    
    Args:
        service: Initialized Gmail API service object
        query: Gmail query string (наприклад, "from:ivan is:unread")
        max_results: Максимальна кількість результатів (за замовчуванням 50)
    
    Returns:
        List of message dictionaries with 'id' and 'threadId' keys
    """
    if not query or not query.strip():
        return []
    
    try:
        # Виклик Gmail API для пошуку
        results = service.users().messages().list(
            userId='me',
            q=query,
            maxResults=max_results
        ).execute()
        
        messages = results.get('messages', [])
        print(f"✅ [Voice Search] Found {len(messages)} emails for query: '{query}'")
        return messages
        
    except Exception as e:
        error_str = str(e)
        print(f"❌ [Voice Search] Error searching emails: {error_str[:200]}")
        return []

