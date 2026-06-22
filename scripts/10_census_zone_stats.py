"""
Script 10: 집계구 기반 구역 내 정밀 통계 산출
- 집계구 경계 SHP로 판교/청라 구역 내 집계구 추출
- 집계구별 사업체 수(10차 대분류) + 인구통계 CSV 조인
- 구역 내 합산 통계를 stats.json에 업데이트
"""

import json
import zipfile
import io
import os
import tempfile
import shutil

import geopandas as gpd
import pandas as pd
from shapely.geometry import shape

BASE = r"C:\Users\nanna\OneDrive\바탕 화면\2026 스마트시티학과\스시론\기말 과제"
DATA_DIR = os.path.join(BASE, "project", "docs", "data")
STATS_JSON = os.path.join(DATA_DIR, "stats.json")

# 집계구 관련 zip 경로
BND_BUNDANG = os.path.join(BASE, "집계구 경계_성남시 분당구.zip")
BND_SEOGU   = os.path.join(BASE, "집계구 경계_인천 서구.zip")
BIZ_BUNDANG = os.path.join(BASE, "집계구별 사업체 수_성남시 분당구.zip")
BIZ_SEOGU   = os.path.join(BASE, "집계구별 사업체 수_인천 서구.zip")
POP_BUNDANG = os.path.join(BASE, "집계구별 인구통계_성남시 분당구.zip")
POP_SEOGU   = os.path.join(BASE, "집계구별 인구통계_인천서구.zip")

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

KEY_INDUSTRIES = [
    "제조업", "건설업", "도소매업", "숙박·음식점업",
    "정보통신업", "금융·보험업", "부동산업",
    "전문·과학·기술서비스업", "사업지원서비스업",
    "교육서비스업", "보건·사회복지",
]


def load_zone_boundary(geojson_path):
    gdf = gpd.read_file(geojson_path)
    if gdf.crs is None or gdf.crs.to_epsg() != 4326:
        gdf = gdf.set_crs(4326)
    return gdf.to_crs(5179).union_all()


def load_census_boundary(zip_path):
    tmpdir = tempfile.mkdtemp()
    try:
        with zipfile.ZipFile(zip_path) as z:
            z.extractall(tmpdir)
        shp_files = [f for f in os.listdir(tmpdir) if f.endswith(".shp")]
        if not shp_files:
            raise FileNotFoundError(f"No .shp in {zip_path}")
        shp_path = os.path.join(tmpdir, shp_files[0])
        gdf = gpd.read_file(shp_path, encoding="euc-kr")
        # Determine CRS
        if gdf.crs is None:
            gdf = gdf.set_crs(5179)
        elif gdf.crs.to_epsg() != 5179:
            gdf = gdf.to_crs(5179)
        return gdf
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def filter_census_in_zone(census_gdf, zone_poly):
    """집계구 대표점이 zone 내에 있는 집계구만 반환"""
    rp = census_gdf.geometry.representative_point()
    mask = rp.within(zone_poly)
    filtered = census_gdf[mask].copy()
    print(f"  집계구 필터: {len(census_gdf)} → {len(filtered)}개")
    return filtered


def _decode_zip_name(name_bytes_or_str):
    """zip 항목 이름을 가능한 한 올바른 유니코드로 디코딩"""
    import unicodedata
    if isinstance(name_bytes_or_str, bytes):
        for enc in ("utf-8", "euc-kr", "cp949"):
            try:
                return unicodedata.normalize("NFC", name_bytes_or_str.decode(enc))
            except Exception:
                continue
        return name_bytes_or_str.decode("latin-1")
    return unicodedata.normalize("NFC", name_bytes_or_str)


def _pick_csv(zip_path, keywords_include, keywords_exclude=None):
    """zip 내 CSV 파일 중 keywords_include를 모두 포함하고 keywords_exclude를 포함하지 않는 첫 항목 반환"""
    import unicodedata
    keywords_exclude = keywords_exclude or []
    with zipfile.ZipFile(zip_path) as z:
        names = z.namelist()
        for raw_name in names:
            name = _decode_zip_name(raw_name)
            name_nfc = unicodedata.normalize("NFC", name)
            # 각 키워드 일치 여부: 직접 비교 + NFC 정규화 비교
            match = all(
                kw in name or unicodedata.normalize("NFC", kw) in name_nfc
                for kw in keywords_include
            )
            if match:
                exclude = any(
                    kw in name or unicodedata.normalize("NFC", kw) in name_nfc
                    for kw in keywords_exclude
                )
                if not exclude:
                    return raw_name, name  # (zip entry name, decoded name)
    # fallback: print available and pick by index heuristic
    print(f"  [WARN] keywords {keywords_include} not matched. Available:")
    for n in names:
        print(f"    {repr(n)}")
    return None, None


