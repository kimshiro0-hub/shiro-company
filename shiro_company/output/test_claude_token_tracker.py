import pytest
from datetime import datetime, date
import json
import os
from claude_token_tracker import TokenTracker

def test_token_tracker_init():
    tracker = TokenTracker()
    assert tracker.monthly_budget == 200
    assert os.path.exists(tracker.data_file)

def test_add_usage():
    tracker = TokenTracker()
    tracker.add_usage("시로컴퍼니", 1000, 2.5)
    data = tracker._load_data()
    today = date.today().isoformat()
    assert today in data
    assert data[today][0]['project'] == "시로컴퍼니"
    assert data[today][0]['tokens'] == 1000

def test_get_daily_stats():
    tracker = TokenTracker()
    tracker.add_usage("테스트", 500, 1.0)
    stats = tracker.get_daily_stats(date.today())
    assert stats['total_tokens'] >= 500
    assert stats['total_cost'] >= 1.0

def test_get_monthly_stats():
    tracker = TokenTracker()
    tracker.add_usage("월간테스트", 1000, 5.0)
    month = datetime.now().strftime("%Y-%m")
    stats = tracker.get_monthly_stats(month)
    assert 'total_tokens' in stats
    assert 'total_cost' in stats

def test_get_remaining_budget():
    tracker = TokenTracker()
    tracker.add_usage("예산테스트", 1000, 10.0)
    remaining = tracker.get_remaining_budget()
    assert remaining <= 200

def test_usage_rate_calculation():
    tracker = TokenTracker()
    tracker.add_usage("비율테스트", 1000, 50.0)
    stats = tracker.get_monthly_stats(datetime.now().strftime("%Y-%m"))
    assert stats['usage_rate'] >= 25.0

def test_project_breakdown():
    tracker = TokenTracker()
    tracker.add_usage("프로젝트A", 1000, 5.0)
    tracker.add_usage("프로젝트B", 500, 2.5)
    stats = tracker.get_monthly_stats(datetime.now().strftime("%Y-%m"))
    assert len(stats['by_project']) >= 2

def test_invalid_date_handling():
    tracker = TokenTracker()
    stats = tracker.get_daily_stats(date(2020, 1, 1))
    assert stats['total_tokens'] == 0
    assert stats['total_cost'] == 0.0