# 시로 컴퍼니

소라(Claude PM) + 테오(Gemini Dev)가 자율 협업하는 멀티 에이전트 시스템.

## 실행 방법

```bash
# 의존성 설치
pip install anthropic google-genai python-dotenv filelock pytest

# .env 파일 생성 (레포 루트)
ANTHROPIC_API_KEY=sk-ant-...
GEMINI_API_KEY=AI...

# 수동 실행
cd shiro_company
python run_task.py "TODO 앱 만들어줘"

# 소라 자율 판단
python run_task.py

# 완전 자동 (1회 실행 후 종료)
python run_task.py --auto
```

## GitHub Actions 설정

1. GitHub에 레포 생성 후 push
2. Settings > Secrets and variables > Actions에 등록:
   - `ANTHROPIC_API_KEY`
   - `GEMINI_API_KEY`
3. Settings > Pages > Source를 `gh-pages` 브랜치로 설정
4. Actions 탭에서 수동 트리거로 테스트

매일 08:00 KST에 자동 실행됨.

## 대시보드

GitHub Pages URL: `https://{username}.github.io/{repo}/`

로컬에서 보려면: `shiro_company/dashboard_gen.bat` 더블클릭

## 구조

```
shiro_company/
├── run_task.py         # 런처 (수동/자동/--auto)
├── sora_manager.py     # 소라 PM (Claude)
├── teo_dev.py          # 테오 Dev (Gemini)
├── board.py            # 메시지 보드
├── budget_tracker.py   # 예산 추적
├── dashboard_gen.py    # 대시보드 생성
├── context.md          # 보스 컨텍스트
├── output/             # 산출물
├── logs/               # 태스크 로그
└── dashboard/          # HTML 대시보드
```

## 문서

버전별 아키텍처 문서: `ARCHITECTURE_V2.x.md`
