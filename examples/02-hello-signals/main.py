from zycelium import Agent

agent = Agent()


@agent.on_start
def startup():
    agent.signal("greet")


@agent.on_signal("greet")
def greet_the_world():
    print("Hello, World!")
    agent.stop()


if __name__ == "__main__":
    agent.run()
