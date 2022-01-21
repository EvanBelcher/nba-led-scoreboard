from collections.abc import Collection, Mapping, Hashable
from datetime import datetime, timedelta, timezone
from dateutil import parser
from functools import lru_cache, wraps
from nba_api.live.nba.endpoints import boxscore, playbyplay, scoreboard
from nba_api.stats.endpoints.leaguestandings import LeagueStandings
from nba_api.stats.static import teams
from PIL import Image
from ratelimiter import RateLimiter
import config
import logging
import os
import pytz
import re
import requests
import time

FAVORITE_TEAMS = [
  find_team(team) for team in config.FAVORITE_TEAMS if team is not None
]
FAVORITE_TEAM_NAMES = [team['nickname'] for team in FAVORITE_TEAMS]
SLEEP_TIME = config.SLEEP_TIME or None
WAKE_TIME = config.WAKE_TIME or None
SLEEP_DAY = config.SLEEP_DAY or None
WAKE_DAY = config.WAKE_DAY or None
TIMEZONE = config.TIMEZONE if config.TIMEZONE in pytz.all_timezones else 'UTC'
os.environ['TZ'] = TIMEZONE
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
  return parser.parse(game["gameTimeUTC"]).replace(
    tzinfo=timezone.utc).astimezone(tz=pytz.timezone(TIMEZONE))


def game_has_started(game):
  return datetime.now(tz=pytz.timezone(TIMEZONE)) < get_game_datetime(game)


def game_is_live(game):
  return game_has_started(game) and not game_has_ended(game)


def get_logo_url(team_id):
  team = teams.find_team_name_by_id(team_id)
  return ('http://i.cdn.turner.com/nba/nba/.element/img/1.0/teamsites/logos/'
          'teamlogos_500x500/%s.png' % team['abbreviation'].lower())


def get_nba_logo():
  bg_img = Image.new('RGB', (64, 32))
  with Image.open('assets/nba_logo.png') as logo_img:
    bg_img.paste(logo_img, box=(4, 0))
    return bg_img


def get_important_games(favorite_teams):
  important_games = []
  for game in get_games_for_today():
    team_importances = [
      _get_team_importance(team, favorite_teams)
      for team in get_teams_from_game(game)
    ]
    if any(team_importances):
      min_importance = min(filter(lambda i: i is not None, team_importances))
      important_games.append({'importance': min_importance, 'game': game})

  important_games.sort(
    key=lambda entry: parser.parse(entry['game']['gameTimeUTC']))
  important_games.sort(key=lambda entry: entry['importance'])
  return list(map(lambda entry: entry['game'], important_games))


def _get_team_importance(team, favorite_teams):
  if team not in favorite_teams:
    return None
  return favorite_teams.index(team) + 1


def get_teams_from_game(game):
  away_team = teams.find_team_by_abbreviation(game['awayTeam']['teamTricode'])
  home_team = teams.find_team_by_abbreviation(game['homeTeam']['teamTricode'])
  return [away_team, home_team]


def get_score_from_game(game):
  away_score = game['awayTeam']['score']
  home_score = game['homeTeam']['score']
  return [away_score, home_score]


def get_game_clock(clock_text):
  match = re.match(r'PT(\d{2})M(\d{2}).+', clock_text)
  mins, secs = match.group(1), match.group(2)
  return '{mins}:{secs}'.format(mins=int(mins), secs=secs)


# Functions that make url requests


@lru_cache(maxsize=50)
@RateLimiter(max_calls=1, period=5)
def _get_game_by_id(game_id, ttl_hash):
  box = boxscore.BoxScore(str(game_id))
  return box.game.get_dict()


