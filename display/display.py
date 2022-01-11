from datetime import datetime, timedelta, timezone
from PIL import Image, ImageTk
import threading
import time
import tkinter as tk

class DataCache(object):
  def __init__(self):
    self._data = dict()

  # Starts subscription on newly spawned thread
  def start_subscribe_thread(self, var_name, update_func, active_func, frequency, transform_func=None, consume_func=None, start_value=None):
    if start_value or not var_name in self._data:
      self[var_name] = start_value
    thread = threading.Thread(name='Thread-%s'%var_name, target=self._subscribe_to_value, args=(var_name, update_func, active_func, frequency), kwargs={'transform_func': transform_func, 'consume_func': consume_func})
    thread.start()
  
  # Subscribes on the current thread
  def _subscribe_to_value(self, var_name, update_func, active_func, frequency, transform_func=None, consume_func=None):
    while active_func():
      self.update_value(var_name, update_func, transform_func=transform_func, consume_func=consume_func)
      time.sleep(frequency.total_seconds())

  def update_value(self, var_name, update_func, transform_func=None, consume_func=None):
    self[var_name] = transform_func(update_func()) if transform_func else update_func()
    if consume_func:
      consume_func(self[var_name])

  def __getitem__(self, key):
    return self._data[key]
  
  def __setitem__(self, key, value):
    self._data[key] = value

class DisplayManager(object):
  _SECONDS_IN_DAY = 86400

  def __init__(self):
    self.data_cache = DataCache()
    self.scheduled_actions = []
    self.start_time, self.stop_time = None, None
    self.start_day, self.stop_day = None, None
    self.time_zone = timezone.utc
    self.rgb_matrix = self.create_rgb_matrix()

  def start(self):
    while True:
      self._sleep_if_necessary()
      self._run_scheduled_actions()
      for display, display_time in self.get_displays_to_show():
        display.show(self.rgb_matrix)
        time.sleep(display_time)

  def create_rgb_matrix(self):
    raise NotImplementedError("create_rgb_matrix must be implemented by the subclass")
    
  def create_debug_label(self):
    raise NotImplementedError("create_debug_label must be implemented by the subclass")

  def get_displays_to_show():
    raise NotImplementedError("get_displays_to_show must be implemented by the subclass")

  def _sleep_if_necessary(self):
    if self.start_day and self.stop_day:
      current_day = datetime.now(self.time_zone).isoweekday()

      # Weird checks
      checks =  [self.start_day > self.stop_day, current_day >= self.start_day, current_day < self.stop_day]
      if len(filter(lambda x: x, checks)) < 2:
        days_to_sleep = self.start_day - current_day
        if days_to_sleep < 0:
          days_to_sleep += 7
        time.sleep(timedelta(days=days_to_sleep).total_seconds() + 30)
        self._sleep_if_necessary()

    if self.start_time and self.stop_time:
      now = datetime.now(self.time_zone)
      current_time = now.time()
      today_date = now.date()

      # Weird checks
      checks =  [self.start_time > self.stop_time, current_time >= self.start_time, current_time < self.stop_time]
      if len(filter(lambda x: x, checks)) < 2:
        seconds_to_sleep = (datetime.combine(today_date, self.start_time) - datetime.combine(today_date, current_time)).total_seconds()
        if seconds_to_sleep < 0:
          seconds_to_sleep += self._SECONDS_IN_DAY
        time.sleep(seconds_to_sleep + 30)
        self._sleep_if_necessary()
  
  def _run_scheduled_actions(self, *args):
    new_action_list = list()
    for action_datetime, action_func, *args in self.scheduled_actions:
      if datetime.now() > action_datetime:
        action_func(*args)
      else:
        new_action_list.append((action_datetime, action_func))
    self.scheduled_actions = new_action_list

  def set_start_and_stop_times(self, start_time, stop_time, time_zone = None):
    if start_time == stop_time:
      raise Exception('Start and stop times must be different')

    self.start_time = start_time
    self.stop_time = stop_time
    if time_zone:
      self.time_zone = time_zone

  # Where Monday is 1 and Sunday is 7
  def set_start_and_stop_days(self, start_day, stop_day, time_zone = None):
    if start_day == stop_day:
      raise Exception('Start and stop days must be different')
    self.start_day = start_day
    self.stop_day = stop_day
    if time_zone:
      self.time_zone = time_zone
  
  def schedule_action(self, action_datetime, action_func):
    self.scheduled_actions.append((action_datetime, action_func))

class Display(object):
  def __init__(self):
    pass
  
  def show(self, matrix, debug_label):
    raise NotImplementedError("Subclasses must implement show()")
  
  def _debug_image(self, image, debug_label):
    big_img = image.resize((image.width*10, image.height*10))
    photo = ImageTk.PhotoImage(big_img)
    debug_label.config(image=photo)
    debug_label.image = photo # keep a reference
    debug_label.pack()
    
    debug_label.master.update_idletasks()
    debug_label.master.update()

class Animation(Display):
  def __init__(self, framerate=30):
    super().__init__()
    self.framerate = framerate
    self.frames = list()
  
  def show(self, matrix, debug_tk):
    if len(self.frames) == 0:
      raise NotImplementedError("Sublclasses must define at least one frame")
    for frame_func in self.frames:
      frame_func(matrix, debug_tk)
      time.sleep(1/self.framerate)

  def add_frame(self, frame_func):
    self.frames.append(frame_func)

  def add_frames(self, frame_funcs):
    self.frames.extend(frame_funcs)
