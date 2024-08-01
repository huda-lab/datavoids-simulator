import psycopg2
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import json
import sys


def words_distr(table_name, title, conn):
  cur = conn.cursor()

  cur.execute(f"SELECT freq FROM {table_name};")
  data = cur.fetchall()

  freqs = np.array([d[0] for d in data])
  cur.execute(f"SELECT MIN(freq), MAX(freq) FROM {table_name};")
  min_freq, max_freq = cur.fetchone()
  print(min_freq, max_freq)

  plt.figure(figsize=(8, 2))
  bins = np.linspace(min(freqs), np.percentile(freqs, 99), 40)

  plt.hist(freqs, bins=bins, edgecolor='black')
  plt.xlabel('Frequency')
  plt.ylabel('Count')
  plt.title(f'Word Frequency Distribution {title}')
  plt.show()

  cur.close()


def num_distribution(tables, conn):
  cur = conn.cursor()
  fig, axs = plt.subplots(len(tables), figsize=(10, 6))

  for i, table in enumerate(tables):
    query = f"SELECT num, COUNT(*) AS count FROM {table} GROUP BY num ORDER BY num;"
    df = pd.read_sql_query(query, conn)

    # Check if there are more than 10 unique 'num' values.
    if len(df['num'].unique()) > 10:
      # Identify the 10th smallest 'num'.
      cutoff = sorted(df['num'].unique())[9]

      # Combine counts of 'num' values larger than cutoff.
      count_sum = df[df['num'] > cutoff]['count'].sum()
      df = df[df['num'] <= cutoff]

      # Append a row for the combined counts.
      df = df.append({'num': cutoff + 1, 'count': count_sum}, ignore_index=True)

    bars = axs[i].bar(df['num'], df['count'], edgecolor='black', label=table, alpha=0.75)
    for bar in bars:
      yval = bar.get_height()
      axs[i].text( bar.get_x() + bar.get_width() / 2.0, yval, int(yval), va='bottom', ha='center', fontsize=8)

    axs[i].set_xlabel('Nodes')
    axs[i].set_ylabel('Words count')
    axs[i].set_xticks(range(len(df['num'])))
    axs[i].set_ylim(0, df['count'].max() * 1.1)
    axs[i].legend()

  plt.tight_layout()
  plt.show()

  cur.close()


config = None
with open('config.json') as config_file:
  config = json.load(config_file)

conn = psycopg2.connect(** (config["database"] | {"database": "wikidump"}))

# words_distr("grams_freq_grp_a", "Group A", conn)
# words_distr("grams_freq_grp_b", "Group B", conn)
# words_distr("grams_freq_ungrp", "Ungrouped", conn)

num_distribution(['grams_freq_grp_a', 'grams_freq_grp_b', 'grams_freq_ungrp'], conn)

conn.close()
