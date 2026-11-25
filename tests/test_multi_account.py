import datetime
import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from mudae_core.bot_config import LIVE_CONFIG_ATTRIBUTES, apply_live_config, configure_client
from mudae_core.bot_runtime import BotInstance, RuntimeManager
from mudae_core.config import MAX_MULTI_ACCOUNTS, resolve_preset_accounts, validate_preset
from mudae_core.coordinator import MainAccountCooldownTracker
from mudae_core.gifting import GiftingAutomation
from mudae_web.app import WebServerContext, build_account_preset_snapshot, create_app


class MainAccountCooldownTrackerTests(unittest.TestCase):
    def test_unknown_policy_hold_vs_allow(self):
        tracker = MainAccountCooldownTracker()
        allowed_hold, _ = tracker.is_claim_allowed("111222333", unknown_policy="hold")
        allowed_allow, _ = tracker.is_claim_allowed("111222333", unknown_policy="allow")
        self.assertFalse(allowed_hold)
        self.assertTrue(allowed_allow)

    def test_ready_blocks_and_cooldown_allows_until_reset(self):
        tracker = MainAccountCooldownTracker()
        now = datetime.datetime(2026, 11, 25, 12, 0, tzinfo=datetime.timezone.utc)

        # Main claim is ready -> alt must hold
        tracker.update_status("999", claim_available=True, source="live", observed_at_utc=now)
        allowed, _ = tracker.is_claim_allowed("999", unknown_policy="hold", now_utc=now)
        self.assertFalse(allowed)

        # Main claims -> alt is allowed for the cooldown period
        reset_at = now + datetime.timedelta(minutes=90)
        tracker.mark_claimed("999", cooldown_until_utc=reset_at, source="claim", observed_at_utc=now)
        allowed_mid, _ = tracker.is_claim_allowed(
            "999", unknown_policy="hold", now_utc=now + datetime.timedelta(minutes=30)
        )
        self.assertTrue(allowed_mid)

        # After cooldown expires -> Main claim is ready again -> alt must hold
        allowed_after_reset, _ = tracker.is_claim_allowed(
            "999", unknown_policy="hold", now_utc=reset_at + datetime.timedelta(seconds=5)
        )
        self.assertFalse(allowed_after_reset)


class MultiAccountConfigValidationTests(unittest.TestCase):
    def test_max_5_accounts_enforced_and_resolved(self):
        accounts = [
            {"slot": i, "label": f"Acc {i}", "token": f"tok_{i}", "role": "main" if i == 1 else "alt", "enabled": True}
            for i in range(1, 6)
        ]
        preset = {
            "prefix": "$", "mudae_prefix": "$", "roll_command": "wa",
            "claim_interval": 180, "roll_interval": 60, "max_dk_power": 100,
            "channel_id": "12345",
            "accounts": accounts,
        }
        self.assertEqual(MAX_MULTI_ACCOUNTS, 5)
        self.assertEqual(validate_preset(preset, require_runtime=True), [])
        self.assertEqual(len(resolve_preset_accounts(preset)), 5)

        # 6th account must fail validation
        preset_6 = {
            **preset,
            "accounts": accounts + [{"slot": 6, "label": "Acc 6", "token": "tok_6", "role": "alt", "enabled": True}],
        }
        errs = validate_preset(preset_6, require_runtime=True)
        self.assertTrue(any("Maximum 5" in e for e in errs), errs)

    def test_duplicate_tokens_rejected(self):
        preset = {
            "prefix": "$", "mudae_prefix": "$", "roll_command": "wa",
            "claim_interval": 180, "roll_interval": 60, "max_dk_power": 100,
            "channel_id": "12345",
            "accounts": [
                {"slot": 1, "token": "same_tok", "role": "main", "enabled": True},
                {"slot": 2, "token": "same_tok", "role": "alt", "enabled": True},
            ],
        }
        errs = validate_preset(preset, require_runtime=True)
        self.assertTrue(any("Duplicate" in e for e in errs), errs)

    def test_live_config_includes_multi_account_attributes(self):
        client = SimpleNamespace(command_prefix="$", hourly_tu_refresh=False)
        configure_client(client, "Alt1", {"channel_id": 123, "_account_role": "alt"},
                         bot_name="MudaRemote", claim_emojis=["💖"], kakera_emojis=["kakera"],
                         sphere_emojis=[], slash_available=False)
        self.assertFalse(client.claim_only_if_main_cooldown)
        changed = apply_live_config(
            client,
            {
                "channel_id": 123,
                "claim_only_if_main_cooldown": True,
                "main_account_id": "555666777",
                "auto_give_characters_enabled": True,
                "auto_give_delay_seconds": 2.0,
            },
            bot_name="MudaRemote",
            claim_emojis=["💖"],
            kakera_emojis=["kakera"],
            sphere_emojis=[],
            slash_available=False,
        )
        self.assertIn("claim_only_if_main_cooldown", LIVE_CONFIG_ATTRIBUTES)
        self.assertIn("claim_only_if_main_cooldown", changed)
        self.assertTrue(client.claim_only_if_main_cooldown)
        self.assertTrue(client.auto_give_characters_enabled)
        self.assertEqual(client.main_account_id, "555666777")


