from zycelium import Agent

agent = Agent()


@agent.on_start
async def startup():
    await agent.emit("greet")


@agent.on_event("greet")
async def greet_the_world():
    print("Hello, World!")
    await agent.stop()


if __name__ == "__main__":
    agent.run("nats://localhost:4222")
