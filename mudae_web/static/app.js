/**
 * MudaDemote Pterodactyl-Inspired Web Dashboard Controller
 */

let activePresetName = "example";
let allPresets = {};
let currentDiscoveredScan = null;
let currentConfigMode = "visual"; // "visual" or "raw"
let ws = null;
let pingInterval = null;

// Header & Navigation Elements
const elServerBreadcrumb = document.getElementById("txtActivePreset");
const elPresetSelect = document.getElementById("presetSelect");
const elStatusBadge = document.getElementById("statusBadge");
const elStatusLabel = document.getElementById("statusLabel");
const elBtnPowerStart = document.getElementById("btnPowerStart");
const elBtnPowerRestart = document.getElementById("btnPowerRestart");
const elBtnPowerStop = document.getElementById("btnPowerStop");

// Metric Cards Elements
const elMetricPowerText = document.getElementById("metricPowerText");
const elMetricPowerValue = document.getElementById("metricPowerValue");
const elMetricPowerBar = document.getElementById("metricPowerBar");
const elMetricRollsBadge = document.getElementById("metricRollsBadge");
const elMetricRollsValue = document.getElementById("metricRollsValue");
const elMetricRollsReset = document.getElementById("metricRollsReset");
const elMetricClaimBadge = document.getElementById("metricClaimBadge");
const elMetricClaimValue = document.getElementById("metricClaimValue");
const elMetricClaimReset = document.getElementById("metricClaimReset");
const elMetricGuildName = document.getElementById("metricGuildName");
const elMetricChannelName = document.getElementById("metricChannelName");

// Terminal & Console Elements
const elConsoleLogStream = document.getElementById("consoleLogStream");
const elTerminalCmdInput = document.getElementById("terminalCmdInput");
const elBtnTerminalSend = document.getElementById("btnTerminalSend");
const elBtnClearConsole = document.getElementById("btnClearConsole");

// Config Editor Elements
const elBtnToggleVisual = document.getElementById("btnToggleVisual");
const elBtnToggleRaw = document.getElementById("btnToggleRaw");
const elConfigVisualView = document.getElementById("configVisualView");
const elConfigRawView = document.getElementById("configRawView");
const elRawJsonEditor = document.getElementById("rawJsonEditor");
const elBtnSaveConfig = document.getElementById("btnSaveConfig");

// Visual Form Fields
const elCfgToken = document.getElementById("cfgToken");
const elCfgChannelId = document.getElementById("cfgChannelId");
const elCfgCmdChannelId = document.getElementById("cfgCmdChannelId");
const elCfgRollCommand = document.getElementById("cfgRollCommand");
const elCfgMinKakera = document.getElementById("cfgMinKakera");
const elCfgRollSpeed = document.getElementById("cfgRollSpeed");
const elCfgClaimInterval = document.getElementById("cfgClaimInterval");
const elCfgRollInterval = document.getElementById("cfgRollInterval");

// Automation Elements
const elChkAutoBadges = document.getElementById("chkAutoBadges");
const elSelBadgeStrategy = document.getElementById("selBadgeStrategy");
const elSelBadgeMaxTier = document.getElementById("selBadgeMaxTier");
const elChkAutoTower = document.getElementById("chkAutoTower");
const elNumTowerMaxFloors = document.getElementById("numTowerMaxFloors");
const elChkAutoWishlistSync = document.getElementById("chkAutoWishlistSync");
const elChkWishlistRemoveClaimed = document.getElementById("chkWishlistRemoveClaimed");
const elBtnSyncWlNow = document.getElementById("btnSyncWlNow");
const elChkAutoGiveCharacters = document.getElementById("chkAutoGiveCharacters");
const elTxtMainAccountId = document.getElementById("txtMainAccountId");
const elChkAutoGiveKakera = document.getElementById("chkAutoGiveKakera");
const elChkAutoLimroul = document.getElementById("chkAutoLimroul");
const elChkAutoDailies = document.getElementById("chkAutoDailies");
const elBtnSaveAutomation = document.getElementById("btnSaveAutomation");

// Server Access & Discovery Elements
const elBtnDiscoverServers = document.getElementById("btnDiscoverServers");
const elBtnAllowAllServers = document.getElementById("btnAllowAllServers");
const elBtnDisallowAllServers = document.getElementById("btnDisallowAllServers");
const elTxtFilterServers = document.getElementById("txtFilterServers");
const elServerListBody = document.getElementById("serverListBody");
const elTxtWhitelistSummary = document.getElementById("txtWhitelistSummary");

