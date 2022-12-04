from data.nba_data import *
from display.display import Animation, Display, DisplayManager, Transition
from PIL import Image, ImageColor, ImageDraw, ImageFont
import config
import logging
import math
import numpy as np
import os
import sys
import threading
import tkinter as tk
import traceback
import random

if os.name == 'nt':

  class RGBMatrix:

    def __init__(self, options=None):
      self.options = options
      self.width = 64
      self.height = 32

  class RGBMatrixOptions:
    pass
else:
  from rgbmatrix import RGBMatrix, RGBMatrixOptions


class ImagePlacement:

  def __init__(self, width, height, offset=(0, 0)):
    self.width = width
    self.height = height
    self.h_offset, self.v_offset = offset

  def h(self, placement):
    return int(round(self.width * placement) + self.h_offset)

  def v(self, placement):
    return int(round(self.height * placement) + self.v_offset)

  def get(self, h_placement, v_placement):
    return (self.h(h_placement), self.v(v_placement))

  def topleft(self):
    return (self.h(0), self.v(0))

  def center(self):
    return (self.h(0.5), self.v(0.5))

  def with_h_offset(self, h_offset=1):
    return ImagePlacement(self.width, self.height, offset=(h_offset, 0))

  def with_v_offset(self, v_offset=1):
    return ImagePlacement(self.width, self.height, offset=(0, v_offset))

  def with_offset(self, offset=(1, 1)):
    return ImagePlacement(self.width, self.height, offset=offset)


FIVE_PX_FONT = ImageFont.truetype('assets/5px font.ttf', size=5)
SEVEN_PX_FONT = ImageFont.truetype('assets/7px font.ttf', size=12)
SEVEN_PX_FONT_BOLD = ImageFont.truetype('assets/7px font bold.ttf', size=12)


def draw_text(img, *args, **kwargs):
  # Get the bounding box for the text
  black_bg = Image.new('RGB', (img.width, img.height))
  black_draw = ImageDraw.Draw(black_bg)
  black_draw.text(*args, **kwargs)
  bounding_box = black_bg.getbbox()

  # Make a translucent gray background that is the same size as and overlaid by the text
  gray_bg = Image.new('RGBA', (img.width, img.height), color='#00000080')
  gray_draw = ImageDraw.Draw(gray_bg)
  gray_draw.text(*args, **kwargs)
  text_img = gray_bg.crop(bounding_box)

  # Transparent image
  clear_bg = Image.new('RGBA', (img.width, img.height), color='#00000000')
  clear_bg.paste(text_img, bounding_box)

  # Paste the text with background on the base image
  return Image.alpha_composite(img, clear_bg)


class NBADisplayManager(DisplayManager):

  def __init__(self, favorite_teams, width=64, height=32):
    super().__init__(width=width, height=height)
    self.favorite_teams = favorite_teams
    self.live_game_times = {}
    self.transitions = [
        FadeTransition, PushTransition, CoverTransition, ShredTransition, BallTransition
    ]

  def create_rgb_matrix(self):
    options = RGBMatrixOptions()
    options.rows = self.height
    options.cols = self.width
    options.hardware_mapping = 'adafruit-hat'
    return RGBMatrix(options=options)

  def create_debug_label(self):
    debug_tk = tk.Tk()
    debug_tk.title('Debug display')
    debug_tk.geometry('%dx%d' % (self.width * 10, self.height * 10))
    debug_label = tk.Label(debug_tk)
    return debug_label

  def get_displays_to_show(self):
    try:
      for game in get_important_games(self.favorite_teams):
        if game_is_live(game):
          return [LiveGame(game, get_playbyplay_for_game(game), manager=self)]
      return list(self._get_idle_displays(get_games_for_today()))
    except KeyboardInterrupt:
      sys.exit()
    except Exception as e:
      traceback.print_exc()
      logging.debug(e)
      return [ScreenSaver()]

  def _get_idle_displays(self, games):
    yield ScreenSaver()
    for game in games:
      if not game_has_started(game):
        yield BeforeGame(game)
      elif game_has_ended(game):
        yield AfterGame(game)
      else:
        yield LiveGame(game)
    for standing in get_standings():
      yield Standings(standing)

  def get_corrected_game_clock_text(self, game_id, mins, secs):
    if config.CLOCK_COUNTDOWN:
      last_time, game_mins, game_secs = self.live_game_times.setdefault(game_id, (0, 0, 0))
      if game_mins == mins and game_secs == secs:
        elapsed_seconds = int(time.time() - last_time)
        secs -= elapsed_seconds
        while secs < 0 and mins > 0:
          secs += 60
          mins -= 1
        if mins < 0:
          mins = 0
        if secs < 0:
          secs = 0
      else:
        self.live_game_times[game_id] = (time.time(), mins, secs)
    secs = str(secs)
    if len(secs) == 1:
      secs = f'0{secs}'
    return f'{mins}:{secs}'


