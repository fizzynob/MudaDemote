/**
 * MudaDemote Pterodactyl-Inspired Web Dashboard Controller
 */

let activePresetName = "example";
let allPresets = {};
let currentConfigMode = "visual"; // "visual" or "raw"
let ws = null;
let pingInterval = null;
let autoScrollEnabled = true;
let activeLogFilter = "all";
let logSearchQuery = "";
let cmdHistory = [];
let cmdHistoryIndex = -1;
let lastStatusSnapshot = null;

// Wishlist & Snipe Arrays for active preset
let wishlistCharacters = [];
let seriesWishlist = [];
let avoidCharacters = [];

// Header & Navigation Elements
const elServerBreadcrumb = document.getElementById("txtActivePreset");
const elPresetSelect = document.getElementById("presetSelect");
const elBtnNewPreset = document.getElementById("btnNewPreset");
const elBtnDeletePreset = document.getElementById("btnDeletePreset");
const elStatusBadge = document.getElementById("statusBadge");
const elStatusLabel = document.getElementById("statusLabel");
const elBtnPowerStart = document.getElementById("btnPowerStart");
const elBtnPowerPause = document.getElementById("btnPowerPause");
const elBtnPowerRestart = document.getElementById("btnPowerRestart");
const elBtnPowerStop = document.getElementById("btnPowerStop");

// Metric Cards Elements
const elMetricPowerText = document.getElementById("metricPowerText");
const elMetricPowerValue = document.getElementById("metricPowerValue");
const elMetricPowerBar = document.getElementById("metricPowerBar");
const elMetricPowerSub = document.getElementById("metricPowerSub");
const elMetricRollsBadge = document.getElementById("metricRollsBadge");
const elMetricRollsValue = document.getElementById("metricRollsValue");
const elMetricRollsReset = document.getElementById("metricRollsReset");
const elMetricClaimBadge = document.getElementById("metricClaimBadge");
const elMetricClaimValue = document.getElementById("metricClaimValue");
const elMetricClaimReset = document.getElementById("metricClaimReset");
const elMetricActivityBadge = document.getElementById("metricActivityBadge");
const elMetricGuildName = document.getElementById("metricGuildName");
const elMetricChannelName = document.getElementById("metricChannelName");

// Terminal & Console Elements
const elConsoleLogStream = document.getElementById("consoleLogStream");
const elTerminalCmdInput = document.getElementById("terminalCmdInput");
const elBtnTerminalSend = document.getElementById("btnTerminalSend");
const elBtnClearConsole = document.getElementById("btnClearConsole");
const elBtnExportLogs = document.getElementById("btnExportLogs");
const elBtnAutoScroll = document.getElementById("btnAutoScroll");
const elBtnWakeLoop = document.getElementById("btnWakeLoop");
const elTerminalSearchInput = document.getElementById("terminalSearchInput");

// Session Activity Feed Elements
const elBadgeSessionClaims = document.getElementById("badgeSessionClaims");
const elRecentClaimsList = document.getElementById("recentClaimsList");
const elBadgeSessionKakera = document.getElementById("badgeSessionKakera");
const elRecentKakeraList = document.getElementById("recentKakeraList");

// Config Editor Elements
const elBtnToggleVisual = document.getElementById("btnToggleVisual");
const elBtnToggleRaw = document.getElementById("btnToggleRaw");
const elConfigVisualView = document.getElementById("configVisualView");
const elConfigRawView = document.getElementById("configRawView");
const elRawJsonEditor = document.getElementById("rawJsonEditor");
const elBtnFormatJson = document.getElementById("btnFormatJson");
const elBtnSaveConfig = document.getElementById("btnSaveConfig");
const elBtnSaveAndRestartConfig = document.getElementById("btnSaveAndRestartConfig");

// Visual Form Fields
const elCfgToken = document.getElementById("cfgToken");
const elBtnToggleTokenVis = document.getElementById("btnToggleTokenVis");
const elCfgChannelId = document.getElementById("cfgChannelId");
const elCfgCmdChannelId = document.getElementById("cfgCmdChannelId");
const elCfgMudaePrefix = document.getElementById("cfgMudaePrefix");
const elCfgRollCommand = document.getElementById("cfgRollCommand");
const elCfgMinKakera = document.getElementById("cfgMinKakera");
const elCfgMaxClaimRank = document.getElementById("cfgMaxClaimRank");
const elCfgMaxLikeRank = document.getElementById("cfgMaxLikeRank");
const elCfgRollSpeed = document.getElementById("cfgRollSpeed");
const elCfgClaimInterval = document.getElementById("cfgClaimInterval");
const elCfgRollInterval = document.getElementById("cfgRollInterval");
const elCfgStartDelay = document.getElementById("cfgStartDelay");

// Core Gameplay Toggles
const elCfgRollingEnabled = document.getElementById("cfgRollingEnabled");
const elCfgUseSlashRolls = document.getElementById("cfgUseSlashRolls");
const elCfgTimeRollsToReset = document.getElementById("cfgTimeRollsToReset");
const elCfgKeyMode = document.getElementById("cfgKeyMode");
const elCfgLurkerMode = document.getElementById("cfgLurkerMode");
const elCfgReactiveSnipeOwnRolls = document.getElementById("cfgReactiveSnipeOwnRolls");
const elCfgAutoFreeClaim = document.getElementById("cfgAutoFreeClaim");
const elCfgAutoRtAfterClaim = document.getElementById("cfgAutoRtAfterClaim");
const elCfgHumanizationEnabled = document.getElementById("cfgHumanizationEnabled");
const elCfgAutoRollsEnabled = document.getElementById("cfgAutoRollsEnabled");
const elCfgAutoMkEnabled = document.getElementById("cfgAutoMkEnabled");
const elCfgAutoUsEnabled = document.getElementById("cfgAutoUsEnabled");

// Wishlist & Snipe Tab Elements
const elCountWishlistChars = document.getElementById("countWishlistChars");
const elInputAddWishlistChar = document.getElementById("inputAddWishlistChar");
const elBtnAddWishlistChar = document.getElementById("btnAddWishlistChar");
const elBtnClearWishlistChars = document.getElementById("btnClearWishlistChars");
const elChipsWishlistChars = document.getElementById("chipsWishlistChars");

const elCountSeriesWishlist = document.getElementById("countSeriesWishlist");
const elInputAddSeriesWishlist = document.getElementById("inputAddSeriesWishlist");
const elBtnAddSeriesWishlist = document.getElementById("btnAddSeriesWishlist");
const elBtnClearSeriesWishlist = document.getElementById("btnClearSeriesWishlist");
const elChipsSeriesWishlist = document.getElementById("chipsSeriesWishlist");

const elCountAvoidChars = document.getElementById("countAvoidChars");
const elInputAddAvoidChar = document.getElementById("inputAddAvoidChar");
const elBtnAddAvoidChar = document.getElementById("btnAddAvoidChar");
const elBtnClearAvoidChars = document.getElementById("btnClearAvoidChars");
const elChipsAvoidChars = document.getElementById("chipsAvoidChars");

const elCfgSnipeDelay = document.getElementById("cfgSnipeDelay");
const elCfgSeriesSnipeDelay = document.getElementById("cfgSeriesSnipeDelay");
const elCfgKakeraSnipeThreshold = document.getElementById("cfgKakeraSnipeThreshold");
const elCfgSnipeMode = document.getElementById("cfgSnipeMode");
const elCfgSeriesSnipeMode = document.getElementById("cfgSeriesSnipeMode");
const elCfgSnipeIgnoreMinKakera = document.getElementById("cfgSnipeIgnoreMinKakera");
const elCfgKakeraSnipeMode = document.getElementById("cfgKakeraSnipeMode");
const elCfgCollectPurpleKakera = document.getElementById("cfgCollectPurpleKakera");
const elCfgImmediateKakeraClick = document.getElementById("cfgImmediateKakeraClick");
const elBtnQuickSyncWlTab = document.getElementById("btnQuickSyncWlTab");
const elBtnSaveWishlistTab = document.getElementById("btnSaveWishlistTab");

