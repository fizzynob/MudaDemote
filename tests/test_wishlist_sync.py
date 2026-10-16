import pytest
from types import SimpleNamespace
from mudae_core.wishlist_sync import (
    clean_character_name,
    parse_wishlist_text,
    WishlistSync,
)


def test_clean_character_name():
    assert clean_character_name("• **Rem** - Re:Zero kara Hajimeru Isekai Seikatsu") == "Rem"
    assert clean_character_name("1. **Megumin** (KonoSuba)") == "Megumin"
    assert clean_character_name("★ **Zero Two** (DARLING in the FRANXX) - 850 kakera") == "Zero Two"
    assert clean_character_name("Asuka Langley Soryu") == "Asuka Langley Soryu"


def test_parse_wishlist_text():
    sample_text = (
        "User's wishlist (3/100 characters):\n"
        "• **Rem** - Re:Zero\n"
        "• **Megumin** - KonoSuba\n"
        "• **Zero Two** - DARLING in the FRANXX\n"
        "Page 1/1"
    )
    parsed = parse_wishlist_text(sample_text)
    assert parsed == ["Megumin", "Rem", "Zero Two"]


def test_wishlist_sync_integration():
    client = SimpleNamespace(wishlist=["Asuka"])
    saved_patches = []

    def mock_save(patch):
        saved_patches.append(patch)

    preset = {"auto_wishlist_sync_enabled": True, "wishlist_remove_claimed": True}
    sync = WishlistSync(client, preset, save_func=mock_save)

    # Ingest $wll response
    msg = "• **Rem** - Re:Zero\n• **Megumin** - KonoSuba"
    updated = sync.on_wishlist_response(msg)
    assert "Asuka" in updated
    assert "Rem" in updated
    assert "Megumin" in updated
    assert len(saved_patches) == 1
    assert "Rem" in saved_patches[0]["wishlist"]

    # Claim character and verify removal
    removed = sync.on_character_claimed("Rem")
    assert removed is True
    assert "Rem" not in client.wishlist
    assert "Asuka" in client.wishlist
