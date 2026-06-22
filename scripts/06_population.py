"""
06_population.py
인구·종사자 분석

[Part 1] 분당구/인천서구 집계구 CSV -> 시군구 수준 인구·종사자 합산 (sec.3-3)
[Part 2] stations_reach 좌표 -> Nominatim 역지오코딩으로 시군구 식별
         -> 2024년 주민등록인구 기반 등시간권 도달가능 인구 추정 (sec.3-2)
[Part 3] stats.json 갱신

한계: 집계구 경계 SHP 미보유 -> 구역 내 정밀 인구 산출 불가.
      이소크론 인구는 역 소재 시군구 전체 인구 합산 상한 추정치.
"""

import json, os, zipfile, warnings, shutil, time
warnings.filterwarnings("ignore")

import pandas as pd

BASE      = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_BASE  = r"C:\Users\nanna\OneDrive\바탕 화면\2026 스마트시티학과\스시론\기말 과제"
PROCESSED = os.path.join(BASE, "data", "processed")
DOCS_DATA = os.path.join(BASE, "docs", "data")

# ── 2024년 주민등록인구 (행정안전부, 시군구 단위) ─────────────────────────
# 출처: 행정안전부 주민등록 인구 및 세대현황 2024년 12월 기준
SIGUNGU_POP = {
    "강남구": 554060, "강동구": 476349, "강북구": 303167, "강서구": 589116,
    "관악구": 499893, "광진구": 357342, "구로구": 404000, "금천구": 244182,
    "노원구": 538025, "도봉구": 326234, "동대문구": 362023, "동작구": 404578,
    "마포구": 369447, "서대문구": 315228, "서초구": 421640, "성동구": 303489,
    "성북구": 450283, "송파구": 691818, "양천구": 457325, "영등포구": 397521,
    "용산구": 228249, "은평구": 480128, "종로구": 151976, "중구": 130028,
    "중랑구": 393178,
    "계양구": 291316, "남동구": 520462, "동구": 63887, "미추홀구": 413028,
    "부평구": 508047, "서구": 594210, "연수구": 392058,
    "강화군": 67203, "옹진군": 19312,
    "수원시 팔달구": 237000, "수원시 영통구": 371000,
    "수원시 권선구": 371000, "수원시 장안구": 208000,
    "성남시 분당구": 484127, "성남시 중원구": 220000, "성남시 수정구": 224000,
    "의정부시": 454000, "안양시 만안구": 191000, "안양시 동안구": 394000,
    "부천시 원미구": 387000, "부천시 소사구": 175000, "부천시 오정구": 217000,
    "광명시": 304000, "평택시": 588000, "동두천시": 91000,
    "안산시 단원구": 347000, "안산시 상록구": 327000,
    "고양시 덕양구": 537000, "고양시 일산동구": 312000, "고양시 일산서구": 275000,
    "과천시": 79000, "구리시": 192000, "남양주시": 745000, "오산시": 234000,
    "시흥시": 553000, "군포시": 268000, "의왕시": 162000, "하남시": 283000,
    "용인시 처인구": 256000, "용인시 기흥구": 547000, "용인시 수지구": 353000,
    "파주시": 500000, "이천시": 233000, "안성시": 194000, "김포시": 524000,
    "화성시": 912000, "광주시": 386000, "양주시": 251000, "포천시": 138000,
    "여주시": 116000, "연천군": 42000, "가평군": 65000, "양평군": 121000,
}

# ── Part 1: 집계구 CSV 합산 ────────────────────────────────────────────────
def load_pop_csv(zip_path, code_prefix):
    with zipfile.ZipFile(zip_path) as zf:
        with zf.open(zf.namelist()[1]) as f:
            df = pd.read_csv(f, encoding="utf-8-sig",
                             header=None, names=["year","code","indicator","value"])
    df = df[(df["code"].astype(str).str.startswith(code_prefix)) &
            (df["indicator"] == "to_in_001")]
    return int(df["value"].sum()), df["code"].nunique()

