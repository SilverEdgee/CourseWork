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
        self.actions_mapping = {} # словарь для хранения действий для жестов
        self.load_config() # загрузка конфигурации из файла
        
        # добавление контроля частоты выполнения действий
        self.action_cooldown = 1.0  # задержка между действиями в секундах (по умолчанию 1 секунда)
        self.last_action_time = {}  # словарь для хранения времени последнего выполнения каждого действия
        
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
            # Базовые действия
            {"id": "none", "name": "Нет действия"},
            {"id": "custom_hotkey", "name": "Своя комбинация клавиш"},
            
            # Действия мыши
            {"id": "click", "name": "Клик мыши"},
            {"id": "right_click", "name": "Правый клик"},
            {"id": "double_click", "name": "Двойной клик"},
            {"id": "scroll_up", "name": "Прокрутка вверх"},
            {"id": "scroll_down", "name": "Прокрутка вниз"},
            
            # Буфер обмена
            {"id": "copy", "name": "Копировать (Ctrl+C)"},
            {"id": "paste", "name": "Вставить (Ctrl+V)"},
            {"id": "cut", "name": "Вырезать (Ctrl+X)"},
            
            # Общие команды редактирования
            {"id": "select_all", "name": "Выделить всё (Ctrl+A)"},
            {"id": "undo", "name": "Отменить (Ctrl+Z)"},
            {"id": "redo", "name": "Повторить (Ctrl+Y)"},
            {"id": "save", "name": "Сохранить (Ctrl+S)"},
            
            # Команды IDE
            {"id": "run_code", "name": "Запустить код (F5)"},
            {"id": "debug", "name": "Запустить отладку (F9)"},
            {"id": "stop_debug", "name": "Остановить отладку (Shift+F5)"},
            {"id": "toggle_breakpoint", "name": "Поставить/убрать точку останова (F9)"},
            {"id": "step_over", "name": "Шаг с обходом (F10)"},
            {"id": "step_into", "name": "Шаг с заходом (F11)"},
            
            # Команды навигации в IDE
            {"id": "go_to_definition", "name": "Перейти к определению (F12)"},
            {"id": "find", "name": "Найти (Ctrl+F)"},
            {"id": "find_in_files", "name": "Найти в файлах (Ctrl+Shift+F)"},
            {"id": "quick_open", "name": "Быстрое открытие файла (Ctrl+P)"},
            {"id": "command_palette", "name": "Палитра команд (Ctrl+Shift+P)"},
            
            # Работа с файлами и окнами
            {"id": "new_file", "name": "Новый файл (Ctrl+N)"},
            {"id": "open_file", "name": "Открыть файл (Ctrl+O)"},
            {"id": "close_file", "name": "Закрыть файл (Ctrl+W)"},
            {"id": "close_window", "name": "Закрыть окно (Alt+F4)"},
            {"id": "switch_tab_next", "name": "Следующая вкладка (Ctrl+Tab)"},
            {"id": "switch_tab_prev", "name": "Предыдущая вкладка (Ctrl+Shift+Tab)"},
            
            # Форматирование кода
            {"id": "format_code", "name": "Форматировать код (Shift+Alt+F)"},
            {"id": "comment_line", "name": "Закомментировать строки (Ctrl+/)"},
            {"id": "indent", "name": "Увеличить отступ (Tab)"},
            {"id": "outdent", "name": "Уменьшить отступ (Shift+Tab)"},
            
            # Системные команды
            {"id": "screenshot", "name": "Сделать скриншот"},
            {"id": "volume_up", "name": "Увеличить громкость"},
            {"id": "volume_down", "name": "Уменьшить громкость"},
            {"id": "volume_mute", "name": "Выключить звук"},
            {"id": "media_play_pause", "name": "Воспроизведение/Пауза"},
            {"id": "media_next", "name": "Следующий трек"},
            {"id": "media_prev", "name": "Предыдущий трек"}
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
        
        action_config = self.actions_mapping[gesture_name]
        action_type = action_config["action"]
        params = action_config["params"]
        
        try:
            # Получаем размеры экрана для справки
            screen_width, screen_height = pyautogui.size()
            
            if action_type == "none":
                return True
                
            # Базовые действия мыши
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
                pyautogui.scroll(100)
                logger.info(f"Выполнена прокрутка вверх")
                
            elif action_type == "scroll_down":
                if not self._check_cooldown(action_type):
                    return False
                pyautogui.scroll(-100)
                logger.info(f"Выполнена прокрутка вниз")
                
            # Буфер обмена
            elif action_type == "copy":
                if not self._check_cooldown(action_type):
                    return False
                pyautogui.hotkey('ctrl', 'c')
                logger.info(f"Выполнено копирование")
                
            elif action_type == "paste":
                if not self._check_cooldown(action_type):
                    return False
                pyautogui.hotkey('ctrl', 'v')
                logger.info(f"Выполнена вставка")
                
            elif action_type == "cut":
                if not self._check_cooldown(action_type):
                    return False
                pyautogui.hotkey('ctrl', 'x')
                logger.info(f"Выполнено вырезание")
                
            # Общие команды редактирования
            elif action_type == "select_all":
                if not self._check_cooldown(action_type):
                    return False
                pyautogui.hotkey('ctrl', 'a')
                logger.info(f"Выполнено выделение всего")
                
            elif action_type == "undo":
                if not self._check_cooldown(action_type):
                    return False
                pyautogui.hotkey('ctrl', 'z')
                logger.info(f"Выполнена отмена действия")
                
            elif action_type == "redo":
                if not self._check_cooldown(action_type):
                    return False
                pyautogui.hotkey('ctrl', 'y')
                logger.info(f"Выполнен повтор действия")
                
            elif action_type == "save":
                if not self._check_cooldown(action_type):
                    return False
                pyautogui.hotkey('ctrl', 's')
                logger.info(f"Выполнено сохранение")
                
            # Команды IDE
            elif action_type == "run_code":
                if not self._check_cooldown(action_type):
                    return False
                pyautogui.press('f5')
                logger.info(f"Выполнен запуск кода")
                
            elif action_type == "debug":
                if not self._check_cooldown(action_type):
                    return False
                pyautogui.press('f9')
                logger.info(f"Запущена отладка")
                
            elif action_type == "stop_debug":
                if not self._check_cooldown(action_type):
                    return False
                pyautogui.hotkey('shift', 'f5')
                logger.info(f"Остановлена отладка")
                
            elif action_type == "toggle_breakpoint":
                if not self._check_cooldown(action_type):
                    return False
                pyautogui.press('f9')
                logger.info(f"Переключена точка останова")
                
            elif action_type == "step_over":
                if not self._check_cooldown(action_type):
                    return False
                pyautogui.press('f10')
                logger.info(f"Выполнен шаг с обходом")
                
            elif action_type == "step_into":
                if not self._check_cooldown(action_type):
                    return False
                pyautogui.press('f11')
                logger.info(f"Выполнен шаг с заходом")
                
            # Команды навигации в IDE
            elif action_type == "go_to_definition":
                if not self._check_cooldown(action_type):
                    return False
                pyautogui.press('f12')
                logger.info(f"Переход к определению")
                
            elif action_type == "find":
                if not self._check_cooldown(action_type):
                    return False
                pyautogui.hotkey('ctrl', 'f')
                logger.info(f"Открыт поиск")
                
            elif action_type == "find_in_files":
                if not self._check_cooldown(action_type):
                    return False
                pyautogui.hotkey('ctrl', 'shift', 'f')
                logger.info(f"Открыт поиск по файлам")
                
            elif action_type == "quick_open":
                if not self._check_cooldown(action_type):
                    return False
                pyautogui.hotkey('ctrl', 'p')
                logger.info(f"Открыто быстрое открытие файла")
                
            elif action_type == "command_palette":
                if not self._check_cooldown(action_type):
                    return False
                pyautogui.hotkey('ctrl', 'shift', 'p')
                logger.info(f"Открыта палитра команд")
                
            # Работа с файлами и окнами
            elif action_type == "new_file":
                if not self._check_cooldown(action_type):
                    return False
                pyautogui.hotkey('ctrl', 'n')
                logger.info(f"Создан новый файл")
                
            elif action_type == "open_file":
                if not self._check_cooldown(action_type):
                    return False
                pyautogui.hotkey('ctrl', 'o')
                logger.info(f"Открыт файл")
                
            elif action_type == "close_file":
                if not self._check_cooldown(action_type):
                    return False
                pyautogui.hotkey('ctrl', 'w')
                logger.info(f"Закрыт файл")
                
            elif action_type == "close_window":
                if not self._check_cooldown(action_type):
                    return False
                pyautogui.hotkey('alt', 'f4')
                logger.info(f"Закрыто окно")
                
            elif action_type == "switch_tab_next":
                if not self._check_cooldown(action_type):
                    return False
                pyautogui.hotkey('ctrl', 'tab')
                logger.info(f"Переход к следующей вкладке")
                
            elif action_type == "switch_tab_prev":
                if not self._check_cooldown(action_type):
                    return False
                pyautogui.hotkey('ctrl', 'shift', 'tab')
                logger.info(f"Переход к предыдущей вкладке")
                
            # Форматирование кода
            elif action_type == "format_code":
                if not self._check_cooldown(action_type):
                    return False
                pyautogui.hotkey('shift', 'alt', 'f')
                logger.info(f"Форматирование кода")
                
            elif action_type == "comment_line":
                if not self._check_cooldown(action_type):
                    return False
                pyautogui.hotkey('ctrl', '/')
                logger.info(f"Комментирование строк")
                
            elif action_type == "indent":
                if not self._check_cooldown(action_type):
                    return False
                pyautogui.press('tab')
                logger.info(f"Увеличен отступ")
                
            elif action_type == "outdent":
                if not self._check_cooldown(action_type):
                    return False
                pyautogui.hotkey('shift', 'tab')
                logger.info(f"Уменьшен отступ")
                
            # Системные команды
            elif action_type == "screenshot":
                if not self._check_cooldown(action_type):
                    return False
                screenshot = pyautogui.screenshot()
                screenshot_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                                         f"screenshot_{pyautogui.time().strftime('%Y%m%d_%H%M%S')}.png")
                screenshot.save(screenshot_path)
                logger.info(f"Скриншот сохранен: {screenshot_path}")
                
            elif action_type == "volume_up":
                if not self._check_cooldown(action_type):
                    return False
                pyautogui.press('volumeup')
                logger.info(f"Увеличена громкость")
                
            elif action_type == "volume_down":
                if not self._check_cooldown(action_type):
                    return False
                pyautogui.press('volumedown')
                logger.info(f"Уменьшена громкость")
                
            elif action_type == "volume_mute":
                if not self._check_cooldown(action_type):
                    return False
                pyautogui.press('volumemute')
                logger.info(f"Звук выключен/включен")
                
            elif action_type == "media_play_pause":
                if not self._check_cooldown(action_type):
                    return False
                pyautogui.press('playpause')
                logger.info(f"Воспроизведение/пауза")
                
            elif action_type == "media_next":
                if not self._check_cooldown(action_type):
                    return False
                pyautogui.press('nexttrack')
                logger.info(f"Следующий трек")
                
            elif action_type == "media_prev":
                if not self._check_cooldown(action_type):
                    return False
                pyautogui.press('prevtrack')
                logger.info(f"Предыдущий трек")
                
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