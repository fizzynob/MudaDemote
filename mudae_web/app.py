from collections import deque
import asyncio
import datetime
import json
import os
import re
import time
import weakref
from aiohttp import web, WSMsgType

from mudae_core.config import MAX_MULTI_ACCOUNTS, atomic_write_json, load_json, resolve_preset_accounts, validate_preset
from mudae_core.auto_discovery import ServerDiscovery
from mudae_core.bot_runtime import InstanceState


def build_account_preset_snapshot(preset_name: str, preset_data: dict, account: dict, stagger_index: int = 0) -> tuple:
    """Return (display_name, instance_id, snapshot_dict) for one configured account slot."""
    import copy

    slot = int(account.get("slot", stagger_index + 1) or (stagger_index + 1))
    label = str(account.get("label") or ("Main" if slot == 1 else f"Alt #{slot}")).strip()
    role = str(account.get("role") or ("main" if slot == 1 else "alt")).strip().lower()
    if role not in ("main", "alt", "sniper", "farmer"):
        role = "alt"

    stagger_step = float(preset_data.get("multi_account_roll_stagger_seconds", 20) or 0)
    snapshot = copy.deepcopy(preset_data)
    snapshot.pop("accounts", None)
    snapshot.pop("tokens", None)
    snapshot["token"] = str(account.get("token") or "").strip().strip("\"'")
    snapshot["_source_preset_name"] = preset_name
    snapshot["_account_slot"] = slot
    snapshot["_account_label"] = label
    snapshot["_account_role"] = role
    snapshot["persistent_stagger_seconds"] = max(0.0, stagger_step * stagger_index)

    if account.get("channel_id"):
        snapshot["channel_id"] = str(account["channel_id"]).strip()
    if account.get("command_channel_id"):
        snapshot["command_channel_id"] = str(account["command_channel_id"]).strip()
    if account.get("rolling") is not None:
        snapshot["rolling"] = bool(account["rolling"])
    if account.get("snipe_mode") is not None:
        snapshot["snipe_mode"] = bool(account["snipe_mode"])

    if role == "main":
        snapshot["auto_give_characters_enabled"] = False
        snapshot["claim_only_if_main_cooldown"] = False
    else:
        if account.get("auto_give_characters") is not None:
            snapshot["auto_give_characters_enabled"] = bool(account["auto_give_characters"])
        if account.get("claim_only_if_main_cooldown") is not None:
            snapshot["claim_only_if_main_cooldown"] = bool(account["claim_only_if_main_cooldown"])

    safe_slug = re.sub(r"[^A-Za-z0-9_-]+", "-", preset_name).strip("-") or "preset"
    instance_id = f"{safe_slug}-slot-{slot}"
    display_name = preset_name if (slot == 1 and label.lower() == "main") else f"{preset_name} [{label}]"
    return display_name, instance_id, snapshot


