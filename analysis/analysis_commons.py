from __future__ import annotations

import matplotlib.pyplot as plt
import matplotlib as mpl
from matplotlib.patches import Patch
import matplotlib.ticker as ticker
from strategies import RandomStrategy, NeighborhoodExpansionStrategy, GreedyStrategy, StaticStrategy
from commons import float_to_string
import psycopg2
import numpy as np
import io
import os
import sys
import re
import math
import copy
import csv
import itertools
import sys
import gzip
from graph import Graph
from rank import Rank
from agent import Agent
from strategies import *
from commons import float_to_string

from graph import Graph
from rank import Rank
from labeler.database_labeler import label_database
from loaders.prepare_lite_db import prepare_lite_db

TABLEAU_PALETTE = ["#4E79A7", "#F28E2B", "#E15759", "#76B7B2", "#59A14F", "#EDC948", "#B07AA1", "#FF9DA7", "#9C755F", "#BAB0AC" ]


def readable_group_name(group):
  if group == "d":
    return "Disinformer"
  if group == "m":
    return "Mitigator"
  if group == "n":
    return "Neutral"
  else:
    return group


def create_simulation_name(config, label):
  name = "_".join(list(filter(lambda g: g != "None", config['target_groups'])))
  return f"{name}-{label}.csv"


def readable_strategy_name(strategy):
  if isinstance(strategy, Strategy):
    strategy = strategy.__class__.__name__
  if "|" in strategy:
    return "|".join([readable_strategy_name(s) for s in strategy.split("|")])

  if strategy == "GreedyStrategy":
    strategy = "Greedy"
  if strategy == "MultiObjectiveStrategy":
    strategy = "Multi-Objective"
  if strategy == "NeighborhoodExpansionStrategy":
    strategy = "Neighborhood Expansion"
  if strategy == "RandomStrategy":
    strategy = "Random"

  return strategy


def csv_strategies_name(mitigator_strategy, disinformer_strategy):
  return mitigator_strategy.get_strategy_name() + "|" + disinformer_strategy.get_strategy_name()


def strategies_names_from_csv_strategies_name(name):
  return {
    'mitigator': name.split("|")[0],
    'disinformer': name.split("|")[1]
  }


def readable_strategies_names_with_labels(strategies, config):
  mitigator_label = config['mitigator_keyword']
  disinformer_label = config['disinformer_keyword']

  names = [readable_strategy_name(s) for s in strategies.split("|")]
  return f"{mitigator_label}: {names[0]}, {disinformer_label}: {names[1]}"


def datavoid_header(datavoid, config):
  """ return a header for the datavoid, removing non alphanumeric characters and spaces"""
  if isinstance(datavoid, list):
    res = []
    for d in datavoid:
      res.append(datavoid_header(d, config))
    res = "|".join(res)
  else:
    res = re.sub(r'\W+', '', datavoid)
    res = res.replace(" ", "")
  return res


def initialize_output(config, append=False):
  output_filename = None  # initialize to None, just in case it's not given in config

  if "output_filename" in config and config['output_filename'] is not None:
    output_filename = config["output_filename"]
    file_mode = "at" if append else "wt"
    if output_filename.endswith('.gz'):
      output_file = gzip.open(output_filename, file_mode)
    else:
      output_file = open(output_filename, file_mode)
  else:
    output_file = io.StringIO()

  config["output"] = {
      "filename": output_filename,
      "csv_writer": csv.writer(output_file, delimiter=","),
      "file": output_file,
  }

  # TODO save info on measures that are saved in the header (e.g. "bay(topk, weighted)) to say
  # that the values here are first the topk, and then the weighted
  datavoids_header = ["datavoid_" + datavoid_header(config["datavoids"][i], config)
                      for i in range(len(config["datavoids"]))]
  groups_header = ["group_" + config["target_groups"][i]
                   for i in range(len(config["target_groups"]))]

  # Write header only if we are not appending
  if not append:
    config["output"]["csv_writer"].writerow(
        ["run_no", "strategy", "step_no", *groups_header, *datavoids_header])
    config["output"]["file"].flush()

  return output_file

def output_csv_reader(curr_config):
  if "output_filename" in curr_config and curr_config['output_filename'] is not None:
    if curr_config["output_filename"].endswith('.gz'):
      # Open and read gzip file
      f = gzip.open(curr_config["output_filename"], 'rt')
      csv_reader = csv.DictReader(row for row in f if not row.startswith('#'))
    else:
      f = open(curr_config["output_filename"], 'r')
      csv_reader = csv.DictReader(row for row in f if not row.startswith('#'))
  else:
    file_content = curr_config["output"]["file"].getvalue()
    read_file_object = io.StringIO(file_content)
    csv_reader = csv.DictReader(row for row in read_file_object if not row.startswith('#'))

  header = csv_reader.fieldnames
  if header[0] != "run_no" or header[1] != "strategy" or header[2] != "step_no":
    raise ("Invalid csv file")

  return (f, csv_reader)

def get_output(config, output_filename=None):
  curr_config = config
  if output_filename is not None:
    curr_config = copy.deepcopy(config)
    curr_config["output_filename"] = output_filename

  f, csv_reader = output_csv_reader(curr_config)
  max_step = 0
  for r in csv_reader:
    max_step = max(max_step, int(r['step_no']))
  f.close()

  f, csv_reader = output_csv_reader(curr_config)
  no_runs = 0
  for r in csv_reader:
    no_runs = max(no_runs, int(r['run_no']))
  f.close()


  f, csv_reader = output_csv_reader(curr_config)
  res = read_csv_vals(csv_reader, max_step, curr_config)
  f.close()

  return res


def close_output(config):
  if "output" not in config:
    return
  if not isinstance(config["output"]["file"], io.StringIO):
    config["output"]["file"].close()
    config["output"] = None


def wikipedia_link_to_db_url(url):
  return url.replace("https://en.wikipedia.org/wiki/", "")


def wikipedia_link_to_title(url):
  return url.split("/")[-1].replace("_", " ").title()


