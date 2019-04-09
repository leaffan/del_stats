#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import json
import datetime
import argparse
from collections import defaultdict

import requests

from lxml import html

from dateutil.parser import parse
from dateutil.rrule import rrule, DAILY
from dateutil.relativedelta import relativedelta

from utils import get_team_from_game, get_season


BASE_URL = "https://www.del.org"
SCHEDULE_URL_SUFFIX = "spielplan"
GAME_DETAILS_SUFFIX = "live-ticker/matches/%d/game-header.json"
GAME_ROSTERS_SUFFIX = "live-ticker/matches/%d/roster.json"
GAME_EVENTS_SUFFIX = "live-ticker/matches/%d/period-events.json"

MATCH_ID_REGEX = re.compile(
    R"livetickerParams\.matchId\s+=\s+(\d+)")
POS_KEYS = {'1': 'G', '2': 'D', '3': 'F'}

TGT_FILE = "del_games.json"
TGT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')

PLAYOFF_DATES = {
    2018: datetime.date(2019, 3, 5)
}

EMERGENCY_MAPPING = {
    3656: 1402, 3659: 1403, 3662: 1404
}


def get_game_ticker_urls_rounds(date):
    """
    Retrieves game ticker urls and round information for all games played on
    specific date.
    """
    # preparing url to schedule page
    schedule_url = "/".join((BASE_URL, SCHEDULE_URL_SUFFIX, str(date)))
    r = requests.get(schedule_url)
    doc = html.fromstring(r.text)
    # collecting urls to game ticker pages
    ticker_urls = doc.xpath(
        "//div[@class='game post']/div/div[@class='link-icons']/a[1]/@href")
    # collecting round information
    rounds = doc.xpath("//span[@class='phase']/strong/text()")

    return ticker_urls, rounds


def get_games_for_date(date, existing_games=None):
    print("+ Retrieving games played on %s" % date)

    # loading games that may have been registered earlier
    if not existing_games:
        games = list()
    else:
        games = existing_games
    # collecting already registered game ids
    registered_game_ids = [g['game_id'] for g in games]

    # retrieving ticker urls and round information for current date
    ticker_urls, rounds = get_game_ticker_urls_rounds(date)

    for ticker_url, round in zip(ticker_urls, rounds):
        schedule_game_id, game_id = get_game_ids_via_ticker(ticker_url)

        if game_id is None:
            game_id = EMERGENCY_MAPPING[schedule_game_id]

        if game_id in registered_game_ids:
            print("Game with id %d already registered" % game_id)
            continue

        # setting up data container
        single_game_data = dict()
        # setting game date and round information
        single_game_data['date'] = date
        single_game_data['season'] = get_season(date)
        if date < PLAYOFF_DATES[single_game_data['season']]:
            single_game_data['season_type'] = 'RS'
        elif date >= PLAYOFF_DATES[single_game_data['season']]:
            single_game_data['season_type'] = 'PO'
        single_game_data['round'] = int(round.split()[-1])

        # setting game ids
        single_game_data['schedule_game_id'] = schedule_game_id
        single_game_data['game_id'] = game_id

        # retrieving game details
        if 'game_id' in single_game_data:
            try:
                single_game_details = get_single_game_details(
                    single_game_data['game_id'])
            except Exception:
                import traceback
                traceback.print_exc()
                print(game_id)
                continue

        # retrieving game rosters
        single_game_rosters = get_game_rosters(game_id)
        # retrieving game events
        single_game_events = get_game_events(game_id)

        single_game_data = {
            **single_game_data, **single_game_details,
            **single_game_rosters, **single_game_events
        }

        single_game_data['first_goal'] = get_team_from_game(
            single_game_data, single_game_data['first_goal'])
        single_game_data['gw_goal'] = get_team_from_game(
            single_game_data, single_game_data['gw_goal'])

        print("\t+ %s (%d) vs. %s (%d)" % (
            single_game_data['home_team'], single_game_data['home_score'],
            single_game_data['road_team'], single_game_data['road_score']
        ))
        games.append(single_game_data)

    return games


