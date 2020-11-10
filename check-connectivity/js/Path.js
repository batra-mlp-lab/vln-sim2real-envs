

var scan_ix = 0;
var path_ix = 0;
var scan, path;

// declare a bunch of variable we will need later
var camera, camera_pose, scene, controls, renderer, skybox, connections, world_frame, cylinder_frame, cubemap_frame;
var mouse = new THREE.Vector2();
var id;

var SIZE_X = 720; // 960
var SIZE_Y = 720; // 540
var VFOV = 100;
var ASPECT = SIZE_X/SIZE_Y;// 1920.0/1080.0;

// Load paths
path_url = 'paths.json'
mesh_url = 'data/mesh_names.json'
d3.json(paths, function(error, data) {
  if (error) return console.warn(error);
  path = data[path_ix];
  image_id = path['path'][0];
  // initialize everything
  d3.json(mesh_url, function(error, data) {
    if (error) return console.warn(error);
    scan = data[scan_ix][0];
    skybox_init();
    load_connections(scan);
  })
})


// ## Initialize everything
function skybox_init(scan, image) {
  // test if webgl is supported
  if (! Detector.webgl) Detector.addGetWebGLMessage();

  // create the camera (kinect 2)
  camera = new THREE.PerspectiveCamera(VFOV, ASPECT, 0.01, 1000);
  camera_pose = new THREE.Object3D();
  camera_pose.add(camera);
  
  // create the Matterport world frame
  world_frame = new THREE.Object3D();
  
  // create the cubemap frame
  cubemap_frame = new THREE.Object3D();
  cubemap_frame.rotation.x = -Math.PI; // Adjust cubemap for z up
  cubemap_frame.add(world_frame);
  
  // Create a cylinder frame for holding moveto positions
  cylinder_frame = new THREE.Object3D();
  world_frame.add(cylinder_frame);
  
  // create the Scene
  scene = new THREE.Scene();
  world_frame.add(camera_pose);
  scene.add(cubemap_frame);

  var light = new THREE.DirectionalLight( 0xffffff, 1 );
  light.position.set(0, 0, 100);
  world_frame.add(light);
  world_frame.add(new THREE.AmbientLight( 0x404040 )); // soft light

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

function select(event) {
  // convert to normalized device coordinates
  mouse.x = ( event.x / SIZE_X ) * 2 - 1;
	mouse.y = - ( event.y / SIZE_Y ) * 2 + 1;
	raycaster.setFromCamera( mouse, camera );
	var intersects = raycaster.intersectObjects( cylinder_frame.children );
	if ( intersects.length > 0 ) {
    // todo start prefetching the next cube image
    intersects[0].object.currentHex = intersects[0].object.material.emissive.getHex();
    intersects[0].object.material.emissive.setHex( 0xff0000 );
    new_image_id = intersects[ 0 ].object.name;
    var target_y = camera.rotation.y - mouse.x * THREE.Math.degToRad(VFOV*ASPECT/2);
    var rotate_tween = new TWEEN.Tween({
      x: camera.rotation.x,
      y: camera.rotation.y,
      z: camera.rotation.z})
    .to( {
			x: 0,
			y: target_y,
			z: 0 }, 1000 )
    .easing( TWEEN.Easing.Cubic.InOut)
    .onUpdate(function() {
      camera.rotation.x = this.x;
      camera.rotation.y = this.y;
      camera.rotation.z = this.z;
      render();
    });
    var new_vfov = VFOV*0.7;
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
      cancelAnimationFrame( id );
      camera.fov = VFOV;
      camera.updateProjectionMatrix();
      intersects[0].object.material.emissive.setHex( intersects[0].object.currentHex );
      load_cube(scan, new_image_id);
    });
    rotate_tween.chain(zoom_tween);
    animate();
    rotate_tween.start();
	}
}

function set_camera_pose(matrix4d, height){
  var ignore = new THREE.Vector3();
  matrix4d.decompose(ignore, camera_pose.quaternion, camera_pose.scale);
  camera_pose.position.z = height;
  camera_pose.rotateX(Math.PI); // convert matterport camera to webgl camera
}

function get_camera_pose(){
  //todo - include pan tilt, get translation
}

function load_cube(scan, image) {
  scene.background = null;
  // load the cube textures
  var urlPrefix	= "https://storage.googleapis.com/bringmeaspoon/" + scan + "/skybox_images/" + image;
  var urls = [ urlPrefix + "_skybox2_sami.jpg", urlPrefix + "_skybox4_sami.jpg",
      urlPrefix + "_skybox0_sami.jpg", urlPrefix + "_skybox5_sami.jpg",
      urlPrefix + "_skybox1_sami.jpg", urlPrefix + "_skybox3_sami.jpg" ];

  var loader = new THREE.CubeTextureLoader();
  loader.setCrossOrigin('anonymous');
  loader.load(urls, function(textureCube){
    scene.background = textureCube;
        
    // Adjust cylinder poses to match the new location
    var pose = cylinder_frame.getObjectByName(image);
    cylinder_frame.position.x = -pose.position.x;
    cylinder_frame.position.y = -pose.position.y;
    cylinder_frame.position.z = -pose.position.z;

    // Adjust cylinder visibility (if on path)
    var cylinders = cylinder_frame.children;
    for (var i = 0; i < cylinders.length; ++i){
      cylinders[i].visible = connections[image]['visible'][i];
    }

    // Correct for individual skybox camera rotation
    var inv = new THREE.Matrix4();
    inv.getInverse(pose.matrix);
    var ignore = new THREE.Vector3();
    inv.decompose(ignore, world_frame.quaternion, world_frame.scale);
    world_frame.updateMatrix();
    render();
  });
}

function load_connections(scan) {
  //var url	= "https://storage.googleapis.com/bringmeaspoon/" + scan + "/matterport_camera_poses";
  //var url	= "/data/" + scan + "_skybox_poses.json";
  //var url	= "/woodside/data/Matterport3D/data/"+scan+"/matterport_camera_poses/pose_visibility.json";
  var url	= "17DRP5sb8fy_skybox_poses.json";
  d3.json(url, function(error, data) {
    if (error) return console.warn(error);
    connections = {};
    var image_id = null;
    for (var i = 0; i < data.length; i++) {
      var im = data[i]['image_id'];
      connections[im] = data[i];
      var pose = data[i]['pose'];
      pose[11] -= data[i]['height']; // drop to surface level
      var m = new THREE.Matrix4();
      m.fromArray(pose);
      m.transpose(); // switch row major to column major to suit three.js         
      var geometry = new THREE.CylinderBufferGeometry(0.15, 0.15, 0.05, 128);
      var material = new THREE.MeshLambertMaterial({color: 0x0000ff});
      material.transparent = true;
      material.opacity = 0.5;
      var cylinder = new THREE.Mesh(geometry, material);
      cylinder.height = data[i]['height'];
      cylinder.applyMatrix(m);
      cylinder.name = im;
      cylinder_frame.add(cylinder);
      if (data[i].hasOwnProperty('included') ) {
        if (data[i]['included'] == false){
          console.log('skip ' + im);
          cylinder.visible = false;
          continue;
        }
      }
    }
    load_cube(scan, image_id);
    var cam_pose = cylinder_frame.getObjectByName(image_id);
    set_camera_pose(cam_pose.matrix, cam_pose.height);
  });
}

// ## Display the Scene
function render() {
  renderer.render(scene, camera);
}

function animate() {
  id = requestAnimationFrame( animate );
  TWEEN.update();
}