// Automation Elements
const elChkAutoBadges = document.getElementById("chkAutoBadges");
const elSelBadgeStrategy = document.getElementById("selBadgeStrategy");
const elSelBadgeMaxTier = document.getElementById("selBadgeMaxTier");
const elChkAutoTower = document.getElementById("chkAutoTower");
const elNumTowerMaxFloors = document.getElementById("numTowerMaxFloors");
const elSelLootMode = document.getElementById("selLootMode");
const elNumKlAmount = document.getElementById("numKlAmount");
const elNumLootMinCd = document.getElementById("numLootMinCd");
const elNumLootMaxCd = document.getElementById("numLootMaxCd");
const elTxtScrapTargetId = document.getElementById("txtScrapTargetId");
const elNumScrapAmount = document.getElementById("numScrapAmount");

const elChkAutoOh = document.getElementById("chkAutoOh");
const elChkAutoOc = document.getElementById("chkAutoOc");
const elChkAutoOq = document.getElementById("chkAutoOq");
const elChkAutoOt = document.getElementById("chkAutoOt");
const elChkOhIndividually = document.getElementById("chkOhIndividually");
const elChkOcCollectAfterRed = document.getElementById("chkOcCollectAfterRed");
const elNumOhExploreClicks = document.getElementById("numOhExploreClicks");

const elChkAutoDk = document.getElementById("chkAutoDk");
const elChkDkPowerManagement = document.getElementById("chkDkPowerManagement");
const elNumMaxDkPower = document.getElementById("numMaxDkPower");
const elNumAutoDkMinPower = document.getElementById("numAutoDkMinPower");
const elTxtDkScheduleTime = document.getElementById("txtDkScheduleTime");

const elNumAutoUsLimit = document.getElementById("numAutoUsLimit");
const elNumAutoRollsLimit = document.getElementById("numAutoRollsLimit");
const elChkAutoUsStopOnClaim = document.getElementById("chkAutoUsStopOnClaim");
const elChkBulkUsEnabled = document.getElementById("chkBulkUsEnabled");
const elChkAutoMkFullPowerOnly = document.getElementById("chkAutoMkFullPowerOnly");
const elChkAutoRollsOnlyClaimHour = document.getElementById("chkAutoRollsOnlyClaimHour");

const elChkOnlyChaos = document.getElementById("chkOnlyChaos");
const elChkWishStarwishKakeraOnly = document.getElementById("chkWishStarwishKakeraOnly");
const elChkPerkEightOnly = document.getElementById("chkPerkEightOnly");
const elChkShopPerk7Only = document.getElementById("chkShopPerk7Only");
const elChkMkOnly = document.getElementById("chkMkOnly");

const elChkHybridPanicClaim = document.getElementById("chkHybridPanicClaim");
const elNumPanicRollMinutes = document.getElementById("numPanicRollMinutes");
const elNumPanicMinKakera = document.getElementById("numPanicMinKakera");
const elNumPanicMaxRank = document.getElementById("numPanicMaxRank");

const elChkAutoWishlistSync = document.getElementById("chkAutoWishlistSync");
const elNumWishlistSyncHours = document.getElementById("numWishlistSyncHours");
const elChkWishlistRemoveClaimed = document.getElementById("chkWishlistRemoveClaimed");
const elBtnSyncWlNow = document.getElementById("btnSyncWlNow");
const elChkAutoGiveCharacters = document.getElementById("chkAutoGiveCharacters");
const elTxtMainAccountId = document.getElementById("txtMainAccountId");
const elNumGiveKakeraThreshold = document.getElementById("numGiveKakeraThreshold");
const elChkAutoGiveKakera = document.getElementById("chkAutoGiveKakera");
const elChkAutoDivorce = document.getElementById("chkAutoDivorce");
const elNumDivorceMaxKakera = document.getElementById("numDivorceMaxKakera");
const elChkDivorceProtectWishes = document.getElementById("chkDivorceProtectWishes");

const elChkFarmCharacterEnabled = document.getElementById("chkFarmCharacterEnabled");
const elTxtFarmCharacters = document.getElementById("txtFarmCharacters");
const elTxtForcedivorceChannelId = document.getElementById("txtForcedivorceChannelId");
const elChkFarmFdBeforeRoll = document.getElementById("chkFarmFdBeforeRoll");
const elChkFarmFdAfterClaim = document.getElementById("chkFarmFdAfterClaim");

const elChkAutoLimroul = document.getElementById("chkAutoLimroul");
const elChkAutoDailies = document.getElementById("chkAutoDailies");
const elChkPauseOnKeyLimit = document.getElementById("chkPauseOnKeyLimit");

const elTxtInactiveHours = document.getElementById("txtInactiveHours");
const elNumHumanWindowMins = document.getElementById("numHumanWindowMins");
const elNumHumanInactivitySecs = document.getElementById("numHumanInactivitySecs");

const elBtnSaveAutomation = document.getElementById("btnSaveAutomation");
const elBtnSaveAutomationTop = document.getElementById("btnSaveAutomationTop");

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
const elCfgSkipInitialCommands = document.getElementById("cfgSkipInitialCommands");
const elCfgDebugMode = document.getElementById("cfgDebugMode");
const elBtnSaveGeneralSettings = document.getElementById("btnSaveGeneralSettings");

// Toast Notification Helper
function showToast(message, type = "info") {
  const container = document.getElementById("toastContainer");
  if (!container) return;
  const toast = document.createElement("div");
  toast.className = `toast-msg toast-${type}`;
  toast.textContent = message.toLowerCase();
  container.appendChild(toast);
  setTimeout(() => {
    toast.remove();
  }, 3500);
}

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

// Show/Hide Token
if (elBtnToggleTokenVis) {
  elBtnToggleTokenVis.addEventListener("click", () => {
    if (elCfgToken.type === "password") {
      elCfgToken.type = "text";
      elBtnToggleTokenVis.textContent = "hide";
    } else {
      elCfgToken.type = "password";
      elBtnToggleTokenVis.textContent = "show";
    }
  });
}

// Format seconds to human string (lowercase)
function formatSeconds(secs) {
  if (secs == null || secs <= 0) return "ready";
  const m = Math.floor(secs / 60);
  const s = secs % 60;
  if (m >= 60) {
    const h = Math.floor(m / 60);
    return `${h}h ${m % 60}m`;
  }
  return `${m}m ${s < 10 ? '0' : ''}${s}s`;
}

// Check if log matches active filter & search
function logMatchesFilter(level, text) {
  const lvl = (level || "info").toLowerCase();
  if (activeLogFilter !== "all") {
    if (activeLogFilter === "warn") {
      if (lvl !== "warn" && lvl !== "warning" && lvl !== "error") return false;
    } else if (lvl !== activeLogFilter) {
      return false;
    }
  }
  if (logSearchQuery && !text.toLowerCase().includes(logSearchQuery)) {
    return false;
  }
  return true;
}

function refreshLogFiltering() {
  const lines = elConsoleLogStream.querySelectorAll(".log-line");
  lines.forEach(line => {
    const lvl = line.dataset.level || "info";
    const txt = line.textContent || "";
    if (logMatchesFilter(lvl, txt)) {
      line.classList.remove("hidden-log");
    } else {
      line.classList.add("hidden-log");
    }
  });
}

// Terminal Filter Pills
document.querySelectorAll(".filter-pill").forEach(pill => {
  pill.addEventListener("click", () => {
    document.querySelectorAll(".filter-pill").forEach(p => p.classList.remove("active"));
    pill.classList.add("active");
    activeLogFilter = pill.dataset.filter || "all";
    refreshLogFiltering();
  });
});

if (elTerminalSearchInput) {
  elTerminalSearchInput.addEventListener("input", () => {
    logSearchQuery = elTerminalSearchInput.value.trim().toLowerCase();
    refreshLogFiltering();
  });
}

