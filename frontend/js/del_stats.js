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
        getFilteredAccumulatedTotal: function(list, attribute, dataSource, to) {
            if (dataSource === undefined) {
                return
            }
            var total = 0;
            for(var i = list.length-1; i >= 0; i--){
                total += list[i][attribute];
                if (list[i]['round'] == to)
                {
                    return total;
                }
            }
            return total;
        },
        getFilteredAverageTotal: function(list, attribute, dataSource, to) {
            if (dataSource === undefined) {
                return
            }
            var total = 0;
            var cnt_data = 0;
            for(var i = list.length-1; i >= 0; i--){
                cnt_data++;
                total += list[i][attribute];
                if (list[i]['round'] == to)
                {
                    return total/cnt_data;
                }
            }
            return total/cnt_data;
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
            // console.log(value['team'] == $scope.currentTeam);
            return value['team'] == $scope.currentTeam;
        });
    });

    // retrieving column headers (and abbreviations + explanations)
    $http.get('./js/team_profile_columns.json').then(function (res) {
        $scope.stats_cols = res.data;
    });

    $scope.model = {
        team: $routeParams.team,
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
        ],
        ascendingAttrs: [
            'opp_team', 'arena', 'coach', 'opp_coach', 'date', 'ref_1',
            'ref_2', 'lma_1', 'lma_2', 'round']
    }

    $scope.team_lookup = $scope.model.full_teams.reduce((o, key) => Object.assign(o, {[key.abbr]: key.url_name}), {});
    $scope.team_full_name_lookup = $scope.model.full_teams.reduce((o, key) => Object.assign(o, {[key.abbr]: key.full_name}), {});

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
    $scope.sortCriterion = 'points';
    $scope.statsSortDescending = true;

    // retrieving column headers (and abbreviations + explanations)
    $http.get('./js/team_stats_columns.json').then(function (res) {
        $scope.stats_cols = res.data;
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
        'faceoffs_won', 'faceoffs_lost', 'faceoffs'
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
                    if ($scope.homeAwaySelect) {
                        if ($scope.homeAwaySelect === element.home_away)
                            is_filtered = true;
                    } else {
                        is_filtered = true;
                    }
                }
            } else if (ctrl.fromDate) {
                if (date_to_test >= ctrl.fromDate.startOf('day')) {
                    if ($scope.homeAwaySelect) {
                        if ($scope.homeAwaySelect === element.home_away)
                            is_filtered = true;
                    } else {
                        is_filtered = true;
                    }
                }
            } else if (ctrl.toDate) {
                if (date_to_test <= ctrl.toDate.startOf('day')) {
                    if ($scope.homeAwaySelect) {
                        if ($scope.homeAwaySelect === element.home_away)
                            is_filtered = true;
                    } else {
                        is_filtered = true;
                    }
                }
            } else {
                if ($scope.homeAwaySelect) {
                    if ($scope.homeAwaySelect === element.home_away)
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
            element['score_diff'] = element['score'] - element['opp_score'];
            element['goals_diff'] = element['goals'] - element['ow'] - element['opp_goals'] + element['ol'];
            element['goals_diff_1'] = element['goals_1'] - element['opp_goals_1'];
            element['goals_diff_2'] = element['goals_2'] - element['opp_goals_2'];
            element['goals_diff_3'] = element['goals_3'] - element['opp_goals_3'];
            if (element['games_played']) {
                element['pt_pctg'] = parseFloat((element['points'] / (element['games_played'] * 3.) * 100).toFixed(2));
            } else {
                element['pt_pctg'] = parseFloat((0).toFixed(2));
            }
            if (element['shots_on_goal']) {
                element['shot_pctg'] = parseFloat(((element['goals'] / element['shots_on_goal']) * 100).toFixed(2));
                element['opp_save_pctg'] = parseFloat(((element['opp_saves'] / element['shots_on_goal']) * 100).toFixed(2));
            } else {
                element['shot_pct'] = parseFloat((0).toFixed(2));
                element['opp_save_pct'] = parseFloat((0).toFixed(2));
            }
            if (element['opp_shots_on_goal']) {
                element['opp_shot_pctg'] = parseFloat(((element['opp_goals'] / element['opp_shots_on_goal']) * 100).toFixed(2));
                element['save_pctg'] = parseFloat(((element['saves'] / element['opp_shots_on_goal']) * 100).toFixed(2));
            } else {
                element['opp_shot_pct'] = parseFloat((0).toFixed(2));
                element['save_pct'] = parseFloat((0).toFixed(2));
            }
            element['pdo'] = parseFloat((parseFloat(element['shot_pctg']) + parseFloat(element['save_pctg'])).toFixed(2));
            element['opp_pdo'] = parseFloat((parseFloat(element['opp_shot_pctg']) + parseFloat(element['opp_save_pctg'])).toFixed(2));
            if (element['shots_on_goal'] + element['opp_shots_on_goal']) {
                element['shot_for_pctg'] = parseFloat((element['shots_on_goal'] / (element['shots_on_goal'] + element['opp_shots_on_goal']) * 100).toFixed(2));
                element['opp_shot_for_pctg'] = parseFloat((element['opp_shots_on_goal'] / (element['shots_on_goal'] + element['opp_shots_on_goal']) * 100).toFixed(2));
            } else {
                element['shot_for_pctg'] = parseFloat((0).toFixed(2));
                element['opp_shot_for_pctg'] = parseFloat((0).toFixed(2));
            }
            element['fenwick_events'] = element['shots_on_goal'] + element['shots_missed']; 
            element['opp_fenwick_events'] = element['opp_shots_on_goal'] + element['opp_shots_missed']; 
            if (element['fenwick_events'] + element['opp_fenwick_events']) {
                element['fenwick_for_pctg'] = parseFloat(((element['fenwick_events']) / (element['fenwick_events' ]+ element['opp_fenwick_events']) * 100).toFixed(2));
                element['opp_fenwick_for_pctg'] = parseFloat(((element['opp_fenwick_events']) / (element['fenwick_events' ]+ element['opp_fenwick_events']) * 100).toFixed(2));
            } else {
                element['fenwick_for_pctg'] = parseFloat((0).toFixed(2));
                element['opp_fenwick_for_pctg'] = parseFloat((0).toFixed(2));
            }
            if (element['shots'] + element['opp_shots']) {
                element['corsi_for_pctg'] = parseFloat((element['shots'] / (element['shots'] + element['opp_shots']) * 100).toFixed(2));
                element['opp_corsi_for_pctg'] = parseFloat((element['opp_shots'] / (element['shots'] + element['opp_shots']) * 100).toFixed(2));
            } else {
                element['corsi_for_pctg'] = parseFloat((0).toFixed(2));
                element['opp_corsi_for_pctg'] = parseFloat((0).toFixed(2));
            }
            if (element['pp_opps']) {
                element['pp_pctg'] = parseFloat(((element['pp_goals'] / element['pp_opps']) * 100).toFixed(2));
            } else {
                element['pp_pctg'] = parseFloat((0).toFixed(2));
            }
            if (element['sh_opps']) {
                element['pk_pctg'] = parseFloat((100 - (element['opp_pp_goals'] / element['sh_opps']) * 100).toFixed(2));
            } else {
                element['pk_pctg'] = parseFloat((0).toFixed(2));
            }
            element['pp_pk_gdiff'] = element['pp_goals'] + element['sh_goals'] - element['opp_pp_goals'] - element['opp_sh_goals']; 
            element['pp_pk_comb_pctg'] = element['pp_pctg'] + element['pk_pctg'];
            if (element['faceoffs']) {
                element['faceoff_pctg'] = parseFloat(((element['faceoffs_won'] / element['faceoffs']) * 100).toFixed(2));
            } else {
                element['faceoff_pctg'] = parseFloat((0).toFixed(2));
            }
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
            $scope.sortCriterion = 'points';
            $scope.statsSortDescending = true;
        } else if ($scope.tableSelect === 'goal_stats') {
            $scope.sortCriterion = 'goals_diff';
            $scope.statsSortDescending = true;
        } else if ($scope.tableSelect === 'shot_stats') {
            $scope.sortCriterion = 'shots_on_goal';
            $scope.statsSortDescending = true;
        } else if ($scope.tableSelect === 'shot_shares') {
            $scope.sortCriterion = 'corsi_for_pctg';
            $scope.statsSortDescending = true;
        } else if ($scope.tableSelect === 'special_team_stats') {
            $scope.sortCriterion = 'pp_pctg';
            $scope.statsSortDescending = true;
        } else if ($scope.tableSelect === 'additional_stats') {
            $scope.sortCriterion = 'faceoff_pctg';
            $scope.statsSortDescending = true;
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

    // loading stats from external json file
    $http.get('data/per_player/' + $routeParams.team + '_' + $routeParams.player_id + '.json').then(function (res) {
        $scope.player_stats = res.data;
        $scope.player_name = res.data[0].full_name;
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

    $scope.tableSelect = 'basic_game_by_game';
    $scope.sortCriterion = 'date';
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

    $scope.changePlrTeam = function() {
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