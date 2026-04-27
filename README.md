# radar-dashboard

## Taxonomy Analysis

`taxonomy-analysis.html` is the integrated data-analysis view for all dashboard-visible child Radar/MCPRadar projects. It joins `data/projects.json` with `data/classification.json` and groups quality metrics by repo class, primary motion, governance, evidence strategy, readiness, and source status.

Build:

```bash
python radar-dashboard/scripts/build_taxonomy_analysis_dataset.py
python radar-dashboard/scripts/build_taxonomy_analysis_dashboard.py
python radar-dashboard/scripts/build_dashboard_html.py
```

Generated outputs:

- `radar-dashboard/data/taxonomy-analysis.json`
- `radar-dashboard/taxonomy-analysis.html`

`radar-dashboard`는 여러 Radar 프로젝트의 결과를 상위에서 요약해 보여주는 정적 대시보드 저장소입니다.

## 현재 상태

- `data/projects.json`, `data/summary.json` 기반 canonical 메인 대시보드
- `data/classification.json` 기반 taxonomy 점검 페이지
- `data/data-quality.json` 기반 데이터 품질 점검 페이지 (`disabled_source_classification` bucket panel + per-row chips 포함)
- `data/daily-collection.json` 기반 일일 수집 계약 점검 페이지
- `data/taxonomy-analysis.json` 기반 통합 taxonomy/risk 분석 페이지
- `data/storage-facts.json` 기반 워크스페이스 storage footprint 페이지 (raw / DuckDB / signal table / ontology / event_model 적재 점검)
- `data/event-model-rollout.json` 기반 event model coverage 페이지 (rollup, namespace × repo grid, coverage progression panel)
- 7개 페이지 HTML: `index.html` / `classification.html` / `data-quality.html` / `daily-collection.html` / `taxonomy-analysis.html` / `storage.html` / `event-model.html`, plus `dashboard.html` redirect alias
- 예전 PNG 자산은 참고용 스냅샷으로 남아 있음

즉, 현재는 완전한 애플리케이션형 대시보드는 아니지만, 워크스페이스 집계와 taxonomy 점검을 자동 생성하는 정적 대시보드까지는 올라온 상태입니다.

## 왜 바꿔야 하는가

- 프로젝트 수/기사 수/매치율/업데이트 날짜가 HTML에 직접 박혀 있어 금방 낡음
- 신규 Radar 추가나 기존 Radar 수치 갱신 시 누락 위험이 큼
- `index.html`과 `dashboard.html`의 중복 관리 비용이 큼
- 전 저장소 분류체계와 소스 공백을 점검할 상위 시각화가 필요함

## 다음 단계

집계형 대시보드 전환 설계는 [docs/aggregation-plan.md](/home/kjs/projects/ai-frendly-datahub/radar-dashboard/docs/aggregation-plan.md)에 정리했습니다.

## Phase 1 구현

기본 집계 데이터셋 생성 스크립트는 아래 경로에 추가했습니다.

```bash
python radar-dashboard/scripts/build_dashboard_dataset.py
```

생성 결과:

- `radar-dashboard/data/projects.json`
- `radar-dashboard/data/summary.json`

## Phase 2 구현

JSON 데이터셋을 canonical HTML로 렌더링하는 스크립트도 추가했습니다.

```bash
python radar-dashboard/scripts/build_dashboard_html.py
```

동작:

- `radar-dashboard/data/projects.json`, `summary.json` 읽기
- `radar-dashboard/index.html` 재생성
- `radar-dashboard/dashboard.html`을 redirect alias로 갱신

## Phase 3 구현

워크스페이스 전 저장소를 공통 taxonomy로 점검하는 분류 데이터셋과 별도 점검판도 추가했습니다.

```bash
python scripts/build_repo_taxonomy_audit.py
python radar-dashboard/scripts/build_classification_dataset.py
python radar-dashboard/scripts/build_classification_dashboard.py
```

생성 결과:

- `docs/harness/repo-taxonomy.json`
- `docs/harness/repo-taxonomy-review.md`
- `radar-dashboard/data/classification.json`
- `radar-dashboard/classification.html`

## Phase 4 구현

워크스페이스 전 저장소의 데이터 품질 우선순위를 점검하는 데이터셋과 별도 점검판을 추가했습니다.

