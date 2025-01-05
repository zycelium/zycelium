from zycelium import Agent

agent = Agent()


@agent.on_start
def startup():
    agent.emit("greet")


@agent.on_event("greet")
def greet_the_world():
    print("Hello, World!")
    agent.stop()


if __name__ == "__main__":
    agent.run("nats://localhost:4222")
