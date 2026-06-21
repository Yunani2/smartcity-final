/* main.js — Leaflet 지도 초기화 및 레이어 관리 */

const USE_COLORS = {
  "업무시설":     "#2166ac",
  "교육연구시설": "#4dac26",
  "근린생활시설": "#f4a582",
  "주거":         "#d6604d",
  "판매시설":     "#fdae61",
  "운수시설":     "#bababa",
  "공장·창고":    "#762a83",
  "기타":         "#cccccc",
};

/* ── 범례 렌더링 ── */
function renderLegend() {
  const el = document.getElementById("use-legend");
  el.innerHTML = "<strong style='font-size:12px;margin-right:6px'>건축물 용도:</strong>";
  Object.entries(USE_COLORS).forEach(([k, v]) => {
    el.innerHTML += `<span class="legend-item"><span class="legend-dot" style="background:${v}"></span>${k}</span>`;
  });
  el.innerHTML += `<span class="legend-item" style="margin-left:auto">
    <span class="legend-dot" style="background:#1a3a5c;opacity:.35"></span>등시간권 30분
    <span class="legend-dot" style="background:#1a3a5c;opacity:.6;margin-left:6px"></span>등시간권 60분
  </span>`;
}
renderLegend();

/* ── Leaflet 지도 생성 헬퍼 ── */
function makeMap(divId, center, zoom) {
  const m = L.map(divId, { zoomControl: true }).setView(center, zoom);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: "© OpenStreetMap contributors",
    maxZoom: 18
  }).addTo(m);
  return m;
}

/* ── 팝업 헬퍼 ── */
function bldgPopup(feat) {
  const p = feat.properties;
  const rows = [
    ["건물명",     p["bd_nm"] || "-"],
    ["주용도",     p["mn_use_nm"] || "-"],
    ["용도분류",   p["use_class"] || "-"],
    ["대지면적",   p["land_ar"] ? Number(p["land_ar"]).toLocaleString() + " ㎡" : "-"],
    ["연면적",     p["tot_fl_ar"] ? Number(p["tot_fl_ar"]).toLocaleString() + " ㎡" : "-"],
    ["용적률",     p["fl_ar_ratio"] ? Number(p["fl_ar_ratio"]).toFixed(1) + " %" : "-"],
    ["지상층수",   p["gr_fl_num"] ? p["gr_fl_num"] + "층" : "-"],
    ["사용승인일", p["use_per_dt"] || "-"],
  ];
  const rowsHtml = rows.map(([l, v]) =>
    `<div class="popup-row"><span class="popup-label">${l}</span><span class="popup-val">${v}</span></div>`
  ).join("");
  return `<div class="popup-title">${p["건물명"] || "건축물"}</div>${rowsHtml}`;
}

/* ── GeoJSON 레이어 로드 헬퍼 ── */
async function loadGeoJSON(url) {
  const r = await fetch(url);
  return r.json();
}

