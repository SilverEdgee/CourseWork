import json
import os
import logging
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
    
    pyautogui = PyAutoGUIStub()

class GestureActions:
    def __init__(self, config_file='gesture_actions_config.json'):
        """
        Инициализация класса действий для жестов.
        
        Args:
            config_file (str): Путь к конфигурационному файлу
        """
        self.config_file = config_file
        self.actions_mapping = {} # словарь для хранения действий для жестов
        self.load_config() # загрузка конфигурации из файла
        
        # добавление глобального контроля частоты выполнения действий
        self.action_cooldown = 1.0  # задержка между действиями в секундах (по умолчанию 1 секунда)
        self.last_action_time = 0  # время последнего выполнения любого действия
        
    def load_config(self):
        """Загрузка конфигурации из файла"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.actions_mapping = json.load(f)
                logger.info(f"Конфигурация загружена из {self.config_file}")
            else:
                self.actions_mapping = {
                    "Open": {"action": "custom_hotkey", "params": {"hotkey": ["ctrl", "o"]}},
                    "Close": {"action": "custom_hotkey", "params": {"hotkey": ["ctrl", "w"]}},
                    "Pointer": {"action": "custom_hotkey", "params": {"hotkey": ["ctrl", "p"]}},
                    "OK": {"action": "custom_hotkey", "params": {"hotkey": ["ctrl", "enter"]}},
                    "Thumb Up": {"action": "custom_hotkey", "params": {"hotkey": ["ctrl", "s"]}},
                    "Peace Sign": {"action": "custom_hotkey", "params": {"hotkey": ["ctrl", "shift", "p"]}},
                    "Thumb Down": {"action": "custom_hotkey", "params": {"hotkey": ["ctrl", "shift", "f"]}},
                    "Rock": {"action": "custom_hotkey", "params": {"hotkey": ["f5"]}},
                }
                self.save_config()
        except Exception as e:
            logger.error(f"Ошибка при загрузке конфигурации: {e}")
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
            # Базовые действия
            {"id": "none", "name": "Нет действия"},
            
            # Действия мыши
            {"id": "click", "name": "Мышь: левый клик"},
            {"id": "right_click", "name": "Мышь: правый клик"},
            {"id": "double_click", "name": "Мышь: двойной клик"},
            {"id": "scroll_up", "name": "Мышь: прокрутка вверх"},
            {"id": "scroll_down", "name": "Мышь: прокрутка вниз"},
            
            # Буфер обмена
            {"id": "copy", "name": "Комбинация клавиш: копировать (Ctrl+C)"},
            {"id": "paste", "name": "Комбинация клавиш: вставить (Ctrl+V)"},
            {"id": "cut", "name": "Комбинация клавиш: вырезать (Ctrl+X)"},
            
            # Общие команды редактирования
            {"id": "select_all", "name": "Комбинация клавиш: выделить всё (Ctrl+A)"},
            {"id": "undo", "name": "Комбинация клавиш: отменить (Ctrl+Z)"},
            {"id": "redo", "name": "Комбинация клавиш: повторить (Ctrl+Y)"},
            {"id": "save", "name": "Комбинация клавиш: сохранить (Ctrl+S)"},
            
            # Команды IDE
            {"id": "run_code", "name": "Комбинация клавиш: запустить код (F5)"},
            
            # Команды навигации в IDE
            {"id": "go_to_definition", "name": "Комбинация клавиш: перейти к определению (F12)"},
            {"id": "find", "name": "Комбинация клавиш: найти (Ctrl+F)"},
            {"id": "find_in_files", "name": "Комбинация клавиш: найти в файлах (Ctrl+Shift+F)"},
            {"id": "quick_open", "name": "Комбинация клавиш: быстрое открытие файла (Ctrl+P)"},
            {"id": "command_palette", "name": "Комбинация клавиш: палитра команд (Ctrl+Shift+P)"},
            
            # Работа с файлами и окнами
            {"id": "new_file", "name": "Комбинация клавиш: новый файл (Ctrl+N)"},
            {"id": "open_file", "name": "Комбинация клавиш: открыть файл (Ctrl+O)"},
            {"id": "close_file", "name": "Комбинация клавиш: закрыть файл (Ctrl+W)"},
            {"id": "close_window", "name": "Комбинация клавиш: закрыть окно (Alt+F4)"},
            {"id": "switch_tab_next", "name": "Комбинация клавиш: следующая вкладка (Ctrl+Tab)"},
            {"id": "switch_tab_prev", "name": "Комбинация клавиш: предыдущая вкладка (Ctrl+Shift+Tab)"},
            
            # Системные команды
            {"id": "screenshot", "name": "Системное: сделать скриншот"}
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
            "click": "Мышь: левый клик",
            "right_click": "Мышь: правый клик",
            "double_click": "Мышь: двойной клик", 
            "scroll_up": "Мышь: прокрутка вверх",
            "scroll_down": "Мышь: прокрутка вниз",
            "save": "Комбинация клавиш: сохранить файл (Ctrl+S)",
            "copy": "Комбинация клавиш: копировать (Ctrl+C)",
            "paste": "Комбинация клавиш: вставить (Ctrl+V)",
            "cut": "Комбинация клавиш: вырезать (Ctrl+X)",
            "select_all": "Комбинация клавиш: выделить всё (Ctrl+A)",
            "undo": "Комбинация клавиш: отменить (Ctrl+Z)",
            "redo": "Комбинация клавиш: повторить (Ctrl+Y)",
            "run_code": "Комбинация клавиш: запустить код (F5)",
            "go_to_definition": "Комбинация клавиш: перейти к определению (F12)",
            "find": "Комбинация клавиш: найти (Ctrl+F)",
            "find_in_files": "Комбинация клавиш: найти в файлах (Ctrl+Shift+F)",
            "quick_open": "Комбинация клавиш: быстрое открытие файла (Ctrl+P)",
            "command_palette": "Комбинация клавиш: палитра команд (Ctrl+Shift+P)",
            "new_file": "Комбинация клавиш: новый файл (Ctrl+N)",
            "open_file": "Комбинация клавиш: открыть файл (Ctrl+O)",
            "close_file": "Комбинация клавиш: закрыть файл (Ctrl+W)",
            "close_window": "Комбинация клавиш: закрыть окно (Alt+F4)",
            "switch_tab_next": "Комбинация клавиш: следующая вкладка (Ctrl+Tab)",
            "switch_tab_prev": "Комбинация клавиш: предыдущая вкладка (Ctrl+Shift+Tab)",
            "screenshot": "Системное: сделать скриншот",
            "custom_hotkey": "Пользовательская комбинация клавиш"
        }
        
        for gesture_name, action_config in self.actions_mapping.items():
            action_type = action_config["action"]
            params = action_config["params"]
            
            description = action_descriptions.get(action_type, "Неизвестное действие")
            details = ""
            
            if action_type == "custom_hotkey" and "hotkey" in params:
                hotkey_str = "+".join(params["hotkey"])
                details = f"Комбинация клавиш: {hotkey_str}"
            
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
        logger.info(f"Установлена глобальная задержка между действиями: {self.action_cooldown} сек")
        # Сбрасываем время последнего действия при изменении задержки
        self.last_action_time = 0
        
    def execute_action(self, gesture_name, x_pos=None, y_pos=None):
        """
        Выполнение действия для указанного жеста
        
        Args:
            gesture_name (str): Название жеста
            x_pos (float, optional): Относительная позиция X (0.0-1.0)
            y_pos (float, optional): Относительная позиция Y (0.0-1.0)
            
        Returns:
            bool: Успешно ли выполнено действие
        """
        if not PYAUTOGUI_AVAILABLE:
            logger.warning(f"Попытка выполнения действия для жеста '{gesture_name}', но pyautogui недоступен")
            return False
            
        if gesture_name not in self.actions_mapping:
            logger.warning(f"Жест '{gesture_name}' не найден в конфигурации")
            return False

        # Проверяем глобальную задержку перед выполнением любого действия
        current_time = time.time()
        if current_time - self.last_action_time < self.action_cooldown:
            logger.info(f"Жест {gesture_name} пропущен: не прошло {self.action_cooldown} сек с последнего действия")
            return False
            
        # Обновляем время последнего действия
        self.last_action_time = current_time
        
        action_config = self.actions_mapping[gesture_name]
        action_type = action_config["action"]
        params = action_config["params"]

        # Получаем русское описание действия
        action_descriptions = {
            "none": "Нет действия",
            "click": "Мышь: левый клик",
            "right_click": "Мышь: правый клик",
            "double_click": "Мышь: двойной клик", 
            "scroll_up": "Мышь: прокрутка вверх",
            "scroll_down": "Мышь: прокрутка вниз",
            "save": "Комбинация клавиш: сохранить файл (Ctrl+S)",
            "copy": "Комбинация клавиш: копировать (Ctrl+C)",
            "paste": "Комбинация клавиш: вставить (Ctrl+V)",
            "cut": "Комбинация клавиш: вырезать (Ctrl+X)",
            "select_all": "Комбинация клавиш: выделить всё (Ctrl+A)",
            "undo": "Комбинация клавиш: отменить (Ctrl+Z)",
            "redo": "Комбинация клавиш: повторить (Ctrl+Y)",
            "run_code": "Комбинация клавиш: запустить код (F5)",
            "go_to_definition": "Комбинация клавиш: перейти к определению (F12)",
            "find": "Комбинация клавиш: найти (Ctrl+F)",
            "find_in_files": "Комбинация клавиш: найти в файлах (Ctrl+Shift+F)",
            "quick_open": "Комбинация клавиш: быстрое открытие файла (Ctrl+P)",
            "command_palette": "Комбинация клавиш: палитра команд (Ctrl+Shift+P)",
            "new_file": "Комбинация клавиш: новый файл (Ctrl+N)",
            "open_file": "Комбинация клавиш: открыть файл (Ctrl+O)",
            "close_file": "Комбинация клавиш: закрыть файл (Ctrl+W)",
            "close_window": "Комбинация клавиш: закрыть окно (Alt+F4)",
            "switch_tab_next": "Комбинация клавиш: следующая вкладка (Ctrl+Tab)",
            "switch_tab_prev": "Комбинация клавиш: предыдущая вкладка (Ctrl+Shift+Tab)",
            "screenshot": "Системное: сделать скриншот",
            "custom_hotkey": "Пользовательская комбинация клавиш"
        }
        action_description = action_descriptions.get(action_type, f"Неизвестное действие: {action_type}")
        
        try:
            # Получаем размеры экрана для справки
            screen_width, screen_height = pyautogui.size()
            
            if action_type == "none":
                logger.info(f"Выполнено действие: {action_description}")
                return True
                
            # Базовые действия мыши
            elif action_type == "click":
                pyautogui.click()
                logger.info(f"Выполнено действие: {action_description}")
                    
            elif action_type == "right_click":
                pyautogui.rightClick()
                logger.info(f"Выполнено действие: {action_description}")
                    
            elif action_type == "double_click":
                pyautogui.doubleClick()
                logger.info(f"Выполнено действие: {action_description}")
                    
            elif action_type == "scroll_up":
                pyautogui.scroll(100)
                logger.info(f"Выполнено действие: {action_description}")
                
            elif action_type == "scroll_down":
                pyautogui.scroll(-100)
                logger.info(f"Выполнено действие: {action_description}")
                
            # Буфер обмена
            elif action_type == "copy":
                pyautogui.hotkey('ctrl', 'c')
                logger.info(f"Выполнено действие: {action_description}")
                
            elif action_type == "paste":
                pyautogui.hotkey('ctrl', 'v')
                logger.info(f"Выполнено действие: {action_description}")
                
            elif action_type == "cut":
                pyautogui.hotkey('ctrl', 'x')
                logger.info(f"Выполнено действие: {action_description}")
                
            # Общие команды редактирования
            elif action_type == "select_all":
                pyautogui.hotkey('ctrl', 'a')
                logger.info(f"Выполнено действие: {action_description}")
                
            elif action_type == "undo":
                pyautogui.hotkey('ctrl', 'z')
                logger.info(f"Выполнено действие: {action_description}")
                
            elif action_type == "redo":
                pyautogui.hotkey('ctrl', 'y')
                logger.info(f"Выполнено действие: {action_description}")
                
            elif action_type == "save":
                pyautogui.hotkey('ctrl', 's')
                logger.info(f"Выполнено действие: {action_description}")
                
            # Команды IDE
            elif action_type == "run_code":
                pyautogui.press('f5')
                logger.info(f"Выполнено действие: {action_description}")
                
            # Команды навигации в IDE
            elif action_type == "go_to_definition":
                pyautogui.press('f12')
                logger.info(f"Выполнено действие: {action_description}")
                
            elif action_type == "find":
                pyautogui.hotkey('ctrl', 'f')
                logger.info(f"Выполнено действие: {action_description}")
                
            elif action_type == "find_in_files":
                pyautogui.hotkey('ctrl', 'shift', 'f')
                logger.info(f"Выполнено действие: {action_description}")
                
            elif action_type == "quick_open":
                pyautogui.hotkey('ctrl', 'p')
                logger.info(f"Выполнено действие: {action_description}")
                
            elif action_type == "command_palette":
                pyautogui.hotkey('ctrl', 'shift', 'p')
                logger.info(f"Выполнено действие: {action_description}")
                
            # Работа с файлами и окнами
            elif action_type == "new_file":
                pyautogui.hotkey('ctrl', 'n')
                logger.info(f"Выполнено действие: {action_description}")
                
            elif action_type == "open_file":
                pyautogui.hotkey('ctrl', 'o')
                logger.info(f"Выполнено действие: {action_description}")
                
            elif action_type == "close_file":
                pyautogui.hotkey('ctrl', 'w')
                logger.info(f"Выполнено действие: {action_description}")
                
            elif action_type == "close_window":
                pyautogui.hotkey('alt', 'f4')
                logger.info(f"Выполнено действие: {action_description}")
                
            elif action_type == "switch_tab_next":
                pyautogui.hotkey('ctrl', 'tab')
                logger.info(f"Выполнено действие: {action_description}")
                
            elif action_type == "switch_tab_prev":
                pyautogui.hotkey('ctrl', 'shift', 'tab')
                logger.info(f"Выполнено действие: {action_description}")
                
            # Системные команды
            elif action_type == "screenshot":
                screenshot = pyautogui.screenshot()
                screenshot_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                                         f"screenshot_{time.strftime('%Y%m%d_%H%M%S')}.png")
                screenshot.save(screenshot_path)
                logger.info(f"Выполнено действие: {action_description}. Сохранено в: {screenshot_path}")
                
            elif action_type == "custom_hotkey" and "hotkey" in params:
                pyautogui.hotkey(*params["hotkey"])
                hotkey_str = "+".join(params["hotkey"])
                logger.info(f"Выполнено действие: Комбинация клавиш: {hotkey_str}")
                
            else:
                logger.warning(f"Неизвестный тип действия: {action_description}")
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при выполнении действия '{action_description}' для жеста '{gesture_name}': {e}")
            return False


if __name__ == "__main__":
    # Тестирование класса
    actions = GestureActions()
    print("Доступные действия:", actions.get_available_actions())
    print("Текущая конфигурация:", actions.actions_mapping) 