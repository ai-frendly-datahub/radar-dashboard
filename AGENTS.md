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
├── index.html                   # 메인 대시보드 (storage / event-model teaser 포함)
├── classification.html          # workspace taxonomy 점검판
├── data-quality.html            # workspace data quality 점검판 (disabled bucket panel + per-row chips)
├── daily-collection.html        # workspace daily collection 계약 점검판
├── taxonomy-analysis.html       # 통합 taxonomy / risk 분석판
├── storage.html                 # workspace storage footprint 점검판
├── event-model.html             # event model coverage 점검판 (rollup + namespace × repo grid + progression panel)
├── dashboard.html               # redirect alias
├── data/
│   ├── projects.json
│   ├── summary.json
│   ├── classification.json
│   ├── data-quality.json
│   ├── daily-collection.json
│   ├── taxonomy-analysis.json
│   ├── storage-facts.json       # radar-analysis 마트 사본
│   └── event-model-rollout.json # radar-analysis 마트 사본
├── scripts/
│   ├── build_dashboard_dataset.py
│   ├── build_dashboard_html.py
│   ├── build_classification_dataset.py
│   ├── build_classification_dashboard.py
│   ├── build_data_quality_dataset.py
│   ├── build_data_quality_dashboard.py
│   ├── build_daily_collection_dataset.py
│   ├── build_daily_collection_dashboard.py
│   ├── build_taxonomy_analysis_dataset.py
│   ├── build_taxonomy_analysis_dashboard.py
│   ├── build_storage_event_model_dataset.py
│   ├── build_storage_dashboard.py
│   └── build_event_model_dashboard.py
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
- Phase 6 storage / event-model 데이터셋 동기화는 `scripts/build_storage_event_model_dataset.py`로 `radar-analysis/data/exports/storage_facts.json` 와 `event_model_rollout.json` 을 복사합니다.
- Phase 6 storage 점검 페이지 생성은 `scripts/build_storage_dashboard.py`를 사용합니다.
- Phase 6 event-model 점검 페이지 생성은 `scripts/build_event_model_dashboard.py`를 사용하며, `data/storage-facts.json` 을 optional 입력으로 받아 coverage progression panel을 렌더합니다.
- 모든 dashboard 페이지는 cross-page nav (Main / Classification / Quality / Daily Collection / Taxonomy Analysis / Storage / Event Model) 를 일관되게 노출합니다.

## NOTES

- 이 저장소는 별도 Python 코드가 없으므로 코드 검증보다 링크/수치/자산 정합성 검증이 중요합니다.
