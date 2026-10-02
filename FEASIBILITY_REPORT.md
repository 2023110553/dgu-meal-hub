# 동국대학교 통합 식단 수집 2차 기술 검증 보고서

검증일: 2026-10-02 (Asia/Seoul)

## 결론

남산학사와 경영관 D-Flex 수집은 1차 구현을 유지한 상태로 정상입니다. 1차 GitHub Actions에서 상록원만 `menu_date 요소가 없습니다`로 실패한 것은 정상 식단 HTML 대신 다른 HTML을 받았다는 뜻입니다. 동일 공식 주소를 외부 데이터센터 환경에서 조회하면 `자동등록방지를 위해 보안절차를 거치고 있습니다` / `Please prove that you are human` 페이지가 재현되므로 **GitHub-hosted runner에 대한 CAPTCHA 또는 접근 제한일 가능성이 높습니다.** 다만 1차 실행은 응답 본문을 보존하지 않았으므로 그 실행만으로 CAPTCHA를 확정할 수는 없습니다. 이번 진단 코드를 올려 Actions를 한 번 더 실행하면 상태 코드·최종 URL·Content-Type·크기와 실패 HTML로 확정할 수 있습니다.

공식 대체 경로로 같은 생협 사이트의 오늘 식단(`store.php?w=4&l=1`)과 모바일 일일 식단(`mobile/menu.html?code=5`)을 확인했습니다. 로컬에서는 두 경로 모두 정상이며 모바일 식단은 데스크톱 식단과 일치합니다. 그러나 외부 데이터센터에서는 모바일 경로도 보안 페이지가 나타나므로 경로 변경만으로 GitHub runner 제한을 피할 수 있다고 보장할 수 없습니다. 우회나 CAPTCHA 무력화는 구현하지 않았습니다.

D-Flex PDF의 1,203자 벡터 텍스트는 날짜 열과 식사 행의 좌표를 이용해 월~금 5일 모두 구조화할 수 있었습니다. 2026-10-02의 3개 코너 메뉴를 원본 표 이미지와 항목 단위로 대조했고 AI API는 사용하지 않았습니다.

## 2차 구현 내용

- 상록원 요청마다 요청 경로, HTTP 상태 코드, 최종 URL, Content-Type, 바이트 크기, SHA-256, 리다이렉트 체인을 `menu.json`과 Actions 로그에 기록
- 실패 응답 본문을 `debug/sangnokwon-*-response.html`로 저장해 Actions 아티팩트에 포함
- 쿠키, Authorization, 요청/응답 헤더 전체 등 인증정보는 기록하지 않음
- `CAPTCHA`, `ACCESS_RESTRICTED`, `UNEXPECTED_REDIRECT`, `SERVER_ERROR`, `HTTP_ERROR`, `UNEXPECTED_CONTENT_TYPE`, `HTML_STRUCTURE_CHANGED`, `NETWORK_ERROR`를 구분
- 주간 데스크톱 경로가 실패하면 공식 모바일 일일 식단 경로를 한 번 사용
- D-Flex PDF를 벡터 텍스트 좌표로 날짜별 3개 식단에 구조화하고 `ai_api_used: false`를 기록
- 남산학사와 D-Flex의 게시물 탐색·이미지·PDF 다운로드 및 크롭 로직은 변경하지 않음

## 검증 근거

```text
python -m pytest -q
32 passed in 1.33s
```

로컬 실환경 2026-10-02 실행 결과:

- 상록원 주간 HTML: HTTP 200, 최종 URL 동일, `text/html`, 137,028바이트, 정상 `menu_date` 존재
- 남산학사: 기존 방식으로 이미지·PDF·일일 크롭 성공
- D-Flex: 기존 방식으로 이미지·PDF·일일 크롭 성공, PDF에서 3개 식단 구조화 성공

D-Flex 2026-10-02 구조화 결과:

