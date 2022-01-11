from datetime import datetime, timedelta, timezone
from dateutil import parser
from nba_api.live.nba.endpoints import playbyplay, scoreboard
from nba_api.stats.endpoints.leaguestandings import LeagueStandings
from nba_api.stats.static import teams
from ratelimiter import RateLimiter
import logging
import os
import pytz
import time
import config

FAVORITE_TEAMS = [find_team(team) for team in config.FAVORITE_TEAMS if team is not None]
FAVORITE_TEAM_NAMES = [team['nickname'] for team in FAVORITE_TEAMS]
SLEEP_TIME = config.SLEEP_TIME or None
WAKE_TIME = config.WAKE_TIME or None
SLEEP_DAY = config.SLEEP_DAY or None
WAKE_DAY = config.WAKE_DAY or None
os.environ['TZ'] = config.TIMEZONE if config.TIMEZONE in pytz.all_timezones else 'UTC'
time.tzset()

def find_team(keyword):
  if not keyword:
    return None

  if teams.find_team_by_abbreviation(keyword.upper()):
    return teams.find_team_by_abbreviation(keyword.upper())
  if teams.find_teams_by_full_name(keyword):
    return teams.find_teams_by_full_name(keyword)[0]
  if teams.find_teams_by_nickname(keyword):
    return teams.find_teams_by_nickname(keyword)[0]
  if teams.find_teams_by_city(keyword):
    return teams.find_teams_by_city(keyword)[0]
  if teams.find_teams_by_state(keyword):
    return teams.find_teams_by_state(keyword)[0]

  return None

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

@RateLimiter(max_calls=1, period=5)
def get_games_for_today():
  games = scoreboard.ScoreBoard().games.get_dict()
  
  game_format = '{gameId}: {awayTeam} vs. {homeTeam} @ {gameTimeLTZ}. {time} in Quarter {quarter}. Score: {awayTeamScore}-{homeTeamScore}'
  for game in games:
    logging.debug(game_format.format(gameId=game['gameId'], awayTeam=game['awayTeam']['teamName'], homeTeam=game['homeTeam']['teamName'], gameTimeLTZ=get_game_datetime(game), time=game['gameClock'], quarter=game['period'], awayTeamScore=game['awayTeam']['score'], homeTeamScore=game['homeTeam']['score']))
  
  return games
  
@RateLimiter(max_calls=1, period=5)
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

def get_logo_url(team_id):
  team = teams.find_team_name_by_id(team_id)
  return 'http://i.cdn.turner.com/nba/nba/.element/img/1.0/teamsites/logos/teamlogos_500x500/%s.png' % team['abbreviation'].lower()
