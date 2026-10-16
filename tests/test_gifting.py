import pytest
from mudae_core.gifting import GiftingAutomation


def test_gifting_is_configured():
    # Not configured if main_account_id is empty or 0
    auto1 = GiftingAutomation(None, {"main_account_id": ""})
    assert auto1.is_configured() is False

    auto2 = GiftingAutomation(None, {"main_account_id": "0"})
    assert auto2.is_configured() is False

    # Valid ID configured
    auto3 = GiftingAutomation(None, {"main_account_id": "987654321098765432"})
    assert auto3.is_configured() is True


@pytest.mark.anyio
async def test_transfer_character_flow():
    sent_commands = []

    async def mock_send(channel, content):
        sent_commands.append(content)
        return True

    async def mock_wait(seconds):
        pass

    preset = {
        "auto_give_characters_enabled": True,
        "main_account_id": "1234567890",
    }
    gifting = GiftingAutomation(
        client=None,
        preset_data=preset,
        send_func=mock_send,
        wait_func=mock_wait,
    )

    class MockHistory:
        def __aiter__(self):
            return self

        async def __anext__(self):
            # Simulate Mudae's confirmation prompt message
            if not getattr(self, "sent", False):
                self.sent = True
                from types import SimpleNamespace
                return SimpleNamespace(
                    author=SimpleNamespace(id=432610292342587392),
                    content="Do you want to give **Rem** to <@1234567890>? (y/n)",
                )
            raise StopAsyncIteration

    class MockChannel:
        def history(self, limit=5):
            return MockHistory()

    success = await gifting.transfer_character(MockChannel(), "Rem")
    assert success is True
    assert "$give Rem <@1234567890>" in sent_commands
    assert "y" in sent_commands