| 구분 | 가격 | 대표 메뉴 |
|---|---:|---|
| 일반식 A코너 | 6,500원 | (뚝)우삼겹순두부찌개&쫄면사리 |
| 특별식 B코너 | 7,500원 | 돼지고기마제덮밥&계란후라이 |
| 석식 | 6,500원 | 미트소스스파게티&해물굴소스볶음밥 |

각 행의 나머지 반찬까지 원본 PDF/PNG와 일치하도록 테스트에 고정했습니다. 9월 28일~10월 2일의 5개 날짜 열도 각각 3개 식단과 가격 `6,500/7,500/6,500`으로 분리되는지 확인했습니다.

## 상록원 원인 판정 기준

| 관측값 | 판정 |
|---|---|
| 사람 확인 문구, CAPTCHA 스크립트/마커 | `ACCESS_BLOCKED` / `CAPTCHA` |
| HTTP 401, 403, 429 또는 Forbidden/Access denied 문구 | `ACCESS_BLOCKED` / `ACCESS_RESTRICTED` |
| 공식 호스트·예상 경로가 아닌 최종 URL | `DOWNLOAD_ERROR` / `UNEXPECTED_REDIRECT` |
| HTTP 5xx | `DOWNLOAD_ERROR` / `SERVER_ERROR` |
| HTTP 4xx | `DOWNLOAD_ERROR` / `HTTP_ERROR` |
| HTML이 아닌 Content-Type | `VALIDATION_ERROR` / `UNEXPECTED_CONTENT_TYPE` |
| 정상 호스트의 HTML이나 필수 식단 DOM이 없음 | `PARSE_ERROR` / `HTML_STRUCTURE_CHANGED` |

HTTP 200이어도 보안 페이지이면 성공으로 처리하지 않습니다. 실패 HTML은 진단용으로만 보존하며 민감 헤더는 저장하지 않습니다.

## 공식 대체 경로 평가

1. 주간 식단: `https://dgucoop.dongguk.edu/store/store.php?w=4&l=2`
2. 오늘의 식단: `https://dgucoop.dongguk.edu/store/store.php?w=4&l=1`
3. 모바일 상록원 3층 일일 식단: `https://dgucoop.dongguk.edu/mobile/menu.html?code=5`

2번과 3번은 로컬에서 정상 식단을 반환했습니다. 현재 코드는 1번 실패 시 3번을 공식 폴백으로 사용합니다. 검색과 공개 페이지 탐색 범위에서는 생협 도메인 밖의 공식 JSON API나 별도 공개 데이터 파일은 확인되지 않았습니다. GitHub runner에서 1번과 3번이 모두 차단된다면 정상적인 공개 URL 교체만으로 해결할 수 없습니다.

## 완전 자동화를 위해 남은 조건

- 갱신된 코드를 GitHub에 업로드하고 Actions를 재실행해 실제 runner 응답 HTML과 분류 결과 확인
- 모바일 공식 폴백이 GitHub runner에서 성공하면 세 식당 자동화 가능
- 두 경로 모두 CAPTCHA/접근 제한이면 생협의 공식 API·허용된 공개 피드·GitHub runner IP 허용 중 하나가 필요
- 또는 정책상 허용되고 사이트가 정상 응답하는 별도 실행 환경을 사용해야 함
- 남산학사의 완전한 텍스트 메뉴가 필요하면 이미지 OCR/검수 규칙은 별도 과제이지만, 원본·일일 크롭 제공은 이미 자동화됨
- 장기 운영에서는 게시판 DOM, PDF 표 좌표, 이미지 템플릿 변경 회귀 알림 필요

현재 판단은 **남산학사 PASS, D-Flex PASS(텍스트 구조화 포함), 상록원은 로컬 PASS/GitHub runner 접근성 재확인 필요**입니다. 보안 장치 무력화 없이 GitHub Actions만으로 세 식당을 완전 자동화할 수 있는지는 2차 Actions 실행에서 모바일 폴백까지 확인한 뒤 확정해야 합니다.