# ============= DISPLAYS =============


class BeforeGame(Display):

  def __init__(self, game):
    super().__init__()
    self.game = game

  def get_pre_image(self, matrix, debug_label):
    return Image.new("RGBA", (matrix.width, matrix.height), color='#000')

  def show(self, matrix, debug_label):
    image = Image.new("RGBA", (matrix.width, matrix.height), color='#000')
    ip = ImagePlacement(matrix.width, matrix.height)
    draw = ImageDraw.Draw(image)

    # Team logos
    teams = get_teams_from_game(self.game)
    logos = [get_team_logo(team['id']) for team in teams]

    slide_logo1 = SlideAnimation(
        logos[0], ip.with_v_offset().get(-0.25, 0), base_image=image, steps=20)
    slide_logo1.show(matrix, debug_label)
    image = slide_logo1.get_post_image(matrix, debug_label)

    slide_logo2 = SlideAnimation(
        logos[1], ip.with_v_offset().get(0.78, 0), base_image=image, steps=20)
    slide_logo2.show(matrix, debug_label)
    image = slide_logo2.get_post_image(matrix, debug_label)

    if os.name == 'nt':
      format_str = '@%I:%M'
    else:
      format_str = '@%l:%M'

    game_time = get_game_datetime(self.game).strftime(format_str)
    display_text = '{team1_name}\nVS.\n{team2_name}\n{game_time}'.format(
        team1_name=teams[0]['abbreviation'],
        team2_name=teams[1]['abbreviation'],
        game_time=game_time)

    # Text
    #17,1 for normal anchor
    image = draw_text(
        image,
        ip.center(),
        display_text,
        fill=ImageColor.getrgb('#fff'),
        font=SEVEN_PX_FONT,
        anchor='mm',
        spacing=-2,
        align='center')

    self._display_image(image, 10, matrix, debug_label)


class AfterGame(Display):

  def __init__(self, game):
    super().__init__()
    self.game = game

  def get_pre_image(self, matrix, debug_label):
    image = Image.new("RGBA", (matrix.width, matrix.height), color='#000')
    ip = ImagePlacement(matrix.width, matrix.height)
    draw = ImageDraw.Draw(image)

    # Team logos
    teams = get_teams_from_game(self.game)
    logos = [get_team_logo(team['id']) for team in teams]
    image.paste(logos[0], ip.with_v_offset().get(-0.28, 0))
    image.paste(logos[1], ip.with_v_offset().get(0.78, 0))

    # Neutral text
    scores = get_score_from_game(self.game)
    score_text = '{scores[0]}-{scores[1]}'.format(scores=scores)
    image = draw_text(
        image,
        ip.center(),
        ' \nVS.\n \n{score}'.format(score=score_text),
        fill=ImageColor.getrgb('#fff'),
        font=SEVEN_PX_FONT,
        anchor='mm',
        spacing=-2,
        align='center')

    # First team text
    first_team_won = scores[0] > scores[1]
    image = draw_text(
        image,
        ip.center(),
        '{team1_name}\n \n \n '.format(team1_name=teams[0]['abbreviation']),
        fill=ImageColor.getrgb('#070' if first_team_won else '#f00'),
        font=SEVEN_PX_FONT,
        anchor='mm',
        spacing=-2,
        align='center')

    # Second team text
    image = draw_text(
        image,
        ip.center(),
        ' \n \n{team2_name}\n '.format(team2_name=teams[1]['abbreviation']),
        fill=ImageColor.getrgb('#f00' if first_team_won else '#070'),
        font=SEVEN_PX_FONT,
        anchor='mm',
        spacing=-2,
        align='center')
    return image

  def show(self, matrix, debug_label):
    image = self.get_pre_image(matrix, debug_label)

    teams = get_teams_from_game(self.game)
    team_1_name = teams[0]['nickname']
    team_2_name = teams[1]['nickname']

    if team_1_name in FAVORITE_TEAM_NAMES or team_2_name in FAVORITE_TEAM_NAMES:
      flash = FlashAnimation(image)
      flash.show(matrix, debug_label)
    self._display_image(image, 10, matrix, debug_label)


