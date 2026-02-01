const statusDot = document.getElementById("status-dot");
const statusText = document.getElementById("status-text");
const serverInfo = document.getElementById("server-info");
const gpuCount = document.getElementById("gpu-count");
const vramUsage = document.getElementById("vram-usage");
const avgUtil = document.getElementById("avg-util");
const avgTemp = document.getElementById("avg-temp");
const driverVersion = document.getElementById("driver-version");
const lastUpdate = document.getElementById("last-update");
const summaryError = document.getElementById("summary-error");
const gpuGrid = document.getElementById("gpu-grid");
const gpuTableBody = document.getElementById("gpu-table-body");

function formatNumber(value, unit) {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "-";
  }
  const rounded = Math.round(value * 10) / 10;
  return unit ? `${rounded}${unit}` : `${rounded}`;
}

function formatPercent(value) {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "-";
  }
  return `${Math.round(value)}%`;
}

function formatTime(value) {
  if (!value) {
    return "-";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleTimeString();
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function updateStatus(ok, message) {
  statusDot.style.background = ok ? "#6dd5a7" : "#f87171";
  statusDot.style.boxShadow = ok
    ? "0 0 10px rgba(109, 213, 167, 0.6)"
    : "0 0 10px rgba(248, 113, 113, 0.6)";
  statusText.textContent = message;
}

function renderCards(gpus) {
  if (!gpus || gpus.length === 0) {
    gpuGrid.innerHTML = "";
    return;
  }

  gpuGrid.innerHTML = gpus
    .map((gpu) => {
      const memPercent = gpu.memory_utilization || 0;
      const utilPercent = gpu.utilization_gpu || 0;
      return `
        <div class="gpu-card">
          <div class="gpu-title">GPU ${gpu.index ?? "-"} · ${escapeHtml(gpu.name)}</div>
          <div class="gpu-sub">Temp ${formatNumber(gpu.temperature_c, "°C")} · Fan ${formatPercent(gpu.fan_speed_pct)}</div>
          <div class="metric"><span>GPU Util</span><span>${formatPercent(utilPercent)}</span></div>
          <div class="bar"><div class="bar-fill" style="width: ${Math.min(utilPercent, 100)}%"></div></div>
          <div class="metric"><span>VRAM</span><span>${formatNumber(gpu.memory_used_mb, "MB")} / ${formatNumber(gpu.memory_total_mb, "MB")}</span></div>
          <div class="bar"><div class="bar-fill" style="width: ${Math.min(memPercent, 100)}%"></div></div>
          <div class="metric"><span>Power</span><span>${formatNumber(gpu.power_draw_w, "W")} / ${formatNumber(gpu.power_limit_w, "W")}</span></div>
        </div>
      `;
    })
    .join("");
}

function renderTable(gpus) {
  if (!gpus || gpus.length === 0) {
    gpuTableBody.innerHTML = "";
    return;
  }

  gpuTableBody.innerHTML = gpus
    .map((gpu) => {
      return `
        <tr>
          <td>${gpu.index ?? "-"}</td>
          <td>${escapeHtml(gpu.name)}</td>
          <td>${formatNumber(gpu.temperature_c, "°C")}</td>
          <td>${formatPercent(gpu.utilization_gpu)}</td>
          <td>${formatNumber(gpu.memory_used_mb, "MB")} / ${formatNumber(gpu.memory_total_mb, "MB")}</td>
          <td>${formatNumber(gpu.power_draw_w, "W")} / ${formatNumber(gpu.power_limit_w, "W")}</td>
          <td>${formatPercent(gpu.fan_speed_pct)}</td>
        </tr>
      `;
    })
    .join("");
}

function updateOverview(data) {
  const summary = data?.summary || {};
  gpuCount.textContent = summary.gpu_count ?? "-";
  vramUsage.textContent = `${formatNumber(summary.memory_used_mb, "MB")} / ${formatNumber(summary.memory_total_mb, "MB")}`;
  avgUtil.textContent = formatPercent(summary.utilization_avg);
  avgTemp.textContent = formatNumber(summary.temperature_avg, "°C");
  driverVersion.textContent = data?.driver_version || "-";
  lastUpdate.textContent = formatTime(data?.timestamp);
}

function updateError(error, configErrors) {
  if (error) {
    summaryError.textContent = error;
    return;
  }
  if (configErrors && configErrors.length > 0) {
    summaryError.textContent = `Missing config: ${configErrors.join(", ")}`;
    return;
  }
  summaryError.textContent = "";
}

async function refresh() {
  try {
    const response = await fetch("/api/status", { cache: "no-store" });
    const payload = await response.json();
    const ok = payload.ok;
    const server = payload.server || {};
    const serverLabel = server.host ? `${server.user || ""}@${server.host}:${server.port || 22}` : "Disconnected";
    serverInfo.textContent = serverLabel;
    updateStatus(ok, ok ? "Live" : "Offline");
    updateError(payload.error, payload.config_errors);
    updateOverview(payload.data);
    renderCards(payload.data?.gpus || []);
    renderTable(payload.data?.gpus || []);
  } catch (error) {
    updateStatus(false, "Offline");
    summaryError.textContent = "Failed to reach local service";
  }
}

refresh();
setInterval(refresh, 1000);
