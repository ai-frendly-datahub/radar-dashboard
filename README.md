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
- `data/data-quality.json` 기반 데이터 품질 점검 페이지
- `data/daily-collection.json` 기반 일일 수집 계약 점검 페이지
- `index.html` 메인 상태판, `classification.html` 분류체계 감사판, `data-quality.html` 데이터 품질 감사판, `daily-collection.html` 일일 수집 계약판, `dashboard.html` redirect alias
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

<!-- DATAHUB-OPS-AUDIT:START -->
## DataHub Operations

- CI/CD workflows: none detected under `.github/workflows/`.
- GitHub Pages visualization: root static pages: `classification.html`, `daily-collection.html`, `dashboard.html`, `data-quality.html`, `index.html`, `taxonomy-analysis.html`; no Pages deployment workflow detected.
- Latest remote Pages check: not applicable.
- Local workspace audit: 10 Python files parsed, 0 syntax errors.
- Re-run audit from the workspace root: `python scripts/audit_ci_pages_readme.py --syntax-check --write`.
- Latest audit report: `_workspace/2026-04-14_github_ci_pages_readme_audit.md`.
- Latest Pages URL report: `_workspace/2026-04-14_github_pages_url_check.md`.
<!-- DATAHUB-OPS-AUDIT:END -->
