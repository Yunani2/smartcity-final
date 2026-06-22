/* main.js — Leaflet 지도 초기화·레이어 관리·이소크론 슬라이더 */

const USE_COLORS = {
  "업무시설":     "#2166ac",
  "교육연구시설": "#4dac26",
  "근린생활시설": "#f4a582",
  "주거":         "#d6604d",
  "판매시설":     "#fdae61",
  "운수시설":     "#9e9ac8",
  "공장·창고":    "#762a83",
  "기타":         "#aaaaaa",
};

const ZONE_COLORS = {
  "중심상업지역":       "#d73027",
  "일반상업지역":       "#fc8d59",
  "유통상업지역":       "#fee08b",
  "근린상업지역":       "#fdae61",
  "준주거지역":         "#74c476",
  "제3종일반주거지역":  "#a1d99b",
  "제2종일반주거지역":  "#c7e9c0",
  "제1종일반주거지역":  "#e5f5e0",
  "제2종전용주거지역":  "#d9f0a3",
  "제1종전용주거지역":  "#f7fcb9",
  "준공업지역":         "#9e9ac8",
  "일반공업지역":       "#756bb1",
  "보전녹지지역":       "#238b45",
  "생산녹지지역":       "#41ab5d",
  "자연녹지지역":       "#74c476",
  "계획관리지역":       "#cccccc",
  "도시지역미지정":     "#f0f0f0",
};

function renderBldgLegend() {
  const el = document.getElementById("sb-legend-bldg");
  if (!el) return;
  el.innerHTML = Object.entries(USE_COLORS).map(([k, v]) =>
    `<div class="sb-legend-item">
      <span class="sb-legend-dot" style="background:${v}"></span>
      <span>${k}</span>
    </div>`
  ).join("");
}

function renderZoningLegend(zoningP, zoningC) {
  const el = document.getElementById("sb-legend-zoning");
  if (!el) return;
  const usedZones = new Set();
  [zoningP, zoningC].forEach(fc => {
    if (!fc) return;
    fc.features.forEach(f => {
      const nm = f.properties?.uzone_nm;
      if (nm) usedZones.add(nm);
    });
  });
  const orderedZones = Object.keys(ZONE_COLORS).filter(k => usedZones.has(k));
  if (orderedZones.length === 0) {
    el.innerHTML = '<div style="font-size:10.5px;color:#8491aa">데이터 없음</div>';
    return;
  }
  el.innerHTML = orderedZones.map(k =>
    `<div class="sb-legend-item">
      <span class="sb-legend-dot" style="background:${ZONE_COLORS[k]}"></span>
      <span>${k}</span>
    </div>`
  ).join("");
}

renderBldgLegend();

async function loadGeoJSON(url) {
  const r = await fetch(url, { cache: "no-store" });
  if (!r.ok) throw new Error(`${url} 로드 실패`);
  return r.json();
}

function fmt(n, unit = "") {
  if (n == null || n === undefined) return "—";
  return Number(n).toLocaleString() + unit;
}

function bldgStyle(feat) {
  const cat = feat.properties.use_class || "기타";
  return { fillColor: USE_COLORS[cat] || "#aaa", color: "#fff", weight: 0.7, fillOpacity: 0.85, opacity: 1 };
}

function zoningStyle(feat) {
  const nm = feat.properties?.uzone_nm || "";
  const clr = ZONE_COLORS[nm] || feat.properties?.color || "#cccccc";
  return { fillColor: clr, color: "#fff", weight: 0.6, fillOpacity: 0.72, opacity: 1 };
}

