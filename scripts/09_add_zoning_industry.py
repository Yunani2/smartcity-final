"""
09_add_zoning_industry.py
목적:
  A) 용도지역 구성비 - 판교/청라 PROM 용도지역.shp → 구역 내 면적 비율
  B) 사업체 업종 재계산 - 10차 대분류 CP_BNU_001~021 올바른 매핑
  C) 구역-핵심역 직선 거리 - 역세권 면적비율 대체
  D) docs/data/pangyo_zoning.geojson, cheongna_zoning.geojson 저장
  E) stats.json 업데이트
"""
import json, zipfile, io, sys, warnings
import geopandas as gpd
import pandas as pd
from shapely.geometry import mapping
from shapely.ops import unary_union
import numpy as np

warnings.filterwarnings("ignore")
sys.stdout.reconfigure(encoding="utf-8")

# ── 경로 설정 ──────────────────────────────────────────────────────────────
BASE  = r"C:\Users\nanna\OneDrive\바탕 화면\2026 스마트시티학과\스시론\기말 과제"
PROJ  = BASE + r"\project"
DOCS  = PROJ + r"\docs\data"
STATS = DOCS + r"\stats.json"

ZIP_P = BASE + r"\prom_구역계 설정_판교테크노밸리.zip"
DIR_C = BASE + r"\prom_cheongna_new"
ZIP_BIZ_P = BASE + r"\집계구별 사업체 수_성남시 분당구.zip"
ZIP_BIZ_C = BASE + r"\집계구별 사업체 수_인천 서구.zip"

ZONE_P_GJ = DOCS + r"\pangyo_zone.geojson"
ZONE_C_GJ = DOCS + r"\cheongna_zone.geojson"

# ── SGIS 10차 대분류 코드 매핑 ─────────────────────────────────────────────
# cp_bnu_NNN 번호 = 한국표준산업분류 대분류 순서
BNU_MAP = {
    "cp_bnu_001": "농림어업",
    "cp_bnu_002": "광업",
    "cp_bnu_003": "제조업",
    "cp_bnu_004": "전기·가스",
    "cp_bnu_005": "수도·환경",
    "cp_bnu_006": "건설업",
    "cp_bnu_007": "도소매업",
    "cp_bnu_008": "운수·창고업",
    "cp_bnu_009": "숙박·음식점업",
    "cp_bnu_010": "정보통신업",
    "cp_bnu_011": "금융·보험업",
    "cp_bnu_012": "부동산업",
    "cp_bnu_013": "전문·과학·기술서비스업",
    "cp_bnu_014": "사업지원서비스업",
    "cp_bnu_015": "공공행정",
    "cp_bnu_016": "교육서비스업",
    "cp_bnu_017": "보건·사회복지",
    "cp_bnu_018": "예술·여가",
    "cp_bnu_019": "기타서비스업",
    "cp_bnu_020": "가구내고용",
    "cp_bnu_021": "국제기관",
}

# 대시보드에 표시할 주요 업종 (의미 있는 것만)
KEY_INDUSTRIES = [
    "제조업", "건설업", "도소매업", "숙박·음식점업",
    "정보통신업", "금융·보험업", "부동산업",
    "전문·과학·기술서비스업", "사업지원서비스업",
    "교육서비스업", "보건·사회복지",
]

# ── 용도지역 색상 매핑 ─────────────────────────────────────────────────────
ZONE_COLORS = {
    "중심상업지역":   "#d73027",
    "일반상업지역":   "#fc8d59",
    "유통상업지역":   "#fee08b",
    "근린상업지역":   "#fdae61",
    "준주거지역":     "#a6d96a",
    "제3종일반주거지역": "#74c476",
    "제2종일반주거지역": "#a1d99b",
    "제1종일반주거지역": "#c7e9c0",
    "제2종전용주거지역": "#d9f0a3",
    "제1종전용주거지역": "#e7f5bf",
    "준공업지역":     "#9e9ac8",
    "일반공업지역":   "#756bb1",
    "자연녹지지역":   "#41ab5d",
    "생산녹지지역":   "#238b45",
    "계획관리지역":   "#cccccc",
    "도시지역미지정": "#f0f0f0",
}

# ── 용도지역 대분류 그룹화 ────────────────────────────────────────────────
def zone_group(nm):
    if "상업" in nm:   return "상업지역"
    if "주거" in nm:   return "주거지역"
    if "공업" in nm:   return "공업지역"
    if "녹지" in nm:   return "녹지지역"
    if "준주거" in nm: return "준주거지역"
    return "기타"


