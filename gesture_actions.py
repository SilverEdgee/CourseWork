#!/usr/bin/env python
# -*- coding: utf-8 -*-
import json
import os
import logging
import sys
import time

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('GestureActions')

# Проверка возможности использования pyautogui
try:
    import pyautogui
    PYAUTOGUI_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Ошибка импорта pyautogui: {e}")
    PYAUTOGUI_AVAILABLE = False
except Exception as e:
    logger.warning(f"Ошибка при инициализации pyautogui: {e}")
    PYAUTOGUI_AVAILABLE = False
    
# Если pyautogui недоступен, создаем заглушку для основных функций
if not PYAUTOGUI_AVAILABLE:
    logger.warning("pyautogui недоступен, будет использоваться эмуляция. Действия не будут выполняться.")
    
    class PyAutoGUIStub:
        def __init__(self):
            self.screen_width = 1920
            self.screen_height = 1080
            
        def size(self):
            return self.screen_width, self.screen_height
            
        def moveTo(self, x, y, duration=0.0):
            logger.info(f"Эмуляция: перемещение мыши в ({x}, {y})")
            
        def click(self, x=None, y=None):
            logger.info(f"Эмуляция: клик мыши в ({x}, {y})")
            
        def rightClick(self, x=None, y=None):
            logger.info(f"Эмуляция: правый клик мыши в ({x}, {y})")
            
        def doubleClick(self, x=None, y=None):
            logger.info(f"Эмуляция: двойной клик мыши в ({x}, {y})")
            
        def scroll(self, clicks):
            logger.info(f"Эмуляция: прокрутка на {clicks} тиков")
            
        def hotkey(self, *args):
            logger.info(f"Эмуляция: нажатие комбинации клавиш {args}")
            
        def press(self, key):
            logger.info(f"Эмуляция: нажатие клавиши {key}")
            
        def screenshot(self):
            logger.info("Эмуляция: создание скриншота")
            
            class StubImage:
                def save(self, path):
                    logger.info(f"Эмуляция: сохранение скриншота в {path}")
            
            return StubImage()
            
        def time(self):
            import time
            return time
    
    # Заменяем модуль pyautogui на заглушку
    pyautogui = PyAutoGUIStub()

