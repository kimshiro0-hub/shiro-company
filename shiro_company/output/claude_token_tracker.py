import json
import os
from datetime import datetime, date

class TokenTracker:
    def __init__(self, data_file="claude_token_data.json", monthly_budget=200):
        self.data_file = data_file
        self.monthly_budget = monthly_budget
        # 임시 토큰당 비용 (USD/token), 실제 비용이 없을 때 사용. Claude Opus 기준 대략 100k 토큰당 $1 (평균치)
        self.default_cost_per_token = 0.00001 
        
        # 데이터 파일이 없으면 빈 JSON 객체로 생성
        if not os.path.exists(self.data_file):
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump({}, f)

        self._data = self._load_data()

    def _load_data(self):
        with open(self.data_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _save_data(self):
        with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(self._data, f, indent=4, ensure_ascii=False)

    def add_usage(self, project, tokens, cost=None):
        today_str = date.today().isoformat()
        
        if cost is None:
            # 비용이 제공되지 않으면 임시 토큰당 비용으로 계산
            calculated_cost = tokens * self.default_cost_per_token
        else:
            calculated_cost = cost

        usage_record = {
            "project": project,
            "tokens": tokens,
            "cost": calculated_cost,
            "timestamp": datetime.now().isoformat()
        }
        
        if today_str not in self._data:
            self._data[today_str] = []
        self._data[today_str].append(usage_record)
        self._save_data()
        print(f"[{project}] 토큰 {tokens:,}개, 비용 ${calculated_cost:.2f} 기록 완료.")

    def get_daily_stats(self, target_date: date):
        date_str = target_date.isoformat()
        daily_records = self._data.get(date_str, [])
        total_tokens = sum(record['tokens'] for record in daily_records)
        total_cost = sum(record['cost'] for record in daily_records)
        return {
            "date": date_str,
            "total_tokens": total_tokens,
            "total_cost": total_cost,
            "records": daily_records
        }

    def get_monthly_stats(self, target_month: str): # YYYY-MM 형식
        total_tokens = 0
        total_cost = 0
        monthly_records = []
        by_project = {} # 프로젝트별 통계 추가
        
        for date_str, daily_usages in self._data.items():
            if date_str.startswith(target_month):
                for record in daily_usages:
                    total_tokens += record['tokens']
                    total_cost += record['cost']
                    monthly_records.append(record)
                    
                    project_name = record['project']
                    if project_name not in by_project:
                        by_project[project_name] = {"tokens": 0, "cost": 0}
                    by_project[project_name]['tokens'] += record['tokens']
                    by_project[project_name]['cost'] += record['cost']
        
        usage_rate = (total_cost / self.monthly_budget) * 100 if self.monthly_budget > 0 else 0

        return {
            "month": target_month,
            "total_tokens": total_tokens,
            "total_cost": total_cost,
            "usage_rate": usage_rate,
            "by_project": by_project,
            "records": monthly_records
        }

    def get_remaining_budget(self):
        current_month = datetime.now().strftime("%Y-%m")
        monthly_stats = self.get_monthly_stats(current_month)
        return self.monthly_budget - monthly_stats['total_cost']

if __name__ == "__main__":
    tracker = TokenTracker()

    print("--- Claude 토큰 사용량 추적기 데모 ---")

    # 기존 데이터 삭제 (테스트용)
    if os.path.exists(tracker.data_file):
        os.remove(tracker.data_file)
        tracker = TokenTracker() # 다시 초기화

    # 1. 사용량 기록
    print("\n[사용량 기록]")
    tracker.add_usage("시로컴퍼니_프로젝트A", 50000, 0.5) # 5만 토큰, $0.5
    tracker.add_usage("개인_논문교정", 120000) # 12만 토큰, 비용 미지정 (기본값으로 계산됨)
    tracker.add_usage("시로컴퍼니_프로젝트B", 80000, 0.8) # 8만 토큰, $0.8
    tracker.add_usage("개인_블로그작성", 30000, 0.3) # 3만 토큰, $0.3

    # 2. 오늘 날짜로 일별 통계 조회
    print("\n[오늘 날짜 일별 통계]")
    today_stats = tracker.get_daily_stats(date.today())
    print(f"날짜: {today_stats['date']}")
    print(f"총 토큰: {today_stats['total_tokens']:,}개")
    print(f"총 비용: ${today_stats['total_cost']:.2f}")
    print("----- 상세 내역 -----")
    for record in today_stats['records']:
        print(f"  - [{record['project']}] 토큰: {record['tokens']:,}, 비용: ${record['cost']:.2f}")

    # 3. 현재 월별 통계 조회
    print("\n[현재 월별 통계]")
    current_month_str = datetime.now().strftime("%Y-%m")
    monthly_stats = tracker.get_monthly_stats(current_month_str)
    print(f"월: {monthly_stats['month']}")
    print(f"총 토큰: {monthly_stats['total_tokens']:,}개")
    print(f"총 비용: ${monthly_stats['total_cost']:.2f}")
    print(f"이번 달 예산 사용률: {monthly_stats['usage_rate']:.2f}%")
    print("----- 프로젝트별 통계 -----")
    for project, stats in monthly_stats['by_project'].items():
        print(f"  - [{project}] 토큰: {stats['tokens']:,}, 비용: ${stats['cost']:.2f}")

    # 4. 남은 예산 계산
    print("\n[남은 예산]")
    remaining_budget_value = tracker.get_remaining_budget() # 이제 float 값 반환
    print(f"남은 예산: ${remaining_budget_value:.2f}") # 직접 값 출력

    # 5. claude_token_data.json 파일 확인
    print(f"\n데이터는 '{tracker.data_file}' 파일에 저장되었습니다.")

    input("종료하려면 Enter를 누르세요...")