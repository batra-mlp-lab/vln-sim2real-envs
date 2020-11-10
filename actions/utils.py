import sys
import random
import json
import math
import numpy as np
import time

from collections import defaultdict
from itertools import zip_longest

random.seed(1)



DATA_DIR = "data/"
SIM_DIR = "../Matterport3DSimulator/"
EXAMPLE_DIR = "examples/"
IMAGENET_FEATURES = ['../Matterport3DSimulator/img_features/ResNet-152-imagenet.tsv']

SCAN_HEIGHT = 0.24 # Height above floor in meters
ALLOWED_HEIGHT_DIFF = 0.1 # Neighbor scans must be on the same floor level to be reachable for a robot

HEADING_BINS = 48
HEADING_BIN_WIDTH = 2*math.pi/HEADING_BINS
RANGE_BINS = 24
RANGE_BIN_WIDTH = 0.2
MAX_RANGE = RANGE_BINS*RANGE_BIN_WIDTH


def read_img_features(feature_stores=IMAGENET_FEATURES):
    import csv
    csv.field_size_limit(sys.maxsize)
    import base64
    from tqdm import tqdm

    views = 36
    tsv_fieldnames = ['scanId', 'viewpointId', 'image_w', 'image_h', 'vfov', 'features']
    features = defaultdict(list)
    for feature_store in feature_stores:
      print("Start loading image features from %s" % feature_store)
      start = time.time()
      with open(feature_store, "r") as tsv_in_file:     # Open the tsv file.
          reader = csv.DictReader(tsv_in_file, delimiter='\t', fieldnames=tsv_fieldnames)
          for item in reader:
              long_id = item['scanId'] + "_" + item['viewpointId']
              features[long_id].append(np.frombuffer(base64.decodestring(item['features'].encode('ascii')),
                                                     dtype=np.float32).reshape((views, -1)))   # Feature of long_id is (36, 2048)

      print("Finish Loading the image features from %s in %0.4f seconds" % (feature_store, time.time() - start))
    return features



def load_data(splits, visualize=False, verbose=False):
    ''' Load training / val data of laser scans plus heading and range to nearby waypoints '''

    # Load scenes
    scenes = []
    for split in splits:
        scenes_file_path = "splits/scenes_" + split + ".txt"
        with open(scenes_file_path) as f:
            for line in f:
                scenes.append(line.strip())

    # Load navigation graph connectivity info
    nb = {}
    for scene in scenes:
        nb[scene] = defaultdict(list)
        with open(SIM_DIR + 'connectivity/%s_connectivity.json' % scene) as f:
            data = json.load(f)
            for i,item in enumerate(data):
                if item['included']:
                    for j,conn in enumerate(item['unobstructed']):
                        if conn and data[j]['included']:
                            nb[scene][item['image_id']].append(data[j]['image_id'])

    # Load generated laser scan data
    degree = []
    dist = []
    dataset = []
    for scene in scenes:
        laser_path = DATA_DIR + scene + "/laser_scans.json"
        with open(laser_path) as jf:
            json_data = json.load(jf)

            # Build lookup by id
            scans = {}
            for item in json_data:
                scans[item['image_id']] = item

            # Identify neighbors to use as targets
            for item in json_data:
                target_heading = []
                target_range = []
                for n_id in nb[scene][item['image_id']]:
                    if n_id in scans: # Some were missed if we couldn't identify floor level
                        height_diff = item['position']['z'] - scans[n_id]['position']['z']
                        item_range = distance(item['position'], scans[n_id]['position'])
                        if abs(height_diff) < ALLOWED_HEIGHT_DIFF and item_range < MAX_RANGE:
                            # Heading from centre of scan, right is positive, in range -pi to +pi
                            target_heading.append(heading(item['position'], scans[n_id]['position']))
                            target_range.append(item_range)
                degree.append(len(target_heading))
                if target_heading:
                    dist += target_range
                    item['laser'] = np.array(item['laser'])
                    item['target_heading'] = np.array(target_heading)
                    item['target_range'] = np.array(target_range)
                    dataset.append(item)

                    img = radial_occupancy(item['laser'])
                    if visualize:
                        target = radial_target(item['target_heading'], item['target_range'])
                        visualize_scan(img, target)

    if verbose:
        print("Loaded %d scans from %d scenes" % (len(dataset), len(scenes)))
        print("Average of %.1f targets per scan" % np.average(np.array(degree)))

        print("\nHistogram of range\nBin\tFreq")
        freqs,bins = np.histogram(np.array(dist), bins=20, range=(0,5), density=True)
        for f,b in zip(freqs,bins):
            print('%.2fm\t%.2f' % (b,f/np.sum(freqs)))

    random.shuffle(data)
    return dataset


def polar_bins_to_cartesian(range_bin, heading_bin):
    radius = (range_bin+0.5)*RANGE_BIN_WIDTH
    heading = (heading_bin+0.5)*HEADING_BIN_WIDTH
    x = radius * math.cos(heading)
    y = radius * math.sin(heading)
    return (x,y)  


