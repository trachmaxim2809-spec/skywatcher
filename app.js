// Интеграция с Telegram Web App
if (window.Telegram && window.Telegram.WebApp) {
    window.Telegram.WebApp.ready(); // Сообщаем Telegram, что приложение готово
    window.Telegram.WebApp.expand(); // Разворачиваем приложение на максимум
}

// Функция логирования на экран (для отладки на мобилках)
function logMsg(text) {
    const logDiv = document.getElementById('debug-log');
    if (logDiv) {
        logDiv.innerText += '\n> ' + text;
    }
    console.log(text);
}

logMsg("App starting...");

// Функция логирования на экран (для отладки на мобилках)
function logMsg(text) {
    const logDiv = document.getElementById('debug-log');
    if (logDiv) {
        logDiv.innerText += '\n> ' + text;
    }
    console.log(text);
}

logMsg("System check: App starting...");

// Инициализируем карту Leaflet
const map = L.map('map', {
    center: [48.37, 31.16], // Географический центр Украины
    zoom: 6,                 // Стартовый масштаб
    zoomControl: true,       // Разрешаем кнопки зума для картографической подложки
    attributionControl: false, // Отключаем копирайты
    zoomAnimation: true,     // Плавная анимация зума
    fadeAnimation: true,
    inertia: false,          // Отключаем инерцию скролла для большей резкости "военного" интерфейса
});

// Добавляем темные тайлы (CartoDB Dark Matter)
// Карта с городами на фоне, под GeoJSON
L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
    maxZoom: 19,
    subdomains: 'abcd'
}).addTo(map);

// Создаем специальный pane (панель) для GeoJSON, чтобы они всегда были поверх подложки
// и корректно перехватывали клики/наведения, не отдавая их нижней карте
map.createPane('regionsPane');
map.getPane('regionsPane').style.zIndex = 400;

// Стили для областей
const defaultStyle = {
    fillColor: 'transparent',
    color: '#333333', // Темно-серая граница
    weight: 1,
    fillOpacity: 0
};

const alarmStyle = {
    fillColor: '#ff0000',
    color: '#ff0000', // Неоново-красная граница
    weight: 2,
    fillOpacity: 0.3
};

// Хранилище слоев для быстрого доступа по имени области
const regionLayers = {};
let geoJsonLayer;

// Загрузка GeoJSON и его отрисовка
logMsg("Fetching GeoJSON (Map)...");
fetch('https://raw.githubusercontent.com/slawomirmatuszak/ukrainian_geodata/master/regiony.geojson')
    .then(response => {
        logMsg("GeoJSON status: " + response.status);
        return response.json();
    })
    .then(data => {
        geoJsonLayer = L.geoJSON(data, {
            style: defaultStyle,
            pane: 'regionsPane',
            onEachFeature: function (feature, layer) {
                const regionName = feature.properties.region;
                regionLayers[regionName] = layer;
                layer.bindPopup(() => `<b>${regionName}</b><br>Статус: З'ясовується...`);
            }
        }).addTo(map);
        logMsg("GeoJSON loaded: " + Object.keys(regionLayers).length + " regions.");
    })
    .catch(error => logMsg("GeoJSON FAIL: " + error.message));

// Инициализация Firebase
const firebaseConfig = {
    databaseURL: "https://skywatcher-3cf3f-default-rtdb.europe-west1.firebasedatabase.app"
};

logMsg("Connecting Firebase...");
if (!firebase.apps.length) {
    firebase.initializeApp(firebaseConfig);
}
const database = firebase.database();
logMsg("Firebase connected.");

// Запускаем слушатель МГНОВЕННО, не дожидаясь скачивания карты
startFirebaseListener();