if (elBtnAutoScroll) {
  elBtnAutoScroll.addEventListener("click", () => {
    autoScrollEnabled = !autoScrollEnabled;
    elBtnAutoScroll.classList.toggle("active", autoScrollEnabled);
  });
}

// Append log entry to terminal
function appendConsoleLog(type, text, timeStr) {
  if (!text) return;
  const lvl = (type || "info").toLowerCase();
  let formattedTime = new Date().toLocaleTimeString().toLowerCase();
  if (timeStr && timeStr !== "invalid date") {
    formattedTime = timeStr;
  }
  const line = document.createElement("div");
  line.dataset.level = lvl;
  const fullText = `[${formattedTime}] [${lvl}] ${text}`;
  line.className = `log-line ${lvl}${logMatchesFilter(lvl, fullText) ? "" : " hidden-log"}`;
  line.textContent = fullText;
  elConsoleLogStream.appendChild(line);

  // Cap DOM log lines at 600 to prevent browser lag over 24/7 uptime
  while (elConsoleLogStream.children.length > 600) {
    elConsoleLogStream.removeChild(elConsoleLogStream.firstChild);
  }

  if (autoScrollEnabled) {
    elConsoleLogStream.scrollTop = elConsoleLogStream.scrollHeight;
  }
}

elBtnClearConsole.addEventListener("click", () => {
  elConsoleLogStream.innerHTML = "";
});

if (elBtnExportLogs) {
  elBtnExportLogs.addEventListener("click", () => {
    const lines = Array.from(elConsoleLogStream.querySelectorAll(".log-line"))
      .map(el => el.textContent)
      .join("\n");
    const blob = new Blob([lines], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `mudademote-logs-${activePresetName}-${Date.now()}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  });
}

// Render Session Claims & Kakera Feeds
function renderActivityFeeds(status) {
  if (!status) return;
  if (elBadgeSessionClaims) {
    const cCount = status.session_claims_count || 0;
    elBadgeSessionClaims.textContent = `${cCount} claimed`;
  }
  if (elBadgeSessionKakera) {
    const kTotal = status.session_kakera_total || 0;
    elBadgeSessionKakera.textContent = `${kTotal} kakera`;
  }

  if (elRecentClaimsList && Array.isArray(status.recent_claims)) {
    if (status.recent_claims.length === 0) {
      elRecentClaimsList.innerHTML = `<div class="feed-empty">no character claims recorded in this session yet.</div>`;
    } else {
      elRecentClaimsList.innerHTML = status.recent_claims.slice(0, 8).map(c => {
        const ts = c.timestamp ? new Date(c.timestamp).toLocaleTimeString().toLowerCase() : "";
        const val = c.value ? ` • ${c.value} ka` : "";
        return `<div class="activity-item">
          <span class="activity-item-main">${(c.character || "character").toLowerCase()}</span>
          <span class="activity-item-meta">${(c.reason || "claimed").toLowerCase()}${val} • ${ts}</span>
        </div>`;
      }).join("");
    }
  }

  if (elRecentKakeraList && Array.isArray(status.recent_kakera)) {
    if (status.recent_kakera.length === 0) {
      elRecentKakeraList.innerHTML = `<div class="feed-empty">no kakera reactions collected in this session yet.</div>`;
    } else {
      elRecentKakeraList.innerHTML = status.recent_kakera.slice(0, 8).map(k => {
        const ts = k.timestamp ? new Date(k.timestamp).toLocaleTimeString().toLowerCase() : "";
        const val = k.value ? `+${k.value} ka` : (k.type || "kakera");
        return `<div class="activity-item">
          <span class="activity-item-main">${(k.character || k.type || "kakera").toLowerCase()}</span>
          <span class="activity-item-meta">${String(val).toLowerCase()} • ${ts}</span>
        </div>`;
      }).join("");
    }
  }
}

// Apply Status to Pterodactyl UI
function applyServerStatus(status) {
  if (!status) return;
  lastStatusSnapshot = status;

  // Breadcrumb
  if (status.preset_name) {
    elServerBreadcrumb.textContent = status.preset_name.toLowerCase();
  }

  // Status Badge & Pause Button Label
  const label = (status.status_label || (status.running ? (status.paused ? "paused" : "running") : "offline")).toLowerCase();
  if (elBtnPowerPause) {
    elBtnPowerPause.textContent = status.paused ? "resume" : "pause";
  }

  if (label === "running") {
    elStatusBadge.className = "status-badge online";
    elStatusLabel.textContent = "running";
  } else if (label === "starting") {
    elStatusBadge.className = "status-badge starting";
    elStatusLabel.textContent = "starting...";
  } else if (label === "paused") {
    elStatusBadge.className = "status-badge paused";
    elStatusLabel.textContent = "paused";
  } else if (label === "stopping") {
    elStatusBadge.className = "status-badge starting";
    elStatusLabel.textContent = "stopping...";
  } else {
    elStatusBadge.className = "status-badge offline";
    elStatusLabel.textContent = "offline";
  }

  // 1. Kakera Power Metric
  const pwr = status.kakera_power != null ? status.kakera_power : 0;
  elMetricPowerText.textContent = `${pwr}%`;
  elMetricPowerValue.textContent = `${pwr}%`;
  elMetricPowerBar.style.width = `${Math.min(100, Math.max(0, pwr))}%`;
  if (elMetricPowerSub) {
    const cost = status.kakera_consumption ? `${status.kakera_consumption}%` : "--";
    const sKakera = status.session_kakera_total || 0;
    elMetricPowerSub.textContent = `click cost: ${cost} • session: +${sKakera} ka`;
  }

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
  const rtTag = status.rt_available ? " • $rt ready" : "";
  elMetricClaimReset.textContent = (status.claim_reset_seconds > 0
    ? `cooldown: ${formatSeconds(status.claim_reset_seconds)}`
    : "claim: ready") + rtTag;

  // 4. Server Allocation Metric
  if (elMetricActivityBadge) {
    elMetricActivityBadge.textContent = (status.activity || (status.running ? "online" : "offline")).toLowerCase();
  }
  const userPart = status.user || "disconnected";
  const guildPart = status.guild_name ? ` (${status.guild_name})` : "";
  elMetricGuildName.textContent = `${userPart}${guildPart}`.toLowerCase();

  const chDisplay = status.channel_name
    ? `#${status.channel_name} (${status.channel_id})`
    : (status.channel_id ? `id: ${status.channel_id}` : "unconfigured");
  const memInfo = status.memory_mb ? ` • ${status.memory_mb}mb` : "";
  elMetricChannelName.textContent = `channel: ${chDisplay}${memInfo}`.toLowerCase();

  renderActivityFeeds(status);
}

// Smooth 1-second local countdown tick between server polls
setInterval(() => {
  if (!lastStatusSnapshot || !lastStatusSnapshot.running) return;
  if (lastStatusSnapshot.roll_reset_seconds > 0) {
    lastStatusSnapshot.roll_reset_seconds -= 1;
    elMetricRollsReset.textContent = `reset in: ${formatSeconds(lastStatusSnapshot.roll_reset_seconds)}`;
  }
  if (lastStatusSnapshot.claim_reset_seconds > 0) {
    lastStatusSnapshot.claim_reset_seconds -= 1;
    const rtTag = lastStatusSnapshot.rt_available ? " • $rt ready" : "";
    elMetricClaimReset.textContent = `cooldown: ${formatSeconds(lastStatusSnapshot.claim_reset_seconds)}${rtTag}`;
  }
}, 1000);

// Dispatch Mudae Command
async function dispatchCommand(cmd) {
  const cleanCmd = cmd.trim();
  if (!cleanCmd) return;
  if (!cmdHistory.length || cmdHistory[cmdHistory.length - 1] !== cleanCmd) {
    cmdHistory.push(cleanCmd);
  }
  cmdHistoryIndex = cmdHistory.length;
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
      showToast(json.error || "failed to send command", "error");
    }
  } catch (err) {
    appendConsoleLog("error", `command error: ${err.message}`);
  }
}

// Terminal Command Input Handling + Up/Down History
elBtnTerminalSend.addEventListener("click", () => {
  dispatchCommand(elTerminalCmdInput.value);
  elTerminalCmdInput.value = "";
});

elTerminalCmdInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") {
    dispatchCommand(elTerminalCmdInput.value);
    elTerminalCmdInput.value = "";
  } else if (e.key === "ArrowUp") {
    if (cmdHistory.length > 0 && cmdHistoryIndex > 0) {
      e.preventDefault();
      cmdHistoryIndex -= 1;
      elTerminalCmdInput.value = cmdHistory[cmdHistoryIndex];
    }
  } else if (e.key === "ArrowDown") {
    if (cmdHistory.length > 0 && cmdHistoryIndex < cmdHistory.length - 1) {
      e.preventDefault();
      cmdHistoryIndex += 1;
      elTerminalCmdInput.value = cmdHistory[cmdHistoryIndex];
    } else if (cmdHistoryIndex >= cmdHistory.length - 1) {
      cmdHistoryIndex = cmdHistory.length;
      elTerminalCmdInput.value = "";
    }
  }
});

