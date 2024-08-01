from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
  from agent import Agent

from .strategy import Strategy


class PassStrategy(Strategy):
  """
    This strategy always pass.
    Mainly used for debugging and when we want only one side to play.
  """

  def __init__(self) -> None:
    super().__init__()

  def get_strategy_name(self):
    return 'pass'

  def initialize_strategy(self, agent: Agent):
    super().initialize_strategy(agent)

    # Planned edges and nodes are shuffled to make the strategy random
    self.plan_nodes = self.agent.plan['nodes'].copy()

  def step(self):
    super().step()

    if len(self.plan_nodes) > 0:
      self.plan_nodes.pop(0)
      return {'nodes': [-1], 'edges': []}  # pass

    return None  # end
