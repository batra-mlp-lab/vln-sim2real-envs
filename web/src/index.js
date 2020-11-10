

const Config = require('../config.json');
console.log(Config);

const showcaseFrame = document.getElementById('showcase');
var data = null;
var modelData = null;
var dimensions = { width: 8192, height: 4096 };
var visibility = { mattertags: false, sweeps: false};

// Matterport showcase URL parameters
// https://support.matterport.com/hc/en-us/articles/209980967-URL-Parameters
showcaseFrame.src = 'https://my.matterport.com/showcase-beta/?m=' + Config.scanId + '&play=1';

window.SHOWCASE_SDK.connect(showcaseFrame, Config.ApiKey, '3.0')
  .then(function(sdk) {
    console.log('SDK Connected!');

    // Matterport SDK application starts here.
    sdk.on(sdk.App.Event.PHASE_CHANGE, function(phase){
      if (phase == "appphase.playing"){

        // Finished loading
        sdk.Model.getData()
        .then(function(mData){
          console.log('Model data loaded for scanId:', mData.sid);
          data = [];
          modelData = mData
          return sdk.Camera.getPose();
        })
        // Get pose and zero camera rotation
        .then(function(pose){
          console.log(pose);
          return sdk.Camera.rotate(pose.rotation.y,-pose.rotation.x);
        })
        .then(function(){
          console.log('rotation finished');
          sleep(1000);
          return scrapePanos(sdk, modelData);
        })
        .catch(function(error){
          console.error(error);
        });
      }
    });
  })
  .catch(function(error) {
    console.error(error);
  });


function scrapePanos(sdk, modelData){
  // Move to each pano in sequence while waiting for promises to resolve
  let result = modelData.sweeps.reduce( (previousPromise, nextSweep) => {
    return previousPromise.then(() => {
      return savePano(sdk, nextSweep);
    });
  }, Promise.resolve());

  // Download file when complete
  result.then(e => {
    var blob = new Blob([JSON.stringify(data)], {type: "data:application/json;charset=utf-8"});
    saveAs(blob, modelData.sid + '.json');
    console.log("Downloaded " + data.length + " panos")
  });
}


function savePano(sdk, sweep){
  console.log(sweep.uuid);
  return sdk.Sweep.moveTo(sweep.uuid)
  .then(function(sweepId){
    sleep(1000);
    return sdk.Renderer.takeEquirectangular(dimensions,visibility)
      .then(function (dataURI) {
        return sdk.Camera.getPose().then(function(pose){
          data.push({
            'image_id': sweep.uuid,
            'neighbors': sweep.neighbors,
            'sweep_position': [sweep.position.x, sweep.position.y, sweep.position.z],
            // Unaffected by camera position
            'sweep_rotation': [sweep.rotation.x, sweep.rotation.y, sweep.rotation.z],
            // Should be same as sweep position
            'camera_position': [pose.position.x, pose.position.y, pose.position.z], 
            // rotation around x (+ is up) and y (+ is left). Only x affects the downloaded equirectangular image.
            'camera_rotation': [pose.rotation.x, pose.rotation.y],
            'image': dataURI
          });
        });
      });
  })
  .catch(function(error){
    console.error(error);
  });
}


function sleep(milliseconds) {
  var start = new Date().getTime();
  for (var i = 0; i < 1e7; i++) {
    if ((new Date().getTime() - start) > milliseconds){
      break;
    }
  }
}

