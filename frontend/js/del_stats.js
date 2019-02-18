var app = angular.module('delStatsApp', ['ngRoute', 'moment-picker'])

app.config(['$routeProvider', function($routeProvider){
    $routeProvider
        .when('/home', {
            templateUrl: 'home.html',
        })
        .when('/del_stats', {
            templateUrl: 'player_stats.html',
            controller: 'mainController'
        })
        .when('/team_stats', {
            templateUrl: 'team_stats.html',
            controller: 'teamController as ctrl'
        })
        .when('/player_profile/:team/:player_id',
        {
            templateUrl: 'player_profile.html',
            controller: 'plrController as ctrl'
        })
        .when('/team_profile/:team',
        {
            templateUrl: 'team_profile.html',
            controller: 'teamProfileController as ctrl'
        })
        .otherwise({
            redirectTo: '/home'
        })
}]);

app.config(['momentPickerProvider', function(momentPickerProvider){
    momentPickerProvider.options({
        locale: 'de',
        format: 'L',
        minView: 'decade',
        maxView: 'day',
        startView: 'month',
        autoclose: true,
        keyboard: true
    })
}]);

// providing functions to several controllers as services
app.factory('svc', function() {
    return {
        // sets sorting order according to selected sort criterion
        setSortOrder: function(sortCriterion, oldSortCriterion, oldStatsSortDescending, ascendingAttrs) {
            // if current criterion equals the new one
            if (oldSortCriterion === sortCriterion) {
                // just change sort direction
                return !oldStatsSortDescending;
            } else {
                // ascending for a few columns
                if (ascendingAttrs.indexOf(sortCriterion) !== -1) {
                    return false;
                } else {
                    // otherwise descending sort order
                    return true;
                }
            }
        },
        // formats time (in seconds) as mm:ss
        formatTime: function(timeInSeconds) {
            return Math.floor(timeInSeconds / 60) + ":" + ('00' + (Math.floor(timeInSeconds) % 60)).slice(-2);
        },
        // gets total sum of filtered attribute values
        getFilteredTotal: function(list, attribute, dataSource) {
            if (dataSource === undefined) {
                return
            }
            var total = 0;
            for(var i = 0; i < list.length; i++){
                total += list[i][attribute];
            }
            return total;
        },
        // gets total sum of filtered attributed values through a specified game date
        getFilteredAccumulatedTotal: function(list, attribute, dataSource, to) {
            if (dataSource === undefined) {
                return
            }
            var total = 0;
            for (var i = list.length-1; i >= 0; i--) {
                total += list[i][attribute];
                if (list[i]['game_date'] == to)
                {
                    return total;
                }
            }
            return total;
        },
        // gets average of filtered attributed values through a specified game date
        getFilteredAverageTotal: function(list, attribute, dataSource, to) {
            if (dataSource === undefined) {
                return
            }
            var total = 0;
            var cnt_data = 0;
            for (var i = list.length-1; i >= 0; i--) {
                cnt_data++;
                total += list[i][attribute];
                
                if (list[i]['game_date'] == to)
                {
                    return total / cnt_data;
                }
            }
            return total / cnt_data;
        },
        parseFloat: function(floatAsString) {
            return parseFloat(floatAsString);
        }
    }
});