def bin_distance(range_bin1, heading_bin1, range_bin2, heading_bin2):
    ''' Distance in meters between two radial cells '''
    x1, y1 = polar_bins_to_cartesian(range_bin1, heading_bin1)
    x2, y2 = polar_bins_to_cartesian(range_bin2, heading_bin2)
    dist = math.sqrt((x1 - x2)**2 + (y1 - y2)**2)
    return dist


def radial_cost_matrix():
    ''' Return a (1, RANGE_BINS*HEADING_BINS, RANGE_BINS*HEADING_BINS) cost
        matrix.'''
    C = np.zeros((1, RANGE_BINS, HEADING_BINS, RANGE_BINS, HEADING_BINS))
    for r1 in range(RANGE_BINS):
      for h1 in range(HEADING_BINS):
        for r2 in range(RANGE_BINS):
          for h2 in range(HEADING_BINS):
            C[0, r1, h1, r2, h2] = bin_distance(r1, h1, r2, h2)
    return C.reshape(1, RANGE_BINS*HEADING_BINS, RANGE_BINS*HEADING_BINS)


def visualize_pred(scan, pred, gt, equi, i):
    ''' scan (4, RANGE_BINS, HEADING_BINS), pred (1, RANGE_BINS, HEADING_BINS) '''

    import matplotlib as mpl
    mpl.use('Agg')
    import matplotlib.pyplot as plt

    fig, axs = plt.subplots(2, 2)

    # Laser scan
    scan = scan.cpu().numpy().transpose((1,2,0))[:,:,1]
    axs[0][0].imshow(scan*-1, origin='lower', interpolation='none', cmap='viridis')
    x_positions = np.arange(-.5, HEADING_BINS, 12)
    x_step = int(12*360/HEADING_BINS)
    x_labels = np.arange(-180, 180+x_step, x_step)
    axs[0][0].set_xticks(x_positions, minor=False)
    axs[0][0].set_xticklabels(x_labels, fontdict=None, minor=False)

    y_positions = np.arange(-.5, RANGE_BINS, 8)
    y_labels = np.arange(0, (RANGE_BINS+1)*8*RANGE_BIN_WIDTH, 8*RANGE_BIN_WIDTH)
    y_labels = np.round(y_labels,decimals=1)
    axs[0][0].set_yticks(y_positions, minor=False)
    axs[0][0].set_yticklabels(y_labels, fontdict=None, minor=False)

    axs[0][0].set_ylabel('Range (m)')
    axs[0][0].set_title('Laser Scan')

    # Predictions
    pred = pred.cpu().numpy().transpose((1,2,0)).squeeze(2)
    axs[1][0].imshow(pred, cmap='hot', origin='lower', interpolation='none')
    axs[1][0].set_xticks(x_positions, minor=False)
    axs[1][0].set_xticklabels(x_labels, fontdict=None, minor=False)
    axs[1][0].set_yticks(y_positions, minor=False)
    axs[1][0].set_yticklabels(y_labels, fontdict=None, minor=False)
    axs[1][0].set_title('Subgoal Prediction')
    axs[1][0].set_xlabel('Heading (deg)')
    axs[1][0].set_ylabel('Range (m)')

    # Equirectangular image
    axs[0][1].imshow(equi)
    axs[0][1].set_title('Image')
    image_x_positions = np.arange(0, equi.shape[1]+1, equi.shape[1]/(HEADING_BINS/12))
    axs[0][1].set_xticks(image_x_positions, minor=False)
    axs[0][1].set_xticklabels(x_labels, fontdict=None, minor=False)
    axs[0][1].set_yticklabels([])
    axs[0][1].set_yticks([])

    # Ground truth
    gt = gt.cpu().numpy().transpose((1,2,0)).squeeze(2)
    axs[1][1].imshow(gt, cmap='Oranges', origin='lower', interpolation='none')
    axs[1][1].set_xticks(x_positions, minor=False)
    axs[1][1].set_xticklabels(x_labels, fontdict=None, minor=False)
    axs[1][1].set_yticks(y_positions, minor=False)
    axs[1][1].set_yticklabels(y_labels, fontdict=None, minor=False)

    axs[1][1].set_title('Subgoal Ground-Truth')
    axs[1][1].set_xlabel('Heading (deg)')

    # Legend
    from matplotlib.patches import Patch
    cmap = mpl.cm.get_cmap('viridis')
    legend_elements = [Patch(color=cmap(1.0), label='Free'),
                       Patch(color=cmap(0.0), label='Occupied'),
                       Patch(color=cmap(0.5), label='Unknown')]
    axs[0][0].legend(handles=legend_elements, fontsize='small', loc='lower center', 
                      bbox_to_anchor=(0.5, -0.5), fancybox=False, shadow=False, ncol=3,
                      handletextpad=0.3)

    fig.savefig('%spred-%d.png' % (EXAMPLE_DIR,i), dpi=300)
    plt.close()


