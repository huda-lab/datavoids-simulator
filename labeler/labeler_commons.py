from __future__ import annotations
import json
import re

ENGLISH_WORD_AVG_CHARACTERS_LENGTH = 5


def check_for_duplicate_keys(pairs):
  obj = {}
  for key, value in pairs:
    if key in obj:
      raise ValueError(f'Duplicate key found: {key}')
    obj[key] = value
  return obj


def sanitize_extracted_text(txt):
  txt = re.sub(r'&[a-zA-Z0-9]+;', '', txt)  # remove html entities
  # txt = re.sub(r'[^a-zA-Z0-9;,.?!-]', ' ', txt) # remove non-alphanumeric characters
  # we remove non-alphanumeric characters except for the text sequence [...] that we use to merge
  # for multiple results that we find in the same place
  txt = re.sub(r'(\[(\.\.\.)\])|[^a-zA-Z0-9;,.:?!-\']',
               lambda m: m.group(1) if m.group(1) else ' ', txt)
  txt = re.sub(r'\s+', ' ', txt)  # remove multiple spaces
  txt = re.sub(r'\'+', '', txt)  # remove multiple single quotes
  txt = re.sub(r'([a-zA-Z0-9])\s+([.,])', r'\1\2', txt)  # remove spaces before punctuation
  txt = re.sub(r'^\b\w{1,2}\b\s+|\s+\b\w{1,2}\b$', '', txt)  # remove single characters
  return txt


def load_keywords_dataset(path):
  with open(path, "r") as f:
    return json.load(f, object_pairs_hook=check_for_duplicate_keys)
