"use strict";

const $ = id => document.getElementById(id);
const openModal = id => $(id).classList.remove("hidden");
const closeModal = id => $(id).classList.add("hidden");
const openLoginModal = () => openModal("modal-login");
const openRegisterModal = () => openModal("modal-register");
const openRescueLoginModal = () => openModal("modal-rescue-login");
const toggleProfileDropdown = () => $("profileDropdown").classList.toggle("hidden");

let account = null;
let pendingSOS = null;
let sendingSOS = false;
let motionHandler = null;
let map = null;
let markers = null;
let queueOffset = 0;
let citizenOffset = 0;
let queueVersion = 0;
let citizenVersion = 0;
const pageSize = 50;
const gatewayStorageKey = "disasterops_gateway_number";

const HOSPITALS = [
  { name: "AIIMS Trauma Center", state: "Delhi", region: "South Delhi", dist: "3.2 km", amb: 14, maxAmb: 16, beds: 48, icu: 12, food: 450, meds: 980 },
  { name: "Safdarjung Emergency", state: "Delhi", region: "South Delhi", dist: "4.1 km", amb: 9, maxAmb: 12, beds: 64, icu: 7, food: 600, meds: 1250 },
  { name: "LNJP Central Hospital", state: "Delhi", region: "Central Delhi", dist: "6.8 km", amb: 8, maxAmb: 10, beds: 35, icu: 4, food: 320, meds: 800 },
  { name: "Medanta The Medicity", state: "Haryana", region: "Gurugram", dist: "16.4 km", amb: 15, maxAmb: 20, beds: 85, icu: 21, food: 900, meds: 2400 }
];

