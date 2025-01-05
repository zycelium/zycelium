# Example 04: Hello, Requests

Following from the previous example (03-hello-events),
run `cd ..` to change back to examples directory.

Run the example:
    `cd 04-hello-requests`
    `python main.py`

## Requirements

As with the previous example, you'll need a local `nats-server` running.

## What's happening?

This example demonstrates request-response pattern using agents.
Let's look at the important bits:

Here we define a request handler, which processes the request and returns a response:

```python
@agent.on_request("greet")
def greet(name):
    return {"greeting": f"Hello, {name}!"}
```

And here we make a request and use the response:

```python
@agent.on_start
def startup():
    response = agent.request("greet", name="World")
    print(response["greeting"])
    agent.stop()
```

The request handler returns a dictionary, which becomes available as the response
in the calling function. Arguments passed to `request()` become available as
parameters in the request handler function.

Unlike events which are broadcast, requests expect one response - the first agent to respond wins.
If no agent handles the request, it will raise a timeout error.

Unlike signals which are local to an agent, requests can be handled by any agent
connected to the NATS server.