function startFirebaseListener() {
    logMsg("Firebase Listener started.");
    const regionsRef = database.ref('regions');

    // Функция обновления слоя карты
    const updateRegionStatus = (regionName, isActive) => {
        // Мы ищем слой. Если нет точного совпадения, ищем частичное (напр. "Харків" -> "Харківська область")
        let layer = regionLayers[regionName];
        
        if (!layer) {
            // Умный поиск (нормализация)
            const cleanInput = regionName.toLowerCase().replace('ская', '').replace('ська', '').replace(' область', '').trim();
            const foundKey = Object.keys(regionLayers).find(key => 
                key.toLowerCase().includes(cleanInput)
            );
            if (foundKey) layer = regionLayers[foundKey];
        }

        if (layer) {
            if (isActive) {
                layer.setStyle(alarmStyle);
            } else {
                layer.setStyle(defaultStyle);
            }
        } else {
            console.warn(`Layer not found for: ${regionName}`);
        }
    };

    // Слушатель на изменение статуса
    regionsRef.on('child_changed', (snapshot) => {
        const regionName = snapshot.key;
        const isActive = snapshot.val();
        console.log(`[Firebase Update] ${regionName}: ${isActive}`);
        updateRegionStatus(regionName, isActive);
    });

    // Слушатель на первоначальную загрузку (чтобы покрасить те, что уже в тревоге)
    regionsRef.on('child_added', (snapshot) => {
        const regionName = snapshot.key;
        const isActive = snapshot.val();
        updateRegionStatus(regionName, isActive);
    });

    // === ФАЗА 7: ВЕРХОВНЫЙ ИИ (Отображение Целей) ===
    // Создаем кастомный DivIcon для цели
    const createTargetIcon = (type, direction) => {
        let emoji = '🔴';
        let extraClass = '';
        
        if (type === 'SHAHED') {
            emoji = '🛸';
            extraClass = 'shahed-marker';
        } else if (type === 'ROCKET') {
            emoji = '🚀';
        } else if (type === 'AVIATION') {
            emoji = '✈️';
        }
        
        // Маппинг направлений в градусы поворота для вектора
        const dirAngles = {
            'E': 0, 'SE': 45, 'S': 90, 'SW': 135,
            'W': 180, 'NW': 225, 'N': 270, 'NE': 315
        };
        
        let vectorHtml = '';
        if (direction && dirAngles[direction] !== undefined) {
            const angle = dirAngles[direction];
            vectorHtml = `<div class="target-vector" style="transform: rotate(${angle}deg);"><div class="vector-line"></div></div>`;
        }

        return L.divIcon({
            className: 'custom-target-icon',
            html: `<div class="target-container">
                    ${vectorHtml}
                    <div class="target-marker ${extraClass}">${emoji}</div>
                   </div>`,
            iconSize: [30, 30],
            iconAnchor: [15, 15] // Центрируем
        });
    };
    // === СЛУШАТЕЛЬ ЦЕЛЕЙ (ВЕРХОВНЫЙ ИИ) ===
    const activeTargetsRef = database.ref('active_targets');
    const markers = {}; // Храним только активные маркеры Leaflet

    activeTargetsRef.on('value', (snapshot) => {
        const data = snapshot.val() || {};
        const currentIds = Object.keys(data);

        // 1. Удаляем маркеры, которых больше нет в базе
        Object.keys(markers).forEach(id => {
            if (!data[id]) {
                map.removeLayer(markers[id]);
                delete markers[id];
            }
        });

        // 2. Добавляем новые или обновляем существующие
        currentIds.forEach(id => {
            const tgt = data[id];
            
            // Определяем координаты для отрисовки. 
            // Если это группа (is_group), создаем массив из 2-3 позиций.
            const positions = [{ lat: tgt.lat, lon: tgt.lon }];
            if (tgt.is_group) {
                positions.push({ lat: tgt.lat + 0.05, lon: tgt.lon + 0.05 });
                positions.push({ lat: tgt.lat - 0.03, lon: tgt.lon + 0.07 });
            }

            if (!markers[id]) {
                // Создание группы маркеров (Leaflet LayerGroup)
                const layerGroup = L.layerGroup().addTo(map);
                positions.forEach((pos, index) => {
                    const m = L.marker([pos.lat, pos.lon], {
                        icon: createTargetIcon(tgt.type, tgt.direction)
                    }).addTo(layerGroup);
                    if (index === 0) m.bindPopup(`<b>ГРУППА ЦЕЛЕЙ: ${tgt.type}</b>`);
                });
                markers[id] = layerGroup;
            } else {
                // Обновление позиций внутри группы
                const layerGroup = markers[id];
                let i = 0;
                layerGroup.eachLayer(layer => {
                    if (positions[i]) {
                        layer.setLatLng([positions[i].lat, positions[i].lon]);
                        layer.setIcon(createTargetIcon(tgt.type, tgt.direction));
                        i++;
                    }
                });
            }
        });
    });
}
