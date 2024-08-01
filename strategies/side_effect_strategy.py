from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
  from agent import Agent

import random
from .strategy import Strategy


class SideEffectStrategy(Strategy):
  """
    This stategy run the specified strategy, and run a given function at each step which can perform
    an arbitraty code that can create side-effect in the graph.
  """

  def __init__(self, strategy_to_run: Strategy, side_effect_function: function) -> None:
    self.strategy_to_run = strategy_to_run
    self.side_effect_function = side_effect_function
    super().__init__()

  def get_strategy_name(self):
    return f'se({self.strategy_to_run.get_strategy_name()})'

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

    res = self.strategy_to_run.step()

    self.side_effect_function(self.agent)

    return res
