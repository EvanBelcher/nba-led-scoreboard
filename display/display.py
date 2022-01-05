from datetime import datetime, timedelta, timezone
import threading
import time
from PIL import Image

class DataCache(object):
  def __init__(self):
    self._data = dict()

  # Starts subscription on newly spawned thread
  def startSubscribeThread(self, varName, updateFunc, activeFunc, frequency, transformFunc=None, consumeFunc=None, startValue=None):
    if startValue or not varName in self._data:
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
        display.show(self.rgbMatrix)
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
  
  def _runScheduledActions(self, *args):
    newActionList = list()
    for actionDateTime, actionFunc, *args in self.scheduledActions:
      if datetime.now() > actionDateTime:
        actionFunc(*args)
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
  def __init__(self):
    pass
  
  def show(self, matrix):
    raise NotImplementedError("Subclasses must implement show()")

  def _debugImage(self, image):
    bigImg = image.resize((image.width*10, image.height*10))
    bigImg.show()

class Animation(Display):
  def __init__(self, framerate=30):
    super().__init__()
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