// Quick action chips
document.querySelectorAll(".chip-action[data-cmd]").forEach(chip => {
  chip.addEventListener("click", () => {
    dispatchCommand(chip.dataset.cmd);
  });
});

// Wake Loop Chip
if (elBtnWakeLoop) {
  elBtnWakeLoop.addEventListener("click", async () => {
    appendConsoleLog("system", "waking status/roll loop immediately...");
    try {
      const res = await fetch("/api/actions/wake", { method: "POST" });
      const json = await res.json();
      if (json.success) {
        showToast("woke bot loop for immediate check", "success");
      } else {
        appendConsoleLog("warn", json.error || "bot not connected");
        showToast(json.error || "bot not connected", "error");
      }
    } catch (err) {
      appendConsoleLog("error", err.message);
    }
  });
}

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
      appendConsoleLog("system", json.message || "start sequence dispatched successfully.");
      showToast(json.message || "bot starting", "success");
    } else {
      appendConsoleLog("error", json.error || "start failed.");
      showToast(json.error || "start failed", "error");
    }
  } catch (err) {
    appendConsoleLog("error", err.message);
  }
});

if (elBtnPowerPause) {
  elBtnPowerPause.addEventListener("click", async () => {
    try {
      const res = await fetch("/api/bot/pause", { method: "POST" });
      const json = await res.json();
      if (json.success) {
        const stateStr = json.paused ? "paused" : "resumed";
        appendConsoleLog("system", `bot ${stateStr}.`);
        showToast(`bot ${stateStr}`, "success");
      } else {
        appendConsoleLog("warn", json.error || "cannot pause while offline");
        showToast(json.error || "bot is offline", "error");
      }
    } catch (err) {
      appendConsoleLog("error", err.message);
    }
  });
}

elBtnPowerRestart.addEventListener("click", async () => {
  appendConsoleLog("system", `restarting bot with fresh config for '${activePresetName}'...`);
  try {
    const res = await fetch("/api/bot/restart", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ preset_name: activePresetName }),
    });
    const json = await res.json();
    if (json.success) {
      appendConsoleLog("system", "restart sequence triggered with latest saved settings.");
      showToast("bot restarting with fresh config", "success");
    } else {
      appendConsoleLog("error", json.error || "restart failed.");
      showToast(json.error || "restart failed", "error");
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
      showToast("bot stopped", "info");
    } else {
      appendConsoleLog("error", json.error || "stop failed.");
    }
  } catch (err) {
    appendConsoleLog("error", err.message);
  }
});

// ============================================================================
// Wishlist, Series & Avoid Chip Manager
// ============================================================================

function parseCharacterInputEntries(rawText) {
  if (!rawText) return [];
  return rawText
    .split(/[\r\n,]+/)
    .map(line => {
      // Strip Mudae $wl / $wll prefixes, numbering, and status markers
      return line
        .replace(/^\s*\d+[\.\)]\s*/, "")
        .replace(/[❤️💕💖⭐🔐✅❌]/g, "")
        .replace(/\s*\([^)]*\)\s*$/, "") // optional trailing series in parens if pasted from $wl
        .trim();
    })
    .filter(Boolean);
}

function renderChipList(container, countEl, items, isAvoid, onRemove) {
  if (countEl) countEl.textContent = String(items.length);
  if (!container) return;
  if (!items.length) {
    container.innerHTML = `<span class="field-hint">empty list. add items above.</span>`;
    return;
  }
  container.innerHTML = "";
  items.forEach((item, idx) => {
    const chip = document.createElement("span");
    chip.className = `wish-chip${isAvoid ? " chip-avoid" : ""}`;
    chip.innerHTML = `<span>${item}</span><button type="button" class="wish-chip-remove" title="remove">&times;</button>`;
    chip.querySelector(".wish-chip-remove").addEventListener("click", () => {
      onRemove(idx);
    });
    container.appendChild(chip);
  });
}

function renderAllWishlistChips() {
  renderChipList(elChipsWishlistChars, elCountWishlistChars, wishlistCharacters, false, (idx) => {
    wishlistCharacters.splice(idx, 1);
    renderAllWishlistChips();
  });
  renderChipList(elChipsSeriesWishlist, elCountSeriesWishlist, seriesWishlist, false, (idx) => {
    seriesWishlist.splice(idx, 1);
    renderAllWishlistChips();
  });
  renderChipList(elChipsAvoidChars, elCountAvoidChars, avoidCharacters, true, (idx) => {
    avoidCharacters.splice(idx, 1);
    renderAllWishlistChips();
  });
}

function addItemsToArray(targetArr, rawInput) {
  const entries = parseCharacterInputEntries(rawInput);
  const existingLower = new Set(targetArr.map(x => x.toLowerCase()));
  entries.forEach(entry => {
    if (!existingLower.has(entry.toLowerCase())) {
      targetArr.push(entry);
      existingLower.add(entry.toLowerCase());
    }
  });
  renderAllWishlistChips();
}

if (elBtnAddWishlistChar) {
  elBtnAddWishlistChar.addEventListener("click", () => {
    addItemsToArray(wishlistCharacters, elInputAddWishlistChar.value);
    elInputAddWishlistChar.value = "";
  });
  elInputAddWishlistChar.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      addItemsToArray(wishlistCharacters, elInputAddWishlistChar.value);
      elInputAddWishlistChar.value = "";
    }
  });
}
if (elBtnClearWishlistChars) {
  elBtnClearWishlistChars.addEventListener("click", () => {
    wishlistCharacters = [];
    renderAllWishlistChips();
  });
}

if (elBtnAddSeriesWishlist) {
  elBtnAddSeriesWishlist.addEventListener("click", () => {
    addItemsToArray(seriesWishlist, elInputAddSeriesWishlist.value);
    elInputAddSeriesWishlist.value = "";
  });
  elInputAddSeriesWishlist.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      addItemsToArray(seriesWishlist, elInputAddSeriesWishlist.value);
      elInputAddSeriesWishlist.value = "";
    }
  });
}
if (elBtnClearSeriesWishlist) {
  elBtnClearSeriesWishlist.addEventListener("click", () => {
    seriesWishlist = [];
    renderAllWishlistChips();
  });
}

if (elBtnAddAvoidChar) {
  elBtnAddAvoidChar.addEventListener("click", () => {
    addItemsToArray(avoidCharacters, elInputAddAvoidChar.value);
    elInputAddAvoidChar.value = "";
  });
  elInputAddAvoidChar.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      addItemsToArray(avoidCharacters, elInputAddAvoidChar.value);
      elInputAddAvoidChar.value = "";
    }
  });
}
if (elBtnClearAvoidChars) {
  elBtnClearAvoidChars.addEventListener("click", () => {
    avoidCharacters = [];
    renderAllWishlistChips();
  });
}