app.controller('teamProfileController', function($scope, $http, $routeParams, $location, svc) {
    var ctrl = this;
    $scope.svc = svc;
    $scope.currentTeam = $routeParams.team;
    $scope.tableSelect = 'basic_game_by_game';
    $scope.sortCriterion = 'date';
    $scope.statsSortDescending = true;

    // loading stats from external json file
    $http.get('data/del_team_game_stats.json').then(function (res) {
        $scope.last_modified = res.data[0];
        $scope.team_stats = res.data[1];
        $scope.game_log = $scope.team_stats.filter(function(value, index, arr) {
            return value['team'] == $scope.currentTeam;
        });
    });

    // retrieving column headers (and abbreviations + explanations)
    $http.get('./js/team_profile_columns.json').then(function (res) {
        $scope.stats_cols = res.data;
    });
    // retrieving teams
    $http.get('./js/teams.json').then(function (res) {
        $scope.teams = res.data;
        // creating lookup structures...
        // ...for team names used in urls
        $scope.team_lookup = $scope.teams.reduce((o, key) => Object.assign(o, {[key.abbr]: key.url_name}), {});
        // ...for full team names
        $scope.team_full_name_lookup = $scope.teams.reduce((o, key) => Object.assign(o, {[key.abbr]: key.full_name}), {});
        // ...for team locations
        $scope.team_location_lookup = $scope.teams.reduce((o, key) => Object.assign(o, {[key.abbr]: key.location}), {});
    });

    $scope.model = {
        team: $routeParams.team,
        // attributes to use ascending sort order per default 
        ascendingAttrs: [
            'opp_team', 'arena', 'coach', 'opp_coach', 'date', 'ref_1',
            'ref_2', 'lma_1', 'lma_2', 'round']
    }

    $scope.changeTable = function () {
        if ($scope.tableSelect === 'basic_game_by_game') {
            $scope.sortCriterion = 'date';
            $scope.statsSortDescending = false;
        } else if ($scope.tableSelect === 'game_refs') {
            $scope.sortCriterion = 'date';
            $scope.statsSortDescending = false;
        }
    };

    $scope.setSortOrder = function(sortCriterion, oldSortCriterion, oldStatsSortDescending) {
        return svc.setSortOrder(sortCriterion, oldSortCriterion, oldStatsSortDescending, $scope.model.ascendingAttrs);
    };

    $scope.setTextColor = function(goals, opp_goals) {
        if (goals > opp_goals) {
            return " green";
        }
        else if (opp_goals > goals) {
            return " red"
        }
        else {
            return ""
        }
    };

    // get standings position through specified game date
    $scope.getStandingsPositionThroughDate = function(cutoff_date) {

        cutoff_date = moment(cutoff_date);

        // creating associative array to contain teams' points, goal difference and goals scored
        var team_points_log = $scope.teams.reduce(
            (o, key) => Object.assign(o, {[key.abbr]: {'team_id': key.id, 'team_abbr': key.abbr, 'pts': 0, 'gdiff': 0, 'gf': 0}}), {});

        // looking at each item containing team game stats
        for (var i = 0; i < $scope.team_stats.length; i++)
        {
            game_date = moment($scope.team_stats[i]['game_date']);
            // bailing out if current game date is beyond specified cutoff date
            if (game_date > cutoff_date)
            {
                break;
            }
            // TODO: check whether current game date is in date fiter interval
            // aggregating points, goal difference and goals scored
            team_points_log[$scope.team_stats[i]['team']]['pts'] += $scope.team_stats[i]['points'];
            team_points_log[$scope.team_stats[i]['team']]['gf'] += $scope.team_stats[i]['goals'];
            team_points_log[$scope.team_stats[i]['team']]['gdiff'] += ($scope.team_stats[i]['goals'] - $scope.team_stats[i]['opp_goals']);
        }

        // converting team points log to an actual array
        team_table = Object.keys(team_points_log).map(function(key) {
            return {
                'team_id': team_points_log[key].id,
                'team': key,
                'pts': team_points_log[key].pts,
                'gdiff': team_points_log[key].gdiff,
                'gf': team_points_log[key].gf};
        });

        // sorting team table
        team_table.sort(function(b, a){
            if (a.pts == b.pts)
            {
                if (a.gdiff == b.gdiff)
                {
                    return a.gf - b.gf;
                }
                return a.gdiff - b.gdiff;
            }

            return a.pts - b.pts;
        });

        // returning actual table position of current team in sorted rankings
        return team_table.map(function(e) { return e.team}).indexOf($scope.currentTeam) + 1;
    };

    $scope.dayFilter = function (a) {
        date_to_test = moment(a.game_date);
        if (ctrl.fromDate && ctrl.toDate) {
            if ((date_to_test >= ctrl.fromDate.startOf('day')) && (date_to_test <= ctrl.toDate.startOf('day'))) {
                return true;
            } else {
                return false;
            }
        } else if (ctrl.fromDate) {
            if (date_to_test >= ctrl.fromDate.startOf('day')) {
                return true;
            } else {
                return false;
            }
        } else if (ctrl.toDate) {
            if (date_to_test <= ctrl.toDate.startOf('day')) {
                return true;
            } else {
                return false;
            }
        } else {
            return true;
        }
    };

    $scope.changeTeam = function() {
        $location.path('/team_profile/' + $scope.model.team);
    };

});

