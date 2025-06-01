import sys
import os
import cv2
import numpy as np
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                           QLabel, QPushButton, QComboBox, QGroupBox, QGridLayout, 
                           QTabWidget, QListWidget, QListWidgetItem, QTableWidget, 
                           QTableWidgetItem, QCheckBox, QSlider, QMessageBox,
                           QDoubleSpinBox, QStyle, QStyleFactory, QDialog, QHeaderView,
                           QLineEdit)
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
    margin-top: 5px;           /* отступ сверху */
    font-weight: bold;          /* жирный текст */
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
        self.setInterval(30)  # 30 мс - где-то 30 фпс
        
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


class AddGestureDialog(QDialog):
    """Диалог для добавления нового жеста"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Добавление нового жеста")
        self.setMinimumWidth(400)
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Описание
        description = QLabel(
            "Введите название нового жеста. После добавления жеста:\n"
            "1. Запишите данные для жеста в режиме записи\n"
            "2. Запустите ноутбук keypoint_classification_EN.ipynb\n"
            "3. Выполните Restart & Run All для обучения модели"
        )
        description.setWordWrap(True)
        description.setStyleSheet("color: #E6E6E6; padding: 10px; background-color: #3E3E42; border-radius: 5px;")
        layout.addWidget(description)
        
        # поле ввода названия
        name_layout = QHBoxLayout()
        name_label = QLabel("Название жеста:")
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Введите название жеста")
        name_layout.addWidget(name_label)
        name_layout.addWidget(self.name_input)
        layout.addLayout(name_layout)
        
        # кнопки
        button_layout = QHBoxLayout()
        save_button = QPushButton("Сохранить")
        save_button.clicked.connect(self.accept)
        cancel_button = QPushButton("Отмена")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(save_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)
        
    def get_gesture_name(self):
        return self.name_input.text().strip()


class MainWindow(QMainWindow):
    """Главное окно приложения"""
    def __init__(self):
        super().__init__()
        
        self.camera_id = 0
        self.camera_width = 640
        self.camera_height = 480
        
        self.recorded_frames = 0
        
        self.apply_styles()
        
        self.setWindowTitle("Hand Gesture Controller")
        self.setMinimumSize(1200, 800)
        
        self.gesture_actions = GestureActions()
        
        self.init_ui()
        
        self.load_initial_settings()
        
        self.video_thread = VideoThread(self)
        self.video_thread.processed_ready.connect(self.update_processed_feed)
        
        self.load_gesture_list()
        
        self.load_action_mappings()
        
    def apply_styles(self):
        """Применение стилей и настройка темы"""
        QApplication.setStyle(QStyleFactory.create("Fusion"))
        
        self.setStyleSheet(STYLE)
        
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
        
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)
        
        settings_panel = QWidget()
        settings_layout = QVBoxLayout(settings_panel)
        settings_layout.setContentsMargins(0, 0, 0, 0)
        settings_layout.setSpacing(15)
        settings_panel.setFixedWidth(300)
        
        self.event_log = QListWidget()
        self.event_log.setMaximumHeight(100)
        
        camera_group = QGroupBox("Камера и управление")
        camera_layout = QVBoxLayout(camera_group)
        camera_layout.setSpacing(12)
        
        camera_selector_layout = QHBoxLayout()
        camera_selector_layout.addWidget(QLabel("Камера:"))
        self.camera_selector = QComboBox()
        self.camera_selector.addItem("Камера по умолчанию", 0)
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
        
        self.camera_button = QPushButton("ЗАПУСТИТЬ КАМЕРУ")
        self.camera_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self.camera_button.setIconSize(QSize(24, 24))
        self.camera_button.setMinimumHeight(40) 
        self.camera_button.setStyleSheet("font-weight: bold;")
        self.camera_button.clicked.connect(self.toggle_camera)
        camera_layout.addWidget(self.camera_button)
        
        self.show_gestures_info_button = QPushButton("СПРАВКА ПО ЖЕСТАМ")
        self.show_gestures_info_button.setIcon(self.style().standardIcon(QStyle.SP_MessageBoxInformation))
        self.show_gestures_info_button.setIconSize(QSize(24, 24))
        self.show_gestures_info_button.setMinimumHeight(40)
        self.show_gestures_info_button.clicked.connect(self.show_gestures_info)
        camera_layout.addWidget(self.show_gestures_info_button)
        
        # добавляем кнопку для создания нового жеста
        self.add_gesture_button = QPushButton("ДОБАВИТЬ НОВЫЙ ЖЕСТ")
        self.add_gesture_button.setIcon(self.style().standardIcon(QStyle.SP_FileIcon))
        self.add_gesture_button.setIconSize(QSize(24, 24))
        self.add_gesture_button.setMinimumHeight(40)
        self.add_gesture_button.clicked.connect(self.show_add_gesture_dialog)
        camera_layout.addWidget(self.add_gesture_button)
        
        settings_layout.addWidget(camera_group)
        
        recognition_group = QGroupBox("Настройки распознавания")
        recognition_layout = QVBoxLayout(recognition_group)
        recognition_layout.setSpacing(12)
        
        sensitivity_label = QLabel("Точность распознавания:")
        sensitivity_label.setStyleSheet("font-weight: bold; margin-top: 5px;")
        recognition_layout.addWidget(sensitivity_label)
        
        sensitivity_explanation = QLabel("Выберите насколько точно будут распознаваться жесты")
        sensitivity_explanation.setStyleSheet("color: #8F8F8F; font-size: 10px; margin-bottom: 5px;")
        recognition_layout.addWidget(sensitivity_explanation)
        
        sensitivity_buttons = QHBoxLayout()
        self.sensitivity_low = QPushButton("Низкая")
        self.sensitivity_low.setToolTip("Жесты распознаются легко, но возможны ложные срабатывания")
        self.sensitivity_low.clicked.connect(lambda: self.set_sensitivity("low"))
        sensitivity_buttons.addWidget(self.sensitivity_low)
        
        self.sensitivity_medium = QPushButton("Средняя")
        self.sensitivity_medium.setToolTip("Сбалансированное распознавание (рекомендуется)")
        self.sensitivity_medium.clicked.connect(lambda: self.set_sensitivity("medium"))
        self.sensitivity_medium.setStyleSheet("background-color: #007ACC;")
        sensitivity_buttons.addWidget(self.sensitivity_medium)
        
        self.sensitivity_high = QPushButton("Высокая")
        self.sensitivity_high.setToolTip("Жесты должны быть выполнены точно, меньше ложных срабатываний")
        self.sensitivity_high.clicked.connect(lambda: self.set_sensitivity("high"))
        sensitivity_buttons.addWidget(self.sensitivity_high)
        
        recognition_layout.addLayout(sensitivity_buttons)
        
        cooldown_layout = QHBoxLayout()
        cooldown_label = QLabel("Задержка (сек):")
        cooldown_label.setStyleSheet("font-weight: bold;")
        cooldown_layout.addWidget(cooldown_label)
        
        self.action_cooldown_spinner = QDoubleSpinBox()
        self.action_cooldown_spinner.setRange(0.1, 5.0)
        self.action_cooldown_spinner.setSingleStep(0.1)
        self.action_cooldown_spinner.setValue(1.0)
        self.action_cooldown_spinner.valueChanged.connect(self.update_action_cooldown)
        cooldown_layout.addWidget(self.action_cooldown_spinner)
        
        recognition_layout.addLayout(cooldown_layout)
        
        self.apply_settings_button = QPushButton("ПРИМЕНИТЬ НАСТРОЙКИ")
        self.apply_settings_button.setIcon(self.style().standardIcon(QStyle.SP_DialogApplyButton))
        self.apply_settings_button.setIconSize(QSize(24, 24))
        self.apply_settings_button.setMinimumHeight(40)
        self.apply_settings_button.clicked.connect(self.apply_mediapipe_settings)
        recognition_layout.addWidget(self.apply_settings_button)
        
        settings_layout.addWidget(recognition_group)
        
        recording_group = QGroupBox("Запись данных для обучения")
        recording_layout = QVBoxLayout(recording_group)
        recording_layout.setSpacing(12)
        
        recording_mode_layout = QHBoxLayout()
        recording_mode_layout.addWidget(QLabel("Режим:"))
        self.recording_mode_selector = QComboBox()
        self.recording_mode_selector.addItem("Нормальный режим", 0)
        self.recording_mode_selector.addItem("Запись жестов", 1)
        recording_mode_layout.addWidget(self.recording_mode_selector)
        recording_layout.addLayout(recording_mode_layout)
        
        gesture_number_layout = QHBoxLayout()
        gesture_number_layout.addWidget(QLabel("Номер жеста:"))
        self.gesture_number_selector = QComboBox()
        self.update_gesture_numbers()
        self.gesture_number_selector.setCurrentIndex(-1)
        gesture_number_layout.addWidget(self.gesture_number_selector)
        recording_layout.addLayout(gesture_number_layout)
        
        self.record_gesture_button = QPushButton("ЗАПИСАТЬ ЖЕСТ")
        self.record_gesture_button.setIcon(self.style().standardIcon(QStyle.SP_DialogSaveButton))
        self.record_gesture_button.setEnabled(False)
        self.record_gesture_button.clicked.connect(self.record_gesture)
        recording_layout.addWidget(self.record_gesture_button)
        
        self.recording_status = QLabel("Статус: Нормальный режим")
        self.recording_status.setStyleSheet("color: #8F8F8F;")
        recording_layout.addWidget(self.recording_status)
        
        self.frames_counter = QLabel("Записано кадров: 0")
        self.frames_counter.setStyleSheet("color: #8F8F8F;")
        recording_layout.addWidget(self.frames_counter)
        
        settings_layout.addWidget(recording_group)
        
        action_group = QGroupBox("Настройка действия")
        action_layout = QGridLayout(action_group)
        action_layout.setSpacing(10)
        
        action_layout.addWidget(QLabel("Жест:"), 0, 0)
        self.action_gesture_selector = QComboBox()
        action_layout.addWidget(self.action_gesture_selector, 0, 1)
        
        action_layout.addWidget(QLabel("Действие:"), 1, 0)
        self.action_type_selector = QComboBox()
        action_layout.addWidget(self.action_type_selector, 1, 1)
        
        for action in self.gesture_actions.get_available_actions():
            self.action_type_selector.addItem(action["name"], action["id"])
        
        self.save_action_button = QPushButton("СОХРАНИТЬ ДЕЙСТВИЕ")
        self.save_action_button.setIcon(self.style().standardIcon(QStyle.SP_DialogSaveButton))
        self.save_action_button.setMinimumHeight(40)
        self.save_action_button.clicked.connect(self.save_action_mapping)
        action_layout.addWidget(self.save_action_button, 2, 0, 1, 2)
        
        settings_layout.addWidget(action_group)
        
        main_layout.addWidget(settings_panel)
        
        video_panel = QWidget()
        video_layout = QVBoxLayout(video_panel)
        video_layout.setContentsMargins(0, 0, 0, 0)
        video_layout.setSpacing(15)
        
        processed_group = QGroupBox("Распознавание жестов")
        processed_layout = QVBoxLayout(processed_group)
        self.processed_feed = QLabel()
        self.processed_feed.setAlignment(Qt.AlignCenter)
        self.processed_feed.setMinimumSize(640, 480)
        self.processed_feed.setStyleSheet("background-color: #1E1E1E; border-radius: 5px; padding: 5px;")
        processed_layout.addWidget(self.processed_feed)
        video_layout.addWidget(processed_group, 1)
        
        info_panel = QWidget()
        info_layout = QHBoxLayout(info_panel)
        info_layout.setContentsMargins(0, 0, 0, 0)
        
        current_gesture_group = QGroupBox("Текущий жест")
        current_gesture_group.setMinimumWidth(200)
        current_gesture_layout = QVBoxLayout(current_gesture_group)
        self.current_gesture_label = QLabel("Нет")
        self.current_gesture_label.setFont(QFont("Arial", 20, QFont.Bold))
        self.current_gesture_label.setStyleSheet("color: #3C9EFF;")
        self.current_gesture_label.setAlignment(Qt.AlignCenter)
        current_gesture_layout.addWidget(self.current_gesture_label)
        info_layout.addWidget(current_gesture_group)
        
        current_action_group = QGroupBox("Текущее действие")
        current_action_group.setMinimumWidth(300)
        current_action_layout = QVBoxLayout(current_action_group)
        self.current_action_label = QLabel("Нет")
        self.current_action_label.setFont(QFont("Arial", 16))
        self.current_action_label.setStyleSheet("color: #3C9EFF;")
        self.current_action_label.setAlignment(Qt.AlignCenter)
        current_action_layout.addWidget(self.current_action_label)
        info_layout.addWidget(current_action_group)
        
        log_group = QGroupBox("Лог событий")
        log_layout = QVBoxLayout(log_group)
        log_layout.addWidget(self.event_log)
        info_layout.addWidget(log_group)
        
        video_layout.addWidget(info_panel)
        
        main_layout.addWidget(video_panel, 3)
        
        self.action_gesture_selector.currentIndexChanged.connect(self.update_action_selector)
        self.recording_mode_selector.currentIndexChanged.connect(self.on_recording_mode_change)
        self.gesture_number_selector.currentIndexChanged.connect(self.on_gesture_number_change)
        
    def set_sensitivity(self, level):
        """Установка предустановленных уровней чувствительности"""
        self.sensitivity_low.setStyleSheet("")
        self.sensitivity_medium.setStyleSheet("")
        self.sensitivity_high.setStyleSheet("")
        
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
            camera_id = self.camera_selector.currentData()
            if self.video_thread.start_camera(camera_id, self.camera_width, self.camera_height):
                self.camera_button.setText("ОСТАНОВИТЬ КАМЕРУ")
                self.camera_button.setIcon(self.style().standardIcon(QStyle.SP_MediaStop))
                self.log_event("Камера запущена")
            else:
                QMessageBox.critical(self, "Ошибка", "Не удалось запустить камеру!")
        else:
            self.video_thread.stop_camera()
            self.camera_button.setText("ЗАПУСТИТЬ КАМЕРУ")
            self.camera_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
            self.processed_feed.clear()
            self.log_event("Камера остановлена")
            
    def update_processed_feed(self, frame, data):
        """Обновление обработанного изображения и информации о распознавании"""
        self._last_frame_data = data
        
        h, w, ch = frame.shape
        bytes_per_line = ch * w
        qt_image = QImage(frame.data, w, h, bytes_per_line, QImage.Format_RGB888).rgbSwapped()
        pixmap = QPixmap.fromImage(qt_image)
        
        self.processed_feed.setPixmap(pixmap.scaled(
            self.processed_feed.width(), self.processed_feed.height(),
            Qt.KeepAspectRatio, Qt.SmoothTransformation))
            
        if "hand_sign" in data:
            gesture_name = data["hand_sign"]
            self.current_gesture_label.setText(gesture_name)
            
            if gesture_name in self.gesture_actions.actions_mapping:
                action_config = self.gesture_actions.actions_mapping[gesture_name]
                action_type = action_config["action"]
                
                action_display = self.get_action_display_name(action_type, action_config["params"])
                self.current_action_label.setText(action_display)
                
                self.log_event(f"Жест распознан: {gesture_name} → {action_display}")
                
                x_pos, y_pos = None, None
                if "index_finger_tip" in data:
                    x_pos, y_pos = data["index_finger_tip"]
                    
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
            
        # действия мыши
        elif action_type == "click":
            return "Мышь: левый клик"
        elif action_type == "double_click":
            return "Мышь: двойной клик"
        elif action_type == "right_click":
            return "Мышь: правый клик"
        elif action_type == "scroll_up":
            return "Мышь: прокрутка вверх"
        elif action_type == "scroll_down":
            return "Мышь: прокрутка вниз"
            
        # буфер обмена
        elif action_type == "copy":
            return "Комбинация клавиш: копировать (Ctrl+C)"
        elif action_type == "paste":
            return "Комбинация клавиш: вставить (Ctrl+V)"
        elif action_type == "cut":
            return "Комбинация клавиш: вырезать (Ctrl+X)"
            
        # общие команды редактирования
        elif action_type == "select_all":
            return "Комбинация клавиш: выделить всё (Ctrl+A)"
        elif action_type == "undo":
            return "Комбинация клавиш: отменить (Ctrl+Z)"
        elif action_type == "redo":
            return "Комбинация клавиш: повторить (Ctrl+Y)"
        elif action_type == "save":
            return "Комбинация клавиш: сохранить (Ctrl+S)"
            
        # запуска
        elif action_type == "run_code":
            return "Комбинация клавиш: запустить код (F5)"
        elif action_type == "go_to_definition":
            return "Комбинация клавиш: перейти к определению (F12)"
        elif action_type == "find":
            return "Комбинация клавиш: найти (Ctrl+F)"
        elif action_type == "find_in_files":
            return "Комбинация клавиш: найти в файлах (Ctrl+Shift+F)"
        elif action_type == "quick_open":
            return "Комбинация клавиш: быстрое открытие файла (Ctrl+P)"
        elif action_type == "command_palette":
            return "Комбинация клавиш: палитра команд (Ctrl+Shift+P)"
            
        # файлы
        elif action_type == "new_file":
            return "Комбинация клавиш: новый файл (Ctrl+N)"
        elif action_type == "open_file":
            return "Комбинация клавиш: открыть файл (Ctrl+O)"
        elif action_type == "close_file":
            return "Комбинация клавиш: закрыть файл (Ctrl+W)"
        elif action_type == "close_window":
            return "Комбинация клавиш: закрыть окно (Alt+F4)"
        elif action_type == "switch_tab_next":
            return "Комбинация клавиш: следующая вкладка (Ctrl+Tab)"
        elif action_type == "switch_tab_prev":
            return "Комбинация клавиш: предыдущая вкладка (Ctrl+Shift+Tab)"
            
        # доп фишки
        elif action_type == "screenshot":
            return "Системное: сделать скриншот"
            
        # возвращаем оригинальное название, если неизвестный тип
        return f"Неизвестное действие: {action_type}"

    def apply_mediapipe_settings(self):
        """Применение настроек MediaPipe"""
        static_mode = False  # статичный режим всегда выключен в новом интерфейсе
        
        # используем значения, сохраненные при выборе чувствительности
        self.video_thread.update_settings(
            static_mode=static_mode,
            min_detection_conf=self.detection_conf,
            min_tracking_conf=self.tracking_conf
        )
        
        # всплывающее уведомление
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Information)
        msg.setWindowTitle("Настройки применены")
        msg.setText("Настройки распознавания обновлены!")
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec_()
        
        self.log_event(f"Настройки применены: обнаружение={self.detection_conf}, трекинг={self.tracking_conf}")
     
    def load_initial_settings(self):
        """Загрузка начальных значений настроек"""
        # инициализируем значения перед вызовом set_sensitivity
        self.detection_conf = 0.7
        self.tracking_conf = 0.5
        
        # устанавливаем средний уровень чувствительности по умолчанию 
        self.set_sensitivity("medium")
        
        # начальная задержка между действиями
        self.action_cooldown_spinner.setValue(3.0)  # 3
        self.gesture_actions.set_action_cooldown(3.0)
        
        # логирование загрузки настроек
        self.log_event("Загружены начальные настройки")

    def load_gesture_list(self):
        """Загрузка списка жестов из CSV-файла"""
        try:
            label_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                'model', 'keypoint_classifier', 'keypoint_classifier_label.csv'
            )
            
            with open(label_path, 'r', encoding='utf-8-sig') as f:
                gestures = []
                for line in f:
                    line = line.strip()
                    if line:  # добавляем только непустые строки
                        gestures.append(line)
                
            # очистка комбобокса
            self.action_gesture_selector.clear()
            
            # заполнение комбобокса актуальными жестами
            for gesture in gestures:
                self.action_gesture_selector.addItem(gesture)
                
            # обновляем список номеров жестов
            self.update_gesture_numbers()
                
            self.log_event(f"Загружено {len(gestures)} жестов")
                
        except Exception as e:
            QMessageBox.warning(self, "Ошибка загрузки жестов", f"Не удалось загрузить список жестов: {str(e)}")
            
    def load_action_mappings(self):
        """Загрузка настроек действий для жестов"""
        self.update_action_selector()
        self.log_event("Загружены настройки действий для жестов")
        
    def update_action_selector(self):
        """Обновление выбора действия при изменении жеста"""
        gesture = self.action_gesture_selector.currentText()
        if not gesture:
            return
            
        action_type = "none"
        if gesture in self.gesture_actions.actions_mapping:
            action_type = self.gesture_actions.actions_mapping[gesture]["action"]
            
        index = self.action_type_selector.findData(action_type)
        if index >= 0:
            self.action_type_selector.setCurrentIndex(index)
            
    def save_action_mapping(self):
        """Сохранение настройки действия для жеста"""
        gesture = self.action_gesture_selector.currentText()
        action_type = self.action_type_selector.currentData()
        
        if not gesture or not action_type:
            return
            
        self.gesture_actions.add_gesture_action(gesture, action_type)
        
        action_display = self.get_action_display_name(action_type)
        
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Information)
        msg.setWindowTitle("Настройка сохранена")
        msg.setText(f"Для жеста '{gesture}' установлено действие '{action_display}'")
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec_()
        
        self.log_event(f"Настройка действия сохранена: {gesture} → {action_display}")
    
    def log_event(self, message):
        """Добавление сообщения в лог событий"""
        if not hasattr(self, 'event_log'):
            print(f"Warning: event_log not initialized, message: {message}")
            return
            
        item = QListWidgetItem(message)
        
        # определение типа сообщения по ключевым словам
        if "ошибка" in message.lower() or "не удалось" in message.lower():
            item.setForeground(QColor(255, 99, 71))  # Красный для ошибок
        elif "жест распознан" in message.lower():
            item.setForeground(QColor(50, 205, 50))  # Зеленый для распознавания
        elif "настройка" in message.lower() or "применены" in message.lower():
            item.setForeground(QColor(135, 206, 250))  # Голубой для настроек
            
        # добавление сообщения в лог
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
        
        for gesture_name in self.gesture_actions.actions_mapping:
            action_info = self.gesture_actions.actions_mapping[gesture_name]
            
            if action_info:
                action_type = action_info["action"]
                action_params = action_info["params"]
                action_display = self.get_action_display_name(action_type, action_params)
                
                gesture_display = gesture_name
                
                gestures_info.append((gesture_display, action_display))
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Справка по жестам IDE")
        dialog.setMinimumWidth(800) 
        dialog.setMinimumHeight(600) 
        dialog.setStyleSheet("background-color: #2D2D30; color: #E6E6E6;")
        
        layout = QVBoxLayout(dialog)
        
        header_label = QLabel("Справочник по жестам и действиям")
        header_label.setStyleSheet("""
            font-size: 18px;
            font-weight: bold;
            color: white;
            padding: 10px;
            background-color: #007ACC;
            border-radius: 5px;
            margin-bottom: 15px;
        """)
        header_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(header_label)
        
        description_label = QLabel(
            "Здесь представлены все доступные жесты и их назначенные действия. "
            "Вы можете изменить действия для жестов в разделе 'Настройка действия'."
        )
        description_label.setStyleSheet("""
            color: #E6E6E6;
            padding: 10px;
            background-color: #3E3E42;
            border-radius: 5px;
            margin-bottom: 15px;
        """)
        description_label.setWordWrap(True)
        layout.addWidget(description_label)
        
        table = QTableWidget()
        table.setColumnCount(2)
        table.setRowCount(len(gestures_info))
        table.setHorizontalHeaderLabels(["Жест", "Действие"])
        
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setStyleSheet("""
            QHeaderView::section {
                background-color: #007ACC;
                color: white;
                padding: 8px;
                border: 1px solid #3F3F46;
                font-weight: bold;
            }
        """)
        
        table.verticalHeader().setVisible(False)
        
        table.setStyleSheet("""
            QTableWidget {
                background-color: #2D2D30;
                gridline-color: #3F3F46;
                border: 1px solid #3F3F46;
                border-radius: 5px;
            }
            QTableWidget::item {
                padding: 8px;
                border-bottom: 1px solid #3F3F46;
            }
            QTableWidget::item:selected {
                background-color: #007ACC;
                color: white;
            }
        """)
        
        for row, (gesture, action) in enumerate(gestures_info):
            # Жест
            gesture_item = QTableWidgetItem(gesture)
            gesture_item.setForeground(QColor("#E6E6E6"))
            gesture_item.setFont(QFont("Arial", 11, QFont.Bold))
            table.setItem(row, 0, gesture_item)
            
            # Действие
            action_item = QTableWidgetItem(action)
            action_item.setForeground(QColor("#E6E6E6"))
            action_item.setFont(QFont("Arial", 11))
            table.setItem(row, 1, action_item)
        
        layout.addWidget(table)
        
        buttons_layout = QHBoxLayout()
        
        # Кнопка обновления
        refresh_button = QPushButton("Обновить")
        refresh_button.setIcon(self.style().standardIcon(QStyle.SP_BrowserReload))
        refresh_button.setStyleSheet("""
            QPushButton {
                background-color: #007ACC;
                color: white;
                padding: 8px 15px;
                border-radius: 3px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1C97EA;
            }
        """)
        refresh_button.clicked.connect(lambda: self.load_gesture_list())
        buttons_layout.addWidget(refresh_button)
        
        # Кнопка закрытия
        close_button = QPushButton("Закрыть")
        close_button.setIcon(self.style().standardIcon(QStyle.SP_DialogCloseButton))
        close_button.setStyleSheet("""
            QPushButton {
                background-color: #3E3E42;
                color: white;
                padding: 8px 15px;
                border-radius: 3px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #4E4E52;
            }
        """)
        close_button.clicked.connect(dialog.close)
        buttons_layout.addWidget(close_button)
        
        layout.addLayout(buttons_layout)
        
        dialog.exec_()

    def show_recording_notification(self, success=True, error_message=None):
        """Показать уведомление о записи данных"""
        msg = QMessageBox(self)
        
        if success:
            msg.setIcon(QMessageBox.Information)
            msg.setWindowTitle("Запись данных")
            msg.setText(f"Успешно записано {self.recorded_frames} кадров")
        else:
            msg.setIcon(QMessageBox.Warning)
            msg.setWindowTitle("Ошибка записи")
            msg.setText(f"Ошибка при записи данных: {error_message}")
            
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec_()
        
    def on_recording_mode_change(self, index):
        """Обработчик изменения режима записи"""
        mode = self.recording_mode_selector.currentData()
        
        if mode == 1:  # Режим записи
            self.recording_status.setText("Статус: Режим записи жестов")
            self.recording_status.setStyleSheet("color: #FF6B6B;")  # Красный цвет для записи
            self.gesture_number_selector.setEnabled(True)
            self.recorded_frames = 0
            self.frames_counter.setText("Записано кадров: 0")
            
            # инструкция
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Information)
            msg.setWindowTitle("Режим записи")
            msg.setText("Инструкция по записи данных:\n\n"
                       "1. Выберите номер жеста (0-9)\n"
                       "2. Покажите жест перед камерой\n"
                       "3. Нажмите кнопку 'ЗАПИСАТЬ ЖЕСТ' для записи кадра\n"
                       "4. Повторяйте шаг 3 столько раз, сколько нужно кадров")
            msg.setStandardButtons(QMessageBox.Ok)
            msg.exec_()
        else:  # Нормальный режим
            if self.recorded_frames > 0:
                self.show_recording_notification(success=True)
                
            self.recording_status.setText("Статус: Нормальный режим")
            self.recording_status.setStyleSheet("color: #8F8F8F;")
            self.gesture_number_selector.setEnabled(False)
            self.gesture_number_selector.setCurrentIndex(-1)
            self.record_gesture_button.setEnabled(False)
            
        if self.video_thread.processor:
            self.video_thread.processor.set_mode(mode)
            self.log_event(f"Режим изменен на: {'Запись жестов' if mode == 1 else 'Нормальный режим'}")
            
        # Проверяем, нужно ли активировать кнопку записи
        self.update_record_button_state()

    def on_gesture_number_change(self, index):
        """Обработчик изменения номера жеста для записи"""
        if index >= 0:
            number = self.gesture_number_selector.currentData()
            if self.video_thread.processor:
                self.video_thread.processor.set_number(number)
                self.log_event(f"Выбран жест для записи: {number}")
                
        # Проверяем, нужно ли активировать кнопку записи
        self.update_record_button_state()

    def update_record_button_state(self):
        """Обновление состояния кнопки записи"""
        mode = self.recording_mode_selector.currentData()
        gesture_selected = self.gesture_number_selector.currentIndex() != -1
        self.record_gesture_button.setEnabled(mode == 1 and gesture_selected)

    def record_gesture(self):
        """Запись жеста при нажатии на кнопку"""
        if not self.video_thread.is_running:
            self.log_event("Ошибка: Камера не запущена!")
            return
            
        current_number = self.gesture_number_selector.currentData()
        if current_number is None:
            self.log_event("Ошибка: Выберите номер жеста (0-9) перед записью!")
            return
            
        if self.video_thread.processor:
            # последние данные о руке
            last_frame_data = getattr(self, '_last_frame_data', None)
            if last_frame_data and 'landmark_list' in last_frame_data:
                self.log_event("Найдены данные о руке, записываю кадр...")
                # кадр записанныйкадр
                if self.video_thread.processor.record_frame(last_frame_data['landmark_list']):
                    self.recorded_frames += 1
                    self.frames_counter.setText(f"Записано кадров: {self.recorded_frames}")
                    self.log_event(f"✓ Успешно записан кадр {self.recorded_frames} для жеста {current_number}")
                else:
                    self.log_event("❌ Ошибка: Не удалось записать кадр")
            else:
                self.log_event("❌ Ошибка: Рука не обнаружена в кадре")

    def keyPressEvent(self, event):
        """Обработка нажатий клавиш"""
        if event.key() == Qt.Key_Escape:  # Escape - выход из режима записи
            if self.video_thread.processor:
                self.video_thread.processor.set_mode(0)  # нормалньый режим
                self.recording_mode_selector.setCurrentIndex(0)  # селектор режима на 0
                self.log_event("Режим записи выключен")
                if self.recorded_frames > 0:
                    self.show_recording_notification(success=True)
                    self.recorded_frames = 0  # Сбрасываем счетчик
                    self.frames_counter.setText("Записано кадров: 0")
        
        super().keyPressEvent(event)

    def update_gesture_numbers(self):
        """Обновление списка номеров жестов на основе файла меток"""
        self.gesture_number_selector.clear()
        try:
            label_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                'model', 'keypoint_classifier', 'keypoint_classifier_label.csv'
            )
            
            with open(label_path, 'r', encoding='utf-8-sig') as f:
                gestures = []
                for line in f:
                    line = line.strip()
                    if line:  # только непустые
                        gestures.append(line)
                
            with open(label_path, 'w', encoding='utf-8-sig') as f:
                for gesture in gestures:
                    f.write(gesture + '\n')
                
            # Обновляем ComboBox только актуальными жестами
            for i, gesture in enumerate(gestures):
                self.gesture_number_selector.addItem(f"Жест {i}: {gesture}", i)
                
            self.log_event(f"Обновлен список жестов: {len(gestures)} жестов")
                
        except Exception as e:
            QMessageBox.warning(self, "Ошибка загрузки жестов", f"Не удалось загрузить список жестов: {str(e)}")

    def show_add_gesture_dialog(self):
        """Показать диалог добавления нового жеста"""
        dialog = AddGestureDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            gesture_name = dialog.get_gesture_name()
            if gesture_name:
                try:
                    label_path = os.path.join(
                        os.path.dirname(os.path.abspath(__file__)),
                        'model', 'keypoint_classifier', 'keypoint_classifier_label.csv'
                    )
                    
                    existing_gestures = []
                    if os.path.exists(label_path):
                        with open(label_path, 'r', encoding='utf-8-sig') as f:
                            existing_gestures = [line.strip() for line in f.readlines()]
                    
                    if gesture_name in existing_gestures:
                        QMessageBox.warning(self, "Ошибка", 
                                         f"Жест с названием '{gesture_name}' уже существует!")
                        return
                    
                    with open(label_path, 'a', encoding='utf-8-sig') as f:
                        f.write(f"{gesture_name}\n")
                    
                    self.load_gesture_list()
                    
                    QMessageBox.information(
                        self,
                        "Жест добавлен",
                        f"Жест '{gesture_name}' успешно добавлен!\n\n"
                        "Теперь необходимо:\n"
                        "1. Записать данные для жеста в режиме записи\n"
                        "2. Запустить ноутбук keypoint_classification_EN.ipynb\n"
                        "3. Выполнить Restart & Run All для обучения модели"
                    )
                    
                except Exception as e:
                    QMessageBox.critical(self, "Ошибка", f"Не удалось добавить жест: {str(e)}")

    def showEvent(self, event):
        """Обработчик события показа окна"""
        super().showEvent(event)
        if hasattr(self, 'cap') and self.cap is not None:
            self.cap.release()
            self.cap = cv2.VideoCapture(0)
            if not self.cap.isOpened():
                QMessageBox.critical(self, "Ошибка", "Не удалось подключиться к камере")
                return
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.camera_width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.camera_height)
            
    def hideEvent(self, event):
        """Обработчик события скрытия окна"""
        super().hideEvent(event)
        if hasattr(self, 'cap') and self.cap is not None:
            self.cap.release()
            
    def closeEvent(self, event):
        """Обработчик события закрытия окна"""
        if hasattr(self, 'cap') and self.cap is not None:
            self.cap.release()
        super().closeEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_()) 