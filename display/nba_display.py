from data.nba_data import *
from datetime import timedelta
from dateutil import parser
from display.display import Display, DisplayManager 
from PIL import Image, ImageColor, ImageDraw, ImageFont, ImageShow
from rgbmatrix import RGBMatrix, RGBMatrixOptions

class NBADisplayManager(DisplayManager):
  def __init__(self, favorite_teams):
    super().__init__()
    self.data_cache.start_subscribe_thread("gamesToday", self._fetch_games, lambda: True, timedelta(minutes=5), start_value=[])
    self.data_cache.start_subscribe_thread("important_gamesToday", self._schedule_live_updates_for_important_games, lambda: True, timedelta(days=1))
    self.favorite_teams = favorite_teams

  def create_rgb_matrix(self):
    options = RGBMatrixOptions()
    options.rows = 32
    options.cols = 64
    options.hardware_mapping = 'adafruit-hat'
    return RGBMatrix(options = options)
  
  def get_displays_to_show(self):
    for game in self._get_important_games(self.data_cache['gamesToday']):
      if game_is_live(game):
        return [LiveGame(game, True)]
    return list(self._get_idle_displays(self, self.data_cache['gamesToday']))

  def _get_idle_displays(self, games):
    yield ScreenSaver()
    for game in games:
      if not game_has_started(game):
        yield BeforeGame(game)
      elif game_has_ended(game):
        yield AfterGame(game)
      else:
        yield LiveGame(game, False)
    for standing in get_standings():
      yield Standings(standing)

  def _fetch_games(self):
    self._sleep_if_necessary()
    return get_games_for_today()

  def _schedule_live_updates_for_important_games(self):
    self._sleep_if_necessary()
    games = get_games_for_today()
    for game in self._get_important_games(games):
      self.scheduled_actions.append((get_game_datetime(game), self._do_live_updates, game))

  def _do_live_updates(self, game):
    self.data_cache.start_subscribe_thread('importantGame %s' % game['gameId'], self._fetch_games, lambda: not game_has_ended(game), timedelta(seconds=15))

  def _get_important_games(self, games):
    important_games = []
    for game in games:
      team_importances = [self._get_team_importance(team) for team in self._get_teams(game)]
      if any(team_importances):
        min_importance = min(filter(lambda i: i is not None, team_importances))
        important_games.append( {'importance': min_importance, 'game': game})
    
    important_games.sort(key = lambda entry: parser.parse(entry['game']['gameTimeUTC']))
    important_games.sort(key = lambda entry: entry['importance'])
    return list(map(lambda entry: entry['game'], important_games))


  def _get_team_importance(self, team):
    if team not in self.favorite_teams:
      return None
    return self.favorite_teams.index(team) + 1

  def _get_teams(self, game):
    away_team = teams.find_team_by_abbreviation(game['awayTeam']['teamTricode'])
    home_team = teams.find_team_by_abbreviation(game['homeTeam']['teamTricode'])
    return [away_team, home_team]

class BeforeGame(Display):
  def __init__(self, game):
    super().__init__()
    self.game = game

  def show(self, matrix):
    image = Image.new("RGB", (matrix.width, matrix.height))
    draw = ImageDraw.Draw(image)
    draw.text((1, 1), 'hello\nworld', fill=ImageColor.getrgb('#f00'))
    self._debug_image(image)

    time.sleep(10)

class AfterGame(Display):
  def __init__(self, game):
    super().__init__()
    self.game = game

  def show(self, matrix):
    pass

class LiveGame(Display):
  def __init__(self, game, gameIsImportant):
    super().__init__()
    self.game = game
    self.gameIsImportant = gameIsImportant

  def show(self, matrix):
    pass

class Standings(Display):
  def __init__(self, standing):
    super().__init__()
    self.standing = standing

  def show(self, matrix):
    pass

class ScreenSaver(Display):
  def __init(self):
    super().__init__()
  
  def show(self, matrix):
    pass