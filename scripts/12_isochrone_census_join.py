"""Script 12: 집계구 × 이소크론 공간조인 → 5분 단위 인구/종사자 산정 + 이소크론 GeoJSON 재생성"""
import json, zipfile, io, os, sys, tempfile, shutil
import geopandas as gpd
import pandas as pd
from shapely.ops import unary_union

sys.stdout.reconfigure(encoding="utf-8")

BASE  = r"C:\Users\nanna\OneDrive\바탕 화면\2026 스마트시티학과\스시론\기말 과제"
DATA  = os.path.join(BASE, "project", "docs", "data")
STATS = os.path.join(DATA, "stats.json")

BND_ZIPS = [
    os.path.join(BASE, "집계구 경계_서울.zip"),
    os.path.join(BASE, "집계구 경계_경기.zip"),
    os.path.join(BASE, "집계구 경계_인천.zip"),
]
POP_ZIPS = [
    os.path.join(BASE, "집계구 인구통계_서울.zip"),
    os.path.join(BASE, "집계구 인구통계_경기.zip"),
    os.path.join(BASE, "집계구 인구통계_인천.zip"),
]

TIMES        = list(range(5, 65, 5))   # 5, 10, ..., 60
BUFFER_M     = 500
WORKER_RATIO = 0.52                    # 취업자/총인구 (2023 통계청 수도권 기준)


# ──────────────────────────────────────────────
# 경계 로드
# ──────────────────────────────────────────────
def load_boundary_zip(zip_path):
    tmpdir = tempfile.mkdtemp()
    try:
        with zipfile.ZipFile(zip_path) as z:
            z.extractall(tmpdir)
        shp_files = []
        for root, _, files in os.walk(tmpdir):
            for fn in files:
                if fn.endswith(".shp"):
                    shp_files.append(os.path.join(root, fn))
        if not shp_files:
            raise FileNotFoundError(f"SHP 없음: {zip_path}")
        gdf = None
        for enc in ("euc-kr", "cp949", "utf-8"):
            try:
                gdf = gpd.read_file(shp_files[0], encoding=enc)
                break
            except Exception:
                continue
        if gdf is None:
            raise ValueError(f"SHP 읽기 실패: {shp_files[0]}")
        if gdf.crs is None:
            gdf = gdf.set_crs(5179)
        elif gdf.crs.to_epsg() != 5179:
            gdf = gdf.to_crs(5179)
        return gdf
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def detect_oa_col_bnd(gdf):
    for c in gdf.columns:
        cl = str(c).lower()
        if "tot_oa" in cl or "oa_cd" in cl or "집계구코드" in cl:
            return c
    for c in gdf.columns:
        if c == "geometry":
            continue
        vals = gdf[c].dropna().astype(str).str.strip().head(5).tolist()
        if all(v.isdigit() and len(v) >= 13 for v in vals if v):
            return c
    return gdf.columns[0]


# ──────────────────────────────────────────────
# 인구통계 로드
# ──────────────────────────────────────────────
TOT_POP_CODE = "to_in_001"   # SGIS 인구총괄(총인구) CSV의 총인구 항목코드


def load_pop_zip(zip_path):
    """인구총괄(총인구).csv → header=None DataFrame 반환"""
    with zipfile.ZipFile(zip_path) as z:
        names = z.namelist()
        csv_names = [n for n in names if n.lower().endswith(".csv")]
        if not csv_names:
            raise FileNotFoundError(f"CSV 없음: {zip_path}")
        # 총인구 파일 우선, 없으면 첫 번째
        entry = next((n for n in csv_names if "총인구" in n), csv_names[0])
        with z.open(entry) as f:
            raw = f.read()
    print(f"  CSV: {entry}")
    for enc in ("euc-kr", "cp949", "utf-8-sig", "utf-8"):
        try:
            df = pd.read_csv(io.BytesIO(raw), encoding=enc, header=None)
            return df, entry
        except Exception:
            continue
    raise ValueError(f"디코딩 실패: {zip_path}")


def extract_pop_dict(df, zip_path):
    """SGIS 인구총괄(총인구) long-format DataFrame → {oa_cd: 총인구} 딕셔너리
    형식: col[0]=연도, col[1]=집계구코드, col[2]=항목코드, col[3]=값
    to_in_001=총인구, to_in_007=남자, to_in_008=여자
    """
    # col[1] = OA 코드, col[2] = 항목코드, col[3] = 값
    oa_col, ind_col, val_col = 1, 2, 3

    # 총인구 코드 확인
    codes = df[ind_col].dropna().unique().tolist()
    tot_code = TOT_POP_CODE if TOT_POP_CODE in codes else codes[0]
    print(f"  항목코드 목록: {codes[:5]}, 총인구 코드: '{tot_code}'")

    sub = df[df[ind_col] == tot_code].copy()
    sub[oa_col] = sub[oa_col].astype(str).str.strip()
    sub[val_col] = pd.to_numeric(sub[val_col], errors="coerce").fillna(0)
    print(f"  OA컬럼: col[{oa_col}], 인구컬럼: col[{val_col}]")
    return sub.set_index(oa_col)[val_col].to_dict()


# ──────────────────────────────────────────────
# 이소크론 폴리곤 생성
# ──────────────────────────────────────────────
def build_iso_poly(sta_5179, time_min, buf=BUFFER_M):
    sub = sta_5179[sta_5179["time_min"] <= time_min]
    if sub.empty:
        return None
    return unary_union(sub.geometry.buffer(buf))


