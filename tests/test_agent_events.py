import asyncio

import pytest

from zycelium import Agent

NATS_URL = "nats://localhost:4222"
EVENT_WAIT_TIME = 0.1  # 100ms wait for events


async def wait_for_events():
    """Helper to wait for events to be processed"""
    await asyncio.sleep(EVENT_WAIT_TIME)


def test_agent_sync_events():
    agent = Agent()
    event_received = False

    @agent.on_start
    def startup():
        agent.emit("test-event")

    @agent.on_event("test-event")
    def handle_event():
        nonlocal event_received
        event_received = True
        agent.stop()

    agent.run(NATS_URL)
    assert event_received


async def test_agent_async_events():
    agent = Agent()
    event_received = False

    @agent.on_start
    async def startup():
        await agent.emit("test-event")

    @agent.on_event("test-event")
    async def handle_event():
        nonlocal event_received
        event_received = True
        await agent.stop()

    await agent.run(NATS_URL)
    await wait_for_events()
    assert event_received


def test_multiple_events():
    agent = Agent()
    events_received = set()

    @agent.on_start
    def startup():
        agent.emit("event1")
        agent.emit("event2")
        agent.emit("event3")

    @agent.on_event("event1")
    def handle_event1():
        events_received.add("event1")

    @agent.on_event("event2")
    def handle_event2():
        events_received.add("event2")

    @agent.on_event("event3")
    def handle_event3():
        events_received.add("event3")
        agent.stop()

    agent.run(NATS_URL)
    assert events_received == {"event1", "event2", "event3"}


def test_invalid_event_handler():
    agent = Agent()
    with pytest.raises(ValueError):
        agent.on_event("test")("not-a-callable")


async def test_mixed_sync_async_events():
    agent = Agent()
    sync_received = False
    async_received = False

    @agent.on_start
    async def startup():
        await agent.emit("sync-event")
        await agent.emit("async-event")
        await wait_for_events()

    @agent.on_event("sync-event")
    def handle_sync():
        nonlocal sync_received
        sync_received = True

    @agent.on_event("async-event")
    async def handle_async():
        nonlocal async_received
        async_received = True
        await agent.stop()

    await agent.run(NATS_URL)
    assert sync_received
    assert async_received


async def test_event_with_data():
    agent = Agent()
    received_data = None

    @agent.on_start
    async def startup():
        await agent.emit("data-event", message="hello", count=42)

    @agent.on_event("data-event")
    async def handle_event(message: str, count: int):
        nonlocal received_data
        received_data = {"message": message, "count": count}
        await agent.stop()

    await agent.run(NATS_URL)
    await wait_for_events()
    assert received_data == {"message": "hello", "count": 42}
