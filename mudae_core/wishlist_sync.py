"""Mudae Wishlist synchronization ($wl, $wll) and management."""

import re
from typing import List, Set


def clean_character_name(raw_line: str) -> str:
    """Clean a single line from a Mudae wishlist into an exact character name."""
    line = raw_line.strip()
    if not line:
        return ""
    # Strip markdown bold, italics, code, strikethrough
    line = re.sub(r"[*_~`]", "", line)
    # Strip leading bullet points, numbers, stars, emojis
    line = re.sub(r"^[\s•\-\d.\u2605\u2B50\U0001F496\U0001F497\U0001F498\U0001F499\U0001F49C\U0001F90E\U0001F90D]+", "", line).strip()
    # If formatted as 'Character - Series', take the character name
    if " - " in line:
        line = line.split(" - ")[0].strip()
    # If formatted as 'Character (Series)', take the character name
    if " (" in line and line.endswith(")"):
        line = line[:line.rfind(" (")].strip()
    # Strip any trailing kakera or rank markers
    line = re.sub(r"<:kakera:\d+>|\(\d+ kakera\)|#\d+", "", line).strip()
    return line


def parse_wishlist_text(text: str, embeds: list = None) -> List[str]:
    """Parse character names from Mudae's $wl or $wll responses."""
    characters: Set[str] = set()

    sources = [text or ""]
    for emb in (embeds or []):
        if hasattr(emb, "description") and emb.description:
            sources.append(emb.description)
        for field in getattr(emb, "fields", ()) or ():
            if hasattr(field, "value") and field.value:
                sources.append(field.value)

    combined = "\n".join(sources)
    for line in combined.splitlines():
        line = line.strip()
        if not line:
            continue
        # Skip header lines, page counters, footer notes
        if re.search(r"\b(?:wishlist|page \d+|characters?|total|keys?)\b", line, re.IGNORECASE) and "/" in line:
            continue
        cleaned = clean_character_name(line)
        if cleaned and len(cleaned) >= 2 and not cleaned.isdigit():
            characters.add(cleaned)

    return sorted(list(characters))


class WishlistSync:
    """Manages periodic or on-demand synchronization with Mudae's wishlist."""

    def __init__(self, client, preset_data, send_func=None, save_func=None, log_func=None):
        self.client = client
        self.send = send_func
        self.save = save_func
        self.log = log_func or (lambda msg, lvl="INFO": None)
        self.enabled = bool(preset_data.get("auto_wishlist_sync_enabled", False))
        self.remove_claimed = bool(preset_data.get("wishlist_remove_claimed", False))
        self.sync_interval_hours = int(preset_data.get("wishlist_sync_interval_hours", 6))
        self.last_sync_timestamp = 0.0
        self.pending_sync = False

    def update_config(self, preset_data: dict):
        """Update live settings."""
        self.enabled = bool(preset_data.get("auto_wishlist_sync_enabled", False))
        self.remove_claimed = bool(preset_data.get("wishlist_remove_claimed", False))
        self.sync_interval_hours = int(preset_data.get("wishlist_sync_interval_hours", 6))

    def on_wishlist_response(self, text: str, embeds: list = None) -> List[str]:
        """Consume $wl or $wll response to update client's wishlist."""
        parsed = parse_wishlist_text(text, embeds)
        if parsed:
            # Merge or overwrite client wishlist
            current = set(getattr(self.client, "wishlist", []))
            updated = sorted(list(current.union(parsed)))
            self.client.wishlist = updated
            self.pending_sync = False
            self.log(f"Wishlist synced: {len(parsed)} characters imported (total: {len(updated)})", "INFO")
            if self.save:
                self.save({"wishlist": updated})
            return updated
        return []

    def on_character_claimed(self, char_name: str) -> bool:
        """Handle claimed character: optionally remove from active wishlist."""
        if not self.remove_claimed:
            return False
        char_lower = char_name.strip().lower()
        current = getattr(self.client, "wishlist", [])
        filtered = [c for c in current if c.strip().lower() != char_lower]
        if len(filtered) < len(current):
            self.client.wishlist = filtered
            self.log(f"Removed claimed character '{char_name}' from wishlist", "INFO")
            if self.save:
                self.save({"wishlist": filtered})
            return True
        return False
