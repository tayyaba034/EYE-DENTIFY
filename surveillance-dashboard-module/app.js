const DATA_URL = "/api/state";
const ALERTS_URL = "/api/alerts";
const STREAM_URL = "/api/stream.mjpg";

// ─── Multi-cam payload support ────────────────────────────────────────────────
// If the backend returns a multi-cam payload ({ cameras: [...] }), unwrap the
// active camera's pipeline data so all existing render functions work unchanged.
// Single-cam payloads pass through untouched.
function unwrapPayload(raw) {
  if (!Array.isArray(raw.cameras) || raw.cameras.length === 0) {
    // Single-cam payload — use as-is
    return { pipeline: raw, activeCameraId: null, cameraCount: 1, mode: null };
  }

  // Multi-cam payload — find the active camera
  const activeCamId = raw.active_camera_id;
  const activeCam =
    raw.cameras.find(c => c.camera_id === activeCamId && c.status === "running") ||
    raw.cameras.find(c => c.status === "running");

  const pipeline = activeCam ? activeCam.pipeline : {};
  return {
    pipeline,
    activeCameraId: activeCamId,
    cameraCount: raw.cameras.length,
    mode: raw.mode || "parallel",
    cameras: raw.cameras,
  };
}
// ─────────────────────────────────────────────────────────────────────────────

const els = {
  systemScore: document.getElementById("system-score"),
  detectionCount: document.getElementById("detection-count"),
  trackCount: document.getElementById("track-count"),
  feedStatus: document.getElementById("feed-status"),
  lastUpdated: document.getElementById("last-updated"),
  lastUpdatedInline: document.getElementById("last-updated-inline"),
  alertCount: document.getElementById("alert-count"),
  validatedCount: document.getElementById("validated-count"),
  framePill: document.getElementById("frame-pill"),
  stageList: document.getElementById("stage-list"),
  latestTitle: document.getElementById("latest-title"),
  latestExplanation: document.getElementById("latest-explanation"),
  statusList: document.getElementById("status-list"),
  alertList: document.getElementById("alert-list"),
  fusionList: document.getElementById("fusion-list"),
  trackTable: document.getElementById("track-table"),
  deliveryList: document.getElementById("delivery-list"),
  liveFeed: document.getElementById("live-feed"),
  skeletonOverlay: document.getElementById("skeleton-overlay"),
  barFace: document.getElementById("bar-face"),
  barClothing: document.getElementById("bar-clothing"),
  barTemporal: document.getElementById("bar-temporal"),
};

let remoteAlerts = [];

function percent(value) {
  return `${Math.round((value || 0) * 100)}%`;
}

function scoreClass(alert) {
  return alert?.alert ? "card-row alert" : "card-row";
}

function formatPercent(value) {
  const number = Number(value || 0);
  return `${Math.round(number * 100)}`;
}

function renderStages(data) {
  const stages = [
    ["Detection", data?.detections?.detections?.length ?? 0, "person candidates ingested"],
    ["Tracking", data?.tracks?.tracks?.length ?? 0, "persistent track register"],
    ["Feature extraction", (data?.face_features?.length ?? 0) + (data?.clothing_features?.length ?? 0), "face, clothing, optional height"],
    ["Fusion", data?.fusion?.length ?? 0, "identity confidence blended"],
    ["Temporal validation", data?.temporal?.length ?? 0, "stability gate enforced"],
    ["Alert decision", data?.alerts?.filter(item => item.alert).length ?? 0, "operator-facing decisions"],
  ];

  els.stageList.innerHTML = stages.map(([name, value, detail]) => `
    <article class="stage-item">
      <strong>${name}</strong>
      <div class="muted">${detail}</div>
      <div>${value}</div>
    </article>
  `).join("");
}

function renderAlerts(alerts) {
  if (!alerts?.length) {
    els.alertList.className = "stack empty-state";
    els.alertList.textContent = "No alert records yet.";
    return;
  }

  els.alertList.className = "stack";
  els.alertList.innerHTML = alerts.map(alert => `
    <article class="${scoreClass(alert)}">
      <strong>Track ${alert.track_id} · ${(alert.priority || alert.alert_level || "medium").toUpperCase()}</strong>
      <div class="muted">${alert.reason || alert.status || "database alert record"}</div>
      <p>${alert.explanation || "No explanation available."}</p>
    </article>
  `).join("");
}

function renderFusion(fusion) {
  if (!fusion?.length) {
    els.fusionList.className = "stack empty-state";
    els.fusionList.textContent = "Fusion results will appear here.";
    return;
  }

  els.fusionList.className = "stack";
  els.fusionList.innerHTML = fusion.map(item => `
    <article class="card-row">
      <strong>Track ${item.track_id} · Final ${item.final_score.toFixed(2)}</strong>
      <div class="muted">Face ${item.contribution.face.toFixed(2)} · Clothing ${item.contribution.clothing.toFixed(2)} · Temporal ${item.contribution.temporal.toFixed(2)}</div>
    </article>
  `).join("");
}