class WebServerContext:
    """Shared state between the web dashboard and the bot runtime."""

    def __init__(self, presets_path: str, runtime_manager=None, default_preset: str = "Example"):
        self.presets_path = presets_path
        self.runtime_manager = runtime_manager
        self.active_preset_name = default_preset
        self.active_instance_id = None
        self._bot_client = None  # Reference to the active discord.Client instance if set directly
        self._web_loop = None
        self.recent_events = deque(maxlen=250)
        self.claims_history = deque(maxlen=50)
        self.kakera_history = deque(maxlen=50)
        self.session_claims_count = 0
        self.session_kakera_total = 0
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
                    if hasattr(instance, "get_client"):
                        client, _ = instance.get_client()
                    else:
                        client = getattr(instance, "_client", None)
                    if client is not None:
                        return client
            for instance in list(getattr(self.runtime_manager, "_instances", {}).values()):
                if hasattr(instance, "get_client"):
                    client, _ = instance.get_client()
                else:
                    client = getattr(instance, "_client", None)
                if client is not None:
                    return client
        return None

    @bot_client.setter
    def bot_client(self, value):
        self._bot_client = value

    def _send_ws_payload(self, payload: str):
        for ws in list(self.ws_clients):
            if not ws.closed:
                asyncio.create_task(ws.send_str(payload))

    def broadcast_status(self):
        """Push an immediate status update to all connected WebSocket clients."""
        try:
            status_record = {
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "type": "status",
                "data": self.get_status(),
            }
            payload = json.dumps(status_record)
            try:
                running_loop = asyncio.get_running_loop()
            except RuntimeError:
                running_loop = None

            target_loop = self._web_loop or running_loop
            if target_loop and not target_loop.is_closed():
                if running_loop is target_loop:
                    self._send_ws_payload(payload)
                else:
                    target_loop.call_soon_threadsafe(self._send_ws_payload, payload)
        except Exception:
            pass

    def broadcast_event(self, event_type: str, data: dict):
        """Dispatch event to all active WebSocket clients (thread-safe) and append to bounded ring buffer."""
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        record = {
            "timestamp": now_iso,
            "type": event_type,
            "data": data,
        }
        self.recent_events.append(record)

        # Track structured session telemetry
        if event_type == "claim" and isinstance(data, dict):
            self.session_claims_count += 1
            ka_val = data.get("kakera")
            if ka_val is None:
                ka_val = data.get("value")
            if ka_val is None and "raw" in data:
                m = re.search(r"\((\d+)\s*ka\)", str(data.get("raw", "")))
                if m:
                    ka_val = int(m.group(1))
            self.claims_history.appendleft({
                "timestamp": now_iso,
                "character": data.get("character") or data.get("message") or "Character Claimed",
                "value": ka_val,
                "kakera": ka_val,
                "reason": "sniped" if data.get("snipe") else "claimed",
                "source": data.get("source") or "",
                "raw": data.get("raw") or data.get("message") or "",
            })
        elif event_type == "kakera" and isinstance(data, dict):
            amount = int(data.get("amount") or 0)
            self.session_kakera_total += amount
            self.kakera_history.appendleft({
                "timestamp": now_iso,
                "amount": amount,
                "raw": data.get("raw") or data.get("message") or f"+{amount} ka",
            })

        payload = json.dumps(record)
        try:
            running_loop = asyncio.get_running_loop()
        except RuntimeError:
            running_loop = None

        target_loop = self._web_loop or running_loop
        if target_loop and not target_loop.is_closed():
            if running_loop is target_loop:
                self._send_ws_payload(payload)
            else:
                target_loop.call_soon_threadsafe(self._send_ws_payload, payload)

        # Whenever lifecycle state, claim, kakera, or reset changes, also push fresh status
        if event_type in ("state_change", "claim", "kakera", "reset"):
            self.broadcast_status()

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
        client = self.bot_client
        metrics = self.get_system_metrics()

        # Resolve instance state from RuntimeManager if present
        instance = None
        if self.runtime_manager:
            if getattr(self, "active_instance_id", None):
                instance = getattr(self.runtime_manager, "_instances", {}).get(self.active_instance_id)
            if not instance:
                instances = list(getattr(self.runtime_manager, "_instances", {}).values())
                if instances:
                    instance = instances[0]

        inst_state = getattr(instance, "state", None) if instance else None
        state_str = getattr(inst_state, "value", str(inst_state or "")).lower()

        is_connected = bool(client and getattr(client, "is_ready", lambda: False)())
        is_paused = bool(client and getattr(client, "is_paused", False))

        # Authoritative status label
        if is_connected:
            running = True
            status_label = "paused" if is_paused else "running"
        elif state_str in ("starting", "running"):
            running = True
            status_label = "starting"
        elif state_str in ("stopping",):
            running = False
            status_label = "stopping"
        else:
            running = False
            status_label = "offline"

        now_utc = datetime.datetime.now(datetime.timezone.utc)
        rolls_left = getattr(client, "rolls_left", 0) if is_connected else 0
        roll_reset = getattr(client, "roll_reset_at_utc", None) if is_connected else None
        claim_avail = getattr(client, "claim_right_available", False) if is_connected else False
        claim_reset = getattr(client, "next_claim_reset_at_utc", None) if is_connected else None

        roll_reset_s = int((roll_reset - now_utc).total_seconds()) if roll_reset and roll_reset > now_utc else 0
        claim_reset_s = int((claim_reset - now_utc).total_seconds()) if claim_reset and claim_reset > now_utc else 0

        # User display name
        if is_connected:
            user_display = str(getattr(client, "user", "Connected"))
        elif status_label == "starting":
            user_display = "starting..."
        elif status_label == "stopping":
            user_display = "stopping..."
        else:
            user_display = "offline"

        channel_id_val = str(getattr(client, "target_channel_id", "") or "")
        main_ch = getattr(client, "_main_channel", None) if is_connected else None
        channel_name_val = getattr(main_ch, "name", "") if main_ch else ""
        guild_obj = getattr(main_ch, "guild", None) if main_ch else None
        guild_name_val = getattr(guild_obj, "name", "") if guild_obj else ""

        # Aggregate all running multi-account instances
        accounts_status = []
        running_count = 0
        if self.runtime_manager:
            for iid, inst in list(getattr(self.runtime_manager, "_instances", {}).items()):
                if hasattr(inst, "get_client"):
                    c, _ = inst.get_client()
                else:
                    c = getattr(inst, "_client", None)
                c_ready = bool(c and getattr(c, "is_ready", lambda: False)())
                c_paused = bool(c and getattr(c, "is_paused", False))
                i_state = str(getattr(getattr(inst, "state", None), "value", getattr(inst, "state", "")) or "").lower()
                if c_ready:
                    i_running = True
                    i_label = "paused" if c_paused else "running"
                elif i_state in ("starting", "running"):
                    i_running = True
                    i_label = "starting"
                elif i_state in ("stopping",):
                    i_running = False
                    i_label = "stopping"
                else:
                    i_running = False
                    i_label = "offline"
                if i_running:
                    running_count += 1

                c_roll_reset = getattr(c, "roll_reset_at_utc", None) if c_ready else None
                c_claim_reset = getattr(c, "next_claim_reset_at_utc", None) if c_ready else None
                c_roll_s = int((c_roll_reset - now_utc).total_seconds()) if c_roll_reset and c_roll_reset > now_utc else 0
                c_claim_s = int((c_claim_reset - now_utc).total_seconds()) if c_claim_reset and c_claim_reset > now_utc else 0
                accounts_status.append({
                    "instance_id": iid,
                    "slot": getattr(c, "account_slot", None) or getattr(inst, "preset_data", {}).get("_account_slot", len(accounts_status) + 1),
                    "label": getattr(c, "account_label", None) or getattr(inst, "preset_name", iid),
                    "role": getattr(c, "account_role", None) or getattr(inst, "preset_data", {}).get("_account_role", "main"),
                    "running": i_running,
                    "status_label": i_label,
                    "paused": c_paused,
                    "user": str(getattr(c, "user", i_label)) if c_ready else i_label,
                    "user_id": str(getattr(getattr(c, "user", None), "id", "") or "") if c_ready else "",
                    "rolls_left": getattr(c, "rolls_left", 0) if c_ready else 0,
                    "roll_reset_seconds": c_roll_s,
                    "claim_available": bool(getattr(c, "claim_right_available", False)) if c_ready else False,
                    "claim_reset_seconds": c_claim_s,
                    "rt_available": bool(getattr(c, "rt_available", False)) if c_ready else False,
                    "kakera_power": getattr(c, "last_known_power", 100) if c_ready else 0,
                    "channel_id": str(getattr(c, "target_channel_id", "") or ""),
                    "claims_count": len(getattr(c, "recent_claims", []) or []) if c else 0,
                    "auto_give_count": int(getattr(c, "auto_give_count", 0) or 0) if c else 0,
                })

        if running_count == 0 and running:
            running_count = 1

        # Aggregate recent claims across all connected accounts + server history
        combined_claims = list(self.claims_history)
        if self.runtime_manager:
            seen_claim_keys = set()
            merged_claims = []
            for inst in list(getattr(self.runtime_manager, "_instances", {}).values()):
                c = inst.get_client()[0] if hasattr(inst, "get_client") else getattr(inst, "_client", None)
                for item in (getattr(c, "recent_claims", None) or []):
                    key = (item.get("timestamp"), item.get("character"))
                    if key not in seen_claim_keys:
                        seen_claim_keys.add(key)
                        merged_claims.append(item)
            for item in combined_claims:
                key = (item.get("timestamp"), item.get("character"))
                if key not in seen_claim_keys:
                    seen_claim_keys.add(key)
                    merged_claims.append(item)
            if merged_claims:
                merged_claims.sort(key=lambda x: str(x.get("timestamp") or ""), reverse=True)
                combined_claims = merged_claims
        elif getattr(client, "recent_claims", None):
            combined_claims = list(client.recent_claims)

        # Live Main Account cooldown tracker status
        main_account_status = {
            "main_account_id": "",
            "known": False,
            "claim_available": None,
            "on_cooldown": False,
            "cooldown_reset_seconds": 0,
            "source": "unknown",
        }
        try:
            presets = load_json(self.presets_path, {})
            active_cfg = presets.get(self.active_preset_name, {})
            cfg_main_id = str(active_cfg.get("main_account_id") or "").strip()
            from mudae_bot import get_main_cooldown_status
            raw_main = get_main_cooldown_status(cfg_main_id)
            main_account_status = {
                "main_account_id": raw_main.get("main_account_id", ""),
                "known": bool(raw_main.get("known", False)),
                "claim_available": raw_main.get("claim_available"),
                "on_cooldown": bool(raw_main.get("on_cooldown", False)),
                "cooldown_reset_seconds": int(raw_main.get("cooldown_reset_seconds", 0) or 0),
                "source": raw_main.get("source", "unknown"),
            }
        except Exception:
            pass

        return {
            "running": running,
            "status_label": status_label,
            "paused": is_paused,
            "running_count": running_count,
            "accounts_status": accounts_status,
            "main_account_status": main_account_status,
            "preset_name": self.active_preset_name,
            "user": user_display,
            "channel_id": channel_id_val,
            "channel_name": channel_name_val,
            "guild_name": guild_name_val,
            "rolls_left": rolls_left,
            "roll_reset_seconds": roll_reset_s,
            "claim_available": claim_avail,
            "claim_reset_seconds": claim_reset_s,
            "rt_available": bool(getattr(client, "rt_available", False)) if is_connected else False,
            "kakera_power": getattr(client, "last_known_power", 100) if is_connected else 0,
            "kakera_consumption": getattr(client, "kakera_consumption", 36) if is_connected else 0,
            "tu_query_count": getattr(client, "tu_query_count", 0) if is_connected else 0,
            "badges": getattr(getattr(client, "badge_automation", None), "current_levels", {}) if is_connected else {},
            "tower_floors": getattr(getattr(client, "tower_automation", None), "floors_built", 0) if is_connected else 0,
            "wishlist_count": len(getattr(client, "wishlist", [])) if is_connected else 0,
            "session_claims_count": self.session_claims_count,
            "session_kakera_total": self.session_kakera_total,
            "recent_claims": combined_claims[:15],
            "recent_kakera": list(self.kakera_history)[:15],
            "memory_mb": metrics["memory_mb"],
            "cpu_percent": metrics["cpu_percent"],
            "uptime_seconds": metrics["uptime_seconds"],
        }


