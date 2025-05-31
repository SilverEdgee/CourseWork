import sys
import os
import cv2
import numpy as np
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                           QLabel, QPushButton, QComboBox, QGroupBox, QGridLayout, 
                           QTabWidget, QListWidget, QListWidgetItem, QTableWidget, 
                           QTableWidgetItem, QProgressBar, QDoubleSpinBox, QStyle, 
                           QStyleFactory, QDialog, QHeaderView, QSizePolicy)
from PyQt5.QtGui import QImage, QPixmap, QColor, QFont, QPalette
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QSize, QTime

from gesture_actions import GestureActions

# Определение цветовой схемы и стилей
STYLE = """
QMainWindow {
    background-color: #2D2D30;
}
QWidget {
    background-color: #2D2D30;
    color: #E6E6E6;
    font-family: 'Segoe UI', Arial, sans-serif;
}
QGroupBox {
    border: 1px solid #3F3F46;
    border-radius: 5px;
    margin-top: 10px;
    font-weight: bold;
    padding: 10px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 5px 0 5px;
}
QPushButton {
    background-color: #007ACC;
    color: white;
    border: none;
    border-radius: 3px;
    padding: 6px 12px;
    font-weight: bold;
}
QPushButton:hover {
    background-color: #1C97EA;
}
QPushButton:pressed {
    background-color: #0062A3;
}
QPushButton:disabled {
    background-color: #4D4D4D;
    color: #9D9D9D;
}
QComboBox {
    border: 1px solid #3F3F46;
    border-radius: 3px;
    padding: 5px;
    min-width: 4em;
}
QComboBox:hover {
    border: 1px solid #007ACC;
}
QSlider::groove:horizontal {
    border: 1px solid #3F3F46;
    height: 8px;
    background: #252526;
    margin: 2px 0;
    border-radius: 4px;
}
QSlider::handle:horizontal {
    background: #007ACC;
    border: 1px solid #5F5F5F;
    width: 18px;
    margin: -2px 0;
    border-radius: 4px;
}
QSlider::handle:horizontal:hover {
    background: #1C97EA;
}
QListWidget {
    border: 1px solid #3F3F46;
    border-radius: 3px;
}
QListWidget::item:selected {
    background-color: #007ACC;
}
QDoubleSpinBox, QSpinBox {
    border: 1px solid #3F3F46;
    border-radius: 3px;
    padding: 5px;
    min-width: 60px;
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
        
        self.processor = None
        
        self.timeout.connect(self.update_frame)
        self.setInterval(30)
        
    def start_camera(self, camera_id=0, width=640, height=480):
        if self.is_running:
            self.stop_camera()
        self.camera_id = camera_id
        self.width = width
        self.height = height
        self.cap = cv2.VideoCapture(self.camera_id)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        if not self.cap.isOpened():
            return False
        self.is_running = True
        super().start()
        return True
        
    def stop_camera(self):
        super().stop()
        if self.cap:
            self.cap.release()
            self.cap = None
        self.is_running = False
        
    def update_frame(self):
        if not self.is_running or not self.cap:
            return
        ret, frame = self.cap.read()
        if not ret:
            return
        frame = cv2.flip(frame, 1)
        self.frame_ready.emit(frame)
        if self.processor:
            result_frame, result_data = self.processor.process_image(frame)
            self.processed_ready.emit(result_frame, result_data)
            
    def set_processor(self, processor):
        self.processor = processor
        
    def update_settings(self, static_mode=None, min_detection_conf=None, min_tracking_conf=None):
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
    def __init__(self):
        super().__init__()
        self.camera_id = 0
        self.camera_width = 640
        self.camera_height = 480
        self.recorded_frames = 0
        self.apply_styles()
        self.setWindowTitle("Hand Gesture Controller")
        self.setMinimumSize(1000, 700)
        
        self.gesture_actions = GestureActions()
        self.init_ui()
        self.load_initial_settings()
        self.video_thread = VideoThread(self)
        self.video_thread.frame_ready.connect(self.update_camera_feed)
        self.video_thread.processed_ready.connect(self.update_processed_feed)
        self.load_gesture_list()
        self.load_action_mappings()

    def apply_styles(self):
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
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # --- Панель управления (слева) ---
        control_tabs = QTabWidget()
        control_tabs.setTabPosition(QTabWidget.West)
        control_tabs.setMinimumWidth(300)

        # Вкладка: Камера
        camera_tab = QWidget()
        camera_tab_layout = QVBoxLayout(camera_tab)
        camera_tab_layout.setContentsMargins(10, 10, 10, 10)
        camera_label = QLabel("Выберите камеру и запустите:")
        camera_label.setFont(QFont("Segoe UI", 10, QFont.Bold))
        camera_tab_layout.addWidget(camera_label)
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
        camera_tab_layout.addWidget(self.camera_selector)
        self.camera_button = QPushButton("Запустить камеру")
        self.camera_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self.camera_button.clicked.connect(self.toggle_camera)
        camera_tab_layout.addWidget(self.camera_button)
        camera_tab_layout.addStretch(1)
        control_tabs.addTab(camera_tab, "Камера")

        # Вкладка: Настройки распознавания
        recognition_tab = QWidget()
        recognition_layout = QVBoxLayout(recognition_tab)
        recognition_layout.setContentsMargins(10, 10, 10, 10)
        recognition_label = QLabel("Настройки чувствительности и задержки")
        recognition_label.setFont(QFont("Segoe UI", 10, QFont.Bold))
        recognition_layout.addWidget(recognition_label)
        
        sens_layout = QHBoxLayout()
        self.sensitivity_low = QPushButton("Низкая")
        self.sensitivity_low.clicked.connect(lambda: self.set_sensitivity("low"))
        sens_layout.addWidget(self.sensitivity_low)
        self.sensitivity_medium = QPushButton("Средняя")
        self.sensitivity_medium.clicked.connect(lambda: self.set_sensitivity("medium"))
        self.sensitivity_medium.setStyleSheet("background-color: #007ACC;")
        sens_layout.addWidget(self.sensitivity_medium)
        self.sensitivity_high = QPushButton("Высокая")
        self.sensitivity_high.clicked.connect(lambda: self.set_sensitivity("high"))
        sens_layout.addWidget(self.sensitivity_high)
        recognition_layout.addLayout(sens_layout)

        cooldown_hbox = QHBoxLayout()
        cooldown_label = QLabel("Задержка (сек):")
        cooldown_hbox.addWidget(cooldown_label)
        self.action_cooldown_spinner = QDoubleSpinBox()
        self.action_cooldown_spinner.setRange(0.1, 5.0)
        self.action_cooldown_spinner.setSingleStep(0.1)
        self.action_cooldown_spinner.setValue(1.0)
        self.action_cooldown_spinner.valueChanged.connect(self.update_action_cooldown)
        cooldown_hbox.addWidget(self.action_cooldown_spinner)
        recognition_layout.addLayout(cooldown_hbox)

        self.apply_settings_button = QPushButton("Применить настройки")
        self.apply_settings_button.clicked.connect(self.apply_mediapipe_settings)
        recognition_layout.addWidget(self.apply_settings_button)
        recognition_layout.addStretch(1)
        control_tabs.addTab(recognition_tab, "Распознавание")

        # Вкладка: Запись данных
        recording_tab = QWidget()
        rec_layout = QVBoxLayout(recording_tab)
        rec_layout.setContentsMargins(10, 10, 10, 10)
        rec_mode_hbox = QHBoxLayout()
        rec_mode_hbox.addWidget(QLabel("Режим:"))
        self.recording_mode_selector = QComboBox()
        self.recording_mode_selector.addItem("Нормальный", 0)
        self.recording_mode_selector.addItem("Запись жестов", 1)
        self.recording_mode_selector.currentIndexChanged.connect(self.on_recording_mode_change)
        rec_mode_hbox.addWidget(self.recording_mode_selector)
        rec_layout.addLayout(rec_mode_hbox)

        rec_gesture_hbox = QHBoxLayout()
        rec_gesture_hbox.addWidget(QLabel("Жест №:"))
        self.gesture_number_selector = QComboBox()
        for i in range(10):
            self.gesture_number_selector.addItem(str(i), i)
        self.gesture_number_selector.setEnabled(False)
        self.gesture_number_selector.currentIndexChanged.connect(self.on_gesture_number_change)
        rec_gesture_hbox.addWidget(self.gesture_number_selector)
        rec_layout.addLayout(rec_gesture_hbox)

        self.record_button = QPushButton("Начать запись")
        self.record_button.setEnabled(False)
        self.record_button.clicked.connect(self.toggle_recording)
        rec_layout.addWidget(self.record_button)

        self.record_progress = QProgressBar()
        self.record_progress.setFormat("Готов к записи")
        rec_layout.addWidget(self.record_progress)
        rec_layout.addStretch(1)
        control_tabs.addTab(recording_tab, "Запись данных")

        # Вкладка: Настройка действия
        action_tab = QWidget()
        act_layout = QVBoxLayout(action_tab)
        act_layout.setContentsMargins(10, 10, 10, 10)
        act_gesture_hbox = QHBoxLayout()
        act_gesture_hbox.addWidget(QLabel("Жест:"))
        self.action_gesture_selector = QComboBox()
        act_gesture_hbox.addWidget(self.action_gesture_selector)
        act_layout.addLayout(act_gesture_hbox)

        act_type_hbox = QHBoxLayout()
        act_type_hbox.addWidget(QLabel("Действие:"))
        self.action_type_selector = QComboBox()
        for action in self.gesture_actions.get_available_actions():
            self.action_type_selector.addItem(action["name"], action["id"])
        act_type_hbox.addWidget(self.action_type_selector)
        act_layout.addLayout(act_type_hbox)

        self.save_action_button = QPushButton("Сохранить действие")
        self.save_action_button.clicked.connect(self.save_action_mapping)
        act_layout.addWidget(self.save_action_button)
        act_layout.addStretch(1)
        control_tabs.addTab(action_tab, "Действия")

        # Вкладка: Справочник жестов
        gestures_tab = QWidget()
        gestures_layout = QVBoxLayout(gestures_tab)
        gestures_layout.setContentsMargins(10, 10, 10, 10)
        
        # Заголовок и описание
        header_label = QLabel("Доступные жесты и их действия")
        header_label.setFont(QFont("Segoe UI", 12, QFont.Bold))
        header_label.setStyleSheet("color: #3C9EFF;")
        gestures_layout.addWidget(header_label)

        # Таблица жестов
        self.gesture_table = QTableWidget()
        self.gesture_table.setColumnCount(3)
        self.gesture_table.setHorizontalHeaderLabels(["Жест", "Действие", "Статус"])
        self.gesture_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.gesture_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.gesture_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.gesture_table.setStyleSheet("""
            QTableWidget {
                border: 1px solid #3F3F46;
                gridline-color: #3F3F46;
            }
            QHeaderView::section {
                background-color: #2D2D30;
                padding: 5px;
                border: 1px solid #3F3F46;
                font-weight: bold;
            }
            QTableWidget::item {
                padding: 5px;
            }
        """)
        gestures_layout.addWidget(self.gesture_table)

        # Кнопки управления
        buttons_layout = QHBoxLayout()
        refresh_button = QPushButton("Обновить список")
        refresh_button.clicked.connect(self.refresh_gesture_table)
        buttons_layout.addWidget(refresh_button)
        help_button = QPushButton("Справка")
        help_button.clicked.connect(self.show_gesture_help)
        buttons_layout.addWidget(help_button)
        gestures_layout.addLayout(buttons_layout)

        control_tabs.addTab(gestures_tab, "Жесты")

        main_layout.addWidget(control_tabs)

        # --- Правая панель: Видео и информация ---
        right_panel = QVBoxLayout()
        right_panel.setSpacing(10)

        # Увеличенное видео
        processed_group = QGroupBox("Распознавание жестов")
        proc_layout = QVBoxLayout(processed_group)
        self.processed_feed = QLabel()
        self.processed_feed.setAlignment(Qt.AlignCenter)
        self.processed_feed.setMinimumSize(640, 480)  # Увеличиваем минимальный размер
        self.processed_feed.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)  # Разрешаем расширение
        self.processed_feed.setStyleSheet("background-color: #1E1E1E; border-radius: 5px;")
        proc_layout.addWidget(self.processed_feed)
        right_panel.addWidget(processed_group, stretch=3)  # Больший вес для видео

        # Уменьшенная информационная панель
        info_panel = QHBoxLayout()
        info_panel.setSpacing(5)  # Уменьшаем отступы

        # Уменьшаем размеры информационных блоков
        current_gesture_group = QGroupBox("Текущий жест")
        current_gesture_group.setMaximumHeight(80)  # Ограничиваем высоту
        cg_layout = QVBoxLayout(current_gesture_group)
        cg_layout.setContentsMargins(5, 5, 5, 5)  # Уменьшаем внутренние отступы
        self.current_gesture_label = QLabel("Нет")
        self.current_gesture_label.setFont(QFont("Segoe UI", 12, QFont.Bold))  # Уменьшаем шрифт
        self.current_gesture_label.setStyleSheet("color: #3C9EFF;")
        self.current_gesture_label.setAlignment(Qt.AlignCenter)
        cg_layout.addWidget(self.current_gesture_label)
        info_panel.addWidget(current_gesture_group)

        current_action_group = QGroupBox("Текущее действие")
        current_action_group.setMaximumHeight(80)  # Ограничиваем высоту
        ca_layout = QVBoxLayout(current_action_group)
        ca_layout.setContentsMargins(5, 5, 5, 5)  # Уменьшаем внутренние отступы
        self.current_action_label = QLabel("Нет")
        self.current_action_label.setFont(QFont("Segoe UI", 12))  # Уменьшаем шрифт
        self.current_action_label.setStyleSheet("color: #3C9EFF;")
        self.current_action_label.setAlignment(Qt.AlignCenter)
        ca_layout.addWidget(self.current_action_label)
        info_panel.addWidget(current_action_group)

        log_group = QGroupBox("Лог событий")
        log_group.setMaximumHeight(80)  # Ограничиваем высоту
        log_layout = QVBoxLayout(log_group)
        log_layout.setContentsMargins(5, 5, 5, 5)  # Уменьшаем внутренние отступы
        self.event_log = QListWidget()
        self.event_log.setMaximumHeight(50)  # Ограничиваем высоту списка
        log_layout.addWidget(self.event_log)
        info_panel.addWidget(log_group)

        right_panel.addLayout(info_panel, stretch=1)  # Меньший вес для инфо-панели

        self.recognition_button = QPushButton("Запустить распознавание")
        self.recognition_button.clicked.connect(self.toggle_recognition)
        self.recognition_button.setEnabled(False)
        self.recognition_button.setMaximumHeight(40)  # Фиксированная высота кнопки
        right_panel.addWidget(self.recognition_button)

        main_layout.addLayout(right_panel)

        # Сигналы
        self.action_gesture_selector.currentIndexChanged.connect(self.update_action_selector)

    def toggle_recognition(self):
        if not self.video_thread.is_running:
            self.toggle_camera()
        else:
            self.toggle_camera()

    def set_sensitivity(self, level):
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
        if not self.video_thread.is_running:
            camera_id = self.camera_selector.currentData()
            if self.video_thread.start_camera(camera_id, self.camera_width, self.camera_height):
                self.camera_button.setText("Остановить камеру")
                self.camera_button.setIcon(self.style().standardIcon(QStyle.SP_MediaStop))
                self.recognition_button.setEnabled(True)
                self.log_event("Камера запущена")
            else:
                QMessageBox.critical(self, "Ошибка", "Не удалось запустить камеру!")
        else:
            self.video_thread.stop_camera()
            self.camera_button.setText("Запустить камеру")
            self.camera_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
            self.recognition_button.setEnabled(False)
            self.processed_feed.clear()
            self.log_event("Камера остановлена")

    def update_camera_feed(self, frame):
        h, w, ch = frame.shape
        bytes_per_line = ch * w
        qt_image = QImage(frame.data, w, h, bytes_per_line, QImage.Format_RGB888).rgbSwapped()
        pixmap = QPixmap.fromImage(qt_image)
        self.processed_feed.setPixmap(pixmap.scaled(
            self.processed_feed.width(), self.processed_feed.height(),
            Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def update_processed_feed(self, frame, data):
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
            for i in range(self.gesture_table.rowCount()):
                item = self.gesture_table.item(i, 0)
                if item.text() == gesture_name:
                    item.setBackground(QColor(0, 122, 204, 100))
                    item.setForeground(QColor(255, 255, 255))
                else:
                    item.setBackground(QColor(0, 0, 0, 0))
                    item.setForeground(QColor(230, 230, 230))
            
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
        if action_type == "none":
            return "Нет действия"
        elif action_type == "custom_hotkey":
            if params and "hotkey" in params:
                hotkey = "+".join(params["hotkey"])
                return f"Комбинация: {hotkey}"
            return "Комбинация клавиш"
        elif action_type == "click": return "Клик мыши"
        elif action_type == "double_click": return "Двойной клик"
        elif action_type == "right_click": return "Правый клик"
        elif action_type == "scroll_up": return "Прокрутка вверх"
        elif action_type == "scroll_down": return "Прокрутка вниз"
        elif action_type == "drag": return "Перетаскивание"
        elif action_type == "app_execute":
            if params and "path" in params:
                app_name = params["path"].split("/")[-1]
                return f"Запуск: {app_name}"
            return "Запуск приложения"
        return action_type

    def apply_mediapipe_settings(self):
        static_mode = False
        self.video_thread.update_settings(
            static_mode=static_mode,
            min_detection_conf=self.detection_conf,
            min_tracking_conf=self.tracking_conf
        )
        msg = QDialog(self)
        msg.setWindowTitle("Настройки применены")
        label = QLabel("Настройки распознавания обновлены!")
        label.setAlignment(Qt.AlignCenter)
        dlg_layout = QVBoxLayout(msg)
        dlg_layout.addWidget(label)
        btn = QPushButton("OK")
        btn.clicked.connect(msg.accept)
        btn.setFixedWidth(100)
        btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        dlg_layout.addWidget(btn, alignment=Qt.AlignCenter)
        msg.exec_()
        self.log_event(f"Настройки применены: обнаружение={self.detection_conf}, трекинг={self.tracking_conf}")

    def load_initial_settings(self):
        self.detection_conf = 0.7
        self.tracking_conf = 0.5
        self.set_sensitivity("medium")
        self.action_cooldown_spinner.setValue(1.0)
        self.gesture_actions.set_action_cooldown(1.0)
        self.log_event("Загружены начальные настройки")

    def load_gesture_list(self):
        """Загрузка списка жестов"""
        try:
            label_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                'model', 'keypoint_classifier', 'keypoint_classifier_label.csv'
            )
            
            with open(label_path, 'r', encoding='utf-8-sig') as f:
                gestures = [line.strip() for line in f.readlines() if line.strip()]
                self.action_gesture_selector.clear()
                for gesture in gestures:
                    self.action_gesture_selector.addItem(gesture)
                
                # Обновляем таблицу жестов
                self.refresh_gesture_table()
                
                self.log_event(f"Загружено {len(gestures)} жестов")
                
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Не удалось загрузить жесты: {e}")

    def load_action_mappings(self):
        self.update_action_selector()
        self.log_event("Загружены настройки действий")

    def update_action_selector(self):
        gesture = self.action_gesture_selector.currentText()
        if not gesture:
            return
        action_type = "none"
        if gesture in self.gesture_actions.actions_mapping:
            action_type = self.gesture_actions.actions_mapping[gesture]["action"]
        idx = self.action_type_selector.findData(action_type)
        if idx >= 0:
            self.action_type_selector.setCurrentIndex(idx)

    def save_action_mapping(self):
        gesture = self.action_gesture_selector.currentText()
        action_type = self.action_type_selector.currentData()
        if not gesture or not action_type:
            return
        self.gesture_actions.add_gesture_action(gesture, action_type)
        self.refresh_gesture_table()
        dialog = QDialog(self)
        dialog.setWindowTitle("Настройка сохранена")
        lbl = QLabel(f"Для жеста '{gesture}' установлено действие.")
        lbl.setAlignment(Qt.AlignCenter)
        dlg_lay = QVBoxLayout(dialog)
        dlg_lay.addWidget(lbl)
        btn = QPushButton("OK")
        btn.clicked.connect(dialog.accept)
        btn.setFixedWidth(100)
        dlg_lay.addWidget(btn, alignment=Qt.AlignCenter)
        dialog.exec_()
        self.log_event(f"Действие сохранено: {gesture} → {action_type}")

    def log_event(self, message):
        item = QListWidgetItem(message)
        lower = message.lower()
        if "ошибка" in lower or "не удалось" in lower:
            item.setForeground(QColor(255, 99, 71))
        elif "жест распознан" in lower:
            item.setForeground(QColor(50, 205, 50))
        elif "настройка" in lower or "применены" in lower:
            item.setForeground(QColor(135, 206, 250))
        time_str = QTime.currentTime().toString('hh:mm:ss')
        item.setToolTip(time_str)
        self.event_log.addItem(item)
        self.event_log.scrollToBottom()

    def update_action_cooldown(self):
        cooldown = self.action_cooldown_spinner.value()
        self.gesture_actions.set_action_cooldown(cooldown)
        self.log_event(f"Задержка между действиями: {cooldown} сек")

    def on_recording_mode_change(self, index):
        mode = self.recording_mode_selector.currentData()
        if mode == 1:
            self.recording_mode_selector.setItemText(1, "Запись жестов")
            self.gesture_number_selector.setEnabled(True)
            self.record_button.setEnabled(True)
            self.recorded_frames = 0
            self.record_progress.setValue(0)
            self.record_progress.setFormat("Готов к записи")
            msg = QDialog(self)
            msg.setWindowTitle("Режим записи")
            lbl = QLabel("Инструкция по записи данных:\n1. Выберите номер жеста (0-9)\n2. Нажмите 'Начать запись'\n3. Удерживайте жест 3 сек\n4. Повторите при необходимости")
            lbl.setAlignment(Qt.AlignLeft)
            dlg_layout = QVBoxLayout(msg)
            dlg_layout.addWidget(lbl)
            btn = QPushButton("OK")
            btn.clicked.connect(msg.accept)
            btn.setFixedWidth(100)
            dlg_layout.addWidget(btn, alignment=Qt.AlignCenter)
            msg.exec_()
            if self.video_thread.processor:
                self.video_thread.processor.set_mode(mode)
            self.log_event("Режим: Запись жестов")
        else:
            if getattr(self, 'is_recording', False):
                self.toggle_recording()
            self.gesture_number_selector.setEnabled(False)
            self.record_button.setEnabled(False)
            self.gesture_number_selector.setCurrentIndex(-1)
            self.record_progress.setValue(0)
            self.record_progress.setFormat("Готов к записи")
            if self.video_thread.processor:
                self.video_thread.processor.set_mode(mode)
            self.log_event("Режим: Нормальный")

    def on_gesture_number_change(self, index):
        if index >= 0 and self.video_thread.processor:
            number = self.gesture_number_selector.currentData()
            self.video_thread.processor.set_number(number)
            self.log_event(f"Выбран жест для записи: {number}")

    def toggle_recording(self):
        if not getattr(self, 'is_recording', False):
            self.is_recording = True
            self.recording_start_time = QTime.currentTime().msecsSinceStartOfDay()
            self.record_button.setText("Остановить запись")
            self.log_event("Запись начата")
        else:
            self.is_recording = False
            self.record_button.setText("Начать запись")
            self.log_event("Запись остановлена")

    def update_recording_progress(self):
        if getattr(self, 'is_recording', False):
            current_time = QTime.currentTime().msecsSinceStartOfDay()
            elapsed = current_time - self.recording_start_time
            duration = 3000  # 3 секунды
            progress = min(100, int(elapsed / duration * 100))
            self.record_progress.setValue(progress)
            self.record_progress.setFormat(f"Запись: {progress}%")
            if elapsed >= duration:
                self.is_recording = False
                self.record_button.setText("Начать запись")
                self.log_event("Запись завершена")
                self.recorded_frames += 1
                dlg = QDialog(self)
                dlg.setWindowTitle("Запись данных")
                lbl = QLabel(f"Успешно записано {self.recorded_frames} наборов для жеста {self.gesture_number_selector.currentText()}")
                lbl.setAlignment(Qt.AlignCenter)
                lay = QVBoxLayout(dlg)
                lay.addWidget(lbl)
                btn = QPushButton("OK")
                btn.clicked.connect(dlg.accept)
                btn.setFixedWidth(100)
                lay.addWidget(btn, alignment=Qt.AlignCenter)
                dlg.exec_()

    def refresh_gesture_table(self):
        """Обновление таблицы жестов"""
        self.gesture_table.setRowCount(0)
        try:
            label_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                'model', 'keypoint_classifier', 'keypoint_classifier_label.csv'
            )
            
            with open(label_path, 'r', encoding='utf-8-sig') as f:
                gestures = [line.strip() for line in f.readlines() if line.strip()]
                
                self.gesture_table.setRowCount(len(gestures))
                for row, gesture in enumerate(gestures):
                    # Жест
                    gesture_item = QTableWidgetItem(gesture)
                    gesture_item.setTextAlignment(Qt.AlignCenter)
                    self.gesture_table.setItem(row, 0, gesture_item)
                    
                    # Действие
                    action_text = "Не назначено"
                    if gesture in self.gesture_actions.actions_mapping:
                        action_config = self.gesture_actions.actions_mapping[gesture]
                        action_text = self.get_action_display_name(
                            action_config["action"], 
                            action_config["params"]
                        )
                    action_item = QTableWidgetItem(action_text)
                    action_item.setTextAlignment(Qt.AlignCenter)
                    self.gesture_table.setItem(row, 1, action_item)
                    
                    # Статус
                    status_item = QTableWidgetItem("✓" if gesture in self.gesture_actions.actions_mapping else "—")
                    status_item.setTextAlignment(Qt.AlignCenter)
                    status_item.setForeground(
                        QColor("#50C878") if gesture in self.gesture_actions.actions_mapping 
                        else QColor("#808080")
                    )
                    self.gesture_table.setItem(row, 2, status_item)
            
            self.gesture_table.resizeColumnsToContents()
            self.gesture_table.resizeRowsToContents()
            
        except Exception as e:
            self.log_event(f"Ошибка при обновлении таблицы жестов: {str(e)}")

    def show_gesture_help(self):
        """Показ справки по жестам"""
        help_dialog = QDialog(self)
        help_dialog.setWindowTitle("Справка по жестам")
        help_dialog.setMinimumWidth(400)
        
        layout = QVBoxLayout(help_dialog)
        
        help_text = QLabel(
            "Как использовать жесты:\n\n"
            "1. Выберите жест из списка\n"
            "2. Назначьте ему действие во вкладке 'Действия'\n"
            "3. Проверьте работу жеста в режиме распознавания\n\n"
            "Советы:\n"
            "• Держите руку в пределах видимости камеры\n"
            "• Выполняйте жесты чётко и удерживайте их\n"
            "• Настройте чувствительность при необходимости"
        )
        help_text.setWordWrap(True)
        layout.addWidget(help_text)
        
        close_button = QPushButton("Закрыть")
        close_button.clicked.connect(help_dialog.accept)
        layout.addWidget(close_button, alignment=Qt.AlignCenter)
        
        help_dialog.exec_()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