@pytest.mark.anyio
async def test_gifting_skips_self_and_retries_alt_syntax():
    sent = []

    async def mock_send(ch, content):
        sent.append(content)
        return True

    async def mock_wait(secs):
        pass

    # 1. Self target skips immediately
    self_client = SimpleNamespace(user=SimpleNamespace(id=123456), auto_give_count=0, recent_gifts=[])
    g_self = GiftingAutomation(
        self_client,
        {"auto_give_characters_enabled": True, "main_account_id": "123456"},
        send_func=mock_send,
        wait_func=mock_wait,
    )
    assert await g_self.transfer_character(SimpleNamespace(), "Rem") is False
    assert sent == []

    # 2. Alt target retries @main <char> when first prompt isn't matched
    alt_client = SimpleNamespace(user=SimpleNamespace(id=999999), auto_give_count=0, recent_gifts=[])

    class MockHistory:
        def __init__(self, should_prompt):
            self.should_prompt = should_prompt
            self.done = False

        def __aiter__(self):
            return self

        async def __anext__(self):
            if not self.done and self.should_prompt:
                self.done = True
                return SimpleNamespace(
                    author=SimpleNamespace(id=432610292342587392),
                    content="Do you want to give **Saber** to <@123456>? (y/n)",
                )
            raise StopAsyncIteration

    class MockChan:
        def __init__(self):
            self.calls = 0

        def history(self, limit=6):
            self.calls += 1
            return MockHistory(should_prompt=(self.calls >= 2))

    g_alt = GiftingAutomation(
        alt_client,
        {"auto_give_characters_enabled": True, "main_account_id": "123456", "auto_give_retry_alt_syntax": True},
        send_func=mock_send,
        wait_func=mock_wait,
    )
    ok = await g_alt.transfer_character(MockChan(), "Saber")
    assert ok is True
    assert sent == ["$give Saber <@123456>", "$give <@123456> Saber", "y"]
    assert alt_client.auto_give_count == 1


@pytest.mark.anyio
async def test_web_api_multi_account_start_stop_and_status(tmp_path):
    presets_path = tmp_path / "presets.json"
    presets_path.write_text(json.dumps({"Team": {"channel_id": "11111"}}), encoding="utf-8")

    mgr = RuntimeManager()
    ctx = WebServerContext(presets_path=str(presets_path), runtime_manager=mgr, default_preset="Team")
    app = create_app(ctx)

    from aiohttp.test_utils import TestClient, TestServer
    server = TestServer(app)
    client = TestClient(server)
    await client.start_server()
    try:
        # Save 3 accounts (Main + 2 Alts)
        resp = await client.post("/api/presets", json={
            "name": "Team",
            "data": {
                "channel_id": "11111",
                "main_account_id": "100001",
                "auto_give_characters_enabled": True,
                "claim_only_if_main_cooldown": True,
                "accounts": [
                    {"slot": 1, "label": "Main", "token": "tok_a", "role": "main", "enabled": True},
                    {"slot": 2, "label": "Alt 1", "token": "tok_b", "role": "alt", "enabled": True, "auto_give_characters": True, "claim_only_if_main_cooldown": True},
                    {"slot": 3, "label": "Alt 2", "token": "tok_c", "role": "alt", "enabled": True, "auto_give_characters": True, "claim_only_if_main_cooldown": True},
                ],
            },
        })
        assert resp.status == 200
        assert (await resp.json())["success"] is True

        # Start all 3 accounts via /api/bot/start
        with patch.object(BotInstance, "start", return_value=True):
            start_resp = await client.post("/api/bot/start", json={"preset_name": "Team"})
            assert start_resp.status == 200
            start_data = await start_resp.json()
            assert start_data["success"] is True
            assert start_data["count"] == 3
            assert len(start_data["instance_ids"]) == 3

        # Verify role overrides on started snapshots
        main_snap = mgr._instances["Team-slot-1"].preset_data
        alt_snap = mgr._instances["Team-slot-2"].preset_data
        assert main_snap["auto_give_characters_enabled"] is False
        assert main_snap["claim_only_if_main_cooldown"] is False
        assert alt_snap["auto_give_characters_enabled"] is True
        assert alt_snap["claim_only_if_main_cooldown"] is True

        # Verify /api/status returns all 3 in accounts_status
        status_resp = await client.get("/api/status")
        assert status_resp.status == 200
        status_json = await status_resp.json()
        assert len(status_json["accounts_status"]) == 3
        assert "main_account_status" in status_json

        # Verify stop all works
        with patch.object(mgr, "stop_instance", return_value=True), \
             patch.object(mgr, "remove_instance", return_value=True):
            stop_resp = await client.post("/api/bot/stop", json={})
            assert stop_resp.status == 200
            stop_data = await stop_resp.json()
            assert stop_data["success"] is True
            assert stop_data["count"] == 3
    finally:
        await client.close()
