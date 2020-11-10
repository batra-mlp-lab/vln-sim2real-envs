

## Download Panos and Poses from a Matterport space

To extract panos and related data for the Matterport3D Simulator from a particular Matterport space:
- First install node and npm
- Next, save the `scanId` for the Matterport space, and your Matterport SDK key into `config.json` (following the format of `config.json.example`). 

On Ubuntu, to allow node to run on port 80 (required for Matterport SDK), run:
```
sudo setcap 'cap_net_bind_service=+ep' `which node`
```

From this directory, install dependencies by running:
```
npm install
```

Build the code:
```
npm run build
```

Run this to open your browser and download the panos, etc:
```
npm run serve
```

This will run in the browswer for a while and at the end a single file named `<scanId>.json` will be saved in your brower's default download directory, e.g. `Downloads`. This file contains all the panoramic images, their poses, and other information.