def visualize_scan(scan):
    import matplotlib.pyplot as plt

    plt.imshow(scan[:,:,0]*-1, origin='lower', interpolation='none', cmap='viridis')
    x_positions = np.arange(-.5, HEADING_BINS, 4)
    x_step = int(4*360/HEADING_BINS)
    x_labels = np.arange(-180, 180+x_step, x_step)
    plt.xticks(x_positions, x_labels)

    y_positions = np.arange(-.5, RANGE_BINS, 4)
    y_labels = np.arange(0, (RANGE_BINS+1)*4*RANGE_BIN_WIDTH, 4*RANGE_BIN_WIDTH)
    y_labels = np.round(y_labels,decimals=1)
    plt.yticks(y_positions, y_labels)

    plt.xlabel('Heading (deg)')
    plt.ylabel('Range (m)')

    plt.waitforbuttonpress() 


def normalize_angle(angle):
    ''' Normalized from -pi to +pi. '''
    # reduce the angle  
    angle =  angle % (2*math.pi)

    # force it to be the positive remainder, so that 0 <= angle < 360  
    angle = (angle + (2*math.pi)) % (2*math.pi)

    # force into the minimum absolute value residue class, so that -180 < angle <= 180  
    if angle > math.pi:
        angle -= (2*math.pi)
    return angle


def heading(pos1, pos2):
    ''' Heading from pos1 to pos2. Matching the simulator, heading is defined 
        from the y-axis with the z-axis up (turning right is positive).'''
    return normalize_angle(math.pi/2.0 - math.atan2(pos2['y']-pos1['y'], pos2['x']-pos1['x']))


def distance(pos1, pos2):
    ''' Euclidean distance between two positions '''
    return ((pos1['x']-pos2['x'])**2 + (pos1['y']-pos2['y'])**2 + (pos1['z']-pos2['z'])**2)**0.5


def radial_target(heading, dist):
    ''' Convert heading and distance values to radial encoding'''
    assert heading.shape == dist.shape
    assert len(heading) > 0
    output = np.zeros((RANGE_BINS, HEADING_BINS, 1)) # rows, cols, channels
    valid = np.logical_and(dist>0, dist<MAX_RANGE)
    dist = dist[valid]
    heading = heading[valid]

    # Heading zero should be the middle of the array  
    heading_bins = np.arange(HEADING_BIN_WIDTH*-HEADING_BINS/2, 
                             HEADING_BIN_WIDTH*(HEADING_BINS/2+1), HEADING_BIN_WIDTH)
    range_bins = np.arange(0, RANGE_BIN_WIDTH*(RANGE_BINS+1), RANGE_BIN_WIDTH)

    x = np.digitize(heading, heading_bins)-1
    y = np.digitize(dist, range_bins)-1

    output[y,x] = 1
    return output


def radial_occupancy(scan):
    ''' Convert an 1D array of 360 degree range scans to a 2D array representing
    a radial occupancy map. Output values are: 1: occupied, -1: free,
    0: unknown. Using 0 as unknown is helpful for using dropout and padding. '''
    output = np.zeros((RANGE_BINS, HEADING_BINS, 1)) # rows, cols, channels
    range_bins = np.arange(0, RANGE_BIN_WIDTH*(RANGE_BINS+1), RANGE_BIN_WIDTH)
    # chunk scan data to generate occupied (value 1)
    assert scan.size % HEADING_BINS == 0
    chunk_size = scan.size//HEADING_BINS
    args = [iter(scan)] * chunk_size
    n = 0
    for chunk in zip_longest(*args):
        chunk = np.array(chunk)
        output[:,n,0],_ = np.histogram(chunk, bins=range_bins)
        n+=1
    output = np.clip(output, 0, 1)
    # free (index 1)
    free_ix = np.flip(np.cumsum(np.flip(output[:,:,0],axis=0), axis=0), axis=0)[1:,:] > 0
    output[:-1,:,0][free_ix] = -1
    return output



if __name__ == "__main__":

    # Plot the laser scan of a particular viewpoint
    with open('/home/peter/Data/mp3d/v1/scans/yZVvKaJZghh/laser_scans.json') as jf:
      json_data = json.load(jf)
      # Build lookup by id
      scans = {}
      for item in json_data:
        laser = np.array(item['laser'])

        # missing part of scan
        length = len(laser)
        miss_start = random.randint(0, length)
        miss_end = miss_start + int((360-270)/360 * length)
        laser[miss_start:miss_end] = -1
        if miss_end >= length:
            laser[:miss_end-length] = -1

        # dropout. Unlike conventional dropout, this occurs at both train and test time and is 
        # considered to represent missing return values in the laser scan.
        drop = np.random.random_sample((len(laser),))
        laser[drop < 0.05] = -1  # Indicates missing return.

        scans[item['image_id']] = laser
    scan = radial_occupancy(scans['b1914edca2984f0a91c56de9159f948d'])
    visualize_scan(scan)



