from zycelium import Agent

agent = Agent()


@agent.on_start
async def startup():
    response = await agent.request("greet", name="World")
    print(response["greeting"])
    await agent.stop()


@agent.on_request("greet")
async def greet(name):
    return {"greeting": f"Hello, {name}!"}


if __name__ == "__main__":
    agent.run("nats://localhost:4222")
