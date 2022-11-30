from data.nba_data import *
from display.nba_display import AfterGame, BeforeGame, LiveGame, NBADisplayManager, ScreenSaver, Standings
import logging

MAIN_LOG_LEVEL = logging.DEBUG  # DEBUG, INFO, WARNING, ERROR, CRITICAL


def main():
  logging.basicConfig()
  logging.getLogger().setLevel(MAIN_LOG_LEVEL)

  show_display()
  # test_display()


def show_display():
  dm = NBADisplayManager(FAVORITE_TEAMS)
  dm.start()


def test_display():
  game = get_game_by_id('0022000196')
  pbp = get_playbyplay_for_game(game)
  standings = get_standings()

  dm = NBADisplayManager(FAVORITE_TEAM_NAMES)

  before = BeforeGame(game)
  after = AfterGame(game)
  live = LiveGame(game)
  live_important = LiveGame(game, pbp[:len(pbp) // 2], dm)
  standing = Standings(standings[5])
  screensaver = ScreenSaver()

  for display in [before, after, live, live_important, standing, screensaver]:
    display.show(dm.rgb_matrix, dm.debug_label)


class Matrix(object):

  def __init__(self):
    self.width = 64
    self.height = 32


if __name__ == '__main__':
  main()
