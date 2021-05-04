app.controller('teamStatsController', function($scope, $http, $routeParams, $q, svc) {

    $scope.svc = svc;
    var ctrl = this;
    $scope.season = $routeParams.season;
    // setting default table selection and sort keys and criteria/order
    $scope.tableSelect = 'standings';
    if ($scope.season == 2020) {
        $scope.seasonTypeSelect = 'PO';
    } else {
        $scope.seasonTypeSelect = 'RS';
    }
    // initially setting indicators which view we're currently in
    $scope.isStandingsView = true;
    $scope.sortConfig = {
        'sortKey': 'pts_per_game',
        'sortCriteria': ['pts_per_game', 'pt_pctg', 'points', 'score_diff', 'score'],
        'sortDescending': true
    }
    $scope.fromRoundSelect = '1';
    // initially setting memory for previously used home/away game selection
    $scope.oldHomeAwaySelect = 'unused';

    // retrieving column headers (and abbreviations + explanations)
    $http.get('./js/team_stats_columns.json').then(function (res) {
        $scope.stats_cols = res.data;
    });

    // for some reason the previous way to load all players doesn't work with 2020 data
    // some problem with asynchronous loading I don't clearly understand
    // that is why we have to wait explicitly for the data being loaded by using a list of promises
    var promises = [];
    promises.push(getDatesAttendances());
    $q.all(promises).then(function (results) {
        $scope.dcup_date = moment(results[0].data['dates']['dcup_date']);
        $scope.reunification_date = moment(results[0].data['dates']['reunification_date']);
        $scope.avg_attendance_last_season = results[0].data['avg_attendance_last_season'];
    });
    function getDatesAttendances() {
        return $http.get('./data/' + $scope.season + '/dates_attendance.json');
    }

    // retrieving significant dates and previous year's attendance from external file
    $http.get('./data/' + $scope.season + '/dates_attendance.json').then(function (res) {
        $scope.dcup_date = moment(res.data['dates']['dcup_date']);
        $scope.avg_attendance_last_season = res.data['avg_attendance_last_season'];
    });

    // retrieving teams
    $http.get('./js/teams.json').then(function (res) {
        // only retaining teams that are valid for current season
        $scope.teams = res.data.filter(team => team.valid_from <= $scope.season && team.valid_to >= $scope.season);
        // creating lookup structures...
        // ...for team locations
        $scope.team_location_lookup = $scope.teams.reduce((o, key) => Object.assign(o, {[key.abbr]: key.location}), {});
        // ...for playoff participation indicator
        $scope.team_playoff_lookup = $scope.teams.reduce((o, key) => Object.assign(o, {[key.abbr]: key.po[$scope.season]}), {});
    });

    // starting to watch filter selection lists
    $scope.$watchGroup([
            'situationSelect', 'homeAwaySelect', 'seasonTypeSelect',
            'fromRoundSelect', 'toRoundSelect', 'weekdaySelect', 'timespanSelect'
        ], function() {
        if ($scope.team_stats) {
            $scope.filtered_team_stats = $scope.filterStats($scope.team_stats);
        }
    }, true);

    // loading stats from external json file
    $http.get('data/' + $scope.season + '/del_team_game_stats.json').then(function (res) {
        $scope.last_modified = res.data[0];
        $scope.team_stats = res.data[1];
        // retrieving maximum round played
        $scope.maxRoundPlayed = Math.max.apply(Math, $scope.team_stats.map(function(o) { return o.round; })).toString();
        // retrieving all weekdays a game was played by all the teams
        $scope.weekdaysPlayed = [...new Set($scope.team_stats.map(item => item.weekday))].sort();
        // retrieving all months a game was played by all the teams
        $scope.monthsPlayed = [...new Set($scope.team_stats.map(item => moment(item.game_date).month()))];
        // setting to round selection to maximum round played
        $scope.toRoundSelect = $scope.maxRoundPlayed;
        $scope.filtered_team_stats = $scope.filterStats($scope.team_stats);
    });

    // TODO: move to out-of-controller location
    $scope.filterStats = function (stats) {
        filtered_team_stats = {};
        if ($scope.team_stats === undefined)
            return filtered_team_stats;
        $scope.teams.forEach(team => {
            abbr = team['abbr'];
            if (!filtered_team_stats[abbr]) {
                if ($scope.seasonTypeSelect == 'MSC' && !team['msc_2020']) {
                    return;
                }
                if ($scope.seasonTypeSelect == 'PO' && !team['po'][$scope.season]) {
                    return;
                }
                filtered_team_stats[abbr] = {};
                filtered_team_stats[abbr]['team'] = abbr;
                // retrieving divisions from team definitions for special season 2020/21
                if ($scope.season == 2020) {
                    // MSC had separate divisions
                    if ($scope.seasonTypeSelect == 'MSC') {
                        seasonType = 'MSC'
                    } else {
                        seasonType = 'RS';
                    }
                    filtered_team_stats[abbr]['division'] = team['division'][$scope.season][seasonType];
                }
                $scope.svc.stats_to_aggregate().forEach(category => {
                    filtered_team_stats[abbr][category] = 0;
                });
            }
        });

        $scope.team_stats.forEach(element => {
            team = element['team'];
            is_equal_past_from_date = false;
            is_prior_equal_to_date = false;
            is_selected_home_away_type = false;
            is_selected_game_situation = false;
            is_selected_season_type = false;
            is_selected_weekday = false;
            is_equal_past_from_round = false;
            is_prior_equal_to_round = false;

            // retrieving game date as moment structure
            date_to_test = moment(element.game_date);

            if (ctrl.fromDate) {
                if (date_to_test >= ctrl.fromDate.startOf('day'))
                    is_equal_past_from_date = true;
            } else {
                is_equal_past_from_date = true;
            }
            if (ctrl.toDate) {
                if (date_to_test <= ctrl.toDate.startOf('day'))
                    is_prior_equal_to_date = true;
            } else {
                is_prior_equal_to_date = true;
            }
            if ($scope.homeAwaySelect) {
                if ($scope.homeAwaySelect === element.home_road)
                    is_selected_home_away_type = true;
            } else {
                is_selected_home_away_type = true;
            }
            if ($scope.situationSelect) {
                if (element[$scope.situationSelect])
                    is_selected_game_situation = true;
            } else {
                is_selected_game_situation = true;
            }
            if ($scope.seasonTypeSelect) {
                if ($scope.seasonTypeSelect === element.season_type)
                    is_selected_season_type = true;
            } else {
                // if seasonTypeSelect is set to "Hauptrunde und Playoffs" we just want that but no pre-season games
                if (element['season_type'] != 'MSC')
                    is_selected_season_type = true;
            }
            if ($scope.weekdaySelect) {
                if ($scope.weekdaySelect == element.weekday)
                    is_selected_weekday = true;
            } else {
                is_selected_weekday = true;
            }
            if ($scope.fromRoundSelect) {
                if (element.round >= parseFloat($scope.fromRoundSelect))
                    is_equal_past_from_round = true;
            } else {
                is_equal_past_from_round = true;
            }
            if ($scope.toRoundSelect) {
                if (element.round <= parseFloat($scope.toRoundSelect))
                    is_prior_equal_to_round = true;
            } else {
                is_prior_equal_to_round = true;
            }

            // finally aggregating values of all season stat lines that have been filtered
            if (
                is_equal_past_from_date && is_prior_equal_to_date &&
                is_selected_home_away_type && is_selected_game_situation &&
                is_selected_season_type && is_selected_weekday &&
                is_equal_past_from_round && is_prior_equal_to_round
            ) {
                $scope.svc.stats_to_aggregate().forEach(category => {
                    // skipping categories that possibly don't exist, e.g. for shootout-related data
                    if (element[category] === undefined) {
                        
                    } else {
                        filtered_team_stats[team][category] += element[category];
                    }
                })
            }
        });
        filtered_team_stats = Object.values(filtered_team_stats);

        filtered_team_stats.forEach(element => {
            // calculating score and goal differentials
            element['score_diff'] = element['score'] - element['opp_score'];
            element['goals_diff'] = element['goals'] - element['opp_goals'];
            element['goals_diff_1'] = element['goals_1'] - element['opp_goals_1'];
            element['goals_diff_2'] = element['goals_2'] - element['opp_goals_2'];
            element['goals_diff_3'] = element['goals_3'] - element['opp_goals_3'];
            // calculating points per game and points percentage
            element['pts_per_game'] = svc.calculateRate(element['points'], element['games_played']);
            element['pt_pctg'] = svc.calculatePercentage(element['points'], element['games_played'], 3);
            // calculating shot zone percentages
            element['sl_p'] = svc.calculatePercentage(element['sl_sh'], element['shots']);
            element['lf_p'] = svc.calculatePercentage(element['lf_sh'], element['shots']);
            element['rg_p'] = svc.calculatePercentage(element['rg_sh'], element['shots']);
            element['bl_p'] = svc.calculatePercentage(element['bl_sh'], element['shots']);
            // calculating zone percentages for shots against
            element['sl_p_a'] = svc.calculatePercentage(element['sl_sh_a'], element['opp_shots']);
            element['lf_p_a'] = svc.calculatePercentage(element['lf_sh_a'], element['opp_shots']);
            element['rg_p_a'] = svc.calculatePercentage(element['rg_sh_a'], element['opp_shots']);
            element['bl_p_a'] = svc.calculatePercentage(element['bl_sh_a'], element['opp_shots']);
            // calculating shooting, save and zone percentages for shots on goal
            element['shot_pctg'] = svc.calculatePercentage(element['goals'], element['shots_on_goal']);
            element['opp_save_pctg'] = svc.calculatePercentage(element['opp_saves'], element['shots_on_goal']);
            element['sl_og_p'] = svc.calculatePercentage(element['sl_og'], element['shots_on_goal']);
            element['lf_og_p'] = svc.calculatePercentage(element['lf_og'], element['shots_on_goal']);
            element['rg_og_p'] = svc.calculatePercentage(element['rg_og'], element['shots_on_goal']);
            element['bl_og_p'] = svc.calculatePercentage(element['bl_og'], element['shots_on_goal']);
            // calculating shooting and save percentages for shots on goal in 5-on-5 play
            element['shot_pctg_5v5'] = svc.calculatePercentage(element['goals_5v5'], element['shots_on_goal_5v5']);
            element['opp_save_pctg_5v5'] = svc.calculatePercentage(element['shots_on_goal_5v5'] - element['goals_5v5'], element['shots_on_goal_5v5']);
            // calculating opponent shooting, save and zone percentages for shots on goal against
            element['opp_shot_pctg'] = svc.calculatePercentage(element['opp_goals'], element['opp_shots_on_goal']);
            element['save_pctg'] = svc.calculatePercentage(element['saves'], element['opp_shots_on_goal']);
            element['sl_og_p_a'] = svc.calculatePercentage(element['sl_og_a'], element['opp_shots_on_goal']);
            element['lf_og_p_a'] = svc.calculatePercentage(element['lf_og_a'], element['opp_shots_on_goal']);
            element['rg_og_p_a'] = svc.calculatePercentage(element['rg_og_a'], element['opp_shots_on_goal']);
            element['bl_og_p_a'] = svc.calculatePercentage(element['bl_og_a'], element['opp_shots_on_goal']);
            // calculating opponent shooting and save percentages for shots on goal against in 5-on-5 play
            element['opp_shot_pctg_5v5'] = svc.calculatePercentage(element['opp_goals_5v5'], element['opp_shots_on_goal_5v5']);
            element['save_pctg_5v5'] = svc.calculatePercentage(element['opp_shots_on_goal_5v5'] - element['opp_goals_5v5'], element['opp_shots_on_goal_5v5']);
            // calculating number of shootout games played
            element['so_games_played'] = element['sw'] + element['sl'];
            // calculating team shootout shooting percentages
            element['so_pctg'] = svc.calculatePercentage(element['so_g'], element['so_a']);
            element['opp_so_pctg'] = svc.calculatePercentage(element['opp_so_g'], element['opp_so_a']);
            element['so_sv_pctg'] = svc.calculatePercentage(element['opp_so_a'] - element['opp_so_g'], element['opp_so_a']);
            // calculating PDO
            element['pdo'] = element['shot_pctg'] + element['save_pctg'];
            element['opp_pdo'] = element['opp_shot_pctg'] + element['opp_save_pctg'];
            // calculating PDO in 5-on-5 play
            element['pdo_5v5'] = element['shot_pctg_5v5'] + element['save_pctg_5v5'];
            element['opp_pdo_5v5'] = element['opp_shot_pctg_5v5'] + element['opp_save_pctg_5v5'];
            // calculating shots on goal for percentage
            element['shot_for_pctg'] = svc.calculatePercentage(element['shots_on_goal'], element['shots_on_goal'] + element['opp_shots_on_goal']);
            element['opp_shot_for_pctg'] = svc.calculatePercentage(element['opp_shots_on_goal'], element['shots_on_goal'] + element['opp_shots_on_goal']);
            // calculating unblocked shots (i.e. Fenwick) for percentage
            element['fenwick_events'] = element['shots_on_goal'] + element['shots_missed']; 
            element['opp_fenwick_events'] = element['opp_shots_on_goal'] + element['opp_shots_missed']; 
            element['fenwick_for_pctg'] = svc.calculatePercentage(element['fenwick_events'], element['fenwick_events'] + element['opp_fenwick_events']);
            element['opp_fenwick_for_pctg'] = svc.calculatePercentage(element['opp_fenwick_events'], element['fenwick_events']+ element['opp_fenwick_events']);
            // calculating shots (i.e. Corsi) for percentage
            element['corsi_for_pctg'] = svc.calculatePercentage(element['shots'], element['shots'] + element['opp_shots']);
            element['opp_corsi_for_pctg'] = svc.calculatePercentage(element['opp_shots'], element['shots'] + element['opp_shots']);
            // calculating power play percentage
            element['pp_pctg'] = svc.calculatePercentage(element['pp_goals'], element['pp_opps']);
            // calculating penalty killing percentage
            element['pk_pctg'] = 100 - svc.calculatePercentage(element['opp_pp_goals'], element['sh_opps']);
            // calculating special teams goal differential and combined special team percentages
            element['pp_pk_gdiff'] = element['pp_goals'] + element['sh_goals'] - element['opp_pp_goals'] - element['opp_sh_goals'];
            element['pp_pk_comb_pctg'] = element['pp_pctg'] + element['pk_pctg'];
            // calculating team faceoff percentage
            element['faceoff_pctg'] = svc.calculatePercentage(element['faceoffs_won'], element['faceoffs']);
            // calculating team penalty minutes per game
            element['pim_per_game'] =  svc.calculateRate(element['pim'], element['games_played']);
            // calculating average attendance
            element['avg_attendance'] = svc.calculateRate(element['attendance'], element['games_played']);
            // retrieving last year's average attendance
            element['avg_attendance_last_season'] = $scope.avg_attendance_last_season[element['team']];
            element['avg_attendance_delta'] = element['avg_attendance'] - element['avg_attendance_last_season']; 
            // calculating utilized attendance capacity
            element['util_capacity_pctg'] = svc.calculatePercentage(element['attendance'], element['capacity']);
            // calculating score state percentages
            element['leading_pctg'] = svc.calculatePercentage(element['leading'], element['time_played']);
            element['trailing_pctg'] = svc.calculatePercentage(element['trailing'], element['time_played']);
            element['tied_pctg'] = svc.calculatePercentage(element['tied'], element['time_played']);
            // calculating 5-on-5 shot share percentages
            element['shots_5v5_pctg'] = svc.calculatePercentage(element['shots_5v5'], element['shots_5v5'] + element['opp_shots_5v5']);
            element['shots_unblocked_5v5_pctg'] = svc.calculatePercentage(element['shots_unblocked_5v5'], element['shots_unblocked_5v5'] + element['opp_shots_unblocked_5v5']);
            element['shots_on_goal_5v5_pctg'] = svc.calculatePercentage(element['shots_on_goal_5v5'], element['shots_on_goal_5v5'] + element['opp_shots_on_goal_5v5']);
            // calculating detailed power play and penalty killing percentages
            element['pp_5v4_pctg'] = svc.calculatePercentage(element['ppg_5v4'], element['pp_5v4'], 1, true);
            element['pp_5v3_pctg'] = svc.calculatePercentage(element['ppg_5v3'], element['pp_5v3'], 1, true);
            element['pp_4v3_pctg'] = svc.calculatePercentage(element['ppg_4v3'], element['pp_4v3'], 1, true);
            element['pk_4v5_pctg'] = svc.calculateFrom100Percentage(element['opp_ppg_5v4'], element['opp_pp_5v4']);
            element['pk_3v5_pctg'] = svc.calculateFrom100Percentage(element['opp_ppg_5v3'], element['opp_pp_5v3']);
            element['pk_3v4_pctg'] = svc.calculateFrom100Percentage(element['opp_ppg_4v3'], element['opp_pp_4v3']);
            // calculating powerplay/penalty killing times per game
            element['pp_time_per_game'] = svc.calculateRate(element['pp_time'], element['games_played']);
            element['pk_time_per_game'] = svc.calculateRate(element['opp_pp_time'], element['games_played']);
            // calculating powerplay time per powerplay goal
            element['pp_time_per_pp_goal'] = svc.calculateRate(element['pp_time'], element['pp_goals']);
            element['pk_time_per_opp_pp_goal'] = svc.calculateRate(element['opp_pp_time'], element['opp_pp_goals']);
            // calculating powerplays per powerplay goal
            element['full_pps_per_pp_goal'] = svc.calculateRate(element['pp_time_per_pp_goal'], 120);
            element['full_pks_per_opp_pp_goal'] = svc.calculateRate(element['pk_time_per_opp_pp_goal'], 120);
        });
        
        return filtered_team_stats;
    };

    // default sorting criteria for all defined tables
    $scope.tableSortCriteria = {
        'standings': 'pts_per_game',
        'group_standings': 'pts_per_game',
        'special_team_stats': 'pp_pctg',
        'goal_stats': 'goals_diff',
        'shot_stats': 'shots_on_goal',
        'shot_save_rates': 'shots_on_goal',
        'shot_save_rates_5v5': 'shots_on_goal_5v5',
        'shot_shares': 'corsi_for_pctg',
        'shot_shares_5v5': 'shots_5v5_pctg',
        'shot_zones': 'shots',
        'shot_on_goal_zones': 'shots_on_goal',
        'shot_zones_against': 'opp_shots',
        'shot_on_goal_zones_against': 'opp_shots_on_goal',
        'additional_stats': 'faceoff_pctg',
        'shootout_stats': 'so_pctg',
        'penalty_stats': 'pim_per_game',
        'score_state_stats': 'leading_pctg',
        'attendance_stats': 'util_capacity_pctg',
        'power_play_details': 'pp_5v4_pctg',
        'penalty_kill_details': 'pk_4v5_pctg',
        'special_team_times': 'pp_time_per_pp_goal'
    }

    // hierarchical sorting criteria for specified sort key
    $scope.sortCriteria = {
        // standings
        "points": ['points', 'score_diff', 'score'],
        "pt_pctg": ['pt_pctg', 'points', 'score_diff', 'score'],
        "pts_per_game": ['pts_per_game', 'pt_pctg', 'points', 'score_diff', 'score'],
        "games_played": ['games_played', '-team'],
        // goal stats
        "goals_diff": ['goals_diff', 'goals'],
        "goals_diff_1": ['goals_diff_1', 'goals_1'],
        "goals_diff_2": ['goals_diff_2', 'goals_2'],
        "goals_diff_3": ['goals_diff_3', 'goals_3'],
        "goals_1": ['goals_1', 'goals_diff_1'],
        "goals_2": ['goals_2', 'goals_diff_2'],
        "goals_3": ['goals_3', 'goals_diff_3'],
        "opp_goals_1": ['opp_goals_1', '-goals_diff_1'],
        "opp_goals_2": ['opp_goals_2', '-goals_diff_2'],
        "opp_goals_3": ['opp_goals_3', '-goals_diff_3'],
        // shots
        "opp_shots_on_goal": ['opp_shots_on_goal', 'games_played'],
        "opp_shots": ['opp_shots', 'games_played'],
        "shots_on_goal": ['shots_on_goal', 'goals', 'games_played'],
        "shots": ['shots', 'games_played'],
        "faceoff_pctg": ['faceoff_pctg', 'faceoffs'],
        // special team stats
        "pp_pctg": ['pp_pctg', '-pp_opps'],
        "pp_goals": ['pp_goals', 'pp_pctg'],
        "sh_goals": ['sh_goals', '-sh_opps'],
        "opp_pp_goals": ['opp_pp_goals', '-pk_pctg'],
        "opp_sh_goals": ['opp_sh_goals', '-sh_opps'],
        "so_pctg": ['so_pctg', 'so_g'],
        // shot shares
        "corsi_for_pctg": ['corsi_for_pctg', 'shots'],
        "shots_5v5_pctg": ['shots_5v5_pctg', 'shots_5v5'],
        "shots_on_goal_5v5": ['shots_on_goal_5v5', 'goals_5v5', '-games_played'],
        "goals_diff": ['goals_diff', 'goals', '-games_played'],
        "pt_pctg": ['pt_pctg', 'points', 'goals_diff', '-games_played', 'score'],
        "pim_per_game": ['pim_per_game', 'penalties'],
        "util_capacity_pctg": ['util_capacity_pctg', 'attendance'],
        "leading_pctg": ['leading_pctg', 'leading'],
        'pp_time_per_pp_goal': ['pp_time_per_pp_goal', 'pp_goals'],
        'pp_5v4_pctg': ['pp_5v4_pctg', 'pp_goals'],
        'pk_4v5_pctg': ['pk_4v5_pctg', '-opp_pp_goals']
    };

    // colums that by default are sorted in ascending order
    $scope.ascendingAttrs = [
        'team', 'opp_score', 'pim_per_game', 'opp_shots', 'opp_shots_on_goal',
        'pp_time_per_pp_goal', 'full_pps_per_pp_goal'
    ];


    // changing sorting criteria according to table selected for display
    $scope.changeTable = function() {
        // retrieving sort key for current table from list of default table
        // sort criteria
        sortKey = $scope.tableSortCriteria[$scope.tableSelect];
        // checking whether current sort key indicates default ascending
        // sort order
        if ($scope.ascendingAttrs.indexOf(sortKey) !== -1) {
            sortDescending = false;
        } else {
            sortDescending = true;
        }
        // setting global sort configuration according to findings
        $scope.sortConfig = {
            'sortKey': sortKey,
            'sortCriteria': $scope.sortCriteria[sortKey],
            'sortDescending': sortDescending
        };
        // toggling additional option list in standings view
        if ($scope.tableSelect === 'standings' || $scope.tableSelect === 'group_standings') {
            $scope.isStandingsView = true;
        } else {
            $scope.isStandingsView = false;
            $scope.situationSelect = undefined
        }
        // checking whether we're in attendance table view
        if ($scope.tableSelect === 'attendance_stats') {
            $scope.oldHomeAwaySelect = $scope.homeAwaySelect;
            $scope.homeAwaySelect = 'home';
        } else {
            if ($scope.oldHomeAwaySelect != 'unused') {
                $scope.homeAwaySelect = $scope.oldHomeAwaySelect;
                $scope.oldHomeAwaySelect = undefined;
            }
        }
        // setting the right divisions/groups corresponding to season type
        if ($scope.seasonTypeSelect === 'MSC') {
            $scope.divisions = ['A', 'B'];
        } else {
            $scope.divisions = ['Nord', 'Süd'];
        }
    };

    // adjusting sort order after click on column header
    $scope.setSortOrder = function(sortKey, oldSortConfig) {
        // if previous sort key equals the new one
        if (oldSortConfig['sortKey'] == sortKey) {
            // just change sort direction
            return {
                'sortKey': oldSortConfig['sortKey'],
                'sortCriteria': oldSortConfig['sortCriteria'],
                'sortDescending': !oldSortConfig['sortDescending']
            }
        } else {
            // ascending sort order for a few columns
            if ($scope.ascendingAttrs.indexOf(sortKey) !== -1) {
                sort_descending = false;
            // otherwise descending sort order
            } else {
                sort_descending = true;
            }
            // retrieving actual (and minor) sort criteria from scope-wide
            // definition of sort criteria
            // use plain sort key if nothing has been defined otherwise
            sort_criteria = $scope.sortCriteria[sortKey] || sortKey;
            return {
                'sortKey': sortKey,
                'sortCriteria': sort_criteria,
                'sortDescending': sort_descending
            }
        }
    }

    $scope.changeTimespan = function() {
        if (!$scope.timespanSelect) {
            ctrl.fromDate = null;
            ctrl.toDate = null;
            return;
        }
        if ($scope.timespanSelect === '-----------')
            return;
        if ($scope.timespanSelect == 'pre_dcup')
        {
            ctrl.fromDate = moment($scope.season + '-09-01');
            ctrl.toDate = $scope.dcup_date;
        } else if ($scope.timespanSelect == 'post_dcup') {
            ctrl.fromDate = $scope.dcup_date;
            var nextSeason = parseFloat($scope.season) + 1;
            ctrl.toDate = moment(nextSeason + '-05-01');
        } else if ($scope.timespanSelect == 'pre_reunification') {
            ctrl.fromDate = moment($scope.season + '-12-16');
            ctrl.toDate = $scope.reunification_date;
        } else if ($scope.timespanSelect == 'post_reunification') {
            ctrl.fromDate = $scope.reunification_date;
            ctrl.toDate = moment('2021-04-19');
        } else {
            timespanSelect = parseInt($scope.timespanSelect) + 1;
            if (timespanSelect < 9) {
                season = parseInt($scope.season) + 1;
            } else {
                season = parseInt($scope.season);
            }
            ctrl.fromDate = moment(season + '-' + timespanSelect + '-1', 'YYYY-M-D');
            ctrl.toDate = moment(season + '-' + timespanSelect + '-1', 'YYYY-M-D').endOf('month');
            }
    }

    // re-filtering team statistics if date range has been changed
    $scope.changeDate = function() {
        if ($scope.team_stats) {
            $scope.filtered_team_stats = $scope.filterStats($scope.team_stats);
        };
    }

});
