#!/usr/bin/env python3
"""
Check database contents to verify logs are being saved to DB instead of JSON.
"""
from server import app
from database import db, ActionLog, Progress, Report

with app.app_context():
    print('📊 Статистика бази даних:\n')
    
    # Check ActionLog
    log_count = ActionLog.query.count()
    print(f'✅ ActionLog записів: {log_count}')
    if log_count > 0:
        latest = ActionLog.query.order_by(ActionLog.timestamp.desc()).first()
        print(f'   Останній запис: {latest.timestamp} - {latest.subject[:50]}...')
        print(f'   Категорія: {latest.ai_category}, Дія: {latest.action_taken}')
    
    # Check Progress
    progress = Progress.query.first()
    if progress:
        print(f'\n✅ Progress: {progress.current}/{progress.total} - {progress.status}')
        if progress.details:
            print(f'   Деталі: {progress.details[:50]}...')
    else:
        print('\n⚠️  Progress: немає записів')
    
    # Check Reports
    report_count = Report.query.count()
    print(f'\n✅ Reports: {report_count}')
    if report_count > 0:
        latest_report = Report.query.order_by(Report.created_at.desc()).first()
        print(f'   Останній звіт: {latest_report.created_at}')
        print(f'   Оброблено листів: {latest_report.total_processed}')
        print(f'   Важливих: {latest_report.important}, Видалено: {latest_report.deleted}')








