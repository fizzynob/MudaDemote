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

    finally:
        await client.close()

