#!/usr/bin/env python3


""" Takes a csv from AMT instruction annotation as input.
    Produces a json output formatting for use with AMT eval-hit.html """

import json
import csv
import random
from collections import defaultdict

PATHS = 'data/yZVvKaJZghh/sample_room_paths.json'
AMT_INPUT = 'data/AMT/Batch_3814726_batch_results.csv'
AMT_OUTPUT = 'data/AMT/coda_test2.json'

if __name__ == '__main__':

  ix_to_instr = defaultdict(list)
  count = 0

  with open(AMT_INPUT) as f:
    reader = csv.DictReader(f)
    for row in reader:
      ix_to_instr[int(row['Input.ix'])].append(row['Answer.tag1'])
      count += 1

  print('Loaded %d trajectories and %d instructions from csv' % (len(ix_to_instr), count))

  amt_data = []
  with open(PATHS) as f:
    data = json.load(f)
    for k,v in data.items():
      ix = v['path_id']
      v['instructions'] = ix_to_instr[ix]

      for instr in ix_to_instr[ix]:
        amt_data.append({
          'scan': v['scan'],
          'path': v['path'],
          'instructions': instr,
          'heading': v['heading']
        })

  print('Saved %d items to json output at: %s' % (len(amt_data), AMT_OUTPUT))
  print('Output format:')
  print(amt_data[0])
  print(amt_data[1])

  random.seed(1)
  random.shuffle(amt_data)
  with open(AMT_OUTPUT, 'w') as f:
    json.dump(amt_data,f)
