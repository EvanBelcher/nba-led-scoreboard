from data.nba_data import *
from display.nba_display import AfterGame, BeforeGame, LiveGame, ScreenSaver, Standings
import logging
import tkinter as tk

MAIN_LOG_LEVEL = logging.DEBUG  # DEBUG, INFO, WARNING, ERROR, CRITICAL


def main():
  logging.basicConfig()
  logging.getLogger().setLevel(MAIN_LOG_LEVEL)

  game = get_game_by_id('0022000196')
  pbp = get_playbyplay_for_game(game)
  standings = get_standings()

  before = BeforeGame(game)
  after = AfterGame(game)
  live = LiveGame(game)
  live_important = LiveGame(game, pbp[:len(pbp) // 2])
  standing = Standings(standings[5])
  screensaver = ScreenSaver()

  debug_tk = tk.Tk()
  debug_tk.title('Debug display')
  debug_tk.geometry('640x320')
  label = tk.Label(debug_tk)

  for display in [before, after, live, live_important, standing, screensaver]:
    display.show(Matrix(), label)


class Matrix(object):

  def __init__(self):
    self.width = 64
    self.height = 32


if __name__ == '__main__':
  main()
