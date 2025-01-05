# Example 02: Hello, Signals

If you've tried the previous example (01-hello-agent),
run `cd ..` to change back to examples directory.

Run the example:
    `cd 02-hello-signals`
    `python main.py`

## What's happening?

Here, we use the `@agent.on_start` hook to send a `signal` to the agent.

```python
@agent.on_start
def startup():
    agent.signal("greet")
```

A `signal` in zycelium triggers a signal handler defined within the same file.
Below, we define the `greet_the_world` function as a signal handler for a signal named `greet`.

Like last example, it prints "Hello, World!" and stops the agent.

```python
@agent.on_signal("greet")
def greet_the_world():
    print("Hello, World!")
    agent.stop()
```

Signals can be used within the agent to execute a function
without having to wait for it to return.

Zycelium uses Python's `asyncio` library and is fully asynchronous,
however, you may ignore that bit and write regular Python functions
instead of using `async def` and `await` if you're not yet familiar
with async/await.

Behind the scenes, zycelium will run the signal handler in a thread.

If you're not familiar with any of the terms used above, that's alright!
Keep following these examples/ tutorials,
look up interesting terms in a search engine
and you'll be up to speed in no time.

Or if you are fluent in Python, skim the READMEs in each example
and tinker with the examples more!
