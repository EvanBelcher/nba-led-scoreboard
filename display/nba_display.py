from data.nba_data import *
from datetime import timedelta
from dateutil import parser
from display.display import Display, DisplayManager 
from PIL import Image, ImageColor, ImageDraw, ImageFont, ImageShow
from rgbmatrix import RGBMatrix, RGBMatrixOptions
import tkinter as tk


class NBADisplayManager(DisplayManager):
  def __init__(self, favorite_teams, width=64, height=32):
    super().__init__()
    self.favorite_teams = favorite_teams
    self.width = width
    self.height = height

  def create_rgb_matrix(self):
    options = RGBMatrixOptions()
    options.rows = self.height
    options.cols = self.width
    options.hardware_mapping = 'adafruit-hat'
    return RGBMatrix(options = options)
    
  def create_debug_label(self):
    debug_tk = tk.Tk()
    debug_tk.title('Debug display')
    debug_tk.geometry('%dx%d'%(self.width*10, self.height*10))
    debug_label = tk.Label(debug_tk)
    return debug_label
  
  def get_displays_to_show(self):
    for game in get_important_games(self.favorite_teams):
      if game_is_live(game):
        return [LiveGame(game, get_playbyplay_for_game(game))]
    return list(self._get_idle_displays(self, get_games_for_today()))

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

class BeforeGame(Display):
  def __init__(self, game):
    super().__init__()
    self.game = game

  def show(self, matrix, debug_label):
    image = Image.new("RGB", (matrix.width, matrix.height))
    draw = ImageDraw.Draw(image)
    draw.text((1, 1), 'hello\nworld', fill=ImageColor.getrgb('#f00'))
    self._debug_image(image, debug_label)
    time.sleep(5)
    image = Image.new("RGB", (matrix.width, matrix.height))
    draw = ImageDraw.Draw(image)
    draw.text((1, 1), 'hello\nworld', fill=ImageColor.getrgb('#0f0'))
    self._debug_image(image, debug_label)
    time.sleep(5)

class AfterGame(Display):
  def __init__(self, game):
    super().__init__()
    self.game = game

  def show(self, matrix, debug_label):
    pass

class LiveGame(Display):
  def __init__(self, game, game_playbyplay=None):
    super().__init__()
    self.game = game
    self.game_playbyplay = game_playbyplay

  def show(self, matrix, debug_label):
    pass

class Standings(Display):
  def __init__(self, standing):
    super().__init__()
    self.standing = standing

  def show(self, matrix, debug_label):
    pass

class ScreenSaver(Display):
  def __init(self):
    super().__init__()
  
  def show(self, matrix, debug_label):
    pass