async function api(path, method = "GET", body) {
  const response = await fetch("/api/v1" + path, {
    method,
    cache: "no-store",
    headers: body === undefined ? {} : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (response.status === 204) return null;
  const data = await response.json();
  if (!response.ok) {
    const error = new Error(data.detail || "Request failed");
    error.status = response.status;
    throw error;
  }
  return data;
}

function setSession(next) {
  account = next;
  pendingSOS = null;
  queueOffset = citizenOffset = 0;
  if (motionHandler) window.removeEventListener("devicemotion", motionHandler);
  motionHandler = null;
  $("shakeButton").textContent = "Enable shake detection";
  markers?.clearLayers();
  for (const id of ["workQueue", "queuePages", "citizenReports", "citizenPages",
                    "citizenNotice", "queueNotice", "navUsername", "menuUsername", "staffRole"]) {
    $(id).textContent = "";
  }
  closeModal("profileDropdown");
  clearSMSPanel();

  const citizen = account?.role === "citizen";
  const staff = account?.role === "dispatcher" || account?.role === "responder";
  for (const [id, visible] of [
    ["view-landing", !account], ["navPublicButtons", !account],
    ["view-citizen-dashboard", citizen], ["navCitizenTabs", citizen], ["navUserProfile", citizen],
    ["view-rescue-dashboard", staff], ["navRescueBadge", staff], ["navRescueLogoutBtn", staff],
  ]) $(id).classList.toggle("hidden", !visible);

  if (citizen) {
    $("navUsername").textContent = $("menuUsername").textContent = "@" + account.username;
    $("navUserInitial").textContent = account.username[0].toUpperCase();
    renderCheckin(account.safety_status, account.safety_updated_at);
    renderHospitals();
    switchCitizenTab("sos");
    refreshCitizenReports();
  } else if (staff) {
    $("staffRole").textContent = account.role + " · @" + account.username;
    $("workQueueTitle").textContent = account.role === "dispatcher" ? "SOS review queue" : "My assignments";
    renderMap([]);
    refreshQueue();
  }
}

function handleBrandClick() {
  if (account?.role === "citizen") switchCitizenTab("sos");
  else window.scrollTo({ top: 0 });
}

async function handleLogin(event, usernameId, passwordId, errorId, modalId) {
  event.preventDefault();
  const button = event.submitter || event.target.querySelector('button[type="submit"]');
  button.disabled = true;
  $(errorId).classList.add("hidden");
  try {
    await api("/auth/login", "POST", { username: $(usernameId).value, password: $(passwordId).value });
    const session = await api("/auth/me");
    closeModal(modalId);
    setSession(session);
  } catch (error) {
    $(errorId).textContent = error.message;
    $(errorId).classList.remove("hidden");
  } finally {
    $(passwordId).value = "";
    button.disabled = false;
  }
}

const handleCitizenLogin = e => handleLogin(e, "loginUsername", "loginPassword", "loginError", "modal-login");
const handleRescueLogin = e => handleLogin(e, "rescueUser", "rescuePass", "rescueLoginError", "modal-rescue-login");

async function handleCitizenRegister(event) {
  event.preventDefault();
  const notice = $("regError");
  const button = event.submitter || event.target.querySelector('button[type="submit"]');
  notice.classList.add("hidden");
  button.disabled = true;
  const username = $("regUsername").value;
  const password = $("regPassword").value;
  let created = false;
  try {
    if (password !== $("regConfirmPassword").value) throw new Error("Passwords do not match.");
    await api("/auth/register", "POST", { username, password, phone: $("regPhone").value.trim() || null });
    created = true;
    await api("/auth/login", "POST", { username, password });
    const session = await api("/auth/me");
    event.target.reset();
    closeModal("modal-register");
    setSession(session);
  } catch (error) {
    if (created) {
      event.target.reset();
      closeModal("modal-register");
      openLoginModal();
      $("loginError").textContent = "Account created. Sign in to continue.";
      $("loginError").classList.remove("hidden");
    } else {
      notice.textContent = error.message;
      notice.classList.remove("hidden");
    }
  } finally {
    button.disabled = false;
  }
}

async function handleLogout() {
  try {
    await api("/auth/logout", "POST");
    setSession(null);
  } catch {
    alert("Sign-out could not be confirmed. Reconnect and try again.");
  }
}

function switchCitizenTab(tab) {
  const sos = tab === "sos";
  $("tabContentSos").classList.toggle("hidden", !sos);
  $("tabContentHospital").classList.toggle("hidden", sos);
  $("tabBtnSos").setAttribute("aria-pressed", sos);
  $("tabBtnHospital").setAttribute("aria-pressed", !sos);
}

function renderHospitals() {
  const grid = $("citizenHospitalGrid");
  grid.replaceChildren();
  for (const h of HOSPITALS) {
    const card = dom("article", "", "p-3 rounded-xl bg-slate-900 border border-slate-800 space-y-1 text-xs");
    card.append(dom("h3", h.name, "font-bold"),
      dom("p", h.dist + " · Beds " + h.beds + " · ICU " + h.icu + " · Ambulances " + h.amb + "/" + h.maxAmb),
      dom("p", "Food packs " + h.food + " · Medicine units " + h.meds));
    grid.append(card);
  }
}

function getLocation() {
  return new Promise(resolve => {
    if (!navigator.geolocation) return resolve({});
    navigator.geolocation.getCurrentPosition(
      ({ coords }) => resolve({
        latitude: coords.latitude, longitude: coords.longitude,
        ...(coords.accuracy <= 100000 ? { accuracy_meters: coords.accuracy } : {}),
      }),
      () => resolve({}),
      { enableHighAccuracy: true, timeout: 8000, maximumAge: 0 },
    );
  });
}

async function enableShake() {
  if (account?.role !== "citizen" || !window.DeviceMotionEvent || motionHandler) return;
  try {
    if (DeviceMotionEvent.requestPermission &&
        await DeviceMotionEvent.requestPermission() !== "granted") throw new Error();
  } catch {
    $("citizenNotice").textContent = "Motion permission is unavailable.";
    return;
  }
  if (account?.role !== "citizen") return;
  let previous = null;
  let lastPrompt = 0;
  motionHandler = event => {
    const current = event.accelerationIncludingGravity || event.acceleration;
    if (!current || ![current.x, current.y, current.z].every(Number.isFinite)) return;
    const before = previous;
    previous = current;
    if (!before || sendingSOS || Date.now() - lastPrompt < 10000) return;
    const delta = Math.abs(current.x - before.x) + Math.abs(current.y - before.y) + Math.abs(current.z - before.z);
    if (delta <= 26) return;
    lastPrompt = Date.now();
    if (confirm("Shake detected. Submit an SOS report?")) handleCitizenStatusUpdate("HELP", "SHAKE_DEVICE");
  };
  window.addEventListener("devicemotion", motionHandler);
  $("shakeButton").textContent = "Shake detection enabled";
}

function renderCheckin(status, updatedAt) {
  $("statusTitle").textContent = status === "SAFE" ? "I am safe" : (status || "No check-in recorded");
  $("statusTimestamp").textContent = updatedAt ? new Date(updatedAt).toLocaleString() : "—";
}

async function handleCitizenStatusUpdate(status, source) {
  const active = account;
  if (active?.role !== "citizen" || sendingSOS) return;
  const notice = $("citizenNotice");
  if (status === "SAFE") {
    try {
      const checkin = await api("/citizen/safety", "PUT", { status: "SAFE" });
      if (account !== active) return;
      renderCheckin(checkin.status, checkin.updated_at);
      notice.textContent = "Safety check-in recorded.";
    } catch (error) {
      if (account === active) notice.textContent = "Check-in could not be confirmed. " + error.message;
    }
    return;
  }
  sendingSOS = true;
  notice.textContent = pendingSOS ? "Retrying SOS…" : "Getting a GPS fix before sending SOS…";
  try {
    if (!pendingSOS) {
      const location = await getLocation();
      if (account !== active) return;
      pendingSOS = { request_id: crypto.randomUUID(), source, ...location };
    }
    notice.textContent = "Sending SOS…";
    const ack = await api("/citizen/sos", "POST", pendingSOS);
    if (account !== active) return;
    if (ack.status !== "acknowledged" || !ack.report_id) throw new Error("Missing acknowledgment");
    pendingSOS = null;
    notice.textContent = "SOS received by DisasterOps. Report " + ack.report_id;
    citizenOffset = 0;
    refreshCitizenReports();
  } catch {
    if (account === active) notice.textContent =
      "SOS receipt is unconfirmed. Tap NEED HELP to retry, or use the SMS option if configured.";
  } finally {
    sendingSOS = false;
  }
}

function clearSMSPanel() {
  $("smsLink").removeAttribute("href");
  $("smsLink").classList.add("hidden");
  $("smsNotice").textContent = "";
  closeModal("smsPanel");
}

async function triggerOfflineSMSFallback(kind) {
  clearSMSPanel();
  openModal("smsPanel");
  const notice = $("smsNotice");
  const number = localStorage.getItem(gatewayStorageKey);
  if (!/^\+[1-9][0-9]{6,14}$/.test(number || "")) {
    notice.textContent = "The project SMS gateway number is unavailable.";
    return;
  }
  notice.textContent = "Getting your location…";
  const fix = await getLocation();
  if ($("smsPanel").classList.contains("hidden")) return;
  const prefix = kind === "LOC" ? "DISASTEROPS LOC" : "DISASTEROPS SOS";
  const coords = fix.latitude == null ? "" : " Lat: " + fix.latitude.toFixed(6) + " Lon: " + fix.longitude.toFixed(6);
  $("smsLink").href = "sms:" + number + (/(iPad|iPhone|iPod)/.test(navigator.userAgent) ? "&" : "?")
    + "body=" + encodeURIComponent(prefix + coords);
  $("smsLink").classList.remove("hidden");
  notice.textContent = "SMS draft ready" + (coords ? " with location." : " without a GPS fix.")
    + " Open the SMS app and tap Send. DisasterOps has yet to acknowledge receipt.";
  notice.scrollIntoView({ block: "nearest" });
}

function dom(tag, text, className = "") {
  const node = document.createElement(tag);
  node.className = className;
  node.textContent = text;
  return node;
}

function action(text, handler) {
  const button = dom("button", text, "px-2.5 py-1.5 rounded bg-slate-700 text-white text-xs hover:bg-slate-600");
  button.type = "button";
  button.addEventListener("click", () => handler(button));
  return button;
}

function pages(target, offset, count, onPage) {
  target.replaceChildren();
  if (offset > 0) target.append(action("Previous", () => onPage(offset - pageSize)));
  if (count === pageSize) target.append(action("Next", () => onPage(offset + pageSize)));
}

function reportCard(report, assignment) {
  const card = dom("article", "", "p-3 rounded-lg bg-slate-800 space-y-1 text-sm break-words");
  card.append(dom("p", report.source + " · " + new Date(report.received_at).toLocaleString(), "font-bold"),
    dom("p", "Report " + report.id),
    dom("p", report.latitude == null ? "Location unavailable" : report.latitude + ", " + report.longitude),
    dom("p", assignment?.status === "CONFIRMED" ? "Assignment confirmed" :
      assignment ? "Assignment awaiting responder confirmation" : "SOS received · Awaiting assignment"));
  if (report.phone) card.append(dom("p", "Unverified callback: " + report.phone));
  if (report.message) card.append(dom("p", report.message, "whitespace-pre-wrap"));
  return card;
}

async function refreshCitizenReports() {
  const active = account;
  const version = ++citizenVersion;
  try {
    const reports = await api("/citizen/sos?offset=" + citizenOffset);
    if (account !== active || version !== citizenVersion) return;
    $("citizenReports").replaceChildren(...reports.map(report => reportCard(report, report.assignment)));
    if (reports.length === 0) $("citizenReports").textContent = "No reports on this page.";
    pages($("citizenPages"), citizenOffset, reports.length, offset => {
      citizenOffset = offset;
      refreshCitizenReports();
    });
  } catch {
    if (account === active && version === citizenVersion) $("citizenReports").textContent = "Could not load your reports.";
  }
}

function renderMap(reports) {
  if (!window.L) {
    $("rescueLeafletMap").textContent = "Map unavailable. Coordinates are shown in each report.";
    return;
  }
  if (!map) {
    map = L.map("rescueLeafletMap").setView([28.6139, 77.2090], 11);
    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: "&copy; OpenStreetMap contributors",
      maxZoom: 19,
    }).addTo(map);
    markers = L.layerGroup().addTo(map);
  }
  markers.clearLayers();
  for (const r of reports) {
    if (r.latitude != null && r.longitude != null) {
      L.circleMarker([r.latitude, r.longitude], { color: "#dc2626" })
        .bindPopup(dom("span", "SOS " + r.id)).addTo(markers);
    }
  }
  map.invalidateSize();
}

