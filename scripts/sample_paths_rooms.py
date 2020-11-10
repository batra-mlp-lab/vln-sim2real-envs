#!/usr/bin/env python3

import json
import math
import networkx as nx
import numpy as np
import matplotlib.pyplot as plt
import pprint
from collections import defaultdict
import random

pp = pprint.PrettyPrinter(depth=6)


CONNECTION_DIR = 'data/connectivity/'
CONNFILE = '%s%s_connectivity.json'
CONFIG = 'web/config.json'
OUTFILE = 'data/%s/sample_room_paths.json'

def distance(pose1, pose2):
  ''' Euclidean distance between two graph poses '''
  return ((pose1['pose'][3]-pose2['pose'][3])**2\
    + (pose1['pose'][7]-pose2['pose'][7])**2\
    + (pose1['pose'][11]-pose2['pose'][11])**2)**0.5


def open_graph(scan_id):
  ''' Build a graph from a connectivity json file '''

  infile = CONNFILE % (CONNECTION_DIR,scan_id)
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


def load_region_to_panos(scan_id, graph):
  region_to_panos = defaultdict(list)
  infile = CONNFILE % (CONNECTION_DIR,scan_id)
  with open(infile) as f:
    data = json.load(f)
    for i,item in enumerate(data):
      if item['included']:
        region_to_panos[int(item['roomId'])].append(item['image_id'])
  return region_to_panos


def sample_scan(scan, min_hops, max_hops, min_dist):
  data_paths = []
  # Load graph and find shortest paths
  g = open_graph(scan)
  if len(g.nodes()) < 30 and min_hops > 3:
    min_hops = 3
  paths = dict(nx.all_pairs_dijkstra_path(g))
  dists = dict(nx.all_pairs_dijkstra_path_length(g))

  # Associate panos to regions (rooms)
  region_to_panos = load_region_to_panos(scan, g)
  
  # Don't stop on entering a room unless we have a good view (i.e. a well connected node)
  region_to_stopping_panos = defaultdict(list)
  for region_index, panos in region_to_panos.items():
    degrees = [g.degree(pano) for pano in panos]
    mean_deg = np.average(degrees)
    region_to_stopping_panos[region_index] = [pano for pano in panos if (g.degree(pano) > 2 or g.degree(pano) > mean_deg)]

  # Now sample all pairs of rooms for a good path
  for start_region, start_panos in region_to_panos.items():
    for goal_region, goal_panos in region_to_stopping_panos.items():
      valid_path_distances = []
      if start_region == goal_region:
        # Include a path that starts and ends in the same room if it's long enough
        for start in start_panos:
          for goal in goal_panos:
            dist = dists[start][goal]
            path = paths[start][goal]
            num_hops = len(path)-1
            if (dist >= min_dist and num_hops >= min_hops and num_hops <= max_hops):
              valid_path_distances.append((path,dist))
      else:
        # Navigation is to a different room
        for start in start_panos:
          # For each start, go to the nearest position in the other room
          nearest_goal = None
          nearest_dist = None
          for goal in goal_panos:
            dist = dists[start][goal]
            if not nearest_dist or dist < nearest_dist:
              nearest_dist = dist
              nearest_goal = goal
          # Check if selected path is valid
          if nearest_goal:
            path = paths[start][nearest_goal]
            num_hops = len(path)-1
            if (nearest_dist >= min_dist and num_hops >= min_hops and num_hops <= max_hops):
              valid_path_distances.append((path,nearest_dist))
      # Sample a valid path from start_region to goal_region
      if valid_path_distances:
        # Keep 10% if not moving room-to-room
        num_samples = math.ceil(math.log(len(valid_path_distances)+1)) if start_region == goal_region else 1
        samples = np.random.choice(len(valid_path_distances), size=int(num_samples), replace=False)
        for idx in samples:
          p = valid_path_distances[idx][0]
          d = valid_path_distances[idx][1]
          data_paths.append({
            'scan': scan,
            'path': p,
            'distance': d,
            'heading': np.random.uniform(0, 2*math.pi), # Randomly select initial heading
            'start_region': start_region,
            'goal_region': goal_region
          })
          print(data_paths[-1]['heading'])
  num_nodes = len(g.nodes())
  print('%s, Num paths / viewpoints / rooms: %d / %d / %d' % (scan, len(data_paths), num_nodes, len(region_to_panos)))
  np.random.shuffle(data_paths)
  return data_paths


def plot(data_paths):
  # plot metres
  lengths = np.array([item['distance'] for item in data_paths])
  print('Average trajectory length: %.2f' % np.average(lengths))
  plt.figure(figsize=(3.0,3.0))
  plt.hist(lengths, bins=range(25), color='orangered', normed=True, alpha=0.8)  # arguments are passed to np.histogram
  plt.axvline(lengths.mean(), color='black', linestyle='dashed', linewidth=1)
  plt.title("Trajectory Length")
  plt.xlim([0,25])
  plt.xlabel('m')
  #plt.ylabel('Frequency')
  plt.tight_layout()
  plt.show()


def average_degree(scan):
  g = open_graph(scan)
  degrees = list(dict(g.degree()).values())
  viewpoints = len(degrees)
  print('Scan: %s' % scan)
  print('Num viewpoints: %d' % len(degrees))
  print('Avg vertex degree: %.1f' % np.mean(degrees))


if __name__ == '__main__':

  np.random.seed(10)

  min_dist=5
  min_hops=4
  max_hops=6
  max_from_scene=100

  with open(CONFIG) as f:
    cfg = json.load(f)
    scan = cfg["scanId"]
    average_degree(scan)
    data_paths = sample_scan(scan, min_hops, max_hops, min_dist)
    data_paths = data_paths[:max_from_scene]

  np.random.shuffle(data_paths)
  print('Generated %d paths' % (len(data_paths)))
  data_dict = {}
  for i,item in enumerate(data_paths):
      item['path_id'] = i
      data_dict[str(i)] = item
  outfile = OUTFILE % (scan)
  with open(outfile, 'w') as f:
    json.dump(data_dict, f, indent=2)
    print('Saved to %s' % outfile)
  plot(data_paths)


