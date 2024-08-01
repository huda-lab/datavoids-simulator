from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
  from agent import Agent

import random
from .strategy import Strategy


class DelayedStartStrategy(Strategy):
  """
    This strategy waits until a specific moment to run strategy_to_run.
  """

  def __init__(self, strategy_to_run: Strategy, delay: int) -> None:
    self.strategy_to_run = strategy_to_run
    self.delay = delay
    super().__init__()

  def get_strategy_name(self):
    return f'delay_start({self.strategy_to_run.get_strategy_name()})'

  def initialize_strategy(self, agent: Agent):
    super().initialize_strategy(agent)
    self.strategy_to_run.initialize_strategy(agent)

    # Planned edges and nodes are shuffled to make the strategy random
    self.plan_edges = self.agent.plan['edges'].copy()
    self.plan_nodes = self.agent.plan['nodes'].copy()
    random.shuffle(self.plan_nodes)
    random.shuffle(self.plan_edges)

  def step(self):
    super().step()

    if self.agent.steps_count > self.delay:
      if len(self.plan_nodes) == 0 and len(self.plan_edges) == 0:
        return None  # end

      return self.strategy_to_run.step()  # give back some node for the next step

    return {'nodes': [-1], 'edges': []}  # pass
