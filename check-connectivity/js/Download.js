

var ix = 34;
var viewpoint_ix = 31;
var scan;
var image_id;
var heading;
var elevation;

// declare a bunch of variable we will need later
var camera, camera_pose, scene, controls, renderer, connections, world_frame, cubemap_frame;
var mouse = new THREE.Vector2();

var BASE_URL = "https://storage.googleapis.com/bringmeaspoon/"
var SIZE_X = 640;
var SIZE_Y = 480;
var VFOV = 60; //horizontal 80
var ASPECT = SIZE_X/SIZE_Y;

// initialize everything
var path;

var matt = new Matterport3D("");
matt.loadJson('data/mesh_names.json').then(function(data){
  scan = data[ix][0];
  console.log(scan);
  skybox_init();
  load_connections(scan);
});


// ## Initialize everything
function skybox_init(scan, image) {
  // test if webgl is supported
  if (! Detector.webgl) Detector.addGetWebGLMessage();

  // create the camera (kinect 2)
  camera = new THREE.PerspectiveCamera(VFOV, ASPECT, 0.01, 1000);
  camera_pose = new THREE.Group();
  camera_pose.add(camera);
  
  // create the Matterport world frame
  world_frame = new THREE.Group();
  
  // create the cubemap frame
  cubemap_frame = new THREE.Group();
  cubemap_frame.rotation.x = -Math.PI; // Adjust cubemap for z up
  cubemap_frame.add(world_frame);
  
  // create the Scene
  scene = new THREE.Scene();
  world_frame.add(camera_pose);
  scene.add(cubemap_frame);

  var light = new THREE.DirectionalLight( 0xffffff, 1 );
  light.position.set(0, 0, 100);
  world_frame.add(light);
  world_frame.add(new THREE.AmbientLight( 0xffffff )); // soft light

  // init the WebGL renderer
  renderer = new THREE.WebGLRenderer({canvas: document.getElementById("skybox"), 
        antialias: true, preserveDrawingBuffer: true } );
  renderer.setSize(SIZE_X, SIZE_Y);

  controls = new THREE.PTZCameraControls(camera, renderer.domElement);
  controls.minZoom = 1;
  controls.maxZoom = 3.0;
  controls.minTilt = -0.6*Math.PI/2;
  controls.maxTilt = 0.6*Math.PI/2;
  controls.enableDamping = true;
  controls.panSpeed = -0.25;
  controls.tiltSpeed = -0.25;
  controls.zoomSpeed = 1.5;
  controls.dampingFactor = 0.5;
  controls.addEventListener( 'change', render );
}

Math.degrees = function(radians) {
  return radians * 180 / Math.PI;
};

function load_connections(scan) {
  var pose_url	= BASE_URL+"connectivity/"+scan+"_connectivity.json";
  d3.json(pose_url, function(error, data) {
    if (error) return console.warn(error);
    var viewpoint = data[viewpoint_ix]
    image_id = viewpoint['image_id']
    console.log(image_id)
    matt.loadCubeTexture(cube_urls(scan, image_id)).then(function(texture){
      scene.background = texture;
      // Correct world frame for individual skybox camera rotation
      var pose = viewpoint['pose'];
      for(var k=0; k<pose.length;k++) pose[k] = parseFloat(pose[k]);
      var m = new THREE.Matrix4();
      m.fromArray(pose);
      m.transpose(); // switch row major to column major to suit three.js
      var inv = new THREE.Matrix4();
      inv.getInverse(m);
      var ignore = new THREE.Vector3();
      inv.decompose(ignore, world_frame.quaternion, world_frame.scale);
      world_frame.updateMatrix();
      set_camera_pose(m);
      render();

      // calculate heading
      var rot = new THREE.Matrix3();
      rot.setFromMatrix4(m);
      var cam_look = new THREE.Vector3(0,0,1); // based on matterport camera
      cam_look.applyMatrix3(rot);
      console.log(cam_look);
      heading = Math.PI/2.0 -Math.atan2(cam_look.y, cam_look.x);
      if (heading < 0) {
        heading += 2.0*Math.PI;
      }  
      console.log(['heading', heading,Math.degrees(heading)]);

      // calculate elevation
      elevation = Math.atan2(cam_look.z, Math.sqrt(Math.pow(cam_look.x,2) + Math.pow(cam_look.y,2)))
      console.log(['elevation', elevation,Math.degrees(elevation)]);

      // download
      //var canvas = document.getElementById("skybox");
      //canvas.toBlob(function(blob) {
      //  console.log(blob);
      //  saveAs(blob, scan+"_"+image_id+"_"+heading.toString()+"_"+elevation.toString()+".png");
      //});

    });
  });
}

function save(){
  // download
  var canvas = document.getElementById("skybox");
  canvas.toBlob(function(blob) {
      console.log(blob);
      saveAs(blob, scan+"_"+image_id+"_"+heading.toString()+"_"+elevation.toString()+".png");
  });
}

function cube_urls(scan, image_id) {
  var urlPrefix	= "https://storage.googleapis.com/bringmeaspoon/" + scan + "/skybox_images/" + image_id;
  return [ urlPrefix + "_skybox2_sami.jpg", urlPrefix + "_skybox4_sami.jpg",
      urlPrefix + "_skybox0_sami.jpg", urlPrefix + "_skybox5_sami.jpg",
      urlPrefix + "_skybox1_sami.jpg", urlPrefix + "_skybox3_sami.jpg" ];
}

function set_camera_pose(matrix4d){
  matrix4d.decompose(camera_pose.position, camera_pose.quaternion, camera_pose.scale);
  camera_pose.rotateX(Math.PI); // convert matterport camera to webgl camera
}

function get_camera_pose(){
  camera.updateMatrix();
  camera_pose.updateMatrix();
  var m = camera.matrix.clone();
  m.premultiply(camera_pose.matrix);
  return m;
}

// Display the Scene
function render() {
  renderer.render(scene, camera);
}



