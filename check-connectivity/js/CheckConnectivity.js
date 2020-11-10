
// Manual adjust "visible" connections to provide "unobstructed" connections -
// defined as connections that are reasonable for a robot to move, i.e. not through furniture or windows etc.
// declare a bunch of variable we will need later
var scan;
var camera, scene, controls, renderer, connections, name_to_id, cylinder_frame, line_frame;
var dollhouse, raycaster, download_data;
var mouse = new THREE.Vector2();
var selected = null;
var deleted = null;

// Directory containing Matterport data
var DATA_DIR = "../data/";
var SIZE_X = 1280;
var SIZE_Y = 960;
var VFOV = 70;
var ASPECT = SIZE_X/SIZE_Y;// 1920.0/1080.0;


// Marker colors
var NOT_INCLUDED = 0x00AA00;
var NORMAL       = 0x0000ff;
var SELECTED     = 0xff0000;

var matt = new Matterport3D(DATA_DIR);
var config_url = "../web/config.json"
d3.json(config_url, function(error, data) {
  if (error) return console.warn(error);
  config = data;

  // initialize everything
  init();
  scan = config.scanId;
  mesh = config.MeshId;
  d3.select("#scan_name").text(scan);
  matt.load_mesh(scan, mesh, function(object){
    dollhouse = object;
    scene.add( object );
    render();
    load_connections(scan);
  })
})

function download() {
  var text = JSON.stringify(download_data);
  var blob = new Blob([text], {type: "application/json"});
  saveAs(blob, scan+"_connectivity.json");
}

// ## Initialize everything
function init() {

  if (controls){
    controls.dispose();
  } else {
    // movement
    document.addEventListener("keydown", onDocumentKeyDown, false);
  }

  // test if webgl is supported
  if (! Detector.webgl) Detector.addGetWebGLMessage();
  
  // create the Scene
  scene = new THREE.Scene();
  scene.background = new THREE.Color( 0xffffff );
  
  camera = new THREE.PerspectiveCamera(VFOV, ASPECT, 1, 100);
  //camera = new THREE.OrthographicCamera(VFOV, ASPECT, 1, 100);
  camera.position.z = 20;

  scene.add(camera);

  var light = new THREE.DirectionalLight( 0x888888, 1 );
  light.position.set(0, 0, 100);
  scene.add(light);
  scene.add(new THREE.AmbientLight( 0x888888 )); // soft light
  
  // Create a cylinder frame for holding moveto positions
  cylinder_frame = new THREE.Object3D();
  line_frame = new THREE.Object3D();
  cylinder_frame.add(line_frame);
  scene.add(cylinder_frame);

  raycaster = new THREE.Raycaster();

  // init the WebGL renderer
  renderer = new THREE.WebGLRenderer({canvas: document.getElementById("skybox"), antialias: true } );
  renderer.setSize(SIZE_X, SIZE_Y);
  
  controls = new THREE.PTZCameraControls(camera, renderer.domElement);
  controls.translate = true;
  controls.minZoom = 1;
  controls.maxZoom = 3.0;
  controls.minTilt = -0.6*Math.PI/2;
  controls.maxTilt = 0.6*Math.PI/2;
  controls.enableDamping = true;
  controls.panSpeed = 2;
  controls.tiltSpeed = 2;
  controls.zoomSpeed = 1.5;
  controls.dampingFactor = 0.5;
  controls.addEventListener( "select", select );
  controls.addEventListener( "change", render );
}

function onDocumentKeyDown(event) {
  event.preventDefault();
  var keyCode = event.which;
  // up
  if (keyCode == 38) {
    camera.position.z += 1;
  // down
  } else if (keyCode == 40) {
    camera.position.z -= 1;
  // left
  } else if (keyCode == 37) {
    camera.near += 0.5;
  // right
  } else if (keyCode == 39) {
    camera.near -= 0.5;
    if (camera.near < 0) camera.near = 0.1;
  // space
  } else if (keyCode == 32) {
    if (selected){
      toggle_node(selected);
    }
  // escape
  } else if (keyCode == 27) {
    controls.translate = !controls.translate;
    controls.panSpeed *= -1;
    controls.tiltSpeed *= -1;
  }
  camera.updateProjectionMatrix();
  render();
};

function select(event) {
  // convert to normalized device coordinates
  mouse.x = ( event.x / SIZE_X ) * 2 - 1;
	mouse.y = - ( event.y / SIZE_Y ) * 2 + 1;
	raycaster.setFromCamera( mouse, camera );
	var intersects = raycaster.intersectObjects( cylinder_frame.children );
	if ( intersects.length > 0 ) {
    obj1 = intersects[ 0 ].object;
    if (selected){
      if (obj1 == selected) {
        var id1 = name_to_id[selected.name];
        if (download_data[id1]["included"]){
          selected.material.emissive.setHex( NORMAL );
        } else {
          selected.material.emissive.setHex( NOT_INCLUDED );
        }
        selected = null;
        render();
      } else {
        //console.log([obj1.name, obj1.position]);
        toggle_connection(selected, obj1);
      }
    } else {
      //console.log([obj1.name, obj1.position]);
      selected = obj1;
      selected.material.emissive.setHex( SELECTED );
      render();
    }
  }
}

