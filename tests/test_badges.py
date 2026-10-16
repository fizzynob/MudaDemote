import pytest
from mudae_core.badges import (
    BadgeAutomation,
    get_badge_cost,
    parse_badge_levels,
    BASE_BADGE_COSTS,
)


def test_parse_badge_levels_english():
    text = (
        "**User**'s badges:\n"
        "Bronze IV: $wa $ha\n"
        "Silver II: +200 kakera\n"
        "Gold I: +10% kakera value\n"
        "Ruby 0: None\n"
        "Emerald 0: None\n"
        "Sapphire 0: None"
    )
    levels = parse_badge_levels(text)
    assert levels["bronze"] == 4
    assert levels["silver"] == 2
    assert levels["gold"] == 1
    assert levels["ruby"] == 0
    assert levels["emerald"] == 0
    assert levels["sapphire"] == 0


def test_parse_badge_levels_multilingual():
    text = (
        "Insignias de **User**:\n"
        "Bronce II: bonificación\n"
        "Plata III: más kakera\n"
        "Oro IV: valor aumentado\n"
        "Rubí I: descuento\n"
        "Zafiro 0: nada\n"
        "Esmeralda 0: nada"
    )
    levels = parse_badge_levels(text)
    assert levels["bronze"] == 2
    assert levels["silver"] == 3
    assert levels["gold"] == 4
    assert levels["ruby"] == 1
    assert levels["sapphire"] == 0
    assert levels["emerald"] == 0


def test_get_badge_cost_base_and_ruby_discount():
    # Base cost without Ruby 4
    assert get_badge_cost("bronze", 1, ruby_level=0) == 1000
    assert get_badge_cost("bronze", 2, ruby_level=2) == 2000
    assert get_badge_cost("gold", 1, ruby_level=3) == 1500
    assert get_badge_cost("ruby", 4, ruby_level=3) == 12000

    # Ruby 4 active: 25% discount on all badges EXCEPT Ruby itself
    assert get_badge_cost("bronze", 1, ruby_level=4) == 750
    assert get_badge_cost("silver", 1, ruby_level=4) == 750
    assert get_badge_cost("gold", 1, ruby_level=4) == 1125
    assert get_badge_cost("emerald", 1, ruby_level=4) == 2250
    assert get_badge_cost("ruby", 1, ruby_level=4) == 3000  # Ruby is not discounted


def test_badge_automation_progression():
    preset = {"auto_badges_enabled": True, "badge_strategy": "optimal", "badge_max_tier": 4}
    auto = BadgeAutomation(client=None, preset_data=preset)

    # Initial state: 0 on all badges, 500 kakera -> cannot afford Bronze 1 (1000)
    assert auto.get_next_upgrade(current_kakera=500) is None

    # Kakera = 1200 -> can afford Bronze 1 (cost 1000)
    up = auto.get_next_upgrade(current_kakera=1200)
    assert up == ("bronze", 1, 1000)

    # Update state: Bronze 1 acquired
    auto.current_levels["bronze"] = 1
    # Next required step is Bronze 2 (cost 2000)
    assert auto.get_next_upgrade(current_kakera=1500) is None
    assert auto.get_next_upgrade(current_kakera=2500) == ("bronze", 2, 2000)

    # Update state: Bronze 2 acquired -> next is Silver 1
    auto.current_levels["bronze"] = 2
    assert auto.get_next_upgrade(current_kakera=1000) == ("silver", 1, 1000)
