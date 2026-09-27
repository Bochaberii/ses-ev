const apiBase = '/api';
let speedChart;
let socChart;
let powerChart;

// These arrays hold rolling values for the telemetry charts so the dashboard can
// show recent history without overwhelming the browser or backend.
const state = {
  speed: [],
  soc: [],
  power: [],
};

async function apiCall(path, method = 'GET', body = null) {
  const options = {
    method,
    headers: {
      'Content-Type': 'application/json',
    },
  };
  if (body !== null) options.body = JSON.stringify(body);
  const response = await fetch(`${apiBase}${path}`, options);
  if (!response.ok) {
    throw new Error('Request failed');
  }
  return response.json();
}

function updateCharts(stateData) {
  state.speed.push(stateData.vehicle.speed_kph);
  state.soc.push(stateData.battery.soc);
  state.power.push(stateData.battery.power_kw);

  if (state.speed.length > 30) state.speed.shift();
  if (state.soc.length > 30) state.soc.shift();
  if (state.power.length > 30) state.power.shift();

  const labels = Array.from({ length: state.speed.length }, (_, index) => index + 1);

  if (speedChart) {
    speedChart.data.labels = labels;
    speedChart.data.datasets[0].data = state.speed;
    speedChart.update();
  }
  if (socChart) {
    socChart.data.labels = labels;
    socChart.data.datasets[0].data = state.soc;
    socChart.update();
  }
  if (powerChart) {
    powerChart.data.labels = labels;
    powerChart.data.datasets[0].data = state.power;
    powerChart.update();
  }
}

function updateDashboard(stateData) {
  // The UI is intentionally a thin projection of the backend simulation state.
  // The source of truth remains the Python model rather than UI-local calculations.
  document.getElementById('speedValue').textContent = `${stateData.vehicle.speed_kph.toFixed(1)} km/h`;
  document.getElementById('stateValue').textContent = stateData.vehicle.state;
  document.getElementById('socValue').textContent = `${stateData.battery.soc.toFixed(1)}%`;
  document.getElementById('batteryPowerValue').textContent = `${stateData.battery.power_kw.toFixed(1)} kW`;
  document.getElementById('motorTorqueValue').textContent = `${stateData.motor.torque_nm.toFixed(1)} Nm`;
  document.getElementById('motorRpmValue').textContent = `${Math.round(stateData.motor.rpm)} rpm`;
  document.getElementById('vcuStatus').textContent = stateData.system_status.vcu_status;
  document.getElementById('bmsStatus').textContent = stateData.battery.status;
  document.getElementById('motorStatus').textContent = stateData.motor.status;
  document.getElementById('commStatus').textContent = stateData.system_status.communication_status;
  document.getElementById('energyConsumed').textContent = `${stateData.energy.energy_consumed_kwh.toFixed(2)} kWh`;
  document.getElementById('energyRecovered').textContent = `${stateData.energy.energy_recovered_kwh.toFixed(2)} kWh`;
  document.getElementById('energyNet').textContent = `${stateData.energy.net_energy_consumed_kwh.toFixed(2)} kWh`;
  document.getElementById('chargingPower').textContent = `${stateData.charging.charging_power_kw.toFixed(1)} kW`;

  const faults = stateData.diagnostics.active_faults.length ? stateData.diagnostics.active_faults.join(', ') : 'No active faults.';
  document.getElementById('faultSummary').textContent = faults;

  document.getElementById('accelReadout').textContent = `${document.getElementById('acceleratorInput').value}%`;
  document.getElementById('brakeReadout').textContent = `${document.getElementById('brakeInput').value}%`;

  updateCharts(stateData);
}

async function refreshState() {
  try {
    const data = await apiCall('/state');
    updateDashboard(data);
  } catch (error) {
    console.error('State fetch failed', error);
  }
}