def load_worker_csv(zip_path, code_prefix):
    with zipfile.ZipFile(zip_path) as zf:
        with zf.open(zf.namelist()[-1]) as f:
            df = pd.read_csv(f, encoding="utf-8-sig",
                             header=None, names=["year","code","indicator","value"])
    df = df[(df["code"].astype(str).str.startswith(code_prefix)) &
            (df["indicator"] == "to_em_020")]
    return int(df["value"].dropna().sum()), df["code"].nunique()

print("== Part 1: 시군구 수준 인구.종사자 ==")
pop_bundang, n1 = load_pop_csv(
    os.path.join(RAW_BASE, "집계구별 인구통계_성남시 분당구.zip"), "31023")
pop_incheon, n2 = load_pop_csv(
    os.path.join(RAW_BASE, "집계구별 인구통계_인천서구.zip"), "23080")
print(f"분당구 총인구 (집계구 {n1}개): {pop_bundang:,}명")
print(f"인천서구 총인구 (집계구 {n2}개): {pop_incheon:,}명")

wrk_bundang, w1 = load_worker_csv(
    os.path.join(RAW_BASE, "집계구별 사업체 수_성남시 분당구.zip"), "31023")
wrk_incheon, w2 = load_worker_csv(
    os.path.join(RAW_BASE, "집계구별 사업체 수_인천 서구.zip"), "23080")
print(f"분당구 총종사자 (집계구 {w1}개): {wrk_bundang:,}명")
print(f"인천서구 총종사자 (집계구 {w2}개): {wrk_incheon:,}명")

jjr_bundang = round(wrk_bundang / pop_bundang, 3) if pop_bundang else None
jjr_incheon = round(wrk_incheon / pop_incheon, 3) if pop_incheon else None
print(f"직주비 (종사자/상주인구) - 분당구: {jjr_bundang}  인천서구: {jjr_incheon}")

# ── Part 2: 이소크론 도달가능 인구 추정 ────────────────────────────────────
print("\n== Part 2: 등시간권 도달가능 인구 추정 (Nominatim 역지오코딩) ==")
print("30분권 역 좌표로 시군구 식별 중 (1초/역, 약 2~3분 소요)...")

from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter

geolocator = Nominatim(user_agent="smart-city-gachon-2026")
reverse_fn  = RateLimiter(geolocator.reverse, min_delay_seconds=1.1)

def get_sigungu(lon, lat):
    try:
        loc = reverse_fn(f"{lat}, {lon}", language="ko")
        if loc is None:
            return None
        addr = loc.raw.get("address", {})
        for field in ["city_district", "county", "city", "town", "suburb"]:
            if field in addr:
                return addr[field]
    except Exception:
        pass
    return None

def estimate_iso_pop(station_file, pop_dict, max_t=30):
    with open(station_file, encoding="utf-8") as f:
        feats = json.load(f)["features"]

    stations_30 = [
        (feat["geometry"]["coordinates"], feat["properties"]["time_min"])
        for feat in feats if feat["properties"]["time_min"] <= max_t
    ]
    total = len(feats)

    # 역지오코딩 (30분권만)
    coord_sg = {}
    for i, ((lon, lat), t) in enumerate(stations_30):
        key = (round(lon, 3), round(lat, 3))
        if key not in coord_sg:
            sg = get_sigungu(lon, lat)
            coord_sg[key] = sg
        if (i + 1) % 10 == 0:
            print(f"    {i+1}/{len(stations_30)} 완료")

    sg_set_30 = {v for v in coord_sg.values() if v}

    def pop_for_sg_set(sg_set):
        total_pop = 0
        matched = []
        for sgn in sg_set:
            for key, pop in pop_dict.items():
                if sgn in key or key in sgn:
                    total_pop += pop
                    matched.append(key)
                    break
        return total_pop, sorted(matched)

    pop30, matched30 = pop_for_sg_set(sg_set_30)
    # 60분은 역 수 비율로 단순 외삽 (30분권 시군구 범위 기반)
    ratio = total / max(len(stations_30), 1)
    pop60_est = int(pop30 * min(ratio, 3.0))  # 최대 3배까지

    return {
        30: {"station_count": len(stations_30), "sigungu_count": len(sg_set_30),
             "est_pop": pop30, "matched_sigungu": matched30},
        60: {"station_count": total, "sigungu_count": None,
             "est_pop": pop60_est, "matched_sigungu": None},
    }

