#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json

from collections import OrderedDict, defaultdict

import requests
import intervaltree

from utils import get_game_info


BASE_URL = 'https://www.del.org/live-ticker'
EVENTS_SUFFIX = "matches/%d/period-events.json"
GAME_SRC = 'del_games.json'
TGT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')


def build_interval_tree(game):
    """
    Builds an interval tree holding information about goalie shifts and
    penalties. Later used to determine which goalie had to save a certain
    shot or what kind of player situation existed at the time of a shot.
    """
    # retrieving raw events data
    events_path = EVENTS_SUFFIX % game['game_id']
    events_url = "%s/%s" % (BASE_URL, events_path)
    r = requests.get(events_url)
    events_data = r.json()

    # using ordered dictionary to maintain insertion order of keys
    goalie_changes = OrderedDict()
    goalie_changes['home'] = list()
    goalie_changes['road'] = list()
    # goalie_in_net = {'home': 0, 'road': 0}
    goalie_for_team = {'home': None, 'road': None}

    # setting up interval tree
    it = intervaltree.IntervalTree()
    # setting up list to contain all end of period times and all times a goal
    # has been scored
    end_period_times = list()
    goal_times = list()

    penalty_times = dict()

    # TODO: tidy up the following mess
    # sorting periods first to retain compatibility with Python 3.5
    for period in sorted(events_data.keys()):

        if period in ['1', '2', '3']:
            end_period_times.append(int(period) * 1200)

        for event in events_data[period]:
            # retrieving type of event first
            event_type = event['type']

            # adding time of period end to list of period end times
            if period == 'overtime' and event_type == 'periodEnd':
                end_period_times.append(event['time'])

            # adding time of goal to list of times a goal has been scored
            if event_type == 'goal':
                goal_times.append(event['time'])

            # handling penalties
            if event_type == 'penalty':
                create_penalty_interval(event, game, it)

                # retrieving involved teams
                if event['data']['team'] == 'home':
                    penalty_team = game['home_abbr']
                else:
                    penalty_team = game['road_abbr']

                create_time = event['data']['createTime']
                duration = event['data']['duration']

                if duration in (120, 300):

                    if create_time not in penalty_times:
                        penalty_times[create_time] = dict()

                    if penalty_team not in penalty_times[create_time]:
                        penalty_times[create_time][penalty_team] = (
                            1, [duration])
                    else:
                        (
                            previous_penalties,
                            previous_durations
                        ) = penalty_times[
                            create_time][penalty_team]
                        penalty_times[create_time][penalty_team] = (
                            previous_penalties + 1,
                            previous_durations + [duration])

            # registering goalie changes
            if event_type == 'goalkeeperChange':
                register_goalie_change(
                    event, game, goalie_changes, goalie_for_team)

    create_goalie_intervals(
        goalie_changes, goalie_for_team, end_period_times, game, it)

    return it, goal_times, penalty_times


def register_goalie_change(event, game, goalie_changes, goalie_for_team):
    """
    Registers a goalie change retrieved from game events by extending the
    specified list of previous changes and by updating the specified dictioary
    holding the current goalie for a team involved in the game.
    """
    # retrieving time of goalie change
    event_time = event['data']['time']
    # retrieving team involved in goalie change
    if event['data']['team'] == 'home':
        event_team = game['home_abbr']
        home_road = 'home'
    else:
        event_team = game['road_abbr']
        home_road = 'road'
    # handling outgoing goalie
    if event['data']['outgoingGoalkeeper']:
        change_type = 'goalie_out'
        player_id = event['data']['outgoingGoalkeeper']['playerId']
        # adding outgoing goalie to list of goalie changes
        goalie_changes[home_road].append((
            event_time, event_team, change_type, player_id))
        # updating the affected team's current goalie
        if goalie_for_team[home_road] == player_id:
            goalie_for_team[home_road] = None
    # handling incoming goalie
    if event['data']['player']:
        change_type = 'goalie_in'
        player_id = event['data']['player']['playerId']
        # adding incoming goalie to list of goalie changes
        goalie_changes[home_road].append((
            event_time, event_team, change_type, player_id))
        # updating the affected team's current goalie
        goalie_for_team[home_road] = player_id