def get_game_by_id(game_id,
                   cache_time=timedelta(minutes=10),
                   cache_override=False):
  if cache_override:
    return _get_game_by_id(game_id, -time.time())
  return _get_game_by_id(game_id, time.time() // cache_time.total_seconds())


@lru_cache(maxsize=30)
@RateLimiter(max_calls=1, period=5)
def _game_has_ended(game_id, ttl_hash):
  game = get_game_by_id(game_id)
  if datetime.now(tz=pytz.timezone(
      TIMEZONE)) > get_game_datetime(game) + timedelta(hours=4):
    # Game started 4 hours ago. It must be over.
    return True
  if any(action['actionType'] == 'game'
         for action in get_playbyplay_for_game(game)['game']['actions']):
    # Game has ended
    return True
  return False


def game_has_ended(game,
                   cache_time=timedelta(minutes=10),
                   cache_override=False):
  if cache_override:
    return _game_has_ended(game['gameId'], -time.time())
  return _game_has_ended(game['gameId'],
                         time.time() // cache_time.total_seconds())


@lru_cache(maxsize=1)
@RateLimiter(max_calls=1, period=5)
def _get_games_for_today(ttl_hash):
  games = scoreboard.ScoreBoard().games.get_dict()

  game_format = (
    '{gameId}: {awayTeam} vs. {homeTeam} @ {gameTimeLTZ}.'
    ' {time} in Quarter {quarter}. Score: {awayTeamScore}-{homeTeamScore}')
  for game in games:
    logging.debug(
      game_format.format(
        gameId=game['gameId'],
        awayTeam=game['awayTeam']['teamName'],
        homeTeam=game['homeTeam']['teamName'],
        gameTimeLTZ=get_game_datetime(game),
        time=game['gameClock'],
        quarter=game['period'],
        awayTeamScore=game['awayTeam']['score'],
        homeTeamScore=game['homeTeam']['score']))

  return games


def get_games_for_today(cache_time=timedelta(minutes=10), cache_override=False):
  if cache_override:
    return _get_games_for_today(-time.time())
  return _get_games_for_today(time.time() // cache_time.total_seconds())


@lru_cache(maxsize=10)
@RateLimiter(max_calls=1, period=5)
def _get_playbyplay_for_game(game_id, ttl_hash):
  game = get_game_by_id(game_id)
  return playbyplay.PlayByPlay(game['gameId']).get_dict()['game']['actions']


def get_playbyplay_for_game(game,
                            cache_time=timedelta(seconds=5),
                            cache_override=False):
  if cache_override:
    return _get_playbyplay_for_game(game['gameId'], -time.time())
  return _get_playbyplay_for_game(game['gameId'],
                                  time.time() // cache_time.total_seconds())


@lru_cache(maxsize=1)
@RateLimiter(max_calls=1, period=5)
def _get_standings(ttl_hash):
  response = LeagueStandings()

  standings = list()
  for team in response.standings.get_dict()['data']:
    standings.append({
      'team': teams.find_team_name_by_id(team[2]),
      'wins': team[12],
      'losses': team[13],
      'winPercent': team[14]
    })

  standings.sort(
    key=lambda standing: standing['wins'], reverse=True)  # Descending by wins
  standings.sort(
    key=lambda standing: standing['winPercent'],
    reverse=True)  # Descending by win %

  rankedStandings = list()
  for i in range(len(standings)):
    standing = standings[i]
    standing['rank'] = i + 1
    rankedStandings.append(standing)

  return rankedStandings


def get_standings(cache_time=timedelta(minutes=10), cache_override=False):
  if cache_override:
    return _get_standings(-time.time())
  return _get_standings(time.time() // cache_time.total_seconds())


@lru_cache(maxsize=30)
@RateLimiter(max_calls=5, period=10)
def _get_team_logo(team_id, ttl_hash, width=32, height=32):
  url = get_logo_url(team_id)
  image_response = requests.get(
    url, stream=True)  # stream is required for response.raw
  img = Image.open(image_response.raw)
  img = img.crop(img.getbbox())
  img.thumbnail(
    (width, height), resample=Image.HAMMING
  )  # lanczos > hamming per documentation, but eye test says otherwise
  if img.width == width and img.height == height:
    return img
  
  h_offset = (width - img.width) // 2
  v_offset = (height - img.height) // 2  
  bg_img = Image.new("RGB", (width, height))
  bg_img.paste(img, (h_offset, v_offset))

  return bg_img


def get_team_logo(team_id,
                  width=32,
                  height=32,
                  cache_time=timedelta(days=30),
                  cache_override=False):
  if cache_override:
    return _get_team_logo(team_id, -time.time(), width=width, height=height)
  return _get_team_logo(
    team_id,
    time.time() // cache_time.total_seconds(),
    width=width,
    height=height)
