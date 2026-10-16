from collections import deque
import asyncio
import datetime
import json
import os
import time
import weakref
from aiohttp import web, WSMsgType

from mudae_core.config import atomic_write_json, load_json, validate_preset
from mudae_core.auto_discovery import ServerDiscovery


class WebServerContext:
    """Shared state between the web dashboard and the bot runtime."""

    def __init__(self, presets_path: str, runtime_manager=None, default_preset: str = "Example"):
        self.presets_path = presets_path
        self.runtime_manager = runtime_manager
        self.active_preset_name = default_preset
        self.active_instance_id = None
        self._bot_client = None  # Reference to the active discord.Client instance if set directly
        self.recent_events = deque(maxlen=200)
        self.ws_clients = weakref.WeakSet()
        self.start_time = time.time()

    @property
    def bot_client(self):
        """Dynamic resolution of active Discord client instance."""
        if getattr(self, "_bot_client", None) is not None:
            return self._bot_client
        if self.runtime_manager:
            if getattr(self, "active_instance_id", None):
                instance = getattr(self.runtime_manager, "_instances", {}).get(self.active_instance_id)
                if instance:
                    client, _ = instance.get_client()
                    if client is not None:
                        return client
            for instance in list(getattr(self.runtime_manager, "_instances", {}).values()):
                client, _ = instance.get_client()
                if client is not None:
                    return client
        return None

    @bot_client.setter
    def bot_client(self, value):
        self._bot_client = value

    def broadcast_event(self, event_type: str, data: dict):
        """Dispatch event to all active WebSocket clients and append to bounded ring buffer."""
        record = {
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "type": event_type,
            "data": data,
        }
        self.recent_events.append(record)

        payload = json.dumps(record)
        for ws in list(self.ws_clients):
            if not ws.closed:
                asyncio.create_task(ws.send_str(payload))

    def get_system_metrics(self) -> dict:
        """Return memory and CPU metrics for EC2 health monitoring."""
        mem_mb = 0.0
        cpu = 0.0
        try:
            import psutil
            process = psutil.Process()
            mem_mb = round(process.memory_info().rss / (1024 * 1024), 2)
            cpu = round(process.cpu_percent(interval=0), 1)
        except Exception:
            try:
                import resource
                mem_mb = round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 2)
            except Exception:
                mem_mb = 0.0

        uptime = int(time.time() - self.start_time)
        return {
            "uptime_seconds": uptime,
            "memory_mb": mem_mb,
            "cpu_percent": cpu,
        }

    def get_status(self) -> dict:
        """Aggregate current status from active client or runtime manager."""
        running = False
        client = self.bot_client

        if client and getattr(client, "is_ready", lambda: False)():
            running = True
            now_utc = datetime.datetime.now(datetime.timezone.utc)
            rolls_left = getattr(client, "rolls_left", 0)
            roll_reset = getattr(client, "roll_reset_at_utc", None)
            claim_avail = getattr(client, "claim_right_available", False)
            claim_reset = getattr(client, "next_claim_reset_at_utc", None)

            roll_reset_s = int((roll_reset - now_utc).total_seconds()) if roll_reset and roll_reset > now_utc else 0
            claim_reset_s = int((claim_reset - now_utc).total_seconds()) if claim_reset and claim_reset > now_utc else 0

            metrics = self.get_system_metrics()
            return {
                "running": True,
                "paused": bool(getattr(client, "is_paused", False)),
                "preset_name": self.active_preset_name,
                "user": str(getattr(client, "user", "Connected")),
                "channel_id": str(getattr(client, "target_channel_id", "")),
                "rolls_left": rolls_left,
                "roll_reset_seconds": roll_reset_s,
                "claim_available": claim_avail,
                "claim_reset_seconds": claim_reset_s,
                "kakera_power": getattr(client, "last_known_power", 100),
                "badges": getattr(getattr(client, "badge_automation", None), "current_levels", {}),
                "tower_floors": getattr(getattr(client, "tower_automation", None), "floors_built", 0),
                "wishlist_count": len(getattr(client, "wishlist", [])),
                "memory_mb": metrics["memory_mb"],
                "uptime_seconds": metrics["uptime_seconds"],
            }

        metrics = self.get_system_metrics()
        return {
            "running": False,
            "paused": False,
            "preset_name": self.active_preset_name,
            "user": "Offline",
            "channel_id": "",
            "rolls_left": 0,
            "roll_reset_seconds": 0,
            "claim_available": False,
            "claim_reset_seconds": 0,
            "kakera_power": 0,
            "badges": {},
            "tower_floors": 0,
            "wishlist_count": 0,
            "memory_mb": metrics["memory_mb"],
            "uptime_seconds": metrics["uptime_seconds"],
        }