def create_goalie_intervals(
        goalie_changes, goalie_for_team, end_period_times,
        game, interval_tree):
    """
    Creates time intervals containing all information about in-game goalie
    changes.
    """
    # first adding outgoing goalies at the end (e.g. maximum time) of
    # the game as these changes are not registered in the official list of
    # game events
    for key in goalie_for_team:
        if goalie_for_team[key] is not None:
            goalie_changes[key].append((
                # using the maximum time from all period end times as time
                # of game end
                max(end_period_times), game["%s_abbr" % key],
                'goalie_out', goalie_for_team[key]))

    # finally converting collected list of goalie changes to actual intervals
    for home_road in goalie_changes:
        for i in range(0, len(goalie_changes[home_road]) - 1, 2):
            goalie_in_time, goalie_in_team, _, goalie_in_id = (
                goalie_changes[home_road][i])
            goalie_out_time, _, _, _ = (goalie_changes[home_road][i + 1])
            # optionally switching goalie in and out times if necessary
            if goalie_out_time < goalie_in_time:
                goalie_in_time, goalie_out_time = (
                    goalie_out_time, goalie_in_time)
            # adding goalie shift to interval tree
            # both times are increased by 1 to work around the interval tree's
            # implementation to include the interval's lower bound (when the
            # new goalie actually hasn't been on the ice yet) in a query result
            # but not the interval's upper bound (which could be a problem if
            # a goalie coming out incidentally falls together with a goal he
            # surrendered)
            interval_tree.addi(
                -goalie_out_time, -goalie_in_time,
                # goalie_in_time + 1, goalie_out_time + 1,
                ("goalie", goalie_in_team, goalie_in_id, goalie_in_time))


def create_penalty_interval(event, game, interval_tree):
    """
    Creates a time interval including all penalty-related information.
    """
    # retrieving involved teams
    if event['data']['team'] == 'home':
        penalty_team = game['home_abbr']
    else:
        penalty_team = game['road_abbr']
    # retrieving penalized player
    if (
        event['data']['disciplinedPlayer'] and
        'playerId' in event['data']['disciplinedPlayer']
    ):
        penalty_player_id = event['data']['disciplinedPlayer']['playerId']
        penalty_player = event['data']['disciplinedPlayer']['surname']
    else:
        penalty_player_id = None
        penalty_player = None
    # retrieving other penalty information
    penalty_start = event['data']['time']['from']['scoreboardTime']
    penalty_end = event['data']['time']['to']['scoreboardTime']
    duration = event['data']['duration']
    infraction = event['data']['codename']
    create_time = event['data']['createTime']

    # disregarding penalties with zero length, i.e. penalty shots
    if penalty_end != penalty_start:
        # optionally switching start and end time of penalty if necessary due
        # to data errors (e.g. Felix Schütz penalty in game 1247)
        if penalty_start > penalty_end:
            penalty_start, penalty_end = penalty_end, penalty_start
        penalty_description = "%d %s %s" % (
            duration, infraction, penalty_player)
        all_penalty_info = (
            penalty_description, penalty_team, penalty_player_id, create_time)
        # adding penalty to interval tree
        # end time is increased by 1 to make sure goals scored at
        # the premature end of a penalty are actually recognized
        # as power play/shorthanded goals
        interval_tree.addi(
            -penalty_end, -penalty_start,
            # penalty_start, penalty_end + 1,
            all_penalty_info)