// Populate Preset Forms
function populatePresetData(data) {
  if (!data) return;

  // Visual Config
  elCfgToken.value = data.token || "";
  elCfgChannelId.value = data.channel_id || "";
  elCfgCmdChannelId.value = data.command_channel_id || "";
  if (elCfgMudaePrefix) elCfgMudaePrefix.value = data.mudae_prefix || "$";
  elCfgRollCommand.value = (data.roll_command || "wa").toLowerCase();
  elCfgMinKakera.value = data.min_kakera != null ? data.min_kakera : 100;
  if (elCfgMaxClaimRank) elCfgMaxClaimRank.value = data.max_claim_rank != null ? data.max_claim_rank : 0;
  if (elCfgMaxLikeRank) elCfgMaxLikeRank.value = data.max_like_rank != null ? data.max_like_rank : 0;
  elCfgRollSpeed.value = data.roll_speed != null ? data.roll_speed : 0.4;
  elCfgClaimInterval.value = data.claim_interval != null ? data.claim_interval : 180;
  elCfgRollInterval.value = data.roll_interval != null ? data.roll_interval : 60;
  if (elCfgStartDelay) elCfgStartDelay.value = data.start_delay != null ? data.start_delay : 0;

  // Core Gameplay Toggles
  if (elCfgRollingEnabled) elCfgRollingEnabled.checked = data.rolling !== false;
  if (elCfgUseSlashRolls) elCfgUseSlashRolls.checked = !!data.use_slash_rolls;
  if (elCfgTimeRollsToReset) elCfgTimeRollsToReset.checked = !!data.time_rolls_to_claim_reset;
  if (elCfgKeyMode) elCfgKeyMode.checked = !!data.key_mode;
  if (elCfgLurkerMode) elCfgLurkerMode.checked = !!data.lurker_mode;
  if (elCfgReactiveSnipeOwnRolls) elCfgReactiveSnipeOwnRolls.checked = data.reactive_snipe_on_own_rolls !== false;
  if (elCfgAutoFreeClaim) elCfgAutoFreeClaim.checked = data.auto_free_claim !== false;
  if (elCfgAutoRtAfterClaim) elCfgAutoRtAfterClaim.checked = !!data.auto_rt_after_claim;
  if (elCfgHumanizationEnabled) elCfgHumanizationEnabled.checked = !!data.humanization_enabled;
  if (elCfgAutoRollsEnabled) elCfgAutoRollsEnabled.checked = data.auto_rolls_enabled !== false;
  if (elCfgAutoMkEnabled) elCfgAutoMkEnabled.checked = !!data.auto_mk_enabled;
  if (elCfgAutoUsEnabled) elCfgAutoUsEnabled.checked = !!data.auto_us_enabled;

  // Wishlist & Snipe Tab (support both wishlist/characters and avoid_list/avoid_characters)
  const rawWl = Array.isArray(data.wishlist) ? data.wishlist : (Array.isArray(data.characters) ? data.characters : []);
  const rawAvoid = Array.isArray(data.avoid_list) ? data.avoid_list : (Array.isArray(data.avoid_characters) ? data.avoid_characters : []);
  wishlistCharacters = [...rawWl];
  seriesWishlist = Array.isArray(data.series_wishlist) ? [...data.series_wishlist] : [];
  avoidCharacters = [...rawAvoid];
  renderAllWishlistChips();

  if (elCfgSnipeDelay) elCfgSnipeDelay.value = data.snipe_delay != null ? data.snipe_delay : 2.0;
  if (elCfgSeriesSnipeDelay) elCfgSeriesSnipeDelay.value = data.series_snipe_delay != null ? data.series_snipe_delay : 3.0;
  if (elCfgKakeraSnipeThreshold) elCfgKakeraSnipeThreshold.value = data.kakera_snipe_threshold != null ? data.kakera_snipe_threshold : 0;
  if (elCfgSnipeMode) elCfgSnipeMode.checked = !!data.snipe_mode;
  if (elCfgSeriesSnipeMode) elCfgSeriesSnipeMode.checked = !!data.series_snipe_mode;
  if (elCfgSnipeIgnoreMinKakera) elCfgSnipeIgnoreMinKakera.checked = !!data.snipe_ignore_min_kakera_reset;
  if (elCfgKakeraSnipeMode) elCfgKakeraSnipeMode.checked = !!data.kakera_snipe_mode;
  if (elCfgCollectPurpleKakera) elCfgCollectPurpleKakera.checked = data.collect_purple_kakera !== false;
  if (elCfgImmediateKakeraClick) elCfgImmediateKakeraClick.checked = data.immediate_kakera_click !== false;

  // Raw JSON editor
  elRawJsonEditor.value = JSON.stringify(data, null, 2);

  // Automation Suite (14 Feature Modules)
  elChkAutoBadges.checked = !!data.auto_badges_enabled;
  elSelBadgeStrategy.value = data.badge_strategy || "optimal";
  elSelBadgeMaxTier.value = String(data.badge_max_tier || 4);
  elChkAutoTower.checked = !!data.auto_tower_enabled;
  elNumTowerMaxFloors.value = data.tower_max_floors || 12;

  if (elSelLootMode) elSelLootMode.value = data.loot_mode || "off";
  if (elNumKlAmount) elNumKlAmount.value = data.kl_amount != null ? data.kl_amount : 1000;
  if (elNumLootMinCd) elNumLootMinCd.value = data.loot_min_cooldown != null ? data.loot_min_cooldown : 30;
  if (elNumLootMaxCd) elNumLootMaxCd.value = data.loot_max_cooldown != null ? data.loot_max_cooldown : 40;
  if (elTxtScrapTargetId) elTxtScrapTargetId.value = data.scrap_target_id || "";
  if (elNumScrapAmount) elNumScrapAmount.value = data.scrap_amount != null ? data.scrap_amount : 100000;

  if (elChkAutoOh) elChkAutoOh.checked = !!data.auto_oh_enabled;
  if (elChkAutoOc) elChkAutoOc.checked = !!data.auto_oc_enabled;
  if (elChkAutoOq) elChkAutoOq.checked = !!data.auto_oq_enabled;
  if (elChkAutoOt) elChkAutoOt.checked = !!data.auto_ot_enabled;
  if (elChkOhIndividually) elChkOhIndividually.checked = !!data.oh_use_individually;
  if (elChkOcCollectAfterRed) elChkOcCollectAfterRed.checked = data.oc_collect_after_red !== false;
  if (elNumOhExploreClicks) elNumOhExploreClicks.value = data.oh_unknown_explore_clicks != null ? data.oh_unknown_explore_clicks : 3;

  if (elChkAutoDk) elChkAutoDk.checked = data.auto_dk_enabled !== false;
  if (elChkDkPowerManagement) elChkDkPowerManagement.checked = !!data.dk_power_management;
  if (elNumMaxDkPower) elNumMaxDkPower.value = data.max_dk_power != null ? data.max_dk_power : 100;
  if (elNumAutoDkMinPower) elNumAutoDkMinPower.value = data.auto_dk_min_power != null ? data.auto_dk_min_power : 0;
  if (elTxtDkScheduleTime) elTxtDkScheduleTime.value = data.dk_schedule_time || "";

  if (elNumAutoUsLimit) elNumAutoUsLimit.value = data.auto_us_limit != null ? data.auto_us_limit : 0;
  if (elNumAutoRollsLimit) elNumAutoRollsLimit.value = data.auto_rolls_limit != null ? data.auto_rolls_limit : 0;
  if (elChkAutoUsStopOnClaim) elChkAutoUsStopOnClaim.checked = data.auto_us_stop_on_claim !== false;
  if (elChkBulkUsEnabled) elChkBulkUsEnabled.checked = !!data.bulk_us_enabled;
  if (elChkAutoMkFullPowerOnly) elChkAutoMkFullPowerOnly.checked = !!data.auto_mk_full_power_only;
  if (elChkAutoRollsOnlyClaimHour) elChkAutoRollsOnlyClaimHour.checked = !!data.auto_rolls_only_claim_hour;

  if (elChkOnlyChaos) elChkOnlyChaos.checked = !!data.only_chaos;
  if (elChkWishStarwishKakeraOnly) elChkWishStarwishKakeraOnly.checked = !!data.wish_starwish_kakera_only;
  if (elChkPerkEightOnly) elChkPerkEightOnly.checked = !!data.perk_eight_only;
  if (elChkShopPerk7Only) elChkShopPerk7Only.checked = !!data.shop_perk_7_only;
  if (elChkMkOnly) elChkMkOnly.checked = !!data.mk_only;

  if (elChkHybridPanicClaim) elChkHybridPanicClaim.checked = !!data.enable_hybrid_panic_claim;
  if (elNumPanicRollMinutes) elNumPanicRollMinutes.value = data.panic_roll_minutes != null ? data.panic_roll_minutes : 5;
  if (elNumPanicMinKakera) elNumPanicMinKakera.value = data.hybrid_panic_instant_claim_min_kakera != null ? data.hybrid_panic_instant_claim_min_kakera : 300;
  if (elNumPanicMaxRank) elNumPanicMaxRank.value = data.hybrid_panic_instant_claim_max_rank != null ? data.hybrid_panic_instant_claim_max_rank : 200;

  elChkAutoWishlistSync.checked = !!data.auto_wishlist_sync_enabled;
  if (elNumWishlistSyncHours) elNumWishlistSyncHours.value = data.wishlist_sync_interval_hours != null ? data.wishlist_sync_interval_hours : 6;
  elChkWishlistRemoveClaimed.checked = !!data.wishlist_remove_claimed;
  elChkAutoGiveCharacters.checked = !!data.auto_give_characters_enabled;
  elTxtMainAccountId.value = data.main_account_id || "";
  if (elNumGiveKakeraThreshold) elNumGiveKakeraThreshold.value = data.auto_give_kakera_threshold != null ? data.auto_give_kakera_threshold : 5000;
  elChkAutoGiveKakera.checked = !!data.auto_give_kakera_enabled;
  if (elChkAutoDivorce) elChkAutoDivorce.checked = !!data.auto_divorce_enabled;
  if (elNumDivorceMaxKakera) elNumDivorceMaxKakera.value = data.auto_divorce_max_kakera != null ? data.auto_divorce_max_kakera : 80;
  if (elChkDivorceProtectWishes) elChkDivorceProtectWishes.checked = data.auto_divorce_protect_wishes !== false;

  if (elChkFarmCharacterEnabled) elChkFarmCharacterEnabled.checked = !!data.farm_character_enabled;
  if (elTxtFarmCharacters) {
    const fcList = Array.isArray(data.farm_characters) ? data.farm_characters : (data.farm_character ? [data.farm_character] : []);
    elTxtFarmCharacters.value = fcList.join(", ");
  }
  if (elTxtForcedivorceChannelId) elTxtForcedivorceChannelId.value = data.forcedivorce_channel_id || "";
  if (elChkFarmFdBeforeRoll) elChkFarmFdBeforeRoll.checked = data.farm_forcedivorce_before_roll !== false;
  if (elChkFarmFdAfterClaim) elChkFarmFdAfterClaim.checked = !!data.farm_forcedivorce_after_claim;

  elChkAutoLimroul.checked = !!data.auto_limroul_enabled;
  elChkAutoDailies.checked = data.auto_p_enabled !== false;
  if (elChkPauseOnKeyLimit) elChkPauseOnKeyLimit.checked = data.pause_on_key_limit !== false;

  if (elTxtInactiveHours) {
    elTxtInactiveHours.value = Array.isArray(data.inactive_hours) ? data.inactive_hours.join(", ") : "";
  }
  if (elNumHumanWindowMins) elNumHumanWindowMins.value = data.humanization_window_minutes != null ? data.humanization_window_minutes : 40;
  if (elNumHumanInactivitySecs) elNumHumanInactivitySecs.value = data.humanization_inactivity_seconds != null ? data.humanization_inactivity_seconds : 5;

  // Settings
  elCfgWebhookUrl.value = data.webhook_url || "";
  if (elCfgSkipInitialCommands) elCfgSkipInitialCommands.checked = !!data.skip_initial_commands;
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

  const current = allPresets[activePresetName] || {};
  syncVisualToPresetObject(current);
  elRawJsonEditor.value = JSON.stringify(current, null, 2);
});

