"""
Export module for AuraMail.
Provides CSV and PDF export functionality for sorting results and analytics.

CRITICAL BUSINESS VALUE: Transforms AuraMail from a technical utility into
a full business tool with exportable reports and analytics.
"""
import csv
import io
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from database import ActionLog, db
from utils.db_logger import get_action_history, get_daily_stats


def export_to_csv(start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> io.StringIO:
    """
    Exports sorting results to CSV format.
    
    Args:
        start_date: Optional start date filter
        end_date: Optional end date filter
    
    Returns:
        StringIO buffer with CSV content
    """
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow([
        'Message ID',
        'Subject',
        'Category',
        'Action Taken',
        'Urgency',
        'Date Processed',
        'Expected Reply Date',
        'Follow-up Pending',
        'Description'
    ])
    
    # Query action logs
    query = ActionLog.query
    
    if start_date:
        query = query.filter(ActionLog.created_at >= start_date)
    if end_date:
        query = query.filter(ActionLog.created_at <= end_date)
    
    logs = query.order_by(ActionLog.created_at.desc()).all()
    
    # Write data rows
    for log in logs:
        writer.writerow([
            log.msg_id,
            log.subject or '',
            log.ai_category or '',
            log.action_taken or '',
            log.urgency or '',
            log.created_at.strftime('%Y-%m-%d %H:%M:%S') if log.created_at else '',
            log.expected_reply_date.strftime('%Y-%m-%d') if log.expected_reply_date else '',
            'Yes' if log.is_followup_pending else 'No',
            log.reason or ''
        ])
    
    output.seek(0)
    return output


def export_to_pdf(start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> bytes:
    """
    Exports sorting results to PDF format.
    
    Args:
        start_date: Optional start date filter
        end_date: Optional end date filter
    
    Returns:
        Bytes with PDF content
    """
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter, A4
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        
        # Create PDF buffer
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=0.5*inch, bottomMargin=0.5*inch)
        
        # Container for PDF elements
        elements = []
        styles = getSampleStyleSheet()
        
        # Title style
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#4A90E2'),
            spaceAfter=30,
            alignment=1  # Center
        )
        
        # Add title
        title = Paragraph("AuraMail - Sorting Report", title_style)
        elements.append(title)
        elements.append(Spacer(1, 0.2*inch))
        
        # Add date range
        date_range_text = f"Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        if start_date or end_date:
            date_range_text += f"<br/>Period: {start_date.strftime('%Y-%m-%d') if start_date else 'Beginning'} to {end_date.strftime('%Y-%m-%d') if end_date else 'Today'}"
        
        date_para = Paragraph(date_range_text, styles['Normal'])
        elements.append(date_para)
        elements.append(Spacer(1, 0.3*inch))
        
        # Get statistics
        stats = calculate_stats()
        
        # Add summary statistics
        summary_data = [
            ['Metric', 'Value'],
            ['Total Processed', str(stats.get('total_processed', 0))],
            ['Important', str(stats.get('important', 0))],
            ['Action Required', str(stats.get('action_required', 0))],
            ['Newsletters', str(stats.get('newsletter', 0))],
            ['Social', str(stats.get('social', 0))],
            ['Archived', str(stats.get('archived', 0))],
            ['Errors', str(stats.get('errors', 0))]
        ]
        
        summary_table = Table(summary_data, colWidths=[3*inch, 2*inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4A90E2')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        elements.append(Paragraph("Summary Statistics", styles['Heading2']))
        elements.append(Spacer(1, 0.1*inch))
        elements.append(summary_table)
        elements.append(Spacer(1, 0.3*inch))
        
        # Query action logs
        query = ActionLog.query
        
        if start_date:
            query = query.filter(ActionLog.created_at >= start_date)
        if end_date:
            query = query.filter(ActionLog.created_at <= end_date)
        
        logs = query.order_by(ActionLog.created_at.desc()).limit(100).all()  # Limit to 100 for PDF
        
        if logs:
            elements.append(Paragraph("Recent Activity (Last 100)", styles['Heading2']))
            elements.append(Spacer(1, 0.1*inch))
            
            # Table data
            table_data = [['Date', 'Subject', 'Category', 'Action']]
            
            for log in logs:
                table_data.append([
                    log.created_at.strftime('%Y-%m-%d') if log.created_at else '',
                    (log.subject or '')[:50],  # Truncate long subjects
                    log.ai_category or '',
                    log.action_taken or ''
                ])
            
            # Create table
            table = Table(table_data, colWidths=[1*inch, 3*inch, 1.5*inch, 1.5*inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#9D4EDD')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('GRID', (0, 0), (-1, -1), 1, colors.grey),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.beige])
            ]))
            
            elements.append(table)
        
        # Build PDF
        doc.build(elements)
        buffer.seek(0)
        return buffer.getvalue()
        
    except ImportError:
        # Fallback if reportlab is not installed
        raise ImportError("reportlab is required for PDF export. Install with: pip install reportlab")


def get_export_data(start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> Dict:
    """
    Gets data for export in structured format.
    
    Args:
        start_date: Optional start date filter
        end_date: Optional end date filter
    
    Returns:
        Dictionary with export data
    """
    query = ActionLog.query
    
    if start_date:
        query = query.filter(ActionLog.created_at >= start_date)
    if end_date:
        query = query.filter(ActionLog.created_at <= end_date)
    
    logs = query.order_by(ActionLog.created_at.desc()).all()
    
    # Calculate stats from logs
    stats = {
        'total_processed': len(logs),
        'important': sum(1 for log in logs if log.ai_category == 'IMPORTANT'),
        'review': sum(1 for log in logs if log.ai_category == 'REVIEW'),
        'archived': sum(1 for log in logs if log.action_taken in ('ARCHIVE', 'DELETE')),
        'action_required': sum(1 for log in logs if log.ai_category == 'ACTION_REQUIRED'),
        'newsletter': sum(1 for log in logs if log.ai_category == 'NEWSLETTER'),
        'social': sum(1 for log in logs if log.ai_category == 'SOCIAL'),
        'errors': sum(1 for log in logs if log.action_taken and 'ERROR' in log.action_taken)
    }
    
    return {
        'logs': [log.to_dict() for log in logs],
        'stats': stats,
        'total_count': len(logs),
        'date_range': {
            'start': start_date.isoformat() if start_date else None,
            'end': end_date.isoformat() if end_date else None
        }
    }

