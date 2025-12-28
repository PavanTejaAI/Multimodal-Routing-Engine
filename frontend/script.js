const HYDERABAD_COORD = [17.385, 78.486];
const API_URL = window.location.origin;

const baseLayer = L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', { maxZoom: 19 });
const satelliteLayer = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', { maxZoom: 19 });

let map = L.map('map', {
    zoomControl: false,
    attributionControl: false,
    layers: [baseLayer]
}).setView(HYDERABAD_COORD, 13);

const createPulseIcon = (color) => L.divIcon({
    className: 'custom-div-icon',
    html: `<div class="marker-pulse" style="background: ${color}"></div>`,
    iconSize: [22, 22],
    iconAnchor: [11, 11]
});

const createStationIcon = () => L.divIcon({
    className: 'station-marker',
    html: `<i data-lucide="train" style="width:14px;height:14px;"></i>`,
    iconSize: [24, 24],
    iconAnchor: [12, 12]
});

const createEVIcon = () => L.divIcon({
    className: 'ev-marker',
    html: `<i data-lucide="zap" style="width:14px;height:14px;"></i>`,
    iconSize: [24, 24],
    iconAnchor: [12, 12]
});

L.control.zoom({ position: 'bottomright' }).addTo(map);

let startMarker, endMarker;
let routeLayers = [];
let startCoords = null;
let endCoords = null;
let validBounds = null;
let currentMode = 'transit';

fetch(`${API_URL}/bounds`)
    .then(res => res.json())
    .then(data => {
        if (data.bounds) {
            const b = data.bounds;
            const p = 0.01;
            validBounds = L.latLngBounds(
                [b.min_lat - p, b.min_lon - p],
                [b.max_lat + p, b.max_lon + p]
            );
            const world = [[90, -180], [90, 180], [-90, 180], [-90, -180]];
            const hole = [
                [validBounds.getNorthEast().lat, validBounds.getNorthEast().lng],
                [validBounds.getNorthWest().lat, validBounds.getNorthWest().lng],
                [validBounds.getSouthWest().lat, validBounds.getSouthWest().lng],
                [validBounds.getSouthEast().lat, validBounds.getSouthEast().lng]
            ];
            L.polygon([world, hole], {
                color: '#000',
                fillColor: '#000',
                fillOpacity: 0.6,
                stroke: false,
                interactive: false
            }).addTo(map);
            map.fitBounds(validBounds);
        }
    })
    .catch(err => console.error(err));

fetch(`${API_URL}/stations`)
    .then(res => res.json())
    .then(data => {
        if (data.stations) {
            data.stations.forEach(st => {
                L.marker([st.lat, st.lon], { icon: createStationIcon() })
                    .addTo(map)
                    .bindPopup(`<b>${st.name}</b><br>Transit Station`);
            });
            if (window.lucide) lucide.createIcons();
        }
    })
    .catch(err => console.error(err));

fetch(`${API_URL}/evs`)
    .then(res => res.json())
    .then(data => {
        if (data.evs) {
            data.evs.forEach(ev => {
                L.marker([ev.lat, ev.lon], { icon: createEVIcon() })
                    .addTo(map)
                    .bindPopup(`<b>EV Charging Station</b><br>Type: ${ev.type || 'Standard'}`);
            });
            if (window.lucide) lucide.createIcons();
        }
    })
    .catch(err => console.error(err));

const startDisplay = document.getElementById('start-coord');
const endDisplay = document.getElementById('end-coord');
const findBtn = document.getElementById('find-route');
const statusPanel = document.getElementById('status-panel');
const resultsPanel = document.getElementById('results');

map.on('click', (e) => {
    if (validBounds && !validBounds.contains(e.latlng)) {
        alert("Select a point within the highlighted area.");
        return;
    }
    const { lat, lng } = e.latlng;
    if (!startCoords) {
        setStart(lat, lng);
    } else if (!endCoords) {
        setEnd(lat, lng);
    } else {
        setStart(lat, lng);
        setEnd(null);
    }
});

function setStart(lat, lng, name = null) {
    if (startMarker) map.removeLayer(startMarker);
    if (lat === null) {
        startCoords = null;
        startDisplay.innerText = 'Click on map to select...';
        startDisplay.classList.remove('selected');
        document.getElementById('start-search').value = '';
        return;
    }
    startCoords = { lat, lng };
    startMarker = L.marker([lat, lng], { icon: createPulseIcon('#2563eb') }).addTo(map);
    startDisplay.innerText = name ? name : `${lat.toFixed(4)}, ${lng.toFixed(4)}`;
    startDisplay.classList.add('selected');
    if (name) document.getElementById('start-search').value = name;
    if (name) map.setView([lat, lng], 15);
}

function setEnd(lat, lng, name = null) {
    if (endMarker) map.removeLayer(endMarker);
    if (lat === null) {
        endCoords = null;
        endDisplay.innerText = 'Click on map to select...';
        endDisplay.classList.remove('selected');
        document.getElementById('end-search').value = '';
        return;
    }
    endCoords = { lat, lng };
    endMarker = L.marker([lat, lng], { icon: createPulseIcon('#ef4444') }).addTo(map);
    endDisplay.innerText = name ? name : `${lat.toFixed(4)}, ${lng.toFixed(4)}`;
    endDisplay.classList.add('selected');
    if (name) document.getElementById('end-search').value = name;
    if (name) map.setView([lat, lng], 15);
}

