# RADAR-DASHBOARD

## TAXONOMY ANALYSIS ADDITION

- `taxonomy-analysis.html` is the integrated data-analysis view for all dashboard-visible child Radar/MCPRadar projects.
- Source dataset: `data/taxonomy-analysis.json`.
- Build commands:
  - `python radar-dashboard/scripts/build_taxonomy_analysis_dataset.py`
  - `python radar-dashboard/scripts/build_taxonomy_analysis_dashboard.py`
- The page joins `data/projects.json` and `data/classification.json`, then groups quality metrics by repo class, primary motion, governance, evidence strategy, readiness, and source status.
- After rebuilding the taxonomy analysis page, run `python radar-dashboard/scripts/build_dashboard_html.py` so `index.html` links to it.

여러 Radar 저장소의 산출물을 상위에서 요약해 보여주는 정적 대시보드 저장소입니다. 현재는 메인 상태판과 taxonomy 점검판을 JSON 데이터셋에서 생성하며, 개별 Radar 저장소의 파이프라인을 직접 실행하지는 않습니다.

## CURRENT STRUCTURE

```
radar-dashboard/
├── index.html                   # 메인 대시보드
├── classification.html          # workspace taxonomy 점검판
├── data-quality.html            # workspace data quality 점검판
├── daily-collection.html        # workspace daily collection 계약 점검판
├── dashboard.html               # redirect alias
├── data/
│   ├── projects.json            # 프로젝트 메트릭 집계
│   ├── summary.json             # 메인 대시보드 요약
│   ├── classification.json      # taxonomy audit 데이터셋
│   ├── data-quality.json        # data quality audit 데이터셋
│   └── daily-collection.json    # daily collection audit 데이터셋
├── scripts/
│   ├── build_dashboard_dataset.py
│   ├── build_dashboard_html.py
│   ├── build_classification_dataset.py
│   ├── build_classification_dashboard.py
│   ├── build_data_quality_dataset.py
│   ├── build_data_quality_dashboard.py
│   ├── build_daily_collection_dataset.py
│   └── build_daily_collection_dashboard.py
└── *.png                        # 예전 수동 스냅샷 자산
```

## CURRENT LIMITATIONS

- 워크플로 자동 실행까지는 아직 붙지 않았습니다.
- taxonomy 점검은 중앙 산출물 기준이며 개별 저장소 내부 문서와 완전히 동기화되는 구조는 아닙니다.
- 예전 PNG 스냅샷 자산과 새 canonical HTML이 함께 있어 정리 여지가 남아 있습니다.

## IMMEDIATE RULES

- 현재는 정적 스냅샷 저장소로 취급합니다.
- 수치를 수정할 때는 upstream Radar 산출물과 대조한 뒤 갱신합니다.
- 자동 집계형으로 전환하려면 먼저 `docs/aggregation-plan.md` 설계를 따릅니다.
- Phase 1 데이터셋 생성은 `scripts/build_dashboard_dataset.py`를 사용합니다.
- Phase 2 canonical HTML 생성은 `scripts/build_dashboard_html.py`를 사용합니다.
- Phase 3 taxonomy 데이터셋 생성은 `scripts/build_classification_dataset.py`를 사용합니다.
- Phase 3 taxonomy 점검 페이지 생성은 `scripts/build_classification_dashboard.py`를 사용합니다.
- Phase 4 data quality 데이터셋 생성은 `scripts/build_data_quality_dataset.py`를 사용합니다.
- Phase 4 data quality 점검 페이지 생성은 `scripts/build_data_quality_dashboard.py`를 사용합니다.
- Phase 5 daily collection 데이터셋 생성은 `scripts/build_daily_collection_dataset.py`를 사용합니다.
- Phase 5 daily collection 점검 페이지 생성은 `scripts/build_daily_collection_dashboard.py`를 사용합니다.

## NOTES

- 이 저장소는 별도 Python 코드가 없으므로 코드 검증보다 링크/수치/자산 정합성 검증이 중요합니다.