def _read_csv_raw(zip_path, raw_name, header="infer"):
    """zip 내 CSV를 인코딩 자동탐지로 읽기. header='infer'|None|0"""
    with zipfile.ZipFile(zip_path) as z:
        with z.open(raw_name) as f:
            raw = f.read()
    for enc in ("euc-kr", "cp949", "utf-8-sig", "utf-8"):
        try:
            df = pd.read_csv(io.BytesIO(raw), encoding=enc, header=header)
            return df
        except Exception:
            continue
    raise ValueError(f"CSV 디코딩 실패: {raw_name}")


def _detect_format(df_header_infer):
    """
    Wide format 여부 판별.
    Wide: cp_bnu_XXX 컬럼이 5개 이상 → 실제 cp_bnu 컬럼들이 헤더로 존재
    Long: cp_bnu_XXX 컬럼 1개 이하 → 첫 데이터 행이 헤더로 오인됨 또는 long format
    """
    bnu_cols = [c for c in df_header_infer.columns if str(c).lower().startswith("cp_bnu_")]
    return len(bnu_cols) >= 5, bnu_cols


def load_biz_csv(zip_path):
    """집계구별 사업체 수 대분류 사업체수 CSV 로드"""
    raw_name, decoded = _pick_csv(zip_path,
                                   keywords_include=["대분류", "사업체수"],
                                   keywords_exclude=["총괄", "중분류"])
    if raw_name is None:
        raw_name, decoded = _pick_csv(zip_path, keywords_include=["사업체수"],
                                       keywords_exclude=["총괄", "중분류"])
    if raw_name is None:
        raise FileNotFoundError(f"사업체수 CSV를 {zip_path}에서 찾을 수 없음")
    print(f"  사업체 CSV 선택: {decoded}")

    # 먼저 header=infer로 읽어서 wide/long 판별
    df_infer = _read_csv_raw(zip_path, raw_name, header="infer")
    is_wide, _ = _detect_format(df_infer)
    if is_wide:
        return df_infer  # Wide: 그대로 반환
    else:
        # Long: header=None으로 재로드 (첫 행이 데이터임)
        df_no_hdr = _read_csv_raw(zip_path, raw_name, header=None)
        df_no_hdr.columns = [f"col{i}" for i in range(len(df_no_hdr.columns))]
        return df_no_hdr


def load_pop_csv(zip_path):
    """집계구별 총인구 CSV 로드"""
    raw_name, decoded = _pick_csv(zip_path,
                                   keywords_include=["총인구"],
                                   keywords_exclude=["성연령"])
    if raw_name is None:
        raw_name, decoded = _pick_csv(zip_path, keywords_include=["인구총괄"])
    if raw_name is None:
        print(f"  [WARN] 인구 CSV를 {zip_path}에서 찾을 수 없음")
        return None
    print(f"  인구 CSV 선택: {decoded}")

    df_infer = _read_csv_raw(zip_path, raw_name, header="infer")
    # 인구 CSV는 항상 long format 간주
    # 컬럼명에 '총인구', 'to_in_001' 등이 있으면 wide or labeled long
    if any("to_in" in str(c).lower() or "총인구" in str(c) for c in df_infer.columns):
        return df_infer  # labeled
    # 첫 행이 헤더처럼 보이는지 확인 (숫자 연도가 컬럼명이면 no-header)
    first_col = str(df_infer.columns[0])
    if first_col.isdigit():  # '2024' → no-header
        df_no_hdr = _read_csv_raw(zip_path, raw_name, header=None)
        df_no_hdr.columns = [f"col{i}" for i in range(len(df_no_hdr.columns))]
        return df_no_hdr
    return df_infer


