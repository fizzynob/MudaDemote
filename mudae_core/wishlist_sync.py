"""Mudae Wishlist synchronization ($wl, $wll) and management."""

import re
from typing import List, Set

WISHLIST_KEYWORDS = ("wishlist", "liste de souhaits", "lista de deseos", "liste des souhaits")

ROLL_WISH_MARKERS = (
    "is on your wishlist",
    "is on <@",
    "est dans votre liste",
    "est dans la liste de",
    "está en tu lista",
    "está en la lista de",
)


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


def is_wishlist_response(text: str = "", embeds: list = None, client_user=None) -> bool:
    """Determine if a Discord message from Mudae is a genuine $wl / $wll wishlist listing."""
    lower_text = (text or "").lower()

    # Roll announcements like "<@user> Rem is on your wishlist!" must NEVER be treated as a wishlist listing
    if any(marker in lower_text for marker in ROLL_WISH_MARKERS):
        return False

    # Check embeds
    for emb in (embeds or []):
        author_name = str(getattr(getattr(emb, "author", None), "name", "") or "").lower()
        title = str(getattr(emb, "title", "") or "").lower()
        description = str(getattr(emb, "description", "") or "").lower()

        if any(marker in description for marker in ROLL_WISH_MARKERS):
            return False

        if any(kw in author_name for kw in WISHLIST_KEYWORDS) or any(kw in title for kw in WISHLIST_KEYWORDS):
            return True

    # Check text message format (plain text $wll format)
    if any(kw in lower_text for kw in WISHLIST_KEYWORDS):
        return True

    # Check if multiple lines have bullet list formatting typical of $wll
    combined = text or ""
    for emb in (embeds or []):
        if getattr(emb, "description", None):
            combined += "\n" + emb.description
    lines = [line.strip() for line in combined.splitlines() if line.strip()]
    bullet_lines = [l for l in lines if l.startswith("•") or re.match(r"^\d+\.\s+", l)]
    if len(bullet_lines) >= 2:
        return True

    return False


def parse_wishlist_text(text: str, embeds: list = None) -> List[str]:
    """Parse character names from Mudae's $wl or $wll responses."""
    characters: Set[str] = set()

    sources = [text or ""]
    has_wishlist_context = any(kw in (text or "").lower() for kw in WISHLIST_KEYWORDS)

    for emb in (embeds or []):
        author_name = str(getattr(getattr(emb, "author", None), "name", "") or "").lower()
        title = str(getattr(emb, "title", "") or "").lower()
        if any(kw in author_name for kw in WISHLIST_KEYWORDS) or any(kw in title for kw in WISHLIST_KEYWORDS):
            has_wishlist_context = True
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
        # Skip roll announcements
        if any(marker in line.lower() for marker in ROLL_WISH_MARKERS):
            continue

        is_bullet_item = bool(re.match(r"^[\s•\-\*\u2605\u2B50]|\d+\.", line))
        if not is_bullet_item and not has_wishlist_context:
            continue

        # Ignore obvious metadata lines
        if not is_bullet_item and re.search(r"\b(?:rank|kakera|claims?|likes?|badge|keys?)\b", line, re.IGNORECASE):
            continue

        cleaned = clean_character_name(line)
        if cleaned and len(cleaned) >= 2 and not cleaned.isdigit():
            if cleaned.lower() in ("claim rank:", "like rank:", "kakera", "claim rank", "like rank"):
                continue
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
        # Only process if auto-sync is enabled or sync was explicitly requested
        if not self.enabled and not self.pending_sync:
            return []

        # Ensure message is actually a Mudae wishlist response, not a roll or chat
        if not is_wishlist_response(text, embeds, getattr(self.client, "user", None)):
            return []

        parsed = parse_wishlist_text(text, embeds)
        if parsed:
            current = set(getattr(self.client, "wishlist", []))
            new_characters = set(parsed) - current
            if not new_characters and not self.pending_sync:
                return list(current)

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