def wikipedia_link_to_id(url, config):
  return node_url_to_id(wikipedia_link_to_db_url(url), config)


def node_url_to_id(url: str, config):
  conn = psycopg2.connect(**config["database"])
  cursor = conn.cursor()
  cursor.execute("select id from nodes_info where url = %s", (url.lower(),))
  res = cursor.fetchall()
  if len(res) > 2:
    print("WARNING: More than one node with the same url")
  if len(res) == 0:
    raise Exception("No node with the url " + url)
  cursor.close()
  conn.close()
  return res[0][0]


def clone_config_with_target(config, mitigator_keyword, disinformer_keyword,
                             mitigator_node, disinformer_node,
                             mitigator_keywords=[], disinformer_keywords=[]):
  """ returns a configuration copy where the nodes and groups have been changed """

  new_config = config.copy()

  new_config["target_groups"] = [
    mitigator_keyword,
    disinformer_keyword,
    "None"
  ]

  new_config["groups_colors"] = {
    mitigator_keyword: config["groups_colors"]["mit"],
    disinformer_keyword: config["groups_colors"]["dis"],
    "None": config["groups_colors"]["None"]
  }

  new_config["mitigator_keyword"] = mitigator_keyword
  new_config["disinformer_keyword"] = disinformer_keyword

  new_config["target_node"] = {
    mitigator_keyword: int(mitigator_node),
    disinformer_keyword: int(disinformer_node),
  }
  # print("target_nodes", new_config["target_node"])

  new_config[mitigator_keyword + "_keywords"] = mitigator_keywords
  new_config[disinformer_keyword + "_keywords"] = disinformer_keywords

  return new_config


def label_for_topic(topic_name):
  return topic_name[:3].lower()


def check_repeated_keys(datavoids_per_topic_json):
  keys_dict = set()
  for _, d in datavoids_per_topic_json.items():
    for k in [label_for_topic(d['mitigator']), label_for_topic(d['disinformer'])]:
      if k in keys_dict:
        raise Exception("Repeated key " + k)
      keys_dict.add(k)
  return True


def plot_results_for_steps_per_strategy_and_base(
  strategy, strategy_base, steps_per_strategy, steps_per_strategy_base,
  config, topk=False, steps_no=None, title_extra='', max_x=None):

  plt.rc('font', family='Helvetica Neue')
  plt.rcParams['figure.dpi'] = 200
  plt.rcParams['axes.prop_cycle'] = plt.cycler(color=TABLEAU_PALETTE)

  if topk:
    fig, axs = plt.subplots(1, 2, squeeze=False)
  else:
    fig, axs = plt.subplots(1, 1, squeeze=False)

  if steps_no is None:
    steps_no = max(
      max(steps_per_strategy[strategy].keys()),
      max(steps_per_strategy_base[strategy_base].keys())
    )

  for t in ['normal', 'base']:
    curr_strategy = strategy if t == 'normal' else strategy_base
    curr_steps_per_strategy = steps_per_strategy if t == 'normal' else steps_per_strategy_base
    xvals = []
    yvals = {
      "weighted_avg_rank": {gr: [] for gr in config["target_groups"]},
      "nodes_in_top_k": {gr: [] for gr in config["target_groups"]},
      "cost": {gr: [] for gr in config["target_groups"]}
    }
    for step_no in range(steps_no):
      if step_no not in curr_steps_per_strategy[curr_strategy]:
        continue
      xvals.append(step_no)
      for g in config["target_groups"]:
        for v in ["weighted_avg_rank", "nodes_in_top_k"]:
          vals = curr_steps_per_strategy[curr_strategy][step_no][g][v]
          yvals[v][g].append(sum(vals) / len(vals))
        costs = curr_steps_per_strategy[curr_strategy][step_no][g]["cost"]
        yvals["cost"][g].append(sum(costs) / len(costs))

    for g in config["target_groups"]:
      if g == 'None':
        continue

      axs[0][0].plot(
          xvals,
          yvals["weighted_avg_rank"][g],
          label=readable_group_name(g),
          alpha=0.2 if t == 'base' else 1,
          color=config["groups_colors"][g])
      axs[0][0].set_title(f'weighted avg rank ' + title_extra, fontsize=8)
      axs[0][0].autoscale(enable=True, axis='y')
      axs[0][0].set_ylim(bottom=-0.1)
      if max_x is not None:
        axs[0][0].set_xlim(left=-1, right=max_x)
      # axs[0][0].set_xticks(xvals)

      if topk:
        axs[0][1].plot(
            xvals,
            yvals["nodes_in_top_k"][g],
            label=readable_group_name(g),
            alpha=0.3 if t == 'base' else 1,
            color=config["groups_colors"][g])
        axs[0][1].set_title(f'nodes in top k ' + title_extra, fontsize=8)
        axs[0][1].autoscale(enable=True, axis='y')
        axs[0][1].set_ylim(bottom=-0.1)
        if max_x is not None:
          axs[0][1].set_xlim(left=-1, right=max_x)

    fig.set_size_inches(12, max(3, 1))
    plt.tight_layout(pad=1)
    handles, labels = axs[0][0].get_legend_handles_labels()
    legend = fig.legend(
        handles,
        labels,
        loc='lower right',
        borderaxespad=1,
        fontsize=20,
        ncol=len(labels))

  legend.get_frame().set_linewidth(0.0)
  fig.suptitle(f'{readable_strategies_names_with_labels(strategy, config)}',
               fontsize=12, y=0.01)
  plt.subplots_adjust(bottom=0.12)

  plt.show()