def detect_oa_col(df, zone_oa_sample):
    """
    집계구 코드 컬럼명 자동 탐지.
    전략: (1) 컬럼명에 'oa' / '집계구' 포함, (2) 값이 zone OA 코드와 같은 자릿수(14자리),
    (3) 인덱스 1번(연도 다음 컬럼) 순으로 fallback.
    """
    # 1) 컬럼명 힌트
    for c in df.columns:
        cl = c.strip().lower()
        if "oa" in cl or "집계구" in cl:
            return c
    # 2) 값 길이로 탐지: zone OA 코드 길이 파악
    if zone_oa_sample:
        oa_len = len(str(zone_oa_sample[0]))
        for c in df.columns:
            sample_vals = df[c].astype(str).str.strip().head(5).tolist()
            # 대부분 같은 길이면 OA 컬럼
            if all(len(v) == oa_len for v in sample_vals if v not in ("nan", "")):
                return c
    # 3) 두 번째 컬럼 (첫 번째는 보통 연도)
    if len(df.columns) >= 2:
        return df.columns[1]
    return df.columns[0]


def compute_biz_stats(biz_df, zone_oa_codes):
    """
    구역 내 집계구 사업체 수 집계.
    CSV가 long format: 연도|집계구코드|업종코드|사업체수 (4컬럼)
    또는 wide format: 연도|집계구코드|cp_bnu_001|...|cp_bnu_021 (24컬럼+)
    자동 판별 후 처리.
    """
    oa_col = detect_oa_col(biz_df, list(zone_oa_codes)[:3])
    print(f"  OA 컬럼 감지: '{oa_col}'")

    biz_df = biz_df.copy()
    biz_df[oa_col] = biz_df[oa_col].astype(str).str.strip()
    zone_codes_str = set(str(c).strip() for c in zone_oa_codes)

    zone_biz = biz_df[biz_df[oa_col].isin(zone_codes_str)].copy()
    print(f"  사업체 CSV: 전체 {len(biz_df)}행 중 구역 내 {len(zone_biz)}행 매칭")

    if zone_biz.empty:
        print(f"  [WARN] 매칭 없음. CSV OA 샘플: {list(biz_df[oa_col].head(5))}")
        print(f"  [WARN] Zone OA 샘플: {list(zone_oa_codes)[:5]}")
        return {}, 0

    # wide vs long format 판별
    # wide: cp_bnu_XXX 컬럼이 여럿 존재
    bnu_cols_wide = [c for c in zone_biz.columns if str(c).lower().startswith("cp_bnu_")]
    if bnu_cols_wide:
        # Wide format
        print(f"  Wide format 감지: cp_bnu 컬럼 {len(bnu_cols_wide)}개")
        col_lower_map = {c.strip().lower(): c for c in zone_biz.columns}
        counts = {}
        total = 0
        for bnu_key, industry in BNU_MAP.items():
            actual_col = col_lower_map.get(bnu_key.lower())
            if actual_col:
                val = pd.to_numeric(zone_biz[actual_col], errors="coerce").fillna(0).sum()
                counts[industry] = int(val)
                total += int(val)
            else:
                counts[industry] = 0
        return counts, total
    else:
        # Long format: col0=연도, col1=집계구코드, col2=업종코드, col3=사업체수
        # (header=None으로 읽어 컬럼명이 col0,col1,col2,col3 형태)
        cols = list(zone_biz.columns)
        if len(cols) < 4:
            print(f"  [WARN] 컬럼 수 부족: {cols}")
            return {}, 0
        # col1 재탐지 (헤더=None이면 'col1')
        oa_col2 = detect_oa_col(zone_biz, list(zone_oa_codes)[:3])
        ind_col = cols[2]  # 업종코드
        cnt_col = cols[3]  # 사업체수
        print(f"  Long format: OA='{oa_col2}', 업종코드='{ind_col}', 사업체수='{cnt_col}'")
        zone_biz_f = zone_biz[zone_biz[oa_col2].astype(str).str.strip().isin(
            set(str(c).strip() for c in zone_oa_codes))].copy()
        print(f"  Long 재필터: {len(zone_biz_f)}행")
        if zone_biz_f.empty:
            return {}, 0
        print(f"  업종코드 샘플: {list(zone_biz_f[ind_col].head(5))}")

        zone_biz_f[cnt_col] = pd.to_numeric(zone_biz_f[cnt_col], errors="coerce").fillna(0)
        grouped = zone_biz_f.groupby(ind_col)[cnt_col].sum()

        counts = {}
        total = 0
        for bnu_key, industry in BNU_MAP.items():
            val = int(grouped.get(bnu_key, 0))
            counts[industry] = val
            total += val
        return counts, total


