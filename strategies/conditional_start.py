from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
  from agent import Agent

import random
from .strategy import Strategy


class ConditionalStartStrategy(Strategy):
  """
    This strategy waits until a specific condition is met, then it runs the strategy_to_run.
    The difference between this and the conditional attack is that once this starts then it
    will not stop even if the condition is false again.
  """

  def __init__(self, strategy_to_run: Strategy, condition: function) -> None:
    self.strategy_to_run = strategy_to_run
    self.condition = condition
    super().__init__()

  def get_strategy_name(self):
    return f'cond_start({self.strategy_to_run.get_strategy_name()})'

  def initialize_strategy(self, agent: Agent):
    super().initialize_strategy(agent)
    self.start = False
    self.strategy_to_run.initialize_strategy(agent)

    # Planned edges and nodes are shuffled to make the strategy random
    self.plan_edges = self.agent.plan['edges'].copy()
    self.plan_nodes = self.agent.plan['nodes'].copy()
    random.shuffle(self.plan_nodes)
    random.shuffle(self.plan_edges)

  def step(self):
    super().step()

    if len(self.plan_nodes) == 0 and len(self.plan_edges) == 0:
      return None

    if not self.start and self.condition(self.agent):
      self.start = True

    if self.start:
      return self.strategy_to_run.step()
    else:
      return {'nodes': [-1], 'edges': []}  # pass