// Server Channel Config Drawer Elements
const elServerConfigPanel = document.getElementById("serverConfigPanel");
const elCfgServerIconWrap = document.getElementById("cfgServerIconWrap");
const elCfgServerTitle = document.getElementById("cfgServerTitle");
const elCfgServerId = document.getElementById("cfgServerId");
const elBtnCloseServerConfig = document.getElementById("btnCloseServerConfig");
const elBtnCancelServerConfig = document.getElementById("btnCancelServerConfig");
const elChkSetAsActiveTarget = document.getElementById("chkSetAsActiveTarget");
const elSelServerRollChannel = document.getElementById("selServerRollChannel");
const elSelServerCmdChannel = document.getElementById("selServerCmdChannel");
const elTxtServerPrefix = document.getElementById("txtServerPrefix");
const elSnipeChannelsList = document.getElementById("snipeChannelsList");
const elKakeraChannelsList = document.getElementById("kakeraChannelsList");
const elBtnSaveServerConfig = document.getElementById("btnSaveServerConfig");

// General Settings Elements
const elCfgWebhookUrl = document.getElementById("cfgWebhookUrl");
const elCfgDebugMode = document.getElementById("cfgDebugMode");
const elBtnSaveGeneralSettings = document.getElementById("btnSaveGeneralSettings");

// Navigation Tabs
document.querySelectorAll(".subnav-tab").forEach(tab => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".subnav-tab").forEach(t => t.classList.remove("active"));
    document.querySelectorAll(".tab-pane").forEach(p => p.classList.remove("active"));
    tab.classList.add("active");
    const target = document.getElementById(tab.dataset.tab);
    if (target) target.classList.add("active");
  });
});

// Format seconds to human string (lowercase)
function formatSeconds(secs) {
  if (secs <= 0) return "ready";
  const m = Math.floor(secs / 60);
  const s = secs % 60;
  if (m >= 60) {
    const h = Math.floor(m / 60);
    return `${h}h ${m % 60}m`;
  }
  return `${m}m ${s < 10 ? '0' : ''}${s}s`;
}

// Append log entry to terminal
function appendConsoleLog(type, text, timeStr) {
  const time = timeStr || new Date().toLocaleTimeString().toLowerCase();
  const line = document.createElement("div");
  line.className = `log-line ${type.toLowerCase()}`;
  line.textContent = `[${time}] [${type.toLowerCase()}] ${text}`;
  elConsoleLogStream.appendChild(line);
  elConsoleLogStream.scrollTop = elConsoleLogStream.scrollHeight;
}

elBtnClearConsole.addEventListener("click", () => {
  elConsoleLogStream.innerHTML = "";
});

// Apply Status to Pterodactyl UI
function applyServerStatus(status) {
  // Breadcrumb
  if (status.preset_name) {
    elServerBreadcrumb.textContent = status.preset_name.toLowerCase();
  }

  // Status Badge
  if (status.running) {
    elStatusBadge.className = "status-badge online";
    elStatusLabel.textContent = status.paused ? "paused" : "running";
  } else {
    elStatusBadge.className = "status-badge offline";
    elStatusLabel.textContent = "offline";
  }

  // 1. Kakera Power Metric
  const pwr = status.kakera_power != null ? status.kakera_power : 0;
  elMetricPowerText.textContent = `${pwr}%`;
  elMetricPowerValue.textContent = `${pwr}%`;
  elMetricPowerBar.style.width = `${Math.min(100, Math.max(0, pwr))}%`;

  // 2. Rolls Metric
  const rolls = status.rolls_left != null ? status.rolls_left : "--";
  elMetricRollsBadge.textContent = `${rolls} left`;
  elMetricRollsValue.textContent = `${rolls} rolls`;
  elMetricRollsReset.textContent = status.roll_reset_seconds > 0
    ? `reset in: ${formatSeconds(status.roll_reset_seconds)}`
    : "reset: ready";

  // 3. Claim Metric
  if (status.claim_available) {
    elMetricClaimBadge.textContent = "ready";
    elMetricClaimBadge.style.color = "var(--ptero-green)";
    elMetricClaimValue.textContent = "available";
  } else {
    elMetricClaimBadge.textContent = "cooldown";
    elMetricClaimBadge.style.color = "var(--ptero-yellow)";
    elMetricClaimValue.textContent = "cooldown";
  }
  elMetricClaimReset.textContent = status.claim_reset_seconds > 0
    ? `cooldown: ${formatSeconds(status.claim_reset_seconds)}`
    : "claim: ready";

  // 4. Server Allocation Metric
  elMetricGuildName.textContent = status.user || "disconnected";
  const memInfo = status.memory_mb ? ` • ${status.memory_mb}mb ram` : "";
  elMetricChannelName.textContent = status.channel_id ? `channel: ${status.channel_id}${memInfo}` : `channel: unconfigured${memInfo}`;
}