def compute_pop_stats(pop_df, zone_oa_codes):
    """
    구역 내 집계구 총인구 집계.
    Long format: 연도|집계구코드|항목코드|값 (4컬럼)
    총인구 항목코드 = 'to_in_001' (SGIS 표준)
    """
    oa_col = detect_oa_col(pop_df, list(zone_oa_codes)[:3])
    print(f"  인구 OA 컬럼 감지: '{oa_col}'")

    pop_df = pop_df.copy()
    pop_df[oa_col] = pop_df[oa_col].astype(str).str.strip()
    zone_codes_str = set(str(c).strip() for c in zone_oa_codes)
    zone_pop = pop_df[pop_df[oa_col].isin(zone_codes_str)].copy()
    print(f"  인구 CSV: 전체 {len(pop_df)}행 중 구역 내 {len(zone_pop)}행 매칭")

    if zone_pop.empty:
        return None

    cols = list(zone_pop.columns)
    # Long format 처리: 항목코드 컬럼 탐색
    if len(cols) >= 4:
        # 항목코드 컬럼 = col2 (또는 'to_in_001' 등이 값으로 있는 컬럼)
        ind_col = None
        val_col = None
        for i, c in enumerate(cols):
            sample = pop_df[c].astype(str).head(20).tolist()
            if any("to_in" in s.lower() for s in sample):
                ind_col = c
                val_col = cols[i + 1] if i + 1 < len(cols) else cols[-1]
                break
        if ind_col is None:
            ind_col = cols[2]
            val_col = cols[3]
        print(f"  항목코드='{ind_col}', 값='{val_col}'")
        print(f"  항목코드 유니크값: {list(zone_pop[ind_col].unique())[:8]}")

        # 총인구 항목 코드 탐색
        tot_pop_code = None
        for code in zone_pop[ind_col].unique():
            code_s = str(code).lower().strip()
            if code_s in ("to_in_001", "tot_pop", "총인구") or "to_in_001" in code_s:
                tot_pop_code = code
                break
        if tot_pop_code is None:
            tot_pop_code = zone_pop[ind_col].iloc[0]
            print(f"  [WARN] to_in_001 미발견, 첫 항목코드 사용: '{tot_pop_code}'")

        tot_rows = zone_pop[zone_pop[ind_col] == tot_pop_code]
        total_pop = int(pd.to_numeric(tot_rows[val_col], errors="coerce").fillna(0).sum())
        print(f"  총인구 (항목={tot_pop_code}) → {total_pop:,}명")
        return total_pop

    # Wide format fallback: 숫자 컬럼 합산
    num_cols = zone_pop.select_dtypes(include="number").columns.tolist()
    if num_cols:
        pop_col = num_cols[-1]
        total_pop = int(pd.to_numeric(zone_pop[pop_col], errors="coerce").fillna(0).sum())
        print(f"  총인구 컬럼(wide fallback): '{pop_col}' → {total_pop:,}명")
        return total_pop
    return None