def save_isochrone_geojson(zone_name, sta_gdf, times, out_path, timeseries):
    sta_5179 = sta_gdf.to_crs(5179)
    ts_dict  = {r["time_min"]: r for r in timeseries}
    features = []
    for t in times:
        poly = build_iso_poly(sta_5179, t)
        if poly is None:
            continue
        r = ts_dict.get(t, {})
        feat_gdf = gpd.GeoDataFrame(
            [{"time_min": t,
              "station_count": r.get("station_count", 0),
              "population":    r.get("population", 0),
              "workers":       r.get("workers", 0)}],
            geometry=[poly], crs=5179
        ).to_crs(4326)
        features.append({
            "type": "Feature",
            "properties": {
                "time_min":      t,
                "station_count": r.get("station_count", 0),
                "population":    r.get("population", 0),
                "workers":       r.get("workers", 0),
            },
            "geometry": feat_gdf.geometry.iloc[0].__geo_interface__,
        })
    fc = {
        "type": "FeatureCollection",
        "name": f"{zone_name}_isochrone",
        "crs":  {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
        "features": features,
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(fc, f, ensure_ascii=False)
    print(f"  GeoJSON 저장: {out_path}  ({len(features)}개 피처)")


# ──────────────────────────────────────────────
# 메인
# ──────────────────────────────────────────────
def main():
    # ── 경계 로드 ──────────────────────────
    print("=" * 55)
    print("집계구 경계 로드")
    bnd_parts = []
    for zp in BND_ZIPS:
        print(f"  {os.path.basename(zp)}")
        gdf   = load_boundary_zip(zp)
        oa_c  = detect_oa_col_bnd(gdf)
        print(f"    OA컬럼: {oa_c}, 행: {len(gdf):,}")
        sub = gdf[[oa_c, "geometry"]].rename(columns={oa_c: "oa_cd"})
        sub["oa_cd"] = sub["oa_cd"].astype(str).str.strip()
        bnd_parts.append(sub)
    bnd_all = gpd.GeoDataFrame(pd.concat(bnd_parts, ignore_index=True), crs=5179)
    print(f"경계 합계: {len(bnd_all):,}개 집계구")

    # ── 인구통계 로드 ───────────────────────
    print("\n집계구 인구통계 로드")
    pop_dict = {}
    for zp in POP_ZIPS:
        print(f"  {os.path.basename(zp)}")
        df, entry = load_pop_zip(zp)
        print(f"    shape: {df.shape}, 컬럼: {list(df.columns[:6])}")
        d = extract_pop_dict(df, zp)
        print(f"    집계구 {len(d):,}개, 인구합계: {int(sum(d.values())):,}")
        pop_dict.update(d)
    print(f"전체 인구통계: {len(pop_dict):,}개 집계구")

    # 경계에 인구 병합
    bnd_all["population"] = bnd_all["oa_cd"].map(pop_dict).fillna(0).astype(int)
    total_mapped = bnd_all["population"].sum()
    print(f"경계+인구 합산: {total_mapped:,}명")

    # 대표점 (EPSG:5179)
    rep_pts = bnd_all.geometry.representative_point()

    # ── stats.json 로드 ─────────────────────
    with open(STATS, encoding="utf-8") as f:
        stats = json.load(f)

    # ── 각 구역 처리 ────────────────────────
    zones = [
        ("판교",  "pangyo",
         os.path.join(DATA, "pangyo_stations_reach.geojson"),
         os.path.join(DATA, "pangyo_isochrone.geojson")),
        ("청라", "cheongna",
         os.path.join(DATA, "cheongna_stations_reach.geojson"),
         os.path.join(DATA, "cheongna_isochrone.geojson")),
    ]

    for zone_label, stat_key, sta_file, iso_path in zones:
        print("\n" + "=" * 55)
        print(f"[{zone_label}] 이소크론 × 집계구 공간조인")

        sta_gdf  = gpd.read_file(sta_file)
        sta_5179 = sta_gdf.to_crs(5179)

        timeseries = []
        for t in TIMES:
            poly = build_iso_poly(sta_5179, t)
            if poly is None:
                timeseries.append(
                    {"time_min": t, "station_count": 0, "population": 0, "workers": 0})
                continue

            sta_cnt   = int((sta_gdf["time_min"] <= t).sum())
            within    = rep_pts.within(poly)
            total_pop = int(bnd_all.loc[within, "population"].sum())
            total_wk  = int(total_pop * WORKER_RATIO)

            timeseries.append({
                "time_min":      t,
                "station_count": sta_cnt,
                "population":    total_pop,
                "workers":       total_wk,
            })
            print(f"  {t:2d}분: 역 {sta_cnt:3d}개 / 인구 {total_pop:>9,} / 종사자 {total_wk:>8,}")

        # GeoJSON 저장 (12개 피처)
        save_isochrone_geojson(zone_label, sta_gdf, TIMES, iso_path, timeseries)

        # stats.json 업데이트
        ts_dict = {r["time_min"]: r for r in timeseries}
        sd = stats["sociodemographics"][stat_key]
        sd["iso_timeseries"] = timeseries

        # 기존 레거시 키 갱신 (30분/60분)
        for legacy_t in (30, 60):
            r = ts_dict.get(legacy_t, {})
            sd[f"iso{legacy_t}_station_count"] = r.get("station_count", 0)
            sd[f"iso{legacy_t}_est_pop"]       = r.get("population", 0)
            sd[f"iso{legacy_t}_est_workers"]   = r.get("workers", 0)

    with open(STATS, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    print("\n" + "=" * 55)
    print("stats.json 업데이트 완료")

    for zone_label, stat_key, _, _ in zones:
        sd = stats["sociodemographics"][stat_key]
        print(f"  {zone_label}: 30분 인구 {sd['iso30_est_pop']:,} / "
              f"60분 인구 {sd['iso60_est_pop']:,}")


if __name__ == "__main__":
    main()