// Dispatch Mudae Command
async function dispatchCommand(cmd) {
  const cleanCmd = cmd.trim();
  if (!cleanCmd) return;
  appendConsoleLog("system", `> ${cleanCmd}`);
  try {
    const res = await fetch("/api/actions/command", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ command: cleanCmd }),
    });
    const json = await res.json();
    if (!json.success) {
      appendConsoleLog("error", json.error || "failed to send command");
    }
  } catch (err) {
    appendConsoleLog("error", `command error: ${err.message}`);
  }
}

// Terminal Command Input Handling
elBtnTerminalSend.addEventListener("click", () => {
  dispatchCommand(elTerminalCmdInput.value);
  elTerminalCmdInput.value = "";
});

elTerminalCmdInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") {
    dispatchCommand(elTerminalCmdInput.value);
    elTerminalCmdInput.value = "";
  }
});

// Quick action chips
document.querySelectorAll(".chip-action").forEach(chip => {
  chip.addEventListener("click", () => {
    dispatchCommand(chip.dataset.cmd);
  });
});

// Power Controls
elBtnPowerStart.addEventListener("click", async () => {
  appendConsoleLog("system", `initiating start for preset '${activePresetName}'...`);
  try {
    const res = await fetch("/api/bot/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ preset_name: activePresetName }),
    });
    const json = await res.json();
    if (json.success) {
      appendConsoleLog("system", "start sequence dispatched successfully.");
    } else {
      appendConsoleLog("error", json.error || "start failed.");
    }
  } catch (err) {
    appendConsoleLog("error", err.message);
  }
});

elBtnPowerRestart.addEventListener("click", async () => {
  appendConsoleLog("system", "initiating bot restart...");
  try {
    const res = await fetch("/api/bot/restart", { method: "POST" });
    const json = await res.json();
    if (json.success) {
      appendConsoleLog("system", "restart sequence triggered.");
    } else {
      appendConsoleLog("error", json.error || "restart failed.");
    }
  } catch (err) {
    appendConsoleLog("error", err.message);
  }
});

elBtnPowerStop.addEventListener("click", async () => {
  appendConsoleLog("system", "stopping bot instance...");
  try {
    const res = await fetch("/api/bot/stop", { method: "POST" });
    const json = await res.json();
    if (json.success) {
      appendConsoleLog("system", "stop sequence executed.");
    } else {
      appendConsoleLog("error", json.error || "stop failed.");
    }
  } catch (err) {
    appendConsoleLog("error", err.message);
  }
});

