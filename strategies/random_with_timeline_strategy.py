from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
  from agent import Agent

import random
from .strategy import RandomStrategy


class RandomStrategyWithTimeline(RandomStrategy):

  def __init__(self) -> None:
    super().__init__()

  def get_strategy_name(self):
    return 'rnd'
