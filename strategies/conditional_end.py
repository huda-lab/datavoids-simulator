from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
  from agent import Agent

from .strategy import Strategy


class ConditionalEndStrategy(Strategy):
  """
    This strategy end if a condition is met, otherwise it runs the strategy_to_run.
    When the strategy end it returns None to signal that there are no more moves to do.
  """

  def __init__(self, strategy_to_run: Strategy, condition: function) -> None:
    self.strategy_to_run = strategy_to_run
    self.condition = condition
    super().__init__()

  def get_strategy_name(self):
    return f'cond_end({self.strategy_to_run.get_strategy_name()})'

  def initialize_strategy(self, agent: Agent):
    self.end = False
    super().initialize_strategy(agent)
    self.strategy_to_run.initialize_strategy(agent)

  def step(self):
    super().step()

    if self.end or self.condition(self.agent):
      self.end = True  # Just to make sure if this strategy is called again and
      # the condition is not true anymore
      return None

    return self.strategy_to_run.step()
