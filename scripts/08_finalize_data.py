# -*- coding: utf-8 -*-
"""
08_finalize_data.py  ─ 최종 stats.json 보완
  Part A: 청라 buildings → polygon geometry (centroid 제거)
  Part B: 역세권 면적 비율 (subway nodes 500m/1km 버퍼 × zone 교차)
  Part C: 이소크론 경제활동인구 추정 (인구 × 0.52) → iso30/60_est_workers
  Part D: 총 사업체수 (to_fa_010) 및 업종별 구성 (cp_bnu_001-005)
  Part E: stats.json 갱신
"""

import os, json, shutil, zipfile
import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.ops import unary_union

BASE      = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROM_DIR  = os.path.join(BASE, "..", "prom_cheongna_new")
RAW_BASE  = r"C:\Users\nanna\OneDrive\바탕 화면\2026 스마트시티학과\스시론\기말 과제"
PROCESSED = os.path.join(BASE, "data", "processed")
DOCS_DATA = os.path.join(BASE, "docs", "data")
SUBWAY_ZIP = os.path.join(RAW_BASE, "subway_network.zip")

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
}

def classify_use(name):
    if pd.isna(name): return "기타"
    name = str(name).strip()
    for k, v in USE_CATEGORY.items():
        if k in name: return v
    return "기타"

# ── Part A: 청라 buildings → 폴리곤 geometry ──────────────────────────
print("=== Part A: 청라 buildings 폴리곤으로 재저장 ===")
all_shp = []
for root, dirs, files in os.walk(PROM_DIR):
    for f in files:
        if f.endswith(".shp"):
            all_shp.append(os.path.join(root, f))

bldg_shps = [p for p in all_shp if os.path.basename(os.path.dirname(p)).startswith("03_")]
bldg_shp  = next(p for p in bldg_shps if gpd.read_file(p, rows=1).columns.tolist().count("mn_use_nm") > 0)

gdf_bldg  = gpd.read_file(bldg_shp)
gdf_bldg["use_class"] = gdf_bldg["mn_use_nm"].apply(classify_use)

# 폴리곤 그대로 WGS84 변환 (centroid 하지 않음)
gdf_bldg_wgs = gdf_bldg.to_crs("EPSG:4326")

# zone으로 필터링
zone_wgs = gpd.read_file(os.path.join(PROCESSED, "cheongna_zone.geojson"))
zone_geom = zone_wgs.geometry.unary_union
# representative_point로 필터 (polygon → zone 내 포함 여부)
mask = gdf_bldg_wgs.geometry.representative_point().within(zone_geom)
gdf_in = gdf_bldg_wgs[mask].copy()
print(f"  zone 내 건축물 (폴리곤): {len(gdf_in)}동")

keep = ["pnu", "bd_nm", "mn_use_nm", "use_class",
        "land_ar", "tot_fl_ar", "fl_ar_ratio", "gr_fl_num", "use_per_dt", "geometry"]
gdf_out = gdf_in[[c for c in keep if c in gdf_in.columns]]
out_bldg = os.path.join(PROCESSED, "cheongna_buildings.geojson")
gdf_out.to_file(out_bldg, driver="GeoJSON")
shutil.copy(out_bldg, os.path.join(DOCS_DATA, "cheongna_buildings.geojson"))
print(f"  저장 완료: {len(gdf_out)}동 (Polygon geometry)")

# 지표 재계산
total_gfa = gdf_out["tot_fl_ar"].sum()
use_gfa   = gdf_out.groupby("use_class")["tot_fl_ar"].sum()
use_ratio = (use_gfa / total_gfa * 100).round(2).to_dict() if total_gfa > 0 else {}
p_arr = (use_gfa / total_gfa).dropna()
p_arr = p_arr[p_arr > 0]
n = len(p_arr)
lum = float((-p_arr * np.log(p_arr)).sum() / np.log(n)) if n > 1 else 0.0
avg_far = float(gdf_out["fl_ar_ratio"].mean())
cheongna_metrics = {
    "label": "청라국제업무지구",
    "building_count": int(len(gdf_out)),
    "total_gfa_m2":   float(round(total_gfa, 2)),
    "use_ratio_pct":  {k: float(v) for k, v in use_ratio.items()},
    "lum_entropy":    round(lum, 4),
    "avg_far_pct":    round(avg_far if not np.isnan(avg_far) else 0, 2),
}
print(f"  건축물 수: {cheongna_metrics['building_count']}  총 연면적: {total_gfa/1e6:.4f}백만m2")

# ── Part B: 역세권 면적 비율 (subway nodes 기반) ──────────────────────
print("\n=== Part B: 역세권 면적 비율 ===")
with zipfile.ZipFile(SUBWAY_ZIP) as zf:
    with zf.open("network/nodes.tsv") as f:
        nodes = pd.read_csv(f, sep="\t")

# 운영 중인 역 (begin <= 2026-06, effective_begin 없음 포함)
nodes["begin"] = pd.to_datetime(nodes["begin"], errors="coerce")
nodes_active = nodes[nodes["begin"] <= pd.Timestamp("2026-06-30")].copy()
print(f"  운영 역 수: {len(nodes_active)}")

