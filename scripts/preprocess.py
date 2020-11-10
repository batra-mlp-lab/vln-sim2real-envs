#!/usr/bin/env python3

''' Script to preprocess json file downloaded from Matterport space into format used
    by the Matterport3D Simulator. '''

import os
import json
import numpy as np
import math
import sys
from base64 import b64decode
from PIL import Image
from e2c import e2c

np.set_printoptions(formatter={'float': lambda x: "{0:0.3f}".format(x)})

JSON_INFILE = sys.argv[1]
JSON_OUTDIR = 'data/connectivity/'
IMG_OUTDIR = 'data/%s/matterport_skybox_images/'


# Downsized values used with Matterport3D Simulator
SKYBOX_WIDTH = 512
SKYBOX_HEIGHT = 512
CAMERA_HEIGHT = 1.36 # Set the approximate height of the matterport camera on the tripod
MAX_EDGE_DIST = 5.0 # Approximate, will be adjusted in check-connectivity step


def pose_matrix(rotation, position):

    # Rotate by -90 degrees around x axis
    # y <= -z
    # z <= y
    T = np.zeros((4,4))
    T[0,0] = 1
    T[2,1] = -1
    T[1,2] = 1
    T[0,3] = position[0]
    T[1,3] = -position[2]
    T[2,3] = position[1]
    T[3,3] = 1

    return T


def distance(pano_to_pos, id1, id2):
    pos1 = pano_to_pos[id1]
    pos2 = pano_to_pos[id2]
    dist = math.sqrt(sum([(x-y)*(x-y) for x,y in zip(pos1,pos2)]))
    return dist


def preprocess(filename):

    # Create output directories
    if not os.path.exists(JSON_OUTDIR):
        os.makedirs(JSON_OUTDIR)
    scanId = filename.split('/')[-1].split('.')[0]
    imgDir = IMG_OUTDIR % scanId
    if not os.path.exists(imgDir):
        os.makedirs(imgDir)
    print('Saving images to %s' % imgDir)

    with open(filename) as f:
        data = json.load(f)

    pano_seq = [i['image_id'] for i in data]
    conn = [] # connectivity output
    pano_to_pos = {}
    for item in data:
        pano_to_pos[item['image_id']] = item['sweep_position']

    for item in data:

        # Save equirectangular pano
        imFile = imgDir + item['image_id'] + '_equirectangular.jpg'
        data_uri = item['image']
        header, encoded = data_uri.split(",", 1)
        e = b64decode(encoded)
        with open(imFile, "wb") as f:
            f.write(e)

        # Convert equirectangular pano to skybox format for simulator
        e_img = np.array(Image.open(imFile))
        # 6 elements with keys 'F', 'R', 'B', 'L', 'U', 'D'
        cube = e2c(e_img, face_w=SKYBOX_WIDTH, mode='bilinear', cube_format='dict')
        cube_ims = [np.fliplr(cube['U']), np.fliplr(cube['B']), cube['L'],
                  cube['F'], np.fliplr(cube['R']), np.fliplr(np.flipud(cube['D']))]
        for i,face in enumerate(cube_ims):
            imFile = imgDir + item['image_id'] + ('_skybox%d_sami.jpg' % i)
            Image.fromarray(face).save(imFile, quality=95)

        newimg = np.concatenate(cube_ims, axis=1)
        imFile = imgDir + item['image_id'] + '_skybox_small.jpg'
        Image.fromarray(newimg).save(imFile, quality=95)

        # Save basic connectivity info
        neighbors = set(item['neighbors'])
        visible = []
        unobstructed = []
        for pano in pano_seq:
            if pano in neighbors:
                visible.append(True)
                unobstructed.append(distance(pano_to_pos, pano, item['image_id']) < MAX_EDGE_DIST)
            else:
                visible.append(False)
                unobstructed.append(False)

        # Save pose info
        pose = pose_matrix(item['sweep_rotation'],item['sweep_position'])

        conn.append({
            'image_id': item['image_id'],
            'pose': pose.flatten().tolist(),
            'unobstructed': unobstructed,
            'visible': visible,
            'height': CAMERA_HEIGHT,
            'included': True
        })

    jsonPath = JSON_OUTDIR + scanId + '_initial_connectivity.json'
    print('Saving json connectivity graph to %s' % jsonPath)
    with open(jsonPath, 'w') as f:
        json.dump(conn, f)

if __name__ == "__main__":

    preprocess(JSON_INFILE)
