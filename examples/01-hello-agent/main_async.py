from zycelium import Agent

agent = Agent()


@agent.on_start
async def startup():
    print("Hello, World!")
    await agent.stop()


agent.run()
