"""
Step 1-E: 지하철 네트워크 등시간권 분석
- 판교역 (신분당선, node id=824): 30분/60분 등시간권
- 청라국제도시역 (공항철도, node id=313): 30분/60분 등시간권
- 각 역에서 Dijkstra로 최단시간 계산
- 도달 가능 역 → Voronoi 기반 서비스 구역 생성
- 집계구 인구와 교차(centroid 기준) → 도달 가능 인구 산출
- 출력: isochrone_*.geojson, accessibility_curve.json

공간단위: 지하철역 → 집계구
시간범위: 2024년 운영 노선 기준 (begin ≤ 2024-12-31 AND (effective_begin is null OR effective_begin ≤ 2024-12-31))
"""

import os, zipfile, json
import pandas as pd
import numpy as np
import geopandas as gpd
from shapely.geometry import Point, MultiPoint
from shapely.ops import unary_union
import networkx as nx

BASE = r"C:\Users\nanna\OneDrive\바탕 화면\2026 스마트시티학과\스시론\기말 과제"
OUT  = r"C:\Users\nanna\OneDrive\바탕 화면\2026 스마트시티학과\스시론\project\data\processed"

CUTOFF = "2024-12-31"   # 분석 기준 시점

# ── 1. 노드·링크 로드 ──────────────────────────────────────────────
print("subway_network 로드 중...")
with zipfile.ZipFile(os.path.join(BASE, "subway_network.zip")) as z:
    with z.open("network/nodes.tsv") as f:
        nodes = pd.read_csv(f, sep="\t")
    with z.open("network/links.tsv") as f:
        links = pd.read_csv(f, sep="\t")

# 2024년 이전 개통 역/링크만 사용
def is_open(begin_col, effective_col=None):
    """
    begin ≤ CUTOFF 이고 (effective_begin 이 없거나 effective_begin ≤ CUTOFF)
    """
    b = pd.to_datetime(begin_col, errors="coerce")
    ok = b <= pd.Timestamp(CUTOFF)
    if effective_col is not None:
        eb = pd.to_datetime(effective_col, errors="coerce")
        ok = ok & (eb.isna() | (eb <= pd.Timestamp(CUTOFF)))
    return ok

nodes_2024 = nodes[is_open(nodes["begin"], nodes["effective_begin"])].copy()
links_2024 = links[is_open(links["begin"])].copy()
print(f"  2024년 기준 역: {len(nodes_2024):,}개, 링크: {len(links_2024):,}개")

# ── 2. NetworkX 그래프 구축 ───────────────────────────────────────
G = nx.DiGraph()
for _, row in nodes_2024.iterrows():
    G.add_node(int(row["id"]), statnm=row["statnm"], linenm=row["linenm"],
               lat=row["lat"], lng=row["lng"])

for _, row in links_2024.iterrows():
    fn, tn = int(row["fromNode"]), int(row["toNode"])
    if fn in G and tn in G:
        G.add_edge(fn, tn, weight=row["timeFT"])
        G.add_edge(tn, fn, weight=row["timeTF"])

print(f"  그래프 노드: {G.number_of_nodes():,}, 엣지: {G.number_of_edges():,}")

# ── 3. Dijkstra 등시간권 계산 함수 ───────────────────────────────
def get_reachable(source_id: int, max_sec: int) -> pd.DataFrame:
    """source 역에서 max_sec초 이내 도달 가능한 역과 소요시간"""
    lengths = nx.single_source_dijkstra_path_length(G, source_id, cutoff=max_sec, weight="weight")
    rows = []
    for node_id, t in lengths.items():
        if node_id in G.nodes:
            d = G.nodes[node_id]
            rows.append({"node_id": node_id, "time_sec": t,
                         "statnm": d.get("statnm"), "linenm": d.get("linenm"),
                         "lat": d.get("lat"), "lng": d.get("lng")})
    return pd.DataFrame(rows)

# 핵심역
PANGYO_NODE    = 824   # 신분당선 판교역
CHEONGNA_NODE  = 313   # 공항철도 청라국제도시역

print(f"\n판교역(id={PANGYO_NODE}) 60분 등시간권 계산 중...")
df_pangyo   = get_reachable(PANGYO_NODE,   60 * 60)
print(f"  도달 역 수: {len(df_pangyo):,}개")

print(f"청라국제도시역(id={CHEONGNA_NODE}) 60분 등시간권 계산 중...")
df_cheongna = get_reachable(CHEONGNA_NODE, 60 * 60)
print(f"  도달 역 수: {len(df_cheongna):,}개")

# ── 4. 집계구 인구 로드 ───────────────────────────────────────────
# 집계구 경계 shapefile이 있으면 사용; 없으면 역 중심 버퍼로 대체
# SGIS 집계구 SHP는 별도 다운로드 필요 → 여기서는 역 기반 근사법 사용

