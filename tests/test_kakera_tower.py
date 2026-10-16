import pytest
from mudae_core.kakera_tower import parse_tower_info, TowerAutomation


def test_parse_tower_info():
    text = (
        "**User**'s Kakera Tower:\n"
        "Floor 1: +1 roll per hour (completed)\n"
        "Floor 2: -15 min claim reset (completed)\n"
        "Floor 3: +10% kakera value (completed)\n"
        "Total floors: 3\n"
        "Cost for floor 4: 6,500 <:kakera:469835869059153940>"
    )
    floors, cost = parse_tower_info(text)
    assert floors == 3
    assert cost == 6500


def test_tower_automation_can_build():
    preset = {"auto_tower_enabled": True, "tower_max_floors": 5}
    tower = TowerAutomation(client=None, preset_data=preset)
    tower.floors_built = 3
    tower.next_floor_cost = 6500

    # Badges not maxed -> should not build
    assert tower.can_build(current_kakera=10000, badges_maxed=False) is False

    # Insufficient kakera -> should not build
    assert tower.can_build(current_kakera=4000, badges_maxed=True) is False

    # Badges maxed and sufficient kakera -> can build
    assert tower.can_build(current_kakera=7000, badges_maxed=True) is True

    # Tower already at max floors ceiling -> should not build
    tower.floors_built = 5
    assert tower.can_build(current_kakera=20000, badges_maxed=True) is False
