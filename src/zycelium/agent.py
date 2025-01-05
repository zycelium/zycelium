"""
Zycelium Agent.
"""

import asyncio
import json
import signal
from asyncio import TimeoutError
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeoutError
from contextlib import contextmanager
from dataclasses import asdict
from inspect import iscoroutinefunction
from typing import Any, Awaitable, Callable, Optional, TypeAlias, Union
from uuid import uuid4

from asgiref.sync import sync_to_async
from asyncgnostic import awaitable

from zycelium.logging import get_logger
from zycelium.transport import NatsTransport

OPERATION_TIMEOUT = 5  # seconds

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
        log_level: str = "WARNING",
    ) -> None:
        logger_name = f"zycelium.agent.{name}" if name else "zycelium.agent"
        self.logger = get_logger(logger_name, level=log_level)
        self.logger.info("Initializing")

        self.name = name or ""
        self.uuid = uuid or uuid4().hex
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._shutdown_trigger: asyncio.Event = asyncio.Event()
        self._start_handler: Optional[Handler] = None
        self._stop_handler: Optional[Handler] = None
        self._signal_handlers: dict[str, Handler] = {}
        self._signal_queue: asyncio.Queue = asyncio.Queue()
        self._signal_processor_task: Optional[asyncio.Task] = None
        self._tasks: set[asyncio.Task] = set()
        self._event_handlers = {}
        self._subscriptions = set()
        self._transport = NatsTransport(log_level)
        self._event_queue: asyncio.Queue = asyncio.Queue()
        self._event_processor_task: Optional[asyncio.Task] = None
        self._request_handlers = {}  # Add request handlers dict
        self._request_queue: asyncio.Queue = asyncio.Queue()
        self._request_processor_task: Optional[asyncio.Task] = None
        self._thread_pool = ThreadPoolExecutor(max_workers=10)
        self._state: Optional[Any] = None
        self._state_path: Optional[str] = (
            f"{self.name}-state.json" if self.name else "agent-state.json"
        )

    # Agent Lifecycle

    def run(
        self,
        nats_uri: Optional[str] = None,
        nats_token: Optional[str] = None,
        handle_os_signals=True,
    ) -> None:
        """Start the agent and run until stopped.

        Can be called either synchronously or asynchronously.
        """
        asyncio.run(
            self._run(
                nats_uri=nats_uri,
                nats_token=nats_token,
                handle_os_signals=handle_os_signals,
            )
        )

    @awaitable(run)
    async def run(
        self,
        nats_uri: Optional[str] = None,
        nats_token: Optional[str] = None,
        handle_os_signals=True,
    ) -> None:
        await self._run(
            nats_uri=nats_uri,
            nats_token=nats_token,
            handle_os_signals=handle_os_signals,
        )

    def _setup_signal_handlers(self) -> None:
        """Set up handlers for OS signals."""
        self.logger.debug("Setting up OS signal handlers")
        try:
            for sig in (signal.SIGTERM, signal.SIGINT):
                self._loop.add_signal_handler(sig, self._stop)
        except NotImplementedError:  # pragma: no cover
            # Windows doesn't support add_signal_handler
            self.logger.warning("OS signal handlers not supported on this platform")

    async def _setup_subscriptions(self) -> None:
        """Subscribe to all registered event handlers."""
        self.logger.debug("Setting up event subscriptions")
        for subject in self._event_handlers:
            try:
                await self._transport.subscribe(subject, self._handle_event)
                self._subscriptions.add(subject)
                self.logger.debug(f"Subscribed to event: {subject}")
            except Exception as e:  # pragma: no cover
                self.logger.error(f"Failed to subscribe to {subject}: {e}")

    async def _cleanup_subscriptions(self) -> None:
        """Cleanup all event subscriptions."""
        if not self._subscriptions:
            return

        self.logger.debug("Cleaning up event subscriptions")
        # Create a copy of subscriptions since we'll modify the set while iterating
        for subject in list(self._subscriptions):
            try:
                if self._transport.connected:
                    await self._transport.unsubscribe(subject)
                    self.logger.debug(f"Unsubscribed from event: {subject}")
                else:  # pragma: no cover
                    # If transport is disconnected, just remove from tracking
                    self._subscriptions.remove(subject)
                    self.logger.debug(f"Removed subscription tracking for: {subject}")
            except Exception as e:  # pragma: no cover
                self.logger.error(f"Error unsubscribing from {subject}: {e}")
                # Still remove from tracking even if unsubscribe fails
                self._subscriptions.discard(subject)
        self._subscriptions.clear()

    async def _setup_request_subscriptions(self) -> None:
        """Subscribe to all registered request handlers."""
        self.logger.debug("Setting up request subscriptions")
        for subject in self._request_handlers:
            try:
                await self._transport.subscribe(subject, self._handle_request)
                self.logger.debug(f"Subscribed to request subject: {subject}")
            except Exception as e:  # pragma: no cover
                self.logger.error(f"Failed to subscribe to request {subject}: {e}")

    async def _run(
        self,
        nats_uri: Optional[str] = None,
        nats_token: Optional[str] = None,
        handle_os_signals=True,
    ) -> None:
        self.logger.info("Starting up")
        self._loop = asyncio.get_event_loop()
        if handle_os_signals:  # pragma: no cover
            self._setup_signal_handlers()

        # Start signal and event processors
        self._signal_processor_task = asyncio.create_task(
            self._process_signals(), name="signal_processor"
        )
        self._event_processor_task = asyncio.create_task(
            self._process_events(), name="event_processor"
        )
        self.register_task(self._signal_processor_task)
        self.register_task(self._event_processor_task)

        # Add request processor task
        self._request_processor_task = asyncio.create_task(
            self._process_requests(), name="request_processor"
        )
        self.register_task(self._request_processor_task)

        if nats_uri:
            await self._transport.connect(nats_uri, nats_token)
            if self._transport.connected:
                await self._setup_subscriptions()
                await self._setup_request_subscriptions()
            else:  # pragma: no cover
                pass
        await self._run_start_handler()
        await self._shutdown_trigger.wait()
        self.logger.info("Shutting down")
        await self._run_stop_handler()
        await self._cleanup_subscriptions()
        if self._transport.connected:
            if self._transport.is_draining:  # pragma: no cover
                self.logger.info("Processing pending events, please wait...")
            await self._transport.drain()
        await self._transport.disconnect()
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
            timeout: The maximum time in seconds to waselfit
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

    # Events

    async def _handle_event(self, msg) -> None:
        """Handle incoming event message."""
        try:
            subject = msg.subject
            data = json.loads(msg.data.decode())
            handler = self._event_handlers.get(subject)
            if handler:
                await handler(**data)
            else:  # pragma: no cover
                pass
        except Exception as e:  # pragma: no cover
            self.logger.error(f"Error handling event: {e}")

    def on_event(self, subject: str) -> Callable:
        """Decorator to register an event handler."""

        def decorator(handler: Handler) -> Handler:
            if not iscoroutinefunction(handler) and not callable(handler):
                raise ValueError("Handler must be a coroutine or a callable")

            # Wrap sync handler in async wrapper
            if not iscoroutinefunction(handler):
                wrapped = sync_to_async(handler)
            else:
                wrapped = handler

            self._event_handlers[subject] = wrapped
            return handler

        return decorator

    async def _process_events(self) -> None:
        """Process queued events."""
        self.logger.debug("Starting event processor")
        while True:
            subject, kwargs = await self._event_queue.get()
            self.logger.debug(f"Processing event '{subject}'")
            try:
                data = json.dumps(kwargs).encode()
                await self._transport.publish(subject, data)
            except Exception as e:  # pragma: no cover
                self.logger.error(f"Error emitting event {subject}: {e}")
            self._event_queue.task_done()

    def emit(self, subject: str, **kwargs) -> None:
        """Queue an event for emission (threadsafe).

        Args:
            subject: The event subject
            **kwargs: Event data
        """
        self.logger.debug(f"Queueing event '{subject}'")
        self._loop.call_soon_threadsafe(self._event_queue.put_nowait, (subject, kwargs))

    @awaitable(emit)
    async def emit(self, subject: str, **kwargs) -> None:
        """Queue an event for emission."""
        await self._event_queue.put((subject, kwargs))

    # Requests

    async def _handle_request(self, msg) -> None:
        """Handle incoming request message."""
        try:
            subject = msg.subject
            data = json.loads(msg.data.decode())
            handler = self._request_handlers.get(subject)
            if handler:
                try:
                    result = await handler(**data)
                    response = json.dumps(result).encode()
                    await msg.respond(response)
                except Exception as e:
                    self.logger.error(f"Error in request handler: {e}")
                    await msg.respond(b"null")  # Send null response on error
            else:  # pragma: no cover
                await msg.respond(b"null")  # No handler found
        except Exception as e:  # pragma: no cover
            self.logger.error(f"Error handling request: {e}")
            await msg.respond(b"null")

    def on_request(self, subject: str) -> Callable:
        """Decorator to register a request handler.

        Args:
            subject: The request subject

        Returns:
            Decorator function

        Example:
            @agent.on_request("greet")
            async def handle_greet(name: str):
                return {"greeting": f"Hello {name}!"}
        """

        def decorator(handler: Handler) -> Handler:
            if not iscoroutinefunction(handler) and not callable(handler):
                raise ValueError("Handler must be a coroutine or a callable")

            # Wrap sync handler to run in thread pool
            if not iscoroutinefunction(handler):

                async def thread_handler(**kwargs):
                    loop = asyncio.get_running_loop()
                    return await loop.run_in_executor(
                        self._thread_pool, lambda: handler(**kwargs)
                    )

                wrapped = thread_handler
            else:
                wrapped = handler

            self._request_handlers[subject] = wrapped
            return handler

        return decorator

    def request(
        self, subject: str, timeout: float = OPERATION_TIMEOUT, **kwargs
    ) -> Optional[dict]:
        """Send a request and wait for response (synchronously)."""
        if not self._loop or self._loop.is_closed():  # pragma: no cover
            self.logger.error("No active event loop available for sync request")
            return None
        data = json.dumps(kwargs).encode()

        # Run in the existing event loop
        future = asyncio.run_coroutine_threadsafe(
            self._async_request(subject, data), self._loop
        )
        try:
            response = future.result(timeout=timeout)
            return json.loads(response.decode()) if response else None
        except FuturesTimeoutError:
            self.logger.error(f"Request to {subject} timed out")
            return None
        except Exception as e:  # pragma: no cover
            self.logger.error(f"Error making sync request to {subject}: {e}")
            return None

    @awaitable(request)
    async def request(
        self, subject: str, timeout: float = OPERATION_TIMEOUT, **kwargs
    ) -> Optional[dict]:
        """Send a request and wait for response (asynchronously)."""
        data = json.dumps(kwargs).encode()
        try:
            response = await asyncio.wait_for(
                self._transport.request(subject, data), timeout=timeout
            )
            return json.loads(response.data.decode()) if response else None
        except asyncio.TimeoutError:  # pragma: no cover
            self.logger.error(f"Request to {subject} timed out")
            return None
        except Exception as e:  # pragma: no cover
            self.logger.error(f"Error making async request to {subject}: {e}")
            return None

    async def _async_request(self, subject: str, data: bytes) -> Optional[bytes]:
        """Helper for sync request to await transport call."""
        response = await self._transport.request(subject, data)
        return response.data if response else None

    async def _process_requests(self) -> None:
        """Process incoming requests."""
        self.logger.debug("Starting request processor")
        while True:  # pragma: no cover
            subject, kwargs = await self._request_queue.get()
            self.logger.debug(f"Processing request '{subject}'")
            try:
                handler = self._request_handlers.get(subject)
                if handler:
                    await handler(**kwargs)
            except Exception as e:
                self.logger.error(f"Error processing request {subject}: {e}")
                self._request_queue.task_done()

    # Persistent state
    @property
    def state(self):
        """Get the current state wrapped in a proxy that auto-saves on modifications."""
        if self._state is None:
            raise RuntimeError("agent.state is not initialized")
        return StateProxy(self._state, self._save_state)

    @state.setter
    def state(self, value):
        """Set the state value, preserving existing state if available."""
        if self._state is None:  # First time state is being set
            try:
                with open(self._state_path, "r") as f:
                    data = json.load(f)
                    self._state = value.__class__(**data)
                    self.logger.debug(f"Loaded existing state from {self._state_path}")
            except FileNotFoundError:
                self._state = value
                self.logger.debug(f"No existing state, using new state")
            except json.JSONDecodeError:
                self.logger.error(f"Error loading state, using new state")
                self._state = value
        else:  # Subsequent state updates
            self._state = value
        self._save_state()

    @contextmanager
    def state_transaction(self):
        """Context manager for atomic state modifications."""
        if self._state is None:
            raise RuntimeError("agent.state is not initialized")
        yield self._state
        self._save_state()

    def _load_state(self):
        if self._state_path is None or self._state is None:
            return
        try:
            with open(self._state_path, "r") as f:
                data = json.load(f)
                self._state = self._state.__class__(**data)
                self.logger.debug(f"Loaded state from {self._state_path}")
                return self._state
        except FileNotFoundError:
            self.logger.debug(f"State file not found: {self._state_path}")
        except json.JSONDecodeError:
            self.logger.error(f"Error loading state from {self._state_path}")

    def _save_state(self):
        if self._state_path is None:
            return
        try:
            with open(self._state_path, "w") as f:
                json.dump(asdict(self._state), f)
        except (json.JSONDecodeError, TypeError) as e:
            self.logger.error(f"Error saving state to {self._state_path}: {e}")


class StateProxy:
    """Proxy that wraps state object and calls save_callback on modifications."""

    def __init__(self, state: Any, save_callback: Callable):
        self._state = state
        self._save_callback = save_callback

    def __getattr__(self, name):
        attr = getattr(self._state, name)
        if callable(attr):
            # If it's a method, wrap it to detect modifications
            def wrapped(*args, **kwargs):
                result = attr(*args, **kwargs)
                self._save_callback()
                return result

            return wrapped
        return attr

    def __setattr__(self, name, value):
        if name in ("_state", "_save_callback"):
            super().__setattr__(name, value)
            return
        setattr(self._state, name, value)
        self._save_callback()
