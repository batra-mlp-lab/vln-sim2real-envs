
## laser_scan

WebGL code to generate a 2D laser scan from each pano location in the Matterport3D simulator
using Nodejs. Scans are generated from the reconstructed mesh using a horizontal plane at a 
given height above the floor.


Make sure `DATA_DIR` and `SIM_DIR` in LaserScan.js are set appropriately, then: 

```bash
cd laser_scan
npm install
node LaserScan.js
```

This will take some hours. After generation a `laser_scan.json` file will be generated in
each scan directory in  `DATA_DIR`. Each json file contains an array of objects (one for
each viewpoint in the scan) formatted as follows:

```
{
  "image_id": string,
  "position": {"x": float, "y": float, "z": float},
  "scan": string,
  "laser": [float x 1440]
}
```

where `laser` contains the range scan return values in meters. Scans are generated in a
clockwise fashion and each scan is centered on the Matterport environment y axis. Non-return
values (indicating holes in the mesh, perhaps due to windows or objects that are very far
away) appear as -1.

See `SCAN_HEIGHT` and `SCAN_VALUES` in LaserScan.js to adjust the scan height and scan
resolution.