function toggle_node(obj1) {
  var id1 = name_to_id[obj1.name];
  if (download_data[id1]["included"]){
    download_data[id1]["included"] = false;
    hide_node(obj1);
  } else {
    download_data[id1]["included"] = true;
    show_node(id1, obj1);
  }
}

function hide_node(obj1){
  // Hide connections
  for (var i = 0; i < download_data.length; i++) {
    var obj2 = cylinder_frame.getObjectByName(download_data[i]["image_id"]);
    remove_connection(obj1,obj2);
  }
}

function show_node(id1, obj1){
  // Display connections
  for (var j = 0; j < download_data.length; j++){
    if (download_data[j]["included"]){
      var target = cylinder_frame.getObjectByName(download_data[j]["image_id"]);
      if (download_data[id1]["unobstructed"][j]){
        add_connection(obj1, target);
      }
    }
  }
}

function toggle_connection(obj1, obj2) {
  var id1 = name_to_id[obj1.name];
  var id2 = name_to_id[obj2.name];
  if (!download_data[id1]["included"] || !download_data[id2]["included"]){
    return;
  }
  if (download_data[id1]["unobstructed"][id2]){
    download_data[id1]["unobstructed"][id2] = false;
    download_data[id2]["unobstructed"][id1] = false;
    remove_connection(obj1, obj2);
  } else {
    download_data[id1]["unobstructed"][id2] = true;
    download_data[id2]["unobstructed"][id1] = true;
    add_connection(obj1, obj2);
  }
}

function make_name(obj1, obj2){
  if (obj1.name < obj2.name){
    return obj1.name+"_"+obj2.name;
  } else {
    return obj2.name+"_"+obj1.name;
  }
}

function add_connection(obj1, obj2) {
  var line_name = make_name(obj1, obj2);
  var line = scene.getObjectByName(line_name);
  if (!line){
    var material = new THREE.LineBasicMaterial({ color: NORMAL, linewidth: 3 });
    var geometry = new THREE.Geometry();
    geometry.vertices.push(obj1.position.clone());
    geometry.vertices.push(obj2.position.clone());
    var line = new THREE.Line(geometry, material);
    line.name = line_name;
    //console.log("adding "+line.name);
    line_frame.add(line);
    render();
  }
}

function distance(obj1, obj2) {
  var dx = obj1.position.x - obj2.position.x;
  var dy = obj1.position.y - obj2.position.y;
  var dz = obj1.position.z - obj2.position.z;
  return Math.sqrt( dx * dx + dy * dy + dz * dz );
}

function remove_connection(obj1, obj2){
  var line_name = make_name(obj1, obj2);
  var line = scene.getObjectByName(line_name);
  if (line){
    //console.log("removing "+line_name);
    line_frame.remove(line);
    render();
  }
}

function load_connections(scan) {
  var url = "../data/connectivity/"+scan+"_initial_connectivity.json";
  name_to_id = {}
  d3.json(url, function(error, data) {
    if (error) return console.warn(error);
    for (var i = 0; i < data.length; i++) {
      if (!data[i].hasOwnProperty("included") ) {
        data[i]["included"] = true;
      }
      var im = data[i]["image_id"];
      name_to_id[im] = i;
      var pose = data[i]["pose"];
      for(var k=0; k<pose.length;k++) pose[k] = parseFloat(pose[k]);
      var m = new THREE.Matrix4();
      m.fromArray(pose);
      m.transpose(); // switch row major to column major to suit three.js
      var geometry = new THREE.CylinderBufferGeometry(0.15, 0.15, 0.05, 128);
      var material = new THREE.MeshLambertMaterial({color: NORMAL});
      var cylinder = new THREE.Mesh(geometry, material);
      cylinder.applyMatrix(m);
      cylinder.name = im;
      cylinder_frame.add(cylinder);
      if (!data[i]["included"]){
        cylinder.material.emissive.setHex( NOT_INCLUDED );
      }
    }
    for (var i = 0; i < data.length; i++) {
      if (data[i]["included"]){
        var cylinder = cylinder_frame.getObjectByName(data[i]["image_id"]);
        // Display connections
        for (var j = 0; j < data.length; j++){
          if (data[j]["included"]){
            var target = cylinder_frame.getObjectByName(data[j]["image_id"]);
            if (data[i]["unobstructed"][j]){
              // check distance is less than 5m
              if (distance(cylinder, target) < 5.0) { 
                add_connection(cylinder, target);
              }
            }
          }
        }
      }
    }
    download_data = data;
    render();
    console.log("Loaded connections from " + url);
  });
}

// ## Display the Scene
function render() {
  renderer.render(scene, camera);
}




