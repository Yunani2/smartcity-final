# 데이터로 진단하는 업무지구의 성공과 실패

**가천대학교 스마트시티학과 | 스마트시티 이론과 실제 기말과제**  
판교테크노밸리(성공) vs 청라국제업무지구(부진) — 공공데이터 비교분석 시스템

---

## 배포 URL

- **대시보드**: https://yunani2.github.io/smartcity-final/
- **보고서**: LMS 제출 (PDF)

---

## 구역 정의

두 구역 모두 법정동 전체가 아닌, **PROM(공간정보 오픈플랫폼) 구역계 직접 설정** 기능으로 업무지구 실제 경계를 수동 지정하였음.

| 항목 | 판교테크노밸리 | 청라국제업무지구 |
|------|--------------|--------------|
| 정식명칭 | 판교테크노밸리 제1단지 사업지구 | 인천경제자유구역 청라지구 업무·상업·주거 복합지구 |
| 행정구역 | 경기도 성남시 분당구 | 인천광역시 서구 |
| 구역계 출처 | PROM 구역계 직접 설정 (2026년 6월) | PROM 구역계 직접 설정 (2026년 6월) |
| **면적** | **0.9621 km²** | **9.8595 km²** |
| 건축물 수 | 83동 | 552동 |
| 총 연면적 | 261.97만 ㎡ | 137.10만 ㎡ |
| 핵심역 | 판교역 (신분당선) | 청라국제도시역 (공항철도) |
| 핵심역 위치 | 구역 **외부** (경계까지 588 m) | 구역 **내부** (중심까지 349 m) |

---

## 데이터 출처 및 기준월

| 데이터 | 출처 | 기준연도·월 | 공간단위 |
|--------|------|-----------|---------|
| 구역계(경계) | 공간정보 오픈플랫폼(PROM) 구역계 직접 설정 | 2026년 6월 | 구역 폴리곤 |
| 건축물 주용도·연면적·용적률 | 공간정보 오픈플랫폼(PROM) 건축물현황정보 | 2026년 6월 | 건축물(동) |
| 용도지역 구성비 | 공간정보 오픈플랫폼(PROM) 도시계획·용도지역 (VWorld) | 2026년 6월 | 용도지역 폴리곤 |
| 지하철 네트워크·이소크론 | subway_network.zip (교수 제공) · 다익스트라 최단경로 | 2026년 5월 export · 2024-12-31 기준 운영 노선 필터 | 역(노드)·구간(엣지) |
| 등시간권 추정 인구·종사자 | SGIS 집계구 인구통계 × 이소크론 폴리곤 공간조인 (Script 12) | 2024년 | 집계구 |
| 구역 내 집계구 인구·가구 | SGIS 통계지리정보서비스 집계구 인구·가구통계 | 2024년 | 집계구 → 구역 내 합산 |
| 구역 내 집계구 사업체 수 | SGIS 집계구별 사업체 수 (전국사업체조사, 10차 산업분류 대분류) | 2023년 | 집계구 → 구역 내 합산 |
| 시군구 인구·종사자·직주비 | SGIS 시군구 단위 통계 (성남시 분당구 / 인천 서구) | 2023~2024년 | 시군구 |
| 도로망 밀도 | OpenStreetMap (osmnx 다운로드) | 2026년 6월 | 도로 구간(edge) |

---

## 핵심 분석 결과

### 3-1 토지이용

| 지표 | 판교테크노밸리 | 청라국제업무지구 |
|------|--------------|--------------|
| 업무시설 비율 (연면적) | **66.2%** | 17.97% |
| 교육연구시설 비율 (연면적) | **29.9%** | 8.75% |
| 업무+교육연구 합계 | **96.1%** | 26.72% |
| 주거 비율 (연면적) | — | **62.29%** |
| 평균 용적률 | **276.51%** | 97.21% |
| 토지이용 혼합도 (LUM 엔트로피) | 0.6937 | 0.6343 |
| 용도지역 1위 (면적) | 준주거지역 74.79% | 자연녹지지역 58.45% |

### 3-2 교통망

| 지표 | 판교테크노밸리 | 청라국제업무지구 |
|------|--------------|--------------|
| 30분권 도달 역수 (지하철) | **86역** | 47역 |
| 60분권 도달 역수 (지하철) | **454역** | 301역 |
| 30분권 추정 총인구 | **824,301명** | 387,690명 |
| 30분권 추정 경제활동인구 | **428,636명** | 201,598명 |
| 차량도로 밀도 | **13.73 km/km²** | 9.93 km/km² |
| 보행도로 밀도 | **25.71 km/km²** | 22.80 km/km² |

### 3-3 인구사회 (구역 내 집계구 합산)