class LiveGame(Display):

  def __init__(self, game, game_playbyplay=None, manager=None):
    super().__init__()
    self.game = game
    self.game_playbyplay = game_playbyplay
    self.manager = manager

  def get_pre_image(self, matrix, debug_label):
    image = Image.new("RGBA", (matrix.width, matrix.height), color='#000')
    ip = ImagePlacement(matrix.width, matrix.height)

    teams = get_teams_from_game(self.game)
    team_1_name = teams[0]['abbreviation']
    team_2_name = teams[1]['abbreviation']

    if not self.game_playbyplay:
      team_1_score, team_2_score = get_score_from_game(self.game)

      # Team text
      image = draw_text(
          image,
          ip.with_h_offset().get(1 / 6, 0.5),
          '{team_1_name}\n{team_1_score}'.format(
              team_1_name=team_1_name, team_1_score=team_1_score),
          fill=ImageColor.getrgb('#fff'),
          font=SEVEN_PX_FONT_BOLD,
          anchor='mm',
          spacing=6,
          align='center' if team_1_score < 100 else 'left')
      image = draw_text(
          image,
          ip.with_h_offset(-1).get(5 / 6, 0.5),
          '{team_2_name}\n{team_2_score}'.format(
              team_2_name=team_2_name, team_2_score=team_2_score),
          fill=ImageColor.getrgb('#fff'),
          font=SEVEN_PX_FONT_BOLD,
          anchor='mm',
          spacing=6,
          align='center' if team_2_score < 100 else 'right')

    # Game text
    image = draw_text(
        image,
        ip.center(),
        'LIVE\n \n ',
        fill=ImageColor.getrgb('#f00'),
        font=FIVE_PX_FONT,
        anchor='mm',
        spacing=6,
        align='center')
    return image

  def show(self, matrix, debug_label):
    image = self.get_pre_image(matrix, debug_label)
    ip = ImagePlacement(matrix.width, matrix.height)

    if self.game_playbyplay:
      with PlayByPlayUpdateThread(self.game, self.game_playbyplay) as update_thread:
        teams = get_teams_from_game(self.game)
        team_1_name = teams[0]['abbreviation']
        team_2_name = teams[1]['abbreviation']

        while not game_has_ended(update_thread.game):
          image_copy = image.copy()

          team_1_score = int(update_thread.playbyplay[-1]['scoreAway'])
          team_2_score = int(update_thread.playbyplay[-1]['scoreHome'])

          # Team text
          image_copy = draw_text(
              image_copy,
              ip.with_h_offset().get(1 / 6, 0.5),
              '{team_1_name}\n{team_1_score}'.format(
                  team_1_name=team_1_name, team_1_score=team_1_score),
              fill=ImageColor.getrgb('#fff'),
              font=SEVEN_PX_FONT_BOLD,
              anchor='mm',
              spacing=6,
              align='center')
          image_copy = draw_text(
              image_copy,
              ip.with_h_offset(-1).get(5 / 6, 0.5),
              '{team_2_name}\n{team_2_score}'.format(
                  team_2_name=team_2_name, team_2_score=team_2_score),
              fill=ImageColor.getrgb('#fff'),
              font=SEVEN_PX_FONT_BOLD,
              anchor='mm',
              spacing=6,
              align='center')

          period = update_thread.playbyplay[-1]['period']
          mins, secs = get_game_clock(update_thread.playbyplay[-1]['clock'])
          game_clock = self.manager.get_corrected_game_clock_text(update_thread.game['gameId'],
                                                                  int(mins), int(secs))

          image_copy = draw_text(
              image_copy,
              ip.center(),
              ' \nQ{period}\n{clock}'.format(period=period, clock=game_clock),
              fill=ImageColor.getrgb('#fff'),
              font=FIVE_PX_FONT,
              anchor='mm',
              spacing=6,
              align='center')
          self._display_image(image_copy, 1, matrix, debug_label)

        update_thread.exitSignal = 1

    else:
      period = self.game['period']
      game_clock = get_game_clock_text(self.game['gameClock'])
      image = draw_text(
          image,
          ip.center(),
          ' \nQ{period}\n{clock}'.format(period=period, clock=game_clock),
          fill=ImageColor.getrgb('#fff'),
          font=FIVE_PX_FONT,
          anchor='mm',
          spacing=6,
          align='center')
      self._display_image(image, 10, matrix, debug_label)


