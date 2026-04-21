# radar-dashboard Aggregation Plan

## 목표

현재의 정적 스냅샷 대시보드를, 각 Radar 저장소의 산출물을 읽어 자동으로 갱신되는 집계형 대시보드로 전환한다.

## 현재 문제

1. `index.html`과 `dashboard.html`에 수치와 날짜가 하드코딩되어 있다.
2. 어떤 Radar가 활성 프로젝트인지, 마지막 업데이트가 언제인지 코드에서 계산되지 않는다.
3. 신규 저장소가 추가되거나 기존 저장소 수치가 변해도 대시보드가 자동 반영되지 않는다.
4. 시각화 PNG도 생성 경로가 명확하지 않아 재현성이 낮다.

## 설계 원칙

- Phase 1에서는 기존 정적 HTML을 최대한 유지하고, 데이터만 자동 생성한다.
- 집계 소스는 각 Radar 저장소의 기존 산출물을 우선 사용한다.
- dashboard 전환이 개별 Radar 파이프라인을 깨지 않도록, 읽기 전용 집계부터 시작한다.
- 없는 데이터는 추론하지 말고 `unknown` 또는 `null`로 남긴다.

## 입력 데이터 원천

### 1. 기본 집계 소스

각 저장소에서 우선적으로 읽을 대상:

- `reports/*_summary.json`
- `reports/index.html`
- `data/*.duckdb`
- 필요 시 `README.md`, `AGENTS.md`

### 2. 최소 프로젝트 메타데이터

프로젝트별로 아래 필드를 집계한다.

```json
{
  "repo": "FoodRadar",
  "display_name": "Food",
  "status": "active",
  "articles_total": 82,
  "matched_total": 35,
  "match_rate": 42.7,
  "sources_count": 5,
  "last_updated": "2026-03-31",
  "report_path": "../FoodRadar/reports/index.html",
  "data_origin": "reports/food_20260331_summary.json"
}
```

## 제안 아키텍처

```text
각 Radar 저장소 reports/*.json, reports/index.html
  -> radar-dashboard/scripts/build_dashboard_dataset.py
  -> radar-dashboard/data/projects.json
  -> radar-dashboard/data/summary.json
  -> radar-dashboard/index.html 템플릿 렌더링
  -> 선택적으로 charts/*.png 또는 JS 차트 데이터 생성
```

## 단계별 전환

### Phase 1: 데이터셋 자동 생성

추가 파일:

- `radar-dashboard/scripts/build_dashboard_dataset.py`
- `radar-dashboard/data/projects.json`
- `radar-dashboard/data/summary.json`

동작:

- 각 하위 저장소를 순회한다.
- 가장 최근 `*_summary.json`을 찾아 핵심 수치를 읽는다.
- summary가 없으면 `reports/index.html` 또는 DuckDB에서 fallback을 시도한다.
- 결과를 JSON으로 저장한다.

이 단계에서는 HTML 시각 구조는 크게 바꾸지 않는다.

### Phase 2: HTML 템플릿화

추가 파일:

- `radar-dashboard/templates/dashboard.html.j2` 또는 단일 HTML 템플릿

동작:

- `projects.json`, `summary.json`을 읽어 `index.html`을 다시 생성한다.
- `dashboard.html`과 `index.html` 중 하나만 canonical로 남긴다.
- 정렬 기준과 결측값 표기를 통일한다.

현재 상태:

- `scripts/build_dashboard_html.py`로 구현됨
- canonical 출력은 `index.html`
- `dashboard.html`은 redirect alias로 유지

### Phase 3: 차트 자동 생성

선택지:

- Python 스크립트로 PNG 재생성
- 또는 차트 데이터 JSON을 만들고 브라우저에서 렌더링

권장:

- 초기에는 JSON + 브라우저 렌더링이 재현성과 유지보수 측면에서 낫다.

### Phase 4: GitHub Actions 통합

워크플로:

1. 각 Radar 파이프라인 실행 또는 기존 아티팩트 수집
2. dashboard dataset 생성
3. HTML 렌더링
4. Pages 배포

## 데이터 계약 제안

개별 Radar 저장소가 dashboard 친화적으로 되려면 summary JSON에 다음 키를 안정적으로 포함하는 것이 좋다.

- `category`
- `generated_at`
- `article_count`
- `matched_count`
- `sources_count`
- `date_range`
- `report_path`

가능하면 모든 Radar가 공통 shape를 따르도록 `radar-core` 또는 `Radar-Template`에서 summary schema를 표준화한다.

## 우선 구현 순서

1. `reports/*_summary.json` shape 조사
2. `build_dashboard_dataset.py` 추가
3. `projects.json`, `summary.json` 생성
4. `index.html`을 JSON 기반으로 재생성
5. `dashboard.html` 중복 제거

## 리스크

- 각 Radar의 summary JSON 구조가 완전히 같지 않을 수 있음
- 일부 저장소는 summary 대신 HTML만 있을 수 있음
- `radar-dashboard`가 루트 워크스페이스 경로에 의존하게 되므로 실행 기준 경로를 명확히 해야 함
- `Radar-Template`와 `radar-core`가 summary schema를 아직 강제하지 않음

## 성공 기준

- 신규 Radar 저장소가 추가돼도 코드 수정 없이 데이터셋에 자동 포함된다.
- 프로젝트 수, 기사 수, 최신 날짜를 수동으로 HTML에 적지 않는다.
- dashboard 페이지가 한 개의 canonical 출력만 가진다.
- 집계 과정이 스크립트로 재현 가능하다.
