"""
Step 1-A: 구역계(경계) shapefile 생성
- 판교테크노밸리: 삼평동 법정동 경계 (PNU 앞 10자리 = 4113510900)
- 청라국제업무지구: 청라동 법정동 경계 (PNU 앞 10자리 = 2826012200)
구역계 출처: 연속지적도 (LSMD_CONT_LDREG, 2026년 6월 기준)
"""

import os
import zipfile
import geopandas as gpd
import pandas as pd
from shapely.ops import unary_union

BASE  = r"C:\Users\nanna\OneDrive\바탕 화면\2026 스마트시티학과\스시론\기말 과제"
RAW   = r"C:\Users\nanna\OneDrive\바탕 화면\2026 스마트시티학과\스시론\project\data\raw"
OUT   = r"C:\Users\nanna\OneDrive\바탕 화면\2026 스마트시티학과\스시론\project\data\processed"

# ── 경기 연속지적도 로드 ──────────────────────────────────────────────
gyeonggi_shp = os.path.join(RAW, "cadastral_gyeonggi", "LSMD_CONT_LDREG_41135_202606.shp")
if not os.path.exists(gyeonggi_shp):
    with zipfile.ZipFile(os.path.join(BASE, "연속지적도_경기_성남시_분당구.zip")) as z:
        z.extractall(os.path.join(RAW, "cadastral_gyeonggi"))

gdf_g = gpd.read_file(gyeonggi_shp, engine="pyogrio")
print(f"경기 분당구 연속지적도: {len(gdf_g):,}개 필지")

# ── 인천 연속지적도 로드 ──────────────────────────────────────────────
incheon_shp = os.path.join(RAW, "cadastral_incheon", "LSMD_CONT_LDREG_28260_202606.shp")
if not os.path.exists(incheon_shp):
    with zipfile.ZipFile(os.path.join(BASE, "연속지적도_인천_서구.zip")) as z:
        z.extractall(os.path.join(RAW, "cadastral_incheon"))

gdf_i = gpd.read_file(incheon_shp, engine="pyogrio")
print(f"인천 서구 연속지적도: {len(gdf_i):,}개 필지")

# ── 판교테크노밸리: 삼평동 (법정동코드 4113510900) 필지 추출 ───────
# PNU 구조: 법정동코드(10) + 산여부(1) + 본번(4) + 부번(4) = 19자리
SAMYEONG_CODE = "4113510900"
pangyo_parcels = gdf_g[gdf_g["PNU"].str.startswith(SAMYEONG_CODE)].copy()
print(f"\n판교(삼평동) 필지 수: {len(pangyo_parcels):,}")

pangyo_zone = gpd.GeoDataFrame(
    {"name": ["판교테크노밸리"], "dong": ["삼평동"], "dong_code": [SAMYEONG_CODE]},
    geometry=[unary_union(pangyo_parcels.geometry)],
    crs=gdf_g.crs
)
# WGS84로 변환
pangyo_zone_wgs = pangyo_zone.to_crs("EPSG:4326")
area_m2 = pangyo_parcels.to_crs("EPSG:5179").geometry.area.sum()
print(f"판교 구역 면적: {area_m2/1e6:.4f} km²")

# ── 청라국제업무지구: 청라동 (법정동코드 2826012200) 필지 추출 ──────
CHEONGNA_CODE = "2826012200"
cheongna_parcels = gdf_i[gdf_i["PNU"].str.startswith(CHEONGNA_CODE)].copy()
print(f"\n청라(청라동) 필지 수: {len(cheongna_parcels):,}")

cheongna_zone = gpd.GeoDataFrame(
    {"name": ["청라국제업무지구"], "dong": ["청라동"], "dong_code": [CHEONGNA_CODE]},
    geometry=[unary_union(cheongna_parcels.geometry)],
    crs=gdf_i.crs
)
cheongna_zone_wgs = cheongna_zone.to_crs("EPSG:4326")
area_m2_c = cheongna_parcels.to_crs("EPSG:5179").geometry.area.sum()
print(f"청라 구역 면적: {area_m2_c/1e6:.4f} km²")

# ── 저장 ───────────────────────────────────────────────────────────────
os.makedirs(OUT, exist_ok=True)
pangyo_zone_wgs.to_file(os.path.join(OUT, "pangyo_zone.geojson"), driver="GeoJSON")
cheongna_zone_wgs.to_file(os.path.join(OUT, "cheongna_zone.geojson"), driver="GeoJSON")

# 면적 정보 저장 (보고서용)
zone_info = {
    "pangyo": {
        "name": "판교테크노밸리",
        "dong": "삼평동",
        "dong_code": SAMYEONG_CODE,
        "area_km2": round(area_m2/1e6, 4),
        "parcel_count": len(pangyo_parcels),
        "source": "연속지적도 LSMD_CONT_LDREG_41135_202606 (2026년 6월 기준)",
        "definition": "경기도 성남시 분당구 삼평동 법정동 경계 (판교테크노밸리 핵심 업무·연구지구)"
    },
    "cheongna": {
        "name": "청라국제업무지구",
        "dong": "청라동",
        "dong_code": CHEONGNA_CODE,
        "area_km2": round(area_m2_c/1e6, 4),
        "parcel_count": len(cheongna_parcels),
        "source": "연속지적도 LSMD_CONT_LDREG_28260_202606 (2026년 6월 기준)",
        "definition": "인천광역시 서구 청라동 법정동 경계 (인천경제자유구역(IFEZ) 청라지구)"
    }
}

import json
with open(os.path.join(OUT, "zone_info.json"), "w", encoding="utf-8") as f:
    json.dump(zone_info, f, ensure_ascii=False, indent=2)

print("\n=== 저장 완료 ===")
print(f"pangyo_zone.geojson, cheongna_zone.geojson, zone_info.json → {OUT}")
print("\n[구역계 정의 요약]")
print(f"판교테크노밸리: {zone_info['pangyo']['definition']}")
print(f"  면적: {zone_info['pangyo']['area_km2']} km², 필지 수: {zone_info['pangyo']['parcel_count']:,}")
print(f"  출처: {zone_info['pangyo']['source']}")
print(f"\n청라국제업무지구: {zone_info['cheongna']['definition']}")
print(f"  면적: {zone_info['cheongna']['area_km2']} km², 필지 수: {zone_info['cheongna']['parcel_count']:,}")
print(f"  출처: {zone_info['cheongna']['source']}")
