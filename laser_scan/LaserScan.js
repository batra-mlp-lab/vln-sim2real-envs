

THREE     = require("three");
jsonfile  = require("jsonfile");
OBJLoader = require("./OBJLoader.js");
OBJLoader(THREE);

// Directory containing Matterport data
var DATA_DIR = "<YOUR_PATH>/matterport/v1/scans/";
var SIM_DIR = "<YOUR_PATH>/Matterport3DSimulator/";
var SCAN_HEIGHT = 0.24; // above floor in meters
var SCAN_VALUES = 1440 // 0.25 degrees, to match Hokuyo


// declare a bunch of variables we will need later
var scan, mesh, scene;
var ix = 0;
var step = 1;
if (process.argv.length >= 4) {
  ix = parseInt(process.argv[2]);
  step = parseInt(process.argv[3]);
}

process_next();

function process_next(){
  mesh_url = "mesh_names.json";
  jsonfile.readFile(mesh_url, function(error, data) {
    if (error) {
      return console.warn(error);
    }
    if (ix>=data.length) {
      return;
    }
    scan = data[ix][0];
    mesh = data[ix][1];
    load_mesh(scan, mesh);
    ix += step;
  });
}

function load_mesh(scan, mesh){
  console.log("Loading mesh...");
  var obj_url = DATA_DIR + scan + "/matterport_mesh/" + mesh + "/" + mesh + ".obj";
  var objLoader = new THREE.OBJLoader();
  scene = new THREE.Scene();
  objLoader.load(obj_url, function ( object ) {
    scene.add(object);
    scene.updateMatrixWorld(true);
    console.log("Loaded mesh for scan: " + scan);
    trace_connections(scan);
  });
}

function laser_scan(position) {
  // laser scan, assuming looking down environment y axis
  // (so start at the negative y axis)
  var laser_ray = new THREE.Raycaster();
  var negY = new THREE.Vector3(0, -1, 0);
  // assume rotation is from the left to the right of scene
  var axis = new THREE.Vector3( 0, 0, -1 );
  var values = [];
  var angle = 2*Math.PI / SCAN_VALUES;
  for (var i=0; i<SCAN_VALUES; i++){
    laser_ray.set(position, negY);
    var intersects = laser_ray.intersectObjects(scene.children, true);
    if (intersects.length >= 1) {
      values.push(intersects[0].distance);
    } else {
      values.push(-1)
    }
    negY.applyAxisAngle( axis, angle );
  }
  return values;
}

function trace_connections(scan) {
  var url = SIM_DIR + "connectivity/" + scan + "_connectivity.json";
  var outfile = DATA_DIR + scan + "/laser_scans.json";
  jsonfile.readFile(url, function(error, data) {
    if (error) {
      return console.warn(error);
    }
    console.log("Laser scanning: "+ scan + ", " + data.length + " poses");
    var laser_scans = []
    var down = new THREE.Vector3(0, 0, -1);

    // construct offsets for raytracing to floor
    var offsets = new Array(9)
    var ov = 0.05;
    offsets[0] = new THREE.Vector3( 0 ,   0, 0);
    offsets[1] = new THREE.Vector3( ov,   0, 0);
    offsets[2] = new THREE.Vector3(  0,  ov, 0);
    offsets[3] = new THREE.Vector3(-ov,   0, 0);
    offsets[4] = new THREE.Vector3(  0, -ov, 0);
    offsets[5] = new THREE.Vector3( ov,  ov, 0);
    offsets[6] = new THREE.Vector3(-ov, -ov, 0);
    offsets[7] = new THREE.Vector3( ov, -ov, 0);
    offsets[8] = new THREE.Vector3(-ov,  ov, 0);

    for (var i=0; i<data.length; i++) {
      if (data[i]["included"]) {
        var image_id = data[i]["image_id"];
        var pose = data[i]["pose"];

        // Accurately establish the floor position (if possible)
        var height = null;
        var position = new THREE.Vector3(pose[3], pose[7], pose[11]);
        var height_ray = new THREE.Raycaster();
        for (var j=0; j<offsets.length; j++) {
          height_ray.set(position.add(offsets[j]), down);
          var intersects = height_ray.intersectObjects(scene.children, true);
          if (intersects.length >= 1) {
            height = intersects[0].distance;
            break;
          }
        }
        if (height == null) {
          console.log("Skipping: "+ scan + ", " + image_id + ", can't find floor");
          continue;
        } else {
          position = new THREE.Vector3(pose[3], pose[7], pose[11]-height+SCAN_HEIGHT);
          // Now do the actual scanning
          laser_scans.push({
            "image_id" : image_id,
            "position": position,
            "scan": scan,
            "laser": laser_scan(position)
          });
          //console.log("Done: "+ scan + ", " + image_id);
        }
      }
    }

    console.log("Saving to " + outfile);
    jsonfile.writeFile(outfile, laser_scans, function (err) {
      console.error(err)
    })
    process_next();
  });
}



