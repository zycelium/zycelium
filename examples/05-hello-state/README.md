# Example 05: Hello, State

If you've tried the previous examples, run `cd ..` to change back to examples directory.

Run the example:
    `cd 05-hello-state`
    `python main.py`

Run it multiple times to see the counter increment across restarts.

## What's happening?

Zycelium agents can maintain persistent state that survives crashes and restarts.
The state is automatically saved to disk whenever it changes.

First, we define what our state looks like using a dataclass:

```python
@dataclass
class State:
    counter: int = 0
```

Then we create an agent and initialize its state:

```python
agent = Agent()
agent.state = State()
```

When the agent starts up, we increment the counter and print it:

```python
@agent.on_start
def startup():
    agent.state.counter += 1
    print(f"Counter: {agent.state.counter}")
    agent.stop()
```

Every time you run the program, the counter will increment, even though the agent stops and starts. This is because the state is automatically saved to a JSON file on disk.

## Making Atomic State Changes

For more complex state changes, you should use the `state_transaction` context manager to ensure changes are atomic:

```python
with agent.state_transaction() as state:
    state.counter += 1
    state.last_update = "2023-01-01"
```

This ensures that either all state changes are saved, or none of them are, preventing partial updates that could corrupt your state.

Note: The example code doesn't use transactions since it's making a single simple change, but it's a good practice to use them when making multiple related state changes.
