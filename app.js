// Интеграция с Telegram Web App
if (window.Telegram && window.Telegram.WebApp) {
    window.Telegram.WebApp.ready(); // Сообщаем Telegram, что приложение готово
    window.Telegram.WebApp.expand(); // Разворачиваем приложение на максимум
}

// Инициализируем карту Leaflet
const map = L.map('map', {
    center: [48.37, 31.16], // Географический центр Украины
    zoom: 6,                 // Стартовый масштаб
    zoomControl: false,      // Отключаем кнопки зума (минимализм)
    attributionControl: false, // Отключаем копирайты
    zoomAnimation: true,     // Плавная анимация зума
    fadeAnimation: true,
    inertia: false,          // Отключаем инерцию скролла для большей резкости "военного" интерфейса
});

// Добавляем темные тайлы (CartoDB Dark Matter)
// В случае отсутствия интернета или ошибки, пользователь увидит черный фон из CSS
L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
    maxZoom: 19,
    subdomains: 'abcd'
}).addTo(map);

// Инициализация Firebase
const firebaseConfig = {
    // В боевом проекте тут могут быть apiKey и projectId, но для простой 
    // Realtime Database часто достаточно только URL (если права на чтение открыты)
    databaseURL: "https://skywatcher-3cf3f-default-rtdb.europe-west1.firebasedatabase.app"
};

if (!firebase.apps.length) {
    firebase.initializeApp(firebaseConfig);
}
const database = firebase.database();

// Прослушиваем изменения статуса регионов
const regionsRef = database.ref('regions');

// child_changed срабатывает при изменении существующего региона
regionsRef.on('child_changed', (snapshot) => {
    const regionName = snapshot.key;
    const isActive = snapshot.val();
    
    if (isActive) {
        console.log(`ВНИМАНИЕ: Тревога в области ${regionName}`);
        // В будущем тут будет код перекрашивания полигона на карте
    } else {
        console.log(`Отбой: Тревога в области ${regionName}`);
    }
});

// child_added срабатывает при первоначальной загрузке данных или при добавлении нового региона
regionsRef.on('child_added', (snapshot) => {
    const regionName = snapshot.key;
    const isActive = snapshot.val();
    
    if (isActive) {
        console.log(`ВНИМАНИЕ: Тревога в области ${regionName}`);
    }
});

// Функция для теста (нужна Антигравити для отладки)
// При клике на карту мы выводим координаты в консоль
map.on('click', function(e) {
    const lat = e.latlng.lat;
    const lng = e.latlng.lng;
    
    console.log(`Клик на карте: Координаты (${lat.toFixed(5)}, ${lng.toFixed(5)})`);
});