def plot_nodes_added(strategy, steps_per_strategy, config,
                     filter_groups=[], steps_no=None, max_x=None):
  plt.rc('font', family='Helvetica Neue')
  plt.rcParams['figure.dpi'] = 200
  plt.rcParams['axes.prop_cycle'] = plt.cycler(color=TABLEAU_PALETTE)

  if steps_no is None:
    steps_no = max(steps_per_strategy[strategy].keys())

  xvals = []
  yvals = {
    "nodes_added": {gr: [] for gr in config["target_groups"]}
  }
  for step_no in range(steps_no):
    xvals.append(step_no)
    for g in config["target_groups"]:
      vals = steps_per_strategy[strategy][step_no][g]["nodes_added"]
      y_val = sum(vals) / len(vals)
      yvals["nodes_added"][g].append(y_val)

  fig, axs = plt.subplots(1, 1, squeeze=False)
  for g in config["target_groups"]:
    if g in filter_groups:
      continue
    axs[0][0].plot(
        xvals,
        yvals["nodes_added"][g],
        label=readable_group_name(g),
        color=config["groups_colors"][g]
    )
    axs[0][0].set_title(f'nodes added', fontsize=8)
    axs[0][0].autoscale(enable=True, axis='y')
    axs[0][0].set_ylim(bottom=0)
    if max_x is not None:
      axs[0][0].set_xlim(right=max_x)

  fig.set_size_inches(12, 3)
  plt.tight_layout(pad=1)
  handles, labels = axs[0][0].get_legend_handles_labels()
  legend = fig.legend(
      handles,
      labels,
      loc='lower right',
      borderaxespad=1,
      fontsize=8,
      ncol=len(labels))
  legend.get_frame().set_linewidth(0.0)
  fig.suptitle(f'{readable_strategies_names_with_labels(strategy, config)}',
               fontsize=12, y=0.01)
  plt.subplots_adjust(bottom=0.12)

  plt.show()


def plot_group_costs_multiple_set_ups_ranges(
  target_group, steps_per_strategy_per_set_up, config, steps_no=None, max_x=None):
  set_ups = steps_per_strategy_per_set_up.keys()

  if steps_no is None:
    steps_no = math.inf
    for set_up in set_ups:
      steps_no = min(
        steps_no,
        max(steps_per_strategy_per_set_up[set_up].keys())
      )

  yvals = {
    "cost": {set_up: [] for set_up in set_ups}
  }
  for step_no in range(steps_no + 1):
    for set_up in set_ups:
      vals = steps_per_strategy_per_set_up[set_up][step_no][target_group]["cost"]
      y_val = sum(vals) / len(vals)
      yvals["cost"][set_up].append(y_val)

  max_all = 0
  for set_up in set_ups:
    max_all = max(max_all, max(yvals["cost"][set_up]))

  return [0, max_all]


def plot_group_costs_multiple_set_ups(target_group, steps_per_strategy_per_set_up,
                                      config, steps_no=None, max_x=None, print_legend=True):
  plt.rc('font', family='Helvetica Neue', size=20)
  plt.rcParams['figure.dpi'] = 200
  plt.rcParams['axes.prop_cycle'] = plt.cycler(color=TABLEAU_PALETTE)
  line_styles = itertools.cycle(["-","--",":",".","h","H"])

  set_ups = steps_per_strategy_per_set_up.keys()

  if steps_no is None:
    steps_no = math.inf
    for set_up in set_ups:
      last_step = max(steps_per_strategy_per_set_up[set_up].keys())
      steps_no = min(
        steps_no,
        int(steps_per_strategy_per_set_up[set_up][last_step][target_group]['nodes_added'][0])
      )

  xvals = []
  yvals = {
    "cost": {set_up: [] for set_up in set_ups}
  }
  confidence_intervals = {
    "cost": {
        set_up: {
            "upper": [],
            "lower": []
        } for set_up in set_ups
    }
  }
  for step_no in range(steps_no + 1):
    xvals.append(step_no)
    for set_up in set_ups:
      vals = steps_per_strategy_per_set_up[set_up][step_no][target_group]["cost"]
      y_val = sum(vals) / len(vals)
      yvals["cost"][set_up].append(y_val)

      confidence_interval_lower, confidence_interval_upper = compute_confidence_interval(vals)
      confidence_intervals["cost"][set_up]["upper"].append(confidence_interval_upper)
      confidence_intervals["cost"][set_up]["lower"].append(confidence_interval_lower)

  # max_s = 0
  # max_all = 0
  # for set_up in set_ups:
  #   max_all = max(max_all, max(yvals["cost"][set_up]))
  # for set_up in set_ups:
  #   max_s = max(yvals["cost"][set_up])
  #   for i in range(len(yvals["cost"][set_up])):
  #     yvals["cost"][set_up][i] = max_all * (yvals["cost"][set_up][i] / max_s)

  fig, axs = plt.subplots(1, 1, squeeze=False)
  for set_up in set_ups:
    axs[0][0].plot(
        xvals,
        yvals["cost"][set_up],
        next(line_styles),
        linewidth=3,
        label=set_up
    )
    # axs[0][0].set_title(f'costs', fontsize=8)
    axs[0][0].autoscale(enable=True, axis='y')
    axs[0][0].set_ylim(bottom=0)
    if max_x is not None:
      axs[0][0].set_xlim(right=max_x)

    axs[0][0].fill_between(
      xvals,
      confidence_intervals["cost"][set_up]["upper"],
      confidence_intervals["cost"][set_up]["lower"],
      color='#AAAAAA',  # gray color
      alpha=0.3 # make it slightly transparent
    )

  fig.set_size_inches(8, 4)
  plt.tight_layout()
  if print_legend:
    handles, labels = axs[0][0].get_legend_handles_labels()
    legend = fig.legend(
        handles,
        labels,
        loc='lower right',
        bbox_to_anchor=(1, -0.0),
        fontsize=20,
        ncol=len(labels))
    legend.get_frame().set_linewidth(0.0)
  plt.subplots_adjust(bottom=0.3)

  plt.show()

  return fig


