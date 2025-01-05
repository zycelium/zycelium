"""
Zycelium Agent.
"""

import asyncio
import signal
from asyncio import TimeoutError
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
        self._loop = None  # type: asyncio.AbstractEventLoop
        logger_name = f"zycelium.agent.{self.name}" if self.name else "zycelium.agent"
        self.logger = get_logger(logger_name, level=log_level)
        self.logger.info("Initializing")
        self._shutdown_trigger: asyncio.Event = asyncio.Event()
        self._start_handler: Optional[Handler] = None
        self._stop_handler: Optional[Handler] = None
        self._signal_handlers: dict[str, Handler] = {}
        self._signal_queue: asyncio.Queue = asyncio.Queue()
        self._signal_processor_task: Optional[asyncio.Task] = None
        self._tasks: set[asyncio.Task] = set()

    # Agent Lifecycle

    def run(self, handle_os_signals=True) -> None:
        """Start the agent and run until stopped.

        Can be called either synchronously or asynchronously.
        """
        asyncio.run(self._run(handle_os_signals=handle_os_signals))

    @awaitable(run)
    async def run(self, handle_os_signals=True) -> None:
        await self._run(handle_os_signals=handle_os_signals)

    def _setup_signal_handlers(self) -> None:
        """Set up handlers for OS signals."""
        self.logger.debug("Setting up OS signal handlers")
        try:
            for sig in (signal.SIGTERM, signal.SIGINT):
                self._loop.add_signal_handler(sig, self._stop)
        except NotImplementedError:  # pragma: no cover
            # Windows doesn't support add_signal_handler
            self.logger.warning("OS signal handlers not supported on this platform")

    async def _run(self, handle_os_signals: bool) -> None:
        self.logger.info("Starting up")
        self._loop = asyncio.get_event_loop()
        if handle_os_signals:  # pragma: no cover
            self._setup_signal_handlers()
        self._signal_processor_task = asyncio.create_task(
            self._process_signals(), name="signal_processor"
        )
        self.register_task(self._signal_processor_task)
        await self._run_start_handler()
        await self._shutdown_trigger.wait()
        self.logger.info("Shutting down")
        await self._run_stop_handler()
        await self.cancel_tasks()

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
        """Trigger agent shutdown."""
        self.logger.info("Stop signal received")
        self._shutdown_trigger.set()

    def register_task(self, task: asyncio.Task) -> None:
        """Register an asyncio task with the agent for lifecycle management."""
        self.logger.debug(f"Registering task {task.get_name()}")
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def cancel_tasks(self) -> None:
        """Cancel all registered tasks gracefully."""
        if not self._tasks:  # pragma: no cover
            return

        self.logger.info(f"Cancelling {len(self._tasks)} tasks")
        for task in self._tasks:
            if not task.done():  # pragma: no cover
                self.logger.debug(f"Cancelling task {task.get_name()}")
                task.cancel()

        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()

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
        timeout = getattr(handler, "__signal_timeout__", 10)

        try:
            if iscoroutinefunction(handler):
                await asyncio.wait_for(handler(), timeout=timeout)
            else:
                await asyncio.wait_for(sync_to_async(handler)(), timeout=timeout)
        except TimeoutError:  # pragma: no cover
            self.logger.error(
                f"Signal handler for '{signal}' timed out after {timeout} seconds"
            )
        except Exception as e:  # pragma: no cover
            self.logger.error(f"Signal handler for '{signal}' failed: {str(e)}")

    def on_signal(self, signal: str, timeout=10) -> Callable[[Handler], Handler]:
        """Decorator to register a function to be called when a signal is received.

        Args:
            signal: The signal name
            handler: A callable or coroutine function with no parameters
            timeout: The maximum time in seconds to wait
                     for the signal handler to complete

        Returns:
            The original handler function

        Raises:
            ValueError: If handler is not callable
        """

        def decorator(handler: Handler) -> Handler:
            if not iscoroutinefunction(handler) and not callable(handler):
                raise ValueError("Handler must be a coroutine or a callable")
            setattr(handler, "__signal_name__", signal)
            setattr(handler, "__signal_timeout__", timeout)
            self._signal_handlers[signal] = handler
            return handler

        return decorator