class Standings(Display):

  def __init__(self, standing):
    super().__init__()
    self.standing = standing

  def get_pre_image(self, matrix, debug_label):
    image = Image.new("RGBA", (matrix.width, matrix.height), color='#000')
    ip = ImagePlacement(matrix.width, matrix.height)
    draw = ImageDraw.Draw(image)

    # Team logos
    team = self.standing['team']
    logo = get_team_logo(team['id'])
    image.paste(logo, ip.with_offset().topleft())

    # Text
    rank = self.standing['rank']
    record = '{wins}-{losses}'.format(wins=self.standing['wins'], losses=self.standing['losses'])
    display_text = '{team}\n#{rank}\n{record}'.format(
        team=team['abbreviation'], rank=rank, record=record)
    image = draw_text(
        image,
        ip.get(0.75, 0.5),
        display_text,
        fill=ImageColor.getrgb('#fff'),
        font=SEVEN_PX_FONT_BOLD,
        anchor='mm',
        spacing=0,
        align='center')

    return image

  def show(self, matrix, debug_label):
    image = self.get_pre_image(matrix, debug_label)
    self._display_image(image, 5, matrix, debug_label)


class ScreenSaver(Display):

  def show(self, matrix, debug_label):
    self._display_image(get_nba_logo(), 10, matrix, debug_label)


# ============= ANIMATIONS =============