def plot_costs(strategy, steps_per_strategy, config, filter_groups=[],
               steps_no=None, max_x=None):
  plt.rc('font', family='Helvetica Neue')
  plt.rcParams['figure.dpi'] = 200
  plt.rcParams['axes.prop_cycle'] = plt.cycler(color=TABLEAU_PALETTE)

  if steps_no is None:
    steps_no = max(steps_per_strategy[strategy].keys())

  xvals = []
  yvals = {
    "cost": {gr: [] for gr in config["target_groups"]}
  }
  for step_no in range(steps_no):
    xvals.append(step_no)
    for g in config["target_groups"]:
      vals = steps_per_strategy[strategy][step_no][g]["cost"]
      y_val = sum(vals) / len(vals)
      yvals["cost"][g].append(y_val)

  fig, axs = plt.subplots(1, 1, squeeze=False)
  for g in config["target_groups"]:
    if g in filter_groups:
      continue
    axs[0][0].plot(
        xvals,
        yvals["cost"][g],
        label=readable_group_name(g),
        color=config["groups_colors"][g]
    )
    # axs[0][0].set_title(f'costs', fontsize=8)
    axs[0][0].autoscale(enable=True, axis='y')
    axs[0][0].set_ylim(bottom=0)
    if max_x is not None:
      axs[0][0].set_xlim(right=max_x)

  fig.set_size_inches(12, 3)
  plt.tight_layout(pad=1)
  handles, labels = axs[0][0].get_legend_handles_labels()
  legend = fig.legend(
      handles,
      labels,
      loc='lower right',
      borderaxespad=1,
      fontsize=8,
      ncol=len(labels))
  legend.get_frame().set_linewidth(0.0)
  # fig.suptitle(f'{readable_strategies_names_with_labels(strategy, config)}', fontsize=12, y=0.01)
  # plt.subplots_adjust(bottom=0.12)

  plt.show()

  return fig


def plot_results_for_steps_per_strategy(
  strategy, steps_per_strategy, config, filter_groups=[], topk=False, show=True):
  plt.rc('font', family='Helvetica Neue')
  plt.rcParams['figure.dpi'] = 200
  plt.rcParams['axes.prop_cycle'] = plt.cycler(color=TABLEAU_PALETTE)

  if topk:
    fig, axs = plt.subplots(1, 2, squeeze=False)
  else:
    fig, axs = plt.subplots(1, 1, squeeze=False)

  xvals = []
  yvals = {
    "weighted_avg_rank": {gr: [] for gr in config["target_groups"]},
    "nodes_in_top_k": {gr: [] for gr in config["target_groups"]}
  }
  for step_no in sorted(steps_per_strategy[strategy].keys()):
    xvals.append(step_no)
    for g in config["target_groups"]:
      for v in ["weighted_avg_rank", "nodes_in_top_k"]:
        vals = steps_per_strategy[strategy][step_no][g][v]
        y_val = sum(vals) / len(vals)
        yvals[v][g].append(y_val)

  for g in config["target_groups"]:
    if g in filter_groups:
      continue

    axs[0][0].plot(
        xvals,
        yvals["weighted_avg_rank"][g],
        label=readable_group_name(g),
        color=config["groups_colors"][g])
    axs[0][0].set_title(f'weighted avg rank', fontsize=8)
    axs[0][0].autoscale(enable=True, axis='y')
    axs[0][0].set_ylim(bottom=0)

    if topk:
      axs[0][1].plot(
          xvals,
          yvals["nodes_in_top_k"][g],
          label=readable_group_name(g),
          color=config["groups_colors"][g])
      axs[0][1].set_title(f'nodes in top k', fontsize=8)
      axs[0][1].autoscale(enable=True, axis='y')
      axs[0][1].set_ylim(bottom=0)

  fig.set_size_inches(12, max(3, 1))
  plt.tight_layout(pad=1)
  handles, labels = axs[0][0].get_legend_handles_labels()
  legend = fig.legend(
      handles,
      labels,
      loc='lower right',
      borderaxespad=1,
      fontsize=8,
      ncol=len(labels))
  legend.get_frame().set_linewidth(0.0)
  fig.suptitle(f'{readable_strategies_names_with_labels(strategy, config)}', fontsize=12, y=0.01)
  plt.subplots_adjust(bottom=0.12)

  if show:
    plt.show()

  return fig


def calculate_area_for_steps_per_strategy(strategy, steps_per_strategy, config):
  """
  Calculate the area for weighted_avg_rank and nodes_in_top_k.
  Now includes areas for both target groups and counts the number of steps each group was above the other.
  """
  target_groups = list(filter(lambda v: v != 'None', config["target_groups"]))
  if len(target_groups) != 2:
    raise ValueError("This method works only when there are exactly two target groups.")

  group1, group2 = target_groups

  xvals = []
  yvals = {
      "weighted_avg_rank": {gr: [] for gr in target_groups},
      "nodes_in_top_k": {gr: [] for gr in target_groups},
  }
  steps_above = {
      "weighted_avg_rank": {gr: 0 for gr in target_groups},
      "nodes_in_top_k": {gr: 0 for gr in target_groups}
  }
  areas = {
      "weighted_avg_rank": {gr: [] for gr in target_groups},
      "nodes_in_top_k": {gr: [] for gr in target_groups}
  }

  for step_no in sorted(steps_per_strategy[strategy].keys()):
    xvals.append(step_no)
    for g in target_groups:
      for v in ["weighted_avg_rank", "nodes_in_top_k"]:
        vals = steps_per_strategy[strategy][step_no][g][v]
        y_val = sum(vals) / len(vals)
        yvals[v][g].append(y_val)

    # Count steps above for each metric
    for v in ["weighted_avg_rank", "nodes_in_top_k"]:
      if yvals[v][group1][-1] > yvals[v][group2][-1]:
        steps_above[v][group1] += 1
        areas[v][group1].append(yvals[v][group1][-1] - yvals[v][group2][-1])
        areas[v][group2].append(0)
      elif yvals[v][group1][-1] < yvals[v][group2][-1]:
        steps_above[v][group2] += 1
        areas[v][group2].append(yvals[v][group2][-1] - yvals[v][group1][-1])
        areas[v][group1].append(0)

  # Calculate the areas for both groups and the difference
  area_results = {}
  for v in ["weighted_avg_rank", "nodes_in_top_k"]:
    area_results[v] = {
        f'area_{group1}': sum(areas[v][group1]),
        f'area_{group2}': sum(areas[v][group2]),
        'steps_above': steps_above[v]
    }

  return area_results


