from display.nba_display import BeforeGame
import logging

MAIN_LOG_LEVEL = logging.DEBUG #DEBUG, INFO, WARNING, ERROR, CRITICAL

def main():
  logging.basicConfig()
  logging.getLogger().setLevel(MAIN_LOG_LEVEL)
	
  b = BeforeGame(None)
  b.show(Matrix())

class Matrix(object):
  def __init__(self):
    self.width = 64
    self.height = 32

if __name__ == '__main__':
	main()
