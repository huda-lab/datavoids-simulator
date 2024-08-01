from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
  from agent import Agent

import random
from .strategy import Strategy


class ConditionalAttackStrategy(Strategy):
  """
    This strategy waits until a specific condition is met, then it runs the strategy_to_run.
    The strategy keeps checking the condition, if this becomes false again it will stop
    the attack.
  """

  def __init__(self, strategy_to_run: Strategy, condition: function) -> None:
    self.strategy_to_run = strategy_to_run
    self.condition = condition
    super().__init__()

  def get_strategy_name(self):
    return f'cond_attack({self.strategy_to_run.get_strategy_name()})'

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

    if len(self.plan_nodes) == 0 and len(self.plan_edges) == 0:
      return None

    if self.condition(self.agent):
      return self.strategy_to_run.step()

    return {'nodes': [-1], 'edges': []}  # pass
