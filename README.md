<p align="center">
  <h1 align="center">⚡ MudaDemote</h1>
  <p align="center">
    <strong>high-performance, 24/7 headless discord automation daemon &amp; web dashboard for mudae</strong>
  </p>
  <p align="center">
    engineered for 24/7 server deployments (aws ec2 / linux systemd / docker / local) with zero desktop gui dependencies.
  </p>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.14-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python Version">
  <img src="https://img.shields.io/badge/platform-linux%20%7C%20aws%20ec2%20%7C%20windows-0078D6?style=for-the-badge&logo=linux&logoColor=white" alt="Platform">
  <img src="https://img.shields.io/badge/ui-i want to die%20off--white-0969da?style=for-the-badge&logo=pterodactyl&logoColor=white" alt="Dashboard UI">
  <img src="https://img.shields.io/badge/telemetry-live%20websocket-22c55e?style=for-the-badge&logo=websocket&logoColor=white" alt="WebSocket Telemetry">
  <img src="https://img.shields.io/badge/license-MIT-yellow?style=for-the-badge" alt="License">
</p>

---

## 📖 Overview

**MudaDemote** is a modern fork of MudaRemote rebuilt specifically for **headless 24/7 operation** on cloud virtual servers (AWS EC2, VPS, Debian/Ubuntu) and local background tasks.

It replaces heavy local desktop GUIs with a sleek, low-latency, off-white **Pterodactyl-inspired Web Dashboard** (`aiohttp` + WebSocket). You get real-time terminal streaming, live power controls, instant hot-reloading preset configuration, multi-server channel routing, advanced humanization behaviors, and full mobile optimization.

> [!WARNING]
> **self-bot disclaimer**: automated discord accounts violate discord's terms of service. use at your own discretion on accounts you can afford to lose. mudademote includes extensive humanization behaviors to blend with natural chatter, but no self-bot is ever 100% immune to detection.

---

## ✨ Key Features

### 🖥️ Pterodactyl-Inspired Web Dashboard
- **clean off-white aesthetic**: uncluttered, minimalist dashboard with lowercase typography and intuitive card layouts.
- **live websocket console**: real-time log streaming with instant log-level filtering (`all`, `info`, `claim`, `kakera`, `warn`, `error`), live search, auto-scroll, and log export.
- **live telemetry cards**: Kakera Power % gauge, Rolls Left counter with reset countdown, Claim Cooldown timer with `$rt` readiness indicator, and server allocation metrics.
- **recent activity feeds**: tracks character claims with verified **kakera values** (`+450 ka`) and kakera reaction gains in real-time.
- **live hot-reloading**: save settings or modify whitelists on the fly—the running bot updates immediately without restart.
- **100% mobile optimized**: touch-friendly 4-column power controls, swipeable tab navigation, 2×2 metrics overview, and responsive single-column form collapse.

---

### 🧠 Humanization & Anti-Detection Suite
- **post-claim randomized chat pool**: send natural reactions after claims with dynamic tags: `{char}`, `{series}`, and `{kakera}`.
- **active-peer presence detection**: toggle `claim_chat_only_when_others_active` to only speak if another human user talked in the channel within a configurable lookback window—preventing speaking into an empty channel.
- **simulated discord typing indicator**: triggers Discord's native `"is typing..."` indicator for a realistic duration before sending chat reactions.
- **kakera snipe chat reactions**: randomized congratulatory or stealth snipes after claiming kakera from external users' rolls.
- **roll cadence jitter & reading micro-pauses**: randomizes interval delays (`±%`) around base roll speed and simulates natural pauses to "read" character embeds.
- **button reflex delays**: humanized click delays on claim and kakera buttons to prevent 0ms superhuman reaction flags.
- **human sleep schedules**: specify inactive time windows (e.g. `02:00–07:30`) where the bot goes completely dark.

---

### 📡 Multi-Server Auto-Discovery & Whitelist
- **gateway server scanning**: automatically inspects all joined guilds via Discord gateway.
- **per-server channel routing**: assign dedicated roll channels, command channels, and separate snipe / kakera snipe channels per server.
- **strict whitelist mode**: toggle server permissions individually or isolate bot actions to an active target server.

---

