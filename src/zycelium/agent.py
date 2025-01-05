"""
Zycelium Agent.
"""

import asyncio
from inspect import iscoroutinefunction
from typing import Any, Awaitable, Callable, Optional, TypeAlias, Union
from uuid import uuid4

from asgiref.sync import sync_to_async
from asyncgnostic import awaitable

from zycelium.logging import get_logger

# Type aliases

Handler: TypeAlias = Union[Callable[[], Any], Callable[[], Awaitable[Any]]]


class Agent:
    """
    Args:
        name: Optional name for the agent
        uuid: Optional UUID string for the agent
    """

    def __init__(
        self,
        name: Optional[str] = None,
        uuid: Optional[str] = None,
        log_level: str = "INFO",
    ) -> None:
        self.name = name or ""
        self.uuid = uuid or uuid4().hex
        logger_name = f"zycelium.agent.{self.name}" if self.name else "zycelium.agent"
        self.logger = get_logger(logger_name, level=log_level)
        self.logger.info("Initializing")
        self._shutdown_trigger: asyncio.Event = asyncio.Event()
        self._start_handler: Optional[Handler] = None
        self._stop_handler: Optional[Handler] = None
        self._signal_handlers: dict[str, Handler] = {}
        self._loop = None  # type: asyncio.AbstractEventLoop
        self._signal_queue: asyncio.Queue = asyncio.Queue()
        self._signal_processor_task: Optional[asyncio.Task] = None

    # Agent Lifecycle

    def run(self) -> None:
        """Start the agent and run until stopped.

        Can be called either synchronously or asynchronously.
        """
        asyncio.run(self._run())

    @awaitable(run)
    async def run(self) -> None:
        await self._run()

    async def _run(self) -> None:
        self.logger.info("Starting up")
        self._loop = asyncio.get_event_loop()
        self._signal_processor_task = asyncio.create_task(self._process_signals())
        await self._run_start_handler()
        await self._shutdown_trigger.wait()
        self.logger.info("Shutting down")
        await self._run_stop_handler()
        if self._signal_processor_task:  # pragma: no cover
            self._signal_processor_task.cancel()
            try:
                await self._signal_processor_task
            except asyncio.CancelledError:
                self.logger.debug("Signal processor task cancelled")
                pass

    async def _run_start_handler(self) -> None:
        if not self._start_handler:
            return
        self.logger.debug("Running start handler")
        if iscoroutinefunction(self._start_handler):
            await self._start_handler()
        else:
            await sync_to_async(self._start_handler)()

    async def _run_stop_handler(self) -> None:
        if not self._stop_handler:
            return
        self.logger.debug("Running stop handler")
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

    # Agent Signals

    async def _process_signals(self) -> None:
        self.logger.debug("Starting signal processor")
        while True:
            signal = await self._signal_queue.get()
            self.logger.debug(f"Processing signal '{signal}'")
            await self._run_signal_handler(signal)
            self._signal_queue.task_done()

    def signal(self, signal: str) -> None:
        """Send a signal to the agent.

        Args:
            signal: The signal name
        """
        self.logger.debug(f"Queueing signal '{signal}'")
        self._loop.call_soon_threadsafe(self._signal_queue.put_nowait, signal)

    @awaitable(signal)
    async def signal(self, signal: str) -> None:
        await self._signal_queue.put(signal)

    async def _run_signal_handler(self, signal: str) -> None:
        handler = self._signal_handlers.get(signal)
        if not handler:  # pragma: no cover
            self.logger.warning(f"No handler registered for signal '{signal}'")
            return
        self.logger.debug(f"Running handler for signal '{signal}'")
        if iscoroutinefunction(handler):
            await handler()
        else:
            await sync_to_async(handler)()

    def on_signal(self, signal: str) -> Callable[[Handler], Handler]:
        """Decorator to register a function to be called when a signal is received.

        Args:
            signal: The signal name
            handler: A callable or coroutine function with no parameters

        Returns:
            The original handler function

        Raises:
            ValueError: If handler is not callable
        """

        def decorator(handler: Handler) -> Handler:
            if not iscoroutinefunction(handler) and not callable(handler):
                raise ValueError("Handler must be a coroutine or a callable")
            self._signal_handlers[signal] = handler
            return handler

        return decorator
