"""
Zycelium Agent.
"""

import asyncio
from inspect import iscoroutinefunction
from typing import Any, Awaitable, Callable, Optional, TypeAlias, Union
from uuid import uuid4

from asgiref.sync import sync_to_async
from asyncgnostic import awaitable

Hook: TypeAlias = Union[Callable[[], Any], Callable[[], Awaitable[Any]]]


class Agent:
    """
    Args:
        name: Optional name for the agent
        uuid: Optional UUID string for the agent
    """

    def __init__(self, name: Optional[str] = None, uuid: Optional[str] = None) -> None:
        self.name = name or ""
        self.uuid = uuid or uuid4().hex
        self._shutdown_trigger: asyncio.Event = asyncio.Event()
        self._start_hook: Optional[Hook] = None
        self._stop_hook: Optional[Hook] = None

    def run(self) -> None:
        """Start the agent and run until stopped.

        Can be called either synchronously or asynchronously.
        """
        asyncio.run(self._run())

    @awaitable(run)
    async def run(self) -> None:
        await self._run()

    async def _run(self) -> None:
        await self._run_start_hook()
        await self._shutdown_trigger.wait()
        await self._run_stop_hook()

    async def _run_start_hook(self) -> None:
        if not self._start_hook:
            return
        if iscoroutinefunction(self._start_hook):
            await self._start_hook()
        else:
            await sync_to_async(self._start_hook)()

    async def _run_stop_hook(self) -> None:
        if not self._stop_hook:
            return
        if iscoroutinefunction(self._stop_hook):
            await self._stop_hook()
        else:
            await sync_to_async(self._stop_hook)()

    def stop(self) -> None:
        """Stop the agent gracefully.

        Can be called either synchronously or asynchronously.
        """
        self._stop()

    @awaitable(stop)
    async def stop(self) -> None:
        self._stop()

    def _stop(self) -> None:
        self._shutdown_trigger.set()

    def on_start(self, hook: Hook) -> Hook:
        """Decorator to register a function to be called when agent starts.

        Args:
            hook: A callable or coroutine function with no parameters

        Returns:
            The original hook function

        Raises:
            ValueError: If hook is not callable
        """
        if not iscoroutinefunction(hook) and not callable(hook):
            raise ValueError("Hook must be a coroutine or a callable")
        self._start_hook = hook
        return hook

    def on_stop(self, hook: Hook) -> Hook:
        """Decorator to register a function to be called when agent stops.

        Args:
            hook: A callable or coroutine function with no parameters

        Returns:
            The original hook function

        Raises:
            ValueError: If hook is not callable
        """
        if not iscoroutinefunction(hook) and not callable(hook):
            raise ValueError("Hook must be a coroutine or a callable")
        self._stop_hook = hook
        return hook