def get_game_ids_via_ticker(url):
    """
    Gets schedule and actual game ids for a given game using the ticker web
    page.
    """
    # retrieving schedule game id from url directly
    schedule_game_id = int(url.split("/")[-1])
    url = "".join((BASE_URL, url))
    r = requests.get(url)
    ticker_doc = html.fromstring(r.text)
    # retrieving first javascript element
    script_el = ticker_doc.xpath("//script[1]/text()")
    if script_el:
        script_raw = script_el.pop().replace("\n", "")
        match = re.search(MATCH_ID_REGEX, script_raw)
        if match:
            game_id = int(match.group(1))
            return schedule_game_id, game_id

    return schedule_game_id, None


def get_single_game_details(game_id):
    """
    Gets game details for a single game with the specified id.
    """
    # setting up url to json file with game details
    game_details_url = "/".join((BASE_URL, GAME_DETAILS_SUFFIX % game_id))

    r = requests.get(game_details_url)
    game_details = r.json()

    single_game_data = dict()

    single_game_data['arena'] = game_details['stadium']
    single_game_data['attendance'] = game_details['numberOfViewers']

    single_game_data['home_id'] = game_details['teamInfo']['home']['id']
    single_game_data['home_team'] = game_details['teamInfo']['home']['name']
    single_game_data['home_abbr'] = game_details[
        'teamInfo']['home']['shortcut']
    if game_details['trainers']:
        if 'homeHeadCoach' in game_details['trainers']:
            if type(game_details['trainers']['homeHeadCoach']) is str:
                single_game_data['home_coach'] = game_details[
                    'trainers']['homeHeadCoach']
            else:
                single_game_data['home_coach_id'] = game_details[
                    'trainers']['homeHeadCoach']['id']
                single_game_data['home_coach'] = game_details[
                    'trainers']['homeHeadCoach']['name']
    single_game_data['road_id'] = game_details['teamInfo']['visitor']['id']
    single_game_data['road_team'] = game_details['teamInfo']['visitor']['name']
    single_game_data['road_abbr'] = game_details[
        'teamInfo']['visitor']['shortcut']
    if game_details['trainers']:
        if 'visitorHeadCoach' in game_details['trainers']:
            if type(game_details['trainers']['visitorHeadCoach']) is str:
                single_game_data['road_coach'] = game_details[
                    'trainers']['visitorHeadCoach']
            else:
                single_game_data['road_coach_id'] = game_details[
                    'trainers']['visitorHeadCoach']['id']
                single_game_data['road_coach'] = game_details[
                    'trainers']['visitorHeadCoach']['name']

    single_game_data['home_score'] = game_details[
        'results']['score']['final']['score_home']
    single_game_data['road_score'] = game_details[
        'results']['score']['final']['score_guest']

    single_game_data['home_goals_1'] = game_details[
        'results']['score']['first_period']['score_home']
    single_game_data['road_goals_1'] = game_details[
        'results']['score']['first_period']['score_guest']
    single_game_data['home_goals_2'] = game_details[
        'results']['score']['second_period']['score_home']
    single_game_data['road_goals_2'] = game_details[
        'results']['score']['second_period']['score_guest']
    single_game_data['home_goals_3'] = game_details[
        'results']['score']['third_period']['score_home']
    single_game_data['road_goals_3'] = game_details[
        'results']['score']['third_period']['score_guest']

    single_game_data['overtime_game'] = False
    single_game_data['shootout_game'] = False

    if (sum([
        single_game_data['home_goals_1'],
        single_game_data['home_goals_2'],
        single_game_data['home_goals_3']
    ]) != single_game_data['home_score']) or (sum([
        single_game_data['road_goals_1'],
        single_game_data['road_goals_2'],
        single_game_data['road_goals_3']
    ]) != single_game_data['road_score']):
        if game_details['results']['extra_time']:
            single_game_data['overtime_game'] = True
        if game_details['results']['shooting']:
            single_game_data['shootout_game'] = True

    if type(game_details['referees']['headReferee1']) is str:
        single_game_data['referee_1'] = game_details[
            'referees']['headReferee1']
    else:
        single_game_data['referee_1_id'] = game_details[
            'referees']['headReferee1']['id']
        single_game_data['referee_1'] = game_details[
            'referees']['headReferee1']['name']
    if type(game_details['referees']['headReferee2']) is str:
        single_game_data['referee_2'] = game_details[
            'referees']['headReferee2']
    else:
        single_game_data['referee_2_id'] = game_details[
            'referees']['headReferee2']['id']
        single_game_data['referee_2'] = game_details[
            'referees']['headReferee2']['name']
    if type(game_details['referees']['lineReferee1']) is str:
        single_game_data['linesman_1'] = game_details[
            'referees']['lineReferee1']
    else:
        single_game_data['linesman_1_id'] = game_details[
            'referees']['lineReferee1']['id']
        single_game_data['linesman_1'] = game_details[
            'referees']['lineReferee1']['name']
    if type(game_details['referees']['lineReferee2']) is str:
        single_game_data['linesman_2'] = game_details[
            'referees']['lineReferee2']
    else:
        single_game_data['linesman_2_id'] = game_details[
            'referees']['lineReferee2']['id']
        single_game_data['linesman_2'] = game_details[
            'referees']['lineReferee2']['name']

    if 'bestPlayers' in game_details:
        single_game_data['home_best_player_id'] = game_details[
            'bestPlayers']['home']['id']
        single_game_data['home_best_player'] = game_details[
            'bestPlayers']['home']['name']
        single_game_data['road_best_player_id'] = game_details[
            'bestPlayers']['visitor']['id']
        single_game_data['road_best_player'] = game_details[
            'bestPlayers']['visitor']['name']

    return single_game_data


