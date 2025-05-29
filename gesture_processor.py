#!/usr/bin/env python
# -*- coding: utf-8 -*-
import copy
import cv2
import numpy as np
import mediapipe as mp
from collections import Counter

# Импорт классификаторов
from model import KeyPointClassifier
from utils import CvFpsCalc

class GestureProcessor:
    def __init__(self):
        """Инициализация обработчика распознавания жестов."""
        
        # Настройки MediaPipe
        self.use_static_image_mode = False
        self.min_detection_confidence = 0.7
        self.min_tracking_confidence = 0.5
        
        # Инициализация MediaPipe рук
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=self.use_static_image_mode,
            max_num_hands=1,
            min_detection_confidence=self.min_detection_confidence,
            min_tracking_confidence=self.min_tracking_confidence,
        )
        self.mp_drawing = mp.solutions.drawing_utils
        
        # Инициализация классификаторов
        self.keypoint_classifier = KeyPointClassifier()
        
        # Загрузка меток классов
        self.keypoint_classifier_labels = self._load_classifier_labels(
            'model/keypoint_classifier/keypoint_classifier_label.csv')
        
        # Режим работы
        self.mode = 0  # 0: Нормальный режим, 1: Запись жестов
        
        # Номер текущего жеста (для записи)
        self.number = -1
        
        # Калькулятор FPS
        self.cvFpsCalc = CvFpsCalc(buffer_len=10)
        
    def update_settings(self, static_mode=None, min_detection_conf=None, min_tracking_conf=None):
        """Обновление настроек MediaPipe."""
        restart_required = False
        
        if static_mode is not None and static_mode != self.use_static_image_mode:
            self.use_static_image_mode = static_mode
            restart_required = True
            
        if min_detection_conf is not None and min_detection_conf != self.min_detection_confidence:
            self.min_detection_confidence = min_detection_conf
            restart_required = True
            
        if min_tracking_conf is not None and min_tracking_conf != self.min_tracking_confidence:
            self.min_tracking_confidence = min_tracking_conf
            restart_required = True
            
        if restart_required:
            #пересоздание объекта рук с новыми настройками
            self.hands = self.mp_hands.Hands(
                static_image_mode=self.use_static_image_mode,
                max_num_hands=1,
                min_detection_confidence=self.min_detection_confidence,
                min_tracking_confidence=self.min_tracking_confidence,
            )
            
    def set_mode(self, mode=0):
        """Установка режима работы."""
        self.mode = mode
        
    def set_number(self, number=-1):
        """Установка номера для записи данных."""
        self.number = number
            
    def process_image(self, image):
        """
        Обработка изображения и распознавание жестов.
        
        Args:
            image: Изображение в формате BGR
            
        Returns:
            tuple: (обработанное изображение, словарь с данными распознавания)
        """
        # копирование изображения для отрисовки
        debug_image = copy.deepcopy(image)
        
        # вычисление FPS
        fps = self.cvFpsCalc.get()
        
        # конвертация изображения в RGB для MediaPipe
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # Запрет записи в изображение для увеличения производительности
        image_rgb.flags.writeable = False
        
        # Обработка изображения с MediaPipe
        results = self.hands.process(image_rgb)
        
        # Разрешение записи в изображение
        image_rgb.flags.writeable = True
        
        # Подготовка словаря с данными распознавания
        result_data = {
            "fps": fps,
            "mode": self.mode,
            "number": self.number
        }
        
        # Если обнаружены руки
        if results.multi_hand_landmarks is not None:
            for hand_landmarks, handedness in zip(results.multi_hand_landmarks, results.multi_handedness):
                # Расчет ограничивающего прямоугольника
                brect = self._calc_bounding_rect(debug_image, hand_landmarks)
                
                # Вычисление координат ключевых точек
                landmark_list = self._calc_landmark_list(debug_image, hand_landmarks)
                
                # Преобразование координат в относительные
                pre_processed_landmark_list = self._pre_process_landmark(landmark_list)
                
                # Запись данных в CSV, если мы в режиме записи
                self._logging_csv(self.number, self.mode, pre_processed_landmark_list)
                
                # Распознавание жеста руки
                hand_sign_id = self.keypoint_classifier(pre_processed_landmark_list)
                
                # Сохранение результатов в словарь
                result_data["hand_sign_id"] = hand_sign_id
                result_data["hand_sign"] = self.keypoint_classifier_labels[hand_sign_id]
                result_data["handedness"] = handedness.classification[0].label[0]  # 'R' или 'L'
                
                # Отрисовка результатов на изображении
                debug_image = self._draw_bounding_rect(debug_image, brect)
                debug_image = self._draw_landmarks(debug_image, landmark_list)
                debug_image = self._draw_info_text(
                    debug_image,
                    brect,
                    handedness.classification[0].label[0],
                    self.keypoint_classifier_labels[hand_sign_id]
                )
        
        # Отрисовка информации (FPS, режим, номер)
        debug_image = self._draw_info(debug_image, fps, self.mode, self.number)
        
        return debug_image, result_data
        
    def _load_classifier_labels(self, path):
        """Загрузка меток классов из CSV-файла."""
        import csv
        
        with open(path, 'r', encoding='utf-8-sig') as f:
            labels = csv.reader(f)
            labels = [row[0] for row in labels]
            
        return labels
        
    def _calc_bounding_rect(self, image, landmarks):
        """Расчет ограничивающего прямоугольника вокруг руки."""
        image_width, image_height = image.shape[1], image.shape[0]
        
        landmark_array = np.empty((0, 2), int)
        
        for _, landmark in enumerate(landmarks.landmark):
            landmark_x = min(int(landmark.x * image_width), image_width - 1)
            landmark_y = min(int(landmark.y * image_height), image_height - 1)
            
            landmark_point = [np.array((landmark_x, landmark_y))]
            landmark_array = np.append(landmark_array, landmark_point, axis=0)
            
        x, y, w, h = cv2.boundingRect(landmark_array)
        
        return [x, y, x + w, y + h]
        
    def _calc_landmark_list(self, image, landmarks):
        """Расчет координат ключевых точек руки."""
        image_width, image_height = image.shape[1], image.shape[0]
        
        landmark_point = []
        
        # Перебор всех 21 точки руки
        for _, landmark in enumerate(landmarks.landmark):
            landmark_x = min(int(landmark.x * image_width), image_width - 1)
            landmark_y = min(int(landmark.y * image_height), image_height - 1)
            
            landmark_point.append([landmark_x, landmark_y])
            
        return landmark_point
        
    def _pre_process_landmark(self, landmark_list):
        """Предобработка координат ключевых точек для классификатора."""
        temp_landmark_list = copy.deepcopy(landmark_list)
        
        # Преобразование в относительные координаты
        base_x, base_y = 0, 0
        for index, landmark_point in enumerate(temp_landmark_list):
            if index == 0:
                base_x, base_y = landmark_point[0], landmark_point[1]
                
            temp_landmark_list[index][0] = temp_landmark_list[index][0] - base_x
            temp_landmark_list[index][1] = temp_landmark_list[index][1] - base_y
            
        # Преобразование в одномерный список
        temp_landmark_list = list(
            itertools.chain.from_iterable(temp_landmark_list))
            
        # Нормализация
        max_value = max(list(map(abs, temp_landmark_list)))
        
        def normalize_(n):
            return n / max_value
            
        temp_landmark_list = list(map(normalize_, temp_landmark_list))
        
        return temp_landmark_list
        
    def _logging_csv(self, number, mode, landmark_list):
        """Запись данных в CSV для обучения."""
        if mode == 0:  # Нормальный режим
            return
            
        if mode == 1 and (0 <= number <= 9):  # Режим записи данных для жестов
            csv_path = 'model/keypoint_classifier/keypoint.csv'
            with open(csv_path, 'a', newline="") as f:
                writer = csv.writer(f)
                writer.writerow([number, *landmark_list])
                
    def _draw_landmarks(self, image, landmark_points):
        """Отрисовка ключевых точек руки."""
        # Соединения между точками
        connections = [
            (0, 1), (1, 2), (2, 3), (3, 4),  # Большой палец
            (0, 5), (5, 6), (6, 7), (7, 8),  # Указательный палец
            (0, 9), (9, 10), (10, 11), (11, 12),  # Средний палец
            (0, 13), (13, 14), (14, 15), (15, 16),  # Безымянный палец
            (0, 17), (17, 18), (18, 19), (19, 20),  # Мизинец
            (5, 9), (9, 13), (13, 17), (0, 17)  # Ладонь
        ]
        
        # Рисуем точки
        for index, point in enumerate(landmark_points):
            # Центр запястья
            if index == 0:
                cv2.circle(image, point, 5, (0, 255, 0), -1)
                cv2.circle(image, point, 10, (0, 255, 0), 2)
            # Суставы пальцев
            elif index in (1, 5, 9, 13, 17):
                cv2.circle(image, point, 5, (255, 0, 0), -1)
                cv2.circle(image, point, 10, (255, 0, 0), 2)
            # Кончики пальцев
            elif index in (4, 8, 12, 16, 20):
                cv2.circle(image, point, 8, (0, 0, 255), -1)
                cv2.circle(image, point, 12, (0, 0, 255), 2)
            # Остальные точки
            else:
                cv2.circle(image, point, 5, (0, 255, 255), -1)
                
        # Рисуем линии
        for connection in connections:
            start_idx, end_idx = connection
            cv2.line(image, landmark_points[start_idx], landmark_points[end_idx], (0, 255, 0), 2)
            
        return image
        
    def _draw_bounding_rect(self, image, brect):
        """Отрисовка ограничивающего прямоугольника."""
        cv2.rectangle(image, (brect[0], brect[1]), (brect[2], brect[3]), (0, 0, 0), 1)
        
        return image
        
    def _draw_info_text(self, image, brect, handedness, hand_sign_text):
        """Отрисовка информации о распознанном жесте."""
        info_text = handedness
        if hand_sign_text != "":
            info_text = f"{info_text}: {hand_sign_text}"
        cv2.putText(image, info_text, (brect[0] + 5, brect[1] - 12),
                  cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1, cv2.LINE_AA)
                    
        return image
        
    def _draw_info(self, image, fps, mode, number):
        """Отрисовка информации о FPS и режиме работы."""
        cv2.putText(image, "FPS:" + str(fps), (10, 30), cv2.FONT_HERSHEY_SIMPLEX,
                   1.0, (0, 0, 0), 4, cv2.LINE_AA)
        cv2.putText(image, "FPS:" + str(fps), (10, 30), cv2.FONT_HERSHEY_SIMPLEX,
                   1.0, (255, 255, 255), 2, cv2.LINE_AA)

        if mode == 1:  # Режим записи жестов
            cv2.putText(image, "MODE: Recording Key Point", (10, 90),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1,
                       cv2.LINE_AA)
            if 0 <= number <= 9:
                cv2.putText(image, "NUM:" + str(number), (10, 110),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1,
                           cv2.LINE_AA)
        return image

# Для корректного импорта itertools
import itertools
import csv 