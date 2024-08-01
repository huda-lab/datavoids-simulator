import csv
import psycopg2
import json


def load_csv_files(nodes_csv_file, edges_csv_file, config):
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
  with open(nodes_csv_file, 'r') as nodes_file:
    nodes_reader = csv.reader(nodes_file)
    header = nodes_reader.__next__()
    col_pos = dict()
    for (i, col) in enumerate(header):
      col_pos[col] = i
    for row in nodes_reader:
      row = (
          int(row[col_pos['id']]),
          row[col_pos['url']],
          row[col_pos['content']],
          row[col_pos['grp']],
          int(row[col_pos['active']]) == 1
      )
      cursor.execute(
          "INSERT INTO nodes (id, url, content, grp, active) VALUES (%s, %s, %s, %s, %s)", row)
      conn.commit()

  print("Loading edges...")
  with open(edges_csv_file, 'r') as edges_file:
    edges_reader = csv.reader(edges_file)
    header = edges_reader.__next__()
    col_pos = dict()
    for (i, col) in enumerate(header):
      col_pos[col] = i
    for row in edges_reader:
      row = (int(row[col_pos['src']]), int(row[col_pos['des']]))
      cursor.execute("INSERT INTO edges (src, des) VALUES (%s, %s)", row)
      conn.commit()

  cursor.close()
  conn.close()


if __name__ == '__main__':
  import sys

  config = None
  with open('config.json') as config_file:
    config = json.load(config_file)

  # get the path to the dump file from the command line
  if len(sys.argv) < 3:
    print("Usage: python3 load_from_csv.py db_name <path to nodes csv file> <path to edges csv file>")
    exit(1)

  print("loading from csv files...")

  print("Database name: " + sys.argv[1])
  config["database"]["database"] = sys.argv[1]

  print("Nodes csv file: " + sys.argv[2])
  nodes_csv_file = sys.argv[2]

  print("Edges csv file: " + sys.argv[3])
  edges_csv_file = sys.argv[3]

  load_csv_files(nodes_csv_file, edges_csv_file, config)

  print("Done.")
