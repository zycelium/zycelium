from dataclasses import dataclass
from zycelium import Agent


@dataclass
class State:
    counter: int = 0


agent = Agent()
agent.state = State()


@agent.on_start
def startup():
    agent.state.counter += 1
    print(f"Counter: {agent.state.counter}")
    agent.stop()


agent.run()
