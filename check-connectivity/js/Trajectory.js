

var ix = 17; // 2, 20, 17
var step = 0;
var playing = false;
var scan;
var curr_image_id;

// declare a bunch of variable we will need later
var camera, camera_pose, scene, controls, renderer, connections, world_frame, cylinder_frame, cubemap_frame;
var mouse = new THREE.Vector2();
var id;

var BASE_URL = "https://storage.googleapis.com/bringmeaspoon/"
var SIZE_X = 640; // 960
var SIZE_Y = 480; // 540
var VFOV = 60;
var ASPECT = SIZE_X/SIZE_Y;// 1920.0/1080.0;

// initialize everything
var path;

var matt = new Matterport3D("");
matt.loadJson('seq2seq_agent_sample_imagenet_val_seen_iter_19900.json').then(function(traj){
  matt.loadJson('R2R_val_seen.json').then(function(gt){
  
    gt_data = gt[ix];
    scan = gt_data['scan'];
    curr_image_id = gt_data['path'][0];
    instr = gt_data['instructions'][0];
    document.getElementsByTagName("p")[0].innerHTML=instr;
    id = gt_data['path_id'] + '_0';
    path = traj[id]; // List of lists
    skybox_init();
    load_connections(scan, curr_image_id);
  });
});

function play() {
  if (!playing){
    document.getElementById("play").disabled = true;
    if (step != 0 || curr_image_id != path[0][0]){
      // First move back to start
      var image_id = path[0][0];
      matt.loadCubeTexture(cube_urls(scan, image_id)).then(function(texture){
        camera.rotation.x = 0;
        camera.rotation.y = 0;
        camera.rotation.z = 0;
        scene.background = texture;
        render();
        move_to(image_id, true);
        step = 0;
        playing = true;
        step_forward();
      });
    } else {
      step = 0;
      playing = true;
      step_forward();
    }
  }
}

function step_forward(){
  step += 1;
  if (step >= path.length) {
    step -= 1;
    playing = false;
    document.getElementById("play").disabled = false;
  } else {
    take_action(path[step]);
  }
};

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
  renderer = new THREE.WebGLRenderer({canvas: document.getElementById("skybox"), antialias: true } );
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

function load_connections(scan, image_id) {
  var pose_url	= BASE_URL+"connectivity/"+scan+"_connectivity.json";
  d3.json(pose_url, function(error, data) {
    if (error) return console.warn(error);
    // Create a cylinder frame for showing arrows of directions
    var id_to_pose = {}
    for (var i = 0; i < data.length; i++) {
      id_to_pose[data[i]['image_id']] = data[i];
      id_to_pose[data[i]['image_id']]['ix'] = i;
    }
    cylinder_frame = new THREE.Group();
    visibility = {};
    for (var i = 0; i < data.length; i++) {
      var image_id = data[i]['image_id'];
      visibility[image_id] = {};
      var found = false;
      for (var j = 0; j < path.length; j++) {
        var target_id = path[j][0];
        if (image_id == target_id){
          found = true;
          // Viewpoint is in path
          var pose = data[i]['pose'];
          for(var k=0; k<pose.length;k++) pose[k] = parseFloat(pose[k]);
          var height = parseFloat(data[i]['height']);
          pose[11] -= height; // drop to surface level
          var m = new THREE.Matrix4();
          m.fromArray(pose);
          m.transpose(); // switch row major to column major to suit three.js
          var geometry = new THREE.CylinderBufferGeometry(0.15, 0.15, 0.05, 128);
          var color = 0x0000ff;
          if (j == path.length-1) {
            color = 0xff0000; // goal
          } else if (j == 0){
            color = 0x00ff00; // start
          }
          var material = new THREE.MeshLambertMaterial({color: color});
          material.transparent = true;
          material.opacity = 1.0;
          var cylinder = new THREE.Mesh(geometry, material);
          cylinder.applyMatrix(m);
          cylinder.height = height;
          cylinder.name = image_id;
          cylinder_frame.add(cylinder);
        }
      }
      if (found){
        for (var j = 0; j < path.length; j++) {
          var target_id = path[j][0];
          if (data[i]['visible'][id_to_pose[target_id]['ix']] || data[i]['unobstructed'][id_to_pose[target_id]['ix']]){
            visibility[image_id][target_id] = true;
          }
        }
      }
    }
    world_frame.add(cylinder_frame);
    var image_id = path[0][0];
    matt.loadCubeTexture(cube_urls(scan, image_id)).then(function(texture){
      scene.background = texture;
      move_to(image_id, true);
      document.getElementById("play").disabled = false;
    });
  });
}

