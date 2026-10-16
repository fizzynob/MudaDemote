import datetime
import pytest
from types import SimpleNamespace
from mudae_core.auto_discovery import (
    score_channel_name,
    parse_tu_reset_boundaries,
    ServerDiscovery,
    TARGET_BOT_ID,
)


def test_score_channel_name():
    score, role = score_channel_name("mudae-rolls")
    assert score >= 50
    assert role == "roll"

    score_cmd, role_cmd = score_channel_name("bot-commands")
    assert score_cmd >= 35
    assert role_cmd == "command"

    score_gen, role_gen = score_channel_name("general-chat")
    assert score_gen == 0
    assert role_gen == "general"


def test_parse_tu_reset_boundaries():
    now = datetime.datetime(2026, 10, 16, 12, 10, 0, tzinfo=datetime.timezone.utc)
    # 25 minutes remaining -> reset at minute 35 (12:35)
    content = (
        "User, rolls reset in 25 min.\n"
        "can't claim for 2h 15 min."
    )
    reset_min, claim_int = parse_tu_reset_boundaries(content, now_utc=now)
    assert reset_min == 35
    assert claim_int == 180  # > 120 minutes -> 3 hours claim interval


def test_server_discovery_guild_scan():
    client = SimpleNamespace()

    class MockPerms:
        read_messages = True
        send_messages = True
        read_message_history = True

    channel_roll = SimpleNamespace(
        id=11111, name="mudae-rolls",
        permissions_for=lambda me: MockPerms()
    )
    channel_cmd = SimpleNamespace(
        id=22222, name="bot-commands",
        permissions_for=lambda me: MockPerms()
    )

    mock_guild = SimpleNamespace(
        id=99999,
        name="Anime Club",
        members=[SimpleNamespace(id=TARGET_BOT_ID)],
        text_channels=[channel_roll, channel_cmd],
        me=SimpleNamespace(),
    )
    client.guilds = [mock_guild]

    scan = ServerDiscovery.inspect_guild_channels(client, 99999)
    assert scan["guild_name"] == "Anime Club"
    assert scan["mudae_present"] is True
    assert scan["recommended_roll_channel"]["id"] == "11111"
    assert scan["recommended_command_channel"]["id"] == "22222"


def test_is_guild_allowed():
    from mudae_core.auto_discovery import is_guild_allowed

    # Unrestricted (None)
    assert is_guild_allowed(123456, None) is True
    assert is_guild_allowed("99999", None) is True

    # Empty whitelist -> No guilds allowed
    assert is_guild_allowed(123456, []) is False

    # Explicit whitelist
    whitelist = ["123456", "789012"]
    assert is_guild_allowed(123456, whitelist) is True
    assert is_guild_allowed("789012", whitelist) is True
    assert is_guild_allowed(999999, whitelist) is False


def test_server_discovery_whitelist_filtering():
    client = SimpleNamespace()
    g1 = SimpleNamespace(id=111, name="Server 1", members=[], icon=None, member_count=10)
    g2 = SimpleNamespace(id=222, name="Server 2", members=[], icon=None, member_count=20)
    client.guilds = [g1, g2]

    # Without whitelist -> both allowed
    all_guilds = ServerDiscovery.list_accessible_guilds(client, None)
    assert len(all_guilds) == 2
    assert all_guilds[0]["allowed"] is True
    assert all_guilds[1]["allowed"] is True

    # With whitelist -> only g2 allowed
    whitelisted = ServerDiscovery.list_accessible_guilds(client, ["222"])
    g2_entry = next(g for g in whitelisted if g["id"] == "222")
    g1_entry = next(g for g in whitelisted if g["id"] == "111")
    assert g2_entry["allowed"] is True
    assert g1_entry["allowed"] is False

