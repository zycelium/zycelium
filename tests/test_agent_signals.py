import asyncio

import pytest

from zycelium import Agent


def test_agent_sync_signals():
    agent = Agent()
    signal_received = False

    @agent.on_start
    def startup():
        agent.signal("test-signal")

    @agent.on_signal("test-signal")
    def handle_signal():
        nonlocal signal_received
        signal_received = True
        agent.stop()

    agent.run()
    assert signal_received


async def test_agent_async_signals():
    agent = Agent()
    signal_received = False

    @agent.on_start
    async def startup():
        await agent.signal("test-signal")

    @agent.on_signal("test-signal")
    async def handle_signal():
        nonlocal signal_received
        signal_received = True
        await agent.stop()

    await agent.run()
    assert signal_received


def test_multiple_signals():
    agent = Agent()
    signals_received = set()

    @agent.on_start
    def startup():
        agent.signal("signal1")
        agent.signal("signal2")
        agent.signal("signal3")

    @agent.on_signal("signal1")
    def handle_signal1():
        signals_received.add("signal1")

    @agent.on_signal("signal2")
    def handle_signal2():
        signals_received.add("signal2")

    @agent.on_signal("signal3")
    def handle_signal3():
        signals_received.add("signal3")
        agent.stop()

    agent.run()
    assert signals_received == {"signal1", "signal2", "signal3"}


def test_invalid_signal_handler():
    agent = Agent()
    with pytest.raises(ValueError):
        agent.on_signal("test")("not-a-callable")


async def test_unhandled_signal():
    agent = Agent()

    @agent.on_start
    async def startup():
        await agent.signal("nonexistent-signal")
        await agent.stop()

    await agent.run()  # Should complete without errors


async def test_mixed_sync_async_signals():
    agent = Agent()
    sync_received = False
    async_received = False

    @agent.on_start
    async def startup():
        await agent.signal("sync-signal")
        await agent.signal("async-signal")

    @agent.on_signal("sync-signal")
    def handle_sync():
        nonlocal sync_received
        sync_received = True

    @agent.on_signal("async-signal")
    async def handle_async():
        nonlocal async_received
        async_received = True
        await agent.stop()

    await agent.run()
    assert sync_received
    assert async_received


async def test_signal_handler_timeout():
    agent = Agent()
    handler_completed = False

    @agent.on_start
    async def startup():
        await agent.signal("slow-signal")
        await agent.stop()

    @agent.on_signal("slow-signal", timeout=0.1)
    async def handle_slow():
        nonlocal handler_completed
        await asyncio.sleep(1.0)  # Sleep longer than timeout
        handler_completed = True

    await agent.run()
    assert not handler_completed  # Handler should not complete due to timeout
