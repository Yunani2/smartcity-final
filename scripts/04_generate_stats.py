"""
Step 2: 최종 stats.json 생성
- building_metrics.json + accessibility_curve.json + zone_info.json 합산
- 집계구 인구: 분당구(31130) / 인천 서구(23080) 행정구역 단위로 수집
  (삼평동·청라동 법정동 단위 집계구 shapefile 없어 행정구역 단위로 대체)
"""

import os, json, zipfile
import pandas as pd

BASE = r"C:\Users\nanna\OneDrive\바탕 화면\2026 스마트시티학과\스시론\기말 과제"
OUT  = r"C:\Users\nanna\OneDrive\바탕 화면\2026 스마트시티학과\스시론\project\data\processed"

# ── 기존 지표 로드 ─────────────────────────────────────────────────
with open(os.path.join(OUT, "building_metrics.json"), encoding="utf-8") as f:
    bm = json.load(f)
with open(os.path.join(OUT, "accessibility_curve.json"), encoding="utf-8") as f:
    ac = json.load(f)
with open(os.path.join(OUT, "zone_info.json"), encoding="utf-8") as f:
    zi = json.load(f)

# ── 집계구 인구 로드 ───────────────────────────────────────────────
def load_pop_csv(zip_path: str, fname_kw: str) -> pd.DataFrame:
    with zipfile.ZipFile(zip_path) as z:
        fname = [n for n in z.namelist() if fname_kw in n][0]
        with z.open(fname) as f:
            return pd.read_csv(f, encoding="utf-8", header=None,
                               names=["year", "code", "indicator", "value"])

pop_zip = os.path.join(BASE, "집계구 단위 인구.zip")
ga_zip  = os.path.join(BASE, "집계구 단위 가구.zip")

df_pop = load_pop_csv(pop_zip, "총인구")
df_pop["code"] = df_pop["code"].astype(str)

# 분당구 집계구 인구 (경기 성남시 분당구 = 31130xxxx 중 분당구 해당)
# 통계청 코드: 경기(31) + 성남시(130) → 앞5자리 31130
# 분당구는 31130 중에서 행정동 구분 필요 → 전체 성남시로 보수적 추출
bundang_pop_total = df_pop[df_pop["code"].str.startswith("311305")]["value"].sum()  # 311305 = 분당구 일부
seongnam_pop_total = df_pop[df_pop["code"].str.startswith("31130")]["value"].sum()
seo_gu_pop_total   = df_pop[df_pop["code"].str.startswith("23080")]["value"].sum()  # 인천 서구

print(f"성남시 전체 인구(31130 시작): {seongnam_pop_total:,.0f}명")
print(f"인천 서구 전체 인구(23080 시작): {seo_gu_pop_total:,.0f}명")

# 가구 수
df_ga = load_pop_csv(ga_zip, "가구총괄")
df_ga["code"] = df_ga["code"].astype(str)
seongnam_ga = df_ga[df_ga["code"].str.startswith("31130")]["value"].sum()
seo_gu_ga   = df_ga[df_ga["code"].str.startswith("23080")]["value"].sum()
print(f"성남시 가구(31130): {seongnam_ga:,.0f}가구")
print(f"인천 서구 가구(23080): {seo_gu_ga:,.0f}가구")

# ── 등시간권 요약 ──────────────────────────────────────────────────
# accessibility_curve.json에서 30분·60분 역 수 추출
def get_station_count(curve: list, t: int) -> int:
    for item in curve:
        if item["time_min"] == t:
            return item["station_count"]
    return 0

p_30  = get_station_count(ac["pangyo"]["curve"],   30)
p_60  = get_station_count(ac["pangyo"]["curve"],   60)
c_30  = get_station_count(ac["cheongna"]["curve"], 30)
c_60  = get_station_count(ac["cheongna"]["curve"], 60)

