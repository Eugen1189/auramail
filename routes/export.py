"""
Export routes for CSV and PDF exports.
"""
import csv
import io
from datetime import datetime
from flask import Blueprint, jsonify, make_response, send_file, session

from database import ActionLog
from routes.helpers import get_user_credentials
from utils.logging_config import get_logger

logger = get_logger(__name__)

export_bp = Blueprint('export', __name__)


@export_bp.route('/export/csv', methods=['GET'])
def export_csv():
    """
    Експорт історії дій у CSV форматі з бази даних ActionLog.
    ---
    tags:
      - Export
    security:
      - sessionAuth: []
    produces:
      - text/csv
    responses:
      200:
        description: CSV file with action history
        headers:
          Content-Disposition:
            type: string
            description: Attachment filename
          Content-Type:
            type: string
            description: text/csv; charset=utf-8
      401:
        description: Not authorized
        schema:
          type: object
          properties:
            status:
              type: string
              example: error
            message:
              type: string
              example: "Not authorized"
      500:
        description: Error exporting CSV
    """
    logger.info("EXPORT CSV ROUTE CALLED - This should only be called when user clicks export button")
    if 'credentials' not in session:
        return jsonify({'status': 'error', 'message': 'Not authorized'}), 401
    
    try:
        logs = ActionLog.query.order_by(ActionLog.timestamp.desc()).all()
        
        si = io.StringIO()
        cw = csv.writer(si)
        
        cw.writerow(['ID', 'Timestamp', 'Message ID', 'Subject', 'Category', 'Action', 'Reason', 'Follow-up Pending', 'Expected Reply Date'])
        
        for log in logs:
            cw.writerow([
                log.id,
                log.timestamp.strftime('%Y-%m-%d %H:%M:%S') if log.timestamp else '',
                log.msg_id,
                log.subject[:100] if log.subject else '',
                log.ai_category,
                log.action_taken,
                log.reason[:200] if log.reason else '',
                'Yes' if log.is_followup_pending else 'No',
                log.expected_reply_date.strftime('%Y-%m-%d') if log.expected_reply_date else ''
            ])
        
        output = make_response(si.getvalue())
        filename = f'auramail_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        output.headers["Content-Disposition"] = f"attachment; filename={filename}"
        output.headers["Content-type"] = "text/csv; charset=utf-8"
        return output
    except Exception as e:
        logger.error(f"CSV Export Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@export_bp.route('/export/pdf', methods=['GET'])
def export_pdf():
    """
    Експорт історії дій у PDF форматі з бази даних ActionLog.
    ---
    tags:
      - Export
    security:
      - sessionAuth: []
    produces:
      - application/pdf
    responses:
      200:
        description: PDF file with action history
        headers:
          Content-Disposition:
            type: string
            description: Attachment filename
          Content-Type:
            type: string
            description: application/pdf
      401:
        description: Not authorized
        schema:
          type: object
          properties:
            status:
              type: string
              example: error
            message:
              type: string
              example: "Not authorized"
      500:
        description: Error exporting PDF
    """
    if 'credentials' not in session:
        return jsonify({'status': 'error', 'message': 'Not authorized'}), 401
    
    try:
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.pdfgen import canvas
            from reportlab.lib import colors
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
            from reportlab.lib.styles import getSampleStyleSheet
        except ImportError:
            logger.error("reportlab is required for PDF export")
            return jsonify({'error': 'Library reportlab not installed. Install with: pip install reportlab'}), 500

        logs = ActionLog.query.order_by(ActionLog.timestamp.desc()).limit(100).all()
        
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        elements = []
        styles = getSampleStyleSheet()
        
        elements.append(Paragraph("AuraMail Activity Report", styles['Title']))
        elements.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles['Normal']))
        elements.append(Paragraph(f"Total Records: {len(logs)}", styles['Normal']))
        elements.append(Paragraph("<br/><br/>", styles['Normal']))
        
        data = [['Time', 'Action', 'Category', 'Subject']]
        for log in logs:
            subj = log.subject[:40] + '...' if len(log.subject) > 40 else log.subject
            time_str = log.timestamp.strftime('%Y-%m-%d %H:%M') if log.timestamp else 'N/A'
            data.append([time_str, log.action_taken, log.ai_category, subj])
        
        t = Table(data, colWidths=[100, 80, 100, 300])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
        ]))
        elements.append(t)
        
        doc.build(elements)
        buffer.seek(0)
        
        filename = f'auramail_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
        return send_file(
            buffer,
            as_attachment=True,
            download_name=filename,
            mimetype='application/pdf'
        )
    except Exception as e:
        logger.error(f"PDF Export Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

