"""Discord Server and Channel Auto-Discovery for Plug-and-Play deployment."""

import datetime
import re
from typing import Any, Dict, List, Optional, Tuple

TARGET_BOT_ID = 432610292342587392

ROLL_CHANNEL_KEYWORDS = ("mudae", "roll", "rolls", "waifu", "husbando", "gacha", "bot-spam", "bot_spam", "casino")
COMMAND_CHANNEL_KEYWORDS = ("command", "commands", "cmd", "cmds", "spam", "bot", "bots", "private")


def score_channel_name(name: str) -> Tuple[int, str]:
    """Score a channel name and return (score, role_type: 'roll'|'command'|'general')."""
    lowered = name.lower()
    score = 0
    role = "general"

    for kw in ROLL_CHANNEL_KEYWORDS:
        if kw in lowered:
            score += 50
            role = "roll"
            break

    for kw in COMMAND_CHANNEL_KEYWORDS:
        if kw in lowered:
            if role == "roll":
                score += 15
            else:
                score += 35
                role = "command"
            break

    return score, role


def parse_tu_reset_boundaries(content: str, now_utc: Optional[datetime.datetime] = None) -> Tuple[Optional[int], Optional[int]]:
    """Parse Mudae's $tu response to deduce (server_reset_minute, claim_interval_minutes).
    Returns (None, None) if parsing fails.
    """
    now = now_utc or datetime.datetime.now(datetime.timezone.utc)
    server_reset_minute = None
    claim_interval = None

    # Roll reset timer: e.g. "rolls reset in 42 min" or "reinicio en 15 min"
    roll_reset_match = re.search(
        r"(?:reset|reinicio|reinicialização|dans)[^\d\n]*\*{0,2}(\d+h)?\*{0,2}\s*\*{0,2}(\d+)\*{0,2}\s*min",
        content,
        re.IGNORECASE,
    )
    if roll_reset_match:
        hours = int(roll_reset_match.group(1).replace("h", "") if roll_reset_match.group(1) else 0)
        minutes = int(roll_reset_match.group(2) or 0)
        total_remaining_minutes = hours * 60 + minutes
        reset_time = now + datetime.timedelta(minutes=total_remaining_minutes)
        server_reset_minute = reset_time.minute

    # Claim cooldown / interval: e.g. "next interval begins in 1h 45 min" or "can't claim for 2h 30 min"
    claim_match = re.search(
        r"(?:next interval begins in|intervalo começa em|intervalo comienza en|can(?:not|'t) claim[^\d\n]*for)\s*\*{0,2}(\d+h)?\s*(\d+)\*{0,2}\s*min",
        content,
        re.IGNORECASE,
    )
    if claim_match:
        hours = int(claim_match.group(1).replace("h", "") if claim_match.group(1) else 0)
        mins = int(claim_match.group(2) or 0)
        total_mins = hours * 60 + mins
        # Standard Mudae claim intervals are 180 (3h), 120 (2h), or 60 (1h)
        if total_mins > 120:
            claim_interval = 180
        elif total_mins > 60:
            claim_interval = 120
        elif total_mins > 0:
            claim_interval = 60

    return server_reset_minute, claim_interval


def is_guild_allowed(guild_id: Any, allowed_guild_ids: Optional[Any]) -> bool:
    """Check if a Discord Guild ID is permitted under the allowed whitelist.

    If allowed_guild_ids is None, all guilds are permitted.
    If allowed_guild_ids is a collection (list/tuple/set), only matching IDs are permitted.
    """
    if allowed_guild_ids is None:
        return True
    str_id = str(guild_id).strip()
    allowed_set = {str(item).strip() for item in allowed_guild_ids if str(item).strip()}
    return str_id in allowed_set


class ServerDiscovery:
    """Discovers accessible Discord servers and scores optimal channels."""

    @staticmethod
    def list_accessible_guilds(client, allowed_guild_ids: Optional[Any] = None) -> List[Dict[str, Any]]:
        """List all Discord servers the client account is joined to, marking allowed status."""
        results = []
        for guild in getattr(client, "guilds", []) or []:
            has_mudae = any(getattr(m, "id", None) == TARGET_BOT_ID for m in getattr(guild, "members", []) or [])
            icon_url = str(guild.icon.url) if getattr(guild, "icon", None) and hasattr(guild.icon, "url") else None
            is_allowed = is_guild_allowed(guild.id, allowed_guild_ids)
            results.append({
                "id": str(guild.id),
                "name": guild.name,
                "icon_url": icon_url,
                "member_count": getattr(guild, "member_count", 0),
                "mudae_present": has_mudae,
                "allowed": is_allowed,
            })
        return sorted(results, key=lambda g: (g["allowed"], g["mudae_present"], g["member_count"]), reverse=True)

    @staticmethod
    def inspect_guild_channels(client, guild_id: int) -> Dict[str, Any]:
        """Scan a specific guild to discover channels, Mudae bot, and recommended setup."""
        guild = None
        for g in getattr(client, "guilds", []) or []:
            if g.id == int(guild_id):
                guild = g
                break

        if guild is None:
            return {"error": f"Guild ID {guild_id} not found."}

        # Check Mudae member presence
        mudae_member = None
        for m in getattr(guild, "members", []) or []:
            if m.id == TARGET_BOT_ID:
                mudae_member = m
                break

        eligible_channels = []
        me = getattr(guild, "me", None)
        if me is None and hasattr(guild, "get_member") and getattr(client, "user", None):
            me = guild.get_member(client.user.id)

        for ch in getattr(guild, "text_channels", []) or []:
            try:
                if me is not None:
                    perms = ch.permissions_for(me)
                    if not (perms.read_messages and perms.send_messages and perms.read_message_history):
                        continue
                score, role = score_channel_name(ch.name)
                eligible_channels.append({
                    "id": str(ch.id),
                    "name": ch.name,
                    "score": score,
                    "role": role,
                })
            except Exception:
                continue

        # If eligible_channels is empty (e.g. member cache not yet populated), fallback to all text channels
        if not eligible_channels and getattr(guild, "text_channels", None):
            for ch in guild.text_channels:
                score, role = score_channel_name(ch.name)
                eligible_channels.append({
                    "id": str(ch.id),
                    "name": ch.name,
                    "score": score,
                    "role": role,
                })

        eligible_channels.sort(key=lambda c: c["score"], reverse=True)

        recommended_roll = None
        recommended_cmd = None

        roll_candidates = [c for c in eligible_channels if c["role"] == "roll"]
        cmd_candidates = [c for c in eligible_channels if c["role"] == "command"]

        if roll_candidates:
            recommended_roll = roll_candidates[0]
            if len(roll_candidates) > 1 and not cmd_candidates:
                recommended_cmd = roll_candidates[1]
        elif eligible_channels:
            recommended_roll = eligible_channels[0]
            if len(eligible_channels) > 1 and not cmd_candidates:
                recommended_cmd = eligible_channels[1]

        if cmd_candidates and not recommended_cmd:
            recommended_cmd = cmd_candidates[0]

        return {
            "guild_id": str(guild.id),
            "guild_name": guild.name,
            "mudae_present": mudae_member is not None,
            "channels": eligible_channels,
            "recommended_roll_channel": recommended_roll,
            "recommended_command_channel": recommended_cmd,
            "detected_prefix": "$",
        }

