"""Mudae Gamemode 2 optimization ($limroul 1 1 1 1)."""

import asyncio


class GamemodeAutomation:
    """Ensures optimal roulette pool limits are enforced in Gamemode 2."""

    def __init__(self, client, preset_data, send_func=None, log_func=None):
        self.client = client
        self.send = send_func
        self.log = log_func or (lambda msg, lvl="INFO": None)
        self.enabled = bool(preset_data.get("auto_limroul_enabled", False))
        self.last_enforced = 0.0

    def update_config(self, preset_data: dict):
        self.enabled = bool(preset_data.get("auto_limroul_enabled", False))

    async def ensure_optimal_limits(self, channel, mudae_prefix: str = "$") -> bool:
        """Send $limroul 1 1 1 1 to lock to minimum roulette pools in Gamemode 2."""
        if not self.enabled:
            return False
        cmd = f"{mudae_prefix}limroul 1 1 1 1"
        self.log("Gamemode: Sending $limroul 1 1 1 1 to optimize roll pool...", "INFO")
        try:
            return await self.send(channel, cmd)
        except Exception as exc:
            self.log(f"Gamemode $limroul error: {exc}", "WARN")
            return False