# ── 헬퍼 ─────────────────────────────────────────────────────────────────
def load_zone(geojson_path):
    gdf = gpd.read_file(geojson_path)
    gdf = gdf.to_crs("EPSG:5174")
    return gdf.union_all(), gdf.to_crs("EPSG:4326").union_all()


def read_zoning_from_zip(zip_path, layer="05_도시계획/용도지역.shp"):
    zf = zipfile.ZipFile(zip_path)
    # 관련 파일(.shp/.dbf/.shx/.prj) 임시 메모리 추출 후 gpd 읽기
    import tempfile, os, shutil
    tmpdir = tempfile.mkdtemp()
    try:
        base = layer.rsplit("/", 1)[-1].replace(".shp", "")
        for ext in [".shp", ".dbf", ".shx", ".prj", ".cpg"]:
            inner = layer.replace(".shp", ext)
            if inner in zf.namelist():
                zf.extract(inner, tmpdir)
        shp_path = os.path.join(tmpdir, layer.replace("/", os.sep))
        gdf = gpd.read_file(shp_path, encoding="cp949")
    finally:
        shutil.rmtree(tmpdir)
    return gdf


def compute_zoning_ratio(zone_geom_5174, gdf_zoning):
    """zone_geom_5174: Shapely geometry in EPSG:5174"""
    gdf_zoning = gdf_zoning.to_crs("EPSG:5174")
    gdf_zoning = gdf_zoning[gdf_zoning.is_valid]
    clipped = gdf_zoning.copy()
    clipped["geometry"] = gdf_zoning.intersection(zone_geom_5174)
    clipped = clipped[~clipped.geometry.is_empty]
    clipped["area_m2"] = clipped.geometry.area
    total = clipped["area_m2"].sum()
    if total == 0:
        return {}, {}
    by_name = clipped.groupby("uzone_nm")["area_m2"].sum()
    ratio_pct = (by_name / total * 100).round(2).to_dict()
    by_group = clipped.groupby(clipped["uzone_nm"].map(zone_group))["area_m2"].sum()
    group_pct = (by_group / total * 100).round(2).to_dict()
    return ratio_pct, group_pct


def save_zoning_geojson(zone_geom_5174, gdf_zoning, out_path):
    """zone_geom_5174: Shapely in EPSG:5174 → clip → convert to WGS84 → save"""
    gdf = gdf_zoning.to_crs("EPSG:5174")
    gdf = gdf[gdf.is_valid].copy()
    gdf["geometry"] = gdf.intersection(zone_geom_5174)
    gdf = gdf[~gdf.geometry.is_empty & gdf.geometry.is_valid]
    gdf = gdf.to_crs("EPSG:4326")
    gdf["color"] = gdf["uzone_nm"].map(lambda x: ZONE_COLORS.get(x, "#cccccc"))
    feat_cols = ["uzone_nm", "uzone_cd", "color", "geometry"]
    feat_cols = [c for c in feat_cols if c in gdf.columns]
    gdf[feat_cols].to_file(out_path, driver="GeoJSON")
    print(f"  저장: {out_path} ({len(gdf)}개 폴리곤)")


