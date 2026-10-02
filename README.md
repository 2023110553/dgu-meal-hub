# dgu-meal-hub 수집 가능성 PoC

동국대학교 서울캠퍼스의 상록원 3층, 남산학사, 경영관 D-Flex 식단을 무인 수집할 수 있는지 검증하는 Python 프로젝트입니다. 이 단계는 웹 UI가 아니라 원본 탐색, 날짜 선택, 다운로드 검증, 표준 JSON 생성에 집중합니다.

## 현재 검증 범위

- 상록원 EUC-KR HTML의 주간 범위, 날짜 열, 코너, 중식·석식, 메뉴, 가격 파싱
- 남산학사와 D-Flex 목록에서 제목의 날짜 범위로 게시물 자동 선택
- 상세 페이지에서 PNG와 PDF 주소 동적 추출
- PNG 시그니처·디코딩·크기, PDF 시그니처·로드·텍스트 추출 가능 여부 검증
- 월~금 일일 이미지 크롭 생성
- 식당별 오류 격리와 원본 SHA-256 기록
- 오프라인 픽스처 테스트와 GitHub Actions 수동 실환경 검증

## 설치와 실행

Python 3.12를 권장합니다.

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

첨부된 원본을 사용하는 재현 가능한 오프라인 실행:

```bash
python -m collector --date 2026-10-02
```

공식 사이트에 실제 접속하는 실행:

```bash
python -m collector --date 2026-10-02 --live
```

`--date`를 생략하면 `Asia/Seoul`의 오늘을 사용합니다. 결과는 기본적으로 `data/YYYY-MM-DD/menu.json`과 `crops/`, `original/` 아래에 저장됩니다. 수집 실패를 성공으로 오인하지 않도록 `PARTIAL_SUCCESS`, `NOT_PUBLISHED`, `ACCESS_BLOCKED`, `DOWNLOAD_ERROR`, `VALIDATION_ERROR`가 있으면 종료 코드는 2입니다. 정상적인 휴무·미등록 메뉴인 `NO_MENU`는 오류가 아닙니다.

## GitHub Actions 실행

1. GitHub 저장소의 **Actions** 탭을 엽니다.
2. 왼쪽에서 **Collector feasibility**를 선택합니다.
3. **Run workflow**를 누릅니다.
4. 필요하면 `YYYY-MM-DD` 날짜를 입력하고 실행합니다. 비우면 한국 시간 오늘입니다.
5. 완료 후 실행 상세의 **Artifacts**에서 `feasibility-날짜`를 내려받습니다.

워크플로는 테스트 후 실제 세 사이트를 요청합니다. 라이브 수집이 부분 성공 또는 실패이면 증거 아티팩트를 먼저 업로드한 뒤 작업을 실패 처리합니다.

## 데이터 해석 원칙

- 게시판의 맨 위 글이 아니라 `시작일 <= 요청일 <= 종료일`인 글만 선택합니다.
- HTTP 200만으로 성공 처리하지 않습니다. 상록원 필수 DOM, PNG/PDF 시그니처, 실제 디코딩을 확인합니다.
- 과거 식단을 오늘 데이터로 재사용하지 않습니다.
- 남산학사와 D-Flex의 이미지 메뉴는 검증되지 않은 OCR 텍스트를 `meals`에 넣지 않습니다. 원본과 일일 크롭을 제공합니다.
- 이미지 비율이 검증된 템플릿에서 4% 넘게 달라지면 크롭을 중단합니다.

상세한 실험 결과와 운영 판단은 [FEASIBILITY_REPORT.md](FEASIBILITY_REPORT.md)를 참고하세요.
