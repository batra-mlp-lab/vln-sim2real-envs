#!/usr/bin/env python


""" Takes a csv from AMT instruction follower task as input.
    Produces a json output for scoring """

import json
import csv
import random
from collections import defaultdict
import networkx as nx
import numpy as np

AMT_INPUT = 'data/AMT/Batch_3814841_batch_results.csv'
TEST_DATA_INPUT = 'data/AMT/coda_test2.json'
OUTPUT = 'data/R2R/coda_test.json'

def load_nav_graphs(scans):
    ''' Load connectivity graph for each scan '''

    def distance(pose1, pose2):
        ''' Euclidean distance between two graph poses '''
        return ((pose1['pose'][3]-pose2['pose'][3])**2\
          + (pose1['pose'][7]-pose2['pose'][7])**2\
          + (pose1['pose'][11]-pose2['pose'][11])**2)**0.5

    graphs = {}
    for scan in scans:
        with open('data/connectivity/%s_connectivity.json' % scan) as f:
            G = nx.Graph()
            positions = {}
            data = json.load(f)
            for i,item in enumerate(data):
                if item['included']:
                    for j,conn in enumerate(item['unobstructed']):
                        if conn and data[j]['included']:
                            positions[item['image_id']] = np.array([item['pose'][3],
                                    item['pose'][7], item['pose'][11]]);
                            assert data[j]['unobstructed'][i], 'Graph should be undirected'
                            G.add_edge(item['image_id'],data[j]['image_id'],weight=distance(item,data[j]))
            nx.set_node_attributes(G, values=positions, name='position')
            graphs[scan] = G
    return graphs

if __name__ == '__main__':
  
    G = load_nav_graphs(['yZVvKaJZghh'])['yZVvKaJZghh']
    distances = dict(nx.all_pairs_dijkstra_path_length(G))

    with open(TEST_DATA_INPUT) as f:
        data = json.load(f)

    print(len(data))

    error = []
    worker_error = defaultdict(list)
    keep_instr = defaultdict(list)

    with open(AMT_INPUT) as f:
        reader = csv.DictReader(f)
        for row in reader:
            ix = int(row['Input.ix'])
            item = data[ix]
            goal = item['path'][-1]
            predicted = []
            for s in row['Answer.traj'][2:-1].split('),('):
                elems = s.split(',')
                predicted.append((elems[0], float(elems[1]), float(elems[2])))

            err = distances[predicted[-1][0]][goal]
            keep_instr[tuple(item['path'])].append((err,ix))
            error.append(err)
            worker_error[row['WorkerId']].append(err)

            assert predicted[0][0] == data[ix]['path'][0], ix


    error = np.array(error)
    # Figure out which workers to bonus
    print('success rate %.3f' % np.mean(error <= 3.0))
    for k,v in worker_error.items():
        v = np.array(v)
        correct = v <= 3.0
        print('%s: %.3f, %d, bonus=%d' % (k, np.mean(correct), len(v), np.sum(correct)))

    keep_indices = []
    keep_error = []
    for k,v in keep_instr.items():
        v = sorted(v)
        for err,ix in v[:3]:
            keep_indices.append(ix)
            keep_error.append(err)
    keep_error = np.array(keep_error)
    print('filtered success rate %.3f, n=%d' % (np.mean(keep_error <= 3.0), len(keep_indices)))

    filtered_data = {}
    for i,ix in enumerate(keep_indices):
        item = data[ix]
        if tuple(item['path']) in filtered_data:
            filtered_data[tuple(item['path'])]['instructions'].append(item['instructions'])
        else:
            filtered_data[tuple(item['path'])] = {
                'distance': distances[item['path'][0]][item['path'][-1]],
                'scan': item['scan'],
                'path_id': None,
                'path': item['path'],
                'heading': item['heading'],
                'instructions': [item['instructions']]
            }

    final_data = []
    count = 0
    for k,v in filtered_data.items():
        v['path_id'] = count
        random.shuffle(v['instructions'])
        count += 1
        final_data.append(v)
    with open(OUTPUT, 'w') as f:
        json.dump(final_data,f)






