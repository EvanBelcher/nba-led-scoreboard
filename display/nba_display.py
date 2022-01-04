from datetime import timedelta
from display import Display, DisplayManager 
from dateutil import parser
from data.nba_data import *
from PIL import Image, ImageColor, ImageDraw, ImageFont, ImageShow

class NBADisplayManager(DisplayManager):
  def __init__(self, favorite_teams):
    super().__init__()
    self.dataCache.startSubscribeThread("gamesToday", self._fetchGames, lambda: True, timedelta(minutes=5), startValue=[])
    self.dataCache.startSubscribeThread("importantGamesToday", self._scheduleLiveUpdatesForImportantGames, lambda: True, timedelta(days=1))
    self.favorite_teams = favorite_teams

  def createRgbMatrix(self):
    pass
  
  def getDisplaysToShow(self):
    for game in self._getImportantGames(self.dataCache['gamesToday']):
      if game_is_live(game):
        return [LiveGame(game)]
    return list(self._getIdleDisplays(self, games))

  def _getIdleDisplays(self, games):
    for game in games:
      if not game_has_started(game):
        yield BeforeGame(game)
      elif game_has_ended(game):
        yield AfterGame(game)
      else:
        yield LiveGame(game)
    for standing in get_standings():
      yield Standings(standing)

  def _fetchGames(self):
    self._sleepIfNecessary()
    return get_games_for_today()

  def _scheduleLiveUpdatesForImportantGames(self):
    self._sleepIfNecessary()
    games = get_games_for_today()
    for game in self._getImportantGames(games):
      self.scheduledActions.append((get_game_datetime(game), self._doLiveUpdates, game))

  def _doLiveUpdates(self, game):
    self.dataCache.startSubscribeThread('importantGame %s' % game['gameId'], self._fetchGames, lambda: not game_has_ended(game), timedelta(seconds=15))

  def _getImportantGames(self, games):
    importantGames = []
    for game in games:
      teamImportances = [self._getTeamImportance(team) for team in self._getTeams(game)]
      # print(teamImportances)
      if any(teamImportances):
        minImportance = min(filter(lambda i: i is not None, teamImportances))
        importantGames.append( {'importance': minImportance, 'game': game})
    
    importantGames.sort(key = lambda entry: parser.parse(entry['game']['gameTimeUTC']))
    importantGames.sort(key = lambda entry: entry['importance'])
    return list(map(lambda entry: entry['game'], importantGames))


  def _getTeamImportance(self, team):
    if team not in self.favorite_teams:
      return None
    return self.favorite_teams.index(team) + 1

  def _getTeams(self, game):
    awayTeam = teams.find_team_by_abbreviation(game['awayTeam']['teamTricode'])
    homeTeam = teams.find_team_by_abbreviation(game['homeTeam']['teamTricode'])
    return [awayTeam, homeTeam]

# dm = NBADisplayManager(FAVORITE_TEAMS)
# board = scoreboard.ScoreBoard()
# games = board.games.get_dict()
# print(games)
# print('\n')
# print(dm._getImportantGames())

class BeforeGame(Display):
  def __init__(self, game):
    super().__init__()
    self.game = game

  def show(self, matrix):
    image = Image.new("RGB", (matrix.width, matrix.height))
    draw = ImageDraw.Draw(image)
    draw.text(10, 10, 'hello world', fill=ImageColor.getrgb('#f00'), font=ImageFont.FreeTypeFont())
    # matrix.setImage(image, 0, 0)
    ImageShow.show(image)

    time.sleep(10)

class AfterGame(Display):
  def __init__(self, game):
    super().__init__()
    self.game = game

  def show(self, matrix):
    time.sleep(10)

class LiveGame(Display):
  def __init__(self, game):
    super().__init__()
    self.game = game

  def show(self, matrix):
    time.sleep(10)

class Standings(Display):
  def __init__(self, standing):
    super().__init__()
    self.standing = standing

  def show(self, matrix):
    time.sleep(7)

b = BeforeGame(None)
class Matrix(object):
  def __init__(self):
    self.width = 64
    self.height = 32
b.show(Matrix())