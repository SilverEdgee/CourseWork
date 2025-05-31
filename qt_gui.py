import sys
import os
import cv2
import numpy as np
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                           QLabel, QPushButton, QComboBox, QGroupBox, QGridLayout, 
                           QTabWidget, QListWidget, QListWidgetItem, QTableWidget, 
                           QTableWidgetItem, QCheckBox, QSlider, QMessageBox,
                           QDoubleSpinBox, QStyle, QStyleFactory, QDialog, QHeaderView,
                           QProgressBar)
from PyQt5.QtGui import QImage, QPixmap, QColor, QFont, QPalette
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QSize, QTime

from gesture_actions import GestureActions

# определение цветовой схемы и стилей
STYLE = """
QMainWindow {
    background-color: #2D2D30;  /* основной цвет фона окна */
}
QWidget {
    background-color: #2D2D30;  /* цвет фона всех элементов */
    color: #E6E6E6;            /* цвет текста */
    font-family: 'Segoe UI', Arial, sans-serif;  /* шрифты */
}
QGroupBox {
    border: 1px solid #3F3F46;  /* рамка группы */
    border-radius: 5px;         /* закругление углов */
    margin-top: 10px;           /* отступ сверху */
    font-weight: bold;          /* жирный текст */
    padding: 10px;              /* внутренние отступы */
    min-width: 320px;           /* минимальная ширина групп */
}
QGroupBox::title {
    subcontrol-origin: margin;  /* размещение заголовка */
    left: 10px;                /* отступ слева */
    padding: 0 5px 0 5px;      /* внутренние отступы */
}
QPushButton {
    background-color: #007ACC;  /* цвет кнопки */
    color: white;              /* цвет текста кнопки */
    border: none;              /* убрать рамку */
    border-radius: 3px;        /* закругление углов */
    padding: 5px 15px;         /* отступы внутри */
    font-weight: bold;         /* жирный текст */
}
QPushButton:hover {
    background-color: #1C97EA;  /* цвет при наведении */
}
QPushButton:pressed {
    background-color: #0062A3;  /* цвет при нажатии */
}
QPushButton:disabled {
    background-color: #4D4D4D;  /* цвет неактивной кнопки */
    color: #9D9D9D;           /* цвет текста неактивной кнопки */
}
QComboBox {
    border: 1px solid #3F3F46;  /* рамка выпадающего списка */
    border-radius: 3px;         /* закругление углов */
    padding: 5px;               /* отступы */
    min-width: 6em;            /* минимальная ширина */
}
QComboBox:hover {
    border: 1px solid #007ACC;  /* рамка при наведении */
}
QComboBox QAbstractItemView {
    border: 1px solid #3F3F46;  /* рамка выпадающего меню */
    selection-background-color: #007ACC;  /* цвет выделения */
}
QSlider::groove:horizontal {
    border: 1px solid #3F3F46;  /* рамка полосы слайдера */
    height: 8px;                /* высота полосы */
    background: #252526;        /* цвет полосы */
    margin: 2px 0;              /* отступы */
    border-radius: 4px;         /* закругление */
}
QSlider::handle:horizontal {
    background: #007ACC;        /* цвет ползунка */
    border: 1px solid #5F5F5F;  /* рамка ползунка */
    width: 18px;               /* ширина ползунка */
    margin: -2px 0;            /* выравнивание */
    border-radius: 4px;        /* закругление */
}
QSlider::handle:horizontal:hover {
    background: #1C97EA;        /* цвет ползунка при наведении */
}
QCheckBox {
    spacing: 5px;              /* отступ между флажком и текстом */
}
QCheckBox::indicator {
    width: 15px;               /* размер флажка */
    height: 15px;              /* высота флажка */
}
QListWidget {
    border: 1px solid #3F3F46;  /* рамка списка */
    border-radius: 3px;         /* закругление углов */
}
QListWidget::item:selected {
    background-color: #007ACC;  /* цвет выделенного элемента */
}
QSpinBox, QDoubleSpinBox {
    border: 1px solid #3F3F46;  /* рамка полей ввода чисел */
    border-radius: 3px;         /* закругление углов */
    padding: 5px;               /* отступы */
}
"""

