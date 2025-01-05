from zycelium import Agent

agent = Agent()


@agent.on_start
async def startup():
    await agent.signal("greet")


@agent.on_signal("greet")
async def greet_the_world():
    print("Hello, World!")
    await agent.stop()


if __name__ == "__main__":
    agent.run()
