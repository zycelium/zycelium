from zycelium import Agent

agent = Agent()


@agent.on_start
def startup():
    print("Hello, World!")
    agent.stop()


agent.run()