| 지표 | 판교테크노밸리 | 청라국제업무지구 |
|------|--------------|--------------|
| 구역 내 상주인구 | 562명 (집계구 3개) | 34,902명 (집계구 67개) |
| 구역 내 가구수 | 519가구 | 13,277가구 |
| 구역 내 사업체수 | 1,927개 | 1,551개 |
| 구역 내 정보통신업 비율 | **22.99%** | 2.77% |
| 구역 내 전문·과학·기술 비율 | **12.97%** | 4.32% |
| 직주비 (시군구) | 0.805 (분당구) | — |

---

## 폴더 구조

```
project/
├── docs/                          GitHub Pages 루트 (별도 서버·DB 없이 동작)
│   ├── index.html                 메인 대시보드 (탭: 지도 비교 / 통계 분석 / 분석 메타데이터)
│   ├── js/
│   │   ├── main.js                Leaflet 지도 초기화·레이어 관리·이소크론 슬라이더
│   │   └── charts.js              Chart.js 통계 패널 (토지이용·교통망·인구사회 차트)
│   └── data/                      전처리 완료 정적 파일 (총 15개)
│       ├── pangyo_zone.geojson         판교 구역계 폴리곤
│       ├── cheongna_zone.geojson       청라 구역계 폴리곤
│       ├── pangyo_buildings.geojson    판교 건축물 (주용도·연면적·용적률, 83동)
│       ├── cheongna_buildings.geojson  청라 건축물 (주용도·연면적·용적률, 552동)
│       ├── pangyo_zoning.geojson       판교 용도지역 폴리곤
│       ├── cheongna_zoning.geojson     청라 용도지역 폴리곤
│       ├── pangyo_isochrone.geojson    판교역 5~60분 등시간권 (5분 단위 12단계)
│       ├── cheongna_isochrone.geojson  청라역 5~60분 등시간권 (5분 단위 12단계)
│       ├── pangyo_roads.geojson        판교 구역 내 도로망 (OSM)
│       ├── cheongna_roads.geojson      청라 구역 내 도로망 (OSM)
│       ├── pangyo_stations_reach.geojson    판교역 30/60분권 도달역 좌표
│       ├── cheongna_stations_reach.geojson  청라역 30/60분권 도달역 좌표
│       ├── accessibility_curve.json    5~60분 누적 접근성 곡선 (역 수·인구·종사자)
│       ├── stats.json                  전체 비교 지표 통합 (대시보드 유일 데이터 소스)
│       └── zone_info.json              구역 기본정보 (면적·건축물수·핵심역 등)
└── scripts/                       데이터 전처리 스크립트 (번호 순서대로 실행)
    ├── 00_inspect_data.py
    ├── 01_extract_zones.py
    ├── 02_preprocess_buildings.py
    ├── 03_subway_isochrone.py
    ├── 04_generate_stats.py
    ├── 05_osm_roads.py
    ├── 06_population.py
    ├── 07_update_cheongna_prom.py
    ├── 08_finalize_data.py
    ├── 09_add_zoning_industry.py
    ├── 10_census_zone_stats.py
    ├── 11_household_stats.py
    └── 12_isochrone_census_join.py
```

---

## 전처리 스크립트 설명 및 처리 과정

