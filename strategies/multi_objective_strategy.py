from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
  from agent import Agent

import random
import math
from .strategy import Strategy


class MultiObjectiveStrategy(Strategy):
  """
  """

  def __init__(self, alpha=0.5) -> None:
    super().__init__()
    self.alpha = alpha

  def get_strategy_name(self):
    if self.alpha == 0:
      return 'multi_objective_zero'
    return 'multi_objective_' + str(self.alpha)

  def initialize_strategy(self, agent: Agent):
    super().initialize_strategy(agent)

    # Planned edges and nodes are shuffled to make the strategy random
    self.plan_edges = self.agent.plan['edges'].copy()
    self.plan_nodes = self.agent.plan['nodes'].copy()

    ordered_nodes = self.agent.graph.get_nodes_ordered_by_rank(self.agent.group)
    order_dict = dict(ordered_nodes)
    self.plan_nodes.sort(key=lambda x: order_dict[x], reverse=True)

    random.shuffle(self.plan_edges)

    print("agent.group", agent.group)

    # Past nodes and edges are used to avoid planning edges that were already proposed
    # in the past, and to check which edges can be proposed
    self.past_nodes = set()
    self.past_edges = set()

    # Edges from plan_nodes that are belonging to nodes that are existing
    # This is just for speeding up things
    self.plan_edges_between_existing_nodes = []
    self.update_plan_edges_between_existing_nodes()

    # Calculate cost-effectiveness ratio for each node and sort them
    self.plan_nodes_cost_effective = self.calculate_cost_effectiveness(self.plan_nodes, agent)

  def calculate_cost_effectiveness(self, nodes, agent):
    cost_effectiveness = []
    for node in nodes:
      score = agent.graph.get_node_ranking(node)
      cost = agent.cost_insert_node(score)
      cost = (cost - 1) / (math.e - 1)
      ratio = (self.alpha * cost) - ((1 - self.alpha) * score)
      cost_effectiveness.append((node, ratio))

    cost_effectiveness.sort(key=lambda x: x[1])
    return [x[0] for x in cost_effectiveness]

  def update_plan_edges_between_existing_nodes(self):
    currently_active_nodes_ids = set(
        self.agent.graph.get_nodes_with_group(
            self.agent.group, active=True))
    currently_active_nodes_ids.update(self.past_nodes)
    self.plan_edges_between_existing_nodes = [
        (s, d) for (s, d) in self.plan_edges
        if s in currently_active_nodes_ids and d in currently_active_nodes_ids
    ]

  def step(self):
    super().step()

    # trying to add edges (we search through the past nodes just in case we already
    # proposed an edge or node that was not committed yet)
    # for e in self.plan_edges_between_existing_nodes:
    if len(self.plan_edges_between_existing_nodes) > 0:
      e = random.choice(self.plan_edges_between_existing_nodes)
      self.past_edges.add(e)
      self.plan_edges.remove(e)
      self.plan_edges_between_existing_nodes.remove(e)
      return {'nodes': [], 'edges': [e]}

    # Add node based on cost-effectiveness
    if len(self.plan_nodes_cost_effective) > 0:
      n = self.plan_nodes_cost_effective.pop(0)
      self.past_nodes.add(n)
      return {'nodes': [n], 'edges': []}

    return None
