"""
Step 1-B: 건축물대장 전처리
- 판교(삼평동) + 청라(청라동) 건축물대장 CSV 로드
- 주용도 분류, 연면적·용적률 정리
- 연속지적도(PNU)와 매칭하여 좌표 획득
- zone boundary 내 건축물 필터링
- GeoJSON 저장

공간 단위: 건축물(동)
시간 범위: 건축HUB 수집 기준 (파일 생성일 기준, 2024~2025년)
"""

import os
import zipfile
import json
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point

BASE  = r"C:\Users\nanna\OneDrive\바탕 화면\2026 스마트시티학과\스시론\기말 과제"
RAW   = r"C:\Users\nanna\OneDrive\바탕 화면\2026 스마트시티학과\스시론\project\data\raw"
OUT   = r"C:\Users\nanna\OneDrive\바탕 화면\2026 스마트시티학과\스시론\project\data\processed"

# ── 주용도 코드 분류 매핑 ────────────────────────────────────────────
# 건축물대장 주용도코드명 → 분석 카테고리
USE_CATEGORY = {
    # 업무시설
    "업무시설": "업무시설",
    # 교육연구시설
    "교육연구시설": "교육연구시설",
    # 근린생활시설
    "제1종근린생활시설": "근린생활시설",
    "제2종근린생활시설": "근린생활시설",
    # 주거
    "단독주택": "주거",
    "공동주택": "주거",
    # 판매
    "판매시설": "판매시설",
    # 운수
    "운수시설": "운수시설",
    # 공장
    "공장": "공장·창고",
    "창고시설": "공장·창고",
    # 기타
    "자동차관련시설": "기타",
    "운동시설": "기타",
    "문화및집회시설": "기타",
    "종교시설": "기타",
    "의료시설": "기타",
    "노유자시설": "기타",
    "수련시설": "기타",
    "숙박시설": "기타",
    "위락시설": "기타",
    "관광휴게시설": "기타",
    "분뇨.쓰레기처리시설": "기타",
    "동물및식물관련시설": "기타",
    "묘지관련시설": "기타",
    "방송통신시설": "기타",
    "발전시설": "기타",
}
CATEGORY_COLORS = {
    "업무시설":     "#2166ac",
    "교육연구시설": "#4dac26",
    "근린생활시설": "#f4a582",
    "주거":         "#d6604d",
    "판매시설":     "#fdae61",
    "운수시설":     "#bababa",
    "공장·창고":    "#762a83",
    "기타":         "#cccccc",
}

def classify_use(use_name: str) -> str:
    if pd.isna(use_name):
        return "기타"
    name = str(use_name).strip()
    for key, cat in USE_CATEGORY.items():
        if key in name:
            return cat
    return "기타"

# ── 연속지적도 로드 (좌표 매칭용) ────────────────────────────────────
print("연속지적도 로드 중...")
gdf_g = gpd.read_file(
    os.path.join(RAW, "cadastral_gyeonggi", "LSMD_CONT_LDREG_41135_202606.shp"),
    engine="pyogrio"
)
gdf_i = gpd.read_file(
    os.path.join(RAW, "cadastral_incheon", "LSMD_CONT_LDREG_28260_202606.shp"),
    engine="pyogrio"
)

# 필지 centroid (EPSG:5179) → WGS84 좌표로 변환해서 dict 생성
def make_pnu_centroid(gdf):
    gdf_5179 = gdf.to_crs("EPSG:5179")
    cents = gdf_5179.geometry.centroid
    gdf_4326 = gpd.GeoSeries(cents, crs="EPSG:5179").to_crs("EPSG:4326")
    result = {}
    for pnu, pt in zip(gdf["PNU"], gdf_4326):
        result[pnu] = (pt.y, pt.x)   # (lat, lng)
    return result

print("경기 필지 centroid 계산 중...")
pnu_coord_g = make_pnu_centroid(gdf_g)
print("인천 필지 centroid 계산 중...")
pnu_coord_i = make_pnu_centroid(gdf_i)

