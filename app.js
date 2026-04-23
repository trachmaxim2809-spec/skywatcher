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

// Подключаем бесплатные темные тайлы CartoDB Dark Matter
// В случае отсутствия интернета или ошибки, пользователь увидит черный фон из CSS
L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
    maxZoom: 19,
    subdomains: 'abcd'
}).addTo(map);

// Функция для теста (нужна Антигравити для отладки)
// При клике на карту мы выводим координаты в консоль
map.on('click', function(e) {
    const lat = e.latlng.lat;
    const lng = e.latlng.lng;
    
    console.log(`Клик на карте: Координаты (${lat.toFixed(5)}, ${lng.toFixed(5)})`);
});