// Populate Preset Forms
function populatePresetData(data) {
  if (!data) return;

  // Visual Config
  elCfgToken.value = data.token || "";
  elCfgChannelId.value = data.channel_id || "";
  elCfgCmdChannelId.value = data.command_channel_id || "";
  elCfgRollCommand.value = data.roll_command || "wa";
  elCfgMinKakera.value = data.min_kakera != null ? data.min_kakera : 100;
  elCfgRollSpeed.value = data.roll_speed != null ? data.roll_speed : 0.4;
  elCfgClaimInterval.value = data.claim_interval != null ? data.claim_interval : 180;
  elCfgRollInterval.value = data.roll_interval != null ? data.roll_interval : 60;

  // Raw JSON editor
  elRawJsonEditor.value = JSON.stringify(data, null, 2);

  // Automation
  elChkAutoBadges.checked = !!data.auto_badges_enabled;
  elSelBadgeStrategy.value = data.badge_strategy || "optimal";
  elSelBadgeMaxTier.value = String(data.badge_max_tier || 4);
  elChkAutoTower.checked = !!data.auto_tower_enabled;
  elNumTowerMaxFloors.value = data.tower_max_floors || 10;
  elChkAutoWishlistSync.checked = !!data.auto_wishlist_sync_enabled;
  elChkWishlistRemoveClaimed.checked = !!data.wishlist_remove_claimed;
  elChkAutoGiveCharacters.checked = !!data.auto_give_characters_enabled;
  elTxtMainAccountId.value = data.main_account_id || "";
  elChkAutoGiveKakera.checked = !!data.auto_give_kakera_enabled;
  elChkAutoLimroul.checked = data.auto_limroul_enabled !== false;
  elChkAutoDailies.checked = data.auto_p_enabled !== false;

  // Settings
  elCfgWebhookUrl.value = data.webhook_url || "";
  elCfgDebugMode.checked = !!data.debug_mode;

  // Server Access & Whitelist state
  allowedGuildIds = data.allowed_guild_ids !== undefined ? data.allowed_guild_ids : null;
  targetGuildId = data.target_guild_id || null;
  serverConfigs = data.server_configs || {};
  updateWhitelistSummary();
  renderServerList();
}

// Config View Toggles (Visual vs Raw JSON)
elBtnToggleVisual.addEventListener("click", () => {
  currentConfigMode = "visual";
  elBtnToggleVisual.classList.add("active");
  elBtnToggleRaw.classList.remove("active");
  elConfigVisualView.classList.add("active");
  elConfigRawView.classList.remove("active");
});

elBtnToggleRaw.addEventListener("click", () => {
  currentConfigMode = "raw";
  elBtnToggleRaw.classList.add("active");
  elBtnToggleVisual.classList.remove("active");
  elConfigRawView.classList.add("active");
  elConfigVisualView.classList.remove("active");

  // Keep raw editor in sync with latest visual edits
  const current = allPresets[activePresetName] || {};
  syncVisualToPresetObject(current);
  elRawJsonEditor.value = JSON.stringify(current, null, 2);
});

function syncVisualToPresetObject(target) {
  if (elCfgToken.value.trim()) target.token = elCfgToken.value.trim();
  target.channel_id = elCfgChannelId.value.trim();
  target.command_channel_id = elCfgCmdChannelId.value.trim();
  target.roll_command = elCfgRollCommand.value.trim() || "wa";
  target.min_kakera = parseInt(elCfgMinKakera.value) || 100;
  target.roll_speed = parseFloat(elCfgRollSpeed.value) || 0.4;
  target.claim_interval = parseInt(elCfgClaimInterval.value) || 180;
  target.roll_interval = parseInt(elCfgRollInterval.value) || 60;
}

// Save Configuration
async function saveActivePreset(presetData) {
  try {
    const res = await fetch("/api/presets", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: activePresetName, data: presetData }),
    });
    const json = await res.json();
    if (json.success) {
      appendConsoleLog("system", `content saved successfully for '${activePresetName}'.`);
      allPresets[activePresetName] = presetData;
      populatePresetData(presetData);
    } else {
      appendConsoleLog("error", `save failed: ${json.errors ? json.errors.join(", ") : json.error}`);
    }
  } catch (err) {
    appendConsoleLog("error", `network save error: ${err.message}`);
  }
}

elBtnSaveConfig.addEventListener("click", () => {
  if (currentConfigMode === "raw") {
    try {
      const parsed = JSON.parse(elRawJsonEditor.value);
      saveActivePreset(parsed);
    } catch (e) {
      appendConsoleLog("error", `invalid json: ${e.message}`);
    }
  } else {
    const current = allPresets[activePresetName] || {};
    syncVisualToPresetObject(current);
    saveActivePreset(current);
  }
});

// Save Automation Settings
elBtnSaveAutomation.addEventListener("click", () => {
  const current = allPresets[activePresetName] || {};
  current.auto_badges_enabled = elChkAutoBadges.checked;
  current.badge_strategy = elSelBadgeStrategy.value;
  current.badge_max_tier = parseInt(elSelBadgeMaxTier.value) || 4;
  current.auto_tower_enabled = elChkAutoTower.checked;
  current.tower_max_floors = parseInt(elNumTowerMaxFloors.value) || 10;
  current.auto_wishlist_sync_enabled = elChkAutoWishlistSync.checked;
  current.wishlist_remove_claimed = elChkWishlistRemoveClaimed.checked;
  current.auto_give_characters_enabled = elChkAutoGiveCharacters.checked;
  current.main_account_id = elTxtMainAccountId.value.trim();
  current.auto_give_kakera_enabled = elChkAutoGiveKakera.checked;
  current.auto_limroul_enabled = elChkAutoLimroul.checked;
  current.auto_p_enabled = elChkAutoDailies.checked;
  saveActivePreset(current);
});

