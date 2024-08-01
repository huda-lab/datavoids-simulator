import os
import glob
import psycopg2
import json

STOP_WORDS_DIR = "data/stopwords"

config = None
with open('config.json') as config_file:
  config = json.load(config_file)

conn = psycopg2.connect(** (config["database"]))
cursor = conn.cursor()

cursor.execute("""
  create table if not exists stopwords (
    word text primary key
  )
""")

cursor.execute("""
  create temporary table temp_stopwords (
    word text
  )
""")

conn.commit()

for file_name in glob.glob(STOP_WORDS_DIR + '/*.txt'):
  with open(file_name, 'r') as file:
    for line in file:
      word = line.strip()
      cursor.execute("insert into temp_stopwords (word) values (%s)", (word,))

cursor.execute("""
  insert into stopwords (word)
  select distinct word
  from temp_stopwords
  on conflict (word) do nothing
""")

conn.commit()
cursor.close()
conn.close()