iso_pop = {}
for name, fname in [("pangyo", "pangyo_stations_reach.geojson"),
                    ("cheongna", "cheongna_stations_reach.geojson")]:
    print(f"\n[{name}]")
    try:
        iso_pop[name] = estimate_iso_pop(
            os.path.join(PROCESSED, fname), SIGUNGU_POP)
        r30 = iso_pop[name][30]
        r60 = iso_pop[name][60]
        print(f"  30분: {r30['station_count']}역, {r30['sigungu_count']}개 시군구, "
              f"추정인구 {r30['est_pop']:,}명")
        print(f"  60분: {r60['station_count']}역, 추정인구 {r60['est_pop']:,}명 (30분 외삽)")
    except Exception as e:
        print(f"  오류: {e}")
        iso_pop[name] = {30: None, 60: None}

# ── Part 3: stats.json 갱신 ────────────────────────────────────────────────
print("\n== Part 3: stats.json 갱신 ==")
stats_path = os.path.join(DOCS_DATA, "stats.json")
with open(stats_path, encoding="utf-8") as f:
    stats = json.load(f)

def safe_get(d, t, field):
    if d.get(t) and isinstance(d[t], dict):
        return d[t].get(field)
    return None

stats["sociodemographics"] = {
    "note": (
        "집계구 경계 SHP 미보유로 구역 내 정밀 집계 불가. "
        "시군구 수준 통계(분당구.인천서구)를 사용. "
        "이소크론 인구는 역 소재 시군구 전체 인구 합산 상한 추정치."
    ),
    "data_year_pop": 2024,
    "data_year_worker": 2023,
    "pangyo": {
        "sigungu": "성남시 분당구",
        "sigungu_pop": pop_bundang,
        "sigungu_workers": wrk_bundang,
        "jjr_sigungu": jjr_bundang,
        "iso30_station_count": safe_get(iso_pop["pangyo"], 30, "station_count"),
        "iso30_sigungu_count": safe_get(iso_pop["pangyo"], 30, "sigungu_count"),
        "iso30_est_pop": safe_get(iso_pop["pangyo"], 30, "est_pop"),
        "iso60_station_count": safe_get(iso_pop["pangyo"], 60, "station_count"),
        "iso60_est_pop": safe_get(iso_pop["pangyo"], 60, "est_pop"),
    },
    "cheongna": {
        "sigungu": "인천광역시 서구",
        "sigungu_pop": pop_incheon,
        "sigungu_workers": wrk_incheon,
        "jjr_sigungu": jjr_incheon,
        "iso30_station_count": safe_get(iso_pop["cheongna"], 30, "station_count"),
        "iso30_sigungu_count": safe_get(iso_pop["cheongna"], 30, "sigungu_count"),
        "iso30_est_pop": safe_get(iso_pop["cheongna"], 30, "est_pop"),
        "iso60_station_count": safe_get(iso_pop["cheongna"], 60, "station_count"),
        "iso60_est_pop": safe_get(iso_pop["cheongna"], 60, "est_pop"),
    },
}

with open(stats_path, "w", encoding="utf-8") as f:
    json.dump(stats, f, ensure_ascii=False, indent=2)
shutil.copy(stats_path, os.path.join(PROCESSED, "stats.json"))

sd = stats["sociodemographics"]
print("완료 - sociodemographics 추가됨")
print(f"판교 - 분당구인구: {sd['pangyo']['sigungu_pop']:,}  "
      f"종사자: {sd['pangyo']['sigungu_workers']:,}  직주비: {sd['pangyo']['jjr_sigungu']}")
print(f"청라 - 서구인구: {sd['cheongna']['sigungu_pop']:,}  "
      f"종사자: {sd['cheongna']['sigungu_workers']:,}  직주비: {sd['cheongna']['jjr_sigungu']}")
p30 = sd['pangyo']['iso30_est_pop']
c30 = sd['cheongna']['iso30_est_pop']
if p30 and c30:
    print(f"\n30분 추정 도달가능 인구 - 판교: {p30:,}명  청라: {c30:,}명")
    print(f"판교/청라 비율: {p30/c30:.2f}배")
