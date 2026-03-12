class Calculator:
    def calculate(self, expression: str):
        parts = expression.split()
        if len(parts) != 3:
            raise ValueError("잘못된 수식 형식입니다. '숫자 연산자 숫자' 형식으로 입력해주세요.")

        try:
            num1 = float(parts[0])
            operator = parts[1]
            num2 = float(parts[2])
        except ValueError:
            raise ValueError("숫자 변환에 실패했습니다. 올바른 숫자를 입력해주세요.")

        if operator == '+':
            return num1 + num2
        elif operator == '-':
            return num1 - num2
        elif operator == '*':
            return num1 * num2
        elif operator == '/':
            if num2 == 0:
                raise ValueError("0으로 나눌 수 없습니다.")
            return num1 / num2
        else:
            raise ValueError(f"지원하지 않는 연산자입니다: {operator}")

if __name__ == "__main__":
    calc = Calculator()
    print("간단한 계산기 데모를 시작합니다.")

    try:
        print(f"'2 + 3' = {calc.calculate('2 + 3')}")
        print(f"'10 - 5' = {calc.calculate('10 - 5')}")
        print(f"'4 * 6' = {calc.calculate('4 * 6')}")
        print(f"'10.5 / 2.5' = {calc.calculate('10.5 / 2.5')}")
        print(f"'-5 + 3' = {calc.calculate('-5 + 3')}")
        print(f"'7 * 0' = {calc.calculate('7 * 0')}")

        # 에러 케이스 테스트
        print("\n에러 케이스 테스트:")
        try:
            calc.calculate("5 / 0")
        except ValueError as e:
            print(f"예상된 에러: {e}")

        try:
            calc.calculate("invalid expression")
        except ValueError as e:
            print(f"예상된 에러: {e}")

        try:
            calc.calculate("2 + ")
        except ValueError as e:
            print(f"예상된 에러: {e}")

    except Exception as e:
        print(f"예기치 않은 오류 발생: {e}")
    
    print("\n데모가 종료되었습니다.")
    input("종료하려면 Enter를 누르세요...")