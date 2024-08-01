#
# This script generates a random graph and loads it into the database.
# Usage example:
# python loaders/random_generator.py mis_example3 50 100 d:0.5,m:0.1,n:0.4 n:d,m:d

import csv
import math
import psycopg2
import json
import random


# generate a random number that respects the proportions in group_proportions
def generate_group(groups_proportions):
  r = random.random()
  for group in groups_proportions:
    if r <= groups_proportions[group]:
      return group
    r -= groups_proportions[group]
  raise Exception("This should never happen")


def check_edge_not_to_be_avoided(src, des, avoid_edges, cursor):
  cursor.execute("SELECT grp FROM nodes WHERE id = %s", (src,))
  src_grp = cursor.fetchone()[0]
  cursor.execute("SELECT grp FROM nodes WHERE id = %s", (des,))
  des_grp = cursor.fetchone()[0]

  for edge in avoid_edges.items():
    if edge[0] == src_grp and edge[1] == des_grp:
      return False

  return True


def generate_and_load(number_of_nodes, number_of_edges, groups_proportions, avoid_edges, config):
  if "database" not in config["database"]:
    raise Exception("database config not found")

  print("Connecting to database...")
  conn = psycopg2.connect(**config["database"])
  cursor = conn.cursor()

  print("Deleting old data...")
  cursor.execute("DELETE FROM edges")
  cursor.execute("DELETE FROM nodes")

  conn.commit()

  print("Loading nodes...")
  for i in range(number_of_nodes):
    cursor.execute("""
      INSERT INTO nodes (id, url, content, grp, active)
      VALUES (%s, %s, %s, %s, %s)
    """, (i, f"u{i}", f"c{i}", generate_group(groups_proportions), True))
    conn.commit()

  for i in range(number_of_edges):

    exists = True
    while exists:
      src = math.floor(random.random() * number_of_nodes)
      des = math.floor(random.random() * number_of_nodes)

      # make sure that the edge is not a loop
      if src == des:
        continue

      if not check_edge_not_to_be_avoided(src, des, avoid_edges, cursor):
        continue

      # check if the edge already exists
      cursor.execute("SELECT * FROM edges WHERE src = %s AND des = %s", (src, des))
      if cursor.fetchone() is None:
        exists = False

    cursor.execute("""
      INSERT INTO edges (src, des)
      VALUES (%s, %s)
    """, (src, des))
    conn.commit()

  cursor.close()
  conn.close()


if __name__ == '__main__':
  import sys

  config = None
  with open('config.json') as config_file:
    config = json.load(config_file)

  # get the path to the dump file from the command line
  if len(sys.argv) != 6:
    print("Usage: python3 random_generator.py db_name number_of_nodes number_of_edges groups_proportions avoid_edges")
    exit(1)

  print("Database name: " + sys.argv[1])
  config["database"]["database"] = sys.argv[1]

  number_of_nodes = int(sys.argv[2])
  print("Number of nodes: " + str(number_of_nodes))

  number_of_edges = int(sys.argv[3])
  print("Number of edges: " + str(number_of_edges))

  group_proportions = {a.split(":")[0]: float(a.split(":")[1]) for a in sys.argv[4].split(",")}

  if sum(group_proportions.values()) != 1:
    raise Exception("The sum of group_proportions values must be 1")

  print("Group Proportions:")
  for group in group_proportions:
    print(" " + group + ":", group_proportions[group])

  avoid_edges = {a.split(":")[0]: a.split(":")[1] for a in sys.argv[5].split(",")}
  print("Avoid edges: " + str(avoid_edges))

  generate_and_load(number_of_nodes, number_of_edges, group_proportions, avoid_edges, config)

  print("Done.")
