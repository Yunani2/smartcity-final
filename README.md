# 데이터로 진단하는 업무지구의 성공과 실패

**가천대학교 스마트시티학과 | 스마트시티 이론과 실제 기말과제**  
판교테크노밸리(성공) vs 청라국제업무지구(실패) — 공공데이터 비교분석 시스템

---

## 배포 URL

- **대시보드**: https://yunani2.github.io/smartcity-final/
- **보고서**: LMS 제출 (PDF)

---

## 구역 정의

| 구역 | 법정동 | 법정동코드 | 면적 | 출처 |
|------|--------|-----------|------|------|
| 판교테크노밸리 | 경기도 성남시 분당구 **삼평동** | 4113510900 | 2.79 km² | 연속지적도 LSMD_CONT_LDREG_41135_202606 |
| 청라국제업무지구 | 인천광역시 서구 **청라동** | 2826012200 | 20.74 km² | 연속지적도 LSMD_CONT_LDREG_28260_202606 |

> **주의**: 두 구역 모두 공간정보 오픈플랫폼(PROM) 구역계 직접 설정 기반(2026년 6월).  
> 청라의 경우 청라지구 전체가 아닌, 호수공원 좌측 업무·상업·주거 복합 핵심지구만 포함.

---

## 데이터 출처 및 기준월

| 데이터 | 출처 | 기준연도/월 | 공간단위 |
|--------|------|------------|---------|
| 구역계(경계) | 공간정보 오픈플랫폼(PROM) 구역계 직접 설정 | 2026년 6월 | 구역 폴리곤 |
| 연속지적도 | 국토교통부 연속지적도 (LSMD_CONT_LDREG) | 2026년 6월 | 필지 폴리곤 |
| 용도지역 구성비 | 공간정보 오픈플랫폼(PROM) 도시계획·용도지역 (VWorld 국토지리정보원) | 2026년 6월 | 용도지역 폴리곤 |
| 건축물 주용도·연면적·용적률 | 공간정보 오픈플랫폼(PROM) 건축물현황정보 | 2026년 6월 | 건축물(동) |
| 지하철 네트워크 | subway_network.zip (교수 제공, 다익스트라 최단경로) | 2026년 5월 | 역(노드)·구간(엣지) |
| 등시간권 추정 인구·종사자 | SGIS 집계구 인구통계 × 이소크론 공간조인 (Script 12) | 2024년 | 집계구 |
| 집계구 인구·가구 (구역 내) | SGIS 통계지리정보서비스 집계구 단위 인구·가구통계 | 2024년 | 집계구 → 구역 내 합산 |
| 집계구 사업체 수 (구역 내) | SGIS 집계구별 사업체 수 (전국사업체조사, 10차 산업분류 대분류) | 2023년 | 집계구 → 구역 내 합산 |
| 도로망 | OpenStreetMap (osmnx 다운로드) | 2026년 6월 | 도로 구간(edge) |

---

## 폴더 구조

