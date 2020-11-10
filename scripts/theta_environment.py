#!/usr/bin/env python3


""" This script constructs an environment from panos taken with the Ricoh Theta V, to create a matching
    environment for an existing Matterport reconstruction. The theta panos should be captured in the same
    order as viewpoints appear in <EXISTING-ENV>_connectivity.json, and from the same locations (e.g., see
    data/top.png and data/bottom.png for pano ordering and location for coda. """

import json
from os import listdir
from os.path import isfile, join
import shutil
import cv2
import numpy as np
from e2c import e2c

EXISTING_ENV = 'yZVvKaJZghh'
NEW_ENV = 'yZVvKaJZghh_theta'
CONN = 'data/connectivity/%s_connectivity.json'
THETA_IMAGES = 'data/%s/theta_images'
MATT_IMAGES = 'data/%s/matterport_skybox_images/%s_equirectangular.jpg'
SAMI_IMAGES = 'data/%s/matterport_skybox_images/%s_skybox%d_sami.jpg'
SKYBOX_IMAGES = 'data/%s/matterport_skybox_images/%s_skybox_small.jpg'

DISPLAY_W = 800
DISPLAY_H = 400

# Downsized values used with Matterport3D Simulator
SKYBOX_WIDTH = 512
SKYBOX_HEIGHT = 512

if __name__ == '__main__':

  theta_path = THETA_IMAGES % NEW_ENV
  theta_ims = [join(theta_path, f) for f in listdir(theta_path) if isfile(join(theta_path, f)) and f.endswith('.JPG')]
  theta_ims.sort()

  new_env = []
  with open(CONN % EXISTING_ENV) as f:
    existing_env = json.load(f)

  count = 0
  for item in existing_env:

    cv2.namedWindow('theta',cv2.WINDOW_NORMAL)
    cv2.resizeWindow('theta', DISPLAY_W, DISPLAY_H)
    cv2.namedWindow('matterport',cv2.WINDOW_NORMAL)
    cv2.resizeWindow('matterport', DISPLAY_W, DISPLAY_H)

    if item['included']:

      print('%i: Copying %s to %s' % (count, theta_ims[count], MATT_IMAGES % (NEW_ENV, item['image_id'])))

      # Display equirectangular
      img1 = cv2.imread(theta_ims[count])
      img1 = np.roll(img1, int(img1.shape[1]/4), axis=1) # Theta camera was 90 degrees off
      cv2.imshow('theta', img1)
      img2 = cv2.imread(MATT_IMAGES % (EXISTING_ENV, item['image_id']))
      cv2.imshow('matterport', img2)
      cv2.waitKey(10)
      
      # Write equirectangular
      cv2.imwrite(MATT_IMAGES % (NEW_ENV, item['image_id']), img1)

      # Convert equirectangular pano to skybox format for simulator
      # 6 elements with keys 'F', 'R', 'B', 'L', 'U', 'D'
      cube = e2c(img1, face_w=SKYBOX_WIDTH, mode='bilinear', cube_format='dict')
      cube_ims = [np.fliplr(cube['U']), np.fliplr(cube['B']), cube['L'],
                cube['F'], np.fliplr(cube['R']), np.fliplr(np.flipud(cube['D']))]
      for i,face in enumerate(cube_ims):
          cv2.imwrite(SAMI_IMAGES % (NEW_ENV, item['image_id'], i), face)

      newimg = np.concatenate(cube_ims, axis=1)
      cv2.imwrite(SKYBOX_IMAGES % (NEW_ENV, item['image_id']), newimg)

      count += 1

  print('Copied %d images' % count)

  shutil.copy(CONN % EXISTING_ENV, CONN % NEW_ENV)
