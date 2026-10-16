"""Mudae character and kakera transfer automation ($give, $givek)."""

import asyncio
import re
from typing import Optional


class GiftingAutomation:
    """Manages transferring claimed characters and surplus kakera to a main account."""

    def __init__(self, client, preset_data, send_func=None, wait_func=None, log_func=None):
        self.client = client
        self.send = send_func
        self.wait = wait_func or asyncio.sleep
        self.log = log_func or (lambda msg, lvl="INFO": None)
        self.give_characters = bool(preset_data.get("auto_give_characters_enabled", False))
        self.give_kakera = bool(preset_data.get("auto_give_kakera_enabled", False))
        self.kakera_threshold = int(preset_data.get("auto_give_kakera_threshold", 5000))
        self.main_account_id = str(preset_data.get("main_account_id", "") or "").strip()

    def update_config(self, preset_data: dict):
        """Update live settings."""
        self.give_characters = bool(preset_data.get("auto_give_characters_enabled", False))
        self.give_kakera = bool(preset_data.get("auto_give_kakera_enabled", False))
        self.kakera_threshold = int(preset_data.get("auto_give_kakera_threshold", 5000))
        self.main_account_id = str(preset_data.get("main_account_id", "") or "").strip()

    def is_configured(self) -> bool:
        """Check if gifting is properly configured with a destination account."""
        return bool(self.main_account_id and self.main_account_id.isdigit() and int(self.main_account_id) > 0)

    async def transfer_character(self, channel, char_name: str, mudae_prefix: str = "$") -> bool:
        """Execute $give <char> @main with y/n confirmation."""
        if not self.give_characters or not self.is_configured():
            return False

        target_mention = f"<@{self.main_account_id}>"
        cmd = f"{mudae_prefix}give {char_name} {target_mention}"
        self.log(f"Auto-Gift: Transferring '{char_name}' to main account ({self.main_account_id})...", "INFO")

        try:
            if not await self.send(channel, cmd):
                return False
            await self.wait(2.0)

            # Look for Mudae confirmation prompt in recent messages
            confirmed = False
            async for msg in channel.history(limit=5):
                if msg.author.id == 432610292342587392:  # TARGET_BOT_ID
                    content = (msg.content or "").lower()
                    if ("(y/n" in content or "yes/no" in content or "(y /" in content) and char_name.lower() in content:
                        confirmed = True
                        break

            if confirmed:
                await self.wait(1.5)
                await self.send(channel, "y")
                self.log(f"Auto-Gift: Sent confirmation for '{char_name}'.", "INFO")
                return True
            else:
                self.log(f"Auto-Gift: No confirmation prompt seen for '{char_name}'.", "WARN")
                return False
        except Exception as exc:
            self.log(f"Auto-Gift error transferring '{char_name}': {exc}", "ERROR")
            return False

    async def transfer_kakera(self, channel, current_kakera: int, mudae_prefix: str = "$") -> bool:
        """Execute $givek <amount> @main if kakera exceeds threshold."""
        if not self.give_kakera or not self.is_configured():
            return False
        if current_kakera < self.kakera_threshold:
            return False

        amount_to_give = current_kakera - 1000  # keep a small reserve of 1000
        if amount_to_give <= 0:
            return False

        target_mention = f"<@{self.main_account_id}>"
        cmd = f"{mudae_prefix}givek {amount_to_give} {target_mention}"
        self.log(f"Auto-Gift: Transferring {amount_to_give} kakera to main account...", "INFO")

        try:
            if not await self.send(channel, cmd):
                return False
            await self.wait(2.0)

            confirmed = False
            async for msg in channel.history(limit=5):
                if msg.author.id == 432610292342587392:
                    content = (msg.content or "").lower()
                    if "(y/n" in content or "yes/no" in content or "(y /" in content:
                        confirmed = True
                        break

            if confirmed:
                await self.wait(1.5)
                await self.send(channel, "y")
                self.log(f"Auto-Gift: Confirmed kakera transfer of {amount_to_give}.", "INFO")
                return True
            return False
        except Exception as exc:
            self.log(f"Auto-Gift kakera error: {exc}", "ERROR")
            return False
