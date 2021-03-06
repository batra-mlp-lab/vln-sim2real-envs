# vln-sim2real-envs

This repo contains tools and code for:
1. Constructing [Matterport3DSimulator](https://github.com/peteanderson80/Matterport3DSimulator) environments from physical environments captured with a Matterport camera, and
2. Sampling paths from these environments and annotating them with natural language navigation instructions in the style of the [R2R dataset](https://bringmeaspoon.org/).

This allows arbitrary indoor spaces to be captured and annotated for the [Vision-and-Language Navigation (VLN)](https://arxiv.org/abs/1711.07280) task, thus enabling the performance of a trained agent to be directly compared:
1. In the Matterport3D Simulator environment (with navigation graph constraints); and 
2. Performing *exactly* the same instruction-following task in the corresponding physical environment on a robot.

This code was used in the paper: [Sim-to-Real Transfer for Vision-and-Language Navigation](). We also include the navigation instruction annotations used in the paper, PyTorch code for training the subgoal model, and javascript code for generating laser scans from environments in the Matterport3D dataset. The code for running the robot is available at [vln-sim2real](https://github.com/batra-mlp-lab/vln-sim2real).

### Bibtex:
```
@inproceedings{vln-pano2real,
  title={Sim-to-Real Transfer for Vision-and-Language Navigation},
  author={Peter Anderson and Ayush Shrivastava and Joanne Truong and Arjun Majumdar and Devi Parikh and Dhruv Batra and Stefan Lee},
  booktitle={CoRL},
  year={2020}
}
```

## Constructing a New Matterport3D Simulator Environment

To construct a new Matterport3D Simulator environment from a Matterport space (i.e., the assets generated by Matterport camera), follow [these instructions](web/README.md) to download the panoramic images and other data needed from the [Matterport cloud](https://my.matterport.com/accounts/login). You will need the `scanId` of the matterport space, as well as an SDK key for the [Matterport javascript SDK](https://matterport.com/developers/). The output will be a single json file named `<scanId>.json`.

To preprocess this json file into the correct format for the Matterport3D Simulator, run:
```
./scripts/preprocess.py PATH_TO_<scanID>.json
```

Download the [MatterPak Bundle](https://support.matterport.com/hc/en-us/articles/115013869728-Download-the-MatterPak-Bundle) containing the textured mesh for your space from your Matterport cloud account. Save it in `data/<scanId>/matterport_mesh` and add the `meshId` (filename of the downloaded obj file) to `web/config.json`.

Follow [these instructions](check-connectivity/README.md) to clean up the connectivity graph for the environment. (The connectivity graph controls which edges between panoramic viewpoint locations are navigable in the simulator, and it needs a bit of manual annotation / checking.)

Once completed, to add this environment to the Matterport3D Simulator:
1. Copy the images in `data/<scanId>/matterport_skybox_images/*_skybox_small.jpg` to the matterport dataset directory used by the simulator, e.g: `$MATTERPORT_DATA_DIR/<scanId>/matterport_skybox_images`
2. Add the new `data/connectivity/<scanId>_connectivity.json` file to the [connectivity](https://github.com/peteanderson80/Matterport3DSimulator/tree/master/connectivity) directory, and
3. Add the new `scanId` to [scans.txt](https://github.com/peteanderson80/Matterport3DSimulator/blob/master/connectivity/scans.txt)

You can now run the [python demo](https://github.com/peteanderson80/Matterport3DSimulator/blob/master/src/driver/driver.py) after modifying it to use your new `scanId`. Note that depth outputs from the Matterport3D Simulator will not be available as the Matterport SDK does not currently allow for downloading the original depth images.


## Sampling and Annotating VLN Trajectories

To sample shortest paths in the navigation graph using the same sampling process as the R2R dataset, after completing the previous steps, run:
```
./scripts/sample_paths_rooms.py
```

The appropriate `data/connectivity/<scanId>_connectivity.json` file will be selected using the `scanId` in `web/config.json`.

The resulting paths can now be annotated using the original AMT interface used for the R2R dataset, available [here](https://github.com/peteanderson80/Matterport3DSimulator/tree/master/web).

The instruction-path pairs annotated in the Coda environment are contained in `data/R2R/coda_test.json`. This file contains the full set of 40 trajectories with 3 annotations each, although only 37 trajectories were used in experiments due to a lack of wifi coverage.

The script `scripts/statistics.py` provides statistics for comparing the coda annotations to R2R.


## Subgoal Prediction Model

See the `actions` subdirectory.


## Generating Laser Scans in Matterport

See the `laser_scan` subdirectory.

## License

The Matterport3D dataset is governed by the
[Matterport3D Terms of Use](http://kaldir.vc.in.tum.de/matterport/MP_TOS.pdf).
This code is released under the BSD 3-Clause license.


