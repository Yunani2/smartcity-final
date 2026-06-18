/* charts.js — Chart.js 통계 패널 및 접근성 곡선 */

async function initCharts() {
  const stats = await fetch("data/stats.json").then(r => r.json());
  const ac    = await fetch("data/accessibility_curve.json").then(r => r.json());

  const p = stats.land_use_buildings.pangyo;
  const c = stats.land_use_buildings.cheongna;
  const colors = stats.land_use_buildings.category_colors;

  // ── KPI 비교표 ────────────────────────────────────────────────────
  const kpiData = [
    ["구역 면적", stats.zone.pangyo.area_km2 + " km²", stats.zone.cheongna.area_km2 + " km²", "삼평동·청라동 법정동 기준"],
    ["건축물 수", p.building_count.toLocaleString() + "동", c.building_count.toLocaleString() + "동", "주건축물 기준"],
    ["총 연면적", (p.total_gfa_m2/1e6).toFixed(2) + " 백만㎡", (c.total_gfa_m2/1e6).toFixed(2) + " 백만㎡", ""],
    ["업무시설 연면적 비율", (p.use_ratio_pct["업무시설"]||0).toFixed(1) + "%",
                             (c.use_ratio_pct["업무시설"]||0).toFixed(1) + "%", "연면적 기준"],
    ["교육연구시설 비율", (p.use_ratio_pct["교육연구시설"]||0).toFixed(1) + "%",
                          (c.use_ratio_pct["교육연구시설"]||0).toFixed(1) + "%", ""],
    ["업무+연구 합계",
      ((p.use_ratio_pct["업무시설"]||0) + (p.use_ratio_pct["교육연구시설"]||0)).toFixed(1) + "%",
      ((c.use_ratio_pct["업무시설"]||0) + (c.use_ratio_pct["교육연구시설"]||0)).toFixed(1) + "%",
      "핵심 용도 합산"],
    ["주거 비율", (p.use_ratio_pct["주거"]||0).toFixed(1) + "%",
                  (c.use_ratio_pct["주거"]||0).toFixed(1) + "%", ""],
    ["LUM 엔트로피", p.lum_entropy.toFixed(4), c.lum_entropy.toFixed(4), "0=단일용도, 1=완전혼합"],
    ["평균 용적률", p.avg_far_pct.toFixed(1) + "%", c.avg_far_pct.toFixed(1) + "%", ""],
    ["30분 등시간권 역수", stats.transport.pangyo.isochrone_30min_stations + "개",
                           stats.transport.cheongna.isochrone_30min_stations + "개",
                           "판교역 / 청라국제도시역 기준"],
    ["60분 등시간권 역수", stats.transport.pangyo.isochrone_60min_stations + "개",
                           stats.transport.cheongna.isochrone_60min_stations + "개", ""],
  ];
  const tbody = document.getElementById("kpi-tbody");
  tbody.innerHTML = kpiData.map(([label, pv, cv, note]) =>
    `<tr><td>${label}</td><td><b>${pv}</b></td><td><b>${cv}</b></td><td style="color:#888;font-size:12px">${note}</td></tr>`
  ).join("");

  // ── 파이 차트 헬퍼 ────────────────────────────────────────────────
  function makePie(canvasId, useRatio) {
    const cats = Object.keys(useRatio).filter(k => useRatio[k] > 0);
    cats.sort((a, b) => useRatio[b] - useRatio[a]);
    return new Chart(document.getElementById(canvasId).getContext("2d"), {
      type: "pie",
      data: {
        labels: cats,
        datasets: [{
          data: cats.map(k => useRatio[k]),
          backgroundColor: cats.map(k => colors[k] || "#ccc"),
          borderWidth: 1, borderColor: "#fff"
        }]
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: {
          legend: { position: "right", labels: { font: { size: 11 }, boxWidth: 12 } },
          tooltip: {
            callbacks: {
              label: ctx => ` ${ctx.label}: ${ctx.raw.toFixed(1)}%`
            }
          }
        }
      }
    });
  }

  makePie("pie-pangyo",   p.use_ratio_pct);
  makePie("pie-cheongna", c.use_ratio_pct);

  // ── 막대 비교 차트 ─────────────────────────────────────────────────
  const barLabels = ["업무시설", "교육연구시설", "근린생활시설", "주거", "기타"];
  new Chart(document.getElementById("bar-compare").getContext("2d"), {
    type: "bar",
    data: {
      labels: barLabels,
      datasets: [
        {
          label: "판교테크노밸리",
          data: barLabels.map(k => p.use_ratio_pct[k] || 0),
          backgroundColor: "#2166ac", borderRadius: 4
        },
        {
          label: "청라국제업무지구",
          data: barLabels.map(k => c.use_ratio_pct[k] || 0),
          backgroundColor: "#c0392b", borderRadius: 4
        }
      ]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: {
        legend: { position: "top" },
        tooltip: { callbacks: { label: ctx => ` ${ctx.dataset.label}: ${ctx.raw.toFixed(1)}%` } }
      },
      scales: {
        y: { title: { display: true, text: "연면적 비율 (%)" }, beginAtZero: true, max: 60 },
        x: { title: { display: true, text: "건축물 주용도" } }
      }
    }
  });

  // ── 누적 접근성 곡선 ───────────────────────────────────────────────
  const curveP = ac.pangyo.curve;
  const curveC = ac.cheongna.curve;
  const timeLabels = curveP.map(d => d.time_min + "분");
  new Chart(document.getElementById("line-access").getContext("2d"), {
    type: "line",
    data: {
      labels: timeLabels,
      datasets: [
        {
          label: "판교역(신분당선) — 도달 역 수",
          data: curveP.map(d => d.station_count),
          borderColor: "#2166ac", backgroundColor: "rgba(33,102,172,0.1)",
          fill: true, tension: 0.3, pointRadius: 3
        },
        {
          label: "청라국제도시역(공항철도) — 도달 역 수",
          data: curveC.map(d => d.station_count),
          borderColor: "#c0392b", backgroundColor: "rgba(192,57,43,0.1)",
          fill: true, tension: 0.3, pointRadius: 3
        }
      ]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: {
        legend: { position: "top" },
        tooltip: { mode: "index", intersect: false }
      },
      scales: {
        y: { title: { display: true, text: "도달 가능 역 수 (개)" }, beginAtZero: true },
        x: { title: { display: true, text: "소요시간 (분)" } }
      }
    }
  });

  // ── 등시간권 역수 막대 ─────────────────────────────────────────────
  new Chart(document.getElementById("bar-iso").getContext("2d"), {
    type: "bar",
    data: {
      labels: ["30분 이내", "60분 이내"],
      datasets: [
        {
          label: "판교역",
          data: [stats.transport.pangyo.isochrone_30min_stations,
                 stats.transport.pangyo.isochrone_60min_stations],
          backgroundColor: "#2166ac", borderRadius: 4
        },
        {
          label: "청라국제도시역",
          data: [stats.transport.cheongna.isochrone_30min_stations,
                 stats.transport.cheongna.isochrone_60min_stations],
          backgroundColor: "#c0392b", borderRadius: 4
        }
      ]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { position: "top" } },
      scales: {
        y: { title: { display: true, text: "역 수 (개)" }, beginAtZero: true }
      }
    }
  });

  console.log("차트 초기화 완료");
}

initCharts().catch(e => console.error("차트 오류:", e));
