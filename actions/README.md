
## actions

This directory contains the Subgoal Prediction model that is trained on Matterport3D to predict the location of adjacent graph nodes in the Matterport graph from the 360 image and a 270 degree flat laser scan.

The laser scan for each pano has been generated in advance using code from the `laser_scan` directory.

First set up some symlinks to the [Matterport3D dataset](https://niessner.github.io/Matterport/) and the [Matterport3D simulator](https://github.com/peteanderson80/Matterport3DSimulator). From the top-level directory run:

```
ln -s <MATTERPORT3D_DATA_DIR> actions/data
ln -s <MATTERPORT3D_SIMULATOR> Matterport3DSimulator
```

Note that the `MATTERPORT3D_DATA_DIR` must contain generated laser scans (see the `laser_scan` subdirectory).

Example command to train and validate the model (from the top-level directory):

```
cd actions
python3 train.py
```
