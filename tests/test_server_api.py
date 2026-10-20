import json
import pytest
from types import SimpleNamespace
from aiohttp import web
from mudae_web.app import WebServerContext, create_app


@pytest.fixture
def test_context(tmp_path):
    presets_file = tmp_path / "presets.json"
    presets_file.write_text(json.dumps({"Example": {"token": "dummy_token", "channel_id": "12345"}}), encoding="utf-8")
    ctx = WebServerContext(presets_path=str(presets_file), default_preset="Example")
    return ctx


@pytest.mark.anyio
async def test_server_status_and_presets_api(test_context):
    app = create_app(test_context)
    
    from aiohttp.test_utils import TestClient, TestServer
    
    server = TestServer(app)
    client = TestClient(server)
    await client.start_server()
    
    try:
        # GET /healthz & /api/health (EC2 Health Check)
        resp_healthz = await client.get("/healthz")
        assert resp_healthz.status == 200
        healthz_data = await resp_healthz.json()
        assert healthz_data["status"] == "healthy"
        assert "uptime_seconds" in healthz_data
        assert "memory_mb" in healthz_data

        # GET /api/status
        resp = await client.get("/api/status")
        assert resp.status == 200
        data = await resp.json()
        assert "running" in data
        assert data["preset_name"] == "Example"

        # GET /api/presets
        resp_presets = await client.get("/api/presets")
        assert resp_presets.status == 200
        presets_data = await resp_presets.json()
        assert "Example" in presets_data

        # POST /api/presets (save update)
        payload = {
            "name": "Example",
            "data": {
                "token": "new_token",
                "channel_id": "99999",
                "auto_badges_enabled": True,
            }
        }
        resp_save = await client.post("/api/presets", json=payload)
        assert resp_save.status == 200
        save_result = await resp_save.json()
        assert save_result["success"] is True

        # Verify persisted
        resp_updated = await client.get("/api/presets")
        updated_data = await resp_updated.json()
        assert updated_data["Example"]["auto_badges_enabled"] is True

        # Test POST /api/actions/command without connected bot
        resp_cmd_fail = await client.post("/api/actions/command", json={"command": "$tu"})
        assert resp_cmd_fail.status == 400

        # Attach mock connected bot
        mock_channel_sends = []

        class MockChannel:
            async def send(self, content):
                mock_channel_sends.append(content)

        test_context.bot_client = SimpleNamespace(
            is_ready=lambda: True,
            command_channel=MockChannel(),
            _main_channel=MockChannel(),
            mudae_prefix="$",
            close=lambda: None,
        )

        # Test POST /api/actions/command with mock bot
        resp_cmd_ok = await client.post("/api/actions/command", json={"command": "$tu"})
        assert resp_cmd_ok.status == 200
        cmd_res = await resp_cmd_ok.json()
        assert cmd_res["success"] is True

        # Test POST /api/discovery/whitelist
        resp_wl = await client.post("/api/discovery/whitelist", json={"allowed_guild_ids": ["123", "456"]})
        assert resp_wl.status == 200
        wl_data = await resp_wl.json()
        assert wl_data["success"] is True
        assert wl_data["allowed_guild_ids"] == ["123", "456"]

        # Test POST /api/discovery/server_config
        resp_scfg = await client.post("/api/discovery/server_config", json={
            "guild_id": "123",
            "channel_id": "789",
            "command_channel_id": "790",
            "snipe_channels": ["789", "791"],
            "kakera_snipe_channels": ["789"],
            "mudae_prefix": ">",
            "allowed": True,
            "set_as_target": True,
        })
        assert resp_scfg.status == 200
        scfg_data = await resp_scfg.json()
        assert scfg_data["success"] is True
        assert scfg_data["target_guild_id"] == "123"
        assert scfg_data["server_config"]["channel_id"] == "789"
        assert scfg_data["server_config"]["mudae_prefix"] == ">"

        # Test dynamic bot_client resolution from runtime_manager
        test_context.bot_client = None
        mock_instance = SimpleNamespace(
            get_client=lambda: (SimpleNamespace(is_ready=lambda: True, user="ResolvedUser"), None)
        )
        test_context.runtime_manager = SimpleNamespace(
            _instances={"inst-1": mock_instance},
            stop_instance=lambda iid: True,
        )
        assert test_context.bot_client is not None
        assert test_context.bot_client.user == "ResolvedUser"

        # Test POST /api/bot/stop
        resp_stop = await client.post("/api/bot/stop")
        assert resp_stop.status == 200
        stop_res = await resp_stop.json()
        assert stop_res["success"] is True

        # Test preset creation, selection, and deletion
        resp_new_preset = await client.post("/api/presets", json={
            "name": "SecondPreset",
            "data": {"token": "tok2", "channel_id": "55555"},
        })
        assert resp_new_preset.status == 200

        resp_sel = await client.post("/api/presets/select", json={"name": "SecondPreset"})
        assert resp_sel.status == 200
        sel_data = await resp_sel.json()
        assert sel_data["active_preset"] == "SecondPreset"

        resp_del = await client.post("/api/presets/delete", json={"name": "SecondPreset"})
        assert resp_del.status == 200
        del_data = await resp_del.json()
        assert del_data["success"] is True

        # Test POST /api/bot/pause and /api/actions/wake with active bot client
        woke_flag = {"called": False}
        mock_bot = SimpleNamespace(
            is_ready=lambda: True,
            is_paused=False,
            _runtime_state_event=SimpleNamespace(set=lambda: None),
            _immediate_check_event=SimpleNamespace(set=lambda: woke_flag.__setitem__("called", True)),
        )
        test_context.bot_client = mock_bot

        resp_pause = await client.post("/api/bot/pause")
        assert resp_pause.status == 200
        pause_data = await resp_pause.json()
        assert pause_data["success"] is True
        assert pause_data["paused"] is True

        resp_wake = await client.post("/api/actions/wake")
        assert resp_wake.status == 200
        wake_data = await resp_wake.json()
        assert wake_data["success"] is True

        # Test saving Humanization settings (post-claim chat pool, active-user check, sleep windows, micro-pauses)
        resp_human = await client.post("/api/presets", json={
            "name": "Example",
            "data": {
                "token": "new_token",
                "channel_id": "99999",
                "enable_claim_chat_messages": True,
                "claim_chat_only_when_others_active": True,
                "claim_chat_other_user_window_minutes": 15,
                "claim_chat_messages": ["nice {char}!", "gg", "lets gooo"],
                "claim_chat_probability": 85,
                "claim_chat_min_delay": 1.5,
                "claim_chat_max_delay": 3.5,
                "claim_chat_min_kakera": 200,
                "claim_chat_on_own_rolls": True,
                "claim_chat_on_snipes": True,
                "human_typing_indicator": True,
                "roll_speed_jitter_pct": 25,
                "human_micro_pause_enabled": True,
                "human_micro_pause_chance": 10,
                "human_micro_pause_min": 1.2,
                "human_micro_pause_max": 2.8,
                "inactive_hours": [["02:00", "07:30"]],
            },
        })
        assert resp_human.status == 200
        human_res = await resp_human.json()
        assert human_res["success"] is True

        # Test claim event telemetry with kakera value retention
        test_context.broadcast_event("claim", {
            "character": "Rem",
            "kakera": 450,
            "snipe": False,
            "source": "button click",
        })
        resp_status_claim = await client.get("/api/status")
        assert resp_status_claim.status == 200
        claim_status_data = await resp_status_claim.json()
        assert claim_status_data["session_claims_count"] == 1
        assert len(claim_status_data["recent_claims"]) == 1
        assert claim_status_data["recent_claims"][0]["character"] == "Rem"
        assert claim_status_data["recent_claims"][0]["value"] == 450
        assert claim_status_data["recent_claims"][0]["reason"] == "claimed"

    finally:
        await client.close()


