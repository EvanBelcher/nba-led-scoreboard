from logging import debug
from data.nba_data import *
from display.display import Animation, Display, DisplayManager
from PIL import Image, ImageColor, ImageDraw, ImageFont
from rgbmatrix import RGBMatrix, RGBMatrixOptions
import logging
import math
import tkinter as tk
import traceback


class ImagePlacement:

  def __init__(self, width, height, offset=(0, 0)):
    self.width = width
    self.height = height
    self.h_offset, self.v_offset = offset

  def h(self, placement):
    return round(self.width * placement) + self.h_offset

  def v(self, placement):
    return round(self.height * placement) + self.v_offset

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


def slide_img(matrix, debug_label, img, final_loc, base_img=Image.new('RGB', (64, 32)), steps=60):
  ip = ImagePlacement(base_img.width, base_img.height)

  start_loc = ip.with_offset((-img.width // 2, -img.height // 2)).center()
  dx = (final_loc[0] - start_loc[0]) / steps
  dy = (final_loc[1] - start_loc[1]) / steps

  animation = Animation()
  last_frame = None

  for step in range(steps + 1):
    paste_x = math.floor(start_loc[0] + step * dx)
    paste_y = math.floor(start_loc[1] + step * dy)

    frame = base_img.copy()
    frame.paste(img, (paste_x, paste_y))
    animation.add_frame(frame)
    last_frame = frame

  animation.show(matrix, debug_label)
  return last_frame


class NBADisplayManager(DisplayManager):

  def __init__(self, favorite_teams, width=64, height=32):
    super().__init__(width=width, height=height)
    self.favorite_teams = favorite_teams

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
          return [LiveGame(game, get_playbyplay_for_game(game))]
      return list(self._get_idle_displays(get_games_for_today()))
    except KeyboardInterrupt:
          sys.exit()  
    except Exception as e:
      traceback.print_exc()
      logging.debug(e)
      return [ScreenSaver()]

  def _get_idle_displays(self, games):
    # yield ScreenSaver()
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
    image = Image.new("RGBA", (matrix.width, matrix.height), color='#000')
    ip = ImagePlacement(matrix.width, matrix.height)
    draw = ImageDraw.Draw(image)

    # Team logos
    teams = get_teams_from_game(self.game)
    logos = [get_team_logo(team['id']) for team in teams]

    image = slide_img(matrix, debug_label,
      logos[0], ip.with_v_offset().get(-0.25, 0), base_img=image, steps=20)
    image = slide_img(matrix, debug_label, logos[1], ip.with_v_offset().get(0.78, 0), base_img=image, steps=20)

    game_time = get_game_datetime(self.game).strftime('@%l:%M')
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

  def show(self, matrix, debug_label):
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

    self._display_image(image, 10, matrix, debug_label)


class LiveGame(Display):

  def __init__(self, game, game_playbyplay=None):
    super().__init__()
    self.game = game
    self.game_playbyplay = game_playbyplay

  def show(self, matrix, debug_label):
    image = Image.new("RGBA", (matrix.width, matrix.height), color='#000')
    ip = ImagePlacement(matrix.width, matrix.height)
    draw = ImageDraw.Draw(image)

    teams = get_teams_from_game(self.game)
    team_1_name = teams[0]['abbreviation']
    team_2_name = teams[1]['abbreviation']

    if self.game_playbyplay:
      team_1_score = int(self.game_playbyplay[-1]['scoreAway'])
      team_2_score = int(self.game_playbyplay[-1]['scoreHome'])
      period = self.game_playbyplay[-1]['period']
      game_clock = get_game_clock(self.game_playbyplay[-1]['clock'])
    else:
      team_1_score, team_2_score = get_score_from_game(self.game)
      period = self.game['period']
      game_clock = get_game_clock(self.game['gameClock'])

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
    image = draw_text(
      image,
      ip.center(),
      ' \nQ{period}\n{clock}'.format(period=period, clock=game_clock),
      fill=ImageColor.getrgb('#fff'),
      font=FIVE_PX_FONT,
      anchor='mm',
      spacing=6,
      align='center')

    self._display_image(image, 5 if self.game_playbyplay else 10, matrix,
                        debug_label)


class Standings(Display):

  def __init__(self, standing):
    super().__init__()
    self.standing = standing

  def show(self, matrix, debug_label):
    image = Image.new("RGBA", (matrix.width, matrix.height), color='#000')
    ip = ImagePlacement(matrix.width, matrix.height)
    draw = ImageDraw.Draw(image)

    # Team logos
    team = self.standing['team']
    logo = get_team_logo(team['id'])
    image.paste(logo, ip.with_offset().topleft())

    # Text
    rank = self.standing['rank']
    record = '{wins}-{losses}'.format(
      wins=self.standing['wins'], losses=self.standing['losses'])
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

    self._display_image(image, 5, matrix, debug_label)


class ScreenSaver(Display):

  def show(self, matrix, debug_label):
    self._display_image(get_nba_logo(), 10, matrix, debug_label)