def prepare_db(config, filter_by_topk_words=3, lite_db_name="wikilite", force_preparation=True):
  if config["database"]["database"] == lite_db_name:
    config["database"]["database"] = "wikidump"

    prepare = True
    if not force_preparation:
      graph = Graph(config)
      graph.connect()
      with graph.conn.cursor() as cursor:
        cursor.execute("SELECT DISTINCT grp FROM nodes")
        normal_db_groups = set(row[0] for row in cursor.fetchall())
      if len(normal_db_groups) == 0:
        raise Exception("No groups found in database")
      wikilite_config = copy.deepcopy(config)
      wikilite_config["database"]["database"] = lite_db_name
      lite_graph = Graph(wikilite_config)
      lite_graph.connect()
      with lite_graph.conn.cursor() as cursor:
        cursor.execute("SELECT DISTINCT grp FROM nodes")
        lite_db_groups = set(row[0] for row in cursor.fetchall())
      if len(lite_db_groups) == 0:
        raise Exception("No groups found in database")
      if normal_db_groups == lite_db_groups:
        print("Group names are the same in both databases. No further action needed.")
        prepare = False
      graph.close()
      lite_graph.close()

    if prepare:
      label_database(config, filter_by_topk_words=filter_by_topk_words)
      prepare_lite_db(config, lite_db_name,
                      prob_node_inserted_if_not_important=0.01,
                      prob_edge_inserted_if_not_important=0.01,
                      )

    config["database"]["database"] = lite_db_name

  return label_database(config, filter_by_topk_words=filter_by_topk_words)


def run_simple_simulation(keyword, mitigator_strategy,
                          disinformer_strategy, simulation_label, config, mute_output=False,
                          number_of_runs=1, delete_results_if_exist=True, delete_pagerank=True, delete_tsrank=True):
  if mute_output:
    original_stdout = sys.stdout
    sys.stdout = io.StringIO()

  graph = Graph(config)
  graph.connect()

  config["output_filename"] = 'results/' + create_simulation_name(config, simulation_label)
  if os.path.isfile(config["output_filename"]):
    if delete_results_if_exist:
      os.remove(config["output_filename"])
    else:
      return config["output_filename"]
  print('Output:', config["output_filename"])
  initialize_output(config, False)

  print("    Setting all nodes and edges to active...")
  graph.set_all_nodes_and_edges_active(True)

  run_no = 0
  max_steps = 0
  ranking_algorithm = Rank(graph, "searchrank")
  ranking_algorithm.rank(keyword, delete_pagerank=delete_pagerank, delete_tsrank=delete_tsrank)
  while run_no < number_of_runs:
    print("Run no: " + str(run_no))
    steps = compare_strategies(
        run_no,
        mitigator_strategy,
        disinformer_strategy,
        ranking_algorithm,
        graph,
        config)
    if steps > max_steps:
      max_steps = steps
    run_no += 1

  graph.close()
  close_output(config)
  print("Done")

  if mute_output:
    sys.stdout = original_stdout

  return config["output_filename"]


def plot_differences_against_opponent_base_ranges(target_group, opponent_group,
                                                  strategy_base, strategy,
                                                  steps_per_strategy_base, steps_per_strategy, config):
  max_y_val = 0
  min_y_val = 0

  steps_no = min(
    max(steps_per_strategy[strategy].keys()),
    max(steps_per_strategy_base[strategy_base].keys())
  )

  for step_no in range(steps_no + 1):
    vals = steps_per_strategy_base[strategy_base][step_no][opponent_group]["weighted_avg_rank"]
    y_val_opponent_base = sum(vals) / len(vals)

    vals = steps_per_strategy[strategy][step_no][opponent_group]["weighted_avg_rank"]
    y_val_opponent = sum(vals) / len(vals)

    vals = steps_per_strategy_base[strategy_base][step_no][target_group]["weighted_avg_rank"]
    y_val_base = sum(vals) / len(vals)

    vals = steps_per_strategy[strategy][step_no][target_group]["weighted_avg_rank"]
    y_val = sum(vals) / len(vals)

    if max_y_val < y_val - y_val_opponent:
      max_y_val = y_val - y_val_opponent
    if max_y_val < y_val_base - y_val_opponent_base:
      max_y_val = y_val_base - y_val_opponent_base
    if min_y_val > y_val - y_val_opponent:
      min_y_val = y_val - y_val_opponent
    if min_y_val > y_val_base - y_val_opponent_base:
      min_y_val = y_val_base - y_val_opponent_base

  return [min_y_val, max_y_val, step_no]


