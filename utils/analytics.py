"""
Analytics module for AuraMail Dashboard 2.0.
Calculates time and cost savings based on action_logs data.

CRITICAL BUSINESS VALUE: Shows real ROI from using AI for email management.
"""
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
from database import ActionLog, db


# Cost assumptions (can be configured)
AVERAGE_TIME_PER_EMAIL_SECONDS = 30  # Average time to manually process one email
HOURLY_RATE_USD = 25  # Average hourly rate for email management
GEMINI_COST_PER_1000_TOKENS = 0.00025  # Gemini 2.0 Flash pricing (approximate)
AVERAGE_TOKENS_PER_EMAIL = 500  # Average tokens used per email classification


def calculate_time_savings(days: int = 30) -> Dict:
    """
    Calculates time savings from automated email sorting.
    
    Args:
        days: Number of days to analyze (default: 30)
    
    Returns:
        Dictionary with time savings metrics
    """
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    # Get processed emails in date range
    processed_count = ActionLog.query.filter(
        ActionLog.created_at >= start_date
    ).count()
    
    # Calculate time savings
    total_seconds_saved = processed_count * AVERAGE_TIME_PER_EMAIL_SECONDS
    total_hours_saved = total_seconds_saved / 3600
    total_days_saved = total_hours_saved / 8  # Assuming 8-hour workday
    
    # Calculate cost savings
    cost_saved_usd = total_hours_saved * HOURLY_RATE_USD
    
    return {
        'period_days': days,
        'emails_processed': processed_count,
        'total_seconds_saved': total_seconds_saved,
        'total_hours_saved': round(total_hours_saved, 2),
        'total_days_saved': round(total_days_saved, 2),
        'cost_saved_usd': round(cost_saved_usd, 2),
        'average_per_day': {
            'emails': round(processed_count / days, 1) if days > 0 else 0,
            'hours': round(total_hours_saved / days, 2) if days > 0 else 0,
            'cost_usd': round(cost_saved_usd / days, 2) if days > 0 else 0
        }
    }


def calculate_ai_costs(days: int = 30) -> Dict:
    """
    Calculates AI costs (Gemini API) for email processing.
    
    Args:
        days: Number of days to analyze (default: 30)
    
    Returns:
        Dictionary with AI cost metrics
    """
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    # Get processed emails in date range
    processed_count = ActionLog.query.filter(
        ActionLog.created_at >= start_date
    ).count()
    
    # Calculate AI costs
    total_tokens = processed_count * AVERAGE_TOKENS_PER_EMAIL
    total_cost_usd = (total_tokens / 1000) * GEMINI_COST_PER_1000_TOKENS
    
    return {
        'period_days': days,
        'emails_processed': processed_count,
        'total_tokens_estimated': total_tokens,
        'total_cost_usd': round(total_cost_usd, 4),
        'cost_per_email_usd': round(total_cost_usd / processed_count, 6) if processed_count > 0 else 0,
        'average_per_day': {
            'cost_usd': round(total_cost_usd / days, 4) if days > 0 else 0
        }
    }


def calculate_roi(days: int = 30) -> Dict:
    """
    Calculates Return on Investment (ROI) from using AuraMail.
    
    Args:
        days: Number of days to analyze (default: 30)
    
    Returns:
        Dictionary with ROI metrics
    """
    time_savings = calculate_time_savings(days)
    ai_costs = calculate_ai_costs(days)
    
    cost_saved = time_savings['cost_saved_usd']
    ai_cost = ai_costs['total_cost_usd']
    net_savings = cost_saved - ai_cost
    
    roi_percentage = ((net_savings / ai_cost) * 100) if ai_cost > 0 else 0
    
    return {
        'period_days': days,
        'cost_saved_usd': cost_saved,
        'ai_cost_usd': ai_cost,
        'net_savings_usd': round(net_savings, 2),
        'roi_percentage': round(roi_percentage, 2),
        'break_even_days': round(ai_cost / (time_savings['average_per_day']['cost_usd']), 1) if time_savings['average_per_day']['cost_usd'] > 0 else 0,
        'time_savings': time_savings,
        'ai_costs': ai_costs
    }


def get_time_savings_chart_data(days: int = 30) -> Dict:
    """
    Gets time savings data formatted for Chart.js.
    
    Args:
        days: Number of days to analyze (default: 30)
    
    Returns:
        Dictionary with chart data
    """
    end_date = datetime.now()
    
    # Get daily breakdown
    daily_data = []
    labels = []
    hours_saved = []
    cost_saved = []
    
    for i in range(days - 1, -1, -1):
        date = end_date - timedelta(days=i)
        date_start = datetime.combine(date.date(), datetime.min.time())
        date_end = datetime.combine(date.date(), datetime.max.time())
        
        count = ActionLog.query.filter(
            ActionLog.created_at >= date_start,
            ActionLog.created_at <= date_end
        ).count()
        
        hours = (count * AVERAGE_TIME_PER_EMAIL_SECONDS) / 3600
        cost = hours * HOURLY_RATE_USD
        
        labels.append(date.strftime('%Y-%m-%d'))
        hours_saved.append(round(hours, 2))
        cost_saved.append(round(cost, 2))
    
    return {
        'labels': labels,
        'datasets': [
            {
                'label': 'Hours Saved',
                'data': hours_saved,
                'borderColor': '#4A90E2',
                'backgroundColor': 'rgba(74, 144, 226, 0.1)',
                'yAxisID': 'y'
            },
            {
                'label': 'Cost Saved (USD)',
                'data': cost_saved,
                'borderColor': '#00D4AA',
                'backgroundColor': 'rgba(0, 212, 170, 0.1)',
                'yAxisID': 'y1'
            }
        ]
    }


def get_category_distribution(days: int = 30) -> Dict:
    """
    Gets category distribution for pie chart.
    
    Args:
        days: Number of days to analyze (default: 30)
    
    Returns:
        Dictionary with category distribution data
    """
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    # Get category counts
    categories = db.session.query(
        ActionLog.ai_category,
        db.func.count(ActionLog.id).label('count')
    ).filter(
        ActionLog.created_at >= start_date
    ).group_by(ActionLog.ai_category).all()
    
    labels = []
    data = []
    colors_list = [
        '#4A90E2',  # Blue
        '#9D4EDD',  # Purple
        '#00D4AA',  # Teal
        '#FFA726',  # Orange
        '#FF4B4B',  # Red
        '#00C853',  # Green
        '#FFD700'   # Gold
    ]
    
    for i, (category, count) in enumerate(categories):
        labels.append(category or 'UNKNOWN')
        data.append(count)
    
    return {
        'labels': labels,
        'datasets': [{
            'data': data,
            'backgroundColor': colors_list[:len(labels)]
        }]
    }