# ── 사업체 업종 재계산 ──────────────────────────────────────────────────────
def read_biz_industry(zip_path):
    """10차 대분류 사업체수/종사자수 CSV → {업종: 비율%}"""
    zf = zipfile.ZipFile(zip_path)
    names = zf.namelist()

    # 총괄사업체수
    total_fn = [n for n in names if "총괄사업체" in n][0]
    df_total = pd.read_csv(io.BytesIO(zf.read(total_fn)), encoding="cp949", header=None)
    df_total.columns = ["year", "jijgu_cd", "indicator", "value"]
    total_biz = pd.to_numeric(df_total["value"], errors="coerce").sum()

    # 대분류 사업체수
    bnu_fn = [n for n in names if "대분류" in n and "사업체수" in n and "총괄" not in n][0]
    df_bnu = pd.read_csv(io.BytesIO(zf.read(bnu_fn)), encoding="cp949", header=None)
    df_bnu.columns = ["year", "jijgu_cd", "indicator", "value"]
    df_bnu["value"] = pd.to_numeric(df_bnu["value"], errors="coerce")
    by_ind = df_bnu.groupby("indicator")["value"].sum()

    # 대분류 종사자수
    bem_fn = [n for n in names if "대분류" in n and "종사자수" in n][0]
    df_bem = pd.read_csv(io.BytesIO(zf.read(bem_fn)), encoding="cp949", header=None)
    df_bem.columns = ["year", "jijgu_cd", "indicator", "value"]
    df_bem["value"] = pd.to_numeric(df_bem["value"], errors="coerce")
    by_wrk = df_bem.groupby("indicator")["value"].sum()

    # 이름 변환 (cp_bnu_010 → 정보통신업 등)
    bnu_named = {}
    for code, name in BNU_MAP.items():
        biz_code = code
        wrk_code = code.replace("bnu", "bem")
        cnt = by_ind.get(biz_code, 0)
        if pd.isna(cnt): cnt = 0
        bnu_named[name] = int(cnt)

    wrk_named = {}
    for code, name in BNU_MAP.items():
        wrk_code = code.replace("bnu", "bem")
        cnt = by_wrk.get(wrk_code, 0)
        if pd.isna(cnt): cnt = 0
        wrk_named[name] = int(cnt)

    total = int(total_biz)

    # 비율 계산 (주요 업종만)
    key_pct = {}
    for ind in KEY_INDUSTRIES:
        v = bnu_named.get(ind, 0)
        key_pct[ind] = round(v / total * 100, 2) if total > 0 else 0.0

    key_wrk_pct = {}
    total_wrk = sum(wrk_named.values())
    for ind in KEY_INDUSTRIES:
        v = wrk_named.get(ind, 0)
        key_wrk_pct[ind] = round(v / total_wrk * 100, 2) if total_wrk > 0 else 0.0

    return {
        "total_businesses": total,
        "biz_by_industry": key_pct,
        "biz_counts_by_industry": bnu_named,
        "workers_by_industry_pct": key_wrk_pct,
    }


# ── 구역-핵심역 직선 거리 ─────────────────────────────────────────────────
def zone_to_station_distance(zone_geom_wgs84, station_lat, station_lon):
    """구역 경계의 가장 가까운 점 → 역 좌표 직선 거리(m, EPSG:5179)"""
    from shapely.geometry import Point
    gdf_zone = gpd.GeoSeries([zone_geom_wgs84], crs="EPSG:4326").to_crs("EPSG:5179")
    gdf_sta  = gpd.GeoSeries([Point(station_lon, station_lat)], crs="EPSG:4326").to_crs("EPSG:5179")
    zone_5179 = gdf_zone.iloc[0]
    sta_5179  = gdf_sta.iloc[0]
    dist_to_boundary = zone_5179.exterior.distance(sta_5179)
    dist_centroid    = zone_5179.centroid.distance(sta_5179)
    return {
        "dist_boundary_m": round(dist_to_boundary),
        "dist_centroid_m": round(dist_centroid),
        "station_inside": zone_5179.contains(sta_5179),
    }


# ══════════════════════════════════════════════════════════════════════════════
# 메인
# ══════════════════════════════════════════════════════════════════════════════
print("=" * 60)
print("09_add_zoning_industry.py 시작")
print("=" * 60)

# 1. 구역 경계 로드
print("\n[1] 구역 경계 로드")
zone_p_5174, zone_p_wgs = load_zone(ZONE_P_GJ)
zone_c_5174, zone_c_wgs = load_zone(ZONE_C_GJ)
print(f"  판교 구역 면적(m²): {zone_p_5174.area:,.0f}")
print(f"  청라 구역 면적(m²): {zone_c_5174.area:,.0f}")

# 2. 판교 용도지역
print("\n[2] 판교 용도지역 처리")
gdf_zone_p = read_zoning_from_zip(ZIP_P, "05_도시계획/용도지역.shp")
print(f"  판교 용도지역 원본: {len(gdf_zone_p)}개 폴리곤")
uzone_ratio_p, uzone_group_p = compute_zoning_ratio(zone_p_5174, gdf_zone_p)
print("  구역 내 용도지역 비율:", uzone_ratio_p)
save_zoning_geojson(zone_p_5174, gdf_zone_p, DOCS + r"\pangyo_zoning.geojson")

# 3. 청라 용도지역
print("\n[3] 청라 용도지역 처리")
gdf_zone_c = gpd.read_file(DIR_C + r"\05_도시계획\용도지역.shp", encoding="cp949")
print(f"  청라 용도지역 원본: {len(gdf_zone_c)}개 폴리곤")
uzone_ratio_c, uzone_group_c = compute_zoning_ratio(zone_c_5174, gdf_zone_c)
print("  구역 내 용도지역 비율:", uzone_ratio_c)
save_zoning_geojson(zone_c_5174, gdf_zone_c, DOCS + r"\cheongna_zoning.geojson")

