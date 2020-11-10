#!/usr/bin/env python3

''' Calculate basic statistics for the coda trajectories and instruction annotations. '''

import os
import json
import numpy as np
import math
import networkx as nx
import re
import string

INSTR_FILE = 'data/R2R/R2R_coda.json'
CONN_FILE = 'data/R2R/yZVvKaJZghh_connectivity.json'
SENTENCE_SPLIT_REGEX = re.compile(r'(\W+)') # Split on any non-alphanumeric character

def distance(pose1, pose2):
  ''' Euclidean distance between two graph poses '''
  return ((pose1['pose'][3]-pose2['pose'][3])**2\
    + (pose1['pose'][7]-pose2['pose'][7])**2\
    + (pose1['pose'][11]-pose2['pose'][11])**2)**0.5


def load_graph(infile):
  ''' Build a graph from a connectivity json file '''
  G = nx.Graph()
  with open(infile) as f:
    data = json.load(f)
    for i,item in enumerate(data):
      if item['included']:
        for j,conn in enumerate(item['unobstructed']):
          if conn and data[j]['included']:
            assert data[j]['unobstructed'][i], 'Graph should be undirected'
            G.add_edge(item['image_id'],data[j]['image_id'],weight=distance(item,data[j]))
  return G


def split_sentence(sentence):
    ''' Break sentence into a list of words and punctuation '''
    toks = []
    for word in [s.strip().lower() for s in SENTENCE_SPLIT_REGEX.split(sentence.strip()) if len(s.strip()) > 0]:
        # Break up any words containing punctuation only, e.g. '!?', unless it is multiple full stops e.g. '..'
        if all(c in string.punctuation for c in word) and not all(c in '.' for c in word):
            toks += list(word)
        else:
            toks.append(word)
    return toks


def statistics(file):
    graph = load_graph(CONN_FILE)
    
    print('Num viewpoints %d' % len(graph))
    avg_degree = np.array([item[1] for item in graph.degree()]).mean()
    print('Graph degree %.1f' % avg_degree)
    avg_edge = np.array([edge[2] for edge in graph.edges(data='weight')]).mean()
    print('Edge distance %.1f' % avg_edge)
    
    words = []
    steps = []
    dist = []
    with open(file) as f:
        data = json.load(f)
    for item in data:
        for instr in item['instructions']:
        	 words.append(len(split_sentence(instr)))
        steps.append(len(item['path'])-1)
        dist.append(item['distance'])

    print('Words %.1f' % np.array(words).mean())
    print('Length %.1f' % np.array(dist).mean())
    print('Steps %.1f' % np.array(steps).mean())
    print('Total distance %.1f' % (np.array(dist).sum()*3))
        

if __name__ == "__main__":

    statistics(INSTR_FILE)