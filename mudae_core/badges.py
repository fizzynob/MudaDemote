"""Mudae Badge automation and optimal upgrade planner."""

import re
from typing import Dict, List, Optional, Tuple

BADGE_NAMES = ("bronze", "silver", "gold", "sapphire", "ruby", "emerald")

# Base costs for levels 1, 2, 3, 4
BASE_BADGE_COSTS = {
    "bronze": [1000, 2000, 3000, 4000],
    "silver": [1000, 2000, 3000, 4000],
    "gold": [1500, 3000, 4500, 6000],
    "ruby": [3000, 6000, 9000, 12000],
    "emerald": [3000, 6000, 9000, 12000],
    "sapphire": [3000, 6000, 9000, 12000],
}

# Optimal progression steps: (badge_name, target_level)
OPTIMAL_PROGRESSION: List[Tuple[str, int]] = [
    ("bronze", 1), ("bronze", 2),
    ("silver", 1), ("silver", 2),
    ("gold", 1), ("gold", 2),
    ("ruby", 1), ("ruby", 2), ("ruby", 3), ("ruby", 4),
    ("bronze", 3), ("bronze", 4),
    ("silver", 3), ("silver", 4),
    ("gold", 3), ("gold", 4),
    ("emerald", 1), ("emerald", 2), ("emerald", 3), ("emerald", 4),
    ("sapphire", 1), ("sapphire", 2), ("sapphire", 3), ("sapphire", 4),
]

ROMAN_TO_INT = {"i": 1, "ii": 2, "iii": 3, "iv": 4, "0": 0, "1": 1, "2": 2, "3": 3, "4": 4}

# Multilingual badge name mapping
BADGE_ALIASES = {
    "bronze": "bronze", "bronce": "bronze",
    "silver": "silver", "prata": "silver", "plata": "silver", "argent": "silver",
    "gold": "gold", "ouro": "gold", "oro": "gold", "or": "gold",
    "ruby": "ruby", "rubi": "ruby", "rubí": "ruby",
    "emerald": "emerald", "esmeralda": "emerald", "émeraude": "emerald",
    "sapphire": "sapphire", "safira": "sapphire", "zafiro": "sapphire", "saphir": "sapphire",
}


def get_badge_cost(badge: str, target_level: int, ruby_level: int = 0) -> int:
    """Calculate the kakera cost for the given badge target level (1-4).
    Ruby 4 gives a 25% discount to all other badges.
    """
    badge = badge.lower()
    if badge not in BASE_BADGE_COSTS or target_level < 1 or target_level > 4:
        return 0
    base = BASE_BADGE_COSTS[badge][target_level - 1]
    if ruby_level >= 4 and badge != "ruby":
        return int(base * 0.75)
    return base


def parse_badge_levels(text: str) -> Dict[str, int]:
    """Extract badge tiers (0-4) from a Mudae $badge response text."""
    levels = {b: 0 for b in BADGE_NAMES}
    lowered = text.lower()
    
    # Matches patterns like 'Bronze IV', 'Bronze 4', 'Bronze Level 2', 'Rubi II'
    pattern = re.compile(
        r"\b(bronze|bronce|silver|prata|plata|argent|gold|ouro|oro|or|ruby|rubi|rubí|emerald|esmeralda|émeraude|sapphire|safira|zafiro|saphir)\b[^\n\dIVX]*\b(iv|iii|ii|i|[0-4])\b",
        re.IGNORECASE,
    )
    for match in pattern.finditer(lowered):
        raw_name, raw_level = match.groups()
        canonical = BADGE_ALIASES.get(raw_name.lower())
        if canonical and raw_level.lower() in ROMAN_TO_INT:
            levels[canonical] = ROMAN_TO_INT[raw_level.lower()]
            
    return levels


class BadgeAutomation:
    """Manages badge level tracking and purchase decisions."""

    def __init__(self, client, preset_data, send_func=None, log_func=None):
        self.client = client
        self.send = send_func
        self.log = log_func or (lambda msg, lvl="INFO": None)
        self.enabled = bool(preset_data.get("auto_badges_enabled", False))
        self.strategy = str(preset_data.get("badge_strategy", "optimal")).strip().lower()
        self.max_tier = int(preset_data.get("badge_max_tier", 4))
        self.current_levels: Dict[str, int] = {b: 0 for b in BADGE_NAMES}
        self.pending_badge_check = False
        self.last_purchase_attempt = 0.0

    def update_config(self, preset_data: dict):
        """Update live settings."""
        self.enabled = bool(preset_data.get("auto_badges_enabled", False))
        self.strategy = str(preset_data.get("badge_strategy", "optimal")).strip().lower()
        self.max_tier = int(preset_data.get("badge_max_tier", 4))

    def on_badge_message(self, content: str):
        """Consume message text from Mudae to update badge levels."""
        parsed = parse_badge_levels(content)
        if any(v > 0 for v in parsed.values()) or "badge" in content.lower():
            self.current_levels.update(parsed)
            self.pending_badge_check = False
            self.log(f"Badge levels updated: {self.current_levels}", "DEBUG")

    def get_next_upgrade(self, current_kakera: int) -> Optional[Tuple[str, int, int]]:
        """Determine next badge to upgrade if sufficient kakera is available.
        Returns: (badge_name, target_level, cost) or None.
        """
        if not self.enabled:
            return None

        ruby_lvl = self.current_levels.get("ruby", 0)

        for badge, target_lvl in OPTIMAL_PROGRESSION:
            if target_lvl > self.max_tier:
                continue
            curr = self.current_levels.get(badge, 0)
            if curr < target_lvl:
                # This is the next required step in optimal progression
                cost = get_badge_cost(badge, target_lvl, ruby_lvl)
                if current_kakera >= cost:
                    return (badge, target_lvl, cost)
                # Next required step is too expensive
                return None

        return None

    def get_upgrade_command(self, badge: str, target_lvl: int, mudae_prefix: str = "$") -> str:
        """Generate purchase command string."""
        return f"{mudae_prefix}{badge}"
