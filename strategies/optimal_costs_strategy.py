from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
  from agent import Agent

import random
import math
import numpy as np
from scipy.optimize import linprog
import gurobipy as gp
from gurobipy import GRB

from .strategy import Strategy

MACHINE_EPSILON = 1e-8


class OptimalCostsStrategy(Strategy):
  """
  Using Gurobi, this finds the cheapest set of pages which can overcome the opponent
  """

  def __init__(self) -> None:
    super().__init__()
    self.max_steps = None

  def get_strategy_name(self):
    return 'optc'

  def initialize_strategy(self, agent: Agent):
    super().initialize_strategy(agent)

    # Past nodes and edges are used to avoid planning edges that were already proposed
    # in the past, and to check which edges can be proposed
    self.past_nodes = set()
    self.past_edges = set()

    # Planned edges and nodes are shuffled to make the strategy random
    self.plan_edges = self.agent.plan['edges'].copy()
    self.plan_nodes = self.agent.plan['nodes'].copy()

    self.priority_nodes = []

    # Edges from plan_nodes that are belonging to nodes that are existing
    # This is just for speeding up things
    self.plan_edges_between_existing_nodes = []
    self.update_plan_edges_between_existing_nodes()

  def set_priority_nodes(self):
    if len(self.plan_nodes) == 1:
      self.priority_nodes = self.plan_nodes
      self.plan_nodes = []
      return

    # Prepare data of existing nodes
    refs = {}
    candidates_ids = []
    for node in self.plan_nodes:
      candidates_ids.append(node)
      score = self.agent.graph.get_node_ranking(node)
      cost = self.agent.cost_insert_node(score)
      cost = (cost - 1) / (math.e - 1)
      if not cost or np.isnan(cost) or np.isinf(cost):
        cost = 1
      refs[node] = {
        'id': node,
        'cost': cost,
        'score': score,
        'mask': 1,
        'active': False
      }
    for node in self.past_nodes:
      score = self.agent.graph.get_node_ranking(node)
      cost = self.agent.cost_insert_node(score)
      cost = (cost - 1) / (math.e - 1)
      if not cost or np.isnan(cost) or np.isinf(cost):
        cost = 1
      refs[node] = {
        'id': node,
        'cost': cost,
        'score': score,
        'mask': 1,
        'active': True
      }
    opponent_group = list(
        filter(
            lambda v: v != 'None' and v != self.agent.group,
            self.agent.config["target_groups"]))[0]
    opponent_nodes_with_score = self.agent.graph.get_nodes_ordered_by_rank(
      opponent_group, rank_field="searchrank", active=True)
    for node, score in opponent_nodes_with_score:
      cost = self.agent.cost_insert_node(score)
      cost = (cost - 1) / (math.e - 1)
      if not cost or np.isnan(cost) or np.isinf(cost):
        cost = 1
      refs[node] = {
        'id': node,
        'cost': cost,
        'score': score,
        'mask': -1,
        'active': True
      }

    initial_score_id_mask = [(refs[id]['score'], id, refs[id]['mask'])
                             for id in filter(lambda d: refs[d]['active'], refs)]
    initial_score_id_mask = sorted(initial_score_id_mask, reverse=True)
    candidate_score_id = [(refs[id]['score'], id) for id in candidates_ids]
    candidate_score_id = sorted(candidate_score_id, reverse=True)
    candidate_id_pos = []
    i = 0
    for score, id in candidate_score_id:
      while i < len(
        initial_score_id_mask) and score < initial_score_id_mask[i][0] + MACHINE_EPSILON:
        i += 1
      candidate_id_pos.append((id, i))

    # Heuristic solver
    # Computing - A
    rhs = 0
    for rank, (score, id, mask) in enumerate(initial_score_id_mask):
      rhs -= mask / (rank + 1)
    candidate_potential = []
    # Computing A_j for each j
    for id, pos in candidate_id_pos:
      potent = 1 / (pos + 1)  # initial of A_j
      for rank, (score, id, mask) in enumerate(initial_score_id_mask):
        if rank >= pos:
          potent += mask * (1 / (rank + 2) - 1 / (rank + 1))
      candidate_potential.append(potent)
    heu_model = gp.Model()
    heu_model.setParam('OutputFlag', 0)
    heu_model.setParam('TimeLimit', 10.0)
    heu_vars = [heu_model.addVar(vtype=GRB.BINARY, obj=refs[id]['cost'])
                for id, _ in candidate_id_pos]
    heu_expr = gp.LinExpr()
    heu_expr.addTerms(candidate_potential, heu_vars)
    heu_model.addConstr(heu_expr >= rhs)

    if self.max_steps:
      step_expr = gp.LinExpr()
      step_expr.addTerms([1.0 for i in range(len(candidate_id_pos))], heu_vars)
      heu_model.addConstr(step_expr <= self.max_steps)

    heu_model.optimize()
    self.priority_nodes = None
    if heu_model.Status == GRB.OPTIMAL or heu_model.Status == GRB.TIME_LIMIT:
      self.priority_nodes = []
      for idx, v in enumerate(heu_model.getVars()):
        if v.X > 0:
          self.priority_nodes.append(candidate_id_pos[idx][0])
          if self.max_steps:
            self.max_steps -= 1

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

    # return a node
    if len(self.plan_nodes) > 0:
      if len(self.priority_nodes) == 0:
        self.set_priority_nodes()
        if self.priority_nodes is None or len(self.priority_nodes) == 0:
          return None

      n = self.priority_nodes.pop(0)
      try:
        self.plan_nodes.remove(n)
      except BaseException:
        print("WARNING: node was removed already")
      self.past_nodes.add(n)

      self.update_plan_edges_between_existing_nodes()
      return {'nodes': [n], 'edges': []}

    return None


class OptimalCostsStrategyLimited(OptimalCostsStrategy):

  def __init__(self, max_steps=None) -> None:
    super().__init__()
    self.max_steps = max_steps

  def get_strategy_name(self):
    return 'optc_limited'
