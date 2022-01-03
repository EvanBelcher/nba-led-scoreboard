# Imports
from datetime import date, datetime, timedelta, timezone
from dateutil import parser
from nba_api.live.nba.endpoints import boxscore, playbyplay, scoreboard
from nba_api.stats.static import teams
from nba_api.stats.library.parameters import GameDate
import pytz
from nba_api.stats.endpoints.leaguestandings import LeagueStandings
from IPython.display import Image

NBA_TEAMS = teams.get_teams()

# Constants
# TODO: Load from config file instead
FAVORITE_TEAMS = ['IND', 'Bucks', 'Clippers', 'Bulls', 'Jazz','Hawks']
TIMEZONE = 'US/Eastern'
SLEEP_TIME = '1:00'
WAKE_TIME = '9:00'
# Where Monday is 1 and Sunday is 7
SLEEP_DAY = ''
WAKE_DAY = ''

# Utility
def find_team(keyword):
  print(keyword)
  if teams.find_team_by_abbreviation(keyword):
    return teams.find_team_by_abbreviation(keyword)
  if teams.find_teams_by_full_name(keyword):
    return teams.find_teams_by_full_name(keyword)[0]
  if teams.find_teams_by_nickname(keyword):
    return teams.find_teams_by_nickname(keyword)[0]
  if teams.find_teams_by_city(keyword):
    return teams.find_teams_by_city(keyword)[0]
  if teams.find_teams_by_state(keyword):
    return teams.find_teams_by_state(keyword)[0]
  return None

FAVORITE_TEAMS = [find_team(team) for team in FAVORITE_TEAMS if team is not None]
FAVORITE_TEAM_NAMES = [team['nickname'] for team in FAVORITE_TEAMS]
SLEEP_TIME = SLEEP_TIME or None
WAKE_TIME = WAKE_TIME or None
SLEEP_DAY = SLEEP_DAY or None
WAKE_DAY = WAKE_DAY or None

def get_game_datetime(game):
  return parser.parse(game["gameTimeUTC"]).replace(tzinfo=timezone.utc).astimezone(tz=pytz.timezone(TIMEZONE))

def game_has_started(game):
  return datetime.now(tz=pytz.timezone(TIMEZONE)) < get_game_datetime(game)

def game_has_ended(game):
  if datetime.now(tz=pytz.timezone(TIMEZONE)) > get_game_datetime(game) + timedelta(hours=4):
    # Game started 4 hours ago. It must be over.
    return True
  pbp = playbyplay.PlayByPlay(game['gameId'])
  if any(action['actionType']=='game' for action in pbp.get_dict()['game']['actions']):
    # Game has ended
    return True
  return False

def game_is_live(game):
  return game_has_started(game) and not game_has_ended(game)

def should_sleep():
  pass

def get_games_for_today():
  return scoreboard.ScoreBoard().games.get_dict()

# Get games for today
import os, time
os.environ['TZ'] = 'US/Eastern'



f = "{gameId}: {awayTeam} vs. {homeTeam} @ {gameTimeLTZ}. {time} in Quarter {quarter}. Score: {awayTeamScore}-{homeTeamScore}"
board = scoreboard.ScoreBoard()
print(board.get_dict())
print("ScoreBoardDate: " + board.score_board_date)
games = board.games.get_dict()
print(games)
for game in games:
  gameTimeLTZ = parser.parse(game["gameTimeUTC"]).replace(tzinfo=timezone.utc).astimezone(tz=pytz.timezone('US/Eastern'))
  print(f.format(gameId=game['gameId'], awayTeam=game['awayTeam']['teamName'], homeTeam=game['homeTeam']['teamName'], gameTimeLTZ=gameTimeLTZ, time=game['gameClock'], quarter=game['period'], awayTeamScore=game['awayTeam']['score'], homeTeamScore=game['homeTeam']['score']))

def get_standings():
  response = LeagueStandings()

  standings = list()
  for team in response.standings.get_dict()['data']:
    standings.append({'teamId': team[2], 'teamName': team[3] + ' ' + team[4], 'wins': team[12], 'losses': team[13], 'winPercent': team[14]})
  
  standings.sort(key = lambda standing: standing['wins'], reverse=True) # Descending by wins
  standings.sort(key = lambda standing: standing['winPercent'], reverse=True) # Descending by win %

  rankedStandings = list()
  for i in range(len(standings)):
    standing = standings[i]
    standing['rank'] = i+1
    rankedStandings.append(standing)

  return rankedStandings

print(get_standings())

def get_logo_url(team_id):
  team = teams.find_team_name_by_id(team_id)
  return 'http://i.cdn.turner.com/nba/nba/.element/img/1.0/teamsites/logos/teamlogos_500x500/%s.png' % team['abbreviation'].lower()

get_logo_url(1610612741)