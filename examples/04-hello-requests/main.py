from zycelium import Agent

agent = Agent()


@agent.on_start
def startup():
    response = agent.request("greet", name="World")
    print(response["greeting"])
    agent.stop()


@agent.on_request("greet")
def greet(name):
    return {"greeting": f"Hello, {name}!"}


if __name__ == "__main__":
    agent.run("nats://localhost:4222")