function bldgPopup(feat) {
  const p = feat.properties;
  const rows = [
    ["건물명",   p.bd_nm || "-"],
    ["주용도",   p.mn_use_nm || "-"],
    ["용도분류", p.use_class || "-"],
    ["대지면적", p.land_ar ? fmt(Math.round(Number(p.land_ar))) + " ㎡" : "-"],
    ["연면적",   p.tot_fl_ar ? fmt(Math.round(Number(p.tot_fl_ar))) + " ㎡" : "-"],
    ["용적률",   p.fl_ar_ratio ? Number(p.fl_ar_ratio).toFixed(1) + " %" : "-"],
    ["지상층수", p.gr_fl_num ? p.gr_fl_num + "층" : "-"],
  ];
  return `<div class="popup-title">${p.bd_nm || "건축물"}</div>` +
    rows.map(([l, v]) =>
      `<div class="popup-row"><span class="popup-label">${l}</span><span class="popup-val">${v}</span></div>`
    ).join("");
}

function isoPopup(feat, stationName) {
  const t = feat.properties.time_min;
  const sc = feat.properties.station_count;
  return `<div class="popup-title">${stationName}</div>
    <div class="popup-row"><span class="popup-label">등시간권</span><span class="popup-val">${t}분 이내 (지하철)</span></div>
    <div class="popup-row"><span class="popup-label">도달 역 수</span><span class="popup-val">${sc}개</span></div>`;
}

function roadStyle(feat) {
  const hw = String(feat.properties?.highway || "");
  if (["motorway","trunk","primary"].includes(hw))
    return { color: "#b44000", weight: 3.5, opacity: .85 };
  if (["secondary","tertiary"].includes(hw))
    return { color: "#0055aa", weight: 2.2, opacity: .78 };
  if (["residential","living_street","unclassified"].includes(hw))
    return { color: "#444", weight: 1.5, opacity: .7 };
  return { color: "#666", weight: 1, opacity: .6 };
}

/* 도달역 원형 마커 (작고 깔끔하게) */
function makeStationDot(timeBucket) {
  const color = timeBucket <= 30 ? "#1a54a0" : "#e67e22";
  const size  = timeBucket <= 30 ? 10 : 8;
  return L.divIcon({
    className: "",
    html: `<div style="width:${size}px;height:${size}px;border-radius:50%;
             background:${color};border:1.5px solid #fff;
             box-shadow:0 1px 4px rgba(0,0,0,.3)"></div>`,
    iconSize: [size, size],
    iconAnchor: [size/2, size/2],
    popupAnchor: [0, -size/2 - 2],
  });
}

/* 핵심역 핀 마커 */
function makeCoreIcon(color) {
  return L.divIcon({
    className: "",
    html: `<div style="position:relative;width:42px;height:50px">
      <div style="
        width:38px;height:38px;border-radius:50% 50% 50% 0;
        transform:rotate(-45deg);background:${color};
        border:3px solid #fff;box-shadow:0 4px 14px rgba(0,0,0,.5);
        position:absolute;top:0;left:0
      "></div>
      <span style="position:absolute;top:5px;left:6px;font-size:18px;line-height:1;">🚉</span>
    </div>`,
    iconSize: [42, 50],
    iconAnchor: [20, 50],
    popupAnchor: [0, -52],
  });
}

/* ── 이소크론 로직 ─────────────────────────────────────────────── */
const ISO_TIMES  = [5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60];
let _isoLayers   = {};   // { "P5": L.geoJSON, "P10": ..., "C5": ..., ... }
let _isoStats    = {};   // statsJson.sociodemographics
let _curIsoMin   = 30;

/* iso_timeseries 배열에서 time_min 매칭 검색 */
function _tsFind(region, min) {
  const ts = _isoStats[region]?.iso_timeseries || [];
  return ts.find(r => r.time_min === min) || null;
}