| 스크립트 | 입력 | 처리 내용 | 주요 출력 |
|---------|------|---------|---------|
| `00_inspect_data.py` | 원본 ZIP | 건축물대장·연속지적도 컬럼 구조·주용도 코드 확인 | 탐색 로그 |
| `01_extract_zones.py` | 연속지적도 SHP (경기·인천) | PNU 앞 10자리로 법정동 필터 → 폴리곤 합집합으로 초기 구역 경계 생성 | `pangyo_zone.geojson`, `cheongna_zone.geojson`, `zone_info.json` |
| `02_preprocess_buildings.py` | 건축물대장 CSV, 연속지적도 SHP | 주용도코드 → 8개 분류 매핑, 연면적·용적률 정제, PNU 매칭 좌표 획득, 구역 내 필터 | `pangyo_buildings.geojson`, `cheongna_buildings.geojson`, `building_metrics.json` |
| `03_subway_isochrone.py` | subway_network.zip | 판교역(node 824)·청라역(node 313)에서 Dijkstra 최단경로, 5~60분 12단계 이소크론, 집계구 공간조인 인구 산출 | `pangyo_isochrone.geojson`, `cheongna_isochrone.geojson`, `accessibility_curve.json` |
| `04_generate_stats.py` | building_metrics.json, accessibility_curve.json, zone_info.json, 집계구 CSV | 초기 지표 통합 및 시군구 수준 인구·종사자 합산 | `stats.json` (초기) |
| `05_osm_roads.py` | zone GeoJSON, OSM API | osmnx로 구역 범위 도로망 다운로드, 차량·보행 도로 밀도(km/km²)·교차로 수 산출 | `pangyo_roads.geojson`, `cheongna_roads.geojson`, stats.json road 항목 추가 |
| `06_population.py` | 집계구 인구 CSV, stations_reach GeoJSON | 2024년 시군구별 주민등록인구 기반 등시간권 도달 가능 인구 추정 | stats.json 인구·종사자 항목 갱신 |
| `07_update_cheongna_prom.py` | PROM 청라 구역계·건축물 SHP (EPSG:5174) | 청라 구역계 및 건축물을 PROM 구역계 직접 설정 버전으로 교체, 좌표계 변환(5174→4326) | `cheongna_zone.geojson`, `cheongna_buildings.geojson`, zone_info·building_metrics 갱신 |
| `08_finalize_data.py` | processed 전체, 집계구 사업체 CSV, subway_network.zip | 건물 geometry 보정, 역세권 500m/1km 버퍼 면적비율, 구역-핵심역 직선거리, 경제활동인구 추정(×0.52), 사업체수 추가 | stats.json 보완 |
| `09_add_zoning_industry.py` | PROM 용도지역 SHP, 집계구 사업체 CSV | 구역 내 용도지역 면적비율 산출, 10차 산업분류 대분류 매핑 재계산, zoning GeoJSON 생성 | `pangyo_zoning.geojson`, `cheongna_zoning.geojson`, stats.json land_use_zoning 추가 |
| `10_census_zone_stats.py` | 집계구 경계 SHP, 집계구 사업체·인구 CSV | 집계구 경계 × 구역 폴리곤 공간필터 → 구역 내 집계구 추출(판교 3개·청라 67개), 인구·사업체 합산 | stats.json sociodemographics 갱신 |
| `11_household_stats.py` | 집계구 경계 SHP, 집계구 가구통계 CSV | 구역 내 집계구 가구수 합산 (판교 519가구·청라 13,277가구) | stats.json 가구수 항목 갱신 |
| `12_isochrone_census_join.py` | 집계구 경계 SHP (서울·경기·인천), 집계구 인구통계 CSV | 집계구 대표점 × 이소크론 폴리곤(역 500m 버퍼 합집합) 공간조인, 5분 단위 누적 인구·종사자(×0.52) 산정, 이소크론 GeoJSON 재생성 | `pangyo_isochrone.geojson`, `cheongna_isochrone.geojson`, `accessibility_curve.json` (최종), stats.json iso_timeseries 갱신 |

---

## 전처리 재현 방법

```bash
# 1. 의존성 설치
pip install geopandas pandas shapely scipy numpy networkx pyogrio pyarrow osmnx

# 2. 원본 데이터 배치 (스크립트 내 BASE 경로 참고)
# 필요 파일 목록:
# - PROM 구역계·건축물·용도지역 다운로드 폴더 (prom_구역계 설정_판교테크노밸리.zip, prom_cheongna_new/)
# - subway_network.zip (교수 제공)
# - 집계구 경계_성남시 분당구.zip / 집계구 경계_인천 서구.zip
# - 집계구 경계_서울.zip / 집계구 경계_경기.zip / 집계구 경계_인천.zip
# - 집계구별 사업체 수_성남시 분당구.zip / 집계구별 사업체 수_인천 서구.zip
# - 집계구별 인구통계_성남시 분당구.zip / 집계구별 인구통계_인천서구.zip
# - 집계구 인구통계_서울.zip / 집계구 인구통계_경기.zip / 집계구 인구통계_인천.zip
# - 집계구별 가구통계_경기도 분당구.zip / 집계구별 가구통계_인천 서구.zip

# 3. 스크립트 순서대로 실행
python scripts/01_extract_zones.py
python scripts/02_preprocess_buildings.py
python scripts/03_subway_isochrone.py
python scripts/04_generate_stats.py
python scripts/05_osm_roads.py
python scripts/06_population.py
python scripts/07_update_cheongna_prom.py
python scripts/08_finalize_data.py
python scripts/09_add_zoning_industry.py
python scripts/10_census_zone_stats.py
python scripts/11_household_stats.py
python scripts/12_isochrone_census_join.py

# 4. docs/data/ 의 정적 파일들이 자동 갱신됨
# 5. git push 후 GitHub Pages 에서 확인
```

---

## AI 활용 내역

Claude Sonnet 4.6 (Anthropic)을 사용하여 전처리 스크립트(Python/geopandas) 및 웹 시스템(HTML/CSS/JavaScript) 초안을 생성하였다. 분석 방법론·지표 선정·결과 해석은 직접 수행하였으며, AI 생성 코드의 정확성은 QGIS 및 직접 계산으로 검증하였다.