def create_app(context: WebServerContext) -> web.Application:
    """Build and configure the aiohttp application."""
    app = web.Application()
    app["ctx"] = context

    # Static assets directory
    static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")

    # REST Routes
    async def handle_index(request):
        index_file = os.path.join(static_dir, "index.html")
        if os.path.exists(index_file):
            return web.FileResponse(index_file)
        return web.Response(text="MudaDemote Web Dashboard", content_type="text/plain")

    async def api_get_status(request):
        return web.json_response(context.get_status())

    async def api_get_presets(request):
        presets = load_json(context.presets_path, {})
        return web.json_response(presets)

    async def api_save_preset(request):
        try:
            body = await request.json()
            preset_name = body.get("name") or context.active_preset_name
            preset_data = body.get("data", {})
            if not preset_name:
                return web.json_response({"success": False, "error": "Preset name is required"}, status=400)

            presets = load_json(context.presets_path, {})
            merged = dict(presets.get(preset_name, {}))
            merged.update(preset_data)

            # Apply defaults for core required keys if omitted
            merged.setdefault("prefix", "/////////////")
            merged.setdefault("mudae_prefix", "$")
            merged.setdefault("roll_command", "wa")
            merged.setdefault("claim_interval", 180)
            merged.setdefault("roll_interval", 60)
            merged.setdefault("max_dk_power", 100)
            merged.setdefault("min_kakera", 100)

            errors = validate_preset(merged, require_runtime=False)
            if errors:
                return web.json_response({"success": False, "errors": errors}, status=400)

            presets[preset_name] = merged
            atomic_write_json(context.presets_path, presets)
            context.broadcast_event("preset_saved", {"name": preset_name})
            return web.json_response({"success": True, "preset_name": preset_name})
        except Exception as exc:
            return web.json_response({"success": False, "error": str(exc)}, status=500)

    async def api_discovery_guilds(request):
        client = context.bot_client
        if not client or not getattr(client, "is_ready", lambda: False)():
            return web.json_response({"success": False, "error": "Bot must be connected to discover servers."}, status=400)
        presets = load_json(context.presets_path, {})
        preset_data = presets.get(context.active_preset_name, {})
        allowed_guild_ids = preset_data.get("allowed_guild_ids")
        target_guild_id = preset_data.get("target_guild_id")
        guilds = ServerDiscovery.list_accessible_guilds(client, allowed_guild_ids)
        return web.json_response({
            "success": True,
            "guilds": guilds,
            "allowed_guild_ids": allowed_guild_ids,
            "target_guild_id": target_guild_id,
            "server_configs": preset_data.get("server_configs", {}),
        })

    async def api_discovery_scan(request):
        client = context.bot_client
        if not client or not getattr(client, "is_ready", lambda: False)():
            return web.json_response({"success": False, "error": "Bot must be connected to scan a server."}, status=400)
        try:
            body = await request.json()
            guild_id = int(body.get("guild_id"))
            scan = ServerDiscovery.inspect_guild_channels(client, guild_id)
            presets = load_json(context.presets_path, {})
            preset_data = presets.get(context.active_preset_name, {})
            server_cfg = (preset_data.get("server_configs") or {}).get(str(guild_id), {})
            return web.json_response({
                "success": True,
                "scan": scan,
                "server_config": server_cfg,
                "is_target": str(preset_data.get("target_guild_id", "")) == str(guild_id),
            })
        except Exception as exc:
            return web.json_response({"success": False, "error": str(exc)}, status=400)

    async def api_discovery_whitelist(request):
        try:
            body = await request.json()
            allowed_guild_ids = body.get("allowed_guild_ids")
            preset_name = body.get("preset_name") or context.active_preset_name
            presets = load_json(context.presets_path, {})
            preset_data = dict(presets.get(preset_name, {}))
            preset_data["allowed_guild_ids"] = allowed_guild_ids
            presets[preset_name] = preset_data
            atomic_write_json(context.presets_path, presets)

            client = context.bot_client
            if client and getattr(client, "is_ready", lambda: False)():
                client.allowed_guild_ids = {str(x).strip() for x in allowed_guild_ids} if allowed_guild_ids is not None else None

            context.broadcast_event("whitelist_updated", {"allowed_guild_ids": allowed_guild_ids})
            return web.json_response({"success": True, "allowed_guild_ids": allowed_guild_ids})
        except Exception as exc:
            return web.json_response({"success": False, "error": str(exc)}, status=500)

    async def api_discovery_server_config(request):
        try:
            body = await request.json()
            guild_id = str(body.get("guild_id") or "").strip()
            if not guild_id:
                return web.json_response({"success": False, "error": "guild_id is required."}, status=400)
            preset_name = body.get("preset_name") or context.active_preset_name
            presets = load_json(context.presets_path, {})
            preset_data = dict(presets.get(preset_name, {}))

            if "allowed" in body:
                raw_allowed = preset_data.get("allowed_guild_ids")
                if raw_allowed is None:
                    # If previously unrestricted, whitelisting this one initializes the whitelist
                    allowed_list = [guild_id] if body["allowed"] else []
                else:
                    allowed_list = [str(x).strip() for x in raw_allowed]
                    if body["allowed"] and guild_id not in allowed_list:
                        allowed_list.append(guild_id)
                    elif not body["allowed"] and guild_id in allowed_list:
                        allowed_list = [g for g in allowed_list if g != guild_id]
                preset_data["allowed_guild_ids"] = allowed_list

            server_configs = dict(preset_data.get("server_configs") or {})
            existing_cfg = dict(server_configs.get(guild_id, {}))
            for key in ("channel_id", "command_channel_id", "snipe_channels", "kakera_snipe_channels", "mudae_prefix"):
                if key in body:
                    existing_cfg[key] = body[key]
            server_configs[guild_id] = existing_cfg
            preset_data["server_configs"] = server_configs

            if body.get("set_as_target"):
                preset_data["target_guild_id"] = guild_id
                if "channel_id" in existing_cfg and existing_cfg["channel_id"]:
                    preset_data["channel_id"] = existing_cfg["channel_id"]
                if "command_channel_id" in existing_cfg:
                    preset_data["command_channel_id"] = existing_cfg["command_channel_id"]
                if "snipe_channels" in existing_cfg:
                    preset_data["snipe_channels"] = existing_cfg["snipe_channels"]
                if "kakera_snipe_channels" in existing_cfg:
                    preset_data["kakera_snipe_channels"] = existing_cfg["kakera_snipe_channels"]
                if "mudae_prefix" in existing_cfg and existing_cfg["mudae_prefix"]:
                    preset_data["mudae_prefix"] = existing_cfg["mudae_prefix"]

            presets[preset_name] = preset_data
            atomic_write_json(context.presets_path, presets)

            # Apply live if client is active
            client = context.bot_client
            if client and getattr(client, "is_ready", lambda: False)():
                if preset_data.get("allowed_guild_ids") is not None:
                    client.allowed_guild_ids = {str(x).strip() for x in preset_data["allowed_guild_ids"]}
                if preset_data.get("target_guild_id"):
                    client.target_guild_id = str(preset_data["target_guild_id"])
                client.server_configs = dict(preset_data.get("server_configs") or {})
                if body.get("set_as_target"):
                    if preset_data.get("channel_id"):
                        try:
                            client.target_channel_id = int(preset_data["channel_id"])
                            get_ch = getattr(client, "get_channel", None)
                            if callable(get_ch):
                                ch = get_ch(client.target_channel_id)
                                if ch:
                                    client._main_channel = ch
                        except (TypeError, ValueError, AttributeError):
                            pass
                    if "command_channel_id" in preset_data:
                        client.command_channel_id_preset = str(preset_data.get("command_channel_id") or "")
                        try:
                            get_ch = getattr(client, "get_channel", None)
                            if callable(get_ch):
                                cmd_ch = get_ch(int(client.command_channel_id_preset))
                                if cmd_ch:
                                    client.command_channel = cmd_ch
                        except Exception:
                            pass
                    if "snipe_channels" in preset_data:
                        client.snipe_channels = {int(x) for x in preset_data["snipe_channels"] if str(x).isdigit()}
                    if "kakera_snipe_channels" in preset_data:
                        client.kakera_snipe_channels = {int(x) for x in preset_data["kakera_snipe_channels"] if str(x).isdigit()}
                    if "mudae_prefix" in preset_data:
                        client.mudae_prefix = str(preset_data["mudae_prefix"])

            context.broadcast_event("server_config_updated", {
                "guild_id": guild_id,
                "preset_name": preset_name,
                "is_target": bool(body.get("set_as_target")),
            })
            return web.json_response({
                "success": True,
                "guild_id": guild_id,
                "allowed_guild_ids": preset_data.get("allowed_guild_ids"),
                "target_guild_id": preset_data.get("target_guild_id"),
                "server_config": existing_cfg,
            })
        except Exception as exc:
            return web.json_response({"success": False, "error": str(exc)}, status=500)

    async def api_action_tu(request):
        client = context.bot_client
        if not client or not getattr(client, "is_ready", lambda: False)():
            return web.json_response({"success": False, "error": "Bot is not connected."}, status=400)
        channel = getattr(client, "_main_channel", None)
        if channel:
            prefix = getattr(client, "mudae_prefix", "$")
            asyncio.create_task(channel.send(f"{prefix}tu"))
            context.broadcast_event("action", {"action": "tu_queried"})
            return web.json_response({"success": True, "message": "$tu sent"})
        return web.json_response({"success": False, "error": "No active channel found."}, status=400)

    async def api_action_wishlist_sync(request):
        client = context.bot_client
        if not client or not getattr(client, "is_ready", lambda: False)():
            return web.json_response({"success": False, "error": "Bot is not connected."}, status=400)
        channel = getattr(client, "command_channel", None) or getattr(client, "_main_channel", None)
        if channel:
            prefix = getattr(client, "mudae_prefix", "$")
            asyncio.create_task(channel.send(f"{prefix}wll"))
            context.broadcast_event("action", {"action": "wishlist_sync_requested"})
            return web.json_response({"success": True, "message": "$wll sent"})
    async def api_action_command(request):
        client = context.bot_client
        if not client or not getattr(client, "is_ready", lambda: False)():
            return web.json_response({"success": False, "error": "Bot is not connected."}, status=400)
        try:
            body = await request.json()
            cmd = str(body.get("command", "") or "").strip()
            if not cmd:
                return web.json_response({"success": False, "error": "Command string cannot be empty."}, status=400)
            channel = getattr(client, "command_channel", None) or getattr(client, "_main_channel", None)
            if channel:
                asyncio.create_task(channel.send(cmd))
                context.broadcast_event("command", {"command": cmd, "status": "dispatched"})
                return web.json_response({"success": True, "message": f"Command '{cmd}' sent"})
            return web.json_response({"success": False, "error": "No active channel found."}, status=400)
        except Exception as exc:
            return web.json_response({"success": False, "error": str(exc)}, status=500)

    async def api_bot_start(request):
        mgr = context.runtime_manager
        if not mgr:
            return web.json_response({"success": False, "error": "Runtime manager not initialized."}, status=400)
        try:
            body = await request.json() if request.can_read_body else {}
        except Exception:
            body = {}
        preset_name = body.get("preset_name") or context.active_preset_name
        presets = load_json(context.presets_path, {})
        preset_data = presets.get(preset_name)
        if not preset_data:
            return web.json_response({"success": False, "error": f"Preset '{preset_name}' not found."}, status=400)
        token = preset_data.get("token")
        if not token:
            return web.json_response({"success": False, "error": "Token is required to start bot."}, status=400)
        try:
            instance_id = mgr.start_instance(preset_name, preset_data, {"token": token}, block=False)
            context.active_instance_id = instance_id
            context.active_preset_name = preset_name
            context.broadcast_event("system", {"message": f"Bot starting for preset '{preset_name}'..."})
            return web.json_response({"success": True, "instance_id": instance_id})
        except Exception as exc:
            return web.json_response({"success": False, "error": str(exc)}, status=500)

    async def api_bot_stop(request):
        mgr = context.runtime_manager
        if mgr and getattr(mgr, "_instances", None):
            instance_id = context.active_instance_id or next(iter(mgr._instances.keys()), None)
            if instance_id and instance_id in mgr._instances:
                stopped = mgr.stop_instance(instance_id)
                context.broadcast_event("system", {"message": "Bot stopped."})
                return web.json_response({"success": True, "stopped": stopped})

        client = context.bot_client
        if client and hasattr(client, "close") and callable(client.close):
            close_res = client.close()
            if asyncio.iscoroutine(close_res):
                asyncio.create_task(close_res)
            context.broadcast_event("system", {"message": "Bot stopping..."})
            return web.json_response({"success": True, "message": "Bot stopped"})
        return web.json_response({"success": False, "error": "No running bot instance."}, status=400)

    async def api_bot_restart(request):
        mgr = context.runtime_manager
        if not mgr or not context.active_instance_id:
            return web.json_response({"success": False, "error": "No active instance to restart."}, status=400)
        restarted = mgr.restart_instance(context.active_instance_id)
        context.broadcast_event("system", {"message": "Bot restarting..."})
        return web.json_response({"success": True, "restarted": restarted})

    async def api_health(request):
        metrics = context.get_system_metrics()
        client = context.bot_client
        bot_running = bool(client and getattr(client, "is_ready", lambda: False)())
        return web.json_response({
            "status": "healthy",
            "bot_running": bot_running,
            "preset": context.active_preset_name,
            **metrics,
        })

    async def websocket_handler(request):
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        context.ws_clients.add(ws)

        # Send initial status & recent events
        await ws.send_json({"type": "init", "status": context.get_status(), "recent_events": list(context.recent_events)[-50:]})

        try:
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    try:
                        data = json.loads(msg.data)
                        if data.get("action") == "ping":
                            await ws.send_json({"type": "pong"})
                    except Exception:
                        pass
                elif msg.type == WSMsgType.ERROR:
                    break
        finally:
            context.ws_clients.discard(ws)

        return ws

    # Register routes
    app.router.add_get("/", handle_index)
    app.router.add_get("/healthz", api_health)
    app.router.add_get("/api/health", api_health)
    app.router.add_get("/api/status", api_get_status)
    app.router.add_get("/api/presets", api_get_presets)
    app.router.add_post("/api/presets", api_save_preset)
    app.router.add_get("/api/discovery/guilds", api_discovery_guilds)
    app.router.add_post("/api/discovery/scan", api_discovery_scan)
    app.router.add_post("/api/discovery/whitelist", api_discovery_whitelist)
    app.router.add_post("/api/discovery/server_config", api_discovery_server_config)
    app.router.add_post("/api/actions/tu", api_action_tu)
    app.router.add_post("/api/actions/wishlist_sync", api_action_wishlist_sync)
    app.router.add_post("/api/actions/command", api_action_command)
    app.router.add_post("/api/bot/start", api_bot_start)
    app.router.add_post("/api/bot/stop", api_bot_stop)
    app.router.add_post("/api/bot/restart", api_bot_restart)
    app.router.add_get("/api/ws", websocket_handler)

    if os.path.exists(static_dir):
        app.router.add_static("/static", static_dir)

    return app