def get_game_events(game_id):
    """
    Register game events for current game from separate data source.
    """
    # setting up url to json file with game events
    game_events_url = "/".join((BASE_URL, GAME_EVENTS_SUFFIX % game_id))
    # retrieving game events
    r = requests.get(game_events_url)
    game_events = r.json()

    single_game_events = dict()

    # setting up containers for all goals
    all_goals = list()
    goals_per_team = {'home': list(), 'road': list()}
    empty_net_goals_per_team = {'home': 0, 'road': 0}
    extra_attacker_goals_per_team = {'home': 0, 'road': 0}

    # collecting all goals scored in the game
    for period in game_events:
        for event in game_events[period]:
            # retrieving team that scored the first goal of the game
            if event['type'] == 'goal':
                all_goals.append(event)
                home_road = event['data']['team'].replace('visitor', 'road')
                goals_per_team[home_road].append(event)

    # retrieving first goal of the game
    first_goal = all_goals[0]

    single_game_events['first_goal'] = first_goal[
        'data']['team'].replace('visitor', 'road')
    single_game_events['first_goal_time'] = first_goal['time']
    single_game_events['first_goal_player_id'] = first_goal[
        'data']['scorer']['playerId']
    single_game_events['first_goal_first_name'] = first_goal[
        'data']['scorer']['name']
    single_game_events['first_goal_last_name'] = first_goal[
        'data']['scorer']['surname']

    # retrieving game-winning goal
    if len(goals_per_team['home']) > len(goals_per_team['road']):
        winning_goal = goals_per_team['home'][len(goals_per_team['road'])]
    else:
        winning_goal = goals_per_team['road'][len(goals_per_team['home'])]

    single_game_events['gw_goal'] = winning_goal[
        'data']['team'].replace('visitor', 'road')
    single_game_events['gw_goal_time'] = winning_goal['time']
    single_game_events['gw_goal_player_id'] = winning_goal[
        'data']['scorer']['playerId']
    single_game_events['gw_goal_first_name'] = winning_goal[
        'data']['scorer']['name']
    single_game_events['gw_goal_last_name'] = winning_goal[
        'data']['scorer']['surname']

    # counting empty net and extra attacker goals per team
    for key in ['home', 'road']:
        for goal in goals_per_team[key]:
            if goal['data']['en']:
                empty_net_goals_per_team[key] += 1
            if goal['data']['ea']:
                # some empty net goals are also falsely registered as extra
                # attacker goals
                if goal['data']['en']:
                    continue
                # game-winning shootout goals are falsely registered as extra
                # attacker goals
                if goal['data']['balance'] == 'GWS':
                    continue
                extra_attacker_goals_per_team[key] += 1
        else:
            single_game_events[
                "%s_en_goals" % key] = empty_net_goals_per_team[key]
            single_game_events[
                "%s_ea_goals" % key] = extra_attacker_goals_per_team[key]

    return single_game_events