# GeoDataFrame 변환 (WGS84)
gdf_nodes = gpd.GeoDataFrame(
    nodes_active, geometry=gpd.points_from_xy(nodes_active.lng, nodes_active.lat), crs="EPSG:4326"
)

def calc_station_area_ratio(zone_path, label):
    zone = gpd.read_file(zone_path)
    zone_5179 = zone.to_crs("EPSG:5179")
    zone_area = zone_5179.geometry.unary_union.area

    nodes_5179 = gdf_nodes.to_crs("EPSG:5179")
    # zone bbox 내 역만 사용 (속도)
    zone_bbox = zone_5179.total_bounds
    margin = 1500   # 1.5km margin
    near = nodes_5179[
        (nodes_5179.geometry.x >= zone_bbox[0] - margin) &
        (nodes_5179.geometry.x <= zone_bbox[2] + margin) &
        (nodes_5179.geometry.y >= zone_bbox[1] - margin) &
        (nodes_5179.geometry.y <= zone_bbox[3] + margin)
    ]
    print(f"  [{label}] zone 인근 역 수: {len(near)}")
    if len(near) == 0:
        return {"500m": 0, "1000m": 0}

    zone_geom = zone_5179.geometry.unary_union
    for dist in [500, 1000]:
        buf = near.geometry.buffer(dist).unary_union
        inter = zone_geom.intersection(buf)
        ratio = round(inter.area / zone_area * 100, 1)
        print(f"    {dist}m 역세권: {ratio:.1f}%")

    r500 = zone_geom.intersection(near.geometry.buffer(500).unary_union).area / zone_area
    r1000 = zone_geom.intersection(near.geometry.buffer(1000).unary_union).area / zone_area
    return {"500m": round(r500 * 100, 1), "1000m": round(r1000 * 100, 1)}

ratio_p = calc_station_area_ratio(os.path.join(DOCS_DATA, "pangyo_zone.geojson"), "판교")
ratio_c = calc_station_area_ratio(os.path.join(DOCS_DATA, "cheongna_zone.geojson"), "청라")
print(f"  판교 역세권 비율: {ratio_p}")
print(f"  청라 역세권 비율: {ratio_c}")

# ── Part C: 이소크론 경제활동인구(종사자) 추정 ─────────────────────────
# 수도권 취업자/총인구 ≈ 0.52 (2023년 통계청)
EMPLOY_RATE = 0.52
print("\n=== Part C: 이소크론 경제활동인구 추정 ===")
stats_path = os.path.join(DOCS_DATA, "stats.json")
with open(stats_path, encoding="utf-8") as f:
    stats = json.load(f)

sd = stats.get("sociodemographics", {})
def est_workers(pop):
    return int(pop * EMPLOY_RATE) if pop else None

for zone_key in ["pangyo", "cheongna"]:
    if zone_key not in sd:
        continue
    z = sd[zone_key]
    z["iso30_est_workers"] = est_workers(z.get("iso30_est_pop"))
    z["iso60_est_workers"] = est_workers(z.get("iso60_est_pop"))
    z["employ_rate_note"]  = f"취업자/총인구={EMPLOY_RATE} (2023 통계청 수도권 기준)"

p30w = sd.get("pangyo", {}).get("iso30_est_workers")
c30w = sd.get("cheongna", {}).get("iso30_est_workers")
if p30w and c30w:
    print(f"  판교 30분 경제활동인구 추정: {p30w:,}명")
    print(f"  청라 30분 경제활동인구 추정: {c30w:,}명")
    print(f"  비율: {p30w/c30w:.2f}배")

# ── Part D: 총 사업체수 & 업종별 사업체수 ─────────────────────────────
print("\n=== Part D: 사업체수·업종 구성 ===")

BIZ_CATEGORY = {
    "cp_bnu_001": "제조업",
    "cp_bnu_002": "건설업",
    "cp_bnu_003": "도소매업",
    "cp_bnu_004": "숙박·음식점업",
    "cp_bnu_005": "기타서비스업",
}
WRKR_CATEGORY = {
    "cp_bem_001": "제조업",
    "cp_bem_002": "건설업",
    "cp_bem_003": "도소매업",
    "cp_bem_004": "숙박·음식점업",
    "cp_bem_005": "기타서비스업",
}