# ── 최종 stats.json 생성 ──────────────────────────────────────────
stats = {
    "meta": {
        "analysis_date": "2026-06-18",
        "data_reference": "2024년 기준",
        "sources": [
            "건축물대장 (건축HUB, 2024년)",
            "연속지적도 LSMD_CONT_LDREG_41135/28260_202606",
            "VWorld 토지이용계획정보 (2026년 6월)",
            "subway_network.zip (2026-05-05 export, 2024년 기준 필터)",
            "SGIS 집계구 단위 인구·가구 (2025년2분기기준_2024년)"
        ]
    },
    "zone": {
        "pangyo": {
            **zi["pangyo"],
            "core_station": "판교역(신분당선)",
            "core_station_node": 824
        },
        "cheongna": {
            **zi["cheongna"],
            "core_station": "청라국제도시역(공항철도)",
            "core_station_node": 313
        }
    },
    "land_use_buildings": {
        "pangyo": bm["pangyo"],
        "cheongna": bm["cheongna"],
        "category_colors": bm["category_colors"]
    },
    "transport": {
        "pangyo": {
            "core_station": "판교역(신분당선)",
            "isochrone_30min_stations": p_30,
            "isochrone_60min_stations": p_60,
        },
        "cheongna": {
            "core_station": "청라국제도시역(공항철도)",
            "isochrone_30min_stations": c_30,
            "isochrone_60min_stations": c_60,
        },
        "comparison": {
            "ratio_30min": round(p_30 / c_30, 2) if c_30 > 0 else None,
            "ratio_60min": round(p_60 / c_60, 2) if c_60 > 0 else None,
        }
    },
    "demographics": {
        "note": "집계구 shapefile 없어 행정구역(성남시/인천 서구) 단위 집계. 삼평동·청라동 단독 집계 불가.",
        "seongnam_city_pop": int(seongnam_pop_total),
        "seogu_incheon_pop": int(seo_gu_pop_total),
        "seongnam_city_households": int(seongnam_ga),
        "seogu_incheon_households": int(seo_gu_ga),
    },
    "accessibility_curve": {
        "pangyo":   ac["pangyo"]["curve"],
        "cheongna": ac["cheongna"]["curve"]
    }
}

with open(os.path.join(OUT, "stats.json"), "w", encoding="utf-8") as f:
    json.dump(stats, f, ensure_ascii=False, indent=2)

print("\n=== stats.json 생성 완료 ===")
print(f"저장: {OUT}/stats.json")
print("\n[핵심 비교 지표 요약]")
print(f"{'지표':<30} {'판교':<20} {'청라':<20}")
print("-" * 70)
print(f"{'구역 면적(km²)':<30} {zi['pangyo']['area_km2']:<20} {zi['cheongna']['area_km2']:<20}")
print(f"{'건축물 수(동)':<30} {bm['pangyo']['building_count']:<20} {bm['cheongna']['building_count']:<20}")
print(f"{'총 연면적(백만㎡)':<30} {bm['pangyo']['total_gfa_m2']/1e6:.4f}{'':10} {bm['cheongna']['total_gfa_m2']/1e6:.4f}{'':10}")
print(f"{'업무시설 연면적비율(%)':<30} {bm['pangyo']['use_ratio_pct'].get('업무시설',0):<20} {bm['cheongna']['use_ratio_pct'].get('업무시설',0):<20}")
print(f"{'교육연구 연면적비율(%)':<30} {bm['pangyo']['use_ratio_pct'].get('교육연구시설',0):<20} {bm['cheongna']['use_ratio_pct'].get('교육연구시설',0):<20}")
print(f"{'주거 연면적비율(%)':<30} {bm['pangyo']['use_ratio_pct'].get('주거',0):<20} {bm['cheongna']['use_ratio_pct'].get('주거',0):<20}")
print(f"{'LUM 엔트로피':<30} {bm['pangyo']['lum_entropy']:<20} {bm['cheongna']['lum_entropy']:<20}")
print(f"{'평균 용적률(%)':<30} {bm['pangyo']['avg_far_pct']:<20} {bm['cheongna']['avg_far_pct']:<20}")
print(f"{'30분 이내 도달 역수':<30} {p_30:<20} {c_30:<20}")
print(f"{'60분 이내 도달 역수':<30} {p_60:<20} {c_60:<20}")
