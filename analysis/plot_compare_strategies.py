import csv
import matplotlib.pyplot as plt
import json
import numpy as np
from strategies import randomstrategy, neighborhoodexpansionstrategy, greedystrategy, staticstrategy
from analysis_commons import readable_group_name, readable_strategy_name, read_csv_vals

def yx_vals(groups, steps_per_strategy):
  xvals = {}
  yvals = {
      'grp_avg_rank': {},
      'grp_avg_rank_ci_min': {},
      'grp_avg_rank_ci_max': {},
      'grp_avg_rank_min': {},
      'grp_avg_rank_max': {},
      'grp_max_rank': {},
      'grp_min_rank': {},
      'weighted_avg_rank': {},
      'nodes_in_top_k': {},
  }
  y_lim_upper = 0
  for strategy_no, strategy in enumerate(steps_per_strategy):
    xvals[strategy_no] = {}
    for k in yvals:
      yvals[k][strategy_no] = {}

    for g in groups:
      xvals[strategy_no][g] = []
      for k in yvals:
        yvals[k][strategy_no][g] = []

      for step_no in sorted(steps_per_strategy[strategy].keys()):
        xvals[strategy_no][g].append(step_no)
        vals = steps_per_strategy[strategy][step_no][g]["avg"]
        y_val = sum(vals) / len(vals)
        yvals['grp_avg_rank'][strategy_no][g].append(y_val)
        ci = 1.96 * np.std(vals) / np.sqrt(len(vals))
        yvals['grp_avg_rank_ci_min'][strategy_no][g].append(y_val - ci)
        yvals['grp_avg_rank_ci_max'][strategy_no][g].append(y_val + ci)
        yvals['grp_avg_rank_min'][strategy_no][g].append(min(vals))
        yvals['grp_avg_rank_max'][strategy_no][g].append(max(vals))

        vals = steps_per_strategy[strategy][step_no][g]["min"]
        y_val = sum(vals) / len(vals)
        yvals['grp_min_rank'][strategy_no][g].append(y_val)
        vals = steps_per_strategy[strategy][step_no][g]["max"]
        y_val = sum(vals) / len(vals)
        yvals['grp_max_rank'][strategy_no][g].append(y_val)

        vals = steps_per_strategy[strategy][step_no][g]["weighted_avg_rank"]
        y_val = sum(vals) / len(vals)
        yvals['weighted_avg_rank'][strategy_no][g].append(y_val)

        vals = steps_per_strategy[strategy][step_no][g]["nodes_in_top_k"]
        y_val = sum(vals) / len(vals)
        yvals['nodes_in_top_k'][strategy_no][g].append(y_val)

      for k in yvals:
        # These two are not rank related, we display with a different y axis scale
        if k == 'nodes_in_top_k' or k == 'weighted_avg_rank':
          continue
        y_lim_upper = max(y_lim_upper, max(yvals[k][strategy_no][g]))

    # y_lim_upper *= 1.5
  return xvals, yvals, y_lim_upper

if __name__ == "__main__":
  config = None
  with open('config.json') as config_file:
    config = json.load(config_file)

  plt.rc('font', family='Helvetica Neue')
  # plt.rcParams['figure.dpi'] = 300
  plt.rcParams['image.cmap'] = 'tab10'
