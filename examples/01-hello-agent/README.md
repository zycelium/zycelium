# Example 01: Hello, Agent

Minimal example using Agent's `on_start` hook.
Prints "Hello, World!" to the console and exits.

In terminal, enter the project directory:
    `cd zycelium`

Install the project dependencies and activate the virtual environment:
    `poetry install`
    `poetry shell`

Run the example:
    `cd examples/01-hello-agent`
    `python main.py`

## What's happening?

Let's first look at the full example:

```python
from zycelium import Agent


agent = Agent()


@agent.on_start
def startup():
    print("Hello, World!")
    agent.stop()


agent.run()
```

Now let's explore at it line-by-line.

First line imports `Agent` class from `zycelium` package.

```python
from zycelium import Agent
```

In the next line of code, we create an instance  of the Agent class.

```python
agent = Agent()
```

In later examples we will look at configuring the agent to connect
to the zycelium network, but for now, just this line is enough.

Then, we use the decorator pattern in Python to define a function
that will be called when the agent starts.

```python
@agent.on_start
```

The decorator above registers the following function to run
every time the agent is run:

```python
def startup():
    print("Hello, World!")
    agent.stop()
```

Finally, we run the agent:

```python
agent.run()
```

Once the agent has initialized, it will call the on_start hook we defined earlier,
which will print the canonical example greeting "Hello, World!" to the terminal
and stop the agent, as there is nothing else to do in this example.

If we delete the line `agent.stop()`, the agent will keep running,
but won't do anything else until we press `Control+C` to stop the program.

Try using the decorator `@agent.on_stop`to define another function,
you could call it `shutdown`, which prints `"See you later!"`
when the agent stops.

Next, try deleting or commenting out `agent.stop()` like below,
run the program again and press `Control+C`
when you get sufficiently bored of looking at the first greeting.

```python
def startup():
    print("Hello, World!")
    # agent.stop()
```

And that's it for this example/ tutorial!
