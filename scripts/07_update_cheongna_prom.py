# -*- coding: utf-8 -*-
"""
07_update_cheongna_prom.py
새로운 청라 PROM 구역계 데이터로 cheongna 관련 파일 전체 갱신

입력: prom_cheongna_new/01_구역계/구역계.shp  (zone, EPSG:5174)
      prom_cheongna_new/03_건축물현황정보/건축물.shp (buildings, EPSG:5174)
출력:
  processed/cheongna_zone.geojson
  processed/cheongna_buildings.geojson
  processed/zone_info.json (cheongna 항목 갱신)
  processed/building_metrics.json (cheongna 항목 갱신)
  docs/data/ 동기화
"""

import os, json, shutil
import numpy as np
import geopandas as gpd
import pandas as pd
from shapely.ops import unary_union

BASE      = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROM_DIR  = os.path.join(BASE, "..", "prom_cheongna_new")
PROCESSED = os.path.join(BASE, "data", "processed")
DOCS_DATA = os.path.join(BASE, "docs", "data")

# ── 주용도 분류 매핑 (script 02 와 동일) ─────────────────────────────
USE_CATEGORY = {
    "업무시설":           "업무시설",
    "교육연구시설":       "교육연구시설",
    "제1종근린생활시설":  "근린생활시설",
    "제2종근린생활시설":  "근린생활시설",
    "단독주택":           "주거",
    "공동주택":           "주거",
    "판매시설":           "판매시설",
    "운수시설":           "운수시설",
    "공장":               "공장·창고",
    "창고시설":           "공장·창고",
    "자동차관련시설":     "기타",
    "운동시설":           "기타",
    "문화및집회시설":     "기타",
    "종교시설":           "기타",
    "의료시설":           "기타",
    "노유자시설":         "기타",
    "수련시설":           "기타",
    "숙박시설":           "기타",
    "위락시설":           "기타",
    "관광휴게시설":       "기타",
    "분뇨.쓰레기처리시설":"기타",
    "동물및식물관련시설": "기타",
    "묘지관련시설":       "기타",
    "방송통신시설":       "기타",
    "발전시설":           "기타",
}

def classify_use(name):
    if pd.isna(name):
        return "기타"
    name = str(name).strip()
    for key, cat in USE_CATEGORY.items():
        if key in name:
            return cat
    return "기타"

# ── SHP 파일 경로 탐색 ────────────────────────────────────────────────
all_shp = []
for root, dirs, files in os.walk(PROM_DIR):
    for f in files:
        if f.endswith(".shp"):
            all_shp.append(os.path.join(root, f))

zone_shp  = [p for p in all_shp if os.path.basename(os.path.dirname(p)).startswith("01_")][0]
# 03_ 폴더: 건축물.shp (가장 많은 column), 건축물별.shp, 층별현황.shp
bldg_shps = [p for p in all_shp if os.path.basename(os.path.dirname(p)).startswith("03_")]
# mn_use_nm 컬럼이 있는 파일 = 건축물.shp (메인)
bldg_shp  = next(p for p in bldg_shps if gpd.read_file(p, rows=1).columns.tolist().count("mn_use_nm") > 0)

print(f"Zone SHP: {zone_shp}")
print(f"Bldg SHP: {bldg_shp}")

# ── Zone 처리 ─────────────────────────────────────────────────────────
print("\n[1] 구역계 처리 중...")
gdf_zone = gpd.read_file(zone_shp)
print(f"  원본 CRS: {gdf_zone.crs}")
print(f"  feature 수: {len(gdf_zone)}")

# 전체 zone을 하나의 polygon으로 union
zone_geom = unary_union(gdf_zone.geometry)

# 면적 계산 (EPSG:5179 투영 사용)
gdf_zone_5179 = gdf_zone.to_crs("EPSG:5179")
area_m2 = gdf_zone_5179.geometry.area.sum()
area_km2 = area_m2 / 1e6
print(f"  면적: {area_km2:.4f} km²")

# WGS84 저장
gdf_zone_wgs = gpd.GeoDataFrame(
    {"name": ["청라국제업무지구(수정)"], "source": ["PROM 구역계설정 2026-06"]},
    geometry=[gdf_zone.to_crs("EPSG:4326").geometry.unary_union],
    crs="EPSG:4326"
)
out_zone = os.path.join(PROCESSED, "cheongna_zone.geojson")
gdf_zone_wgs.to_file(out_zone, driver="GeoJSON")
print(f"  저장: {out_zone}")

# ── Buildings 처리 ────────────────────────────────────────────────────
print("\n[2] 건축물 처리 중...")
gdf_bldg = gpd.read_file(bldg_shp)
print(f"  원본: {len(gdf_bldg)}동, CRS: {gdf_bldg.crs}")

# 용도 분류
gdf_bldg["use_class"] = gdf_bldg["mn_use_nm"].apply(classify_use)

# 용도 분포 확인
use_dist = gdf_bldg["use_class"].value_counts()
print("  용도 분포:")
for cls, cnt in use_dist.items():
    print(f"    {cls}: {cnt}동")