function cube_urls(scan, image_id) {
  var urlPrefix	= "https://storage.googleapis.com/bringmeaspoon/" + scan + "/skybox_images/" + image_id;
  return [ urlPrefix + "_skybox2_sami.jpg", urlPrefix + "_skybox4_sami.jpg",
      urlPrefix + "_skybox0_sami.jpg", urlPrefix + "_skybox5_sami.jpg",
      urlPrefix + "_skybox1_sami.jpg", urlPrefix + "_skybox3_sami.jpg" ];
}

function move_to(image_id, isInitial=false) {
  // Adjust cylinder visibility
  var cylinders = cylinder_frame.children;
  for (var i = 0; i < cylinders.length; ++i){
    cylinders[i].visible = false; //visibility[image_id].hasOwnProperty(cylinders[i].name);
  }
  // Correct world frame for individual skybox camera rotation
  var inv = new THREE.Matrix4();
  var cam_pose = cylinder_frame.getObjectByName(image_id);
  inv.getInverse(cam_pose.matrix);
  var ignore = new THREE.Vector3();
  inv.decompose(ignore, world_frame.quaternion, world_frame.scale);
  world_frame.updateMatrix();
  if (isInitial){
    set_camera_pose(cam_pose.matrix, cam_pose.height);
  } else {
    set_camera_position(cam_pose.matrix, cam_pose.height);
  }
  render();
  curr_image_id = image_id;
  // Animation
  if (playing) {
    step_forward();
  }
}

function set_camera_pose(matrix4d, height){
  matrix4d.decompose(camera_pose.position, camera_pose.quaternion, camera_pose.scale);
  camera_pose.position.z += height;
  camera_pose.rotateX(Math.PI); // convert matterport camera to webgl camera
}

function set_camera_position(matrix4d, height) {
  var ignore_q = new THREE.Quaternion();
  var ignore_s = new THREE.Vector3();
  matrix4d.decompose(camera_pose.position, ignore_q, ignore_s);
  camera_pose.position.z += height;
}

function get_camera_pose(){
  camera.updateMatrix();
  camera_pose.updateMatrix();
  var m = camera.matrix.clone();
  m.premultiply(camera_pose.matrix);
  return m;
}

function take_action(dest) {
  image_id = dest[0]
  heading = dest[1]
  elevation = dest[2]
  if (image_id !== curr_image_id) {
    var texture_promise = matt.loadCubeTexture(cube_urls(scan, image_id)); // start fetching textures
    var target = cylinder_frame.getObjectByName(image_id);

    // Camera up vector
    var camera_up = new THREE.Vector3(0,1,0);
    var camera_look = new THREE.Vector3(0,0,-1);
    var camera_m = get_camera_pose();// Animation
    var zero = new THREE.Vector3(0,0,0);
    camera_m.setPosition(zero);
    camera_up.applyMatrix4(camera_m);
    camera_up.normalize();
    camera_look.applyMatrix4(camera_m);
    camera_look.normalize();

    // look direction
    var look = target.position.clone();
    look.sub(camera_pose.position);
    look.projectOnPlane(camera_up);
    look.normalize();
    // Simplified - assumes z is zero
    var rotate = Math.atan2(look.y,look.x) - Math.atan2(camera_look.y,camera_look.x);
    if (rotate < -Math.PI) rotate += 2*Math.PI;
    if (rotate > Math.PI) rotate -= 2*Math.PI;

    var target_y = camera.rotation.y + rotate;
    var rotate_tween = new TWEEN.Tween({
      x: camera.rotation.x,
      y: camera.rotation.y,
      z: camera.rotation.z})
    .to( {
		  x: 0,
		  y: target_y,
		  z: 0 }, 2000*Math.abs(rotate) )
    .easing( TWEEN.Easing.Cubic.InOut)
    .onUpdate(function() {
      camera.rotation.x = this.x;
      camera.rotation.y = this.y;
      camera.rotation.z = this.z;
      render();
    });
    var new_vfov = VFOV*0.95;
    var zoom_tween = new TWEEN.Tween({
      vfov: VFOV})
    .to( {vfov: new_vfov }, 1000 )
    .easing(TWEEN.Easing.Cubic.InOut)
    .onUpdate(function() {
      camera.fov = this.vfov;
      camera.updateProjectionMatrix();
      render();
    })
    .onComplete(function(){
      cancelAnimationFrame(id);
      texture_promise.then(function(texture) {
        scene.background = texture; 
        camera.fov = VFOV;
        camera.updateProjectionMatrix();
        move_to(image_id);
      });
    });
    rotate_tween.chain(zoom_tween);
    animate();
    rotate_tween.start();
  } else {
    // Just move the camera
    console.log('move camera');
    
    // Animation
    if (playing) {
      step_forward();
    }
  }
}

// Display the Scene
function render() {
  renderer.render(scene, camera);
}

// tweening
function animate() {
  id = requestAnimationFrame( animate );
  TWEEN.update();
}


