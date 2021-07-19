~/react-prod$ grep ".get(\`" ./src/ -r
./src/containers/TheHeader.js:      .get(`/api/${API_KEY}/groups/0`)
./src/views/Alarm.js:    axios.get(`/api/${API_KEY}/config/alarm`).then((result) => {
./src/views/Mqtt.js:    axios.get(`/api/${API_KEY}/config/mqtt`).then((result) => {
./src/views/Bridge.js:      .get(`/api/${API_KEY}/info/timezones`)
./src/views/Bridge.js:    axios.get(`/api/${API_KEY}/config`).then((result) => {
./src/views/HueBridge.js:    axios.get(`/api/${API_KEY}/config/hue`).then((result) => {
./src/views/Groups.js:      .get(`/api/${API_KEY}`)
./src/views/Devices.js:        .get(`/sensors`)
./src/views/Deconz.js:    axios.get(`/api/${API_KEY}/config/deconz`).then((result) => {
./src/views/Lights.js:        .get(`/lights`)
./src/views/Lights.js:        .get(`/light-types`)
./src/views/Tradfri.js:    axios.get(`/api/${API_KEY}/config/tradfri`).then((result) => {