def plot_differences_against_opponent_base(title, target_group, opponent_group, strategy_base, strategy,
                                           steps_per_strategy_base, steps_per_strategy, config, y_min=None, y_max=None,
                                           show=True, steps_no=None, plot_x_axis=True, plot_y_axis=True, log_scale=False, ylabel=None, xlabel=None, 
                                           show_legend=True):
  plt.rc('font', family='Helvetica Neue', size=25)
  plt.rcParams['figure.dpi'] = 200
  plt.rcParams['axes.prop_cycle'] = plt.cycler(color=TABLEAU_PALETTE)

  fig, axs = plt.subplots(1, 1, squeeze=False)

  if steps_no is None:
    steps_no = max(steps_per_strategy[strategy].keys())

  xvals = []
  yvals = {
    "weighted_avg_rank": {gr: [] for gr in [opponent_group + '_base', opponent_group, target_group + '_base', target_group]},
    "diff": {gr: [] for gr in ['base', 'test']}
  }
  for step_no in range(steps_no + 1):
    if step_no not in steps_per_strategy_base[strategy_base] \
      or step_no not in steps_per_strategy[strategy]:
      continue

    xvals.append(step_no)

    vals = steps_per_strategy_base[strategy_base][step_no][opponent_group]["weighted_avg_rank"]
    y_val_opponent_base = sum(vals) / len(vals)
    yvals["weighted_avg_rank"][opponent_group + '_base'].append(y_val_opponent_base)

    vals = steps_per_strategy[strategy][step_no][opponent_group]["weighted_avg_rank"]
    y_val_opponent = sum(vals) / len(vals)
    yvals["weighted_avg_rank"][opponent_group].append(y_val_opponent)

    vals = steps_per_strategy_base[strategy_base][step_no][target_group]["weighted_avg_rank"]
    y_val_base = sum(vals) / len(vals)
    yvals["weighted_avg_rank"][target_group + '_base'].append(y_val_base)

    vals = steps_per_strategy[strategy][step_no][target_group]["weighted_avg_rank"]
    y_val = sum(vals) / len(vals)
    yvals["weighted_avg_rank"][target_group].append(y_val)

    yvals["diff"]['test'].append(y_val - y_val_opponent)
    yvals["diff"]['base'].append(y_val_base - y_val_opponent_base)

  for g in ['base', 'test']:
    axs[0][0].plot(
        xvals,
        yvals['diff'][g],
        label=readable_group_name(g),
        color='#777777' if g == 'base' else 'black',
        linewidth=3
    )
    if title:
      axs[0][0].set_title(title, fontsize=8)
    axs[0][0].autoscale(enable=True, axis='y')

    if y_min is not None and y_max is not None:
      axs[0][0].set_ylim(bottom=y_min, top=y_max)
      # axs[0][0].set_yticks([y_min, 0, y_max])
    elif y_max is not None:
      axs[0][0].set_ylim(bottom=0, top=y_max)
      # axs[0][0].set_yticks([0, y_max])
    elif y_min is not None:
      axs[0][0].set_ylim(bottom=y_min)
      # axs[0][0].set_yticks([y_min, 0])
    axs[0][0].set_xlim(left=0, right=step_no)

  label_above = "Outperform"
  label_below = "Underperform"

  axs[0][0].fill_between(xvals,
                         yvals["diff"]['test'],
                         yvals["diff"]['base'],
                         color="#90EE90",
                         alpha=0.5,
                         interpolate=True,
                         label=label_above,
                         where=[yvals["diff"]['test'][i] >= yvals["diff"]['base'][i]
                                for i in range(len(xvals))]
                         )
  axs[0][0].fill_between(xvals,
                         yvals["diff"]['test'],
                         yvals["diff"]['base'],
                         color="#c90076",
                         alpha=0.9,
                         interpolate=True,
                         label=label_below,
                         where=[yvals["diff"]['test'][i] <= yvals["diff"]['base'][i]
                                for i in range(len(xvals))]
                         )

  axs[0][0].axhline(y=0, color='gray', linestyle=':')

  fig.set_size_inches(6, 4)

  plt.tight_layout()

  axs[0][0].spines['top'].set_visible(False)
  axs[0][0].spines['right'].set_visible(False)

  axs[0][0].tick_params(axis="x", direction="in")
  axs[0][0].tick_params(axis="y", direction="in")
  axs[0][0].tick_params(axis='both', which='both', length=1, labelbottom=plot_x_axis, labelleft=plot_y_axis)

  if show_legend:
    handles, labels = axs[0][0].get_legend_handles_labels()
    legend = fig.legend(
      handles,
      labels + [label_above, label_below],  
      loc='lower right',
      borderaxespad=1,
      bbox_to_anchor=(1, -0.0),
      fontsize=20,
      ncol=len(labels) + 2
    )
    legend.get_frame().set_linewidth(0.0)
  plt.subplots_adjust(left=0.1, right=0.9, top=0.9, bottom=0.3)

  if xlabel:
    plt.xlabel(xlabel)
  
  if ylabel:
    plt.ylabel(ylabel)

  if show:
    plt.show()

  return fig


def plot_differences_against_base_ranges(target_group, strategy_base_csv_name, strategy_csv_name,
                                         steps_per_strategy_base, steps_per_strategy, config):
  max_y_val = 0
  max_steps = min(
    max([int(s) for s in steps_per_strategy[strategy_csv_name].keys()]),
    max([int(s) for s in steps_per_strategy_base[strategy_base_csv_name].keys()])
  )
  for step_no in range(max_steps + 1):
    vals_base = steps_per_strategy_base[strategy_base_csv_name][step_no][target_group]["weighted_avg_rank"]
    y_val_base = sum(vals_base) / len(vals_base)
    vals = steps_per_strategy[strategy_csv_name][step_no][target_group]["weighted_avg_rank"]
    y_val = sum(vals) / len(vals)
    if y_val_base > max_y_val:
      max_y_val = y_val_base
    if y_val > max_y_val:
      max_y_val = y_val

  return [0, max_y_val]


def compute_confidence_interval(vals, confidence_level=0.95):
    # Compute sample mean and standard deviation
  mean = np.mean(vals)
  std = np.std(vals, ddof=1)  # ddof=1 provides an unbiased estimator of the variance
  n = len(vals)

  # Compute the Z-value from the desired confidence level
  z = {
      0.90: 1.645,
      0.95: 1.96,
      0.99: 2.576
  }.get(confidence_level, 1.96)  # Default is 95%

  # Calculate margin of error
  moe = z * (std / np.sqrt(n))

  # Return lower and upper bounds of the confidence interval
  return mean - moe, mean + moe