// Save General Settings
elBtnSaveGeneralSettings.addEventListener("click", () => {
  const current = allPresets[activePresetName] || {};
  current.webhook_url = elCfgWebhookUrl.value.trim();
  current.debug_mode = elCfgDebugMode.checked;
  saveActivePreset(current);
});

// Trigger Wishlist Sync
elBtnSyncWlNow.addEventListener("click", () => {
  dispatchCommand("$wll");
});

// State for multi-server management
let discoveredGuilds = [];
let allowedGuildIds = null;
let targetGuildId = null;
let serverConfigs = {};
let currentConfigGuildId = null;

function updateWhitelistSummary() {
  if (!elTxtWhitelistSummary) return;
  if (allowedGuildIds === null) {
    elTxtWhitelistSummary.className = "status-pill subtle";
    elTxtWhitelistSummary.textContent = "all servers allowed (unrestricted)";
  } else if (allowedGuildIds.length === 0) {
    elTxtWhitelistSummary.className = "status-pill pill-denied";
    elTxtWhitelistSummary.textContent = "all servers blocked (whitelist: 0)";
  } else {
    elTxtWhitelistSummary.className = "status-pill pill-allowed";
    elTxtWhitelistSummary.textContent = `${allowedGuildIds.length} server${allowedGuildIds.length === 1 ? '' : 's'} whitelisted`;
  }
}

function renderServerList() {
  if (!elServerListBody) return;
  const filter = (elTxtFilterServers ? elTxtFilterServers.value : "").trim().toLowerCase();
  const visible = discoveredGuilds.filter(g => {
    if (!filter) return true;
    return g.name.toLowerCase().includes(filter) || String(g.id).includes(filter);
  });

  if (!visible.length) {
    elServerListBody.innerHTML = `<tr><td colspan="6" class="table-empty">${discoveredGuilds.length ? 'no servers match your filter.' : 'click "scan joined servers" to load servers connected to this bot account.'}</td></tr>`;
    return;
  }

  elServerListBody.innerHTML = "";
  visible.forEach(g => {
    const isTarget = String(g.id) === String(targetGuildId);
    const isAllowed = allowedGuildIds === null || allowedGuildIds.map(String).includes(String(g.id));
    const tr = document.createElement("tr");

    // Icon & Name
    const iconHtml = g.icon_url
      ? `<img src="${g.icon_url}" class="guild-icon" alt="" />`
      : `<div class="guild-icon-fallback">${g.name.slice(0, 1).toUpperCase()}</div>`;

    tr.innerHTML = `
      <td>
        <div class="guild-profile">
          ${iconHtml}
          <div class="guild-details">
            <span class="guild-name">${g.name.toLowerCase()}</span>
            <span class="code-tag">id: ${g.id}</span>
          </div>
        </div>
      </td>
      <td>${g.member_count}</td>
      <td>
        ${g.mudae_present
          ? '<span class="status-pill pill-mudae">mudae verified</span>'
          : '<span class="status-pill subtle">not present</span>'}
      </td>
      <td>
        <label class="switch">
          <input type="checkbox" class="chk-server-allowed" data-guild-id="${g.id}" ${isAllowed ? 'checked' : ''}>
          <span class="slider"></span>
        </label>
      </td>
      <td>
        ${isTarget
          ? '<span class="status-pill pill-target">active target</span>'
          : (isAllowed
            ? '<span class="status-pill pill-allowed">allowed</span>'
            : '<span class="status-pill pill-denied">blocked</span>')}
      </td>
      <td class="text-right">
        <button class="btn-ptero-secondary btn-configure-server" data-guild-id="${g.id}">
          configure channels
        </button>
      </td>
    `;

    // Hook toggle
    const toggle = tr.querySelector(".chk-server-allowed");
    toggle.addEventListener("change", async (e) => {
      const allowed = e.target.checked;
      await toggleGuildAccess(g.id, allowed);
    });

    // Hook configure button
    const btnCfg = tr.querySelector(".btn-configure-server");
    btnCfg.addEventListener("click", () => {
      openServerConfig(g.id);
    });

    elServerListBody.appendChild(tr);
  });
}

