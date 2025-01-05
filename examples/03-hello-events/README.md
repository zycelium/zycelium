# Example 03: Hello, Events

Following along from previous example (02-hello-signals),
run `cd ..` to change back to examples directory.

Run the example:
    `cd 03-hello-events`
    `python main.py`

## Requirements

This example onward, we'll need a local `nats-server` running.

> TODO: Add instructions to download and run nats-server.
> Workaround: <https://docs.nats.io/running-a-nats-service/introduction/installation>

## What's happening?

On the surface, not much is different.
However, you will notice three lines of code that are not the same as last example.

Let's start at the bottom this time.

```python
agent.run("nats://localhost:4222")
```

We're specifying a uri for a local `NATS` server.
If you run this example and don't have a nats-server running yet,
the agent will appear to do nothing,
however it will warn in the logs about not being able to connect to the given uri.

Once you run `nats-server`, the agent will connect and run as expected,
print "Hello, World!" and then exit.

Looking at rest of the code, we find that instead of `signal`, we are using `event`.
As we've seen before, signals are limited to the agent, however,
events that an agent `emit()`s are broadcast to all agents connected
to the specified NATS server.

Here's how we define an event handler:

```python
@agent.on_event("greet")
```

And how we emit a signal that's broadcast to any agent that has an event handler
defined for that specific event.

```python
agent.emit("greet")
```

If you have more than one agent that handles the same event,
they will all respond to it however they are programmed,
if any agent emits that event.

Events are not limited to a simple name, but are tied to `subject` from NATS.
Read more on subjects: <https://docs.nats.io/nats-concepts/subjects>
