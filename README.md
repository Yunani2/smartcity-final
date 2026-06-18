# 데이터로 진단하는 업무지구의 성공과 실패

**가천대학교 스마트시티학과 | 스마트시티 이론과 실제 기말과제**  
판교테크노밸리(성공) vs 청라국제업무지구(실패) — 공공데이터 비교분석 시스템

---

## 배포 URL

- **시스템**: https://[GitHub-username].github.io/[repo-name]/
- **보고서**: LMS 제출 (PDF)

---

## 구역 정의

| 구역 | 법정동 | 법정동코드 | 면적 | 출처 |
|------|--------|-----------|------|------|
| 판교테크노밸리 | 경기도 성남시 분당구 **삼평동** | 4113510900 | 2.79 km² | 연속지적도 LSMD_CONT_LDREG_41135_202606 |
| 청라국제업무지구 | 인천광역시 서구 **청라동** | 2826012200 | 20.74 km² | 연속지적도 LSMD_CONT_LDREG_28260_202606 |

**분석 범위 명시**
- 시간범위: 2024년 기준 (건축물대장 기준일, subway_network 2024-12-31 이전 운영 노선)
- 공간범위: 상기 법정동 경계 내
- 공간단위: 건축물(동) / 집계구 / 지하철역
- 데이터 출처: SGIS 집계구는 행정구역(성남시 / 인천 서구) 단위 집계 — 집계구 shapefile 미확보로 법정동 단위 인구 배분 불가(보고서 한계 섹션 명시)

---

## 데이터 출처 및 기준

| 데이터 | 출처 | 기준일 |
|--------|------|--------|
| 건축물대장 | 건축HUB (대지구분=대지) | 2024~2025년 |
| 연속지적도 | 국토교통부 | 2026년 6월 |
| 토지이용계획정보 | VWorld | 2026년 6월 |
| 집계구 단위 인구·가구 | SGIS 통계지리정보서비스 | 2025Q2 기준, 2024년 통계 |
| 지하철 네트워크 | subway_network.zip (교수 제공) | 2026-05-05 export |
| OSM 도로망 | OpenStreetMap | 2025년 |

---

## 폴더 구조

```
project/
├── docs/                    GitHub Pages 루트
│   ├── index.html           메인 시스템
│   ├── js/
│   │   ├── main.js          Leaflet 지도 컨트롤
│   │   └── charts.js        Chart.js 통계·접근성 패널
│   └── data/                전처리 완료 정적 파일
│       ├── pangyo_zone.geojson
│       ├── cheongna_zone.geojson
│       ├── pangyo_buildings.geojson
│       ├── cheongna_buildings.geojson
│       ├── pangyo_isochrone.geojson
│       ├── cheongna_isochrone.geojson
│       ├── stats.json
│       └── accessibility_curve.json
└── scripts/                 데이터 전처리 스크립트
    ├── 00_inspect_data.py   데이터 구조 파악
    ├── 01_extract_zones.py  구역계(경계) 생성
    ├── 02_preprocess_buildings.py  건축물대장 전처리
    ├── 03_subway_isochrone.py      지하철 등시간권 분석
    └── 04_generate_stats.py        최종 stats.json 생성
```

---

## 전처리 재현 방법

```bash
# 1. 의존성 설치
pip install geopandas pandas shapely scipy numpy networkx pyogrio pyarrow

# 2. 기말 과제 데이터를 scripts와 같은 상위 폴더에 위치
# BASE 경로는 각 스크립트 상단에서 수정

# 3. 스크립트 순서대로 실행
python scripts/01_extract_zones.py
python scripts/02_preprocess_buildings.py
python scripts/03_subway_isochrone.py
python scripts/04_generate_stats.py

# 4. 결과 파일을 docs/data/로 복사 후 GitHub Pages 배포
```

---

## 핵심 분석 결과

| 지표 | 판교테크노밸리 | 청라국제업무지구 |
|------|--------------|--------------|
| 업무+연구시설 연면적 비율 | **69.9%** | 24.5% |
| 주거 연면적 비율 | 21.8% | **49.4%** |
| 평균 용적률 | **136.7%** | 91.4% |
| 30분 이내 도달 역수 | **86개** | 47개 |
| 60분 이내 도달 역수 | **454개** | 301개 |

---

## AI 활용 내역

Claude Sonnet 4.6 (Anthropic)을 사용하여 전처리 스크립트(Python/geopandas) 및 웹 시스템(HTML/CSS/JavaScript) 초안을 생성하였다. 분석 방법론·지표 선정·결과 해석은 직접 수행하였으며, AI 생성 코드의 정확성은 QGIS 및 직접 계산으로 검증하였다.
