import time
import logging
from database_manager import init_firebase, set_region_status

logging.basicConfig(level=logging.INFO)

if __name__ == "__main__":
    if init_firebase():
        print("Внимание! Имитация атаки началась...")
        
        regions_to_attack = [
            "Київська область", 
            "Вінницька область", 
            "Дніпропетровська область",
            "Одеська область",
            "Харківська область"
        ]

        # Включаем тревогу
        for region in regions_to_attack:
            set_region_status(region, True)
            time.sleep(0.5)
        
        print("\nВсе указанные регионы должны стать КРАСНЫМИ на карте.")
        print("Ожидание 10 секунд для визуальной проверки...\n")
        time.sleep(10)
        
        print("Отбой тревоги! Восстановление зеленого статуса...")
        for region in regions_to_attack:
            set_region_status(region, False)
            time.sleep(0.5)
            
        print("\nТест завершен.")
    else:
        print("Критическая ошибка: Не удалось подключиться к Firebase")
