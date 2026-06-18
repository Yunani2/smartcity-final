"""
데이터 구조 파악 스크립트
- 연속지적도 shapefile 컬럼 확인
- 토지이용계획 CSV 중 삼평동·청라동 행 샘플 추출
- 집계구 CSV 컬럼 확인
- subway_network nodes/links 샘플 확인
"""

import zipfile
import io
import sys
import os

import pandas as pd
import geopandas as gpd

BASE = r"C:\Users\nanna\OneDrive\바탕 화면\2026 스마트시티학과\스시론\기말 과제"
OUT  = r"C:\Users\nanna\OneDrive\바탕 화면\2026 스마트시티학과\스시론\project\data\raw"

# ── 1. 연속지적도 (경기 성남 분당구) ──────────────────────────────────
print("=== 연속지적도 (경기 성남시 분당구) ===")
with zipfile.ZipFile(os.path.join(BASE, "연속지적도_경기_성남시_분당구.zip")) as z:
    shp_name = [n for n in z.namelist() if n.endswith(".shp")][0]
    z.extractall(OUT + "/cadastral_gyeonggi")

gdf = gpd.read_file(OUT + "/cadastral_gyeonggi/" + shp_name)
print("CRS:", gdf.crs)
print("컬럼:", list(gdf.columns))
print("행 수:", len(gdf))
print(gdf.head(3).to_string())

print()

# ── 2. 연속지적도 (인천 서구) ────────────────────────────────────────
print("=== 연속지적도 (인천 서구) ===")
with zipfile.ZipFile(os.path.join(BASE, "연속지적도_인천_서구.zip")) as z:
    shp_name2 = [n for n in z.namelist() if n.endswith(".shp")][0]
    z.extractall(OUT + "/cadastral_incheon")

gdf2 = gpd.read_file(OUT + "/cadastral_incheon/" + shp_name2)
print("CRS:", gdf2.crs)
print("컬럼:", list(gdf2.columns))
print("행 수:", len(gdf2))
print(gdf2.head(3).to_string())

print()

# ── 3. 토지이용계획 인천 (전체 로드 가능한 크기) ─────────────────────
print("=== 토지이용계획 인천 (청라동 필터) ===")
with zipfile.ZipFile(os.path.join(BASE, "토지이용계획정보_인천.zip")) as z:
    csv_name = [n for n in z.namelist() if n.endswith(".csv")][0]
    with z.open(csv_name) as f:
        df_lu_ic = pd.read_csv(f, encoding="cp949", dtype={"법정동코드": str})

# 청라동: 2826012200
df_cheongna_lu = df_lu_ic[df_lu_ic["법정동코드"].str.startswith("2826012200")]
print("청라동 토지이용계획 행 수:", len(df_cheongna_lu))
print("용도지역지구 종류:")
print(df_cheongna_lu["용도지역지구명"].value_counts().head(20).to_string())
print()
print(df_cheongna_lu.head(3).to_string())

print()

# ── 4. 토지이용계획 경기 (삼평동·백현동만 chunked 추출) ──────────────
print("=== 토지이용계획 경기 (삼평동 + 백현동 필터, chunked) ===")
SAMPY_CODES = {"4113510900", "4113510800"}  # 삼평동, 백현동

rows = []
with zipfile.ZipFile(os.path.join(BASE, "토지이용계획정보_경기.zip")) as z:
    csv_name_g = [n for n in z.namelist() if n.endswith(".csv")][0]
    with z.open(csv_name_g) as f:
        for chunk in pd.read_csv(f, encoding="cp949", dtype={"법정동코드": str}, chunksize=200_000):
            sub = chunk[chunk["법정동코드"].isin(SAMPY_CODES)]
            if len(sub):
                rows.append(sub)
            # 분당구(41135)를 지나면 중단 가능 — 하지만 정렬 보장 없으므로 전체 스캔
            sys.stdout.write(".")
            sys.stdout.flush()

print()
df_pangyo_lu = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()
print("판교(삼평+백현동) 토지이용계획 행 수:", len(df_pangyo_lu))
if len(df_pangyo_lu):
    print("용도지역지구 종류:")
    print(df_pangyo_lu["용도지역지구명"].value_counts().head(20).to_string())
    df_pangyo_lu.to_csv(OUT + "/pangyo_landuse_raw.csv", index=False, encoding="utf-8-sig")
    print("저장 완료: pangyo_landuse_raw.csv")

print()

# ── 5. 집계구 인구 CSV ────────────────────────────────────────────────
print("=== 집계구 단위 인구 CSV ===")
with zipfile.ZipFile(os.path.join(BASE, "집계구 단위 인구.zip")) as z:
    csv_pop = [n for n in z.namelist() if "인구총괄(총인구)" in n][0]
    with z.open(csv_pop) as f:
        df_pop = pd.read_csv(f, encoding="cp949")
print("컬럼:", list(df_pop.columns))
print(df_pop.head(3).to_string())

print()

# ── 6. subway_network nodes/links ─────────────────────────────────────
print("=== subway_network nodes.tsv ===")
with zipfile.ZipFile(os.path.join(BASE, "subway_network.zip")) as z:
    with z.open("network/nodes.tsv") as f:
        df_nodes = pd.read_csv(f, sep="\t")
print("컬럼:", list(df_nodes.columns))
print(df_nodes.head(5).to_string())
# 판교역, 검암역 찾기
for kw in ["판교", "검암", "청라"]:
    found = df_nodes[df_nodes.apply(lambda r: r.astype(str).str.contains(kw).any(), axis=1)]
    if len(found):
        print(f"\n[{kw}역 후보]")
        print(found[["node_id" if "node_id" in found.columns else found.columns[0], *found.columns[1:5]]].to_string())

print("\n=== subway_network links.tsv (상위 5행) ===")
with zipfile.ZipFile(os.path.join(BASE, "subway_network.zip")) as z:
    with z.open("network/links.tsv") as f:
        df_links = pd.read_csv(f, sep="\t", nrows=5)
print("컬럼:", list(df_links.columns))
print(df_links.to_string())
