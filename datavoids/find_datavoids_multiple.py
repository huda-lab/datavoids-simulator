from __future__ import annotations
from graph import Graph
import sys
import json
import time

if __name__ == "__main__":
  database_name = "wikidump"

  config_file_path = sys.argv[1] if len(sys.argv) > 1 else "config.json"
  config = None
  with open(config_file_path) as config_file:
    config = json.load(config_file)

  config["database"]["database"] = database_name

  graph = Graph(config)
  graph.connect()

  print("Datavoid search started")
  starting_time = time.perf_counter()
  graph.cursor.execute("drop table if exists datavoids_m")
  graph.conn.commit()
  graph.cursor.execute("select find_datavoids_m('bay', 'fre')")
  graph.conn.commit()

  finish_time = time.perf_counter()
  print("Time:", (finish_time - starting_time) / 60, "minutes")
  print("done")