if (elBtnFormatJson) {
  elBtnFormatJson.addEventListener("click", () => {
    try {
      const parsed = JSON.parse(elRawJsonEditor.value);
      elRawJsonEditor.value = JSON.stringify(parsed, null, 2);
      showToast("json formatted", "info");
    } catch (e) {
      showToast(`invalid json: ${e.message}`, "error");
    }
  });
}

function syncVisualToPresetObject(target) {
  if (elCfgToken.value.trim()) {
    target.token = elCfgToken.value.trim().replace(/^["']|["']$/g, "");
  }
  target.channel_id = elCfgChannelId.value.trim();
  target.command_channel_id = elCfgCmdChannelId.value.trim();
  if (elCfgMudaePrefix) target.mudae_prefix = elCfgMudaePrefix.value.trim() || "$";
  target.roll_command = elCfgRollCommand.value.trim() || "wa";
  target.min_kakera = parseInt(elCfgMinKakera.value, 10) || 0;
  if (elCfgMaxClaimRank) target.max_claim_rank = parseInt(elCfgMaxClaimRank.value, 10) || 0;
  if (elCfgMaxLikeRank) target.max_like_rank = parseInt(elCfgMaxLikeRank.value, 10) || 0;
  target.roll_speed = parseFloat(elCfgRollSpeed.value) || 0.4;
  target.claim_interval = parseInt(elCfgClaimInterval.value, 10) || 180;
  target.roll_interval = parseInt(elCfgRollInterval.value, 10) || 60;
  if (elCfgStartDelay) target.start_delay = parseInt(elCfgStartDelay.value, 10) || 0;

  if (elCfgRollingEnabled) target.rolling = elCfgRollingEnabled.checked;
  if (elCfgUseSlashRolls) target.use_slash_rolls = elCfgUseSlashRolls.checked;
  if (elCfgTimeRollsToReset) target.time_rolls_to_claim_reset = elCfgTimeRollsToReset.checked;
  if (elCfgKeyMode) target.key_mode = elCfgKeyMode.checked;
  if (elCfgLurkerMode) target.lurker_mode = elCfgLurkerMode.checked;
  if (elCfgReactiveSnipeOwnRolls) target.reactive_snipe_on_own_rolls = elCfgReactiveSnipeOwnRolls.checked;
  if (elCfgAutoFreeClaim) target.auto_free_claim = elCfgAutoFreeClaim.checked;
  if (elCfgAutoRtAfterClaim) target.auto_rt_after_claim = elCfgAutoRtAfterClaim.checked;
  if (elCfgHumanizationEnabled) target.humanization_enabled = elCfgHumanizationEnabled.checked;
  if (elCfgAutoRollsEnabled) target.auto_rolls_enabled = elCfgAutoRollsEnabled.checked;
  if (elCfgAutoMkEnabled) target.auto_mk_enabled = elCfgAutoMkEnabled.checked;
  if (elCfgAutoUsEnabled) target.auto_us_enabled = elCfgAutoUsEnabled.checked;
}

// Save Configuration
async function saveActivePreset(presetData, restartAfter = false) {
  try {
    const res = await fetch("/api/presets", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: activePresetName, data: presetData }),
    });
    const json = await res.json();
    if (json.success) {
      appendConsoleLog("system", `saved configuration for '${activePresetName}' (live-reloaded).`);
      showToast(`saved '${activePresetName}'`, "success");
      allPresets[activePresetName] = presetData;
      populatePresetData(presetData);
      if (restartAfter) {
        elBtnPowerRestart.click();
      }
    } else {
      const errMsg = json.errors ? json.errors.join(", ") : json.error;
      appendConsoleLog("error", `save failed: ${errMsg}`);
      showToast(`save failed: ${errMsg}`, "error");
    }
  } catch (err) {
    appendConsoleLog("error", `network save error: ${err.message}`);
    showToast(`save error: ${err.message}`, "error");
  }
}

