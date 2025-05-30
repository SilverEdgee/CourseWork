#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import os
import argparse
from PyQt5.QtWidgets import QApplication, QMessageBox

from qt_gui import MainWindow
from gesture_processor import GestureProcessor
from gesture_actions import GestureActions


def check_requirements():
    """Проверка наличия необходимых зависимостей."""
    try:
        import mediapipe
        import numpy as np
        import tensorflow as tf
        
        return True
    except ImportError as e:
        return False, str(e)


def parse_args():
    """Разбор аргументов командной строки."""
    parser = argparse.ArgumentParser(description='Hand Gesture Recognition с PyQt GUI')
    
    parser.add_argument('--disable-pyautogui', action='store_true',
                      help='Отключить функциональность pyautogui (для работы без X-сервера)')
    
    parser.add_argument('--camera', type=int, default=0,
                      help='ID камеры для захвата (по умолчанию: 0)')
    
    parser.add_argument('--width', type=int, default=640,
                      help='Ширина изображения с камеры (по умолчанию: 640)')
    
    parser.add_argument('--height', type=int, default=480,
                      help='Высота изображения с камеры (по умолчанию: 480)')
    
    return parser.parse_args()


def main():
    """Основная функция приложения."""
    # разбор аргументов командной строки
    args = parse_args()
    
    # проверка требований
    requirements_met = check_requirements()
    if requirements_met is not True:
        _, missing_lib = requirements_met
        print(f"Ошибка: отсутствует библиотека {missing_lib}")
        print("Установите необходимые зависимости с помощью команды:")
        print("pip install -r requirements.txt")
        return 1
    
    # инициализация приложения
    app = QApplication(sys.argv)
    
    # проверка наличия необходимых моделей
    model_paths = [
        'model/keypoint_classifier/keypoint_classifier.tflite'
    ]
    
    missing_files = [path for path in model_paths if not os.path.exists(path)]
    if missing_files:
        QMessageBox.critical(None, "Ошибка", 
                          f"Отсутствуют необходимые файлы моделей:\n{', '.join(missing_files)}\n\n"
                          "Запустите сначала обучение моделей с помощью ноутбука KeyPoint.")
        return 1
    
    # создание основного окна
    main_window = MainWindow()
    
    # инициализация обработчика жестов
    processor = GestureProcessor()
    
    # увтановка обработчика для видеопотока
    main_window.video_thread.set_processor(processor)
    
    # обработчик изменения режима
    def on_mode_change(index):
        processor.set_mode(index)
        main_window.log_event(f"Режим изменен на: {index}")
    
    # Обработчик для клавиш (0-9)
    def on_key_press(key):
        if 48 <= key <= 57:  # 0-9
            number = key - 48
            processor.set_number(number)
            main_window.log_event(f"Номер установлен: {number}")
        elif key == 110:  # n - нормальный режим
            processor.set_mode(0)
            main_window.camera_selector.setCurrentIndex(0)
            main_window.log_event("Режим: Нормальный")
        elif key == 107:  # k - запись жестов
            processor.set_mode(1)
            main_window.camera_selector.setCurrentIndex(1)
            main_window.log_event("Режим: Запись жестов")
    
    # подключение обработчиков
    main_window.camera_selector.currentIndexChanged.connect(on_mode_change)
    
    # установка параметров камеры из аргументов командной строки
    main_window.camera_id = args.camera
    main_window.camera_width = args.width
    main_window.camera_height = args.height
    
    # если выбрана камера отличная от 0, выбираем её в интерфейсе
    if args.camera != 0 and args.camera < main_window.camera_selector.count():
        main_window.camera_selector.setCurrentIndex(args.camera)
    
    # показ окна
    main_window.show()
    
    # запуск основного цикла приложения
    return app.exec_()


if __name__ == "__main__":
    sys.exit(main()) 