def process_zone(zone_name, zone_geojson, bnd_zip, biz_zip, pop_zip):
    print(f"\n{'='*50}")
    print(f"[{zone_name}] 처리 시작")

    # 1. zone polygon
    zone_poly = load_zone_boundary(zone_geojson)
    print(f"  Zone area: {zone_poly.area / 1e6:.4f} km²")

    # 2. 집계구 경계 로드 및 필터
    census_gdf = load_census_boundary(bnd_zip)
    print(f"  집계구 전체: {len(census_gdf)}개, CRS: {census_gdf.crs}")
    print(f"  집계구 컬럼: {list(census_gdf.columns)}")

    zone_census = filter_census_in_zone(census_gdf, zone_poly)

    if zone_census.empty:
        print(f"  [ERROR] {zone_name}: 구역 내 집계구 없음!")
        return None

    # 집계구 OA 코드 목록
    # SGIS 집계구 코드 컬럼 찾기
    oa_col_shp = None
    for c in zone_census.columns:
        if "tot_oa" in c.lower() or "oa_cd" in c.lower() or c.upper() == "TOT_OA_CD":
            oa_col_shp = c
            break
    if oa_col_shp is None:
        # 컬럼 출력 후 첫 번째 문자형 컬럼 사용
        print(f"  [WARN] OA코드 컬럼 못찾음, 컬럼 목록: {list(zone_census.columns)}")
        oa_col_shp = zone_census.columns[0]

    zone_oa_codes = zone_census[oa_col_shp].astype(str).str.strip().tolist()
    print(f"  OA코드({oa_col_shp}) 샘플: {zone_oa_codes[:5]}")

    # 3. 사업체 수 CSV 로드 및 집계
    biz_df = load_biz_csv(biz_zip)
    print(f"  사업체 CSV 컬럼 샘플: {list(biz_df.columns[:6])}")
    biz_counts, total_biz = compute_biz_stats(biz_df, zone_oa_codes)

    # 4. 인구 CSV
    pop_total = None
    try:
        pop_df = load_pop_csv(pop_zip)
        if pop_df is not None:
            print(f"  인구 CSV 컬럼: {list(pop_df.columns[:6])}")
            pop_total = compute_pop_stats(pop_df, zone_oa_codes)
    except Exception as e:
        print(f"  [WARN] 인구 CSV 처리 실패: {e}")

    # 5. 결과 정리
    if total_biz > 0:
        biz_pct = {k: round(v / total_biz * 100, 2) for k, v in biz_counts.items() if v > 0}
        key_biz_pct = {k: round(biz_counts.get(k, 0) / total_biz * 100, 2) for k in KEY_INDUSTRIES}
    else:
        biz_pct = {}
        key_biz_pct = {}

    # 면적 비율로 집계 결과 확인
    zone_area_m2 = zone_poly.area
    census_area_m2 = zone_census.geometry.area.sum()
    area_ratio = census_area_m2 / zone_area_m2

    result = {
        "zone_census_count": int(len(zone_census)),
        "zone_area_m2": round(zone_area_m2),
        "census_area_m2": round(census_area_m2),
        "coverage_ratio": round(area_ratio, 3),
        "total_businesses_zone": total_biz,
        "biz_by_industry_zone": biz_pct,
        "biz_counts_zone": biz_counts,
        "key_industry_pct_zone": key_biz_pct,
        "total_pop_zone": pop_total,
        "note": f"집계구 {len(zone_census)}개 합산 (구역 내 대표점 기준 필터, 2023 사업체·2024 인구)"
    }

    print(f"\n  [{zone_name}] 결과 요약:")
    print(f"    집계구 {len(zone_census)}개, 총 사업체 {total_biz:,}개")
    if pop_total:
        print(f"    총 인구 {pop_total:,}명")
    top3 = sorted(biz_pct.items(), key=lambda x: -x[1])[:3]
    for nm, pct in top3:
        print(f"    {nm}: {pct}%")

    return result


def main():
    with open(STATS_JSON, encoding="utf-8") as f:
        stats = json.load(f)

    # 판교
    pangyo_result = process_zone(
        "판교",
        os.path.join(DATA_DIR, "pangyo_zone.geojson"),
        BND_BUNDANG,
        BIZ_BUNDANG,
        POP_BUNDANG,
    )

    # 청라
    cheongna_result = process_zone(
        "청라",
        os.path.join(DATA_DIR, "cheongna_zone.geojson"),
        BND_SEOGU,
        BIZ_SEOGU,
        POP_SEOGU,
    )

    # stats.json 업데이트
    if pangyo_result:
        stats["sociodemographics"]["pangyo"].update({
            "total_businesses_zone": pangyo_result["total_businesses_zone"],
            "biz_by_industry_zone": pangyo_result["biz_by_industry_zone"],
            "biz_counts_zone": pangyo_result["biz_counts_zone"],
            "key_industry_pct_zone": pangyo_result["key_industry_pct_zone"],
            "zone_pop": pangyo_result["total_pop_zone"],
            "zone_census_count": pangyo_result["zone_census_count"],
            "zone_note": pangyo_result["note"],
        })
        if pangyo_result["total_pop_zone"]:
            stats["sociodemographics"]["pangyo"]["zone_pop"] = pangyo_result["total_pop_zone"]

    if cheongna_result:
        stats["sociodemographics"]["cheongna"].update({
            "total_businesses_zone": cheongna_result["total_businesses_zone"],
            "biz_by_industry_zone": cheongna_result["biz_by_industry_zone"],
            "biz_counts_zone": cheongna_result["biz_counts_zone"],
            "key_industry_pct_zone": cheongna_result["key_industry_pct_zone"],
            "zone_pop": cheongna_result["total_pop_zone"],
            "zone_census_count": cheongna_result["zone_census_count"],
            "zone_note": cheongna_result["note"],
        })

    # note 업데이트
    stats["sociodemographics"]["note"] = (
        "구역 내 집계구(대표점 기준) 집계. "
        "사업체 수: SGIS 2023년 10차 대분류. "
        "인구: SGIS 2024년 총인구. "
        "시군구 수준 통계도 병행 보존."
    )

    with open(STATS_JSON, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

    print(f"\n stats.json 업데이트 완료: {STATS_JSON}")


if __name__ == "__main__":
    main()