function handleConfigSave(restartAfter = false) {
  if (currentConfigMode === "raw") {
    try {
      const parsed = JSON.parse(elRawJsonEditor.value);
      saveActivePreset(parsed, restartAfter);
    } catch (e) {
      appendConsoleLog("error", `invalid json: ${e.message}`);
      showToast(`invalid json: ${e.message}`, "error");
    }
  } else {
    const current = allPresets[activePresetName] || {};
    syncVisualToPresetObject(current);
    saveActivePreset(current, restartAfter);
  }
}

elBtnSaveConfig.addEventListener("click", () => handleConfigSave(false));
if (elBtnSaveAndRestartConfig) {
  elBtnSaveAndRestartConfig.addEventListener("click", () => handleConfigSave(true));
}

// Save Wishlist & Snipe Settings
if (elBtnSaveWishlistTab) {
  elBtnSaveWishlistTab.addEventListener("click", () => {
    const current = allPresets[activePresetName] || {};
    current.wishlist = [...wishlistCharacters];
    current.characters = [...wishlistCharacters];
    current.series_wishlist = [...seriesWishlist];
    current.avoid_list = [...avoidCharacters];
    current.avoid_characters = [...avoidCharacters];
    current.snipe_delay = parseFloat(elCfgSnipeDelay.value) || 0;
    current.series_snipe_delay = parseFloat(elCfgSeriesSnipeDelay.value) || 0;
    current.kakera_snipe_threshold = parseInt(elCfgKakeraSnipeThreshold.value, 10) || 0;
    current.snipe_mode = elCfgSnipeMode.checked;
    current.series_snipe_mode = elCfgSeriesSnipeMode.checked;
    current.snipe_ignore_min_kakera_reset = elCfgSnipeIgnoreMinKakera.checked;
    current.kakera_snipe_mode = elCfgKakeraSnipeMode.checked;
    current.collect_purple_kakera = elCfgCollectPurpleKakera.checked;
    current.immediate_kakera_click = elCfgImmediateKakeraClick.checked;
    saveActivePreset(current);
  });
}

if (elBtnQuickSyncWlTab) {
  elBtnQuickSyncWlTab.addEventListener("click", () => {
    dispatchCommand("$wll");
    showToast("sent $wll to discord", "info");
  });
}

// Save Automation Settings
function handleSaveAutomation() {
  const current = allPresets[activePresetName] || {};
  current.auto_badges_enabled = elChkAutoBadges.checked;
  current.badge_strategy = elSelBadgeStrategy.value;
  current.badge_max_tier = parseInt(elSelBadgeMaxTier.value, 10) || 4;
  current.auto_tower_enabled = elChkAutoTower.checked;
  current.tower_max_floors = parseInt(elNumTowerMaxFloors.value, 10) || 12;

  if (elSelLootMode) current.loot_mode = elSelLootMode.value;
  if (elNumKlAmount) current.kl_amount = Math.max(1, parseInt(elNumKlAmount.value, 10) || 1000);
  if (elNumLootMinCd) current.loot_min_cooldown = Math.max(1, parseFloat(elNumLootMinCd.value) || 30);
  if (elNumLootMaxCd) current.loot_max_cooldown = Math.max(current.loot_min_cooldown, parseFloat(elNumLootMaxCd.value) || 40);
  if (elTxtScrapTargetId) current.scrap_target_id = elTxtScrapTargetId.value.trim();
  if (elNumScrapAmount) current.scrap_amount = Math.max(1, parseInt(elNumScrapAmount.value, 10) || 100000);

  if (elChkAutoOh) current.auto_oh_enabled = elChkAutoOh.checked;
  if (elChkAutoOc) current.auto_oc_enabled = elChkAutoOc.checked;
  if (elChkAutoOq) current.auto_oq_enabled = elChkAutoOq.checked;
  if (elChkAutoOt) current.auto_ot_enabled = elChkAutoOt.checked;
  if (elChkOhIndividually) current.oh_use_individually = elChkOhIndividually.checked;
  if (elChkOcCollectAfterRed) current.oc_collect_after_red = elChkOcCollectAfterRed.checked;
  if (elNumOhExploreClicks) current.oh_unknown_explore_clicks = Math.max(0, parseInt(elNumOhExploreClicks.value, 10) || 0);

  if (elChkAutoDk) current.auto_dk_enabled = elChkAutoDk.checked;
  if (elChkDkPowerManagement) current.dk_power_management = elChkDkPowerManagement.checked;
  if (elNumMaxDkPower) current.max_dk_power = parseInt(elNumMaxDkPower.value, 10) || 100;
  if (elNumAutoDkMinPower) current.auto_dk_min_power = parseInt(elNumAutoDkMinPower.value, 10) || 0;
  if (elTxtDkScheduleTime) current.dk_schedule_time = elTxtDkScheduleTime.value.trim();

  if (elNumAutoUsLimit) current.auto_us_limit = Math.max(0, parseInt(elNumAutoUsLimit.value, 10) || 0);
  if (elNumAutoRollsLimit) current.auto_rolls_limit = Math.max(0, parseInt(elNumAutoRollsLimit.value, 10) || 0);
  if (elChkAutoUsStopOnClaim) current.auto_us_stop_on_claim = elChkAutoUsStopOnClaim.checked;
  if (elChkBulkUsEnabled) current.bulk_us_enabled = elChkBulkUsEnabled.checked;
  if (elChkAutoMkFullPowerOnly) current.auto_mk_full_power_only = elChkAutoMkFullPowerOnly.checked;
  if (elChkAutoRollsOnlyClaimHour) current.auto_rolls_only_claim_hour = elChkAutoRollsOnlyClaimHour.checked;

  if (elChkOnlyChaos) current.only_chaos = elChkOnlyChaos.checked;
  if (elChkWishStarwishKakeraOnly) current.wish_starwish_kakera_only = elChkWishStarwishKakeraOnly.checked;
  if (elChkPerkEightOnly) current.perk_eight_only = elChkPerkEightOnly.checked;
  if (elChkShopPerk7Only) current.shop_perk_7_only = elChkShopPerk7Only.checked;
  if (elChkMkOnly) current.mk_only = elChkMkOnly.checked;

  if (elChkHybridPanicClaim) current.enable_hybrid_panic_claim = elChkHybridPanicClaim.checked;
  if (elNumPanicRollMinutes) current.panic_roll_minutes = Math.max(1, parseInt(elNumPanicRollMinutes.value, 10) || 5);
  if (elNumPanicMinKakera) current.hybrid_panic_instant_claim_min_kakera = parseInt(elNumPanicMinKakera.value, 10) || 300;
  if (elNumPanicMaxRank) current.hybrid_panic_instant_claim_max_rank = parseInt(elNumPanicMaxRank.value, 10) || 200;

  current.auto_wishlist_sync_enabled = elChkAutoWishlistSync.checked;
  if (elNumWishlistSyncHours) current.wishlist_sync_interval_hours = Math.max(1, parseInt(elNumWishlistSyncHours.value, 10) || 6);
  current.wishlist_remove_claimed = elChkWishlistRemoveClaimed.checked;
  current.auto_give_characters_enabled = elChkAutoGiveCharacters.checked;
  current.main_account_id = elTxtMainAccountId.value.trim();
  if (elNumGiveKakeraThreshold) current.auto_give_kakera_threshold = Math.max(1000, parseInt(elNumGiveKakeraThreshold.value, 10) || 5000);
  current.auto_give_kakera_enabled = elChkAutoGiveKakera.checked;
  if (elChkAutoDivorce) current.auto_divorce_enabled = elChkAutoDivorce.checked;
  if (elNumDivorceMaxKakera) current.auto_divorce_max_kakera = parseInt(elNumDivorceMaxKakera.value, 10) || 80;
  if (elChkDivorceProtectWishes) current.auto_divorce_protect_wishes = elChkDivorceProtectWishes.checked;

  if (elChkFarmCharacterEnabled) current.farm_character_enabled = elChkFarmCharacterEnabled.checked;
  if (elTxtFarmCharacters) {
    const fcList = elTxtFarmCharacters.value.split(",").map(s => s.trim()).filter(Boolean);
    current.farm_characters = fcList;
    current.farm_character = fcList[0] || "";
  }
  if (elTxtForcedivorceChannelId) current.forcedivorce_channel_id = elTxtForcedivorceChannelId.value.trim();
  if (elChkFarmFdBeforeRoll) current.farm_forcedivorce_before_roll = elChkFarmFdBeforeRoll.checked;
  if (elChkFarmFdAfterClaim) current.farm_forcedivorce_after_claim = elChkFarmFdAfterClaim.checked;

  current.auto_limroul_enabled = elChkAutoLimroul.checked;
  current.auto_p_enabled = elChkAutoDailies.checked;
  if (elChkPauseOnKeyLimit) current.pause_on_key_limit = elChkPauseOnKeyLimit.checked;

  if (elTxtInactiveHours) {
    const hours = [];
    elTxtInactiveHours.value.split(",").forEach(part => {
      const p = part.trim();
      if (!p) return;
      if (p.includes("-")) {
        const [start, end] = p.split("-").map(x => parseInt(x.trim(), 10));
        if (!isNaN(start) && !isNaN(end)) {
          for (let h = start; h <= end; h++) {
            if (h >= 0 && h <= 23 && !hours.includes(h)) hours.push(h);
          }
        }
      } else {
        const h = parseInt(p, 10);
        if (!isNaN(h) && h >= 0 && h <= 23 && !hours.includes(h)) hours.push(h);
      }
    });
    current.inactive_hours = hours;
  }
  if (elNumHumanWindowMins) current.humanization_window_minutes = Math.max(5, parseInt(elNumHumanWindowMins.value, 10) || 40);
  if (elNumHumanInactivitySecs) current.humanization_inactivity_seconds = Math.max(0, parseInt(elNumHumanInactivitySecs.value, 10) || 5);

  saveActivePreset(current);
}