class SlideAnimation(Animation):

  def __init__(self,
               image,
               final_loc,
               base_image=Image.new('RGB', (64, 32)),
               steps=60,
               framerate=30):
    super().__init__(framerate=framerate)
    self.add_frames(self.get_animation_frames(image, final_loc, base_image, steps))

  def get_animation_frames(self, image, final_loc, base_image, steps):
    ip = ImagePlacement(base_image.width, base_image.height)
    start_loc = ip.with_offset((-image.width // 2, -image.height // 2)).center()
    dx = (final_loc[0] - start_loc[0]) / steps
    dy = (final_loc[1] - start_loc[1]) / steps

    for step in range(steps + 1):
      paste_x = math.floor(start_loc[0] + step * dx)
      paste_y = math.floor(start_loc[1] + step * dy)

      frame = base_image.copy()
      frame.paste(image, (paste_x, paste_y))
      yield frame


class FlashAnimation(Animation):

  def __init__(self, image, flash_rate=3, flash_count=3, framerate=30):
    super().__init__(framerate=framerate)
    self.add_frames(self.get_animation_frames(image, flash_rate, flash_count))

  def get_animation_frames(self, image, flash_rate, flash_count):
    black_screen = Image.new("RGBA", (image.width, image.height), color='#000')
    for _ in range(flash_count):
      for _ in range(flash_rate):
        yield image
      for _ in range(flash_rate):
        yield black_screen
    for _ in range(flash_rate):
      yield image


# ============= TRANSITIONS =============


class FadeTransition(Transition):

  def __init__(self, start_img, end_img, duration=14, framerate=30):
    self.duration = duration
    super().__init__(start_img, end_img, framerate=framerate)

  def get_transition_frames(self):
    delta = 255 / (self.duration / 2)
    for i in range(1, int(self.duration / 2 + 1)):
      img = self.start_img.copy()
      color = int(delta * i)
      img.paste(
          Image.new("RGBA", (img.width, img.height), color='#000'),
          mask=Image.new("RGBA", (img.width, img.height), color=(color, color, color, color)))
      yield img
    for i in range(1, int(self.duration / 2 + 1)):
      img = Image.new("RGBA", (self.start_img.width, self.start_img.height), color='#000')
      color = int(delta * i)
      img.paste(
          self.end_img,
          mask=Image.new("RGBA", (img.width, img.height), color=(color, color, color, color)))
      yield img


class PushTransition(Transition):

  def __init__(self,
               start_img,
               end_img,
               framerate=30,
               x_direction=None,
               y_direction=None,
               duration=14):
    if x_direction is None:
      x_direction = random.randint(-1, 1)
    if y_direction is None:
      y_direction = random.randint(-1, 1)
    if not x_direction and not y_direction:
      x_direction = 1
    self.x_direction = x_direction
    self.y_direction = y_direction
    self.duration = duration
    super().__init__(start_img, end_img, framerate=framerate)

  def get_transition_frames(self):
    ip = ImagePlacement(self.start_img.width, self.start_img.height)
    start_pos_x, start_pos_y = ip.with_offset(
        (self.x_direction, self.y_direction)).get(self.x_direction, self.y_direction)

    delta_x = int(-start_pos_x / self.duration)
    delta_y = int(-start_pos_y / self.duration)

    for i in range(0, self.duration):
      image = Image.new("RGBA", (self.start_img.width, self.start_img.height), color='#000')
      image.paste(self.start_img, box=(delta_x * i, delta_y * i))
      image.paste(self.end_img, box=(start_pos_x + delta_x * i, start_pos_y + delta_y * i))
      yield image
    yield self.end_img


class CoverTransition(Transition):

  def __init__(self,
               start_img,
               end_img,
               framerate=30,
               x_direction=None,
               y_direction=None,
               duration=14):
    if x_direction is None:
      x_direction = random.randint(-1, 1)
    if y_direction is None:
      y_direction = random.randint(-1, 1)
    if not x_direction and not y_direction:
      x_direction = 1
    self.x_direction = x_direction
    self.y_direction = y_direction
    self.duration = duration
    super().__init__(start_img, end_img, framerate=framerate)

  def get_transition_frames(self):
    ip = ImagePlacement(self.start_img.width, self.start_img.height)
    start_pos_x, start_pos_y = ip.with_offset(
        (self.x_direction, self.y_direction)).get(self.x_direction, self.y_direction)

    delta_x = int(-start_pos_x / self.duration)
    delta_y = int(-start_pos_y / self.duration)

    for i in range(0, self.duration):
      image = self.start_img.copy()
      image.paste(self.end_img, box=(start_pos_x + delta_x * i, start_pos_y + delta_y * i))
      yield image
    yield self.end_img


class ZoomTransition(Transition):
  pass


class ShredTransition(Transition):

  def __init__(self, start_img, end_img, framerate=30, direction=None, duration=20):
    if direction is None:
      direction = random.randint(0, 1)
    self.direction = direction
    self.duration = duration
    super().__init__(start_img, end_img, framerate=framerate)

  def get_transition_frames(self):
    if self.start_img.width != 64 or self.start_img.height != 32:
      return []
    if self.direction == 0:
      mask1 = Image.open('assets/vmask1.png')
      mask2 = Image.open('assets/vmask2.png')
      delta_x = 0
      delta_y = int(self.start_img.height / (self.duration / 2))
    else:
      mask1 = Image.open('assets/hmask1.png')
      mask2 = Image.open('assets/hmask2.png')
      delta_x = int(self.start_img.width / (self.duration / 2))
      delta_y = 0

    for i in range(0, self.duration // 2):
      image = Image.new("RGBA", (self.start_img.width, self.start_img.height), color='#000')

      image.paste(self.start_img, box=(delta_x * i, delta_y * i), mask=mask1)
      image.paste(self.start_img, box=(-delta_x * i, -delta_y * i), mask=mask2)
      yield image
    for i in range(self.duration // 2, 0, -1):
      image = Image.new("RGBA", (self.start_img.width, self.start_img.height), color='#000')

      image.paste(self.end_img, box=(delta_x * i, delta_y * i), mask=mask1)
      image.paste(self.end_img, box=(-delta_x * i, -delta_y * i), mask=mask2)
      yield image
    yield self.end_img


class BallTransition(Transition):

  def __init__(self, start_img, end_img, framerate=30, duration=15):
    self.duration = duration
    super().__init__(start_img, end_img, framerate)

  def get_transition_frames(self):
    basketball_img = get_basketball_img(size=self.start_img.height)
    basketball_offset = basketball_img.width // 2
    ip = ImagePlacement(self.start_img.width, self.start_img.height)  #.with_h_offset(-basketball_offset)

    delta_x = 1 / self.duration

    for i in range(self.duration, -self.duration // 2, -1):
      x = ip.h(delta_x * i)
      image = Image.new("RGBA", (self.start_img.width, self.start_img.height), color='#000')
      if 0 < x:
        image.paste(self.start_img.crop((0, 0, x + basketball_offset, self.start_img.height)))
      if x + basketball_offset < self.end_img.width:
        image.paste(
            self.end_img.crop((x + basketball_offset, 0, self.end_img.width, self.end_img.height)),
            box=(x + basketball_offset, 0))

      rot_basketball_img = basketball_img.rotate(-360 // self.duration * i)
      image.paste(rot_basketball_img, box=(x, 0), mask=basketball_img)
      yield image
    yield self.end_img


class PlayByPlayUpdateThread(threading.Thread):

  def __init__(self, game, playbyplay):
    super().__init__()
    self.game = game
    self.exitSignal = 0
    self.playbyplay = playbyplay

  def run(self):
    while not self.exitSignal:
      self.playbyplay = get_playbyplay_for_game(self.game, cache_override=True)
      self.game = get_game_by_id(self.game['gameId'], cache_override=True)
      time.sleep(1)
    logging.debug('Thread for game %s exited.' % self.game['gameId'])

  def stop(self):
    self.exitSignal = 1

  def __enter__(self):
    self.start()
    return self

  def __exit__(self, *args, **kwargs):
    self.stop()