### ⚙️ 14-Module Automation Engine
- **auto-badges**: automated `$buy` leveling with optimal order calculation up to Tier 4.
- **auto-tower**: automatic tower floor building and investment.
- **daily & power management**: automated `$dk` with customizable power ceilings, `$daily`, `$p`, and reset queries.
- **kakera orbits**: handles `$oh`, `$oc`, `$oq`, and `$ot` minigames.
- **emergency hybrid panic claiming**: switches to instant claims on high-kakera or top-ranked characters in the final minutes before hourly reset.
- **main account sync & kakera giving**: transfers rolls, wishes, and surplus kakera to a designated main account.
- **character farming & divorce**: automated `$forcedivorce` before rolls or after claims with wish protection.

---

## 🚀 Quick Start

### Option A: 24/7 AWS EC2 / Linux Deployment (Recommended)

1. **Clone the repository on your server:**
   ```bash
   git clone https://github.com/fizzynob/MudaDemote.git /opt/mudademote
   cd /opt/mudademote
   ```

2. **Install Python dependencies:**
   ```bash
   sudo apt update && sudo apt install -y python3 python3-pip
   pip3 install -r requirements.txt
   ```

3. **Run as a systemd service (auto-restart & boot on startup):**
   Create `/etc/systemd/system/mudademote.service`:
   ```ini
   [Unit]
   Description=MudaDemote 24/7 Automation Daemon
   After=network.target

   [Service]
   Type=simple
   User=ubuntu
   WorkingDirectory=/opt/mudademote
   ExecStart=/usr/bin/python3 mudae_server.py --host 0.0.0.0 --port 8080 --autostart
   Restart=always
   RestartSec=5
   Environment=PYTHONUNBUFFERED=1

   [Install]
   WantedBy=multi-user.target
   ```

4. **Enable & Start:**
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable --now mudademote
   ```

5. **Access the Dashboard:**
   Open `http://<your-server-ip>:8080` in any desktop or mobile browser.

---

### Option B: Local Machine (Windows / macOS / Linux)

1. **Clone and install dependencies:**
   ```bash
   git clone https://github.com/fizzynob/MudaDemote.git
   cd MudaDemote
   pip install -r requirements.txt
   ```

2. **Launch the server:**
   ```bash
   python mudae_server.py --host 127.0.0.1 --port 8080
   ```

3. **Open the Web UI:**
   Navigate to [http://127.0.0.1:8080](http://127.0.0.1:8080) in your browser. Configure your Discord user token, target roll channel, and hit **Start**.

---

## 🗂️ Project Architecture

```text
MudaDemote/
├── mudae_server.py           # server entrypoint (aiohttp web server + daemon supervisor)
├── mudae_bot.py              # core mudae automation runtime & discord gateway client
├── mudae_web/
│   ├── app.py                # REST API, WebSocket handler, and static file router
│   └── static/
│       ├── index.html        # pterodactyl-inspired single page web interface
│       ├── app.js            # frontend reactive controller & websocket manager
│       └── style.css         # off-white pterodactyl theme & mobile stylesheet
├── mudae_core/
│   ├── bot_runtime.py        # multi-instance process supervisor & lifecycle manager
│   ├── bot_config.py         # live hot-reloadable configuration attributes
│   ├── config.py             # preset validation, parsing, and serialization
│   └── activity_events.py    # structured activity log classification & telemetry
├── tests/                    # unit test suite (898+ automated tests)
└── version.json              # release integrity manifest & checksums
```

---

## 🛡️ Health & Telemetry API

MudaDemote exposes lightweight health and status endpoints for uptime monitoring:

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/healthz` | `GET` | Returns 200 OK with uptime, memory footprint (MB), and CPU % |
| `/api/status` | `GET` | Complete snapshot of bot state, reset timers, and recent activity |
| `/api/presets` | `GET/POST` | Fetch or live-update preset configuration |
| `/api/ws` | `WebSocket` | Real-time terminal log feed and status broadcasts |

---

## 🧪 Testing

Run the automated test suite locally:
```bash
python -m pytest tests/test_server_api.py tests/test_release_manifest.py tests/test_activity_events.py
```

---

## 📜 License

Released under the [MIT License](LICENSE).
Made with ❤️ for headless 24/7 Mudae automation.