def reconstruct_skater_situation(game):
    """
    Reconstructs on-ice skater situation for each second of the specified game.
    """
    print(
        "+ Reconstructing on-ice skater situation for " +
        "game %s" % get_game_info(game))

    # building interval tree to query goalies and player situations
    # receiving a list of times when goals has been scored
    it, goal_times, penalty_times = build_interval_tree(game)

    # retrieving game begin and end (in seconds) from interval tree
    game_end = - it.range().begin

    # setting up dictionary to hold skater situations for each second
    # of the game
    time_dict = dict()

    # setting up container to hold goalie/penalty intervals that have been
    # valid previously
    last_intervals = ''
    # set of currently on-going penalties that reduce the skater count on
    # ice
    on_going_intervals = set()
    extra_intervals = set()
    # initial setting for skater counts per team
    skr_count = {'home': 5, 'road': 5}
    goalies_not_on_ice = list()
    goalie_was_off = list()

    # doing the following for each second of the game
    for t in range(1, game_end + 1):
        if game['season_type'] == 'RS' and t == 3601:
            skr_count['home'] = 3
            skr_count['road'] = 3
            skr_count[game['home_abbr']] = 3
            skr_count[game['road_abbr']] = 3

        # retrieving all currently valid goalie and penalty intervals, i.e.
        # on-going goalie shifts and currently served penalties
        current_intervals = it[-t]

        # doing further processing for the current second of the game only
        # if goalie or penalty intervals have changed from previous second
        # of the game
        if current_intervals != last_intervals:
            # # copying skater count from previous second of the game
            # last_skr_count = copy.deepcopy(skr_count)

            # setting up containers holding the difference in skaters
            # produced by current intervals
            curr_delta = {'home': 0, 'road': 0}
            # helper container holding all teams that current have no
            # goalie on ice
            if goalies_not_on_ice:
                goalie_was_off = goalies_not_on_ice
            goalies_not_on_ice = ['home', 'road']
            goalies_on_ice = {'home_goalie': None, 'road_goalie': None}

            # effective_intervals = {'home': list(), 'road': list()}
            effective_intervals = defaultdict(list)

            for interval in current_intervals:
                # exploding interval payload
                desc, team, plr_id, create_time = interval[-1]
                # converting actual team abbreviation to home/road
                # denominator
                if game['home_abbr'] == team:
                    team = 'home'
                else:
                    team = 'road'
                # if a goalie shift is on-going, the current team's goalie
                # is on ice, i.e. *not not on ice*
                if desc == 'goalie':
                    goalies_not_on_ice.remove(team)
                    goalies_on_ice["%s_goalie" % team] = plr_id
                    if team in goalie_was_off:
                        curr_delta[team] -= 1
                        goalie_was_off.remove(team)
                # if a penalty shift is on-going...
                else:
                    # retrieving duration, infraction, and player name
                    duration, infraction, plr_name = desc.split(maxsplit=2)
                    # converting duration to actual number
                    duration = int(duration)
                    # only two- and five-minute-penalties can result in
                    # a reduction of the number of skaters on ice
                    if duration in (120, 300):
                        # checking if current interval has already been
                        # encountered previously
                        if (
                            interval not in on_going_intervals and
                            interval not in extra_intervals
                        ):
                            effective_intervals[team].append(interval)

            penalties_from_time = dict()

            if t - 1 in penalty_times:
                penalties_from_time = penalty_times[t - 1]

            if len(penalties_from_time) == 1:
                for team in effective_intervals:
                    for interval in effective_intervals[team]:
                        # add current interval to set of currently on-
                        # going intervals
                        on_going_intervals.add(interval)
                        # reducing the number of skaters for
                        # corresponding team starting at current time
                        curr_delta[team] -= 1

            elif len(penalties_from_time) == 2:

                home_pen_cnt, home_durations = penalty_times[t - 1][
                    game['home_abbr']]
                road_pen_cnt, road_durations = penalty_times[t - 1][
                    game['road_abbr']]

                # if number and durations of penalties for both teams
                # match, we have incidental penalties (DEL Rulebook,
                # Rule #112)
                if (
                    home_pen_cnt == road_pen_cnt and
                    sum(home_durations) == sum(road_durations)
                ):
                    if (
                        home_pen_cnt == 1 and
                        list(skr_count.values()) == [5, 5]
                    ):
                        for team in effective_intervals:
                            for interval in effective_intervals[team]:
                                # add current interval to set of currently
                                # on-going intervals
                                on_going_intervals.add(interval)
                                # reducing the number of skaters for
                                # corresponding team starting at current
                                # time
                                curr_delta[team] -= 1
                elif (
                    home_pen_cnt == road_pen_cnt and
                    sum(home_durations) != sum(road_durations)
                ):
                    for team in effective_intervals:
                        for interval in effective_intervals[team]:
                            # add current interval to set of currently
                            # on-going intervals
                            on_going_intervals.add(interval)
                            # reducing the number of skaters for
                            # corresponding team starting at current
                            # time
                            curr_delta[team] -= 1

                elif home_pen_cnt > road_pen_cnt:
                    pen_cnt_diff = home_pen_cnt - road_pen_cnt
                    pen_cnt = 0
                    for interval in effective_intervals['home']:
                        if pen_cnt < pen_cnt_diff:
                            # add current interval to set of currently
                            # on-going intervals
                            on_going_intervals.add(interval)
                            # reducing the number of skaters for
                            # corresponding team starting at current
                            # time
                            curr_delta['home'] -= 1
                        else:
                            extra_intervals.add(interval)
                        pen_cnt += 1
                    for interval in effective_intervals['road']:
                        extra_intervals.add(interval)

                elif road_pen_cnt > home_pen_cnt:
                    pen_cnt_diff = road_pen_cnt - home_pen_cnt
                    pen_cnt = 0
                    for interval in effective_intervals['road']:
                        if pen_cnt < pen_cnt_diff:
                            # add current interval to set of currently
                            # on-going intervals
                            on_going_intervals.add(interval)
                            # reducing the number of skaters for
                            # corresponding team starting at current
                            # time
                            curr_delta['road'] -= 1
                        else:
                            extra_intervals.add(interval)
                        pen_cnt += 1
                    for interval in effective_intervals['home']:
                        extra_intervals.add(interval)

            # preparing to remove intervals from set of on-going intervals
            # if they have been passed
            intervals_to_remove = set()
            # doing the following for each interval currently registered as
            # on-going
            for interval in on_going_intervals:
                desc, team, plr_id, create_time = interval[-1]
                # converting actual team abbreviation to home/road
                # denominator
                if game['home_abbr'] == team:
                    team = 'home'
                else:
                    team = 'road'
                # checking whether interval currently registered as
                # on-going is in fact still on-going
                if interval not in current_intervals:
                    # select no-longer on-going interval for removal from
                    # set of intervals currently registered as on-going
                    intervals_to_remove.add(interval)
                    # increading the number of skaters for corresponding
                    # team starting at current time
                    curr_delta[team] += 1
            # actually removing no longer on-going intervals
            on_going_intervals.difference_update(intervals_to_remove)

            intervals_to_remove = set()
            for interval in extra_intervals:
                # checking whether interval currently registered as
                # on-going is in fact still on-going
                if interval not in current_intervals:
                    # select no-longer on-going interval for removal from
                    # set of intervals currently registered as on-going
                    intervals_to_remove.add(interval)
                    # increading the number of skaters for corresponding
                    # team starting at current time
                    # curr_delta[team] += 1
            # actually removing no longer on-going intervals
            extra_intervals.difference_update(intervals_to_remove)

            # increasing the number of skaters on the ice in case an
            # involved team has been found to be playing without a goalie
            for team in goalies_not_on_ice:
                curr_delta[team] += 1

            # actually calculating current skater count from previous count
            # and deltas collected from all current intervals
            skr_count['home'] = skr_count['home'] + curr_delta['home']
            skr_count['road'] = skr_count['road'] + curr_delta['road']

            skr_count[game['home_abbr']] = skr_count['home']
            skr_count[game['road_abbr']] = skr_count['road']

        # saving currently valid intervals for comparison at next
        # second in the game
        last_intervals = current_intervals

        # setting current skater count per team for second in game
        time_dict[t] = {**skr_count, **goalies_on_ice}

    return time_dict, goal_times


if __name__ == '__main__':

    # setting up source path
    src_path = os.path.join(TGT_DIR, GAME_SRC)

    # loading games
    games = json.loads(open(src_path).read())

    cnt = 0
    for game in games[:]:
        cnt += 1

        time_dict, goal_times = reconstruct_skater_situation(game)

        for t in time_dict:
            print(t, time_dict[t])
