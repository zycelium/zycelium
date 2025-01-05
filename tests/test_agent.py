import asyncio

import pytest

from zycelium import Agent


def test_agent_initialization():
    agent = Agent(name="test-agent")
    assert agent.name == "test-agent"
    assert isinstance(agent.uuid, str)
    assert len(agent.uuid) == 32


def test_agent_custom_uuid():
    agent = Agent(uuid="custom-uuid")
    assert agent.uuid == "custom-uuid"


def test_agent_sync_hooks():
    agent = Agent()
    started = False
    stopped = False

    @agent.on_start
    def startup():
        nonlocal started
        started = True
        agent.stop()

    @agent.on_stop
    def shutdown():
        nonlocal stopped
        stopped = True

    agent.run()
    assert started
    assert stopped


@pytest.mark.asyncio
async def test_agent_async_hooks():
    agent = Agent()
    started = False
    stopped = False

    @agent.on_start
    async def startup():
        nonlocal started
        started = True
        await agent.stop()

    @agent.on_stop
    async def shutdown():
        nonlocal stopped
        stopped = True

    await agent.run()
    assert started
    assert stopped


def test_invalid_hook_type():
    agent = Agent()
    with pytest.raises(ValueError):
        agent.on_start("not-a-callable")
    with pytest.raises(ValueError):
        agent.on_stop("not-a-callable")


@pytest.mark.asyncio
async def test_agent_stop_without_hooks():
    agent = Agent()
    task = asyncio.create_task(agent.run())
    await asyncio.sleep(0.1)
    await agent.stop()
    await task
