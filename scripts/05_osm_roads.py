"""
05_osm_roads.py
OSM에서 판교·청라 구역 내 도로망 다운로드 후 지표 산출
- 도로망 밀도 (km/km2), 교차로 수, 도로 구간 수
- docs/data/에 edges GeoJSON 저장 (지도 레이어용)
- data/processed/stats.json에 road 항목 추가
"""

import json, os
import geopandas as gpd
import osmnx as ox
from shapely.geometry import shape

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROCESSED = os.path.join(BASE, "data", "processed")
DOCS_DATA = os.path.join(BASE, "docs", "data")

# zone_info.json에서 실제 면적 읽기
with open(os.path.join(PROCESSED, "zone_info.json"), encoding="utf-8") as f:
    _zi = json.load(f)

ZONES = {
    "pangyo":  {"file": "pangyo_zone.geojson",  "area_km2": _zi["pangyo"]["area_km2"]},
    "cheongna": {"file": "cheongna_zone.geojson", "area_km2": _zi["cheongna"]["area_km2"]},
}

road_stats = {}

for name, cfg in ZONES.items():
    print(f"\n[{name}] 도로망 다운로드 중...")
    with open(os.path.join(PROCESSED, cfg["file"]), encoding="utf-8") as f:
        zd = json.load(f)
    polygon = shape(zd["features"][0]["geometry"])

    # 차량 도로망 (도로망 지표용)
    G_drive = ox.graph_from_polygon(polygon, network_type="drive", retain_all=False)
    # 보행 도로망 (도보 접근 보정용)
    G_walk  = ox.graph_from_polygon(polygon, network_type="walk",  retain_all=False)

    # --- 차량 도로 지표 ---
    _, edges_d = ox.graph_to_gdfs(G_drive)
    nodes_d, _ = ox.graph_to_gdfs(G_drive)
    drive_length_m  = edges_d["length"].sum()
    drive_length_km = drive_length_m / 1000
    area_km2        = cfg["area_km2"]
    drive_density   = drive_length_km / area_km2   # km/km²
    n_intersections = len(nodes_d)
    n_segments      = len(edges_d)

    # --- 보행 도로 지표 ---
    _, edges_w = ox.graph_to_gdfs(G_walk)
    walk_length_km  = edges_w["length"].sum() / 1000
    walk_density    = walk_length_km / area_km2

    print(f"  차량도로: {drive_length_km:.1f} km  밀도 {drive_density:.1f} km/km²  교차로 {n_intersections}개  구간 {n_segments}개")
    print(f"  보행도로: {walk_length_km:.1f} km  밀도 {walk_density:.1f} km/km²")

    road_stats[name] = {
        "drive_length_km":  round(drive_length_km, 2),
        "drive_density_km_km2": round(drive_density, 2),
        "walk_length_km":   round(walk_length_km, 2),
        "walk_density_km_km2":  round(walk_density, 2),
        "n_intersections":  int(n_intersections),
        "n_road_segments":  int(n_segments),
    }

    # --- 차량 도로 GeoJSON 저장 (지도 레이어용, 필요 컬럼만) ---
    keep_cols = ["name", "highway", "length", "geometry"]
    save_cols = [c for c in keep_cols if c in edges_d.columns]
    edges_save = edges_d[save_cols].reset_index(drop=True)
    out_path = os.path.join(DOCS_DATA, f"{name}_roads.geojson")
    edges_save.to_file(out_path, driver="GeoJSON")
    print(f"  저장: {out_path}")

# --- stats.json에 road_stats 병합 ---
stats_path = os.path.join(DOCS_DATA, "stats.json")
with open(stats_path, encoding="utf-8") as f:
    stats = json.load(f)

stats["road"] = road_stats

with open(stats_path, "w", encoding="utf-8") as f:
    json.dump(stats, f, ensure_ascii=False, indent=2)

# processed에도 동기화
import shutil
shutil.copy(stats_path, os.path.join(PROCESSED, "stats.json"))

print("\n완료 - stats.json에 road 항목 추가됨")
print(json.dumps(road_stats, ensure_ascii=False, indent=2))