function renderStatus(data) {
  const alertsActive = (data?.alerts || []).filter(item => item.alert);
  const faceMatches = (data?.face_features || []).filter(
    item => item.face_detected && (item.face_score || 0) >= 0.4
  ).length;
  const faceUnmatched = (data?.face_features || []).filter(
    item => item.face_detected && (item.face_score || 0) < 0.4
  ).length;
  const faceUnavailable = (data?.face_features || []).filter(
    item => !item.face_detected
  ).length;
  const clothingDetected = (data?.clothing_features || []).filter(
    item => item?.clothing?.detected
  );
  const clothingCounter = {};
  for (const item of clothingDetected) {
    const color = item?.clothing?.color || "unknown";
    clothingCounter[color] = (clothingCounter[color] || 0) + 1;
  }
  const clothingSummary = clothingDetected.length
    ? Object.entries(clothingCounter)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 3)
        .map(([color, count]) => `${color}:${count}`)
        .join(" · ")
    : "none";

  const items = [
    `Persons detected: ${data?.detections?.detections?.length ?? 0}`,
    `Tracks active: ${data?.tracks?.tracks?.length ?? 0}`,
    `Face matched: ${faceMatches} · not matched: ${faceUnmatched} · unavailable: ${faceUnavailable}`,
    `Clothing active: ${clothingDetected.length} · ${clothingSummary}`,
    `Alerts active: ${alertsActive.length}`,
  ];

  if (!items.length) {
    els.statusList.className = "stack empty-state";
    els.statusList.textContent = "Waiting for live module state.";
    return;
  }

  els.statusList.className = "stack";
  els.statusList.innerHTML = items.map(item => `
    <article class="card-row">
      <strong>${item}</strong>
    </article>
  `).join("");
}

function renderTracks(data) {
  const rows = data?.tracks?.tracks ?? [];
  if (!rows.length) {
    els.trackTable.innerHTML = `<tr><td colspan="6" class="muted center">No tracks yet.</td></tr>`;
    return;
  }

  const faceByTrack = Object.fromEntries((data.face_features || []).map(item => [item.track_id, item]));
  const clothingByTrack = Object.fromEntries((data.clothing_features || []).map(item => [item.track_id, item]));
  const heightByTrack = Object.fromEntries((data.height_features || []).map(item => [item.track_id, item]));

  els.trackTable.innerHTML = rows.map(track => {
    const face = faceByTrack[track.track_id];
    const clothing = clothingByTrack[track.track_id];
    const height = heightByTrack[track.track_id];
    return `
      <tr>
        <td>#${track.track_id}</td>
        <td>${track.state}</td>
        <td>${track.frames_seen}</td>
        <td>${face?.face_score?.toFixed(2) ?? "n/a"}</td>
        <td>${clothing?.clothing?.color ?? "n/a"} · ${clothing?.clothing?.confidence?.toFixed(2) ?? "0.00"}</td>
        <td>${height?.height?.estimated_height_m?.toFixed(2) ?? "n/a"} m</td>
      </tr>
    `;
  }).join("");
}

function renderDeliveries(deliveries) {
  if (!deliveries?.length) {
    els.deliveryList.className = "stack empty-state";
    els.deliveryList.textContent = "No delivery payloads generated yet.";
    return;
  }

  els.deliveryList.className = "stack";
  els.deliveryList.innerHTML = deliveries.map(item => `
    <article class="card-row">
      <strong>Track ${item.track_id}</strong>
      <div class="muted">${new Date(item.timestamp).toLocaleString()}</div>
      <p>${item.explanation}</p>
      <div class="muted">${item.snapshot || "No snapshot saved"}</div>
    </article>
  `).join("");
}

function renderRemoteDeliveries(alerts) {
  if (!alerts?.length) {
    renderDeliveries([]);
    return;
  }

  els.deliveryList.className = "stack";
  els.deliveryList.innerHTML = alerts.map(item => `
    <article class="card-row">
      <strong>Track ${item.track_id}</strong>
      <div class="muted">${item.timestamp ? new Date(item.timestamp).toLocaleString() : "No timestamp"}</div>
      <p>${item.explanation || "No explanation available."}</p>
      <div class="muted">${item.snapshot || "No snapshot saved"}</div>
    </article>
  `).join("");
}