class GestureActions:
    def __init__(self, config_file='gesture_actions_config.json'):
        """
        Инициализация класса действий для жестов.
        
        Args:
            config_file (str): Путь к конфигурационному файлу
        """
        self.config_file = config_file
        self.actions_mapping = {}
        self.load_config()
        
        # Добавление контроля частоты выполнения действий
        self.action_cooldown = 1.0  # Задержка между действиями в секундах (по умолчанию 1 секунда)
        self.last_action_time = {}  # Словарь для хранения времени последнего выполнения каждого действия
        
    def load_config(self):
        """Загрузка конфигурации из файла"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.actions_mapping = json.load(f)
                logger.info(f"Конфигурация загружена из {self.config_file}")
            else:
                # Дефолтная конфигурация
                self.actions_mapping = {
                    "Open": {"action": "custom_hotkey", "params": {"hotkey": ["ctrl", "o"]}},
                    "Close": {"action": "custom_hotkey", "params": {"hotkey": ["ctrl", "w"]}},
                    "Pointer": {"action": "custom_hotkey", "params": {"hotkey": ["ctrl", "p"]}},
                    "OK": {"action": "custom_hotkey", "params": {"hotkey": ["ctrl", "enter"]}},
                    "Thumb Up": {"action": "save", "params": {"hotkey": ["ctrl", "s"]}},
                    "Peace Sign": {"action": "custom_hotkey", "params": {"hotkey": ["ctrl", "shift", "p"]}},
                    "Thumb Down": {"action": "custom_hotkey", "params": {"hotkey": ["ctrl", "shift", "f"]}},
                    "XUY": {"action": "run_code", "params": {"hotkey": ["f5"]}},
                    "STRELYATEM PO XOXLAM": {"action": "custom_hotkey", "params": {"hotkey": ["ctrl", "shift", "b"]}}
                }
                self.save_config()
        except Exception as e:
            logger.error(f"Ошибка при загрузке конфигурации: {e}")
            # Создаем пустую конфигурацию
            self.actions_mapping = {}
            
    def save_config(self):
        """Сохранение конфигурации в файл"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.actions_mapping, f, indent=4, ensure_ascii=False)
            logger.info(f"Конфигурация сохранена в {self.config_file}")
        except Exception as e:
            logger.error(f"Ошибка при сохранении конфигурации: {e}")
    
    def add_gesture_action(self, gesture_name, action_type, params={}):
        """
        Добавление или обновление действия для жеста
        
        Args:
            gesture_name (str): Название жеста
            action_type (str): Тип действия (none, move_mouse, click, hotkey, text, etc.)
            params (dict): Параметры действия
        """
        self.actions_mapping[gesture_name] = {
            "action": action_type,
            "params": params
        }
        self.save_config()
        
    def get_available_actions(self):
        """Получение списка доступных действий"""
        return [
            {"id": "none", "name": "Нет действия"},
            {"id": "click", "name": "Клик мыши"},
            {"id": "right_click", "name": "Правый клик"},
            {"id": "double_click", "name": "Двойной клик"},
            {"id": "scroll_up", "name": "Прокрутка вверх"},
            {"id": "scroll_down", "name": "Прокрутка вниз"},
            {"id": "save", "name": "Сохранить (Ctrl+S)"},
            {"id": "copy", "name": "Копировать (Ctrl+C)"},
            {"id": "paste", "name": "Вставить (Ctrl+V)"},
            {"id": "cut", "name": "Вырезать (Ctrl+X)"},
            {"id": "select_all", "name": "Выделить всё (Ctrl+A)"},
            {"id": "run_code", "name": "Запустить код (F5)"},
            {"id": "close_window", "name": "Закрыть окно (Alt+F4)"},
            {"id": "screenshot", "name": "Сделать скриншот"},
            {"id": "custom_hotkey", "name": "Своя комбинация клавиш"}
        ]
        
    def get_gesture_actions_info(self):
        """
        Получение подробной информации о всех жестах и их действиях в понятном формате.
        
        Returns:
            list: Список словарей с информацией о жестах и действиях
        """
        info_list = []
        action_descriptions = {
            "none": "Нет действия",
            "click": "Клик мыши",
            "right_click": "Правый клик мыши",
            "double_click": "Двойной клик мыши", 
            "scroll_up": "Прокрутка вверх",
            "scroll_down": "Прокрутка вниз",
            "save": "Сохранить файл (Ctrl+S)",
            "copy": "Копировать выделенное (Ctrl+C)",
            "paste": "Вставить из буфера (Ctrl+V)",
            "cut": "Вырезать выделенное (Ctrl+X)",
            "select_all": "Выделить всё (Ctrl+A)",
            "run_code": "Запустить код (F5)",
            "close_window": "Закрыть окно (Alt+F4)",
            "screenshot": "Сделать скриншот экрана",
            "custom_hotkey": "Пользовательское сочетание клавиш"
        }
        
        ide_hotkey_descriptions = {
            "ctrl+o": "Открыть файл",
            "ctrl+w": "Закрыть файл",
            "ctrl+p": "Быстрый поиск файлов",
            "ctrl+enter": "Выполнить команду",
            "ctrl+s": "Сохранить файл",
            "ctrl+shift+p": "Открыть палитру команд",
            "ctrl+shift+f": "Поиск по всем файлам",
            "ctrl+shift+b": "Запустить сборку проекта",
            "f5": "Запустить отладку",
            "ctrl+f5": "Запустить без отладки",
            "ctrl+c": "Копировать",
            "ctrl+v": "Вставить",
            "ctrl+x": "Вырезать",
            "ctrl+a": "Выделить всё",
            "alt+f4": "Закрыть окно"
        }
        
        for gesture_name, action_config in self.actions_mapping.items():
            action_type = action_config["action"]
            params = action_config["params"]
            
            description = action_descriptions.get(action_type, "Неизвестное действие")
            details = ""
            
            if action_type == "custom_hotkey" and "hotkey" in params:
                hotkey_str = "+".join(params["hotkey"])
                ide_description = ide_hotkey_descriptions.get(hotkey_str.lower(), "Пользовательское сочетание клавиш")
                details = f"{hotkey_str} - {ide_description}"
            
            info_list.append({
                "gesture": gesture_name,
                "action_type": action_type,
                "description": description,
                "details": details
            })
            
        return info_list
        
    def set_action_cooldown(self, seconds):
        """Установка задержки между выполнением действий"""
        self.action_cooldown = max(0.1, float(seconds))
        logger.info(f"Установлена задержка между действиями: {self.action_cooldown} сек")
        
    def _check_cooldown(self, action_type):
        """Проверка таймаута между действиями"""
        current_time = time.time()
        last_time = self.last_action_time.get(action_type, 0)
        
        if current_time - last_time < self.action_cooldown:
            return False
            
        self.last_action_time[action_type] = current_time
        return True
        
    def execute_action(self, gesture_name, x_pos=None, y_pos=None):
        """
        Выполнение действия для указанного жеста
        
        Args:
            gesture_name (str): Название жеста
            x_pos (float, optional): Относительная позиция X (0.0-1.0) - не используется
            y_pos (float, optional): Относительная позиция Y (0.0-1.0) - не используется
            
        Returns:
            bool: Успешно ли выполнено действие
        """
        if not PYAUTOGUI_AVAILABLE:
            logger.warning(f"Попытка выполнения действия для жеста '{gesture_name}', но pyautogui недоступен")
            return False
            
        if gesture_name not in self.actions_mapping:
            logger.warning(f"Жест '{gesture_name}' не найден в конфигурации")
            return False
        
        action_config = self.actions_mapping[gesture_name]
        action_type = action_config["action"]
        params = action_config["params"]
        
        try:
            # Получаем размеры экрана для справки
            screen_width, screen_height = pyautogui.size()
            
            if action_type == "none":
                return True
                
            elif action_type == "click":
                if not self._check_cooldown(action_type):
                    return False
                    
                pyautogui.click()
                logger.info(f"Выполнен клик мыши")
                    
            elif action_type == "right_click":
                if not self._check_cooldown(action_type):
                    return False
                    
                pyautogui.rightClick()
                logger.info(f"Выполнен правый клик мыши")
                    
            elif action_type == "double_click":
                if not self._check_cooldown(action_type):
                    return False
                    
                pyautogui.doubleClick()
                logger.info(f"Выполнен двойной клик мыши")
                    
            elif action_type == "scroll_up":
                if not self._check_cooldown(action_type):
                    return False
                    
                pyautogui.scroll(100)  # положительное значение для прокрутки вверх
                logger.info(f"Выполнена прокрутка вверх")
                
            elif action_type == "scroll_down":
                if not self._check_cooldown(action_type):
                    return False
                    
                pyautogui.scroll(-100)  # отрицательное значение для прокрутки вниз
                logger.info(f"Выполнена прокрутка вниз")
                
            elif action_type == "save":
                if not self._check_cooldown(action_type):
                    return False
                    
                pyautogui.hotkey('ctrl', 's')
                logger.info(f"Выполнено сохранение (Ctrl+S)")
                
            elif action_type == "copy":
                if not self._check_cooldown(action_type):
                    return False
                    
                pyautogui.hotkey('ctrl', 'c')
                logger.info(f"Выполнено копирование (Ctrl+C)")
                
            elif action_type == "paste":
                if not self._check_cooldown(action_type):
                    return False
                    
                pyautogui.hotkey('ctrl', 'v')
                logger.info(f"Выполнена вставка (Ctrl+V)")
                
            elif action_type == "cut":
                if not self._check_cooldown(action_type):
                    return False
                    
                pyautogui.hotkey('ctrl', 'x')
                logger.info(f"Выполнено вырезание (Ctrl+X)")
                
            elif action_type == "select_all":
                if not self._check_cooldown(action_type):
                    return False
                    
                pyautogui.hotkey('ctrl', 'a')
                logger.info(f"Выполнено выделение всего (Ctrl+A)")
                
            elif action_type == "run_code":
                if not self._check_cooldown(action_type):
                    return False
                
                # Попробуем разные способы запуска кода, так как F5 может не работать в некоторых окружениях
                try:
                    # Метод 1: прямое нажатие клавиши F5
                    pyautogui.press('f5')
                    logger.info("Метод 1: Выполнен запуск кода (press F5)")
                    
                    # Метод 2: использование hotkey для F5
                    pyautogui.hotkey('f5')
                    logger.info("Метод 2: Выполнен запуск кода (hotkey F5)")
                    
                    # Метод 3: использование сочетания Shift+F10 (альтернативный способ запуска)
                    pyautogui.hotkey('shift', 'f10')
                    logger.info("Метод 3: Выполнен запуск кода (Shift+F10)")
                    
                    # Метод 4: использование Ctrl+F5 (запуск без отладки в некоторых средах)
                    pyautogui.hotkey('ctrl', 'f5')
                    logger.info("Метод 4: Выполнен запуск кода (Ctrl+F5)")
                except Exception as e:
                    logger.error(f"Ошибка при запуске кода: {e}")
                
            elif action_type == "close_window":
                if not self._check_cooldown(action_type):
                    return False
                    
                pyautogui.hotkey('alt', 'f4')
                logger.info(f"Выполнено закрытие окна (Alt+F4)")
                
            elif action_type == "screenshot":
                if not self._check_cooldown(action_type):
                    return False
                    
                screenshot = pyautogui.screenshot()
                screenshot_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                                             f"screenshot_{pyautogui.time().strftime('%Y%m%d_%H%M%S')}.png")
                screenshot.save(screenshot_path)
                logger.info(f"Скриншот сохранен: {screenshot_path}")
                
            elif action_type == "custom_hotkey" and "hotkey" in params:
                if not self._check_cooldown(action_type):
                    return False
                    
                pyautogui.hotkey(*params["hotkey"])
                logger.info(f"Выполнено нажатие комбинации клавиш: {params['hotkey']}")
                
            else:
                logger.warning(f"Неизвестный тип действия: {action_type}")
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при выполнении действия '{action_type}' для жеста '{gesture_name}': {e}")
            return False


if __name__ == "__main__":
    # Тестирование класса
    actions = GestureActions()
    print("Доступные действия:", actions.get_available_actions())
    print("Текущая конфигурация:", actions.actions_mapping) 