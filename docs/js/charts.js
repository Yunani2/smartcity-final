/* charts.js — 통계 패널 차트 & 비교표 */

const COL_P  = "#1d5fa8";
const COL_C  = "#b03030";
const COL_PA = "rgba(29,95,168,0.18)";
const COL_CA = "rgba(176,48,48,0.18)";

function fmt(n, unit = "") {
  if (n == null) return "—";
  return Number(n).toLocaleString() + (unit || "");
}
function pctFmt(n) {
  if (n == null) return "—";
  return Number(n).toFixed(1) + "%";
}

function baseOpts(opts = {}) {
  return {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { position: "bottom", labels: { font: { size: 11 }, boxWidth: 13, padding: 8 } },
      tooltip: { callbacks: { label: (ctx) => " " + ctx.dataset.label + ": " + ctx.raw } },
      ...opts.plugins,
    },
    ...opts
  };
}

async function initCharts() {
  const stats = await fetch("data/stats.json").then(r => r.json());

  const lu  = stats.land_use_buildings || {};
  const lz  = stats.land_use_zoning    || {};
  const p   = lu.pangyo   || {};
  const c   = lu.cheongna || {};
  const zp  = lz.pangyo   || {};
  const zc  = lz.cheongna || {};
  const tr  = stats.transport || {};
  const rd  = stats.road || {};
  const sd  = stats.sociodemographics || {};
  const sdP = sd.pangyo   || {};
  const sdC = sd.cheongna || {};
  const sar = stats.station_area_ratio || {};
  const dst = stats.station_distance   || {};

  // ──────────────────────────────────────────────────────────────────
  // 핵심 지표 비교표
  // ──────────────────────────────────────────────────────────────────
  const tbody = document.getElementById("kpi-tbody");
  const rows = [
    // 3-1 토지이용
    ["3-1", "구역 면적",           (stats.zone?.pangyo?.area_km2||"—")+" km²",  (stats.zone?.cheongna?.area_km2||"—")+" km²", "PROM 구역계"],
    ["3-1", "건축물 수",            fmt(p.building_count,"동"),              fmt(c.building_count,"동"),                "주건축물 기준"],
    ["3-1", "총 연면적",            ((p.total_gfa_m2||0)/1e6).toFixed(2)+" 백만㎡", ((c.total_gfa_m2||0)/1e6).toFixed(2)+" 백만㎡", ""],
    ["3-1", "업무시설 비율",        pctFmt(p.use_ratio_pct?.["업무시설"]),   pctFmt(c.use_ratio_pct?.["업무시설"]),   "연면적 기준"],
    ["3-1", "업무+교육연구 합계",   (((p.use_ratio_pct?.["업무시설"]||0)+(p.use_ratio_pct?.["교육연구시설"]||0)).toFixed(1))+"%",
                                   (((c.use_ratio_pct?.["업무시설"]||0)+(c.use_ratio_pct?.["교육연구시설"]||0)).toFixed(1))+"%", "핵심 업무 용도"],
    ["3-1", "토지이용 혼합도(LUM엔트로피)", p.lum_entropy?.toFixed(4)||"—", c.lum_entropy?.toFixed(4)||"—", "0=단일, 1=완전혼합"],
    ["3-1", "개발 실현 정도(평균 용적률)",  pctFmt(p.avg_far_pct),          pctFmt(c.avg_far_pct),          "연면적/대지면적"],
    ["3-1", "용도지역 주 지정 (면적 1위)", Object.entries(zp.uzone_ratio_pct||{}).sort((a,b)=>b[1]-a[1])[0]?.[0]||"—",
                                           Object.entries(zc.uzone_ratio_pct||{}).sort((a,b)=>b[1]-a[1])[0]?.[0]||"—", "PROM 용도지역"],
    // 3-2 교통망
    ["3-2", "30분권 도달 역수(지하철)",  fmt(tr.pangyo?.isochrone_30min_stations,"역"), fmt(tr.cheongna?.isochrone_30min_stations,"역"), "핵심역 기준"],
    ["3-2", "60분권 도달 역수(지하철)",  fmt(tr.pangyo?.isochrone_60min_stations,"역"), fmt(tr.cheongna?.isochrone_60min_stations,"역"), ""],
    ["3-2", "30분권 추정 총인구",        sdP.iso30_est_pop ? fmt(sdP.iso30_est_pop,"명"):"—",     sdC.iso30_est_pop ? fmt(sdC.iso30_est_pop,"명"):"—",     "집계구 공간조인 기반"],
    ["3-2", "30분권 추정 경제활동인구",  sdP.iso30_est_workers ? fmt(sdP.iso30_est_workers,"명"):"—", sdC.iso30_est_workers ? fmt(sdC.iso30_est_workers,"명"):"—", "노동시장 크기 지표"],
    ["3-2", "핵심역 위치",               dst.pangyo?.station_inside  ? "구역 내부" : "구역 외부", dst.cheongna?.station_inside ? "구역 내부" : "구역 외부", ""],
    ["3-2", "핵심역까지 거리(경계→역)",  dst.pangyo  ? (dst.pangyo.station_inside  ? "0m (내부)" : dst.pangyo.dist_boundary_m+"m")  : "—",
                                          dst.cheongna? (dst.cheongna.station_inside ? "0m (내부)" : dst.cheongna.dist_boundary_m+"m") : "—", "직선, EPSG:5179"],
    ["3-2", "차량도로 밀도",     rd.pangyo ? rd.pangyo.drive_density_km_km2.toFixed(1)+" km/km²":"—",  rd.cheongna ? rd.cheongna.drive_density_km_km2.toFixed(1)+" km/km²":"—",  "OSM"],
    ["3-2", "보행도로 밀도",     rd.pangyo ? rd.pangyo.walk_density_km_km2.toFixed(1)+" km/km²":"—",   rd.cheongna ? rd.cheongna.walk_density_km_km2.toFixed(1)+" km/km²":"—",   "OSM"],
    // 3-3 인구사회
    ["3-3", "구역 내 상주인구",  sdP.zone_pop != null ? fmt(sdP.zone_pop,"명") : "—",  sdC.zone_pop != null ? fmt(sdC.zone_pop,"명") : "—",  "집계구 합산 2024년"],
    ["3-3", "구역 내 사업체수",  sdP.total_businesses_zone != null ? fmt(sdP.total_businesses_zone,"개") : "—", sdC.total_businesses_zone != null ? fmt(sdC.total_businesses_zone,"개") : "—", "집계구 합산 2023년"],
    ["3-3", "시군구 상주인구",   fmt(sdP.sigungu_pop,"명"),     fmt(sdC.sigungu_pop,"명"),     "분당구/인천서구 2024년"],
    ["3-3", "시군구 종사자수",   fmt(sdP.sigungu_workers,"명"), fmt(sdC.sigungu_workers,"명"), "2023년"],
    ["3-3", "직주비",            sdP.jjr_sigungu?.toFixed(3)||"—", sdC.jjr_sigungu?.toFixed(3)||"—", "종사자/상주인구(시군구)"],
    ["3-3", "정보통신업 비율",   pctFmt((sdP.biz_by_industry_zone||sdP.biz_by_industry||{})["정보통신업"]),   pctFmt((sdC.biz_by_industry_zone||sdC.biz_by_industry||{})["정보통신업"]),   "구역 내 사업체"],
    ["3-3", "전문·과학·기술서비스업", pctFmt((sdP.biz_by_industry_zone||sdP.biz_by_industry||{})["전문·과학·기술서비스업"]), pctFmt((sdC.biz_by_industry_zone||sdC.biz_by_industry||{})["전문·과학·기술서비스업"]), "구역 내 사업체"],
    ["3-3", "제조업 비율",       pctFmt((sdP.biz_by_industry_zone||sdP.biz_by_industry||{})["제조업"]),       pctFmt((sdC.biz_by_industry_zone||sdC.biz_by_industry||{})["제조업"]),       "구역 내 사업체"],
  ];

  if (tbody) {
    tbody.innerHTML = rows.map(([sec, label, pv, cv, note]) => `
      <tr>
        <td class="td-note">${sec}</td>
        <td>${label}</td>
        <td class="td-p">${pv}</td>
        <td class="td-c">${cv}</td>
        <td class="td-note">${note}</td>
      </tr>`).join("");
  }

  // ──────────────────────────────────────────────────────────────────
  // 핵심역 정보 & 접근성 수치 채우기
  // ──────────────────────────────────────────────────────────────────
  const fillEl = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };
  fillEl("acc-p30",   fmt(tr.pangyo?.isochrone_30min_stations,  "역"));
  fillEl("acc-c30",   fmt(tr.cheongna?.isochrone_30min_stations,"역"));
  fillEl("acc-p60",   fmt(tr.pangyo?.isochrone_60min_stations,  "역"));
  fillEl("acc-c60",   fmt(tr.cheongna?.isochrone_60min_stations,"역"));
  fillEl("acc-pp30",  sdP.iso30_est_pop ? fmt(sdP.iso30_est_pop,"명") : "—");
  fillEl("acc-cp30",  sdC.iso30_est_pop ? fmt(sdC.iso30_est_pop,"명") : "—");
  fillEl("acc-ppw30", sdP.iso30_est_workers ? fmt(sdP.iso30_est_workers,"명") : "—");
  fillEl("acc-cpw30", sdC.iso30_est_workers ? fmt(sdC.iso30_est_workers,"명") : "—");
  fillEl("meta-area-p",  (stats.zone?.pangyo?.area_km2||"—") + " km²");
  fillEl("meta-area-c",  (stats.zone?.cheongna?.area_km2||"—") + " km²");
  fillEl("meta-bldg-p",  fmt(p.building_count, "동"));
  fillEl("meta-bldg-c",  fmt(c.building_count, "동"));

  // ──────────────────────────────────────────────────────────────────
  // 3-1 수치 카드
  // ──────────────────────────────────────────────────────────────────
  fillEl("m-lum-p", p.lum_entropy != null ? p.lum_entropy.toFixed(4) : "—");
  fillEl("m-lum-c", c.lum_entropy != null ? c.lum_entropy.toFixed(4) : "—");
  fillEl("m-far-p", p.avg_far_pct != null ? p.avg_far_pct.toFixed(1) + "%" : "—");
  fillEl("m-far-c", c.avg_far_pct != null ? c.avg_far_pct.toFixed(1) + "%" : "—");
  fillEl("m-wk-p", (((p.use_ratio_pct?.["업무시설"]||0)+(p.use_ratio_pct?.["교육연구시설"]||0)).toFixed(1)) + "%");
  fillEl("m-wk-c", (((c.use_ratio_pct?.["업무시설"]||0)+(c.use_ratio_pct?.["교육연구시설"]||0)).toFixed(1)) + "%");

  const topZP = Object.entries(zp.uzone_ratio_pct||{}).sort((a,b)=>b[1]-a[1])[0];
  const topZC = Object.entries(zc.uzone_ratio_pct||{}).sort((a,b)=>b[1]-a[1])[0];
  fillEl("m-zone-p",  topZP ? topZP[0] : "—");
  fillEl("m-zone-pp", topZP ? "판교 " + topZP[1].toFixed(1) + "%" : "—");
  fillEl("m-zone-c",  topZC ? topZC[0] : "—");
  fillEl("m-zone-cp", topZC ? "청라 " + topZC[1].toFixed(1) + "%" : "—");

  // ──────────────────────────────────────────────────────────────────
  // 3-3 수치 카드
  // ──────────────────────────────────────────────────────────────────
  fillEl("m-pop-p", sdP.zone_pop != null ? fmt(sdP.zone_pop, "명") : "—");
  fillEl("m-pop-c", sdC.zone_pop != null ? fmt(sdC.zone_pop, "명") : "—");
  fillEl("m-hh-p",  sdP.zone_households != null ? fmt(sdP.zone_households, "가구") : "—");
  fillEl("m-hh-c",  sdC.zone_households != null ? fmt(sdC.zone_households, "가구") : "—");
  fillEl("m-biz-p", sdP.total_businesses_zone != null ? fmt(sdP.total_businesses_zone, "개") : "—");
  fillEl("m-biz-c", sdC.total_businesses_zone != null ? fmt(sdC.total_businesses_zone, "개") : "—");
  fillEl("m-jjr-p", sdP.jjr_sigungu != null ? sdP.jjr_sigungu.toFixed(3) : "—");
  fillEl("m-jjr-c", sdC.jjr_sigungu != null ? sdC.jjr_sigungu.toFixed(3) : "—");

  // ──────────────────────────────────────────────────────────────────
  // 용도지역 구성비
  // ──────────────────────────────────────────────────────────────────
  const ZONE_COLORS_CHART = {
    "중심상업지역":"#d73027","일반상업지역":"#fc8d59","유통상업지역":"#fee08b",
    "준주거지역":"#74c476","제3종일반주거지역":"#a1d99b","제2종일반주거지역":"#c7e9c0",
    "제1종일반주거지역":"#e5f5e0","제2종전용주거지역":"#d9f0a3","제1종전용주거지역":"#f7fcb9",
    "준공업지역":"#9e9ac8","일반공업지역":"#756bb1",
    "보전녹지지역":"#238b45","생산녹지지역":"#41ab5d","자연녹지지역":"#74c476",
    "계획관리지역":"#cccccc","도시지역미지정":"#f0f0f0",
  };

  function makePieZone(canvasId, ratioDict) {
    const ctx = document.getElementById(canvasId);
    if (!ctx || !ratioDict) return;
    const labels = Object.keys(ratioDict).filter(k => (ratioDict[k]||0) >= 0.5).sort((a,b)=>ratioDict[b]-ratioDict[a]);
    const data   = labels.map(k => ratioDict[k]);
    const colors = labels.map(k => ZONE_COLORS_CHART[k] || "#ccc");
    new Chart(ctx, {
      type: "doughnut",
      data: { labels, datasets: [{ data, backgroundColor: colors, borderWidth: 1, borderColor: "#fff" }] },
      options: baseOpts({
        plugins: {
          legend: { position: "right", labels: { font: { size: 10 }, boxWidth: 11 } },
          tooltip: { callbacks: { label: ctx => ` ${ctx.label}: ${ctx.raw}%` } },
        },
        cutout: "50%"
      })
    });
  }
  makePieZone("pie-zone-p", zp.uzone_ratio_pct);
  makePieZone("pie-zone-c", zc.uzone_ratio_pct);

  // 용도지역 나란히 비교 막대
  (function() {
    const ctx = document.getElementById("bar-zone");
    if (!ctx) return;
    const allZones = Array.from(new Set([
      ...Object.keys(zp.uzone_ratio_pct||{}),
      ...Object.keys(zc.uzone_ratio_pct||{})
    ])).filter(k => ((zp.uzone_ratio_pct||{})[k]||0) + ((zc.uzone_ratio_pct||{})[k]||0) >= 1)
      .sort((a,b) => (zp.uzone_ratio_pct||{})[b] - (zp.uzone_ratio_pct||{})[a]);

    new Chart(ctx, {
      type: "bar",
      data: {
        labels: allZones,
        datasets: [
          { label: "판교테크노밸리", data: allZones.map(k => (zp.uzone_ratio_pct||{})[k]||0), backgroundColor: COL_P+"cc" },
          { label: "청라국제업무지구", data: allZones.map(k => (zc.uzone_ratio_pct||{})[k]||0), backgroundColor: COL_C+"cc" },
        ]
      },
      options: baseOpts({
        indexAxis: "y",
        scales: {
          x: { title: { display: true, text: "면적 비율 (%)", font: { size: 11 } }, max: 100 },
          y: { ticks: { font: { size: 10 } } }
        },
        plugins: {
          tooltip: { callbacks: { label: ctx => ` ${ctx.dataset.label}: ${ctx.raw}%` } },
          legend: { position: "bottom" }
        }
      })
    });
  })();

  // ──────────────────────────────────────────────────────────────────
  // 건축물 주용도 구성비
  // ──────────────────────────────────────────────────────────────────
  const USE_COLORS = {
    "업무시설":"#2166ac","교육연구시설":"#4dac26","근린생활시설":"#f4a582",
    "주거":"#d6604d","판매시설":"#fdae61","운수시설":"#9e9ac8",
    "공장·창고":"#762a83","기타":"#aaaaaa"
  };

  function makePie(canvasId, ratioDict) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;
    const labels = Object.keys(ratioDict).filter(k => (ratioDict[k]||0) > 0);
    const data   = labels.map(k => ratioDict[k]);
    const colors = labels.map(k => USE_COLORS[k] || "#ccc");
    new Chart(ctx, {
      type: "doughnut",
      data: { labels, datasets: [{ data, backgroundColor: colors, borderWidth: 1, borderColor: "#fff" }] },
      options: baseOpts({
        plugins: {
          legend: { position: "right", labels: { font: { size: 10 }, boxWidth: 11 } },
          tooltip: { callbacks: { label: ctx => ` ${ctx.label}: ${ctx.raw}%` } },
        },
        cutout: "50%"
      })
    });
  }
  makePie("pie-pangyo",   p.use_ratio_pct || {});
  makePie("pie-cheongna", c.use_ratio_pct || {});

  // 건축물 주용도 나란히 막대
  (function() {
    const ctx = document.getElementById("bar-use");
    if (!ctx) return;
    const allCats = Object.keys(USE_COLORS);
    const pVals = allCats.map(k => p.use_ratio_pct?.[k] || 0);
    const cVals = allCats.map(k => c.use_ratio_pct?.[k] || 0);
    new Chart(ctx, {
      type: "bar",
      data: {
        labels: allCats,
        datasets: [
          { label: "판교테크노밸리", data: pVals, backgroundColor: COL_P + "cc", borderColor: COL_P, borderWidth: 1 },
          { label: "청라국제업무지구", data: cVals, backgroundColor: COL_C + "cc", borderColor: COL_C, borderWidth: 1 },
        ]
      },
      options: baseOpts({
        indexAxis: "y",
        scales: {
          x: { title: { display: true, text: "연면적 비율 (%)", font: { size: 11 } }, max: 100 },
          y: { ticks: { font: { size: 11 } } }
        },
        plugins: {
          tooltip: { callbacks: { label: ctx => ` ${ctx.dataset.label}: ${ctx.raw}%` } },
          legend: { position: "bottom" }
        }
      })
    });
  })();

  // ──────────────────────────────────────────────────────────────────
  // 누적 접근성 곡선
  // ──────────────────────────────────────────────────────────────────
  (function() {
    const ctx = document.getElementById("line-access");
    if (!ctx) return;
    const accP = stats.accessibility_curve?.pangyo   || [];
    const accC = stats.accessibility_curve?.cheongna || [];
    const labels = accP.map(d => d.time_min);
    new Chart(ctx, {
      type: "line",
      data: {
        labels,
        datasets: [
          { label: "판교역(신분당선)", data: accP.map(d => d.station_count),
            borderColor: COL_P, backgroundColor: COL_PA, fill: true, tension: 0.3, pointRadius: 3, borderWidth: 2 },
          { label: "청라국제도시역(공항철도)", data: accC.map(d => d.station_count),
            borderColor: COL_C, backgroundColor: COL_CA, fill: true, tension: 0.3, pointRadius: 3, borderWidth: 2 },
        ]
      },
      options: baseOpts({
        scales: {
          x: { title: { display: true, text: "소요 시간 (분) — 지하철 네트워크 기반", font: { size: 11 } } },
          y: { title: { display: true, text: "누적 도달 역 수", font: { size: 11 } }, beginAtZero: true }
        },
        plugins: {
          tooltip: { callbacks: { label: ctx => ` ${ctx.dataset.label}: ${ctx.raw}역` } },
          legend: { position: "bottom" }
        }
      })
    });
  })();

  // 등시간권 역수 막대
  (function() {
    const ctx = document.getElementById("bar-iso");
    if (!ctx) return;
    new Chart(ctx, {
      type: "bar",
      data: {
        labels: ["30분권", "60분권"],
        datasets: [
          { label: "판교", data: [tr.pangyo?.isochrone_30min_stations, tr.pangyo?.isochrone_60min_stations],
            backgroundColor: [COL_P + "bb", COL_P + "88"] },
          { label: "청라", data: [tr.cheongna?.isochrone_30min_stations, tr.cheongna?.isochrone_60min_stations],
            backgroundColor: [COL_C + "bb", COL_C + "88"] },
        ]
      },
      options: baseOpts({
        scales: { y: { beginAtZero: true, title: { display: true, text: "도달 역 수", font: { size: 11 } } } },
        plugins: {
          tooltip: { callbacks: { label: ctx => ` ${ctx.dataset.label}: ${ctx.raw}역` } },
          legend: { position: "bottom" }
        }
      })
    });
  })();

  // 30분권 인구·경제활동인구
  (function() {
    const ctx = document.getElementById("bar-iso-pop");
    if (!ctx) return;
    new Chart(ctx, {
      type: "bar",
      data: {
        labels: ["추정 총인구", "추정 경제활동인구"],
        datasets: [
          { label: "판교", data: [sdP.iso30_est_pop||0, sdP.iso30_est_workers||0], backgroundColor: COL_P+"cc" },
          { label: "청라", data: [sdC.iso30_est_pop||0, sdC.iso30_est_workers||0], backgroundColor: COL_C+"cc" },
        ]
      },
      options: baseOpts({
        indexAxis: "y",
        scales: { x: { beginAtZero: true, ticks: { callback: v => (v/10000).toFixed(0)+"만" } } },
        plugins: {
          tooltip: { callbacks: { label: ctx => ` ${ctx.dataset.label}: ${fmt(ctx.raw,"명")}` } },
          legend: { position: "bottom" }
        }
      })
    });
  })();

  // 도로망 밀도
  (function() {
    const ctx = document.getElementById("bar-road");
    if (!ctx) return;
    new Chart(ctx, {
      type: "bar",
      data: {
        labels: ["차량도로", "보행도로"],
        datasets: [
          { label: "판교", data: [rd.pangyo?.drive_density_km_km2, rd.pangyo?.walk_density_km_km2], backgroundColor: COL_P+"cc" },
          { label: "청라", data: [rd.cheongna?.drive_density_km_km2, rd.cheongna?.walk_density_km_km2], backgroundColor: COL_C+"cc" },
        ]
      },
      options: baseOpts({
        scales: { y: { beginAtZero: true, title: { display: true, text: "km/km²", font: { size: 11 } } } },
        plugins: {
          tooltip: { callbacks: { label: ctx => ` ${ctx.dataset.label}: ${ctx.raw} km/km²` } },
          legend: { position: "bottom" }
        }
      })
    });
  })();

  // 직주비
  (function() {
    const ctx = document.getElementById("bar-jjr");
    if (!ctx) return;
    new Chart(ctx, {
      type: "bar",
      data: {
        labels: ["판교 (분당구)", "청라 (인천서구)"],
        datasets: [{
          label: "직주비 (종사자/상주인구)",
          data: [sdP.jjr_sigungu||0, sdC.jjr_sigungu||0],
          backgroundColor: [COL_P+"cc", COL_C+"cc"],
          borderColor: [COL_P, COL_C],
          borderWidth: 1,
        }]
      },
      options: baseOpts({
        scales: {
          y: { beginAtZero: true, title: { display: true, text: "직주비", font: { size: 11 } },
               ticks: { callback: v => v.toFixed(2) } }
        },
        plugins: {
          legend: { display: false },
          tooltip: { callbacks: { label: ctx => ` 직주비: ${ctx.raw.toFixed(3)}` } },
          annotation: {
            annotations: {
              line1: { type: "line", yMin: 1, yMax: 1, borderColor: "#888", borderWidth: 1.5, borderDash: [5,4],
                        label: { display: true, content: "균형(1.0)", font: { size: 10 }, position: "end", backgroundColor: "rgba(0,0,0,.5)", color: "#fff" } }
            }
          }
        }
      })
    });
  })();

  // 업종별 사업체 구성비 — 구역 내 집계구 기반 (10차 대분류)
  (function() {
    const ctx = document.getElementById("bar-biz-ind");
    if (!ctx) return;
    const pBiz = sdP.biz_by_industry_zone || sdP.biz_by_industry || {};
    const cBiz = sdC.biz_by_industry_zone || sdC.biz_by_industry || {};
    const cats = [
      "도소매업","숙박·음식점업","교육서비스업","보건·사회복지",
      "전문·과학·기술서비스업","정보통신업","부동산업",
      "사업지원서비스업","건설업","제조업","운수·창고업",
    ];

    const hasZone = !!sdP.biz_by_industry_zone;
    const suffix = hasZone ? "(구역 내)" : "(시군구)";

    new Chart(ctx, {
      type: "bar",
      data: {
        labels: cats,
        datasets: [
          { label: `판교 ${suffix}`,   data: cats.map(k => pBiz[k]||0), backgroundColor: COL_P+"cc" },
          { label: `청라 ${suffix}`,   data: cats.map(k => cBiz[k]||0), backgroundColor: COL_C+"cc" },
        ]
      },
      options: baseOpts({
        indexAxis: "y",
        scales: {
          x: { beginAtZero: true, title: { display: true, text: "비율 (%)", font: { size: 11 } } },
          y: { ticks: { font: { size: 10 } } }
        },
        plugins: {
          tooltip: { callbacks: { label: ctx => ` ${ctx.dataset.label}: ${ctx.raw}%` } },
          legend: { position: "bottom" }
        }
      })
    });
  })();
}

initCharts().catch(e => console.error("차트 초기화 오류:", e));
