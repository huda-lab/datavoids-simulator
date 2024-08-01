from __future__ import annotations
from graph import Graph
import sys
import json
import time


def find_datavoids(config, min_freq_a=0.2, min_freq_b=0.2, max_freq_ungrp=0.01,
                   ratio_t=2, ratio_k=5, rewrite_datavoids=False):
  graph = Graph(config)
  graph.connect()

  starting_time = time.perf_counter()

  # if the datavoids table not exists or rewrite_datavoids is true
  graph.cursor.execute("""
  select exists (
      select 1
      from information_schema.tables
      where table_schema = 'public'
      and table_name = 'datavoids'
      )
  """)
  datavoids_table_exists = graph.cursor.fetchone()[0]

  if not datavoids_table_exists or rewrite_datavoids:
    print("Datavoid search started")
    graph.cursor.execute("drop table if exists datavoids")
    graph.conn.commit()
    graph.cursor.execute("select find_datavoids('mit', 'dis')")
    graph.conn.commit()

  print("Updating ratio")
  graph.cursor.execute("select update_datavoids_ratio(%s, %s)", (ratio_k, ratio_t))
  graph.conn.commit()

  graph.cursor.execute("""
    select * from datavoids
    where ratio is not null
    and freq_group_a > {min_freq_a}
    and freq_group_b > {min_freq_b}
    and freq_ungrouped < {max_freq_ungrp}
    order by ratio desc
  """.format(min_freq_a=min_freq_a,
             min_freq_b=min_freq_b,
             max_freq_ungrp=max_freq_ungrp))
  datavoids = graph.cursor.fetchall()
  graph.close()

  finish_time = time.perf_counter()
  print("Time:", (finish_time - starting_time) / 60, "minutes")
  print("done")
  return datavoids


if __name__ == "__main__":
  config_file_path = sys.argv[1] if len(sys.argv) > 1 else "config.json"
  config = None
  with open(config_file_path) as config_file:
    config = json.load(config_file)

  config["database"]["database"] = "wikilite"

  res = find_datavoids(config)
  print(res)