function updateIsoTime(min, mapP, mapC) {
  _curIsoMin = min;

  // 슬라이더 + 프리셋 UI
  const slider = document.getElementById("iso-slider");
  const curVal = document.getElementById("iso-cur-val");
  if (slider) {
    slider.value = min;
    const pct = ((min - 5) / 55) * 100;
    slider.style.background =
      `linear-gradient(to right,var(--p) ${pct}%,var(--gray3) ${pct}%)`;
  }
  if (curVal) curVal.textContent = min;

  document.querySelectorAll(".iso-preset").forEach(btn => {
    btn.classList.toggle("active", Number(btn.dataset.val) === min);
  });

  // 이소크론 레이어: 선택된 시간의 레이어만 ON, 나머지 OFF
  ISO_TIMES.forEach(t => {
    ["P", "C"].forEach(prefix => {
      const key   = prefix + t;
      const layer = _isoLayers[key];
      const map   = prefix === "P" ? mapP : mapC;
      if (!layer) return;
      if (t === min) { if (!map.hasLayer(layer)) map.addLayer(layer); }
      else           { if (map.hasLayer(layer))  map.removeLayer(layer); }
    });
  });

  // 오버레이 채우기 — iso_timeseries 우선, fallback으로 30/60 레거시키
  const label = min + "분권 등시간권";
  const fillEl = (id, v) => { const e = document.getElementById(id); if (e) e.textContent = v; };

  function getVals(region) {
    const ts = _tsFind(region, min);
    if (ts) return { sta: ts.station_count, pop: ts.population, wrk: ts.workers };
    // fallback: 가장 가까운 레거시 값
    const sd = _isoStats[region] || {};
    const pop = min <= 30 ? sd.iso30_est_pop    : sd.iso60_est_pop;
    const wrk = min <= 30 ? sd.iso30_est_workers : sd.iso60_est_workers;
    const sta = min <= 30 ? sd.iso30_station_count : sd.iso60_station_count;
    return { sta: sta || 0, pop: pop || 0, wrk: wrk || 0 };
  }

  const vP = getVals("pangyo");
  const vC = getVals("cheongna");

  fillEl("iso-time-p", label);
  fillEl("ip-sta",  fmt(vP.sta, "역"));
  fillEl("ip-pop",  vP.pop ? fmt(vP.pop, "명") : "—");
  fillEl("ip-wrk",  vP.wrk ? fmt(vP.wrk, "명") : "—");

  fillEl("iso-time-c", label);
  fillEl("ic-sta",  fmt(vC.sta, "역"));
  fillEl("ic-pop",  vC.pop ? fmt(vC.pop, "명") : "—");
  fillEl("ic-wrk",  vC.wrk ? fmt(vC.wrk, "명") : "—");
}