elBtnSaveAutomation.addEventListener("click", handleSaveAutomation);
if (elBtnSaveAutomationTop) {
  elBtnSaveAutomationTop.addEventListener("click", handleSaveAutomation);
}

// Save General Settings
elBtnSaveGeneralSettings.addEventListener("click", () => {
  const current = allPresets[activePresetName] || {};
  current.webhook_url = elCfgWebhookUrl.value.trim();
  if (elCfgSkipInitialCommands) current.skip_initial_commands = elCfgSkipInitialCommands.checked;
  current.debug_mode = elCfgDebugMode.checked;
  saveActivePreset(current);
});

// Trigger Wishlist Sync
elBtnSyncWlNow.addEventListener("click", () => {
  dispatchCommand("$wll");
  showToast("dispatched $wll sync command", "info");
});

// ============================================================================
// Multi-Preset Management (+ New / Delete / Select)
// ============================================================================

if (elBtnNewPreset) {
  elBtnNewPreset.addEventListener("click", async () => {
    const newName = prompt("enter a name for the new preset:");
    if (!newName || !newName.trim()) return;
    const cleanName = newName.trim();
    const template = JSON.parse(JSON.stringify(allPresets[activePresetName] || {}));
    activePresetName = cleanName;
    await saveActivePreset(template, false);
    await loadPresetsList();
  });
}

if (elBtnDeletePreset) {
  elBtnDeletePreset.addEventListener("click", async () => {
    if (Object.keys(allPresets).length <= 1) {
      showToast("cannot delete the only remaining preset", "error");
      return;
    }
    if (!confirm(`delete preset '${activePresetName}'?`)) return;
    try {
      const res = await fetch("/api/presets/delete", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: activePresetName }),
      });
      const json = await res.json();
      if (json.success) {
        showToast(`deleted '${activePresetName}'`, "info");
        activePresetName = json.active_preset || Object.keys(allPresets)[0];
        await loadPresetsList();
      } else {
        showToast(json.error || "delete failed", "error");
      }
    } catch (err) {
      showToast(err.message, "error");
    }
  });
}

// ============================================================================
// Multi-Server Discovery & Whitelist Management
// ============================================================================

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

    const toggle = tr.querySelector(".chk-server-allowed");
    toggle.addEventListener("change", async (e) => {
      const allowed = e.target.checked;
      await toggleGuildAccess(g.id, allowed);
    });

    const btnCfg = tr.querySelector(".btn-configure-server");
    btnCfg.addEventListener("click", () => {
      openServerConfig(g.id);
    });

    elServerListBody.appendChild(tr);
  });
}

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
      showToast(`server ${allowed ? 'whitelisted' : 'blocked'}`, "info");
    } else {
      appendConsoleLog("error", json.error || "failed updating whitelist.");
    }
  } catch (err) {
    appendConsoleLog("error", err.message);
  }
}

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
      showToast("all servers allowed", "success");
    }
  } catch (err) {
    appendConsoleLog("error", err.message);
  }
});

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
      showToast("all servers blocked", "info");
    }
  } catch (err) {
    appendConsoleLog("error", err.message);
  }
});

if (elTxtFilterServers) {
  elTxtFilterServers.addEventListener("input", renderServerList);
}

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
      showToast(`found ${json.guilds.length} servers`, "success");
    } else {
      appendConsoleLog("warn", json.error || "could not retrieve servers.");
      showToast(json.error || "start the bot first to scan servers", "error");
    }
  } catch (err) {
    appendConsoleLog("error", err.message);
  } finally {
    elBtnDiscoverServers.disabled = false;
  }
});

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
      showToast(json.error || "failed inspecting channels", "error");
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
        showToast("server rules saved & synced live", "success");
        elServerConfigPanel.classList.add("hidden");
        await loadPresetsList();
      } else {
        appendConsoleLog("error", json.error || "failed saving server rules.");
        showToast(json.error || "failed saving server rules", "error");
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

elPresetSelect.addEventListener("change", async () => {
  activePresetName = elPresetSelect.value;
  elServerBreadcrumb.textContent = activePresetName.toLowerCase();
  if (allPresets[activePresetName]) {
    populatePresetData(allPresets[activePresetName]);
  }
  try {
    await fetch("/api/presets/select", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: activePresetName }),
    });
  } catch (e) {}
});

function formatConsoleEvent(type, data) {
  if (!data) return { text: "", level: (type || "info").toLowerCase() };
  if (typeof data === "string") {
    try {
      const parsed = JSON.parse(data);
      if (parsed && typeof parsed === "object") {
        data = parsed;
      }
    } catch (e) {}
  }
  if (typeof data === "string") {
    return { text: data, level: (type || "info").toLowerCase() };
  }
  if (data.message) {
    const lvl = (data.level || type || "info").toLowerCase();
    const text = typeof data.message === "string" ? data.message : JSON.stringify(data.message);
    return { text: text, level: lvl };
  }
  return { text: JSON.stringify(data), level: (type || "info").toLowerCase() };
}

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
      if (msg.type === "pong") {
        return; // Silent WebSocket heartbeat keepalive
      }
      if (msg.type === "init") {
        applyServerStatus(msg.status);
        if (msg.recent_events) {
          msg.recent_events.forEach(ev => {
            if (!ev || ev.type === "pong" || ev.type === "status") return;
            const formatted = formatConsoleEvent(ev.type, ev.data);
            const ts = ev.timestamp ? new Date(ev.timestamp).toLocaleTimeString().toLowerCase() : undefined;
            appendConsoleLog(formatted.level, formatted.text, ts);
          });
        }
      } else if (msg.type === "status") {
        applyServerStatus(msg.data);
      } else {
        const formatted = formatConsoleEvent(msg.type, msg.data);
        const ts = msg.timestamp ? new Date(msg.timestamp).toLocaleTimeString().toLowerCase() : undefined;
        appendConsoleLog(formatted.level, formatted.text, ts);
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
}, 3000);
