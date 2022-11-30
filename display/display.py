from datetime import datetime, timedelta, timezone
from PIL import ImageTk
import logging
import sys
import time
import traceback
import random


class DisplayManager(object):
  _SECONDS_IN_DAY = 86400

  def __init__(self, width=64, height=32):
    self.width = width
    self.height = height
    self.scheduled_actions = []
    self.start_time, self.stop_time = None, None
    self.start_day, self.stop_day = None, None
    self.time_zone = timezone.utc
    self.rgb_matrix = self.create_rgb_matrix()
    self.debug_label = self.create_debug_label()
    self.transitions = []

  def start(self):
    while True:
      self._sleep_if_necessary()
      self._run_scheduled_actions()
      displays_to_show = self.get_displays_to_show()
      for index, display in enumerate(displays_to_show):
        try:
          display.show(self.rgb_matrix, self.debug_label)
          if self.transitions and len(displays_to_show) > 1 and index != len(displays_to_show) - 1:
            self.show_transition(
                display.current_image,
                displays_to_show[index + 1].get_pre_image(self.rgb_matrix, self.debug_label))
        except KeyboardInterrupt:
          sys.exit()
        except Exception as e:
          traceback.print_exc()
          logging.debug(e)

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
      checks = [
          self.start_day > self.stop_day, current_day >= self.start_day, current_day < self.stop_day
      ]
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
      checks = [
          self.start_time > self.stop_time, current_time >= self.start_time,
          current_time < self.stop_time
      ]
      if len(filter(lambda x: x, checks)) < 2:
        seconds_to_sleep = (datetime.combine(today_date, self.start_time) -
                            datetime.combine(today_date, current_time)).total_seconds()
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

  def set_start_and_stop_times(self, start_time, stop_time, time_zone=None):
    if start_time == stop_time:
      raise Exception('Start and stop times must be different')

    self.start_time = start_time
    self.stop_time = stop_time
    if time_zone:
      self.time_zone = time_zone

  # Where Monday is 1 and Sunday is 7
  def set_start_and_stop_days(self, start_day, stop_day, time_zone=None):
    if start_day == stop_day:
      raise Exception('Start and stop days must be different')
    self.start_day = start_day
    self.stop_day = stop_day
    if time_zone:
      self.time_zone = time_zone

  def schedule_action(self, action_datetime, action_func):
    self.scheduled_actions.append((action_datetime, action_func))

  def show_transition(self, start_img, end_img, transition_num=None):
    if transition_num is None:
      transition_num = random.randint(0, len(self.transitions) - 1)
    if isinstance(self.transitions[transition_num], tuple):
      transition_class, args, kwargs = self.transitions[transition_num]
      transition = transition_class(start_img, end_img, *args, **kwargs)
    else:
      transition_class = self.transitions[transition_num]
      transition = transition_class(start_img, end_img)
    transition.show(self.rgb_matrix, self.debug_label)


class Display(object):

  def __init__(self):
    pass

  def get_pre_image(self, matrix, debug_label):
    raise NotImplementedError("Subclasses must implement get_pre_image()")

  def show(self, matrix, debug_label):
    raise NotImplementedError("Subclasses must implement show()")

  def _update(self, debug_label):
    debug_label.master.update_idletasks()
    debug_label.master.update()

  def _debug_image(self, image, debug_label):
    # image.save('assets/testing/%d.png' % time.time())
    big_img = image.resize((image.width * 10, image.height * 10))
    photo = ImageTk.PhotoImage(big_img)
    debug_label.config(image=photo)
    debug_label.image = photo  # keep a reference
    debug_label.pack()

    self._update(debug_label)

  def _display_image(self, image, display_secs, matrix, debug_label):
    self.current_image = image
    self._debug_image(image, debug_label)

    display_full_secs = int(display_secs // 1)
    display_part_secs = display_secs - display_full_secs

    for _ in range(0, display_full_secs):
      for _ in range(10):
        time.sleep(0.1)
        self._update(debug_label)
    time.sleep(display_part_secs)
    self._update(debug_label)


class Animation(Display):

  def __init__(self, framerate=30):
    super().__init__()
    self.framerate = framerate
    self.frames = list()

  def get_pre_image(self, matrix, debug_label):
    return self.frames[0]

  def get_post_image(self, matrix, debug_label):
    return self.frames[-1]

  def show(self, matrix, debug_label):
    if len(self.frames) == 0:
      raise NotImplementedError("Subclasses must define at least one frame")
    for frame in self.frames:
      self._display_image(frame, 1 / self.framerate, matrix, debug_label)

  def add_frame(self, frame):
    self.frames.append(frame)

  def add_frames(self, frames):
    self.frames.extend(list(frames))


class Transition(Animation):

  def __init__(self, start_img, end_img, framerate=30):
    super().__init__(framerate=framerate)
    self.start_img = start_img
    self.end_img = end_img
    self.add_frames(self.get_transition_frames())

  def get_transition_frames(self):
    raise NotImplementedError("Subclasses must implement get_transition_frames()")