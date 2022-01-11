from display.nba_display import BeforeGame
import logging
import tkinter as tk

MAIN_LOG_LEVEL = logging.DEBUG #DEBUG, INFO, WARNING, ERROR, CRITICAL

def main():
  logging.basicConfig()
  logging.getLogger().setLevel(MAIN_LOG_LEVEL)
	
  b = BeforeGame(None)
  
  debug_tk = tk.Tk()
  debug_tk.title('Debug display')
  debug_tk.geometry('640x320')
  label = tk.Label(debug_tk)
  b.show(Matrix(), label)

class Matrix(object):
  def __init__(self):
    self.width = 64
    self.height = 32

if __name__ == '__main__':
	main()
