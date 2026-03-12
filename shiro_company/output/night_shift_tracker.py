import csv
from datetime import datetime, timedelta

class NightShiftTracker:
    def __init__(self, csv_filename="night_shift_records.csv"):
        self.csv_filename = csv_filename
        self.shifts = [] # Stores list of dicts: {'date': date_obj, 'check_in_dt': datetime_obj, 'check_out_dt': datetime_obj, 'hours': float}
        self.current_shift_start = None # datetime object when check-in happened
        self._load_from_csv() # Load existing records on tracker initialization

    def _load_from_csv(self):
        """CSV 파일에서 기존 근무 기록을 불러옵니다."""
        try:
            with open(self.csv_filename, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Parse string data back into datetime objects for internal use
                    record_date = datetime.strptime(row['date'], '%Y-%m-%d').date()
                    check_in_dt_str = f"{row['date']} {row['check_in']}"
                    check_out_dt_str = f"{row['date']} {row['check_out']}" if row['check_out'] else None

                    check_in_dt = datetime.strptime(check_in_dt_str, '%Y-%m-%d %H:%M:%S')
                    check_out_dt = datetime.strptime(check_out_dt_str, '%Y-%m-%d %H:%M:%S') if check_out_dt_str else None
                    
                    # Ensure check_out_dt is correct for overnight shifts from CSV
                    if check_in_dt and check_out_dt and check_out_dt < check_in_dt:
                        check_out_dt += timedelta(days=1)

                    self.shifts.append({
                        'date': record_date,
                        'check_in_dt': check_in_dt,
                        'check_out_dt': check_out_dt,
                        'hours': float(row['hours']) if row['hours'] else 0.0
                    })
        except FileNotFoundError:
            pass # No file yet, start fresh
        except Exception as e:
            print(f"기존 기록 불러오기 실패: {e}. 새로운 기록을 시작합니다.")
            self.shifts = [] # Reset on error

    def record_check_in(self):
        """현재 시간을 출근 시간으로 기록합니다."""
        if self.current_shift_start:
            print("이미 출근 기록이 있습니다. 퇴근을 먼저 기록해주세요.")
            return False
        self.current_shift_start = datetime.now()
        print(f"출근 기록: {self.current_shift_start.strftime('%Y-%m-%d %H:%M:%S')}")
        return True

    def record_check_out(self):
        """현재 시간을 퇴근 시간으로 기록하고 일일 근무 시간을 계산합니다."""
        if not self.current_shift_start:
            print("출근 기록이 없습니다. 출근을 먼저 기록해주세요.")
            return False

        check_out_dt = datetime.now()
        # Calculate duration based on internal datetime objects
        daily_hours = self._calculate_duration_from_datetimes(self.current_shift_start, check_out_dt)
        
        self.shifts.append({
            'date': self.current_shift_start.date(),
            'check_in_dt': self.current_shift_start,
            'check_out_dt': check_out_dt,
            'hours': daily_hours
        })
        print(f"퇴근 기록: {check_out_dt.strftime('%Y-%m-%d %H:%M:%S')}, 근무 시간: {daily_hours:.1f} 시간")
        self.current_shift_start = None # Reset for next shift
        self.save_to_csv() # Save immediately after completing a shift
        return True

    def _calculate_duration_from_datetimes(self, start_dt, end_dt):
        """두 datetime 객체 간의 근무 시간을 계산합니다 (야간 근무 포함)."""
        # If end_dt is earlier than start_dt, assume it's the next day
        if end_dt < start_dt:
            end_dt += timedelta(days=1)
        
        duration = end_dt - start_dt
        return duration.total_seconds() / 3600.0

    def calculate_daily_hours(self, check_in_str, check_out_str):
        """
        'HH:MM' 형식의 문자열 출퇴근 시간으로 일일 근무 시간을 계산합니다.
        잘못된 시간 형식일 경우 ValueError를 발생시킵니다.
        """
        today = datetime.now().date()
        
        # ValueError가 발생하도록 try-except 블록을 제거합니다.
        check_in_time = datetime.strptime(check_in_str, '%H:%M').time()
        check_out_time = datetime.strptime(check_out_str, '%H:%M').time()

        check_in_dt = datetime.combine(today, check_in_time)
        check_out_dt = datetime.combine(today, check_out_time)

        return self._calculate_duration_from_datetimes(check_in_dt, check_out_dt)

    def get_weekly_summary(self):
        """현재 주의 총 근무 시간 통계를 반환합니다."""
        today = datetime.now().date()
        # Calculate the start of the current week (Monday)
        start_of_week = today - timedelta(days=today.weekday()) # Monday = 0
        end_of_week = start_of_week + timedelta(days=6) # Sunday = 6
        
        total_hours = 0.0
        weekly_shifts = []

        for shift in self.shifts:
            if start_of_week <= shift['date'] <= end_of_week:
                total_hours += shift['hours']
                weekly_shifts.append(shift)
        
        return {
            'start_of_week': start_of_week.strftime('%Y-%m-%d'),
            'end_of_week': end_of_week.strftime('%Y-%m-%d'),
            'total_hours': total_hours,
            'shifts': weekly_shifts
        }

    def get_monthly_summary(self):
        """현재 월의 총 근무 시간 통계를 반환합니다."""
        today = datetime.now().date()
        
        total_hours = 0.0
        monthly_shifts = []

        for shift in self.shifts:
            if shift['date'].year == today.year and shift['date'].month == today.month:
                total_hours += shift['hours']
                monthly_shifts.append(shift)
        
        return {
            'year': today.year,
            'month': today.month,
            'total_hours': total_hours,
            'shifts': monthly_shifts
        }

    def save_to_csv(self):
        """현재까지 기록된 모든 근무 기록을 CSV 파일로 저장합니다. 성공 시 True를 반환합니다."""
        fieldnames = ['date', 'check_in', 'check_out', 'hours']
        
        try:
            with open(self.csv_filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for shift in self.shifts:
                    # Convert datetime objects back to string format for CSV
                    row_data = {
                        'date': shift['date'].strftime('%Y-%m-%d'),
                        'check_in': shift['check_in_dt'].strftime('%H:%M:%S'),
                        'check_out': shift['check_out_dt'].strftime('%H:%M:%S') if shift['check_out_dt'] else '',
                        'hours': f"{shift['hours']:.1f}"
                    }
                    writer.writerow(row_data)
            return True # 성공 시 True 반환
        except Exception as e:
            print(f"CSV 저장 중 오류 발생: {e}")
            return False # 오류 발생 시 False 반환

if __name__ == "__main__":
    tracker = NightShiftTracker("night_shift_records.csv")
    print("--- 편의점 야간근무 시간 추적기 데모 ---")
    
    # 기존 기록이 있다면 출력
    if tracker.shifts:
        print(f"기존 기록 {len(tracker.shifts)}개를 불러왔습니다.")
        for shift in tracker.shifts:
            print(f" - 날짜: {shift['date'].strftime('%Y-%m-%d')}, 출근: {shift['check_in_dt'].strftime('%H:%M:%S')}, 퇴근: {shift['check_out_dt'].strftime('%H:%M:%S')}, 근무: {shift['hours']:.1f}h")
    else:
        print("새로운 기록을 시작합니다.")

    while True:
        print("\n메뉴:")
        print("1. 출근 기록")
        print("2. 퇴근 기록")
        print("3. 일일 근무 시간 계산 (시뮬레이션)")
        print("4. 주간 근무 통계")
        print("5. 월간 근무 통계")
        print("6. 종료") 
        
        choice = input("선택: ")

        if choice == '1':
            tracker.record_check_in()
        elif choice == '2':
            tracker.record_check_out()
        elif choice == '3':
            in_time = input("출근 시간 (HH:MM): ")
            out_time = input("퇴근 시간 (HH:MM): ")
            try:
                calculated_hours = tracker.calculate_daily_hours(in_time, out_time)
                print(f"시뮬레이션된 근무 시간: {calculated_hours:.1f} 시간")
            except ValueError:
                print("오류: 시간 형식이 잘못되었습니다. HH:MM 형식으로 입력해주세요.")
        elif choice == '4':
            weekly_summary = tracker.get_weekly_summary()
            print(f"\n--- 주간 근무 통계 ({weekly_summary['start_of_week']} ~ {weekly_summary['end_of_week']}) ---")
            print(f"총 근무 시간: {weekly_summary['total_hours']:.1f} 시간")
            if weekly_summary['shifts']:
                for shift in weekly_summary['shifts']:
                    print(f"  - {shift['date'].strftime('%Y-%m-%d')}: {shift['check_in_dt'].strftime('%H:%M')} ~ {shift['check_out_dt'].strftime('%H:%M')} ({shift['hours']:.1f}h)")
            else:
                print("  이번 주 근무 기록이 없습니다.")
        elif choice == '5':
            monthly_summary = tracker.get_monthly_summary()
            print(f"\n--- 월간 근무 통계 ({monthly_summary['year']}년 {monthly_summary['month']}월) ---")
            print(f"총 근무 시간: {monthly_summary['total_hours']:.1f} 시간")
            if monthly_summary['shifts']:
                for shift in monthly_summary['shifts']:
                    print(f"  - {shift['date'].strftime('%Y-%m-%d')}: {shift['check_in_dt'].strftime('%H:%M')} ~ {shift['check_out_dt'].strftime('%H:%M')} ({shift['hours']:.1f}h)")
            else:
                print("  이번 달 근무 기록이 없습니다.")
        elif choice == '6':
            print("프로그램을 종료합니다. 기록이 자동으로 저장됩니다.")
            break
        else:
            print("잘못된 선택입니다. 다시 시도해주세요.")
    
    input("종료하려면 Enter를 누르세요...")