function setupSearch(inputId, onSelect) {
    const input = document.getElementById(inputId);
    if (!input) return;
    const container = input.parentElement;
    const list = document.createElement('div');
    list.className = 'suggestions-list';
    container.appendChild(list);
    let debounceTimer;
    input.addEventListener('input', (e) => {
        const query = e.target.value;
        clearTimeout(debounceTimer);
        if (query.length < 3) {
            list.style.display = 'none';
            return;
        }
        debounceTimer = setTimeout(() => {
            fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(query + ', Hyderabad, India')}&viewbox=${validBounds ? validBounds.toBBoxString() : ''}&bounded=1&limit=5`, {
                headers: { 'User-Agent': 'HyderaNav-2025' }
            })
                .then(res => res.json())
                .then(results => {
                    list.innerHTML = '';
                    if (results && results.length > 0) {
                        list.style.display = 'block';
                        results.forEach(place => {
                            const item = document.createElement('div');
                            item.className = 'suggestion-item';
                            item.innerText = place.display_name.split(',')[0];
                            item.onclick = () => {
                                onSelect(parseFloat(place.lat), parseFloat(place.lon), place.display_name.split(',')[0]);
                                list.style.display = 'none';
                            };
                            list.appendChild(item);
                        });
                    } else {
                        list.style.display = 'none';
                    }
                })
                .catch(() => { list.style.display = 'none'; });
        }, 600);
    });
    document.addEventListener('click', (e) => {
        if (!container.contains(e.target)) list.style.display = 'none';
    });
}

setupSearch('start-search', setStart);
setupSearch('end-search', setEnd);

document.getElementById('start-locate')?.addEventListener('click', () => {
    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(pos => {
            setStart(pos.coords.latitude, pos.coords.longitude, "Current Location");
        }, () => {
            alert("Location access denied.");
        });
    }
});

document.querySelectorAll('.mode-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('.mode-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        currentMode = btn.dataset.mode;
    });
});

document.getElementById('layer-satellite').addEventListener('click', function () {
    if (map.hasLayer(satelliteLayer)) {
        map.removeLayer(satelliteLayer);
        map.addLayer(baseLayer);
        this.classList.remove('active');
    } else {
        map.removeLayer(baseLayer);
        map.addLayer(satelliteLayer);
        this.classList.add('active');
    }
});

document.getElementById('view-3d').addEventListener('click', function () {
    const mapEl = document.getElementById('map');
    mapEl.classList.toggle('map-3d');
    this.classList.toggle('active');
    setTimeout(() => map.invalidateSize(), 800);
});

findBtn.addEventListener('click', async () => {
    if (!startCoords || !endCoords) {
        alert("Select points.");
        return;
    }
    statusPanel.classList.remove('hidden');
    resultsPanel.classList.add('hidden');
    routeLayers.forEach(l => map.removeLayer(l));
    routeLayers = [];
    try {
        const response = await fetch(`${API_URL}/route`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                start_lat: startCoords.lat,
                start_lon: startCoords.lng,
                end_lat: endCoords.lat,
                end_lon: endCoords.lng,
                mode: currentMode
            })
        });
        if (!response.ok) throw new Error();
        const data = await response.json();
        const pathData = data.path;
        if (!pathData || !pathData.segments || pathData.segments.length === 0 || pathData.totalCost === -1) {
            alert("No results found.");
            statusPanel.classList.add('hidden');
            return;
        }
        renderRoute(pathData);
    } catch (err) {
        statusPanel.innerHTML = `<p style="color:var(--error)">Connection failed.</p>`;
    } finally {
        statusPanel.classList.add('hidden');
    }
});

function renderRoute(pathData) {
    const segments = pathData.segments;
    const totalCost = pathData.totalCost;
    const totalDistance = pathData.totalDistance || 0;
    let bounds = L.latLngBounds([]);
    segments.forEach(seg => {
        const color = seg.mode === 'TRANSIT' ? '#dc2626' : '#2563eb';
        const dashArray = seg.mode === 'TRANSIT' ? '12, 10' : null;
        const className = seg.mode === 'TRANSIT' ? 'transit-path' : 'route-glow';
        const opacity = seg.mode === 'TRANSIT' ? 0.8 : 0.9;
        const weight = seg.mode === 'TRANSIT' ? 6 : 8;
        const polyline = L.polyline(seg.coords, {
            color: color,
            weight: weight,
            opacity: opacity,
            dashArray: dashArray,
            className: className,
            lineCap: 'round'
        }).addTo(map);
        routeLayers.push(polyline);
        bounds.extend(polyline.getBounds());
    });
    map.fitBounds(bounds, { padding: [50, 50] });
    resultsPanel.classList.remove('hidden');
    document.getElementById('res-time').innerText = Math.ceil(totalCost / 60) + ' min';
    document.getElementById('res-distance').innerText = (totalDistance / 1000).toFixed(1) + ' km';
}