function initCharts() {
  const speedCtx = document.getElementById('speedChart');
  speedChart = new Chart(speedCtx, {
    type: 'line',
    data: { labels: [], datasets: [{ label: 'Speed', data: [], borderColor: '#63d0ff', fill: false, tension: 0.2 }] },
    options: { responsive: true, animation: false, scales: { x: { beginAtZero: false }, y: { beginAtZero: true } } },
  });

  const socCtx = document.getElementById('socChart');
  socChart = new Chart(socCtx, {
    type: 'line',
    data: { labels: [], datasets: [{ label: 'SOC %', data: [], borderColor: '#7ef5b8', fill: false, tension: 0.2 }] },
    options: { responsive: true, animation: false, scales: { x: { beginAtZero: false }, y: { beginAtZero: false, suggestedMax: 100 } } },
  });

  const powerCtx = document.getElementById('powerChart');
  powerChart = new Chart(powerCtx, {
    type: 'line',
    data: { labels: [], datasets: [{ label: 'Battery Power (kW)', data: [], borderColor: '#ffb347', fill: false, tension: 0.2 }] },
    options: { responsive: true, animation: false, scales: { x: { beginAtZero: false }, y: { beginAtZero: false } } },
  });
}

async function handleInputChange() {
  const payload = {
    accelerator: Number(document.getElementById('acceleratorInput').value),
    brake: Number(document.getElementById('brakeInput').value),
    charger_connected: false,
  };
  try {
    const data = await apiCall('/inputs', 'POST', payload);
    updateDashboard(data);
  } catch (error) {
    console.error('Input update failed', error);
  }
}

async function startVehicle() {
  const data = await apiCall('/start', 'POST');
  updateDashboard(data);
}

async function stopVehicle() {
  const data = await apiCall('/stop', 'POST');
  updateDashboard(data);
}

async function resetSimulation() {
  const data = await apiCall('/reset', 'POST');
  updateDashboard(data);
}

async function connectCharger() {
  const data = await apiCall('/charger/connect', 'POST');
  updateDashboard(data);
}

async function disconnectCharger() {
  const data = await apiCall('/charger/disconnect', 'POST');
  updateDashboard(data);
}

async function injectFault() {
  const fault = document.getElementById('faultSelect').value;
  const data = await apiCall('/fault', 'POST', { fault });
  updateDashboard(data);
}

async function clearFault() {
  const fault = document.getElementById('faultSelect').value;
  const data = await apiCall('/fault/clear', 'POST', { fault });
  updateDashboard(data);
}

function bindDemoButtons() {
  document.querySelectorAll('[data-demo]').forEach((button) => {
    button.addEventListener('click', async () => {
      const demo = button.dataset.demo;
      const actions = {
        startup: () => apiCall('/start', 'POST'),
        driving: () => apiCall('/inputs', 'POST', { accelerator: 60, brake: 0, charger_connected: false }),
        regen: () => apiCall('/inputs', 'POST', { accelerator: 0, brake: 75, charger_connected: false }),
        charging: () => apiCall('/charger/connect', 'POST'),
        fault: () => apiCall('/fault', 'POST', { fault: 'HIGH_BATTERY_TEMPERATURE' }),
      };
      const data = await actions[demo]();
      updateDashboard(data);
    });
  });
}

function connectSocket() {
  // The browser keeps a persistent WebSocket open to the FastAPI backend so the
  // dashboard receives a live stream of vehicle state updates without continuous
  // polling. If the socket fails, the page still falls back to periodic polling.
  const socket = new WebSocket(`ws://${window.location.host}/api/ws`);
  socket.addEventListener('message', (event) => {
    const data = JSON.parse(event.data);
    updateDashboard(data);
  });
  socket.addEventListener('error', () => {
    console.warn('WebSocket disconnected; falling back to polling');
  });
}

function bindEvents() {
  document.getElementById('startBtn').addEventListener('click', startVehicle);
  document.getElementById('stopBtn').addEventListener('click', stopVehicle);
  document.getElementById('resetBtn').addEventListener('click', resetSimulation);
  document.getElementById('chargerConnectBtn').addEventListener('click', connectCharger);
  document.getElementById('chargerDisconnectBtn').addEventListener('click', disconnectCharger);
  document.getElementById('injectFaultBtn').addEventListener('click', injectFault);
  document.getElementById('clearFaultBtn').addEventListener('click', clearFault);
  document.getElementById('acceleratorInput').addEventListener('input', handleInputChange);
  document.getElementById('brakeInput').addEventListener('input', handleInputChange);
  bindDemoButtons();
}

initCharts();
bindEvents();
connectSocket();
refreshState();
setInterval(refreshState, 1000);