app.controller('teamController', function($scope, $http, svc) {

    var ctrl = this;
    // setting default table selection and sort criterion/order
    $scope.tableSelect = 'standings';
    $scope.isStandingsView = true;
    $scope.sortCriterion = 'points';
    $scope.statsSortDescending = true;

    // retrieving column headers (and abbreviations + explanations)
    $http.get('./js/team_stats_columns.json').then(function (res) {
        $scope.stats_cols = res.data;
    });
    // retrieving teams
    $http.get('./js/teams.json').then(function (res) {
        $scope.teams = res.data;
        // creating lookup structures...
        // ...for team locations
        $scope.team_location_lookup = $scope.teams.reduce((o, key) => Object.assign(o, {[key.abbr]: key.location}), {});
    });

    $scope.$watch('ctrl.fromDate', function() {
        if ($scope.team_stats) {
            $scope.filtered_team_stats = $scope.filter_stats($scope.team_stats);
        }
    });

    $scope.$watch('ctrl.toDate', function() {
        if ($scope.team_stats) {
            $scope.filtered_team_stats = $scope.filter_stats($scope.team_stats);
        }
    });

    $scope.$watch('situationSelect', function() {
        if ($scope.team_stats) {
            $scope.filtered_team_stats = $scope.filter_stats($scope.team_stats);
        }
    });

    $scope.$watch('homeAwaySelect', function() {
        if ($scope.team_stats) {
            $scope.filtered_team_stats = $scope.filter_stats($scope.team_stats);
        }
    });

    $scope.stats_to_aggregate = [
        'games_played', 'score', 'opp_score', 'goals', 'opp_goals',
        'w', 'rw', 'ow', 'sw', 'l', 'rl', 'ol', 'sl', 'points', 'goals_1',
        'opp_goals_1', 'goals_2', 'opp_goals_2', 'goals_3', 'opp_goals_3',
        'shots', 'shots_on_goal', 'shots_missed', 'shots_blocked',
        'opp_shots', 'opp_shots_on_goal', 'opp_shots_missed',
        'opp_shots_blocked', 'saves', 'opp_saves', 'pim', 'pp_time',
        'pp_opps', 'pp_goals', 'opp_pim', 'opp_pp_time', 'opp_pp_opps',
        'opp_pp_goals', 'sh_opps', 'sh_goals', 'opp_sh_opps', 'opp_sh_goals',
        'faceoffs_won', 'faceoffs_lost', 'faceoffs', 'sl_sh', 'lf_sh', 'rg_sh',
        'bl_sh', 'sl_og', 'lf_og', 'rg_og', 'bl_og', 'sl_sh_a', 'lf_sh_a',
        'rg_sh_a', 'bl_sh_a', 'sl_og_a', 'lf_og_a', 'rg_og_a', 'bl_og_a' 
    ]

    // loading stats from external json file
    $http.get('data/del_team_game_stats.json').then(function (res) {
        $scope.last_modified = res.data[0];
        $scope.team_stats = res.data[1];
        $scope.filtered_team_stats = $scope.filter_stats($scope.team_stats);
    });


    $scope.filter_stats = function (stats) {
        filtered_team_stats = {};
        if ($scope.team_stats === undefined)
            return filtered_team_stats;
        $scope.team_stats.forEach(element => {
            date_to_test = moment(element.game_date);
            team = element['team'];
            if (!filtered_team_stats[team]) {
                filtered_team_stats[team] = {};
                filtered_team_stats[team]['team'] = team;
                $scope.stats_to_aggregate.forEach(category => {
                    filtered_team_stats[team][category] = 0;
                });
            }
            var is_filtered = false;
            if (ctrl.fromDate && ctrl.toDate) {
                if ((date_to_test >= ctrl.fromDate.startOf('day')) && (date_to_test <= ctrl.toDate.startOf('day'))) {
                    if ($scope.homeAwaySelect && $scope.situationSelect) {
                        if ($scope.homeAwaySelect === element.home_road && element[$scope.situationSelect])
                            is_filtered = true;
                    } else if ($scope.homeAwaySelect) {
                        if ($scope.homeAwaySelect === element.home_road)
                            is_filtered = true;
                    } else if ($scope.situationSelect) {
                        if (element[$scope.situationSelect])
                            is_filtered = true;
                    } else {
                        is_filtered = true;
                    }
                }
            } else if (ctrl.fromDate) {
                if (date_to_test >= ctrl.fromDate.startOf('day')) {
                    if ($scope.homeAwaySelect && $scope.situationSelect) {
                        if ($scope.homeAwaySelect === element.home_road && element[$scope.situationSelect])
                            is_filtered = true;
                    } else if ($scope.homeAwaySelect) {
                        if ($scope.homeAwaySelect === element.home_road)
                            is_filtered = true;
                    } else if ($scope.situationSelect) {
                        if (element[$scope.situationSelect])
                            is_filtered = true;
                    } else {
                        is_filtered = true;
                    }
                }
            } else if (ctrl.toDate) {
                if (date_to_test <= ctrl.toDate.startOf('day')) {
                    if ($scope.homeAwaySelect && $scope.situationSelect) {
                        if ($scope.homeAwaySelect === element.home_road && element[$scope.situationSelect])
                            is_filtered = true;
                    } else if ($scope.homeAwaySelect) {
                        if ($scope.homeAwaySelect === element.home_road)
                            is_filtered = true;
                    } else if ($scope.situationSelect) {
                        if (element[$scope.situationSelect])
                            is_filtered = true;
                    } else {
                        is_filtered = true;
                    }
                }
            } else {
                if ($scope.homeAwaySelect && $scope.situationSelect) {
                    if ($scope.homeAwaySelect === element.home_road && element[$scope.situationSelect])
                        is_filtered = true;
                }
                else if ($scope.situationSelect) {
                    if (element[$scope.situationSelect])
                        is_filtered = true;
                }
                else if ($scope.homeAwaySelect) {
                    if ($scope.homeAwaySelect === element.home_road)
                        is_filtered = true;
                } else {
                    is_filtered = true;
                }
        }
            if (is_filtered) {
                $scope.stats_to_aggregate.forEach(category => {
                    filtered_team_stats[team][category] += element[category];
                })
            }
        });
        filtered_team_stats = Object.values(filtered_team_stats);

        filtered_team_stats.forEach(element => {
            // calculating score and goal differentials
            element['score_diff'] = element['score'] - element['opp_score'];
            element['goals_diff'] = element['goals'] - element['ow'] - element['opp_goals'] + element['ol'];
            element['goals_diff_1'] = element['goals_1'] - element['opp_goals_1'];
            element['goals_diff_2'] = element['goals_2'] - element['opp_goals_2'];
            element['goals_diff_3'] = element['goals_3'] - element['opp_goals_3'];
            // calculating points percentage
            if (element['games_played']) {
                element['pt_pctg'] = parseFloat((element['points'] / (element['games_played'] * 3.) * 100).toFixed(2));
            } else {
                element['pt_pctg'] = parseFloat((0).toFixed(2));
            }
            // calculating shot zone percentages
            if (element['shots']) {
                element['sl_p'] = parseFloat(((element['sl_sh'] / element['shots']) * 100).toFixed(2));
                element['lf_p'] = parseFloat(((element['lf_sh'] / element['shots']) * 100).toFixed(2));
                element['rg_p'] = parseFloat(((element['rg_sh'] / element['shots']) * 100).toFixed(2));
                element['bl_p'] = parseFloat(((element['bl_sh'] / element['shots']) * 100).toFixed(2));
            } else {
                element['sl_p'] = parseFloat((0).toFixed(2));
                element['lf_p'] = parseFloat((0).toFixed(2));
                element['rg_p'] = parseFloat((0).toFixed(2));
                element['bl_p'] = parseFloat((0).toFixed(2));
            }
            // calculating zone percentages for shots against
            if (element['opp_shots']) {
                element['sl_p_a'] = parseFloat(((element['sl_sh_a'] / element['opp_shots']) * 100).toFixed(2));
                element['lf_p_a'] = parseFloat(((element['lf_sh_a'] / element['opp_shots']) * 100).toFixed(2));
                element['rg_p_a'] = parseFloat(((element['rg_sh_a'] / element['opp_shots']) * 100).toFixed(2));
                element['bl_p_a'] = parseFloat(((element['bl_sh_a'] / element['opp_shots']) * 100).toFixed(2));
            } else {
                element['sl_p_a'] = parseFloat((0).toFixed(2));
                element['lf_p_a'] = parseFloat((0).toFixed(2));
                element['rg_p_a'] = parseFloat((0).toFixed(2));
                element['bl_p_a'] = parseFloat((0).toFixed(2));
            }
            // calculating shooting, save and zone percentages for shots on goal
            if (element['shots_on_goal']) {
                element['shot_pctg'] = parseFloat(((element['goals'] / element['shots_on_goal']) * 100).toFixed(2));
                element['opp_save_pctg'] = parseFloat(((element['opp_saves'] / element['shots_on_goal']) * 100).toFixed(2));
                element['sl_og_p'] = parseFloat(((element['sl_og'] / element['shots_on_goal']) * 100).toFixed(2));
                element['lf_og_p'] = parseFloat(((element['lf_og'] / element['shots_on_goal']) * 100).toFixed(2));
                element['rg_og_p'] = parseFloat(((element['rg_og'] / element['shots_on_goal']) * 100).toFixed(2));
                element['bl_og_p'] = parseFloat(((element['bl_og'] / element['shots_on_goal']) * 100).toFixed(2));
            } else {
                element['shot_pct'] = parseFloat((0).toFixed(2));
                element['opp_save_pct'] = parseFloat((0).toFixed(2));
                element['sl_og_p'] = parseFloat((0).toFixed(2));
                element['lf_og_p'] = parseFloat((0).toFixed(2));
                element['rg_og_p'] = parseFloat((0).toFixed(2));
                element['bl_og_p'] = parseFloat((0).toFixed(2));
            }
            // calculating opponent shooting, save and zone percentages for shots on goal against
            if (element['opp_shots_on_goal']) {
                element['opp_shot_pctg'] = parseFloat(((element['opp_goals'] / element['opp_shots_on_goal']) * 100).toFixed(2));
                element['save_pctg'] = parseFloat(((element['saves'] / element['opp_shots_on_goal']) * 100).toFixed(2));
                element['sl_og_p_a'] = parseFloat(((element['sl_og_a'] / element['opp_shots_on_goal']) * 100).toFixed(2));
                element['lf_og_p_a'] = parseFloat(((element['lf_og_a'] / element['opp_shots_on_goal']) * 100).toFixed(2));
                element['rg_og_p_a'] = parseFloat(((element['rg_og_a'] / element['opp_shots_on_goal']) * 100).toFixed(2));
                element['bl_og_p_a'] = parseFloat(((element['bl_og_a'] / element['opp_shots_on_goal']) * 100).toFixed(2));
            } else {
                element['opp_shot_pct'] = parseFloat((0).toFixed(2));
                element['save_pct'] = parseFloat((0).toFixed(2));
                element['sl_og_p_a'] = parseFloat((0).toFixed(2));
                element['lf_og_p_a'] = parseFloat((0).toFixed(2));
                element['rg_og_p_a'] = parseFloat((0).toFixed(2));
                element['bl_og_p_a'] = parseFloat((0).toFixed(2));
            }
            // calculating PDO
            element['pdo'] = parseFloat((parseFloat(element['shot_pctg']) + parseFloat(element['save_pctg'])).toFixed(2));
            element['opp_pdo'] = parseFloat((parseFloat(element['opp_shot_pctg']) + parseFloat(element['opp_save_pctg'])).toFixed(2));
            // calculating shots on goal for percentage
            if (element['shots_on_goal'] + element['opp_shots_on_goal']) {
                element['shot_for_pctg'] = parseFloat((element['shots_on_goal'] / (element['shots_on_goal'] + element['opp_shots_on_goal']) * 100).toFixed(2));
                element['opp_shot_for_pctg'] = parseFloat((element['opp_shots_on_goal'] / (element['shots_on_goal'] + element['opp_shots_on_goal']) * 100).toFixed(2));
            } else {
                element['shot_for_pctg'] = parseFloat((0).toFixed(2));
                element['opp_shot_for_pctg'] = parseFloat((0).toFixed(2));
            }
            // calculating unblocked shots (i.e. Fenwick) for percentage
            element['fenwick_events'] = element['shots_on_goal'] + element['shots_missed']; 
            element['opp_fenwick_events'] = element['opp_shots_on_goal'] + element['opp_shots_missed']; 
            if (element['fenwick_events'] + element['opp_fenwick_events']) {
                element['fenwick_for_pctg'] = parseFloat(((element['fenwick_events']) / (element['fenwick_events' ]+ element['opp_fenwick_events']) * 100).toFixed(2));
                element['opp_fenwick_for_pctg'] = parseFloat(((element['opp_fenwick_events']) / (element['fenwick_events' ]+ element['opp_fenwick_events']) * 100).toFixed(2));
            } else {
                element['fenwick_for_pctg'] = parseFloat((0).toFixed(2));
                element['opp_fenwick_for_pctg'] = parseFloat((0).toFixed(2));
            }
            // calculating shots (i.e. Corsi) for percentage
            if (element['shots'] + element['opp_shots']) {
                element['corsi_for_pctg'] = parseFloat((element['shots'] / (element['shots'] + element['opp_shots']) * 100).toFixed(2));
                element['opp_corsi_for_pctg'] = parseFloat((element['opp_shots'] / (element['shots'] + element['opp_shots']) * 100).toFixed(2));
            } else {
                element['corsi_for_pctg'] = parseFloat((0).toFixed(2));
                element['opp_corsi_for_pctg'] = parseFloat((0).toFixed(2));
            }
            // calculating power play percentage
            if (element['pp_opps']) {
                element['pp_pctg'] = parseFloat(((element['pp_goals'] / element['pp_opps']) * 100).toFixed(2));
            } else {
                element['pp_pctg'] = parseFloat((0).toFixed(2));
            }
            // calculating penalty killing percentage
            if (element['sh_opps']) {
                element['pk_pctg'] = parseFloat((100 - (element['opp_pp_goals'] / element['sh_opps']) * 100).toFixed(2));
            } else {
                element['pk_pctg'] = parseFloat((0).toFixed(2));
            }
            // calculating special teams goal differential and combined special team percentages
            element['pp_pk_gdiff'] = element['pp_goals'] + element['sh_goals'] - element['opp_pp_goals'] - element['opp_sh_goals']; 
            element['pp_pk_comb_pctg'] = element['pp_pctg'] + element['pk_pctg'];
            // calculating team faceoff percentage
            if (element['faceoffs']) {
                element['faceoff_pctg'] = parseFloat(((element['faceoffs_won'] / element['faceoffs']) * 100).toFixed(2));
            } else {
                element['faceoff_pctg'] = parseFloat((0).toFixed(2));
            }
            // calculating team penalty minutes per game
            if (element['games_played']) {
                element['pim_per_game'] = parseFloat((element['pim'] / element['games_played']).toFixed(2));
            } else {
                element['pim_per_game'] = parseFloat((0).toFixed(2));
            }
        });
        
        return filtered_team_stats;
    };

    $scope.changeTable = function () {
        if ($scope.tableSelect === 'standings') {
            if ($scope.situationSelect) {
                $scope.sortCriterion = 'pt_pctg';
            } else {
                $scope.sortCriterion = 'points';
            }
            $scope.statsSortDescending = true;
            $scope.isStandingsView = true;
        } else if ($scope.tableSelect === 'goal_stats') {
            $scope.sortCriterion = 'goals_diff';
            $scope.statsSortDescending = true;
            $scope.isStandingsView = false;
            $scope.situationSelect = undefined;
        } else if ($scope.tableSelect === 'shot_stats') {
            $scope.sortCriterion = 'shots_on_goal';
            $scope.statsSortDescending = true;
            $scope.isStandingsView = false;
            $scope.situationSelect = undefined;
        } else if ($scope.tableSelect === 'shot_shares') {
            $scope.sortCriterion = 'corsi_for_pctg';
            $scope.statsSortDescending = true;
            $scope.isStandingsView = false;
            $scope.situationSelect = undefined;
        } else if ($scope.tableSelect === 'special_team_stats') {
            $scope.sortCriterion = 'pp_pctg';
            $scope.statsSortDescending = true;
            $scope.isStandingsView = false;
            $scope.situationSelect = undefined;
        } else if ($scope.tableSelect === 'additional_stats') {
            $scope.sortCriterion = 'faceoff_pctg';
            $scope.statsSortDescending = true;
            $scope.isStandingsView = false;
            $scope.situationSelect = undefined;
        } else if ($scope.tableSelect === 'shot_zones') {
            $scope.sortCriterion = 'shots';
            $scope.statsSortDescending = true;
            $scope.isStandingsView = false;
            $scope.situationSelect = undefined;
        } else if ($scope.tableSelect === 'shot_on_goal_zones') {
            $scope.sortCriterion = 'shots_on_goal';
            $scope.statsSortDescending = true;
            $scope.isStandingsView = false;
            $scope.situationSelect = undefined;
        } else if ($scope.tableSelect === 'shot_zones_against') {
            $scope.sortCriterion = 'opp_shots';
            $scope.statsSortDescending = true;
            $scope.isStandingsView = false;
            $scope.situationSelect = undefined;
        } else if ($scope.tableSelect === 'shot_on_goal_zones_against') {
            $scope.sortCriterion = 'opp_shots_on_goal';
            $scope.statsSortDescending = true;
            $scope.isStandingsView = false;
            $scope.situationSelect = undefined;
        }
    };

    $scope.setSortOrder = function(sortCriterion, oldSortCriterion, oldStatsSortDescending) {
        return svc.setSortOrder(sortCriterion, oldSortCriterion, oldStatsSortDescending, ['team']);
    }

    $scope.setTextColor = function(goals, opp_goals) {
        if (goals > opp_goals) {
            return " green";
        }
        else if (opp_goals > goals) {
            return " red"
        }
        else {
            return ""
        }
    };

});