def get_game_rosters(game_id):
    """
    Retrieves rosters for all teams in game with the specified game id.
    """
    # setting up url to json file with game rosters
    game_rosters_url = "/".join((BASE_URL, GAME_ROSTERS_SUFFIX % game_id))
    # retrieving game rosters
    r = requests.get(game_rosters_url)
    game_rosters = r.json()

    roster_data = defaultdict(list)
    collected_tgt_keys = set()

    for home_road_key in ['home', 'visitor']:
        roster = game_rosters[home_road_key]
        for roster_key in sorted(roster.keys()):
            # splitting key into single string digits
            pos, line, clr = list(str(roster_key))
            # converting coded position into actual position
            pos = POS_KEYS[pos]
            # goaltender's starting status is coded in third, not second digit
            if pos == 'G':
                line = clr
            # setting up target key
            tgt_key = ("%s_%s%s" % (
                home_road_key.replace('visitor', 'road'), pos, line)).lower()
            collected_tgt_keys.add(tgt_key)
            # appending a dummy player id if necessary, e.g. for fourth
            # defensive pairs only consisting of a right defenseman
            if pos != 'G' and int(clr) > len(roster_data[tgt_key]) + 1:
                roster_data[tgt_key].append(0)
            roster_data[tgt_key].append(roster[roster_key]['playerId'])
        else:
            for tgt_key in collected_tgt_keys:
                if '_d' in tgt_key:
                    while len(roster_data[tgt_key]) < 2:
                        roster_data[tgt_key].append(0)
                if '_f' in tgt_key:
                    while len(roster_data[tgt_key]) < 3:
                        roster_data[tgt_key].append(0)

    return roster_data


if __name__ == '__main__':

    # retrieving arguments specified on command line
    parser = argparse.ArgumentParser(
        description='Download DEL game information.')
    parser.add_argument(
        '-f', '--from', dest='from_date', required=False,
        metavar='first date to download summaries for',
        help="The first date information will be downloaded for")
    parser.add_argument(
        '-t', '--to', dest='to_date', required=False,
        metavar='last date to download summaries for',
        help="The last date information will be downloaded for")
    parser.add_argument(
        '--initial', dest='initial', required=False,
        action='store_true', help='Re-create list of games')

    args = parser.parse_args()

    # setting time interval of interest from command line options
    from_date = args.from_date
    to_date = args.to_date
    initial = args.initial

    if from_date is None:
        # using yesterday's date as default from date
        from_date = datetime.date.today() - relativedelta(days=1)
    else:
        from_date = parse(from_date).date()

    if to_date is None:
        # using from date as default to date
        to_date = from_date
    else:
        to_date = parse(to_date).date()

    # setting up list of all game dates
    game_dates = list(rrule(DAILY, dtstart=from_date, until=to_date))

    # setting up target path
    tgt_path = os.path.join(TGT_DIR, TGT_FILE)

    if initial:
        games = list()
    else:
        games = json.loads(open(tgt_path).read())

    # retrieving games for each game date
    for game_date in game_dates:
        games = get_games_for_date(game_date.date(), games)

    open(tgt_path, 'w').write(
        json.dumps(games, indent=2, default=str))