// Toggle individual guild access
async function toggleGuildAccess(guildId, allowed) {
  try {
    let newAllowed;
    if (allowedGuildIds === null) {
      newAllowed = allowed ? [String(guildId)] : discoveredGuilds.map(g => String(g.id)).filter(id => id !== String(guildId));
    } else {
      newAllowed = [...allowedGuildIds.map(String)];
      if (allowed && !newAllowed.includes(String(guildId))) {
        newAllowed.push(String(guildId));
      } else if (!allowed && newAllowed.includes(String(guildId))) {
        newAllowed = newAllowed.filter(id => id !== String(guildId));
      }
    }
    allowedGuildIds = newAllowed;
    updateWhitelistSummary();
    renderServerList();

    const res = await fetch("/api/discovery/whitelist", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ allowed_guild_ids: newAllowed, preset_name: activePresetName }),
    });
    const json = await res.json();
    if (json.success) {
      appendConsoleLog("system", `server ${guildId} ${allowed ? 'whitelisted' : 'blocked'}.`);
    } else {
      appendConsoleLog("error", json.error || "failed updating whitelist.");
    }
  } catch (err) {
    appendConsoleLog("error", err.message);
  }
}

// Allow all servers
elBtnAllowAllServers.addEventListener("click", async () => {
  allowedGuildIds = null;
  updateWhitelistSummary();
  renderServerList();
  try {
    const res = await fetch("/api/discovery/whitelist", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ allowed_guild_ids: null, preset_name: activePresetName }),
    });
    const json = await res.json();
    if (json.success) {
      appendConsoleLog("system", "unrestricted access enabled: all servers allowed.");
    }
  } catch (err) {
    appendConsoleLog("error", err.message);
  }
});

// Disallow all servers
elBtnDisallowAllServers.addEventListener("click", async () => {
  allowedGuildIds = [];
  updateWhitelistSummary();
  renderServerList();
  try {
    const res = await fetch("/api/discovery/whitelist", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ allowed_guild_ids: [], preset_name: activePresetName }),
    });
    const json = await res.json();
    if (json.success) {
      appendConsoleLog("warn", "strict whitelist activated: all servers disallowed until manually approved.");
    }
  } catch (err) {
    appendConsoleLog("error", err.message);
  }
});

if (elTxtFilterServers) {
  elTxtFilterServers.addEventListener("input", renderServerList);
}

// Discover Servers Action
elBtnDiscoverServers.addEventListener("click", async () => {
  elBtnDiscoverServers.disabled = true;
  appendConsoleLog("system", "contacting discord gateway for server list...");
  try {
    const res = await fetch("/api/discovery/guilds");
    const json = await res.json();
    if (json.success && json.guilds) {
      discoveredGuilds = json.guilds;
      allowedGuildIds = json.allowed_guild_ids;
      targetGuildId = json.target_guild_id;
      serverConfigs = json.server_configs || {};
      updateWhitelistSummary();
      renderServerList();
      appendConsoleLog("system", `discovered ${json.guilds.length} joined servers.`);
    } else {
      appendConsoleLog("warn", json.error || "could not retrieve servers.");
    }
  } catch (err) {
    appendConsoleLog("error", err.message);
  } finally {
    elBtnDiscoverServers.disabled = false;
  }
});

