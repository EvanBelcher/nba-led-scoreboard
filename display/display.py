from datetime import date, datetime, timedelta, timezone
from dateutil import parser
import pytz
import threading
import time

class DataCache(object):
  def __init__(self):
    self._data = dict()

  # Starts subscription on newly spawned thread
  def startSubscribeThread(self, varName, updateFunc, activeFunc, frequency, transformFunc=None, consumeFunc=None, startValue=None):
    self[varName] = startValue
    thread = threading.Thread(name='Thread-%s'%varName, target=self._subscribeToValue, args=(varName, updateFunc, activeFunc, frequency), kwargs={'transformFunc': transformFunc, 'consumeFunc': consumeFunc})
    thread.start()
  
  # Subscribes on the current thread
  def _subscribeToValue(self, varName, updateFunc, activeFunc, frequency, transformFunc=None, consumeFunc=None):
    while activeFunc():
      self.updateValue(varName, updateFunc, transformFunc=transformFunc, consumeFunc=consumeFunc)
      time.sleep(frequency.total_seconds())

  def updateValue(self, varName, updateFunc, transformFunc=None, consumeFunc=None):
    self[varName] = transformFunc(updateFunc()) if transformFunc else updateFunc()
    if consumeFunc:
      consumeFunc(self[varName])

  def __getitem__(self, key):
    return self._data[key]
  
  def __setitem__(self, key, value):
    self._data[key] = value

class DisplayManager(object):
  _SECONDS_IN_DAY = 86400

  def __init__(self):
    self.dataCache = DataCache()
    self.scheduledActions = []
    self.startTime, self.stopTime = None, None
    self.startDay, self.stopDay = None, None
    self.timeZone = timezone.utc
    self.rgbMatrix = self.createRgbMatrix()

  def start(self):
    while True:
      self._sleepIfNecessary()
      self._runScheduledActions()
      for display, displayTime in self.getDisplaysToShow():
        display.show()
        time.sleep(displayTime)

  def createRgbMatrix(self):
    raise NotImplementedError("createRgbMatrix must be implemented by the subclass")

  def getDisplaysToShow():
    raise NotImplementedError("getDisplaysToShow must be implemented by the subclass")

  def _sleepIfNecessary(self):
    if self.startDay and self.stopDay:
      currentDay = datetime.now(self.timeZone).isoweekday()

      # Weird checks
      checks =  [self.startDay > self.stopDay, currentDay >= self.startDay, currentDay < self.stopDay]
      if len(filter(lambda x: x)) < 2:
        daysToSleep = self.startDay - currentDay
        if daysToSleep < 0:
          daysToSleep += 7
        time.sleep(timedelta(days=daysToSleep).total_seconds() + 30)
        self._sleepIfNecessary()

    if self.startTime and self.stopTime:
      now = datetime.now(self.timeZone)
      currentTime = now.time()
      todayDate = now.date()

      # Weird checks
      checks =  [self.startTime > self.stopTime, currentTime >= self.startTime, currentTime < self.stopTime]
      if len(filter(lambda x: x)) < 2:
        secondsToSleep = (datetime.combine(todayDate, self.startTime) - datetime.combine(todayDate, currentTime)).total_seconds()
        if secondsToSleep < 0:
          secondsToSleep += self._SECONDS_IN_DAY
        time.sleep(secondsToSleep + 30)
        self._sleepIfNecessary()
  
  def _runScheduledActions(self):
    newActionList = list()
    for actionDateTime, actionFunc in self.scheduledActions:
      if datetime.now() > actionDateTime:
        actionFunc()
      else:
        newActionList.append((actionDateTime, actionFunc))
    self.scheduledActions = newActionList

  def setStartAndStopTimes(self, startTime, stopTime, timeZone = None):
    if startTime == stopTime:
      raise Exception('Start and stop times must be different')

    self.startTime = startTime
    self.stopTime = stopTime
    if timeZone:
      self.timeZone = timeZone

  # Where Monday is 1 and Sunday is 7
  def setStartAndStopDays(self, startDay, stopDay, timeZone = None):
    if startDay == stopDay:
      raise Exception('Start and stop days must be different')
    self.startDay = startDay
    self.stopDay = stopDay
    if timeZone:
      self.timeZone = timeZone
  
  def scheduleAction(self, actionDateTime, actionFunc):
    self.scheduledActions.append((actionDateTime, actionFunc))

class Display(object):
  def __init__(self, width, height):
    self.width = width
    self.height = height
  
  def show(self, matrix):
    raise NotImplementedError("Subclasses must implement show()")

class Animation(Display):
  def __init__(self, width, height, framerate=30):
    super().__init__(width, height)
    self.framerate = framerate
    self.frames = list()
  
  def show(self, matrix):
    if len(self.frames) == 0:
      raise NotImplementedError("Sublclasses must define at least one frame")
    for frameFunc in self.frames:
      frameFunc()
      time.sleep(1/self.framerate)

  def addFrame(self, frameFunc):
    self.frames.append(frameFunc)

  def addFrames(self, frameFuncs):
    self.frames.extend(frameFuncs)

class NBADisplayManager(DisplayManager):
  def __init__(self, favorite_teams):
    super().__init__()
    self.dataCache.startSubscribeThread("gamesToday", get_games_for_today, lambda: not should_sleep(), timedelta(minutes=5), startValue=[])
    self.favorite_teams = favorite_teams

  def createRgbMatrix(self):
    pass
  
  def getDisplaysToShow(self):
    board = scoreboard.ScoreBoard()
    games = board.games.get_dict()
    for game in self._getImportantGames(games):
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

  def _getImportantGames(self, games):
    # print(self.favorite_teams)
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

dm = NBADisplayManager(FAVORITE_TEAMS)
board = scoreboard.ScoreBoard()
games = board.games.get_dict()
print(games)
print('\n')
print(dm._getImportantGames(games))

class BeforeGame(Display):
  def __init__(self, game):
    super().__init__()
    self.game = game

  def show(self, matrix):
    pass

class AfterGame(Display):
  def __init__(self, game):
    super().__init__()
    self.game = game

  def show(self, matrix):
    pass

class LiveGame(Display):
  def __init__(self, game):
    super().__init__()
    self.game = game

  def show(self, matrix):
    pass

class Standings(Display):
  def __init__(self, standing):
    super().__init__()
    self.standing = standing

  def show(self, matrix):
    pass