function queueAction(label, run, refresh = true) {
  return action(label, async button => {
    const active = account;
    button.disabled = true;
    try {
      const message = await run();
      if (account !== active) return;
      $("queueNotice").textContent = message;
      if (refresh) await refreshQueue();
    } catch (error) {
      if (account === active) $("queueNotice").textContent = error.message;
    } finally {
      button.disabled = false;
    }
  });
}

function renderQueueCard(row, dispatcher) {
  const report = dispatcher ? row : row.report;
  const assignment = dispatcher ? row.assignment : row;
  const card = reportCard(report, assignment);
  const controls = dom("div", "", "flex flex-wrap gap-2 mt-2");
  if (!dispatcher && assignment.status === "PENDING") {
    controls.append(queueAction("Confirm assignment", async () => {
      await api("/rescue/assignments/" + assignment.id + "/confirm", "POST");
      return "Assignment confirmed.";
    }));
  }
  if (dispatcher && !report.incident_id) {
    controls.append(queueAction("Open incident", async () => {
      await api("/rescue/incidents", "POST", { report_id: report.id });
      return "Incident opened.";
    }));
  }
  if (dispatcher && report.incident_id && !assignment) {
    const username = dom("input", "", "input-box rounded px-2 text-xs");
    username.placeholder = "Responder username";
    username.setAttribute("aria-label", "Responder username");
    controls.append(username, queueAction("Assign", async () => {
      await api("/rescue/incidents/" + report.incident_id + "/assignments", "POST",
        { responder_username: username.value });
      return "Assignment pending responder confirmation.";
    }));
  }
  if (dispatcher && report.phone) {
    controls.append(queueAction("Request location by SMS", async () => {
      const result = await api("/locate/request", "POST", { report_id: report.id });
      return result.status === "accepted_by_gateway" ? "Gateway accepted the request. Awaiting consent."
        : "SMS delivery could not be confirmed.";
    }));
    const requestId = report.location_request_id;
    if (requestId) controls.append(queueAction("Check location request", async () => {
      const result = await api("/locate/status/" + requestId);
      if (result.status === "LOCATED") return "Location shared by consent: " + result.latitude + ", " + result.longitude;
      return result.status === "EXPIRED" ? "Location request expired." : "Awaiting location consent.";
    }, false));
  }
  card.append(controls);
  return card;
}