```
project/
├── docs/                          GitHub Pages 루트 (정적 사이트)
│   ├── index.html                 메인 대시보드 (탭: 지도 비교 / 통계 분석 / 분석 메타데이터)
│   ├── js/
│   │   ├── main.js                Leaflet 지도 초기화·레이어 관리·이소크론 슬라이더
│   │   └── charts.js              Chart.js 통계 패널 (토지이용·교통망·인구사회 차트)
│   └── data/                      전처리 완료 정적 파일 (서버 불필요)
│       ├── pangyo_zone.geojson    판교 구역계 폴리곤
│       ├── cheongna_zone.geojson  청라 구역계 폴리곤
│       ├── pangyo_buildings.geojson    판교 건축물 (주용도·연면적·용적률)
│       ├── cheongna_buildings.geojson  청라 건축물 (주용도·연면적·용적률)
│       ├── pangyo_zoning.geojson       판교 용도지역 구성
│       ├── cheongna_zoning.geojson     청라 용도지역 구성
│       ├── pangyo_isochrone.geojson    판교역 5~60분 등시간권 (5분 단위 12단계)
│       ├── cheongna_isochrone.geojson  청라국제도시역 5~60분 등시간권
│       ├── pangyo_roads.geojson        판교 구역 내 도로망 (OSM)
│       ├── cheongna_roads.geojson      청라 구역 내 도로망 (OSM)
│       ├── pangyo_stations_reach.geojson    판교역 30/60분권 도달역 좌표
│       ├── cheongna_stations_reach.geojson  청라역 30/60분권 도달역 좌표
│       ├── accessibility_curve.json    5~60분 누적 접근성 곡선 데이터
│       ├── stats.json                  전체 비교 지표 통합 JSON
│       └── zone_info.json              구역 기본정보 (면적·건축물수 등)
└── scripts/                       데이터 전처리 스크립트
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

스크립트는 번호 순서대로 실행해야 하며, 각 단계의 출력물이 다음 단계의 입력이 됩니다.

| 스크립트 | 입력 데이터 | 처리 내용 | 주요 출력 |
|---------|------------|---------|---------|
| `00_inspect_data.py` | 원본 ZIP 파일들 | 건축물대장·연속지적도 컬럼 구조 파악, 주용도 코드 목록 확인 | 탐색 로그 (파일 미생성) |
| `01_extract_zones.py` | 연속지적도 SHP (경기·인천) | PNU 앞 10자리로 법정동 필터 → 폴리곤 합집합으로 구역 경계 생성 | `pangyo_zone.geojson`, `cheongna_zone.geojson`, `zone_info.json` |
| `02_preprocess_buildings.py` | 건축물대장 CSV, 연속지적도 SHP | 주용도코드 → 8개 분류 매핑, 연면적·용적률 정제, PNU 매칭으로 좌표 획득, 구역 내 건축물 필터 | `pangyo_buildings.geojson`, `cheongna_buildings.geojson`, `building_metrics.json` |
| `03_subway_isochrone.py` | subway_network.zip | 판교역(node 824)·청라역(node 313)에서 Dijkstra 최단경로, 5~60분 12단계 이소크론 생성, 집계구 공간조인으로 도달 인구 산출 | `pangyo_isochrone.geojson`, `cheongna_isochrone.geojson`, `accessibility_curve.json` |
| `04_generate_stats.py` | building_metrics.json, accessibility_curve.json, zone_info.json, 집계구 CSV | 지표 통합, 분당구/인천서구 집계구 CSV → 시군구 수준 인구·종사자 합산 | `stats.json` (초기 버전) |
| `05_osm_roads.py` | zone GeoJSON, OSM API | osmnx로 구역 범위 도로망 다운로드, 도로 밀도(km/km²)·교차로 수 산출 | `pangyo_roads.geojson`, `cheongna_roads.geojson`, stats.json road 항목 추가 |
| `06_population.py` | 집계구 인구 CSV, stations_reach GeoJSON | 시군구 단위 2024년 주민등록인구 기반 등시간권 도달 가능 인구 추정 (Nominatim 역지오코딩 활용) | stats.json 인구·종사자 항목 갱신 |
| `07_update_cheongna_prom.py` | PROM 청라 구역계·건축물 SHP (EPSG:5174) | 청라 구역계 및 건축물 데이터를 PROM 최신 버전으로 전면 교체, 좌표계 변환(5174→4326) | `cheongna_zone.geojson`, `cheongna_buildings.geojson`, zone_info/building_metrics 갱신 |
| `08_finalize_data.py` | processed 전체, 집계구 사업체 CSV | 청라 건물 geometry polygon 보정, 역세권 500m/1km 버퍼 면적비율 산출, 경제활동인구 추정(인구×0.52), 사업체수 추가 | stats.json 보완 |
| `09_add_zoning_industry.py` | PROM 용도지역 SHP, 집계구 사업체 CSV | 구역 내 용도지역 면적비율 산출, 10차 산업분류 대분류(CP_BNU_001~021) 매핑 재계산, 구역-핵심역 직선거리 계산 | `pangyo_zoning.geojson`, `cheongna_zoning.geojson`, stats.json 갱신 |
| `10_census_zone_stats.py` | 집계구 경계 SHP, 집계구 사업체·인구 CSV | 집계구 경계 × 구역 폴리곤 공간필터 → 구역 내 집계구 추출, 인구·사업체 합산 (판교 3개·청라 67개) | stats.json sociodemographics 갱신 |
| `11_household_stats.py` | 집계구 경계 SHP, 집계구 가구통계 CSV | 구역 내 집계구 가구수 합산 | stats.json 가구수 항목 갱신 |
| `12_isochrone_census_join.py` | 집계구 경계 SHP (서울·경기·인천), 집계구 인구통계 CSV, 이소크론 GeoJSON | 집계구 대표점 × 이소크론 폴리곤(역 500m 버퍼 합집합) 공간조인, 5분 단위 누적 인구·종사자(×0.52) 산정, 이소크론 GeoJSON 재생성 | `pangyo_isochrone.geojson`, `cheongna_isochrone.geojson`, `accessibility_curve.json` (최종), stats.json iso_timeseries 갱신 |

---

## 전처리 재현 방법

```bash
# 1. 의존성 설치
pip install geopandas pandas shapely scipy numpy networkx pyogrio pyarrow osmnx

# 2. 원본 데이터 배치
# 아래 파일들을 스크립트와 같은 프로젝트 폴더 상위 디렉토리에 위치
# - 연속지적도_경기_성남시_분당구.zip
# - 연속지적도_인천_서구.zip
# - subway_network.zip
# - prom_구역계 설정_판교테크노밸리.zip
# - prom_cheongna_new/ (청라 PROM 폴더)
# - 집계구 경계_성남시 분당구.zip / 집계구 경계_인천 서구.zip
# - 집계구별 사업체 수_성남시 분당구.zip / 집계구별 사업체 수_인천 서구.zip
# - 집계구별 인구통계_성남시 분당구.zip / 집계구별 인구통계_인천서구.zip
# - 집계구별 가구통계_경기도 분당구.zip / 집계구별 가구통계_인천 서구.zip
# - 집계구 경계_서울.zip / 집계구 경계_경기.zip / 집계구 경계_인천.zip
# - 집계구 인구통계_서울.zip / 집계구 인구통계_경기.zip / 집계구 인구통계_인천.zip

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

# 4. docs/data/ 폴더의 정적 파일이 자동 갱신됨
# 5. git push 후 GitHub Pages에서 확인
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