def plot_differences_against_base(title, target_group, strategy_base_csv_name, strategy_csv_name,
                                  steps_per_strategy_base, steps_per_strategy, config, y_max=None,
                                  show=True, show_xaxis_numbers=True, show_yaxis_numbers=True):
  plt.rc('font', family='Helvetica Neue', size=20)
  plt.rcParams['figure.dpi'] = 200
  plt.rcParams['axes.prop_cycle'] = plt.cycler(color=TABLEAU_PALETTE)

  fig, axs = plt.subplots(1, 1, squeeze=False)

  xvals = []
  yvals = {
    "weighted_avg_rank": {gr: [] for gr in [target_group + '_base', target_group]},
  }
  confidence_intervals = {
    "weighted_avg_rank": {
        gr: {
            "upper": [],
            "lower": []
        } for gr in [target_group + '_base', target_group]
    }
  }

  max_steps = min(
    max([int(s) for s in steps_per_strategy[strategy_csv_name].keys()]),
    max([int(s) for s in steps_per_strategy_base[strategy_base_csv_name].keys()])
  )
  for step_no in range(max_steps + 1):
    xvals.append(step_no)
    vals = steps_per_strategy_base[strategy_base_csv_name][step_no][target_group]["weighted_avg_rank"]
    y_val = sum(vals) / len(vals)
    yvals["weighted_avg_rank"][target_group + '_base'].append(y_val)

    vals = steps_per_strategy[strategy_csv_name][step_no][target_group]["weighted_avg_rank"]
    y_val = sum(vals) / len(vals)
    yvals["weighted_avg_rank"][target_group].append(y_val)

    confidence_interval_lower, confidence_interval_upper = compute_confidence_interval(vals)
    confidence_intervals["weighted_avg_rank"][target_group]["upper"].append(
      confidence_interval_upper)
    confidence_intervals["weighted_avg_rank"][target_group]["lower"].append(
      confidence_interval_lower)

  for g in [target_group + '_base', target_group]:
    axs[0][0].plot(
        xvals,
        yvals["weighted_avg_rank"][g],
        label=readable_group_name(g),
        color='#555555',
        alpha=0.5 if g.endswith('_base') else 1.0
    )

    if title:
      axs[0][0].set_title(title, fontsize=8)
    axs[0][0].autoscale(enable=True, axis='y')
    if y_max is None:
      axs[0][0].set_ylim(bottom=0)
    else:
      axs[0][0].set_ylim(bottom=0, top=y_max)

  axs[0][0].fill_between(
      xvals,
      confidence_intervals["weighted_avg_rank"][g]["upper"],
      confidence_intervals["weighted_avg_rank"][g]["lower"],
      color='#AAAAAA',  # gray color
      alpha=0.3,       # make it slightly transparent
      label=f'{readable_group_name(g)} Confidence Interval'
    )

  axs[0][0].fill_between(xvals,
                         yvals["weighted_avg_rank"][target_group],
                         yvals["weighted_avg_rank"][target_group + '_base'],
                         color='green',
                         alpha=0.2,
                         interpolate=True,
                         where=[yvals["weighted_avg_rank"][target_group][i] >= yvals["weighted_avg_rank"]
                                [target_group + '_base'][i] for i in range(len(xvals))]
                         )
  axs[0][0].fill_between(xvals,
                         yvals["weighted_avg_rank"][target_group],
                         yvals["weighted_avg_rank"][target_group + '_base'],
                         color='red',
                         alpha=0.2,
                         interpolate=True,
                         where=[yvals["weighted_avg_rank"][target_group][i] <= yvals["weighted_avg_rank"]
                                [target_group + '_base'][i] for i in range(len(xvals))]
                         )

  fig.set_size_inches(4, max(3, len(config["datavoids"])))

  plt.tight_layout()

  if show:
    plt.show()

  return fig


def top_k_group_analysis(graph, config):
  top_k_nodes = graph.get_top_k(config["top_k"], config["target_groups"], active=True)
  topk_nodes_per_group = {}
  wavgrank_per_group = {}
  for group in config["target_groups"]:
    topk_nodes_per_group[group] = 0
    wavgrank_per_group[group] = 0
  for pos, node in enumerate(top_k_nodes):
    topk_nodes_per_group[node["group"]] += 1
    wavgrank_per_group[node["group"]] += 1 / (pos + 1)
  for group in config["target_groups"]:
    topk_nodes_per_group[group] = topk_nodes_per_group[group] / config["top_k"]

  # DEBUG
  # topk_nodes_per_group_positions = {}
  # for pos, node in enumerate(top_k_nodes):
  #   if node["group"] not in topk_nodes_per_group_positions:
  #     topk_nodes_per_group_positions[node["group"]] = []
  #   topk_nodes_per_group_positions[node["group"]].append(pos)
  # if 'opt' in topk_nodes_per_group_positions:
  #   print('opt')
  # for k in topk_nodes_per_group_positions.keys():
  #   print(k, wavgrank_per_group[k], topk_nodes_per_group_positions[k])

  return topk_nodes_per_group, wavgrank_per_group


