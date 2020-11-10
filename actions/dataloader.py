import os
import sys
import random
import math
import numpy as np


from utils import load_data, radial_target, radial_occupancy, HEADING_BINS, RANGE_BINS, normalize_angle
random.seed(1)


class DataLoader:
    """ Class to handle data loading, data augmentation and batch sampling """

    def __init__(self, features, splits=['train'], bs=1, augment=False, dropout=0, laser_fov_deg=270):

        self.splits = splits
        self.batch_size = bs
        self.augment = augment
        self.dropout = dropout
        self.laser_fov_deg = laser_fov_deg

        self.data = load_data(splits)
        random.shuffle(self.data)
        self.reset_epoch()
        print('Loaded %d data tuples from %s' % (len(self.data), self.splits))

        for item in self.data:
            long_id = item['scan'] + "_" + item['image_id']
            # reshape to 12 near range views, 12 medium range views, and 12 ceiling views
            # roll so zero in the middle of the scan (although actually out by 0.5 grid cells)
            item['features'] = []
            for feature_version in features[long_id]:
                item['features'].append(np.roll(feature_version.reshape(3,12,2048), 6, axis=1))
            # which is 15 degrees, so we rotate scan and heading by that much
            item['target_heading'] = np.array([normalize_angle(h + math.pi/12) for h in item['target_heading']])
            item['laser'] = np.roll(item['laser'], int(len(item['laser'])/24))

    def reset_epoch(self):
        """ Reset the data index to beginning of epoch. Primarily for testing. """
        self.ix = 0


    def _next_minibatch(self):
        """ Internal function to sample next random minibatch """
        batch = self.data[self.ix:self.ix+self.batch_size]
        if len(batch) < self.batch_size:
            random.shuffle(self.data)
            self.ix = self.batch_size - len(batch)
            batch += self.data[:self.ix]
        else:
            self.ix += self.batch_size
        self.batch = batch


    def get_batch(self):
        """ Prepare next batch for consumption """
        self._next_minibatch()
        scans = np.empty((self.batch_size, 2, RANGE_BINS, HEADING_BINS), dtype=np.float32)
        targets = np.empty((self.batch_size, 1, RANGE_BINS, HEADING_BINS), dtype=np.float32)
        features = np.empty((self.batch_size, 2048, 3, 12), dtype=np.float32)

        long_ids = []
        assert len(self.batch) == self.batch_size
        for n,item in enumerate(self.batch):
            long_ids.append(item['scan'] + "_" + item['image_id'])
            # Select one feature if there are multiple versions
            selected_features = random.choice(item['features'])

            if self.augment:
                # random rotation by a 30 degree increment
                rotation = random.randint(0,12)
                ix = int(len(item['laser'])/12*rotation)
                laser = np.roll(item['laser'], ix) # end rolls around to start
                tgt_heading = np.array([normalize_angle(h + (math.pi/6)*rotation) for h in item['target_heading']])
                feat = np.roll(selected_features, rotation, axis=1)
            else:
                laser = np.array(item['laser'], copy=True)
                tgt_heading = item['target_heading']
                feat = selected_features

            # missing part of scan
            length = len(laser)
            miss_start = random.randint(0, length)
            miss_end = miss_start + int((360-self.laser_fov_deg)/360 * length)
            laser[miss_start:miss_end] = -1
            if miss_end >= length:
                laser[:miss_end-length] = -1

            # dropout. Unlike conventional dropout, this occurs at both train and test time and is 
            # considered to represent missing return values in the laser scan.
            drop = np.random.random_sample((len(laser),))
            laser[drop < self.dropout] = -1  # Indicates missing return.

            scans[n, 1, :, :] = radial_occupancy(laser).transpose((2,0,1))
            # add a range indicating channel
            r = np.linspace(-0.5, 0.5, num=RANGE_BINS)
            scans[:,0,:,:] = np.expand_dims(np.expand_dims(r, axis=0), axis=2)
            targets[n, :, :, :] = radial_target(tgt_heading, item['target_range']).transpose((2,0,1))
            features[n, :, :, :] = feat.transpose((2,0,1))
        # features = np.zeros_like(features)  # How does it work without image features?
        # scans = np.zeros_like(scans)  # How does it work with only image features?
        # Normalize targets into a probability dist
        targets /= targets.reshape(targets.shape[0], -1).sum(axis=1).reshape(-1, 1, 1, 1)
        return scans, features, targets, long_ids