app.controller('plrController', function($scope, $http, $routeParams, $location, svc) {

    var ctrl = this;
    $scope.svc = svc;

    // retrieving column headers (and abbreviations + explanations)
    $http.get('./js/player_profile_columns.json').then(function (res) {
        $scope.stats_cols = res.data;
    });

    // retrieving players
    $http.get('./data/del_players.json').then(function (res) {
        $scope.players = res.data;
    });

    // loading stats from external json file
    $http.get('data/per_player/' + $routeParams.team + '_' + $routeParams.player_id + '.json').then(function (res) {
        $scope.player_stats = res.data;
        $scope.player_name = res.data[0].full_name;
        if ($scope.player_stats[0]['position'] == 'GK') {
            $scope.tableSelect = 'goalie_stats'
        } else {
            $scope.tableSelect = 'basic_game_by_game'
        }
    });

    // loading goalie stats
    $http.get('./data/del_goalie_game_stats.json').then(function (res) {
        $scope.goalie_stats = res.data;
    });

    $http.get('data/del_player_game_stats_aggregated.json').then(function (res) {
        $scope.all_players = res.data[1];
    });

    $scope.model = {
        team: $routeParams.team,
        new_team: $routeParams.team,
        player_id: $routeParams.player_id,
        new_player_id: $routeParams.player_id,
        countries: {
            'GER': 'de', 'CAN': 'ca', 'SWE': 'se', 'USA': 'us', 'FIN': 'fi',
            'ITA': 'it', 'NOR': 'no', 'FRA': 'fr', 'LVA': 'lv', 'SVK': 'sk',
            'DNK': 'dk', 'RUS': 'ru', 'SVN': 'si', 'HUN': 'hu', 'SLO': 'si',
        },
        full_teams: [
            {'abbr': 'AEV', 'url_name': 'augsburger-panther', 'full_name': 'Augsburger Panther'},
            {'abbr': 'EBB', 'url_name': 'eisbaeren-berlin', 'full_name': 'Eisbären Berlin'},
            {'abbr': 'BHV', 'url_name': 'pinguins-bremerhaven', 'full_name': 'Pinguins Bremerhaven'},
            {'abbr': 'DEG', 'url_name': 'duesseldorfer-eg', 'full_name': 'Düsseldorfer EG'},
            {'abbr': 'ING', 'url_name': 'erc-ingolstadt', 'full_name': 'ERC Ingolstadt'},
            {'abbr': 'IEC', 'url_name': 'iserlohn-roosters', 'full_name': 'Iserlohn Roosters'},
            {'abbr': 'KEC', 'url_name': 'koelner-haie', 'full_name': 'Kölner Haie'},
            {'abbr': 'KEV', 'url_name': 'krefeld-pinguine', 'full_name': 'Krefeld Pinguine'},
            {'abbr': 'MAN', 'url_name': 'adler-mannheim', 'full_name': 'Adler Mannheim'},
            {'abbr': 'RBM', 'url_name': 'ehc-red-bull-muenchen', 'full_name': 'EHC Red Bull München'},
            {'abbr': 'NIT', 'url_name': 'thomas-sabo-ice-tigers', 'full_name': 'Thomas Sabo Ice Tigers'},
            {'abbr': 'SWW', 'url_name': 'schwenninger-wild-wings', 'full_name': 'Schwenninger Wild Wings'},
            {'abbr': 'STR', 'url_name': 'straubing-tigers', 'full_name': 'Straubing Tigers'},
            {'abbr': 'WOB', 'url_name': 'grizzlys-wolfsburg', 'full_name': 'Grizzlys Wolfsburg'},
        ]
    }

    $scope.team_lookup = $scope.model.full_teams.reduce((o, key) => Object.assign(o, {[key.abbr]: key.url_name}), {});

    $scope.sortCriterion = 'game_date';
    $scope.statsSortDescending = true;

    $scope.setSortOrder = function(sortCriterion, oldSortCriterion, oldStatsSortDescending) {
        return svc.setSortOrder(sortCriterion, oldSortCriterion, oldStatsSortDescending, ['round', 'opp_team']);
    }

    $scope.getTotal = function(attribute) {
        if ($scope.player_stats === undefined) {
            return;
        }
        var total = 0;
        for(var i = 0; i < $scope.player_stats.length; i++){
            total += $scope.player_stats[i][attribute];
        }
        return total;
    }

    $scope.goalieFilter = function(a) {
        if (!a['games_played']) {
            return false;
        }
        if (a['goalie_id'] == $routeParams.player_id) {
            return true;
        } else {
            return false;
        }
    }

    $scope.dayFilter = function (a) {
        date_to_test = moment(a.game_date);
        if (ctrl.fromDate && ctrl.toDate) {
            if ((date_to_test >= ctrl.fromDate.startOf('day')) && (date_to_test <= ctrl.toDate.startOf('day'))) {
                return true;
            } else {
                return false;
            }
        } else if (ctrl.fromDate) {
            if (date_to_test >= ctrl.fromDate.startOf('day')) {
                return true;
            } else {
                return false;
            }
        } else if (ctrl.toDate) {
            if (date_to_test <= ctrl.toDate.startOf('day')) {
                return true;
            } else {
                return false;
            }
        } else {
            return true;
        }
    };


    $scope.setTextColor = function(score, opp_score) {
        if (score > opp_score) {
            return " green";
        }
        else if (opp_score > score) {
            return " red"
        }
        else {
            return ""
        }
    };

    $scope.changePlayer = function() {
        $scope.model.player_id = $scope.model.new_player_id;
        $location.path('/player_profile/' + $scope.model.new_team + '/' + $scope.model.player_id);
    };


});

