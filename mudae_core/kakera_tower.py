"""Mudae Kakera Tower automation ($kt, $build)."""

import re
from typing import Optional, Tuple


def parse_tower_info(text: str) -> Tuple[int, Optional[int]]:
    """Extract (floors_built, next_floor_cost) from a Mudae $kt response text."""
    lowered = text.lower()
    floors = 0
    cost = None

    # Pattern for total floors built
    floors_match = re.search(
        r"(?:total floors|floors built|andares construídos|pisos construidos|étages construits)\s*:?\s*\**(\d+)\**",
        lowered,
    )
    if floors_match:
        floors = int(floors_match.group(1))
    else:
        # Alternative: highest Floor X header or number
        highest = 0
        for m in re.finditer(r"\b(?:floor|andar|piso|étage)\s*(\d+)\b", lowered):
            num = int(m.group(1))
            if num > highest and ("completed" in lowered or "built" in lowered or "construído" in lowered):
                highest = num
        if highest > 0:
            floors = highest

    # Pattern for next floor cost
    cost_match = re.search(
        r"(?:next floor|cost for floor|próximo andar|costo del piso|prochain étage)[^\d]*([\d,.]+)\s*(?:<:kakera:|\$|kakera)",
        lowered,
    )
    if cost_match:
        raw_cost = cost_match.group(1).replace(",", "").replace(".", "")
        if raw_cost.isdigit():
            cost = int(raw_cost)

    # Fallback estimated cost: floor 1 = 5000, floor 2 = 5500, etc.
    if cost is None:
        cost = 5000 + (floors * 500)

    return floors, cost


class TowerAutomation:
    """Manages kakera tower building decisions."""

    def __init__(self, client, preset_data, send_func=None, log_func=None):
        self.client = client
        self.send = send_func
        self.log = log_func or (lambda msg, lvl="INFO": None)
        self.enabled = bool(preset_data.get("auto_tower_enabled", False))
        self.max_floors = int(preset_data.get("tower_max_floors", 10))
        self.floors_built = 0
        self.next_floor_cost: Optional[int] = 5000
        self.last_build_attempt = 0.0

    def update_config(self, preset_data: dict):
        """Update live settings."""
        self.enabled = bool(preset_data.get("auto_tower_enabled", False))
        self.max_floors = int(preset_data.get("tower_max_floors", 10))

    def on_tower_message(self, content: str):
        """Parse $kt message response."""
        if "$kt" in content.lower() or "floor" in content.lower() or "andar" in content.lower() or "piso" in content.lower():
            floors, cost = parse_tower_info(content)
            self.floors_built = floors
            if cost is not None:
                self.next_floor_cost = cost
            self.log(f"Kakera Tower status: {self.floors_built} floors built, next cost: {self.next_floor_cost}", "DEBUG")

    def can_build(self, current_kakera: int, badges_maxed: bool = True) -> bool:
        """Check if building the next tower floor is eligible."""
        if not self.enabled:
            return False
        if not badges_maxed:
            # Optimal play prioritizes maxing badges before dumping kakera into tower
            return False
        if self.floors_built >= self.max_floors:
            return False
        cost = self.next_floor_cost or (5000 + self.floors_built * 500)
        return current_kakera >= cost

    def get_build_command(self, mudae_prefix: str = "$") -> str:
        """Generate build command string."""
        return f"{mudae_prefix}build"