/* ── 메인 초기화 ── */
async function initMaps() {
  // 지도 생성
  const mapP = L.map("map-pangyo",  { zoomControl:true }).setView([37.404, 127.105], 15);
  const mapC = L.map("map-cheongna",{ zoomControl:true }).setView([37.533, 126.625], 15);
  window.mapPangyo   = mapP;
  window.mapCheongna = mapC;

  const tileOpts = { attribution:"© OpenStreetMap contributors", maxZoom:18 };
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", tileOpts).addTo(mapP);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", tileOpts).addTo(mapC);

  // 데이터 병렬 로드
  const [zoneP, zoneC, bldgP, bldgC, isoP30_raw, isoC30_raw, isoP60_raw, isoC60_raw, statP, statC] = await Promise.all([
    loadGeoJSON("data/pangyo_zone.geojson"),
    loadGeoJSON("data/cheongna_zone.geojson"),
    loadGeoJSON("data/pangyo_buildings.geojson"),
    loadGeoJSON("data/cheongna_buildings.geojson"),
    // isochrone은 time_min=30, 60으로 필터
    loadGeoJSON("data/pangyo_isochrone.geojson"),
    loadGeoJSON("data/cheongna_isochrone.geojson"),
    loadGeoJSON("data/pangyo_isochrone.geojson"),
    loadGeoJSON("data/cheongna_isochrone.geojson"),
    loadGeoJSON("data/pangyo_stations_reach.geojson"),
    loadGeoJSON("data/cheongna_stations_reach.geojson"),
  ]);

  // 등시간권 30분/60분 분리
  function filterIso(fc, t) {
    return { ...fc, features: fc.features.filter(f => f.properties.time_min === t) };
  }
  const isoP30 = filterIso(isoP30_raw, 30), isoP60 = filterIso(isoP60_raw, 60);
  const isoC30 = filterIso(isoC30_raw, 30), isoC60 = filterIso(isoC60_raw, 60);

  // ── 구역 경계 레이어 ──
  const zoneStyle = { color:"#1a3a5c", weight:2.5, fillOpacity:0, dashArray:"6 3" };
  const layerZoneP = L.geoJSON(zoneP, { style: zoneStyle }).addTo(mapP);
  const layerZoneC = L.geoJSON(zoneC, { style: zoneStyle }).addTo(mapC);

  // ── 건축물 레이어 ──
  function bldgStyle(feat) {
    const cat = feat.properties["use_class"] || "기타";
    return { radius: 5, fillColor: USE_COLORS[cat] || "#ccc", color:"#fff",
             weight:0.5, fillOpacity:0.85 };
  }
  const bldgOpts = {
    pointToLayer: (f, latlng) => L.circleMarker(latlng, bldgStyle(f)),
    onEachFeature: (f, layer) => layer.bindPopup(bldgPopup(f), { maxWidth:240 })
  };
  const layerBldgP = L.geoJSON(bldgP, bldgOpts).addTo(mapP);
  const layerBldgC = L.geoJSON(bldgC, bldgOpts).addTo(mapC);

  // ── 등시간권 레이어 ──
  const iso30Style = { color:"#1a3a5c", weight:1.5, fillColor:"#1a3a5c", fillOpacity:0.12 };
  const iso60Style = { color:"#1a3a5c", weight:1,   fillColor:"#1a3a5c", fillOpacity:0.06 };
  const layerIsoP30 = L.geoJSON(isoP30, { style: iso30Style });
  const layerIsoP60 = L.geoJSON(isoP60, { style: iso60Style });
  const layerIsoC30 = L.geoJSON(isoC30, { style: iso30Style });
  const layerIsoC60 = L.geoJSON(isoC60, { style: iso60Style });

  // ── 도달 역 레이어 ──
  function stationStyle(feat) {
    const t = feat.properties.time_min;
    const r = t <= 30 ? 5 : (t <= 60 ? 4 : 3);
    const c = t <= 30 ? "#e74c3c" : (t <= 60 ? "#e67e22" : "#95a5a6");
    return { radius: r, fillColor: c, color:"#fff", weight:1, fillOpacity:0.9 };
  }
  function stationPopup(f) {
    const p = f.properties;
    return `<b>${p.statnm}</b><br>${p.linenm}<br>소요: ${p.time_min}분`;
  }
  const stationOpts = {
    pointToLayer: (f, ll) => L.circleMarker(ll, stationStyle(f)),
    onEachFeature: (f, layer) => layer.bindPopup(stationPopup(f))
  };
  const layerStatP = L.geoJSON(statP, stationOpts);
  const layerStatC = L.geoJSON(statC, stationOpts);

  // ── 핵심역 마커 ──
  const iconStar = L.divIcon({ html:"⭐", className:"", iconSize:[20,20], iconAnchor:[10,10] });
  L.marker([37.3946, 127.1112], { icon: iconStar })
    .bindPopup("<b>판교역 (신분당선)</b><br>핵심역 — 강남역까지 ~15분")
    .addTo(mapP);
  L.marker([37.5330, 126.6231], { icon: iconStar })
    .bindPopup("<b>청라국제도시역 (공항철도)</b><br>핵심역 — 개통 2014-06-21")
    .addTo(mapC);

  // ── 체크박스 컨트롤 ──
  function toggleLayer(chkId, ...layerPairs) {
    document.getElementById(chkId).addEventListener("change", e => {
      layerPairs.forEach(([layer, map]) => {
        if (e.target.checked) map.addLayer(layer);
        else map.removeLayer(layer);
      });
    });
  }
  toggleLayer("chk-zone",    [layerZoneP, mapP], [layerZoneC, mapC]);
  toggleLayer("chk-bldg",    [layerBldgP, mapP], [layerBldgC, mapC]);
  toggleLayer("chk-iso30",   [layerIsoP30, mapP], [layerIsoC30, mapC]);
  toggleLayer("chk-iso60",   [layerIsoP60, mapP], [layerIsoC60, mapC]);
  toggleLayer("chk-station", [layerStatP, mapP], [layerStatC, mapC]);

  // ── 지도 뷰 동기화 (선택) ──
  // (각 지역이 다른 위치이므로 동기화 OFF)

  console.log("지도 초기화 완료");
}

initMaps().catch(e => console.error("지도 초기화 오류:", e));