app.controller('mainController', function ($scope, $http, svc) {

        // default table selection and sort criterion for skater page
        $scope.tableSelect = 'basic_stats';
        $scope.sortCriterion = 'points';
        // default sort order is descending
        $scope.statsSortDescending = true;
        $scope.showOnlyU23 = false;
    
        $scope.ascendingAttrs = [
            'last_name', 'team', 'position', 'shoots',
            'date_of_birth', 'iso_country'
        ];

        // loading stats from external json file
        $http.get('data/del_player_game_stats_aggregated.json').then(function (res) {
            $scope.last_modified = res.data[0];
            $scope.stats = res.data[1];
        });

        // retrieving column headers (and abbreviations + explanations)
        $http.get('./js/player_stats_columns.json').then(function (res) {
            $scope.stats_cols = res.data;
        });

        // default filter values
        $scope.nameFilter = ''; // empty name filter
        $scope.teamFilter = ''; // empty name filter

        $scope.changeTable = function () {
            if ($scope.tableSelect === 'player_information') {
                $scope.sortCriterion = 'last_name';
                $scope.statsSortDescending = false;
            } else if ($scope.tableSelect === 'basic_stats') {
                $scope.sortCriterion = 'points';
                $scope.statsSortDescending = true;
            } else if ($scope.tableSelect === 'per_game_stats') {
                $scope.sortCriterion = 'points_per_game';
                $scope.statsSortDescending = true;
            } else if ($scope.tableSelect === 'time_on_ice_shift_stats') {
                $scope.sortCriterion = 'time_on_ice_seconds';
                $scope.statsSortDescending = true;
            } else if ($scope.tableSelect === 'power_play_stats') {
                $scope.sortCriterion = 'time_on_ice_pp_seconds';
                $scope.statsSortDescending = true;
            } else if ($scope.tableSelect === 'penalty_stats') {
                $scope.sortCriterion = 'pim_from_events';
                $scope.statsSortDescending = true;
            } else if ($scope.tableSelect === 'additional_stats') {
                $scope.sortCriterion = 'faceoff_pctg';
                $scope.statsSortDescending = true;
            } else if ($scope.tableSelect === 'per_60_stats') {
                $scope.sortCriterion = 'points_per_60';
                $scope.statsSortDescending = true;
            }
        };

        $scope.setSortOrder = function(sortCriterion, oldSortCriterion, oldStatsSortDescending) {
            return svc.setSortOrder(sortCriterion, oldSortCriterion, oldStatsSortDescending, $scope.ascendingAttrs);
        };

        $scope.greaterThan = function (prop, val) {
            return function (item) {
                return item[prop] > val;
            }
        }

        $scope.u23Filter = function(a) {
            if (!$scope.showOnlyU23)
                return true;
            if ($scope.showOnlyU23 && a.u23) {
                return true;
            } else {
                return false;
            }
        };

        $scope.minimumAgeFilter = function (a) {
            if ($scope.minimumAge) {
                if (a.age < $scope.minimumAge) {
                    return false;
                } else {
                    return true;
                }
            } else {
                return true;
            }
        }

        $scope.maximumAgeFilter = function (a) {
            if ($scope.maximumAge) {
                if (a.age > $scope.maximumAge) {
                    return false;
                } else {
                    return true;
                }
            } else {
                return true;
            }
        }
});