/* ── 메인 초기화 ──────────────────────────────────────────────────── */
async function initMaps() {
  const mapP = L.map("map-pangyo",   { zoomControl: true }).setView([37.404, 127.105], 15);
  const mapC = L.map("map-cheongna", { zoomControl: true }).setView([37.534, 126.620], 14);
  window.mapPangyo   = mapP;
  window.mapCheongna = mapC;

  const tileOpts = { attribution: "© OpenStreetMap contributors", maxZoom: 19 };
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", tileOpts).addTo(mapP);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", tileOpts).addTo(mapC);

  const [zoneP, zoneC, bldgP, bldgC, isoRawP, isoRawC, statsJson, accJson] = await Promise.all([
    loadGeoJSON("data/pangyo_zone.geojson"),
    loadGeoJSON("data/cheongna_zone.geojson"),
    loadGeoJSON("data/pangyo_buildings.geojson"),
    loadGeoJSON("data/cheongna_buildings.geojson"),
    loadGeoJSON("data/pangyo_isochrone.geojson"),
    loadGeoJSON("data/cheongna_isochrone.geojson"),
    loadGeoJSON("data/stats.json"),
    loadGeoJSON("data/accessibility_curve.json"),
  ]);

  _isoStats = statsJson.sociodemographics || {};

  // 도달역 데이터 (실패 허용)
  let statP = null, statC = null;
  try { statP = await loadGeoJSON("data/pangyo_stations_reach.geojson");   } catch(e) {}
  try { statC = await loadGeoJSON("data/cheongna_stations_reach.geojson"); } catch(e) {}

  let zoningP = null, zoningC = null;
  try { zoningP = await loadGeoJSON("data/pangyo_zoning.geojson");   } catch(e) {}
  try { zoningC = await loadGeoJSON("data/cheongna_zoning.geojson"); } catch(e) {}

  let roadP = null, roadC = null;
  try { roadP = await loadGeoJSON("data/pangyo_roads.geojson");   } catch(e) {}
  try { roadC = await loadGeoJSON("data/cheongna_roads.geojson"); } catch(e) {}

  renderZoningLegend(zoningP, zoningC);

  // 구역 경계
  const zoneStyleDef = { color: "#0c2a5e", weight: 2.5, fillOpacity: 0, dashArray: "7 4" };
  L.geoJSON(zoneP, { style: zoneStyleDef }).addTo(mapP);
  L.geoJSON(zoneC, { style: zoneStyleDef }).addTo(mapC);

  // 용도지역 (기본 ON)
  const zoningOpts = {
    style: zoningStyle,
    onEachFeature: (f, layer) => {
      const nm = f.properties?.uzone_nm || "—";
      layer.bindTooltip(nm, { sticky: true });
      layer.bindPopup(`<div class="popup-title">용도지역</div>
        <div class="popup-row"><span class="popup-label">지역명</span><span class="popup-val">${nm}</span></div>`);
    }
  };
  const layerZoningP = zoningP ? L.geoJSON(zoningP, zoningOpts).addTo(mapP) : null;
  const layerZoningC = zoningC ? L.geoJSON(zoningC, zoningOpts).addTo(mapC) : null;

  // 건축물 (기본 ON)
  function makeBldgLayer(geojson, map) {
    let ref;
    ref = L.geoJSON(geojson, {
      style: bldgStyle,
      onEachFeature: (f, layer) => {
        layer.bindPopup(bldgPopup(f), { maxWidth: 270 });
        layer.on("mouseover", function() { this.setStyle({ weight: 2.5, color: "#333", fillOpacity: 1 }); });
        layer.on("mouseout",  function() { ref.resetStyle(this); });
      }
    }).addTo(map);
    return ref;
  }
  const bldgLayer  = makeBldgLayer(bldgP, mapP);
  const bldgLayerC = makeBldgLayer(bldgC, mapC);

  // 도로 (기본 OFF)
  const roadOpts = {
    style: roadStyle,
    onEachFeature: (f, layer) => {
      const p = f.properties || {};
      layer.bindTooltip(`${p.name || "도로"} · ${p.highway || ""}`, { sticky: true });
    }
  };
  const layerRoadP = roadP ? L.geoJSON(roadP, roadOpts) : null;
  const layerRoadC = roadC ? L.geoJSON(roadC, roadOpts) : null;

  // 도달역 마커 (기본 OFF — 작은 원형 dot + 역명 팝업)
  const stOpts = {
    pointToLayer: (f, ll) => {
      const t = f.properties.time_min || 60;
      return L.marker(ll, { icon: makeStationDot(t) });
    },
    onEachFeature: (f, l) => {
      const p = f.properties;
      l.bindTooltip(p.statnm || p.station_name || "역", { direction: "top", offset: [0, -6] });
      l.bindPopup(`<div class="popup-title">🚇 ${p.statnm || p.station_name || "역"}</div>
        <div class="popup-row"><span class="popup-label">노선</span><span class="popup-val">${p.linenm || p.line_name || "—"}</span></div>
        <div class="popup-row"><span class="popup-label">소요시간</span><span class="popup-val">${p.time_min}분 이내</span></div>`);
    }
  };
  const layerStatP = statP ? L.geoJSON(statP, stOpts) : null;  // 기본 OFF
  const layerStatC = statC ? L.geoJSON(statC, stOpts) : null;  // 기본 OFF

  // 이소크론 — 5분 단위 12개 레이어 (시간에 따라 색상 농도 변화)
  function isoStyle(t) {
    const ratio  = (t - 5) / 55;                        // 0 (5분) → 1 (60분)
    const fill   = ratio < 0.5 ? "#1a54a0" : "#4a90d9"; // 30분 이하=진파랑, 이상=연파랑
    const fOpacity = 0.18 - ratio * 0.12;               // 0.18(5분) → 0.06(60분)
    return { color: fill, weight: 1.8, fillColor: fill, fillOpacity: fOpacity, dashArray: "5 4" };
  }

  function mkIso(fc, style, name) {
    return L.geoJSON(fc, {
      style,
      onEachFeature: (f, layer) => layer.bindPopup(isoPopup(f, name))
    });
  }

  ISO_TIMES.forEach(t => {
    const fcP = { ...isoRawP, features: isoRawP.features.filter(f => f.properties.time_min === t) };
    const fcC = { ...isoRawC, features: isoRawC.features.filter(f => f.properties.time_min === t) };
    _isoLayers["P" + t] = mkIso(fcP, isoStyle(t), "판교역(신분당선)");
    _isoLayers["C" + t] = mkIso(fcC, isoStyle(t), "청라국제도시역(공항철도)");
  });

  // 초기 30분 레이어 ON
  _isoLayers.P30.addTo(mapP);
  _isoLayers.C30.addTo(mapC);

  // 핵심역 핀 마커
  L.marker([37.3946, 127.1112], { icon: makeCoreIcon("#1a54a0"), zIndexOffset: 1000 })
    .bindPopup(`<div class="popup-title">🚉 판교역 (신분당선)</div>
      <div class="popup-row"><span class="popup-label">노선</span><span class="popup-val">신분당선</span></div>
      <div class="popup-row"><span class="popup-label">개통</span><span class="popup-val">2011-10-28</span></div>
      <div class="popup-row"><span class="popup-label">30분권 도달역</span><span class="popup-val">86역</span></div>
      <div class="popup-row"><span class="popup-label">구역까지 거리</span><span class="popup-val">경계에서 ~588m</span></div>`)
    .addTo(mapP);
  L.marker([37.5330, 126.6231], { icon: makeCoreIcon("#9e1a1a"), zIndexOffset: 1000 })
    .bindPopup(`<div class="popup-title">🚉 청라국제도시역 (공항철도)</div>
      <div class="popup-row"><span class="popup-label">노선</span><span class="popup-val">공항철도(AREX)</span></div>
      <div class="popup-row"><span class="popup-label">개통</span><span class="popup-val">2014-06-21</span></div>
      <div class="popup-row"><span class="popup-label">30분권 도달역</span><span class="popup-val">47역</span></div>
      <div class="popup-row"><span class="popup-label">구역 내 위치</span><span class="popup-val">구역 내부 (349m)</span></div>`)
    .addTo(mapC);

  // 레이어 토글
  function btnToggle(id, pairs) {
    const btn = document.getElementById(id);
    if (!btn) return;
    btn.addEventListener("click", () => {
      const isActive = btn.classList.toggle("active");
      pairs.forEach(([layer, map]) => {
        if (!layer) return;
        if (isActive) { if (!map.hasLayer(layer)) map.addLayer(layer); }
        else          { if (map.hasLayer(layer))  map.removeLayer(layer); }
      });
    });
  }
  btnToggle("tog-zoning",  [[layerZoningP, mapP], [layerZoningC, mapC]]);
  btnToggle("tog-bldg",    [[bldgLayer, mapP], [bldgLayerC, mapC]]);
  btnToggle("tog-road",    [[layerRoadP, mapP], [layerRoadC, mapC]]);
  btnToggle("tog-station", [[layerStatP, mapP], [layerStatC, mapC]]);

  // 이소크론 슬라이더 (30 또는 60만 가능)
  const slider = document.getElementById("iso-slider");
  if (slider) {
    slider.addEventListener("input", e => {
      updateIsoTime(Number(e.target.value), mapP, mapC);
    });
  }

  // 이소크론 프리셋 버튼
  document.querySelectorAll(".iso-preset").forEach(btn => {
    btn.addEventListener("click", () => {
      updateIsoTime(Number(btn.dataset.val), mapP, mapC);
    });
  });

  updateIsoTime(30, mapP, mapC);
  console.log("지도 초기화 완료");
}

initMaps().catch(e => console.error("지도 초기화 오류:", e));