# ── 건축물대장 CSV 로드 및 전처리 함수 ──────────────────────────────
def load_building_csv(csv_paths: list, pnu_coord: dict) -> pd.DataFrame:
    frames = []
    for path in csv_paths:
        df = pd.read_csv(path, encoding="utf-8-sig", low_memory=False)
        frames.append(df)
    df = pd.concat(frames, ignore_index=True)

    # 주건축물만
    df = df[df["주부속구분코드명"] == "주건축물"].copy()

    # 숫자형 변환
    for col in ["대지면적(㎡)", "건축면적(㎡)", "연면적(㎡)", "용적률산정연면적(㎡)", "용적률(%)"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # 용적률 재계산 (결측치 보완)
    mask = df["용적률(%)"].isna() & df["대지면적(㎡)"].gt(0)
    df.loc[mask, "용적률(%)"] = (
        df.loc[mask, "용적률산정연면적(㎡)"] / df.loc[mask, "대지면적(㎡)"] * 100
    )

    # 주용도 분류
    df["용도분류"] = df["주용도코드명"].apply(classify_use)

    # PNU 생성: 법정동코드(10) + 산구분(1) + 본번(4) + 부번(4) = 19자리
    # 건축물대장 대지구분코드: 0=대지(일반) → PNU산구분"1", 1=산 → PNU산구분"2"
    df["시군구코드"] = df["시군구코드"].astype(str).str.zfill(5)
    df["법정동코드"] = df["법정동코드"].astype(str).str.zfill(5)
    df["번"] = pd.to_numeric(df["번"], errors="coerce").fillna(0).astype(int).astype(str).str.zfill(4)
    df["지"] = pd.to_numeric(df["지"], errors="coerce").fillna(0).astype(int).astype(str).str.zfill(4)
    df["산구분"] = df["대지구분코드"].astype(str).str.strip().map({"0": "1", "1": "2"}).fillna("1")
    df["PNU"] = df["시군구코드"] + df["법정동코드"] + df["산구분"] + df["번"] + df["지"]

    # 좌표 매칭
    df["lat"] = df["PNU"].map(lambda p: pnu_coord.get(p, (None, None))[0])
    df["lng"] = df["PNU"].map(lambda p: pnu_coord.get(p, (None, None))[1])

    matched = df["lat"].notna().sum()
    print(f"  전체 {len(df):,}동 중 좌표 매칭: {matched:,}동 ({matched/len(df)*100:.1f}%)")
    return df

# ── 판교 건축물 ───────────────────────────────────────────────────────
print("\n판교 건축물대장 로드 중...")
pangyo_csv = [
    os.path.join(BASE, "판교_삼평동_건축물대장.csv"),
    os.path.join(BASE, "판교_백현동_건축물대장.csv"),
    os.path.join(BASE, "판교_운중동_건축물대장.csv"),
    os.path.join(BASE, "판교_판교동_건축물대장.csv"),
]
df_p = load_building_csv(pangyo_csv, pnu_coord_g)

# 삼평동만 (판교테크노밸리 핵심) — 법정동코드 10900
df_p_samyeong = df_p[df_p["법정동코드"] == "10900"].copy()
print(f"삼평동 건축물: {len(df_p_samyeong):,}동 (좌표 있는 것: {df_p_samyeong['lat'].notna().sum():,})")

# ── 청라 건축물 ───────────────────────────────────────────────────────
print("\n청라 건축물대장 로드 중...")
cheongna_csv = [os.path.join(BASE, "청라_청라동_건축물대장.csv")]
df_c = load_building_csv(cheongna_csv, pnu_coord_i)
print(f"청라동 건축물: {len(df_c):,}동")

# ── zone polygon 로드 → 경계 내 건축물만 필터링 ──────────────────────
zone_p = gpd.read_file(os.path.join(OUT, "pangyo_zone.geojson"))
zone_c = gpd.read_file(os.path.join(OUT, "cheongna_zone.geojson"))

def filter_by_zone(df: pd.DataFrame, zone: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    sub = df[df["lat"].notna()].copy()
    gdf = gpd.GeoDataFrame(
        sub,
        geometry=[Point(row.lng, row.lat) for _, row in sub.iterrows()],
        crs="EPSG:4326"
    )
    return gpd.sjoin(gdf, zone[["geometry"]], how="inner", predicate="within").drop(columns=["index_right"])

print("\nzone 내 건축물 필터링...")
gdf_p = filter_by_zone(df_p_samyeong, zone_p)
gdf_c = filter_by_zone(df_c, zone_c)
print(f"판교 zone 내 건축물: {len(gdf_p):,}동")
print(f"청라 zone 내 건축물: {len(gdf_c):,}동")

# ── 지표 계산 ─────────────────────────────────────────────────────────
def calc_metrics(gdf: pd.DataFrame, label: str) -> dict:
    total_gfa = gdf["연면적(㎡)"].sum()
    use_gfa = gdf.groupby("용도분류")["연면적(㎡)"].sum()
    use_ratio = (use_gfa / total_gfa * 100).round(2).to_dict()

    # LUM 엔트로피 (Land Use Mix)
    import numpy as np
    p = use_gfa / total_gfa
    p = p[p > 0]
    n = len(p)
    if n > 1:
        lum = (-p * np.log(p)).sum() / np.log(n)
    else:
        lum = 0.0

    avg_far = gdf["용적률(%)"].mean()
    avg_bcr = gdf["건폐율(%)"].mean() if "건폐율(%)" in gdf.columns else None

    total_buildings = len(gdf)
    total_gfa_office = gdf[gdf["용도분류"] == "업무시설"]["연면적(㎡)"].sum()
    total_gfa_research = gdf[gdf["용도분류"] == "교육연구시설"]["연면적(㎡)"].sum()

    print(f"\n[{label}] 지표 요약")
    print(f"  건축물 수: {total_buildings:,}동")
    print(f"  총 연면적: {total_gfa/1e6:.4f} 백만㎡")
    print(f"  업무시설 연면적 비율: {use_ratio.get('업무시설', 0):.1f}%")
    print(f"  교육연구시설 연면적 비율: {use_ratio.get('교육연구시설', 0):.1f}%")
    print(f"  LUM 엔트로피: {lum:.4f}")
    print(f"  평균 용적률: {avg_far:.1f}%")
    print(f"  용도별 연면적 비율: {use_ratio}")

    return {
        "label": label,
        "building_count": int(total_buildings),
        "total_gfa_m2": float(round(total_gfa, 2)),
        "use_ratio_pct": {k: float(v) for k, v in use_ratio.items()},
        "lum_entropy": round(float(lum), 4),
        "avg_far_pct": round(float(avg_far), 2),
    }

metrics_p = calc_metrics(gdf_p, "판교테크노밸리(삼평동)")
metrics_c = calc_metrics(gdf_c, "청라국제업무지구(청라동)")

# ── GeoJSON 저장 ──────────────────────────────────────────────────────
keep_cols = [
    "PNU", "건물명", "주용도코드명", "용도분류",
    "대지면적(㎡)", "건축면적(㎡)", "연면적(㎡)", "용적률(%)",
    "지상층수", "지하층수", "사용승인일",
    "lat", "lng", "geometry"
]

def safe_keep(gdf, cols):
    return gdf[[c for c in cols if c in gdf.columns]]

gdf_p_out = safe_keep(gdf_p, keep_cols)
gdf_c_out = safe_keep(gdf_c, keep_cols)

gdf_p_out.to_file(os.path.join(OUT, "pangyo_buildings.geojson"), driver="GeoJSON")
gdf_c_out.to_file(os.path.join(OUT, "cheongna_buildings.geojson"), driver="GeoJSON")

with open(os.path.join(OUT, "building_metrics.json"), "w", encoding="utf-8") as f:
    json.dump({"pangyo": metrics_p, "cheongna": metrics_c,
               "category_colors": CATEGORY_COLORS}, f, ensure_ascii=False, indent=2)

print("\n=== 저장 완료 ===")
print(f"pangyo_buildings.geojson, cheongna_buildings.geojson, building_metrics.json → {OUT}")
