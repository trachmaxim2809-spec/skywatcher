// Интеграция с Telegram Web App
if (window.Telegram && window.Telegram.WebApp) {
    window.Telegram.WebApp.ready(); // Сообщаем Telegram, что приложение готово
    window.Telegram.WebApp.expand(); // Разворачиваем приложение на максимум
}

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

// Загрузка GeoJSON и его отрисовка (один раз при старте)
fetch('https://raw.githubusercontent.com/slawomirmatuszak/ukrainian_geodata/master/regiony.geojson')
    .then(response => response.json())
    .then(data => {
        geoJsonLayer = L.geoJSON(data, {
            style: defaultStyle,
            pane: 'regionsPane', // Привязываем GeoJSON к нашей панели поверх тайлов
            onEachFeature: function (feature, layer) {
                const regionName = feature.properties.region; // Имя из файла (напр. "Київська область")
                // Можно нормализовать имя или сохранить как есть
                regionLayers[regionName] = layer;
                
                // Настраиваем Popup для интерактивности
                layer.bindPopup(() => {
                    return `<b>${regionName}</b><br>Статус: З'ясовується...`;
                });
            }
        }).addTo(map);

        // После загрузки карты и слоев начинаем слушать Firebase
        startFirebaseListener();
    })
    .catch(error => {
        console.error('Ошибка загрузки GeoJSON:', error);
    });

// Инициализация Firebase
const firebaseConfig = {
    databaseURL: "https://skywatcher-3cf3f-default-rtdb.europe-west1.firebasedatabase.app"
};

if (!firebase.apps.length) {
    firebase.initializeApp(firebaseConfig);
}
const database = firebase.database();

function startFirebaseListener() {
    const regionsRef = database.ref('regions');

    // Функция обновления слоя карты
    const updateRegionStatus = (regionName, isActive) => {
        // Мы ищем точное совпадение имени в GeoJSON
        // Если имена в базе не совпадают (напр. Firebase: "Kyiv", GeoJSON: "Київська область"), 
        // то нужно будет написать маппинг. Пока предполагаем, что имена идентичны.
        const layer = regionLayers[regionName];
        
        if (layer) {
            // Перекрашиваем полигон
            if (isActive) {
                layer.setStyle(alarmStyle);
                layer.setPopupContent(`<b>${regionName}</b><br>Статус: <span style="color:red">🔴 ТРИВОГА</span>`);
            } else {
                layer.setStyle(defaultStyle);
                layer.setPopupContent(`<b>${regionName}</b><br>Статус: 🟢 Спокійно`);
            }
        } else {
            console.warn(`Не найден слой для региона: ${regionName}`);
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
}