def create_app(context: WebServerContext) -> web.Application:
    """Build and configure the aiohttp application."""
    app = web.Application()
    app["ctx"] = context

    async def on_startup(app_instance):
        context._web_loop = asyncio.get_running_loop()

    app.on_startup.append(on_startup)

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
            preset_name = body.get("name") or body.get("preset_name") or context.active_preset_name
            preset_data = body.get("data") if "data" in body else body.get("preset_data", {})
            if not preset_name:
                return web.json_response({"success": False, "error": "Preset name is required"}, status=400)

            presets = load_json(context.presets_path, {})
            merged = dict(presets.get(preset_name, {}))
            merged.update(preset_data)

            # Synchronize accounts <-> tokens <-> primary token
            if "accounts" in preset_data and isinstance(merged.get("accounts"), list):
                resolved_accts = resolve_preset_accounts({"accounts": merged["accounts"]})
                merged["accounts"] = resolved_accts
                enabled_tokens = [a["token"] for a in resolved_accts if a.get("enabled", True) and a.get("token")]
                merged["tokens"] = enabled_tokens[:MAX_MULTI_ACCOUNTS]
                if enabled_tokens:
                    merged["token"] = enabled_tokens[0]
                elif resolved_accts and resolved_accts[0].get("token"):
                    merged["token"] = resolved_accts[0]["token"]
            elif "token" in preset_data and isinstance(merged.get("accounts"), list) and merged["accounts"]:
                tok_val = str(merged.get("token") or "").strip().strip("\"'")
                merged["accounts"][0]["token"] = tok_val
                resolved_accts = resolve_preset_accounts({"accounts": merged["accounts"]})
                merged["accounts"] = resolved_accts
                merged["tokens"] = [a["token"] for a in resolved_accts if a.get("enabled", True) and a.get("token")][:MAX_MULTI_ACCOUNTS]

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
            context.active_preset_name = preset_name

            # Live apply to all running instances of this preset
            restart_required = []
            mgr = context.runtime_manager
            if mgr and getattr(mgr, "_instances", None):
                resolved_accts = resolve_preset_accounts(merged)
                acct_by_slot = {a["slot"]: a for a in resolved_accts}
                for iid, inst in list(mgr._instances.items()):
                    if not hasattr(inst, "apply_preset") or not callable(inst.apply_preset):
                        continue
                    inst_src = getattr(inst, "preset_data", {}).get("_source_preset_name") or getattr(inst, "preset_name", "")
                    if inst_src != preset_name and iid != context.active_instance_id:
                        continue
                    slot_num = int(getattr(inst, "preset_data", {}).get("_account_slot", 1) or 1)
                    acct = acct_by_slot.get(slot_num)
                    payload_for_inst = (
                        build_account_preset_snapshot(preset_name, merged, acct, stagger_index=max(0, slot_num - 1))[2]
                        if acct
                        else merged
                    )
                    try:
                        live_outcome = inst.apply_preset(payload_for_inst)
                        for req in (live_outcome or {}).get("restart_required", []):
                            if req not in restart_required:
                                restart_required.append(req)
                    except Exception:
                        pass

            context.broadcast_event("preset_saved", {
                "name": preset_name,
                "restart_required": restart_required,
            })
            return web.json_response({
                "success": True,
                "preset_name": preset_name,
                "restart_required": restart_required,
            })
        except Exception as exc:
            return web.json_response({"success": False, "error": str(exc)}, status=500)

    async def api_delete_preset(request):
        try:
            body = await request.json()
            preset_name = str(body.get("name") or body.get("preset_name") or "").strip()
            if not preset_name:
                return web.json_response({"success": False, "error": "Preset name is required."}, status=400)
            presets = load_json(context.presets_path, {})
            if preset_name not in presets:
                return web.json_response({"success": False, "error": f"Preset '{preset_name}' not found."}, status=404)
            if len(presets) <= 1:
                return web.json_response({"success": False, "error": "Cannot delete the only remaining preset."}, status=400)
            del presets[preset_name]
            atomic_write_json(context.presets_path, presets)
            if context.active_preset_name == preset_name:
                context.active_preset_name = next(iter(presets.keys()))
            context.broadcast_event("system", {"message": f"Preset '{preset_name}' deleted."})
            return web.json_response({"success": True, "active_preset": context.active_preset_name})
        except Exception as exc:
            return web.json_response({"success": False, "error": str(exc)}, status=500)

    async def api_select_preset(request):
        try:
            body = await request.json()
            preset_name = str(body.get("name") or body.get("preset_name") or "").strip()
            presets = load_json(context.presets_path, {})
            if preset_name not in presets:
                return web.json_response({"success": False, "error": f"Preset '{preset_name}' not found."}, status=404)
            context.active_preset_name = preset_name
            context.broadcast_status()
            return web.json_response({"success": True, "preset_name": preset_name, "active_preset": preset_name})
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

    def _schedule_on_client_loop(client, coro_or_fn):
        """Safely dispatch a coroutine or callback onto the Discord client's event loop."""
        client_loop = getattr(client, "loop", None)
        try:
            running_loop = asyncio.get_running_loop()
        except RuntimeError:
            running_loop = None

        if asyncio.iscoroutine(coro_or_fn):
            if client_loop and not client_loop.is_closed() and client_loop is not running_loop:
                asyncio.run_coroutine_threadsafe(coro_or_fn, client_loop)
            else:
                asyncio.create_task(coro_or_fn)
        elif callable(coro_or_fn):
            if client_loop and not client_loop.is_closed() and client_loop is not running_loop:
                client_loop.call_soon_threadsafe(coro_or_fn)
            else:
                coro_or_fn()

    def _resolve_target_clients(target_id=None):
        """Return list of ready Discord clients matching target_id ('all', instance_id, or default primary)."""
        mgr = context.runtime_manager
        clients = []
        if mgr and getattr(mgr, "_instances", None):
            instances = getattr(mgr, "_instances", {})
            if target_id == "all":
                for inst in list(instances.values()):
                    c = inst.get_client()[0] if hasattr(inst, "get_client") else getattr(inst, "_client", None)
                    if c and getattr(c, "is_ready", lambda: False)():
                        clients.append(c)
                return clients
            if target_id and target_id in instances:
                inst = instances[target_id]
                c = inst.get_client()[0] if hasattr(inst, "get_client") else getattr(inst, "_client", None)
                if c and getattr(c, "is_ready", lambda: False)():
                    return [c]
                return []
        primary = context.bot_client
        if primary and getattr(primary, "is_ready", lambda: False)():
            clients.append(primary)
        return clients

    async def api_action_tu(request):
        try:
            body = await request.json() if request.can_read_body else {}
        except Exception:
            body = {}
        targets = _resolve_target_clients(body.get("instance_id"))
        if not targets:
            return web.json_response({"success": False, "error": "Bot is not connected."}, status=400)
        sent_count = 0
        last_prefix = "$"
        for c in targets:
            channel = getattr(c, "command_channel", None) or getattr(c, "_main_channel", None)
            if channel:
                prefix = getattr(c, "mudae_prefix", "$")
                last_prefix = prefix
                _schedule_on_client_loop(c, channel.send(f"{prefix}tu"))
                sent_count += 1
        if sent_count:
            context.broadcast_event("action", {"action": "tu_queried", "count": sent_count})
            return web.json_response({"success": True, "message": f"{last_prefix}tu sent ({sent_count} account{'s' if sent_count > 1 else ''})"})
        return web.json_response({"success": False, "error": "No active channel found."}, status=400)

    async def api_action_wishlist_sync(request):
        try:
            body = await request.json() if request.can_read_body else {}
        except Exception:
            body = {}
        targets = _resolve_target_clients(body.get("instance_id"))
        if not targets:
            return web.json_response({"success": False, "error": "Bot is not connected."}, status=400)
        sent_count = 0
        last_prefix = "$"
        for c in targets:
            channel = getattr(c, "command_channel", None) or getattr(c, "_main_channel", None)
            if channel:
                prefix = getattr(c, "mudae_prefix", "$")
                last_prefix = prefix
                _schedule_on_client_loop(c, channel.send(f"{prefix}wll"))
                sent_count += 1
        if sent_count:
            context.broadcast_event("action", {"action": "wishlist_sync_requested", "count": sent_count})
            return web.json_response({"success": True, "message": f"{last_prefix}wll sent"})
        return web.json_response({"success": False, "error": "No active channel found."}, status=400)

    async def api_action_wake(request):
        try:
            body = await request.json() if request.can_read_body else {}
        except Exception:
            body = {}
        targets = _resolve_target_clients(body.get("instance_id") or "all")
        if not targets:
            return web.json_response({"success": False, "error": "Bot is not connected."}, status=400)

        for c in targets:
            def _wake(target_c=c):
                for ev_name in ("_immediate_check_event", "_runtime_state_event"):
                    ev = getattr(target_c, ev_name, None)
                    if ev is not None:
                        ev.set()

            _schedule_on_client_loop(c, _wake)
        context.broadcast_event("system", {"message": f"Status & roll loop wake signal dispatched ({len(targets)} account{'s' if len(targets) > 1 else ''})."})
        return web.json_response({"success": True, "message": "Loop wake triggered", "count": len(targets)})

    async def api_action_command(request):
        try:
            body = await request.json()
            cmd = str(body.get("command", "") or "").strip()
            if not cmd:
                return web.json_response({"success": False, "error": "Command string cannot be empty."}, status=400)
            targets = _resolve_target_clients(body.get("instance_id"))
            if not targets:
                return web.json_response({"success": False, "error": "Bot is not connected."}, status=400)
            sent_count = 0
            for c in targets:
                channel = getattr(c, "command_channel", None) or getattr(c, "_main_channel", None)
                if channel:
                    _schedule_on_client_loop(c, channel.send(cmd))
                    sent_count += 1
            if sent_count:
                context.broadcast_event("command", {"command": cmd, "status": "dispatched", "count": sent_count})
                return web.json_response({"success": True, "message": f"Command '{cmd}' sent ({sent_count} account{'s' if sent_count > 1 else ''})"})
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

        target_slot = body.get("slot")
        accounts = [a for a in resolve_preset_accounts(preset_data) if a.get("enabled", True) and a.get("token")]
        if target_slot is not None:
            accounts = [a for a in accounts if int(a.get("slot", 0)) == int(target_slot)]
            if not accounts:
                return web.json_response({"success": False, "error": f"Account slot #{target_slot} has no enabled token."}, status=400)
        if not accounts:
            return web.json_response({"success": False, "error": "Discord token is required in Configs or Multi-Account tab before starting."}, status=400)

        # Clean up stopped instances or instances belonging to a different preset
        instances = getattr(mgr, "_instances", {})
        for iid, inst in list(instances.items()):
            st = getattr(inst, "state", None)
            src_preset = getattr(inst, "preset_data", {}).get("_source_preset_name") or getattr(inst, "preset_name", None)
            if st in (InstanceState.STARTING, InstanceState.RUNNING):
                if src_preset != preset_name and target_slot is None:
                    await asyncio.to_thread(mgr.stop_instance, iid)
                    if hasattr(mgr, "remove_instance"):
                        mgr.remove_instance(iid)
            else:
                if hasattr(mgr, "remove_instance"):
                    mgr.remove_instance(iid)

        started_ids = []
        resumed_count = 0
        try:
            for idx, acct in enumerate(accounts[:MAX_MULTI_ACCOUNTS]):
                display_name, iid, snap = build_account_preset_snapshot(preset_name, preset_data, acct, stagger_index=idx)
                existing_inst = getattr(mgr, "_instances", {}).get(iid)
                if existing_inst and getattr(existing_inst, "state", None) in (InstanceState.STARTING, InstanceState.RUNNING):
                    c = existing_inst.get_client()[0] if hasattr(existing_inst, "get_client") else getattr(existing_inst, "_client", None)
                    if c and getattr(c, "is_paused", False):
                        c.is_paused = False
                        _schedule_on_client_loop(c, lambda target_c=c: getattr(target_c, "_runtime_state_event", None) and target_c._runtime_state_event.set())
                        resumed_count += 1
                    started_ids.append(iid)
                    continue

                created_id = mgr.start_instance(
                    display_name, snap, {"token": acct["token"]}, instance_id=iid, block=False
                )
                started_ids.append(created_id)
                if not context.active_instance_id or int(acct.get("slot", 1)) == 1:
                    context.active_instance_id = created_id

            context.active_preset_name = preset_name
            msg = (
                f"Resumed {resumed_count} account(s)."
                if resumed_count and len(started_ids) == resumed_count
                else f"Started {len(started_ids)} account(s) for preset '{preset_name}'."
            )
            context.broadcast_event("system", {"message": msg})
            context.broadcast_status()
            return web.json_response({
                "success": True,
                "instance_id": started_ids[0] if started_ids else None,
                "instance_ids": started_ids,
                "count": len(started_ids),
                "message": msg,
            })
        except Exception as exc:
            return web.json_response({"success": False, "error": str(exc)}, status=500)

    async def api_bot_stop(request):
        try:
            body = await request.json() if request.can_read_body else {}
        except Exception:
            body = {}
        target_iid = body.get("instance_id")
        mgr = context.runtime_manager
        if mgr and getattr(mgr, "_instances", None):
            instances = getattr(mgr, "_instances", {})
            target_ids = [target_iid] if (target_iid and target_iid in instances) else list(instances.keys())
            if target_ids:
                stopped_any = False
                for iid in target_ids:
                    try:
                        if await asyncio.to_thread(mgr.stop_instance, iid):
                            stopped_any = True
                        if hasattr(mgr, "remove_instance") and callable(mgr.remove_instance):
                            mgr.remove_instance(iid)
                    except Exception:
                        pass
                if context.active_instance_id not in getattr(mgr, "_instances", {}):
                    context.active_instance_id = next(iter(getattr(mgr, "_instances", {}).keys()), None)
                label = f"Account '{target_iid}' stopped." if target_iid else "All bot accounts stopped."
                context.broadcast_event("system", {"message": label})
                context.broadcast_status()
                return web.json_response({"success": True, "stopped": stopped_any, "count": len(target_ids)})

        client = context.bot_client
        if client and hasattr(client, "close") and callable(client.close):
            close_res = client.close()
            if asyncio.iscoroutine(close_res):
                asyncio.create_task(close_res)
            context.broadcast_event("system", {"message": "Bot stopping..."})
            context.broadcast_status()
            return web.json_response({"success": True, "message": "Bot stopped"})
        return web.json_response({"success": False, "error": "No running bot instance."}, status=400)

    async def api_bot_restart(request):
        mgr = context.runtime_manager
        if not mgr:
            return web.json_response({"success": False, "error": "Runtime manager not initialized."}, status=400)
        try:
            body = await request.json() if request.can_read_body else {}
        except Exception:
            body = {}
        preset_name = body.get("preset_name") or context.active_preset_name
        presets = load_json(context.presets_path, {})
        preset_data = presets.get(preset_name, {})
        target_slot = body.get("slot")
        accounts = [a for a in resolve_preset_accounts(preset_data) if a.get("enabled", True) and a.get("token")]
        if target_slot is not None:
            accounts = [a for a in accounts if int(a.get("slot", 0)) == int(target_slot)]
        if not accounts:
            return web.json_response({"success": False, "error": "Discord token is required in Configs or Multi-Account tab to restart."}, status=400)

        target_iids_to_stop = (
            [build_account_preset_snapshot(preset_name, preset_data, accounts[0])[1]]
            if target_slot is not None
            else list(getattr(mgr, "_instances", {}).keys())
        )
        for iid in target_iids_to_stop:
            if iid not in getattr(mgr, "_instances", {}):
                continue
            try:
                await asyncio.to_thread(mgr.stop_instance, iid)
                if hasattr(mgr, "remove_instance") and callable(mgr.remove_instance):
                    mgr.remove_instance(iid)
            except Exception:
                pass

        try:
            started_ids = []
            for idx, acct in enumerate(accounts[:MAX_MULTI_ACCOUNTS]):
                display_name, iid, snap = build_account_preset_snapshot(preset_name, preset_data, acct, stagger_index=idx)
                created_id = mgr.start_instance(
                    display_name, snap, {"token": acct["token"]}, instance_id=iid, block=False
                )
                started_ids.append(created_id)
                if not context.active_instance_id or int(acct.get("slot", 1)) == 1:
                    context.active_instance_id = created_id
            context.active_preset_name = preset_name
            context.broadcast_event("system", {"message": f"Restarted {len(started_ids)} account(s) with latest '{preset_name}' configuration."})
            context.broadcast_status()
            return web.json_response({
                "success": True,
                "restarted": True,
                "instance_id": started_ids[0] if started_ids else None,
                "instance_ids": started_ids,
                "count": len(started_ids),
            })
        except Exception as exc:
            return web.json_response({"success": False, "error": str(exc)}, status=500)

    async def api_bot_pause(request):
        try:
            body = await request.json() if request.can_read_body else {}
        except Exception:
            body = {}
        target_iid = body.get("instance_id")
        targets = _resolve_target_clients(target_iid or "all")
        if not targets:
            return web.json_response({"success": False, "error": "Bot is not connected."}, status=400)

        if target_iid:
            new_paused = not bool(getattr(targets[0], "is_paused", False))
        else:
            # If any account is unpaused, pause all; if all are paused, resume all
            any_unpaused = any(not bool(getattr(c, "is_paused", False)) for c in targets)
            new_paused = any_unpaused

        for c in targets:
            c.is_paused = new_paused

            def _notify_pause(target_c=c):
                for ev_name in ("_runtime_state_event", "_immediate_check_event"):
                    ev = getattr(target_c, ev_name, None)
                    if ev is not None:
                        ev.set()

            _schedule_on_client_loop(c, _notify_pause)

        state_word = "paused" if new_paused else "resumed"
        scope_word = f"Account {target_iid}" if target_iid else f"Bot ({len(targets)} account{'s' if len(targets) > 1 else ''})"
        context.broadcast_event("system", {"message": f"{scope_word} {state_word} by user."})
        context.broadcast_status()
        return web.json_response({"success": True, "paused": new_paused, "status_label": "paused" if new_paused else "running"})

    async def api_health(request):
        status = context.get_status()
        metrics = context.get_system_metrics()
        return web.json_response({
            "status": "healthy",
            "bot_running": status["running"],
            "status_label": status["status_label"],
            "preset": context.active_preset_name,
            **metrics,
        })

    async def websocket_handler(request):
        context._web_loop = asyncio.get_running_loop()
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        context.ws_clients.add(ws)

        # Send initial status & recent events
        await ws.send_json({"type": "init", "status": context.get_status(), "recent_events": list(context.recent_events)[-80:]})

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
    app.router.add_post("/api/presets/delete", api_delete_preset)
    app.router.add_post("/api/presets/select", api_select_preset)
    app.router.add_get("/api/discovery/guilds", api_discovery_guilds)
    app.router.add_post("/api/discovery/scan", api_discovery_scan)
    app.router.add_post("/api/discovery/whitelist", api_discovery_whitelist)
    app.router.add_post("/api/discovery/server_config", api_discovery_server_config)
    app.router.add_post("/api/actions/tu", api_action_tu)
    app.router.add_post("/api/actions/wishlist_sync", api_action_wishlist_sync)
    app.router.add_post("/api/actions/wake", api_action_wake)
    app.router.add_post("/api/actions/command", api_action_command)
    app.router.add_post("/api/bot/start", api_bot_start)
    app.router.add_post("/api/bot/stop", api_bot_stop)
    app.router.add_post("/api/bot/restart", api_bot_restart)
    app.router.add_post("/api/bot/pause", api_bot_pause)
    app.router.add_get("/api/ws", websocket_handler)
    app.router.add_get("/ws", websocket_handler)

    if os.path.exists(static_dir):
        app.router.add_static("/static", static_dir)

    return app
