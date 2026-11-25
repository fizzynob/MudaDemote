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
        self.kakera_threshold = int(preset_data.get("auto_give_kakera_threshold", 5000) or 5000)
        self.kakera_reserve = max(0, int(preset_data.get("auto_give_kakera_reserve", 1000) or 0))
        self.give_delay = max(0.0, float(preset_data.get("auto_give_delay_seconds", 0.0) or 0.0))
        self.retry_alt_syntax = bool(preset_data.get("auto_give_retry_alt_syntax", True))
        self.main_account_id = str(preset_data.get("main_account_id", "") or "").strip()

    def update_config(self, preset_data: dict):
        """Update live settings."""
        self.give_characters = bool(preset_data.get("auto_give_characters_enabled", False))
        self.give_kakera = bool(preset_data.get("auto_give_kakera_enabled", False))
        self.kakera_threshold = int(preset_data.get("auto_give_kakera_threshold", 5000) or 5000)
        self.kakera_reserve = max(0, int(preset_data.get("auto_give_kakera_reserve", 1000) or 0))
        self.give_delay = max(0.0, float(preset_data.get("auto_give_delay_seconds", 0.0) or 0.0))
        self.retry_alt_syntax = bool(preset_data.get("auto_give_retry_alt_syntax", True))
        self.main_account_id = str(preset_data.get("main_account_id", "") or "").strip()

    def sync_from_client(self, main_account_id: Optional[str] = None):
        """Synchronize live config flags directly from the running Discord client."""
        if self.client is None:
            return
        self.give_characters = bool(getattr(self.client, "auto_give_characters_enabled", self.give_characters))
        self.give_kakera = bool(getattr(self.client, "auto_give_kakera_enabled", self.give_kakera))
        self.kakera_threshold = int(getattr(self.client, "auto_give_kakera_threshold", self.kakera_threshold) or 5000)
        self.kakera_reserve = max(0, int(getattr(self.client, "auto_give_kakera_reserve", self.kakera_reserve) or 0))
        self.give_delay = max(0.0, float(getattr(self.client, "auto_give_delay_seconds", self.give_delay) or 0.0))
        self.retry_alt_syntax = bool(getattr(self.client, "auto_give_retry_alt_syntax", self.retry_alt_syntax))
        resolved_main = main_account_id if main_account_id is not None else getattr(self.client, "main_account_id", self.main_account_id)
        self.main_account_id = str(resolved_main or "").strip()

    def is_configured(self) -> bool:
        """Check if gifting is properly configured with a destination account."""
        return bool(self.main_account_id and self.main_account_id.isdigit() and int(self.main_account_id) > 0)

    def _is_self_target(self) -> bool:
        own_id = getattr(getattr(self.client, "user", None), "id", None)
        return bool(own_id is not None and self.main_account_id and str(own_id) == self.main_account_id)

    async def _find_and_confirm_prompt(self, channel, char_name: Optional[str] = None) -> bool:
        confirmed = False
        prompt_msg = None
        async for msg in channel.history(limit=6):
            if getattr(getattr(msg, "author", None), "id", None) == 432610292342587392:  # TARGET_BOT_ID
                content = (getattr(msg, "content", "") or "").lower()
                embed_desc = ""
                for emb in getattr(msg, "embeds", ()) or ():
                    embed_desc += " " + (getattr(emb, "description", "") or "").lower()
                combined = content + " " + embed_desc
                has_prompt_marker = (
                    "(y/n" in combined
                    or "yes/no" in combined
                    or "(y /" in combined
                    or "type y to confirm" in combined
                    or "click to confirm" in combined
                )
                has_char = True if not char_name else (char_name.lower() in combined)
                if has_prompt_marker and has_char:
                    confirmed = True
                    prompt_msg = msg
                    break
                # Check interactive confirmation button if Mudae uses buttons
                for comp in getattr(msg, "components", ()) or ():
                    for btn in getattr(comp, "children", ()) or ():
                        emoji_name = str(getattr(getattr(btn, "emoji", None), "name", "") or "").lower()
                        label_text = str(getattr(btn, "label", "") or "").lower()
                        if any(tok in emoji_name or tok in label_text for tok in ("white_check_mark", "✅", "confirm", "yes")) and not getattr(btn, "disabled", False):
                            if has_char:
                                try:
                                    await self.wait(1.0)
                                    await btn.click()
                                    return True
                                except Exception:
                                    pass
        if confirmed:
            await self.wait(1.5)
            await self.send(channel, "y")
            return True
        return False

    async def transfer_character(self, channel, char_name: str, mudae_prefix: str = "$") -> bool:
        """Execute $give <char> @main with y/n confirmation (and optional @main <char> fallback)."""
        if not self.give_characters or not self.is_configured():
            return False
        if self._is_self_target():
            self.log(f"Auto-Gift skipped for '{char_name}': claiming account is already the main account.", "INFO")
            return False

        target_mention = f"<@{self.main_account_id}>"
        if self.give_delay > 0:
            await self.wait(self.give_delay)

        commands_to_try = [f"{mudae_prefix}give {char_name} {target_mention}"]
        if self.retry_alt_syntax:
            commands_to_try.append(f"{mudae_prefix}give {target_mention} {char_name}")

        self.log(f"Auto-Gift: Transferring '{char_name}' to main account ({self.main_account_id})...", "INFO")

        try:
            for idx, cmd in enumerate(commands_to_try):
                if not await self.send(channel, cmd):
                    return False
                await self.wait(2.0)

                if await self._find_and_confirm_prompt(channel, char_name=char_name):
                    self.log(f"Auto-Gift: Sent confirmation for '{char_name}'.", "INFO")
                    if self.client is not None:
                        self.client.auto_give_count = int(getattr(self.client, "auto_give_count", 0) or 0) + 1
                        gifts = getattr(self.client, "recent_gifts", None)
                        if isinstance(gifts, list):
                            gifts.insert(0, {"character": char_name, "target": self.main_account_id})
                            del gifts[20:]
                    return True

                if idx == 0 and len(commands_to_try) > 1:
                    self.log(f"Auto-Gift: No prompt for '<char> @main'; retrying with '@main <char>' syntax for '{char_name}'.", "INFO")

            self.log(f"Auto-Gift: No confirmation prompt seen for '{char_name}'.", "WARN")
            return False
        except Exception as exc:
            self.log(f"Auto-Gift error transferring '{char_name}': {exc}", "ERROR")
            return False

    async def transfer_kakera(self, channel, current_kakera: int, mudae_prefix: str = "$") -> bool:
        """Execute $givek <amount> @main if kakera exceeds threshold."""
        if not self.give_kakera or not self.is_configured():
            return False
        if self._is_self_target():
            return False
        if current_kakera < self.kakera_threshold:
            return False

        amount_to_give = current_kakera - self.kakera_reserve
        if amount_to_give <= 0:
            return False

        target_mention = f"<@{self.main_account_id}>"
        cmd = f"{mudae_prefix}givek {amount_to_give} {target_mention}"
        self.log(f"Auto-Gift: Transferring {amount_to_give} kakera to main account...", "INFO")

        try:
            if not await self.send(channel, cmd):
                return False
            await self.wait(2.0)

            if await self._find_and_confirm_prompt(channel, char_name=None):
                self.log(f"Auto-Gift: Confirmed kakera transfer of {amount_to_give}.", "INFO")
                return True
            return False
        except Exception as exc:
            self.log(f"Auto-Gift kakera error: {exc}", "ERROR")
            return False