# 투영 좌표계에서 centroid 계산 후 WGS84 변환 (geographic CRS에서 centroid 하면 부정확)
gdf_bldg_5179 = gdf_bldg.to_crs("EPSG:5179")
gdf_bldg_5179["geometry"] = gdf_bldg_5179.geometry.centroid
gdf_bldg_wgs = gdf_bldg_5179.to_crs("EPSG:4326")

# zone으로 공간 필터링
zone_wgs = gdf_zone_wgs.geometry.iloc[0]
mask = gdf_bldg_wgs.geometry.within(zone_wgs)
gdf_in_zone = gdf_bldg_wgs[mask].copy()
print(f"  zone 내 건축물: {len(gdf_in_zone)}동 (전체 {len(gdf_bldg_wgs)}동 중)")

# 저장 컬럼 선택 (main.js popup과 맞춤)
keep = ["pnu", "bd_nm", "mn_use_nm", "use_class",
        "land_ar", "tot_fl_ar", "fl_ar_ratio", "gr_fl_num", "use_per_dt", "geometry"]
save_cols = [c for c in keep if c in gdf_in_zone.columns]
gdf_out = gdf_in_zone[save_cols].copy()

out_bldg = os.path.join(PROCESSED, "cheongna_buildings.geojson")
gdf_out.to_file(out_bldg, driver="GeoJSON")
print(f"  저장: {out_bldg}")

# ── 건축물 지표 계산 ──────────────────────────────────────────────────
print("\n[3] 건축물 지표 계산...")

total_gfa = gdf_out["tot_fl_ar"].sum()
use_gfa = gdf_out.groupby("use_class")["tot_fl_ar"].sum()
use_ratio = (use_gfa / total_gfa * 100).round(2).to_dict() if total_gfa > 0 else {}

p_arr = use_gfa / total_gfa if total_gfa > 0 else pd.Series(dtype=float)
p_arr = p_arr[p_arr > 0]
n = len(p_arr)
lum = float((-p_arr * np.log(p_arr)).sum() / np.log(n)) if n > 1 else 0.0

avg_far = gdf_out["fl_ar_ratio"].mean()

metrics_cheongna = {
    "label": "청라국제업무지구(수정)",
    "building_count": int(len(gdf_out)),
    "total_gfa_m2": float(round(total_gfa, 2)),
    "use_ratio_pct": {k: float(v) for k, v in use_ratio.items()},
    "lum_entropy": round(lum, 4),
    "avg_far_pct": round(float(avg_far) if not np.isnan(avg_far) else 0, 2),
}

print(f"  건축물 수: {metrics_cheongna['building_count']}동")
print(f"  총 연면적: {total_gfa/1e6:.4f} 백만m2")
print(f"  용도 비율: {use_ratio}")
print(f"  LUM 엔트로피: {lum:.4f}")
print(f"  평균 용적률: {avg_far:.1f}%")

# ── zone_info.json 갱신 ───────────────────────────────────────────────
print("\n[4] zone_info.json 갱신...")
zi_path = os.path.join(PROCESSED, "zone_info.json")
with open(zi_path, encoding="utf-8") as f:
    zone_info = json.load(f)

zone_info["cheongna"] = {
    "name": "청라국제업무지구",
    "area_km2": round(area_km2, 4),
    "building_count": len(gdf_out),
    "source": "공간정보 오픈플랫폼(PROM) 구역계 설정 (2026-06)",
    "definition": "인천경제자유구역 청라지구 중 청라 호수공원 중심 좌측 업무·상업 지구",
    "note": "청라동 전체 행정경계 대신 PROM 구역계 도구로 업무지구 핵심 영역 직접 설정"
}

with open(zi_path, "w", encoding="utf-8") as f:
    json.dump(zone_info, f, ensure_ascii=False, indent=2)
print(f"  판교: {zone_info['pangyo']['area_km2']} km²")
print(f"  청라(수정): {zone_info['cheongna']['area_km2']} km²")

# ── building_metrics.json 갱신 ────────────────────────────────────────
print("\n[5] building_metrics.json 갱신...")
bm_path = os.path.join(PROCESSED, "building_metrics.json")
if os.path.exists(bm_path):
    with open(bm_path, encoding="utf-8") as f:
        bm = json.load(f)
else:
    bm = {}

bm["cheongna"] = metrics_cheongna

with open(bm_path, "w", encoding="utf-8") as f:
    json.dump(bm, f, ensure_ascii=False, indent=2)
print("  building_metrics.json 갱신 완료")

# ── docs/data 동기화 ──────────────────────────────────────────────────
print("\n[6] docs/data 동기화...")
for fname in ["cheongna_zone.geojson", "cheongna_buildings.geojson"]:
    src = os.path.join(PROCESSED, fname)
    dst = os.path.join(DOCS_DATA, fname)
    shutil.copy(src, dst)
    print(f"  복사: {fname}")

print("\n=== 완료 ===")
print(f"청라 zone 면적: {area_km2:.4f} km²")
print(f"청라 건축물: {len(gdf_out)}동")
print("다음 단계: 05_osm_roads.py, 06_population.py, 04_generate_stats.py 재실행 필요")