def read_csv_vals(csv_reader, max_steps, config):
  steps_per_strategy = {}
  strategies = set()
  id_max_rank = {}
  for g in config["target_groups"]:
    id_max_rank[g] = (None, 0)
  current_run = 0
  for r in csv_reader:
    if current_run != int(r['run_no']):
      for step in range(max_steps + 1):
        for g in config["target_groups"]:
          if len(steps_per_strategy[strategy][step][g]["nodes_in_top_k"]) < current_run + 1:
            steps_per_strategy[strategy][step][g]["nodes_in_top_k"].append(None)
          if len(steps_per_strategy[strategy][step][g]["weighted_avg_rank"]) < current_run + 1:
            steps_per_strategy[strategy][step][g]["weighted_avg_rank"].append(None)
          if len(steps_per_strategy[strategy][step][g]["cost"]) < current_run + 1:
            steps_per_strategy[strategy][step][g]["cost"].append(None)
          if len(steps_per_strategy[strategy][step][g]["nodes_added"]) < current_run + 1:
            steps_per_strategy[strategy][step][g]["nodes_added"].append(None)
          if len(steps_per_strategy[strategy][step][g]["edges_added"]) < current_run + 1:
            steps_per_strategy[strategy][step][g]["edges_added"].append(None)
      current_run = int(r['run_no'])
      
    strategy = r['strategy']
    if strategy not in steps_per_strategy:
      steps_per_strategy[strategy] = {}
      for step in range(max_steps + 1):
        steps_per_strategy[strategy][step] = {gr: {
            "avg": [],
            "max": [],
            "min": [],
            "nodes_in_top_k": [],
            "weighted_avg_rank": [],
            "cost": [],
            "nodes_added": [],
            "edges_added": []
        } for gr in config["target_groups"]}
    if strategy not in strategies:
      strategies.add(strategy)
    step_no = int(r['step_no'])
    for grp in config["target_groups"]:
      vals = r["group_" + grp].split("|")
      if vals[0] != "None":
        steps_per_strategy[strategy][step_no][grp]["avg"].append(float(vals[0]))
      if vals[1] != "None":
        steps_per_strategy[strategy][step_no][grp]["max"].append(float(vals[1]))
      if vals[2] != "None":
        steps_per_strategy[strategy][step_no][grp]["min"].append(float(vals[2]))
      steps_per_strategy[strategy][step_no][grp]["nodes_in_top_k"].append(float(vals[3]))
      steps_per_strategy[strategy][step_no][grp]["weighted_avg_rank"].append(float(vals[4]))
      steps_per_strategy[strategy][step_no][grp]["cost"].append(float(vals[5]))
      steps_per_strategy[strategy][step_no][grp]["nodes_added"].append(float(vals[6]))
      steps_per_strategy[strategy][step_no][grp]["edges_added"].append(float(vals[7]))

  for step in range(max_steps + 1):
    for g in config["target_groups"]:
      if len(steps_per_strategy[strategy][step][g]["nodes_in_top_k"]) < current_run + 1:
        steps_per_strategy[strategy][step][g]["nodes_in_top_k"].append(None)
      if len(steps_per_strategy[strategy][step][g]["weighted_avg_rank"]) < current_run + 1:
        steps_per_strategy[strategy][step][g]["weighted_avg_rank"].append(None)
      if len(steps_per_strategy[strategy][step][g]["cost"]) < current_run + 1:
        steps_per_strategy[strategy][step][g]["cost"].append(None)
      if len(steps_per_strategy[strategy][step][g]["nodes_added"]) < current_run + 1:
        steps_per_strategy[strategy][step][g]["nodes_added"].append(None)
      if len(steps_per_strategy[strategy][step][g]["edges_added"]) < current_run + 1:
        steps_per_strategy[strategy][step][g]["edges_added"].append(None)

  return steps_per_strategy, list(strategies), id_max_rank


def save_res_csv(step_no, run_no, disinformer_strategy, mitigator_strategy, graph: Graph, config):
  test_output_tuple = [
      run_no,
      csv_strategies_name(mitigator_strategy, disinformer_strategy),
      step_no
  ]

  topk_nodes_per_group, wavgrank_per_group = top_k_group_analysis(graph, config)
  for group in config["target_groups"]:
    cost = float_to_string(
      disinformer_strategy.agent.cost if group == disinformer_strategy.agent.group
      else mitigator_strategy.agent.cost if group == mitigator_strategy.agent.group
      else -1
    )
    node_added = str(
      disinformer_strategy.agent.nodes_added if group == disinformer_strategy.agent.group
      else mitigator_strategy.agent.nodes_added if group == mitigator_strategy.agent.group
      else -1
    )
    edges_added = str(
      disinformer_strategy.agent.edges_added if group == disinformer_strategy.agent.group
      else mitigator_strategy.agent.edges_added if group == mitigator_strategy.agent.group
      else -1
    )
    group_results = [
        float_to_string(graph.get_avg_all_rank_of_a_group(group, active=True)),
        float_to_string(graph.get_max_rank_of_a_group(group, active=True)),
        float_to_string(graph.get_min_rank_of_a_group(group, active=True)),
        float_to_string(topk_nodes_per_group[group]),
        float_to_string(wavgrank_per_group[group]),
        cost,
        node_added,
        edges_added
    ]
    test_output_tuple.append("|".join(group_results))

  config["output"]["csv_writer"].writerow(test_output_tuple)
  config["output"]["file"].flush()


def compare_strategies(run_no, mitigator_strategy, disinformer_strategy,
                       ranking_algorithm, graph, config):

  print("    Setting all nodes and edges to active...")
  graph.set_all_nodes_and_edges_active(True)

  print("  Testing strategy: ")
  print("             " + disinformer_strategy.get_strategy_name())
  print("             " + mitigator_strategy.get_strategy_name())

  disinformer = Agent(graph, config["disinformer_keyword"], config)
  disinformer.set_strategy(disinformer_strategy)
  print("    Disinformer initializing plan...")
  disinformer.initialize_plan()

  mitigator = Agent(graph, config["mitigator_keyword"], config)
  mitigator.set_strategy(mitigator_strategy)
  print("    Mitigator initializing plan...")
  mitigator.initialize_plan()

  disinformer_done = False
  mitigator_done = False
  step_no = 0

  if config["compute_initial_rage_rank"]:
    print("Computing initial pagerank...")
    ranking_algorithm.rank()

  print("Running...", end="")
  while not disinformer_done or not mitigator_done:
    print(".", end="")
    if step_no % 30 == 0:
      print("")

    save_res_csv(step_no, run_no, disinformer_strategy, mitigator_strategy, graph, config)

    # graph.display_graph(title="Step " + str(step_no), **(display_params | {'auto_close': 1}))

    if not disinformer_done:
      disinformer_done = disinformer.step() is None
    if not mitigator_done:
      mitigator_done = mitigator.step() is None

    graph.conn.commit()

    if config["page_rank_at_each_step"]:
      ranking_algorithm.rank()

    # Print the number of active nodes in mitigator and disinformer
    # print("        Disinformer active nodes: " +
    #     str(len(graph.get_nodes_with_group( config['disinformer_keyword'], True))))
    # print("        Mitigator active nodes: " +
    #     str(len(graph.get_nodes_with_group( config['mitigator_keyword'], True))))

    # print("        Going to next step...")
    step_no += 1

  print("\n")

  print("Disinformer done after", disinformer.steps_count, "steps")
  print("Mitigator done after", mitigator.steps_count, "steps")

  print("\n")

  save_res_csv(step_no, run_no, disinformer_strategy, mitigator_strategy, graph, config)

  return step_no
