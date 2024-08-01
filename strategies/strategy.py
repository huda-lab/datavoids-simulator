from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
  from agent import Agent


class Strategy:
  """
  focus_node is a node that the strategy will try to expand. If None, it will try to gravitate around.
  In case of neighborhood expansion, it will try to expand the neighborhood of this node.

  datavoid is the datavoid that the strategy is going to try to optimize for. For example instead
  of randomly choosing, choosing the nodes that contain these datavoids.
  """

  def __init__(self, focus_node=None) -> None:
    self.focus_node = focus_node
    self.initialized = False

  def initialize_strategy(self, agent: Agent):
    """
    Initializes the strategy. This method is called before the first step.
    """
    self.agent = agent
    self.initialized = True

  def get_strategy_name(self):
    return ''

  def step(self):
    """
    Returns a dictionary with the following structure:
    {
      'nodes': [node_id, node_id, ...],
      'edges': [(node_id, node_id), (node_id, node_id), ...]
    }

    If the strategy is not initialized, it will raise an exception.

    If the strategy is initialized but there is nothing to do, it will return None.
    """

    if not self.initialized:
      raise Exception("Strategy not initialized")

    return None