async function refreshQueue() {
  const active = account;
  if (!active || active.role === "citizen") return;
  const version = ++queueVersion;
  const dispatcher = active.role === "dispatcher";
  try {
    const path = dispatcher ? "/rescue/reports" : "/rescue/assignments";
    const rows = await api(path + "?offset=" + queueOffset);
    if (account !== active || version !== queueVersion) return;
    $("workQueue").replaceChildren(...rows.map(row => renderQueueCard(row, dispatcher)));
    if (rows.length === 0) $("workQueue").textContent = "No items on this page.";
    renderMap(dispatcher ? rows : rows.map(row => row.report));
    pages($("queuePages"), queueOffset, rows.length, offset => {
      queueOffset = offset;
      refreshQueue();
    });
  } catch {
    if (account !== active || version !== queueVersion) return;
    $("workQueue").textContent = "The queue could not be loaded.";
    $("queuePages").replaceChildren();
    renderMap([]);
  }
}

window.addEventListener("DOMContentLoaded", async () => {
  for (const key of ["disasterops_session_role", "disasterops_active_citizen",
                     "disasterops_map_markers_v2", "disasterops_last_fix"]) localStorage.removeItem(key);
  if (location.hash === "#register") openRegisterModal();
  if ("serviceWorker" in navigator) navigator.serviceWorker.register("/sw.js").catch(() => {});
  api("/config").then(data => {
    if (data.gateway_number) localStorage.setItem(gatewayStorageKey, data.gateway_number);
    else localStorage.removeItem(gatewayStorageKey);
  }).catch(() => {});
  const versionAtLoad = account;
  try {
    const session = await api("/auth/me");
    if (account === versionAtLoad) setSession(session);
  } catch {
    // The public shell and SMS composer can still be used offline.
  }
});
