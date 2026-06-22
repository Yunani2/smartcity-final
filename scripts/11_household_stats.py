"""Script 11: 집계구별 가구통계 → 구역 내 집계구 합산 → stats.json 업데이트"""
import json, zipfile, io, os, tempfile, shutil
import geopandas as gpd
import pandas as pd

BASE = r"C:\Users\nanna\OneDrive\바탕 화면\2026 스마트시티학과\스시론\기말 과제"
DATA = os.path.join(BASE, "project", "docs", "data")
STATS = os.path.join(DATA, "stats.json")

HH_BUNDANG = os.path.join(BASE, "집계구별 가구통계_경기도 분당구.zip")
HH_SEOGU   = os.path.join(BASE, "집계구별 가구통계_인천 서구.zip")
BND_BUNDANG = os.path.join(BASE, "집계구 경계_성남시 분당구.zip")
BND_SEOGU   = os.path.join(BASE, "집계구 경계_인천 서구.zip")

def load_census_boundary(zip_path):
    tmpdir = tempfile.mkdtemp()
    try:
        with zipfile.ZipFile(zip_path) as z:
            z.extractall(tmpdir)
        shp = next(f for f in os.listdir(tmpdir) if f.endswith(".shp"))
        gdf = gpd.read_file(os.path.join(tmpdir, shp), encoding="euc-kr")
        if gdf.crs is None: gdf = gdf.set_crs(5179)
        elif gdf.crs.to_epsg() != 5179: gdf = gdf.to_crs(5179)
        return gdf
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

def load_zone(geojson_path):
    gdf = gpd.read_file(geojson_path)
    if gdf.crs is None or gdf.crs.to_epsg() != 4326: gdf = gdf.set_crs(4326)
    return gdf.to_crs(5179).union_all()

def filter_oa(census_gdf, zone_poly):
    rp = census_gdf.geometry.representative_point()
    return census_gdf[rp.within(zone_poly)]

def read_zip_csv(zip_path, keyword, no_header=True):
    with zipfile.ZipFile(zip_path) as z:
        names = z.namelist()
        entry = next((n for n in names if keyword in n or keyword.lower() in n.lower()), names[0])
        with z.open(entry) as f:
            raw = f.read()
    print(f"  CSV: {entry}")
    hdr = None if no_header else "infer"
    for enc in ("euc-kr", "cp949", "utf-8-sig", "utf-8"):
        try:
            df = pd.read_csv(io.BytesIO(raw), encoding=enc, header=hdr)
            return df
        except Exception:
            continue
    raise ValueError(f"디코딩 실패: {entry}")

def detect_oa_col(df, sample_oa):
    oa_len = len(str(sample_oa[0])) if sample_oa else 14
    for c in df.columns:
        cl = str(c).lower()
        if "oa" in cl or "집계구" in cl:
            return c
    for c in df.columns:
        vals = df[c].astype(str).str.strip().head(5).tolist()
        if all(len(v) == oa_len for v in vals if v not in ("nan", "")):
            return c
    return df.columns[1] if len(df.columns) >= 2 else df.columns[0]

def get_total_households(hh_zip, zone_oa_codes):
    """가구총괄 CSV에서 구역 내 집계구 총가구수 합산"""
    try:
        df = read_zip_csv(hh_zip, "가구총괄", no_header=True)
    except Exception:
        df = read_zip_csv(hh_zip, "가구", no_header=True)
    df.columns = [f"col{i}" for i in range(len(df.columns))]
    print(f"  가구 CSV 컬럼: {list(df.columns)}, 행수: {len(df)}")

    oa_col = detect_oa_col(df, list(zone_oa_codes)[:3])
    df[oa_col] = df[oa_col].astype(str).str.strip()
    zone_codes = set(str(c).strip() for c in zone_oa_codes)
    zone_df = df[df[oa_col].isin(zone_codes)].copy()
    print(f"  가구 CSV 매칭: 전체 {len(df)}행 → 구역 내 {len(zone_df)}행")

    if zone_df.empty:
        print(f"  [WARN] 매칭 없음. OA 샘플: {list(df[oa_col].head(3))}")
        return None, None

    cols = list(zone_df.columns)
    # long format: col2=항목코드, col3=값
    # 가구총괄의 항목코드: 가구총계 = to_hh_001 또는 첫 번째 항목
    ind_col = cols[2]
    val_col = cols[3]
    print(f"  항목 유니크: {list(zone_df[ind_col].unique())[:8]}")

    # 총가구 코드 탐색
    tot_code = None
    for code in zone_df[ind_col].unique():
        code_s = str(code).lower().strip()
        if code_s in ("to_hh_001", "tot_hh", "가구총계") or "to_hh_001" in code_s or "총가구" in code_s:
            tot_code = code
            break
    if tot_code is None:
        tot_code = zone_df[ind_col].iloc[0]
        print(f"  [INFO] 첫 항목 사용: '{tot_code}'")

    tot_rows = zone_df[zone_df[ind_col] == tot_code]
    total_hh = int(pd.to_numeric(tot_rows[val_col], errors="coerce").fillna(0).sum())
    print(f"  총가구수 (항목={tot_code}) → {total_hh:,}가구")
    return total_hh, tot_code

def process(zone_name, zone_geojson, bnd_zip, hh_zip):
    print(f"\n{'='*50}")
    print(f"[{zone_name}] 처리")
    zone_poly = load_zone(zone_geojson)
    census_gdf = load_census_boundary(bnd_zip)
    zone_census = filter_oa(census_gdf, zone_poly)
    print(f"  집계구 필터: {len(census_gdf)} → {len(zone_census)}개")
    if zone_census.empty:
        return None

    oa_col_shp = next((c for c in zone_census.columns if "tot_oa" in c.lower()), zone_census.columns[0])
    zone_oa = zone_census[oa_col_shp].astype(str).str.strip().tolist()
    print(f"  OA 샘플: {zone_oa[:3]}")

    total_hh, code = get_total_households(hh_zip, zone_oa)
    return {"zone_households": total_hh, "zone_households_note": f"집계구 {len(zone_census)}개 합산 (2024년)"}

def main():
    with open(STATS, encoding="utf-8") as f:
        stats = json.load(f)

    p_res = process("판교", os.path.join(DATA, "pangyo_zone.geojson"),  BND_BUNDANG, HH_BUNDANG)
    c_res = process("청라", os.path.join(DATA, "cheongna_zone.geojson"), BND_SEOGU,   HH_SEOGU)

    if p_res:
        stats["sociodemographics"]["pangyo"].update(p_res)
    if c_res:
        stats["sociodemographics"]["cheongna"].update(c_res)

    with open(STATS, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    print(f"\nstats.json 업데이트 완료")
    if p_res: print(f"  판교 가구수: {p_res.get('zone_households'):,}")
    if c_res: print(f"  청라 가구수: {c_res.get('zone_households'):,}")

if __name__ == "__main__":
    main()