def load_biz_stats(zip_path, code_prefix):
    results = {}
    with zipfile.ZipFile(zip_path) as zf:
        fnames = zf.namelist()
        # 총 사업체수 (to_fa_010) — 파일 [2]
        with zf.open(fnames[2]) as f:
            df = pd.read_csv(f, encoding="utf-8-sig", header=None, names=["year","code","ind","val"])
            df = df[df["code"].astype(str).str.startswith(code_prefix)]
            results["total_businesses"] = int(df[df["ind"]=="to_fa_010"]["val"].sum())

        # 업종별 사업체수 (cp_bnu_001-005) — 파일 [0]
        with zf.open(fnames[0]) as f:
            df = pd.read_csv(f, encoding="utf-8-sig", header=None, names=["year","code","ind","val"])
            df = df[df["code"].astype(str).str.startswith(code_prefix)]
            biz_by_ind = df.groupby("ind")["val"].sum()
            total_cat = biz_by_ind.sum()
            results["biz_by_industry"] = {
                BIZ_CATEGORY[k]: round(float(v / total_cat * 100), 1) if total_cat > 0 else 0
                for k, v in biz_by_ind.items()
                if k in BIZ_CATEGORY
            }

        # 업종별 종사자수 (cp_bem_001-005) — 파일 [1]
        with zf.open(fnames[1]) as f:
            df = pd.read_csv(f, encoding="utf-8-sig", header=None, names=["year","code","ind","val"])
            df = df[df["code"].astype(str).str.startswith(code_prefix)]
            em_by_ind = df.groupby("ind")["val"].sum()
            total_em_cat = em_by_ind.sum()
            results["workers_by_industry"] = {
                WRKR_CATEGORY[k]: round(float(v / total_em_cat * 100), 1) if total_em_cat > 0 else 0
                for k, v in em_by_ind.items()
                if k in WRKR_CATEGORY
            }
    return results

biz_p = load_biz_stats(
    os.path.join(RAW_BASE, "집계구별 사업체 수_성남시 분당구.zip"), "31023")
biz_c = load_biz_stats(
    os.path.join(RAW_BASE, "집계구별 사업체 수_인천 서구.zip"), "23080")

print(f"  판교(분당구) 총 사업체수: {biz_p['total_businesses']:,}개")
print(f"  청라(인천서구) 총 사업체수: {biz_c['total_businesses']:,}개")
print(f"  판교 업종별 사업체 비율: {biz_p['biz_by_industry']}")
print(f"  청라 업종별 사업체 비율: {biz_c['biz_by_industry']}")

# ── Part E: stats.json 최종 갱신 ─────────────────────────────────────
print("\n=== Part E: stats.json 갱신 ===")

# 건축물 지표 갱신
stats["land_use_buildings"]["cheongna"] = cheongna_metrics

# 역세권 면적 비율
stats["station_area_ratio"] = {
    "pangyo":   ratio_p,
    "cheongna": ratio_c,
    "note": "역 500m/1km 버퍼 × zone 교차 면적 / zone 면적 (2026년 운영 역 기준)"
}

# 이소크론 경제활동인구 (sociodemographics 안에 이미 반영됨)
stats["sociodemographics"] = sd

# 사업체 통계
stats["sociodemographics"]["pangyo"]["total_businesses"]    = biz_p["total_businesses"]
stats["sociodemographics"]["pangyo"]["biz_by_industry"]     = biz_p["biz_by_industry"]
stats["sociodemographics"]["pangyo"]["workers_by_industry"] = biz_p["workers_by_industry"]
stats["sociodemographics"]["cheongna"]["total_businesses"]  = biz_c["total_businesses"]
stats["sociodemographics"]["cheongna"]["biz_by_industry"]   = biz_c["biz_by_industry"]
stats["sociodemographics"]["cheongna"]["workers_by_industry"] = biz_c["workers_by_industry"]

stats["meta"]["analysis_date"] = "2026-06-21"

with open(stats_path, "w", encoding="utf-8") as f:
    json.dump(stats, f, ensure_ascii=False, indent=2)
shutil.copy(stats_path, os.path.join(PROCESSED, "stats.json"))
print("stats.json 갱신 완료")

# ── 요약 출력 ──────────────────────────────────────────────────────────
print("\n=== 최종 지표 요약 ===")
p = stats["land_use_buildings"]["pangyo"]
c = stats["land_use_buildings"]["cheongna"]
sp = stats["sociodemographics"]["pangyo"]
sc = stats["sociodemographics"]["cheongna"]
print(f"{'':30s} {'판교':>15s} {'청라':>15s}")
print("-"*62)
print(f"{'건축물 수':30s} {p['building_count']:>15,} {c['building_count']:>15,}")
print(f"{'업무+교육연구 비율(%)':30s} {(p['use_ratio_pct'].get('업무시설',0)+p['use_ratio_pct'].get('교육연구시설',0)):>15.1f} {(c['use_ratio_pct'].get('업무시설',0)+c['use_ratio_pct'].get('교육연구시설',0)):>15.1f}")
print(f"{'LUM 엔트로피':30s} {p['lum_entropy']:>15.4f} {c['lum_entropy']:>15.4f}")
print(f"{'30분권 추정인구':30s} {sp.get('iso30_est_pop',0):>15,} {sc.get('iso30_est_pop',0):>15,}")
print(f"{'30분권 추정경제활동인구':30s} {sp.get('iso30_est_workers',0):>15,} {sc.get('iso30_est_workers',0):>15,}")
print(f"{'역세권비율 500m(%)':30s} {ratio_p['500m']:>15} {ratio_c['500m']:>15}")
print(f"{'총 사업체수':30s} {biz_p['total_businesses']:>15,} {biz_c['total_businesses']:>15,}")
print(f"{'시군구 종사자수':30s} {sp.get('sigungu_workers',0):>15,} {sc.get('sigungu_workers',0):>15,}")
