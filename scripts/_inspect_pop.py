import zipfile, io, pandas as pd, sys
sys.stdout.reconfigure(encoding="utf-8")

BASE = r"C:\Users\nanna\OneDrive\바탕 화면\2026 스마트시티학과\스시론\기말 과제"

for region, fname in [("서울", "집계구 인구통계_서울.zip"),
                       ("경기", "집계구 인구통계_경기.zip"),
                       ("인천", "집계구 인구통계_인천.zip")]:
    zp = BASE + "\\" + fname
    with zipfile.ZipFile(zp) as z:
        names = z.namelist()
        # 총인구 파일 우선
        entry = next((n for n in names if "총인구" in n), None)
        if entry is None:
            entry = names[0]
        print(f"\n[{region}] 선택 파일: {entry}")
        with z.open(entry) as f:
            raw = f.read()

    for enc in ("euc-kr", "cp949", "utf-8-sig"):
        try:
            df = pd.read_csv(io.BytesIO(raw), encoding=enc, header=None)
            print(f"  shape: {df.shape}")
            print(f"  첫 3행:\n{df.head(3)}")
            print(f"  col[2] unique[:5]: {df[2].unique()[:5].tolist()}")
            # OA 한 개 합계
            sample = df[1].iloc[0]
            subset = df[df[1] == sample]
            total = pd.to_numeric(subset[3], errors='coerce').sum()
            print(f"  샘플 OA '{sample}' 행수: {len(subset)}, 합계: {total}")
            break
        except Exception as e:
            print(f"  에러: {e}")