class VideoThread(QTimer):
    """Класс для обработки видеопотока"""
    frame_ready = pyqtSignal(np.ndarray)
    processed_ready = pyqtSignal(np.ndarray, dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.cap = None
        self.camera_id = 0
        self.is_running = False
        self.width = 640
        self.height = 480
        
        # настройки MediaPipe
        self.use_static_image_mode = False
        self.min_detection_confidence = 0.7
        self.min_tracking_confidence = 0.5
        
        # обработчик жестов (будет установлен позже)
        self.processor = None
        
        # Запуск таймера
        self.timeout.connect(self.update_frame)
        self.setInterval(30)  # ~30 FPS
        
    def start_camera(self, camera_id=0, width=640, height=480):
        """Запуск камеры"""
        if self.is_running:
            self.stop_camera()
            
        self.camera_id = camera_id
        self.width = width
        self.height = height
        
        # инициализация камеры
        self.cap = cv2.VideoCapture(self.camera_id)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        
        if not self.cap.isOpened():
            return False
            
        self.is_running = True
        super().start()
        return True
        
    def stop_camera(self):
        """Остановка камеры"""
        super().stop()
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        self.is_running = False
        
    def update_frame(self):
        """Обновление кадра"""
        if not self.is_running or self.cap is None:
            return
            
        ret, frame = self.cap.read()
        if not ret:
            return
            
        # отражение изображения по горизонтали (зеркально)
        frame = cv2.flip(frame, 1)
        
        # отправка оригинального кадра
        self.frame_ready.emit(frame)
        
        # если есть обработчик, обрабатываем кадр и отправляем результат
        if self.processor is not None:
            result_frame, result_data = self.processor.process_image(frame)
            self.processed_ready.emit(result_frame, result_data)
            
    def set_processor(self, processor):
        """Установка обработчика жестов"""
        self.processor = processor
        
    def update_settings(self, 
                     static_mode=None, 
                     min_detection_conf=None, 
                     min_tracking_conf=None):
        """Обновление настроек MediaPipe"""
        if static_mode is not None:
            self.use_static_image_mode = static_mode
        if min_detection_conf is not None:
            self.min_detection_confidence = min_detection_conf
        if min_tracking_conf is not None:
            self.min_tracking_confidence = min_tracking_conf
            
        if self.processor:
            self.processor.update_settings(
                static_mode=self.use_static_image_mode,
                min_detection_conf=self.min_detection_confidence,
                min_tracking_conf=self.min_tracking_confidence
            )


class MainWindow(QMainWindow):
    """Главное окно приложения"""
    def __init__(self):
        super().__init__()
        
        # параметры камеры
        self.camera_id = 0
        self.camera_width = 640
        self.camera_height = 480
        
        # счетчик записанных кадров
        self.recorded_frames = 0
        
        # применение стилей
        self.apply_styles()
        
        # настройка окна
        self.setWindowTitle("Hand Gesture Controller")
        self.setMinimumSize(1200, 800)
        
        # инициализация менеджера действий
        self.gesture_actions = GestureActions()
        
        # инициализация компонентов
        self.init_ui()
        
        # загрузка начальных значений настроек
        self.load_initial_settings()
        
        # инициализация видеопотока
        self.video_thread = VideoThread(self)
        self.video_thread.frame_ready.connect(self.update_camera_feed)
        self.video_thread.processed_ready.connect(self.update_processed_feed)
        
        # загрузка списка жестов
        self.load_gesture_list()
        
        # Загрузка конфигурации действий
        self.load_action_mappings()
        
    def apply_styles(self):
        """Применение стилей и настройка темы"""
        # Установка темного стиля Fusion
        QApplication.setStyle(QStyleFactory.create("Fusion"))
        
        # Применение пользовательских стилей
        self.setStyleSheet(STYLE)
        
        # Установка цветов палитры для всего приложения
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(45, 45, 48))
        palette.setColor(QPalette.WindowText, QColor(230, 230, 230))
        palette.setColor(QPalette.Base, QColor(37, 37, 38))
        palette.setColor(QPalette.AlternateBase, QColor(45, 45, 48))
        palette.setColor(QPalette.ToolTipBase, QColor(0, 122, 204))
        palette.setColor(QPalette.ToolTipText, QColor(230, 230, 230))
        palette.setColor(QPalette.Text, QColor(230, 230, 230))
        palette.setColor(QPalette.Button, QColor(45, 45, 48))
        palette.setColor(QPalette.ButtonText, QColor(230, 230, 230))
        palette.setColor(QPalette.BrightText, QColor(255, 255, 255))
        palette.setColor(QPalette.Link, QColor(0, 122, 204))
        palette.setColor(QPalette.Highlight, QColor(0, 122, 204))
        palette.setColor(QPalette.HighlightedText, QColor(255, 255, 255))
        QApplication.setPalette(palette)
        
    def init_ui(self):
        """Инициализация пользовательского интерфейса"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Основной layout с отступами
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)
        
        # ----- ЛЕВАЯ ПАНЕЛЬ -----
        settings_panel = QWidget()
        settings_layout = QVBoxLayout(settings_panel)
        settings_layout.setContentsMargins(0, 0, 0, 0)
        settings_layout.setSpacing(15)
        settings_panel.setFixedWidth(400)  # Увеличенная ширина левой панели
        
        # ----- БЛОК КАМЕРЫ И УПРАВЛЕНИЯ -----
        camera_group = QGroupBox("Камера и управление")
        camera_layout = QVBoxLayout(camera_group)
        camera_layout.setSpacing(12)
        
        # Выбор камеры (горизонтальный layout с увеличенным расстоянием)
        camera_selector_layout = QHBoxLayout()
        camera_selector_layout.setSpacing(10)
        camera_label = QLabel("Камера:")
        camera_label.setMinimumWidth(60)
        camera_selector_layout.addWidget(camera_label)
        self.camera_selector = QComboBox()
        self.camera_selector.addItem("Камера по умолчанию", 0)
        # Добавим поиск дополнительных камер
        for i in range(1, 5):
            try:
                cap = cv2.VideoCapture(i)
                if cap.isOpened():
                    self.camera_selector.addItem(f"Камера {i}", i)
                cap.release()
            except:
                pass
        camera_selector_layout.addWidget(self.camera_selector, 1) 
        camera_layout.addLayout(camera_selector_layout)
        
        # Кнопка запуска/остановки камеры (большая)
        self.camera_button = QPushButton("ЗАПУСТИТЬ КАМЕРУ")
        self.camera_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self.camera_button.setIconSize(QSize(24, 24))
        self.camera_button.setMinimumHeight(50) 
        self.camera_button.setStyleSheet("font-weight: bold;")
        self.camera_button.clicked.connect(self.toggle_camera)
        camera_layout.addWidget(self.camera_button)
        
        # Кнопка для просмотра информации о жестах (большая)
        self.show_gestures_info_button = QPushButton("СПРАВКА ПО ЖЕСТАМ")
        self.show_gestures_info_button.setIcon(self.style().standardIcon(QStyle.SP_MessageBoxInformation))
        self.show_gestures_info_button.setIconSize(QSize(24, 24))
        self.show_gestures_info_button.setMinimumHeight(50)
        self.show_gestures_info_button.clicked.connect(self.show_gestures_info)
        camera_layout.addWidget(self.show_gestures_info_button)
        
        settings_layout.addWidget(camera_group)
        
        # ----- БЛОК НАСТРОЕК РАСПОЗНАВАНИЯ -----
        recognition_group = QGroupBox("Настройки распознавания")
        recognition_layout = QGridLayout(recognition_group)
        recognition_layout.setSpacing(12)
        
        # Точность распознавания (с пояснением)
        sensitivity_label = QLabel("Точность распознавания:")
        sensitivity_label.setStyleSheet("font-weight: bold; margin-top: 5px;")
        recognition_layout.addWidget(sensitivity_label, 0, 0, 1, 3)
        
        # Пояснение что это такое
        sensitivity_explanation = QLabel("Выберите насколько точно будут распознаваться жесты")
        sensitivity_explanation.setStyleSheet("color: #8F8F8F; font-size: 10px; margin-bottom: 5px;")
        recognition_layout.addWidget(sensitivity_explanation, 1, 0, 1, 3)
        
        # Кнопки чувствительности в одну строку с равным распределением
        self.sensitivity_low = QPushButton("Низкая")
        self.sensitivity_low.setMinimumHeight(40)
        self.sensitivity_low.setToolTip("Жесты распознаются легко, но возможны ложные срабатывания")
        self.sensitivity_low.clicked.connect(lambda: self.set_sensitivity("low"))
        recognition_layout.addWidget(self.sensitivity_low, 2, 0)
        
        self.sensitivity_medium = QPushButton("Средняя")
        self.sensitivity_medium.setMinimumHeight(40)
        self.sensitivity_medium.setToolTip("Сбалансированное распознавание (рекомендуется)")
        self.sensitivity_medium.clicked.connect(lambda: self.set_sensitivity("medium"))
        self.sensitivity_medium.setStyleSheet("background-color: #007ACC;")
        recognition_layout.addWidget(self.sensitivity_medium, 2, 1)
        
        self.sensitivity_high = QPushButton("Высокая")
        self.sensitivity_high.setMinimumHeight(40)
        self.sensitivity_high.setToolTip("Жесты должны быть выполнены точно, меньше ложных срабатываний")
        self.sensitivity_high.clicked.connect(lambda: self.set_sensitivity("high"))
        recognition_layout.addWidget(self.sensitivity_high, 2, 2)
        
        # Задержка между действиями (регулируемая)
        cooldown_layout = QHBoxLayout()
        cooldown_label = QLabel("Задержка (сек):")
        cooldown_label.setStyleSheet("font-weight: bold;")
        cooldown_layout.addWidget(cooldown_label)
        
        self.action_cooldown_spinner = QDoubleSpinBox()
        self.action_cooldown_spinner.setMinimumHeight(30)
        self.action_cooldown_spinner.setRange(0.1, 5.0)
        self.action_cooldown_spinner.setSingleStep(0.1)
        self.action_cooldown_spinner.setValue(1.0)
        self.action_cooldown_spinner.valueChanged.connect(self.update_action_cooldown)
        cooldown_layout.addWidget(self.action_cooldown_spinner)
        recognition_layout.addLayout(cooldown_layout, 3, 0, 1, 3)
        
        # Кнопка применения настроек
        self.apply_settings_button = QPushButton("ПРИМЕНИТЬ НАСТРОЙКИ")
        self.apply_settings_button.setIcon(self.style().standardIcon(QStyle.SP_DialogApplyButton))
        self.apply_settings_button.setIconSize(QSize(24, 24))
        self.apply_settings_button.setMinimumHeight(50)
        self.apply_settings_button.clicked.connect(self.apply_mediapipe_settings)
        recognition_layout.addWidget(self.apply_settings_button, 4, 0, 1, 3)
        
        settings_layout.addWidget(recognition_group)
        
        # ----- БЛОК ЗАПИСИ ДАННЫХ -----
        recording_group = QGroupBox("Запись данных для обучения")
        recording_layout = QVBoxLayout(recording_group)
        recording_layout.setSpacing(12)
        
        # Режим записи
        recording_mode_layout = QHBoxLayout()
        recording_mode_layout.addWidget(QLabel("Режим:"))
        self.recording_mode_selector = QComboBox()
        self.recording_mode_selector.setMinimumHeight(30)
        self.recording_mode_selector.addItem("Нормальный режим", 0)
        self.recording_mode_selector.addItem("Запись жестов", 1)
        recording_mode_layout.addWidget(self.recording_mode_selector)
        recording_layout.addLayout(recording_mode_layout)
        
        # Выбор номера жеста (0-9)
        gesture_number_layout = QHBoxLayout()
        gesture_number_layout.addWidget(QLabel("Номер жеста (0-9):"))
        self.gesture_number_selector = QComboBox()
        self.gesture_number_selector.setMinimumHeight(30)
        for i in range(10):
            self.gesture_number_selector.addItem(f"Жест {i}", i)
        self.gesture_number_selector.setCurrentIndex(-1)
        gesture_number_layout.addWidget(self.gesture_number_selector)
        recording_layout.addLayout(gesture_number_layout)
        
        # Кнопка записи и прогресс
        self.record_button = QPushButton("НАЧАТЬ ЗАПИСЬ (3 СЕК)")
        self.record_button.setIcon(self.style().standardIcon(QStyle.SP_DialogSaveButton))
        self.record_button.setMinimumHeight(50)
        self.record_button.setEnabled(False)
        self.record_button.clicked.connect(self.toggle_recording)
        recording_layout.addWidget(self.record_button)
        
        # Прогресс-бар записи
        self.record_progress = QProgressBar()
        self.record_progress.setRange(0, 100)
        self.record_progress.setValue(0)
        self.record_progress.setTextVisible(True)
        self.record_progress.setFormat("Готов к записи")
        self.record_progress.setMinimumHeight(25)
        recording_layout.addWidget(self.record_progress)
        
        # Статус записи и счетчик кадров
        status_layout = QVBoxLayout()
        self.recording_status = QLabel("Статус: Нормальный режим")
        self.recording_status.setStyleSheet("color: #8F8F8F;")
        status_layout.addWidget(self.recording_status)
        
        self.frames_counter = QLabel("Записано кадров: 0")
        self.frames_counter.setStyleSheet("color: #8F8F8F;")
        status_layout.addWidget(self.frames_counter)
        recording_layout.addLayout(status_layout)
        
        settings_layout.addWidget(recording_group)
        
        # ----- БЛОК ДОСТУПНЫХ ЖЕСТОВ -----
        gesture_group = QGroupBox("Доступные жесты")
        gesture_layout = QVBoxLayout(gesture_group)
        
        # Список жестов
        self.gesture_list = QListWidget()
        self.gesture_list.setStyleSheet("min-height: 150px;")
        gesture_layout.addWidget(self.gesture_list)
        
        settings_layout.addWidget(gesture_group)
        
        # ----- БЛОК НАСТРОЙКИ ЖЕСТА -----
        action_group = QGroupBox("Настройка действия")
        action_layout = QGridLayout(action_group)
        action_layout.setSpacing(10)
        
        # Выбор жеста и действия
        action_layout.addWidget(QLabel("Жест:"), 0, 0)
        self.action_gesture_selector = QComboBox()
        self.action_gesture_selector.setMinimumHeight(30)
        action_layout.addWidget(self.action_gesture_selector, 0, 1)
        
        action_layout.addWidget(QLabel("Действие:"), 1, 0)
        self.action_type_selector = QComboBox()
        self.action_type_selector.setMinimumHeight(30)
        action_layout.addWidget(self.action_type_selector, 1, 1)
        
        # Загрузка доступных действий
        for action in self.gesture_actions.get_available_actions():
            self.action_type_selector.addItem(action["name"], action["id"])
        
        # Кнопка сохранения настроек действия
        self.save_action_button = QPushButton("СОХРАНИТЬ ДЕЙСТВИЕ")
        self.save_action_button.setIcon(self.style().standardIcon(QStyle.SP_DialogSaveButton))
        self.save_action_button.setMinimumHeight(50)
        self.save_action_button.clicked.connect(self.save_action_mapping)
        action_layout.addWidget(self.save_action_button, 2, 0, 1, 2)
        
        settings_layout.addWidget(action_group)
        
        # Добавляем левую панель в основной layout
        main_layout.addWidget(settings_panel)
        
        # ----- ПРАВАЯ ПАНЕЛЬ (ВИДЕО + ИНФОРМАЦИЯ) -----
        video_panel = QWidget()
        video_layout = QVBoxLayout(video_panel)
        video_layout.setContentsMargins(0, 0, 0, 0)
        video_layout.setSpacing(15)
        
        # ----- ВИДЕО ПОТОК -----
        processed_group = QGroupBox("Распознавание жестов")
        processed_layout = QVBoxLayout(processed_group)
        self.processed_feed = QLabel()
        self.processed_feed.setAlignment(Qt.AlignCenter)
        self.processed_feed.setMinimumSize(640, 480)
        self.processed_feed.setStyleSheet("background-color: #1E1E1E; border-radius: 5px; padding: 5px;")
        processed_layout.addWidget(self.processed_feed)
        video_layout.addWidget(processed_group)
        
        # ----- ИНФОРМАЦИОННЫЙ БЛОК -----
        info_panel = QWidget()
        info_layout = QHBoxLayout(info_panel)
        info_layout.setContentsMargins(0, 0, 0, 0)
        
        # Текущий жест (крупный шрифт)
        current_gesture_group = QGroupBox("Текущий жест")
        current_gesture_layout = QVBoxLayout(current_gesture_group)
        self.current_gesture_label = QLabel("Нет")
        self.current_gesture_label.setFont(QFont("Arial", 24, QFont.Bold))
        self.current_gesture_label.setStyleSheet("color: #3C9EFF;")
        self.current_gesture_label.setAlignment(Qt.AlignCenter)
        current_gesture_layout.addWidget(self.current_gesture_label)
        info_layout.addWidget(current_gesture_group)
        
        # Текущее действие
        current_action_group = QGroupBox("Текущее действие")
        current_action_layout = QVBoxLayout(current_action_group)
        self.current_action_label = QLabel("Нет")
        self.current_action_label.setFont(QFont("Arial", 20))
        self.current_action_label.setStyleSheet("color: #3C9EFF;")
        self.current_action_label.setAlignment(Qt.AlignCenter)
        current_action_layout.addWidget(self.current_action_label)
        info_layout.addWidget(current_action_group)
        
        # Лог событий
        log_group = QGroupBox("Лог событий")
        log_layout = QVBoxLayout(log_group)
        self.event_log = QListWidget()
        self.event_log.setMaximumHeight(150)
        log_layout.addWidget(self.event_log)
        info_layout.addWidget(log_group)
        
        video_layout.addWidget(info_panel)
        
        # ----- КНОПКИ УПРАВЛЕНИЯ -----
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)
        
        # Кнопка запуска/паузы распознавания
        self.recognition_button = QPushButton("ЗАПУСТИТЬ РАСПОЗНАВАНИЕ")
        self.recognition_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self.recognition_button.setIconSize(QSize(24, 24))
        self.recognition_button.setMinimumHeight(50)
        self.recognition_button.setEnabled(False)
        buttons_layout.addWidget(self.recognition_button)
        
        video_layout.addLayout(buttons_layout)
        
        # Добавляем правую панель в основной layout
        main_layout.addWidget(video_panel, 2)
        
        # Подключение сигналов
        self.action_gesture_selector.currentIndexChanged.connect(self.update_action_selector)
        self.recording_mode_selector.currentIndexChanged.connect(self.on_recording_mode_change)
        self.gesture_number_selector.currentIndexChanged.connect(self.on_gesture_number_change)
        
    def set_sensitivity(self, level):
        """Установка предустановленных уровней чувствительности"""
        # Сбрасываем стили всех кнопок
        self.sensitivity_low.setStyleSheet("")
        self.sensitivity_medium.setStyleSheet("")
        self.sensitivity_high.setStyleSheet("")
        
        # Храним настройки как атрибуты класса вместо слайдеров
        if level == "low":
            self.detection_conf = 0.9
            self.tracking_conf = 0.8
            self.sensitivity_low.setStyleSheet("background-color: #007ACC;")
            self.log_event("Установлена низкая чувствительность")
        elif level == "medium":
            self.detection_conf = 0.7
            self.tracking_conf = 0.5
            self.sensitivity_medium.setStyleSheet("background-color: #007ACC;")
            self.log_event("Установлена средняя чувствительность")
        elif level == "high":
            self.detection_conf = 0.5
            self.tracking_conf = 0.3
            self.sensitivity_high.setStyleSheet("background-color: #007ACC;")
            self.log_event("Установлена высокая чувствительность")
            
    def toggle_camera(self):
        """Переключение состояния камеры (включение/выключение)"""
        if not self.video_thread.is_running:
            # Запуск камеры
            camera_id = self.camera_selector.currentData()
            if self.video_thread.start_camera(camera_id, self.camera_width, self.camera_height):
                self.camera_button.setText("ОСТАНОВИТЬ КАМЕРУ")
                self.camera_button.setIcon(self.style().standardIcon(QStyle.SP_MediaStop))
                self.recognition_button.setEnabled(True)
                self.log_event("Камера запущена")
            else:
                QMessageBox.critical(self, "Ошибка", "Не удалось запустить камеру!")
        else:
            # Остановка камеры
            self.video_thread.stop_camera()
            self.camera_button.setText("ЗАПУСТИТЬ КАМЕРУ")
            self.camera_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
            self.recognition_button.setEnabled(False)
            self.processed_feed.clear()
            self.log_event("Камера остановлена")
            
    def update_camera_feed(self, frame):
        """Обновление изображения с камеры"""
        h, w, ch = frame.shape
        bytes_per_line = ch * w
        qt_image = QImage(frame.data, w, h, bytes_per_line, QImage.Format_RGB888).rgbSwapped()
        pixmap = QPixmap.fromImage(qt_image)
        
        # Добавляем границу к изображению
        self.processed_feed.setPixmap(pixmap.scaled(
            self.processed_feed.width(), self.processed_feed.height(),
            Qt.KeepAspectRatio, Qt.SmoothTransformation))
            
    def update_processed_feed(self, frame, data):
        """Обновление обработанного изображения и информации о распознавании"""
        h, w, ch = frame.shape
        bytes_per_line = ch * w
        qt_image = QImage(frame.data, w, h, bytes_per_line, QImage.Format_RGB888).rgbSwapped()
        pixmap = QPixmap.fromImage(qt_image)
        
        # Добавляем обработанное изображение с границей
        self.processed_feed.setPixmap(pixmap.scaled(
            self.processed_feed.width(), self.processed_feed.height(),
            Qt.KeepAspectRatio, Qt.SmoothTransformation))
            
        # Проверяем, был ли записан кадр или возникла ошибка
        if "frame_recorded" in data:
            if "error" in data:
                self.update_recording_status(error_message=data["error"])
            else:
                self.update_recording_status(frame_recorded=data["frame_recorded"])
            
        # Обновление информации о распознанном жесте и действии
        if "hand_sign" in data:
            gesture_name = data["hand_sign"]
            self.current_gesture_label.setText(gesture_name)
            
            # Визуальное выделение текущего жеста в списке
            for i in range(self.gesture_list.count()):
                item = self.gesture_list.item(i)
                if item.text() == gesture_name:
                    item.setBackground(QColor(0, 122, 204, 100))
                    item.setForeground(QColor(255, 255, 255))
                else:
                    item.setBackground(QColor(0, 0, 0, 0))
                    item.setForeground(QColor(230, 230, 230))
            
            # Если есть действие для этого жеста, выполняем его
            if gesture_name in self.gesture_actions.actions_mapping:
                action_config = self.gesture_actions.actions_mapping[gesture_name]
                action_type = action_config["action"]
                
                # Отображаем понятное описание действия вместо технического имени
                action_display = self.get_action_display_name(action_type, action_config["params"])
                self.current_action_label.setText(action_display)
                
                # Добавляем запись о выполнении действия в лог
                self.log_event(f"Жест распознан: {gesture_name} → {action_display}")
                
                # Если есть координаты указательного пальца, передаем их
                x_pos, y_pos = None, None
                if "index_finger_tip" in data:
                    x_pos, y_pos = data["index_finger_tip"]
                    
                # Выполнение действия
                self.gesture_actions.execute_action(gesture_name, x_pos, y_pos)
            else:
                self.current_action_label.setText("Нет")
                
    def get_action_display_name(self, action_type, params=None):
        """Возвращает понятное название действия для интерфейса"""
        if action_type == "none":
            return "Нет действия"
        elif action_type == "custom_hotkey":
            if params and "hotkey" in params:
                hotkey = "+".join(params["hotkey"])
                return f"Комбинация клавиш: {hotkey}"
            return "Комбинация клавиш"
        elif action_type == "click":
            return "Клик мыши"
        elif action_type == "double_click":
            return "Двойной клик мыши"
        elif action_type == "right_click":
            return "Правый клик мыши"
        elif action_type == "scroll_up":
            return "Прокрутка вверх"
        elif action_type == "scroll_down":
            return "Прокрутка вниз"
        elif action_type == "drag":
            return "Перетаскивание"
        elif action_type == "app_execute":
            if params and "path" in params:
                app_name = params["path"].split("/")[-1]
                return f"Запуск приложения: {app_name}"
            return "Запуск приложения"
        # Возвращаем оригинальное название, если неизвестный тип
        return action_type

    def apply_mediapipe_settings(self):
        """Применение настроек MediaPipe"""
        static_mode = False  # Статичный режим всегда выключен в новом интерфейсе
        
        # Используем значения, сохраненные при выборе чувствительности
        self.video_thread.update_settings(
            static_mode=static_mode,
            min_detection_conf=self.detection_conf,
            min_tracking_conf=self.tracking_conf
        )
        
        # Всплывающее уведомление
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Information)
        msg.setWindowTitle("Настройки применены")
        msg.setText("Настройки распознавания обновлены!")
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec_()
        
        self.log_event(f"Настройки применены: обнаружение={self.detection_conf}, трекинг={self.tracking_conf}")
     
    def load_initial_settings(self):
        """Загрузка начальных значений настроек"""
        # Инициализируем значения перед вызовом set_sensitivity
        self.detection_conf = 0.7
        self.tracking_conf = 0.5
        
        # Устанавливаем средний уровень чувствительности по умолчанию 
        # (теперь это безопасно, так как значения уже инициализированы)
        self.set_sensitivity("medium")
        
        # Начальная задержка между действиями
        self.action_cooldown_spinner.setValue(1.0)  # 1 секунда по умолчанию
        self.gesture_actions.set_action_cooldown(1.0)
        
        # Логирование загрузки настроек
        self.log_event("Загружены начальные настройки")

    def load_gesture_list(self):
        """Загрузка списка жестов из CSV-файла"""
        try:
            label_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                'model', 'keypoint_classifier', 'keypoint_classifier_label.csv'
            )
            
            with open(label_path, 'r', encoding='utf-8-sig') as f:
                lines = f.readlines()
                gestures = [line.strip() for line in lines if line.strip()]
                
                # Очистка списков
                self.gesture_list.clear()
                self.action_gesture_selector.clear()
                
                # Заполнение списков
                for gesture in gestures:
                    # Добавляем в список жестов с выделением
                    item = QListWidgetItem(gesture)
                    action_display = "Нет"
                    
                    # Проверяем, есть ли действие для этого жеста
                    if gesture in self.gesture_actions.actions_mapping:
                        action_config = self.gesture_actions.actions_mapping[gesture]
                        action_type = action_config["action"]
                        action_display = self.get_action_display_name(action_type, action_config["params"])
                        
                    item.setToolTip(f"Жест: {gesture}\nДействие: {action_display}")
                    self.gesture_list.addItem(item)
                    self.action_gesture_selector.addItem(gesture)
                    
                self.log_event(f"Загружено {len(gestures)} жестов")
                    
        except Exception as e:
            QMessageBox.warning(self, "Ошибка загрузки жестов", f"Не удалось загрузить список жестов: {str(e)}")
            
    def load_action_mappings(self):
        """Загрузка настроек действий для жестов"""
        # Здесь конфигурация уже загружена в self.gesture_actions
        self.update_action_selector()
        self.log_event("Загружены настройки действий для жестов")
        
    def update_action_selector(self):
        """Обновление выбора действия при изменении жеста"""
        gesture = self.action_gesture_selector.currentText()
        if not gesture:
            return
            
        # Выбираем соответствующее действие в селекторе
        action_type = "none"
        if gesture in self.gesture_actions.actions_mapping:
            action_type = self.gesture_actions.actions_mapping[gesture]["action"]
            
        # Находим индекс действия
        index = self.action_type_selector.findData(action_type)
        if index >= 0:
            self.action_type_selector.setCurrentIndex(index)
            
    def save_action_mapping(self):
        """Сохранение настройки действия для жеста"""
        gesture = self.action_gesture_selector.currentText()
        action_type = self.action_type_selector.currentData()
        
        if not gesture or not action_type:
            return
            
        # Сохраняем настройку
        self.gesture_actions.add_gesture_action(gesture, action_type)
        
        # Обновляем подсказку для элемента в списке жестов
        for i in range(self.gesture_list.count()):
            item = self.gesture_list.item(i)
            if item.text() == gesture:
                item.setToolTip(f"Жест: {gesture}\nДействие: {action_type}")
                break
        
        # Показываем уведомление
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Information)
        msg.setWindowTitle("Настройка сохранена")
        msg.setText(f"Для жеста '{gesture}' установлено действие '{action_type}'")
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec_()
        
        self.log_event(f"Настройка действия сохранена: {gesture} → {action_type}")
    
    def log_event(self, message):
        """Добавление сообщения в лог событий"""
        item = QListWidgetItem(message)
        
        # определение типа сообщения по ключевым словам
        if "ошибка" in message.lower() or "не удалось" in message.lower():
            item.setForeground(QColor(255, 99, 71))  # Красный для ошибок
        elif "жест распознан" in message.lower():
            item.setForeground(QColor(50, 205, 50))  # Зеленый для распознавания
        elif "настройка" in message.lower() or "применены" in message.lower():
            item.setForeground(QColor(135, 206, 250))  # Голубой для настроек
            
        # Добавление сообщения в лог
        current_time = QApplication.instance().translate("Time", "Now: ") + \
                      QTime.currentTime().toString('hh:mm:ss')
        item.setToolTip(current_time)
        
        self.event_log.addItem(item)
        self.event_log.scrollToBottom()

    def update_action_cooldown(self):
        """Обновление задержки между действиями"""
        cooldown = self.action_cooldown_spinner.value()
        self.gesture_actions.set_action_cooldown(cooldown)
        self.log_event(f"Установлена задержка между действиями: {cooldown} сек")

    def show_gestures_info(self):
        """Отображает информацию о доступных жестах и их действиях"""
        gestures_info = []
        
        # Получаем список всех жестов и действий
        for gesture_name in self.gesture_actions.actions_mapping:
            action_info = self.gesture_actions.actions_mapping[gesture_name]
            
            if action_info:
                action_type = action_info["action"]
                action_params = action_info["params"]
                action_display = self.get_action_display_name(action_type, action_params)
                
                # Используем названия жестов на русском языке из файла меток
                gesture_display = gesture_name
                
                gestures_info.append((gesture_display, action_display))
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Справка по жестам IDE")
        dialog.setMinimumWidth(600)
        dialog.setMinimumHeight(400)
        dialog.setStyleSheet("background-color: #2D2D30; color: #E6E6E6;")
        
        layout = QVBoxLayout(dialog)
        
        # Создаем таблицу
        table = QTableWidget()
        table.setColumnCount(2)
        table.setRowCount(len(gestures_info))
        table.setHorizontalHeaderLabels(["Жест", "Действие"])
        
        # Настраиваем заголовки
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setStyleSheet("QHeaderView::section {background-color: #007ACC; color: white; padding: 5px; border: 1px solid #3F3F46;}")
        
        # Настраиваем вертикальный заголовок
        table.verticalHeader().setVisible(False)
        
        # Заполняем таблицу
        for row, (gesture, action) in enumerate(gestures_info):
            # Жест
            gesture_item = QTableWidgetItem(gesture)
            gesture_item.setForeground(QColor("#E6E6E6"))
            gesture_item.setFont(QFont("Arial", 10, QFont.Bold))
            table.setItem(row, 0, gesture_item)
            
            # Действие
            action_item = QTableWidgetItem(action)
            action_item.setForeground(QColor("#E6E6E6"))
            table.setItem(row, 1, action_item)
        
        layout.addWidget(table)
        
        # Добавляем информационный текст
        info_label = QLabel("Чтобы изменить действие, перейдите в раздел <b>Настройка действия</b>.")
        info_label.setStyleSheet("color: #E6E6E6; margin: 10px;")
        info_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(info_label)
        
        # Кнопка закрытия
        close_button = QPushButton("Закрыть")
        close_button.setStyleSheet("background-color: #007ACC; color: white; padding: 5px 15px;")
        close_button.clicked.connect(dialog.close)
        layout.addWidget(close_button)
        
        dialog.exec_()

    def show_recording_notification(self, success=True, error_message=None):
        """Показать уведомление о записи данных"""
        msg = QMessageBox(self)
        
        if success:
            msg.setIcon(QMessageBox.Information)
            msg.setWindowTitle("Запись данных")
            msg.setText(f"Успешно записано {self.recorded_frames} кадров для жеста {self.gesture_number_selector.currentText()}")
        else:
            msg.setIcon(QMessageBox.Warning)
            msg.setWindowTitle("Ошибка записи")
            msg.setText(f"Ошибка при записи данных: {error_message}")
            
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec_()
        
    def update_recording_status(self, frame_recorded=False, error_message=None):
        """Обновление статуса записи и счетчика кадров"""
        if error_message:
            self.show_recording_notification(success=False, error_message=error_message)
            return
            
        if frame_recorded and self.is_recording:
            self.recorded_frames += 1
            self.frames_counter.setText(f"Записано кадров: {self.recorded_frames}")
            
    def on_recording_mode_change(self, index):
        """Обработчик изменения режима записи"""
        mode = self.recording_mode_selector.currentData()
        
        if mode == 1:  # Режим записи
            self.recording_status.setText("Статус: Режим записи жестов")
            self.recording_status.setStyleSheet("color: #FF6B6B;")  # Красный цвет для записи
            self.gesture_number_selector.setEnabled(True)
            self.record_button.setEnabled(True)
            self.recorded_frames = 0
            self.frames_counter.setText("Записано кадров: 0")
            
            # Показываем инструкцию по записи
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Information)
            msg.setWindowTitle("Режим записи")
            msg.setText("Инструкция по записи данных:\n\n"
                       "1. Выберите номер жеста (0-9)\n"
                       "2. Нажмите кнопку 'НАЧАТЬ ЗАПИСЬ'\n"
                       "3. Покажите и удерживайте жест 3 секунды\n"
                       "4. Запись остановится автоматически\n"
                       "5. Повторите для других вариаций жеста")
            msg.setStandardButtons(QMessageBox.Ok)
            msg.exec_()
        else:  # Нормальный режим
            if self.is_recording:
                self.toggle_recording()  # Останавливаем запись если она идет
                
            self.recording_status.setText("Статус: Нормальный режим")
            self.recording_status.setStyleSheet("color: #8F8F8F;")
            self.gesture_number_selector.setEnabled(False)
            self.record_button.setEnabled(False)
            self.gesture_number_selector.setCurrentIndex(-1)
            self.record_progress.setValue(0)
            self.record_progress.setFormat("Готов к записи")
            
        # Обновляем режим в процессоре жестов
        if self.video_thread.processor:
            self.video_thread.processor.set_mode(mode)
            self.log_event(f"Режим изменен на: {'Запись жестов' if mode == 1 else 'Нормальный режим'}")
            
    def on_gesture_number_change(self, index):
        """Обработчик изменения номера жеста для записи"""
        if index >= 0:
            number = self.gesture_number_selector.currentData()
            if self.video_thread.processor:
                self.video_thread.processor.set_number(number)
                self.log_event(f"Выбран жест для записи: {number}")
                
    def toggle_recording(self):
        """Переключение состояния записи данных"""
        if not self.is_recording:
            self.is_recording = True
            self.recording_start_time = QTime.currentTime().msecsSinceStartOfDay()
            self.record_button.setText("ОСТАНОВИТЬ ЗАПИСЬ")
            self.record_button.setIcon(self.style().standardIcon(QStyle.SP_DialogCancelButton))  # Иконка для остановки
            self.log_event("Запись данных начата")
        else:
            self.is_recording = False
            self.record_button.setText("НАЧАТЬ ЗАПИСЬ (3 СЕК)")
            self.record_button.setIcon(self.style().standardIcon(QStyle.SP_DialogSaveButton))  # Возвращаем иконку записи
            self.log_event("Запись данных остановлена")

    def update_recording_progress(self):
        """Обновление прогресса записи данных"""
        if self.is_recording:
            current_time = QTime.currentTime().msecsSinceStartOfDay()
            elapsed_time = current_time - self.recording_start_time
            progress = min(100, int(elapsed_time / self.RECORD_DURATION * 100))
            
            # Обновляем прогресс-бар
            self.record_progress.setValue(progress)
            self.record_progress.setFormat(f"Запись: {progress}%")
            
            # Если время записи истекло
            if elapsed_time >= self.RECORD_DURATION:
                self.toggle_recording()  # Останавливаем запись
                self.show_recording_notification(success=True)
                

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_()) 