function renderSkeleton(data) {
  const canvas = els.skeletonOverlay;
  if (!canvas) return;
  
  const ctx = canvas.getContext("2d");
  if (!ctx) return;
  
  // Match canvas size to image
  const img = els.liveFeed;
  if (img && img.naturalWidth && img.naturalHeight) {
    canvas.width = img.offsetWidth;
    canvas.height = img.offsetHeight;
  }
  
  // Clear canvas
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  
  // Get scale factors if image dimensions differ from display
  const scaleX = canvas.width / (img?.naturalWidth || 1);
  const scaleY = canvas.height / (img?.naturalHeight || 1);
  
  // Render skeleton for each detected person
  const heightFeatures = data?.height_features || [];
  heightFeatures.forEach(feature => {
    if (!feature.landmarks || !feature.skeleton) return;
    
    const landmarks = feature.landmarks;
    const skeleton = feature.skeleton;
    
    // Draw skeleton connections
    ctx.strokeStyle = "#FF4444";
    ctx.lineWidth = 2;
    skeleton.forEach(([start, end]) => {
      const p1 = landmarks.find(l => l.id === start);
      const p2 = landmarks.find(l => l.id === end);
      
      if (p1 && p2 && p1.visibility > 0.3 && p2.visibility > 0.3) {
        ctx.beginPath();
        ctx.moveTo(p1.x * scaleX, p1.y * scaleY);
        ctx.lineTo(p2.x * scaleX, p2.y * scaleY);
        ctx.stroke();
      }
    });
    
    // Draw keypoints
    landmarks.forEach(landmark => {
      if (landmark.visibility < 0.3) return;
      
      const radius = landmark.visibility > 0.7 ? 5 : 3;
      const color = landmark.visibility > 0.7 ? "#00FF00" : "#FFFF00";
      
      ctx.fillStyle = color;
      ctx.beginPath();
      ctx.arc(landmark.x * scaleX, landmark.y * scaleY, radius, 0, 2 * Math.PI);
      ctx.fill();
      
      // Draw keypoint ID
      ctx.fillStyle = "#FFFFFF";
      ctx.font = "10px monospace";
      ctx.fillText(String(landmark.id), landmark.x * scaleX + 8, landmark.y * scaleY - 5);
    });
  });
}

function render(data) {
  const detections = data?.detections?.detections?.length ?? 0;
  const tracks = data?.tracks?.tracks?.length ?? 0;
  const validated = (data?.temporal || []).filter(item => item.validated).length;
  const alertCount = (data?.alerts || []).filter(item => item.alert).length;
  const topFusion = (data?.fusion || [])[0];
  const localAlerts = data?.alerts || [];
  const topAlert = localAlerts[0] || remoteAlerts[0];
  const displayAlerts = remoteAlerts.length ? remoteAlerts : localAlerts;

  els.systemScore.textContent = topFusion ? formatPercent(topFusion.final_score) : "--";
  els.detectionCount.textContent = detections;
  els.trackCount.textContent = tracks;
  els.alertCount.textContent = remoteAlerts.length || alertCount;
  els.validatedCount.textContent = validated;
  els.feedStatus.textContent = detections || tracks ? "Pipeline feed active" : "Pipeline idle";
  const refreshedText = `Refreshed ${new Date().toLocaleTimeString()}`;
  els.lastUpdated.textContent = refreshedText;
  els.lastUpdatedInline.textContent = refreshedText;
  els.framePill.textContent = `Frame ${data?.frame_id ?? "--"}`;

  els.latestTitle.textContent = topAlert
    ? `Track ${topAlert.track_id} decision`
    : "Awaiting actionable signal";
  els.latestExplanation.textContent = topAlert?.explanation || "No active alert explanation yet.";

  els.barFace.style.width = percent(topFusion?.contribution?.face);
  els.barClothing.style.width = percent(topFusion?.contribution?.clothing);
  els.barTemporal.style.width = percent(topFusion?.contribution?.temporal);

  renderStages(data);
  renderStatus(data);
  renderAlerts(displayAlerts);
  renderFusion(data?.fusion || []);
  renderTracks(data);
  renderSkeleton(data);
  renderRemoteDeliveries(remoteAlerts.length ? remoteAlerts : (data?.deliveries || []));
}

async function loadAlerts() {
  try {
    const response = await fetch(`${ALERTS_URL}?t=${Date.now()}`, { cache: "no-store" });
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    const payload = await response.json();
    remoteAlerts = payload.alerts || [];
  } catch (error) {
    remoteAlerts = [];
  }
}

async function loadData() {
  try {
    await loadAlerts();
    const response = await fetch(`${DATA_URL}?t=${Date.now()}`, { cache: "no-store" });
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    const raw = await response.json();
    const { pipeline, activeCameraId, cameraCount, mode } = unwrapPayload(raw);

    // Update stream src to active camera if multi-cam
    if (activeCameraId && activeCameraId !== "none") {
      const camStream = `/api/stream/${activeCameraId}.mjpg?t=${Date.now()}`;
      if (!els.liveFeed.src.includes(activeCameraId)) {
        els.liveFeed.src = camStream;
      }
    }

    // Show multi-cam context in feed status
    if (cameraCount > 1) {
      const camLabel = activeCameraId && activeCameraId !== "none"
        ? ` · Active: ${activeCameraId}`
        : "";
      const modeLabel = mode === "priority_failover" ? "Failover" : "Parallel";
      els.feedStatus.textContent = `${cameraCount} cameras · ${modeLabel}${camLabel}`;
    }

    render(pipeline);
  } catch (error) {
    els.feedStatus.textContent = "Waiting for backend artifact";
    els.lastUpdated.textContent = `Load issue: ${error.message}`;
    renderStages({});
  }
}

els.liveFeed.src = `${STREAM_URL}?t=${Date.now()}`;
loadData();
setInterval(loadData, 2500);
