import json, os
BASE = r"C:\Users\nanna\OneDrive\바탕 화면\2026 스마트시티학과\스시론\기말 과제\project\docs\data"
for fn in ["pangyo_isochrone.geojson", "cheongna_isochrone.geojson"]:
    path = os.path.join(BASE, fn)
    with open(path, encoding="utf-8") as f:
        d = json.load(f)
    feats = d["features"]
    print(f"\n=== {fn} ===")
    print(f"  n_features: {len(feats)}")
    for feat in feats[:4]:
        g = feat["geometry"]
        p = feat["properties"]
        nc = len(g["coordinates"][0]) if g["type"] == "Polygon" else (len(g["coordinates"]) if g["type"] == "MultiPolygon" else "?")
        print(f"  time_min={p.get('time_min')}, geom={g['type']}, ring_pts={nc}, station_count={p.get('station_count')}")