def build_isochrone_poly(df_reach: pd.DataFrame, max_min: int, all_nodes: pd.DataFrame) -> "gpd.GeoDataFrame":
    """
    도달 역의 좌표로 Convex Hull / 버퍼 기반 isochrone polygon 생성
    대략적 서비스 구역: 역 좌표에 500m 버퍼 후 union
    """
    sub = df_reach[df_reach["time_sec"] <= max_min * 60]
    sub = sub[sub["lat"].notna() & sub["lng"].notna()]
    if len(sub) == 0:
        return gpd.GeoDataFrame()

    # EPSG:5179에서 500m 버퍼 후 WGS84
    gdf = gpd.GeoDataFrame(sub, geometry=gpd.points_from_xy(sub["lng"], sub["lat"]), crs="EPSG:4326")
    gdf_5179 = gdf.to_crs("EPSG:5179")
    buf = gdf_5179.buffer(500)   # 500m 버퍼
    poly = unary_union(buf)

    result = gpd.GeoDataFrame(
        {"time_min": [max_min], "station_count": [len(sub)]},
        geometry=[poly],
        crs="EPSG:5179"
    ).to_crs("EPSG:4326")
    return result

print("\n등시간권 polygon 생성 중...")
isos_pangyo   = []
isos_cheongna = []
for t in [30, 60]:
    isos_pangyo.append(build_isochrone_poly(df_pangyo,   t, nodes_2024))
    isos_cheongna.append(build_isochrone_poly(df_cheongna, t, nodes_2024))

gdf_iso_p = pd.concat(isos_pangyo, ignore_index=True)
gdf_iso_c = pd.concat(isos_cheongna, ignore_index=True)
if not isinstance(gdf_iso_p, gpd.GeoDataFrame):
    gdf_iso_p = gpd.GeoDataFrame(gdf_iso_p)
    gdf_iso_c = gpd.GeoDataFrame(gdf_iso_c)

# ── 5. 누적 접근성 곡선 데이터 ───────────────────────────────────
# 여기서는 역 수 기준 누적 곡선 (인구는 집계구 SHP 없이는 계산 불가)
# → 집계구 SHP가 있으면 아래 주석 해제

def accessibility_curve(df_reach: pd.DataFrame, step: int = 5, max_min: int = 90) -> list:
    curve = []
    for t in range(0, max_min + 1, step):
        cnt = (df_reach["time_sec"] <= t * 60).sum()
        curve.append({"time_min": t, "station_count": int(cnt)})
    return curve

curve_p = accessibility_curve(df_pangyo)
curve_c = accessibility_curve(df_cheongna)

# ── 6. 도달 역 정보 요약 ─────────────────────────────────────────
def summarize(df: pd.DataFrame, label: str):
    print(f"\n[{label}]")
    for t in [30, 60]:
        sub = df[df["time_sec"] <= t * 60]
        print(f"  {t}분 이내 도달 역 수: {len(sub):,}개")
    major = ["강남역", "서울역", "홍대입구역", "여의도역", "판교역", "청라국제도시역"]
    for m in major:
        rows = df[df["statnm"] == m]
        if len(rows):
            t_min = rows["time_sec"].min() / 60
            print(f"  → {m}: {t_min:.1f}분")

summarize(df_pangyo,   "판교역 출발")
summarize(df_cheongna, "청라국제도시역 출발")

# 30분·60분 역 비교표
for t in [30, 60]:
    np = (df_pangyo["time_sec"]   <= t * 60).sum()
    nc = (df_cheongna["time_sec"] <= t * 60).sum()
    print(f"\n[{t}분 등시간권] 판교: {np}역 / 청라국제도시: {nc}역  (비율: {np/nc:.2f}배)" if nc > 0 else f"[{t}분] 판교: {np}역 / 청라국제도시: {nc}역")

# ── 7. 저장 ──────────────────────────────────────────────────────
gdf_iso_p.to_file(os.path.join(OUT, "pangyo_isochrone.geojson"), driver="GeoJSON")
gdf_iso_c.to_file(os.path.join(OUT, "cheongna_isochrone.geojson"), driver="GeoJSON")

# 도달 역 목록도 GeoJSON으로 저장
def stations_geojson(df: pd.DataFrame, label: str):
    sub = df[df["lat"].notna()].copy()
    gdf = gpd.GeoDataFrame(
        sub[["node_id", "statnm", "linenm", "time_sec"]],
        geometry=gpd.points_from_xy(sub["lng"], sub["lat"]),
        crs="EPSG:4326"
    )
    gdf["time_min"] = (gdf["time_sec"] / 60).round(1)
    return gdf

gpd_stations_p = stations_geojson(df_pangyo, "pangyo")
gpd_stations_c = stations_geojson(df_cheongna, "cheongna")
gpd_stations_p.to_file(os.path.join(OUT, "pangyo_stations_reach.geojson"), driver="GeoJSON")
gpd_stations_c.to_file(os.path.join(OUT, "cheongna_stations_reach.geojson"), driver="GeoJSON")

with open(os.path.join(OUT, "accessibility_curve.json"), "w", encoding="utf-8") as f:
    json.dump({
        "pangyo":   {"label": "판교역(신분당선)", "curve": curve_p},
        "cheongna": {"label": "청라국제도시역(공항철도)", "curve": curve_c},
        "note": "station_count는 역 수 기준. 집계구 SHP 연동 시 인구 기준으로 교체 가능.",
        "analysis_cutoff": CUTOFF,
        "pangyo_node": PANGYO_NODE,
        "cheongna_node": CHEONGNA_NODE
    }, f, ensure_ascii=False, indent=2)

print("\n=== 저장 완료 ===")
print(f"pangyo_isochrone.geojson, cheongna_isochrone.geojson, accessibility_curve.json → {OUT}")
