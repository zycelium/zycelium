import asyncio

import pytest

from zycelium import Agent

NATS_URL = "nats://localhost:4222"
REQUEST_WAIT_TIME = 0.1  # 100ms wait for requests


async def wait_for_requests():
    """Helper to wait for requests to be processed"""
    await asyncio.sleep(REQUEST_WAIT_TIME)


def test_sync_request():
    agent = Agent()
    response = None

    @agent.on_start
    def startup():
        nonlocal response
        response = agent.request("greet", name="World")
        agent.stop()

    @agent.on_request("greet")
    def handle_request(name: str):
        return {"greeting": f"Hello, {name}!"}

    agent.run(NATS_URL)
    assert response == {"greeting": "Hello, World!"}


async def test_async_request():
    agent = Agent()
    response = None

    @agent.on_start
    async def startup():
        nonlocal response
        response = await agent.request("greet", name="World")
        await agent.stop()

    @agent.on_request("greet")
    async def handle_request(name: str):
        return {"greeting": f"Hello, {name}!"}

    await agent.run(NATS_URL)
    assert response == {"greeting": "Hello, World!"}


def test_request_timeout():
    agent = Agent()
    response = None

    @agent.on_start
    def startup():
        nonlocal response
        response = agent.request("slow-response", timeout=0.1)
        agent.stop()

    @agent.on_request("slow-response")
    def handle_request():
        # Simulate slow response by sleeping
        import time

        time.sleep(0.2)
        return {"status": "too late"}

    agent.run(NATS_URL)
    assert response is None


def test_invalid_request_handler():
    agent = Agent()
    with pytest.raises(ValueError):
        agent.on_request("test")("not-a-callable")


async def test_request_with_complex_data():
    agent = Agent()
    response = None

    test_data = {
        "user": {"name": "Alice", "age": 30},
        "items": [1, 2, 3],
        "active": True,
    }

    @agent.on_start
    async def startup():
        nonlocal response
        response = await agent.request("echo", **test_data)
        await agent.stop()

    @agent.on_request("echo")
    async def handle_request(user: dict, items: list, active: bool):
        return {"received": {"user": user, "items": items, "active": active}}

    await agent.run(NATS_URL)
    assert response == {"received": test_data}


async def test_multiple_concurrent_requests():
    agent = Agent()
    responses = []

    @agent.on_start
    async def startup():
        nonlocal responses
        tasks = [agent.request("counter", id=i) for i in range(3)]
        responses = await asyncio.gather(*tasks)
        await agent.stop()

    @agent.on_request("counter")
    async def handle_request(id: int):
        return {"count": id}

    await agent.run(NATS_URL)
    assert responses == [{"count": 0}, {"count": 1}, {"count": 2}]


def test_request_no_handler():
    agent = Agent()
    response = None

    @agent.on_start
    def startup():
        nonlocal response
        response = agent.request("nonexistent")
        agent.stop()

    agent.run(NATS_URL)
    assert response is None


async def test_request_handler_error():
    agent = Agent()
    response = None

    @agent.on_start
    async def startup():
        nonlocal response
        response = await agent.request("error")
        await agent.stop()

    @agent.on_request("error")
    async def handle_request():
        raise ValueError("Simulated error")

    await agent.run(NATS_URL)
    assert response is None


def test_sync_request_threading():
    """Test that sync request handlers run in separate threads."""
    import threading

    agent = Agent()
    main_thread = threading.current_thread()
    handler_thread = None

    @agent.on_start
    def startup():
        agent.request("check-thread")
        agent.stop()

    @agent.on_request("check-thread")
    def handle_request():
        nonlocal handler_thread
        handler_thread = threading.current_thread()
        return {"thread_name": handler_thread.name}

    agent.run(NATS_URL)
    assert handler_thread is not None
    assert handler_thread != main_thread, "Handler should run in different thread"
