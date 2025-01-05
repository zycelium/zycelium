"""
Zycelium Agent.
"""

import asyncio
from inspect import iscoroutinefunction
from typing import Any, Awaitable, Callable, Optional, TypeAlias, Union
from uuid import uuid4

from asgiref.sync import sync_to_async
from asyncgnostic import awaitable

Handler: TypeAlias = Union[Callable[[], Any], Callable[[], Awaitable[Any]]]


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
        self._start_handler: Optional[Handler] = None
        self._stop_handler: Optional[Handler] = None

    def run(self) -> None:
        """Start the agent and run until stopped.

        Can be called either synchronously or asynchronously.
        """
        asyncio.run(self._run())

    @awaitable(run)
    async def run(self) -> None:
        await self._run()

    async def _run(self) -> None:
        await self._run_start_handler()
        await self._shutdown_trigger.wait()
        await self._run_stop_handler()

    async def _run_start_handler(self) -> None:
        if not self._start_handler:
            return
        if iscoroutinefunction(self._start_handler):
            await self._start_handler()
        else:
            await sync_to_async(self._start_handler)()

    async def _run_stop_handler(self) -> None:
        if not self._stop_handler:
            return
        if iscoroutinefunction(self._stop_handler):
            await self._stop_handler()
        else:
            await sync_to_async(self._stop_handler)()

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

    def on_start(self, handler: Handler) -> Handler:
        """Decorator to register a function to be called when agent starts.

        Args:
            handler: A callable or coroutine function with no parameters

        Returns:
            The original handler function

        Raises:
            ValueError: If handler is not callable
        """
        if not iscoroutinefunction(handler) and not callable(handler):
            raise ValueError("Handler must be a coroutine or a callable")
        self._start_handler = handler
        return handler

    def on_stop(self, handler: Handler) -> Handler:
        """Decorator to register a function to be called when agent stops.

        Args:
            handler: A callable or coroutine function with no parameters

        Returns:
            The original handler function

        Raises:
            ValueError: If handler is not callable
        """
        if not iscoroutinefunction(handler) and not callable(handler):
            raise ValueError("Handler must be a coroutine or a callable")
        self._stop_handler = handler
        return handler