# 4. 사업체 업종 (10차 대분류 올바른 매핑)
print("\n[4] 사업체 업종 재계산 (10차 대분류)")
biz_p = read_biz_industry(ZIP_BIZ_P)
biz_c = read_biz_industry(ZIP_BIZ_C)
print(f"  분당구 총사업체: {biz_p['total_businesses']:,}")
print(f"  인천서구 총사업체: {biz_c['total_businesses']:,}")
print("  분당구 주요 업종:", {k:v for k,v in biz_p['biz_by_industry'].items() if v > 0})
print("  인천서구 주요 업종:", {k:v for k,v in biz_c['biz_by_industry'].items() if v > 0})

# 5. 구역-핵심역 거리
print("\n[5] 구역-핵심역 직선 거리")
# 판교역: 37.3946, 127.1112  /  청라국제도시역: 37.5330, 126.6231
dist_p = zone_to_station_distance(zone_p_wgs, 37.3946, 127.1112)
dist_c = zone_to_station_distance(zone_c_wgs, 37.5330, 126.6231)
print(f"  판교 구역→판교역: 경계까지 {dist_p['dist_boundary_m']}m, 중심에서 {dist_p['dist_centroid_m']}m, 역이 구역 안: {dist_p['station_inside']}")
print(f"  청라 구역→청라역: 경계까지 {dist_c['dist_boundary_m']}m, 중심에서 {dist_c['dist_centroid_m']}m, 역이 구역 안: {dist_c['station_inside']}")

# 6. stats.json 업데이트
print("\n[6] stats.json 업데이트")
with open(STATS, encoding="utf-8") as f:
    stats = json.load(f)

# 용도지역 구성비
stats["land_use_zoning"] = {
    "pangyo": {
        "label": "판교테크노밸리",
        "uzone_ratio_pct": uzone_ratio_p,
        "uzone_group_pct": uzone_group_p,
        "source": "PROM 용도지역 (2026년 6월 기준)",
    },
    "cheongna": {
        "label": "청라국제업무지구",
        "uzone_ratio_pct": uzone_ratio_c,
        "uzone_group_pct": uzone_group_c,
        "source": "PROM 용도지역 (2026년 6월 기준)",
    },
    "zone_colors": ZONE_COLORS,
}

# 사업체 업종 (올바른 매핑)
stats["sociodemographics"]["pangyo"]["total_businesses"]  = biz_p["total_businesses"]
stats["sociodemographics"]["pangyo"]["biz_by_industry"]   = biz_p["biz_by_industry"]
stats["sociodemographics"]["pangyo"]["biz_counts"]        = biz_p["biz_counts_by_industry"]
stats["sociodemographics"]["pangyo"]["workers_by_industry_pct"] = biz_p["workers_by_industry_pct"]

stats["sociodemographics"]["cheongna"]["total_businesses"] = biz_c["total_businesses"]
stats["sociodemographics"]["cheongna"]["biz_by_industry"]  = biz_c["biz_by_industry"]
stats["sociodemographics"]["cheongna"]["biz_counts"]       = biz_c["biz_counts_by_industry"]
stats["sociodemographics"]["cheongna"]["workers_by_industry_pct"] = biz_c["workers_by_industry_pct"]

# 구역-핵심역 거리
stats["station_distance"] = {
    "pangyo":  {**dist_p,  "station": "판교역(신분당선)"},
    "cheongna":{**dist_c,  "station": "청라국제도시역(공항철도)"},
    "note": "구역 경계(nearest)·중심점에서 핵심역까지 직선 거리(m), EPSG:5179 기준",
}

# 역세권 면적비율 note 업데이트
if "station_area_ratio" in stats:
    stats["station_area_ratio"]["note"] += " | 판교역은 구역 경계 외부에 위치 (경계까지 " + str(dist_p['dist_boundary_m']) + "m)"

with open(STATS, "w", encoding="utf-8") as f:
    json.dump(stats, f, ensure_ascii=False, indent=2)
print("  stats.json 저장 완료")

print("\n" + "=" * 60)
print("완료! 생성 파일:")
print("  docs/data/pangyo_zoning.geojson")
print("  docs/data/cheongna_zoning.geojson")
print("  docs/data/stats.json (업데이트)")
print("=" * 60)
