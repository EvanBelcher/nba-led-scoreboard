from logging import debug
from data.nba_data import *
from display.display import Display, DisplayManager
from PIL import Image, ImageColor, ImageDraw, ImageFont
from rgbmatrix import RGBMatrix, RGBMatrixOptions
import tkinter as tk


class ImagePlacement:

  def __init__(self, width, height):
    self.width = width
    self.height = height

  def h(self, placement):
    return round(self.width * placement)

  def v(self, placement):
    return round(self.height * placement)

  def get(self, h_placement, v_placement):
    return (self.h(h_placement), self.v(v_placement))

  def topleft(self):
    return (0, 0)

  def center(self):
    return (self.h(0.5), self.v(0.5))


FIVE_PX_FONT = ImageFont.truetype('assets/5px font.ttf', size=4)
SEVEN_PX_FONT = ImageFont.truetype('assets/7px font.ttf', size=12)
SEVEN_PX_FONT_BOLD = ImageFont.truetype('assets/7px font bold.ttf', size=12)


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
    return RGBMatrix(options=options)

  def create_debug_label(self):
    debug_tk = tk.Tk()
    debug_tk.title('Debug display')
    debug_tk.geometry('%dx%d' % (self.width * 10, self.height * 10))
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
    ip = ImagePlacement(matrix.width, matrix.height)
    draw = ImageDraw.Draw(image)

    # Team logos
    teams = get_teams_from_game(self.game)
    logos = [get_team_logo(team['id']) for team in teams]
    image.paste(logos[0], ip.get(-0.25, 0))
    image.paste(logos[1], ip.get(0.75, 0))

    game_time = get_game_datetime(self.game).strftime('%l:%M %p')
    display_text = '{team1_name}\nVS.\n{team2_name}\n{game_time}'.format(
      team1_name=teams[0]['abbreviation'],
      team2_name=teams[1]['abbreviation'],
      game_time=game_time)

    # Text
    #17,1 for normal anchor
    draw.text(
      ip.center(),
      display_text,
      fill=ImageColor.getrgb('#fff'),
      font=SEVEN_PX_FONT,
      anchor='mm',
      spacing=1,
      align='center')

    self._display_image(image, 10, matrix, debug_label)


class AfterGame(Display):

  def __init__(self, game):
    super().__init__()
    self.game = game

  def show(self, matrix, debug_label):
    image = Image.new("RGB", (matrix.width, matrix.height))
    ip = ImagePlacement(matrix.width, matrix.height)
    draw = ImageDraw.Draw(image)

    # Team logos
    teams = get_teams_from_game(self.game)
    logos = [get_team_logo(team['id']) for team in teams]
    image.paste(logos[0], ip.get(-0.25, 0))
    image.paste(logos[1], ip.get(0.75, 0))

    # Neutral text
    scores = get_score_from_game(self.game)
    score_text = '{scores[0]}-{scores[1]}'.format(scores=scores)
    draw.text(
      ip.center(),
      ' \nVS.\n \n{score}'.format(score=score_text),
      fill=ImageColor.getrgb('#fff'),
      font=SEVEN_PX_FONT,
      anchor='mm',
      spacing=1,
      align='center')

    # First team text
    first_team_won = scores[0] > scores[1]
    draw.text(
      ip.center(),
      '{team1_name}\n \n \n '.format(team1_name=teams[0]['abbreviation']),
      fill=ImageColor.getrgb('#070' if first_team_won else '#f00'),
      font=SEVEN_PX_FONT,
      anchor='mm',
      spacing=1,
      align='center')

    # Second team text
    draw.text(
      ip.center(),
      ' \n \n{team2_name}\n '.format(team2_name=teams[1]['abbreviation']),
      fill=ImageColor.getrgb('#f00' if first_team_won else '#070'),
      font=SEVEN_PX_FONT,
      anchor='mm',
      spacing=1,
      align='center')

    self._display_image(image, 10, matrix, debug_label)


class LiveGame(Display):

  def __init__(self, game, game_playbyplay=None):
    super().__init__()
    self.game = game
    self.game_playbyplay = game_playbyplay

  def show(self, matrix, debug_label):
    image = Image.new("RGB", (matrix.width, matrix.height))
    ip = ImagePlacement(matrix.width, matrix.height)
    draw = ImageDraw.Draw(image)

    teams = get_teams_from_game(self.game)
    team_1_name = teams[0]['abbreviation']
    team_2_name = teams[1]['abbreviation']

    if self.game_playbyplay:
      team_1_score = self.game_playbyplay[-1]['scoreAway']
      team_2_score = self.game_playbyplay[-1]['scoreHome']
      period = self.game_playbyplay[-1]['period']
      game_clock = get_game_clock(self.game_playbyplay[-1]['clock'])
    else:
      team_1_score, team_2_score = get_score_from_game(self.game)
      period = self.game['period']
      game_clock = get_game_clock(self.game['gameClock'])

    # Team text
    draw.text(
      ip.get(1 / 6, 0.5),
      '{team_1_name}\n{team_1_score}'.format(
        team_1_name=team_1_name, team_1_score=team_1_score),
      fill=ImageColor.getrgb('#fff'),
      font=SEVEN_PX_FONT_BOLD,
      anchor='mm',
      spacing=8,
      align='center')
    draw.text(
      ip.get(5 / 6, 0.5),
      '{team_2_name}\n{team_2_score}'.format(
        team_2_name=team_2_name, team_2_score=team_2_score),
      fill=ImageColor.getrgb('#fff'),
      font=SEVEN_PX_FONT_BOLD,
      anchor='mm',
      spacing=8,
      align='center')

    # Game text
    draw.text(
      ip.center(),
      'LIVE\n \n ',
      fill=ImageColor.getrgb('#f00'),
      font=FIVE_PX_FONT,
      anchor='mm',
      spacing=6,
      align='center')
    draw.text(
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
    image = Image.new("RGB", (matrix.width, matrix.height))
    ip = ImagePlacement(matrix.width, matrix.height)
    draw = ImageDraw.Draw(image)

    # Team logos
    team = self.standing['team']
    logo = get_team_logo(team['id'])
    image.paste(logo, ip.topleft())

    # Text
    rank = self.standing['rank']
    record = '{wins}-{losses}'.format(
      wins=self.standing['wins'], losses=self.standing['losses'])
    display_text = '{team}\n#{rank}\n{record}'.format(
      team=team['abbreviation'], rank=rank, record=record)
    draw.text(
      ip.get(0.5, 0),
      display_text,
      fill=ImageColor.getrgb('#fff'),
      font=SEVEN_PX_FONT_BOLD,
      anchor='mm',
      spacing=3,
      align='center')

    self._display_image(image, 5, matrix, debug_label)


class ScreenSaver(Display):

  def show(self, matrix, debug_label):
    self._display_image(get_nba_logo(), 10, matrix, debug_label)