```bash
python scripts/build_data_quality_review.py --write-repo-plans --repo-plan-priority P1 --repo-plan-scope only
python radar-dashboard/scripts/build_data_quality_dataset.py
python radar-dashboard/scripts/build_data_quality_dashboard.py
python radar-dashboard/scripts/build_dashboard_html.py
```

생성 결과:

- `docs/harness/data-quality.json`
- `docs/harness/data-quality-review.md`
- `radar-dashboard/data/data-quality.json`
- `radar-dashboard/data-quality.html`

## Phase 5 구현

워크스페이스 전 저장소의 일일 수집/날짜 기록 계약을 dashboard에 노출하는 데이터셋과 별도 점검판을 추가했습니다.

```bash
python scripts/check_daily_collection_contract.py --fail-on-partial
python radar-dashboard/scripts/build_daily_collection_dataset.py
python radar-dashboard/scripts/build_daily_collection_dashboard.py
python radar-dashboard/scripts/build_dashboard_html.py
```

생성 결과:

- `docs/harness/daily-collection-review.json`
- `docs/harness/daily-collection-review.md`
- `radar-dashboard/data/daily-collection.json`
- `radar-dashboard/daily-collection.html`

## Phase 6 구현

`radar-analysis` 가 만든 storage_facts / event_model_rollout 마트를 dashboard 가 직접 소비하도록 두 데이터셋 + 두 페이지를 추가했습니다.

```bash
python radar-dashboard/scripts/build_storage_event_model_dataset.py
python radar-dashboard/scripts/build_storage_dashboard.py
python radar-dashboard/scripts/build_event_model_dashboard.py
python radar-dashboard/scripts/build_dashboard_html.py
```

생성 결과:

- `radar-dashboard/data/storage-facts.json`
- `radar-dashboard/data/event-model-rollout.json`
- `radar-dashboard/storage.html` (Repo Storage Matrix + Raw/Signal/Ontology/Event Model gap panels)
- `radar-dashboard/event-model.html` (Namespace Coverage + Coverage Progression + Rollup + Repo × Event Model Coverage Grid)
- `index.html` 의 Storage Footprint / Event Model Coverage hero teaser

`build_event_model_dashboard.py` 는 `data/storage-facts.json` 을 optional 입력으로 받아 progression panel 을 렌더합니다 (`--storage-facts-path` 로 override).

## 빌드 순서 요약

전체 dashboard 를 재빌드하는 표준 순서:

```bash
# upstream artifacts (radar-analysis)
PYTHONPATH=radar-core python3 radar-analysis/scripts/build_workspace_analysis.py

# datasets (radar-dashboard)
python3 radar-dashboard/scripts/build_dashboard_dataset.py
python3 radar-dashboard/scripts/build_classification_dataset.py
python3 radar-dashboard/scripts/build_data_quality_dataset.py
python3 radar-dashboard/scripts/build_daily_collection_dataset.py
python3 radar-dashboard/scripts/build_storage_event_model_dataset.py
python3 radar-dashboard/scripts/build_taxonomy_analysis_dataset.py

# HTML pages (radar-dashboard)
python3 radar-dashboard/scripts/build_dashboard_html.py
python3 radar-dashboard/scripts/build_classification_dashboard.py
python3 radar-dashboard/scripts/build_data_quality_dashboard.py
python3 radar-dashboard/scripts/build_daily_collection_dashboard.py
python3 radar-dashboard/scripts/build_taxonomy_analysis_dashboard.py
python3 radar-dashboard/scripts/build_storage_dashboard.py
python3 radar-dashboard/scripts/build_event_model_dashboard.py
```

<!-- DATAHUB-OPS-AUDIT:START -->
## DataHub Operations

- CI/CD workflows: none detected under `.github/workflows/`.
- GitHub Pages visualization: root static pages: `classification.html`, `daily-collection.html`, `dashboard.html`, `data-quality.html`, `event-model.html`, `index.html`, `storage.html`, `taxonomy-analysis.html`; no Pages deployment workflow detected.
- Latest remote Pages check: not applicable.
- Local workspace audit: 10 Python files parsed, 0 syntax errors.
- Re-run audit from the workspace root: `python scripts/audit_ci_pages_readme.py --syntax-check --write`.
- Latest audit report: `_workspace/2026-04-14_github_ci_pages_readme_audit.md`.
- Latest Pages URL report: `_workspace/2026-04-14_github_pages_url_check.md`.
<!-- DATAHUB-OPS-AUDIT:END -->