// Open Server Channel Config Drawer
async function openServerConfig(guildId) {
  currentConfigGuildId = String(guildId);
  const guild = discoveredGuilds.find(g => String(g.id) === currentConfigGuildId);
  if (!guild) return;

  elCfgServerTitle.textContent = guild.name.toLowerCase();
  elCfgServerId.textContent = `id: ${guild.id}`;
  if (guild.icon_url) {
    elCfgServerIconWrap.innerHTML = `<img src="${guild.icon_url}" class="guild-icon" alt="" />`;
  } else {
    elCfgServerIconWrap.innerHTML = `<div class="guild-icon-fallback">${guild.name.slice(0, 1).toUpperCase()}</div>`;
  }

  appendConsoleLog("system", `inspecting channels for '${guild.name.toLowerCase()}'...`);
  try {
    const res = await fetch("/api/discovery/scan", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ guild_id: guildId }),
    });
    const json = await res.json();
    if (!json.success || !json.scan) {
      appendConsoleLog("error", json.error || "failed inspecting server channels.");
      return;
    }

    const scan = json.scan;
    const existingCfg = json.server_config || {};
    const isTarget = json.is_target || String(guildId) === String(targetGuildId);

    elChkSetAsActiveTarget.checked = isTarget;
    elTxtServerPrefix.value = existingCfg.mudae_prefix || scan.detected_prefix || "$";

    // Populate Roll Channel Select
    elSelServerRollChannel.innerHTML = '<option value="">select roll channel...</option>';
    (scan.channels || []).forEach(ch => {
      const opt = document.createElement("option");
      opt.value = ch.id;
      const isRec = scan.recommended_roll_channel && scan.recommended_roll_channel.id === ch.id;
      opt.textContent = `#${ch.name} (${ch.id})${isRec ? ' [recommended]' : ''}`;
      if (existingCfg.channel_id && String(existingCfg.channel_id) === String(ch.id)) {
        opt.selected = true;
      } else if (!existingCfg.channel_id && isRec) {
        opt.selected = true;
      }
      elSelServerRollChannel.appendChild(opt);
    });

    // Populate Command Channel Select
    elSelServerCmdChannel.innerHTML = '<option value="">same as roll channel</option>';
    (scan.channels || []).forEach(ch => {
      const opt = document.createElement("option");
      opt.value = ch.id;
      const isRec = scan.recommended_command_channel && scan.recommended_command_channel.id === ch.id;
      opt.textContent = `#${ch.name} (${ch.id})${isRec ? ' [recommended]' : ''}`;
      if (existingCfg.command_channel_id && String(existingCfg.command_channel_id) === String(ch.id)) {
        opt.selected = true;
      }
      elSelServerCmdChannel.appendChild(opt);
    });

    // Populate Snipe Channels Checklist
    const savedSnipe = (existingCfg.snipe_channels || []).map(String);
    elSnipeChannelsList.innerHTML = "";
    (scan.channels || []).forEach(ch => {
      const label = document.createElement("label");
      label.className = "channel-check-item";
      const isChecked = savedSnipe.includes(String(ch.id));
      label.innerHTML = `
        <input type="checkbox" value="${ch.id}" class="chk-snipe-ch" ${isChecked ? 'checked' : ''}>
        <span>#${ch.name} <span class="code-tag">(${ch.id})</span></span>
      `;
      elSnipeChannelsList.appendChild(label);
    });

    // Populate Kakera Snipe Channels Checklist
    const savedKakera = (existingCfg.kakera_snipe_channels || []).map(String);
    elKakeraChannelsList.innerHTML = "";
    (scan.channels || []).forEach(ch => {
      const label = document.createElement("label");
      label.className = "channel-check-item";
      const isChecked = savedKakera.includes(String(ch.id));
      label.innerHTML = `
        <input type="checkbox" value="${ch.id}" class="chk-kakera-ch" ${isChecked ? 'checked' : ''}>
        <span>#${ch.name} <span class="code-tag">(${ch.id})</span></span>
      `;
      elKakeraChannelsList.appendChild(label);
    });

    elServerConfigPanel.classList.remove("hidden");
    elServerConfigPanel.scrollIntoView({ behavior: "smooth" });
  } catch (err) {
    appendConsoleLog("error", err.message);
  }
}

// Close & Cancel Server Config
if (elBtnCloseServerConfig) {
  elBtnCloseServerConfig.addEventListener("click", () => {
    elServerConfigPanel.classList.add("hidden");
  });
}
if (elBtnCancelServerConfig) {
  elBtnCancelServerConfig.addEventListener("click", () => {
    elServerConfigPanel.classList.add("hidden");
  });
}

// Save Server Configuration & Rules
if (elBtnSaveServerConfig) {
  elBtnSaveServerConfig.addEventListener("click", async () => {
    if (!currentConfigGuildId) return;
    elBtnSaveServerConfig.disabled = true;

    const rollCh = elSelServerRollChannel.value;
    const cmdCh = elSelServerCmdChannel.value;
    const prefix = elTxtServerPrefix.value.trim() || "$";
    const setAsTarget = elChkSetAsActiveTarget.checked;

    const snipeChs = [];
    document.querySelectorAll(".chk-snipe-ch:checked").forEach(cb => {
      snipeChs.push(cb.value);
    });

    const kakeraChs = [];
    document.querySelectorAll(".chk-kakera-ch:checked").forEach(cb => {
      kakeraChs.push(cb.value);
    });

    try {
      const payload = {
        guild_id: currentConfigGuildId,
        preset_name: activePresetName,
        channel_id: rollCh,
        command_channel_id: cmdCh,
        snipe_channels: snipeChs,
        kakera_snipe_channels: kakeraChs,
        mudae_prefix: prefix,
        allowed: true,
        set_as_target: setAsTarget,
      };

      const res = await fetch("/api/discovery/server_config", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const json = await res.json();
      if (json.success) {
        if (setAsTarget) {
          targetGuildId = currentConfigGuildId;
          if (rollCh) elCfgChannelId.value = rollCh;
          if (cmdCh) elCfgCmdChannelId.value = cmdCh;
        }
        allowedGuildIds = json.allowed_guild_ids;
        updateWhitelistSummary();
        renderServerList();
        appendConsoleLog("system", `server rules saved for guild ${currentConfigGuildId}${setAsTarget ? ' and activated as target' : ''}.`);
        elServerConfigPanel.classList.add("hidden");
        await loadPresetsList();
      } else {
        appendConsoleLog("error", json.error || "failed saving server rules.");
      }
    } catch (err) {
      appendConsoleLog("error", err.message);
    } finally {
      elBtnSaveServerConfig.disabled = false;
    }
  });
}


// Load Presets
async function loadPresetsList() {
  try {
    const res = await fetch("/api/presets");
    allPresets = await res.json();
    elPresetSelect.innerHTML = "";
    const names = Object.keys(allPresets);
    if (!names.length) {
      allPresets["example"] = {};
      names.push("example");
    }
    names.forEach(name => {
      const opt = document.createElement("option");
      opt.value = name;
      opt.textContent = name.toLowerCase();
      if (name.toLowerCase() === activePresetName.toLowerCase()) opt.selected = true;
      elPresetSelect.appendChild(opt);
    });
    activePresetName = elPresetSelect.value || names[0];
    elServerBreadcrumb.textContent = activePresetName.toLowerCase();
    populatePresetData(allPresets[activePresetName]);
  } catch (err) {
    appendConsoleLog("error", `failed loading presets: ${err.message}`);
  }
}

elPresetSelect.addEventListener("change", () => {
  activePresetName = elPresetSelect.value;
  elServerBreadcrumb.textContent = activePresetName.toLowerCase();
  if (allPresets[activePresetName]) {
    populatePresetData(allPresets[activePresetName]);
  }
});

// WebSocket Connection to Server
function initWebSocket() {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const wsUrl = `${protocol}//${window.location.host}/api/ws`;
  ws = new WebSocket(wsUrl);

  ws.onopen = () => {
    appendConsoleLog("system", "connected to daemon via websocket.");
    if (pingInterval) clearInterval(pingInterval);
    pingInterval = setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ action: "ping" }));
      }
    }, 20000);
  };

  ws.onmessage = (event) => {
    try {
      const msg = JSON.parse(event.data);
      if (msg.type === "init") {
        applyServerStatus(msg.status);
        if (msg.recent_events) {
          msg.recent_events.forEach(ev => {
            appendConsoleLog(ev.type, JSON.stringify(ev.data), new Date(ev.timestamp).toLocaleTimeString().toLowerCase());
          });
        }
      } else if (msg.type === "status") {
        applyServerStatus(msg.data);
      } else {
        appendConsoleLog(msg.type, JSON.stringify(msg.data), new Date(msg.timestamp).toLocaleTimeString().toLowerCase());
      }
    } catch (e) {
      console.error(e);
    }
  };

  ws.onclose = () => {
    appendConsoleLog("warn", "daemon connection closed. reconnecting in 3s...");
    setTimeout(initWebSocket, 3000);
  };

  ws.onerror = () => {
    ws.close();
  };
}

// Initial Boot
loadPresetsList();
initWebSocket();

// Periodic status poll fallback
setInterval(async () => {
  try {
    const res = await fetch("/api/status");
    const json = await res.json();
    applyServerStatus(json);
  } catch (e) {}
}, 4000);
