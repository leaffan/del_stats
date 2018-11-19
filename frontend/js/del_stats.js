var app = angular.module('delStatsApp', ['ngRoute', 'moment-picker'])

app.config(['$routeProvider', function($routeProvider){
    $routeProvider
        .when('/home', {
            templateUrl: 'home.html',
        })
        .when('/del_stats', {
            templateUrl: 'stats.html',
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
        .otherwise({
            redirectTo: '/del_stats'
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

app.controller('teamController', function($scope, $http) {

    var ctrl = this;
    $scope.tableSelect = 'standings';
    $scope.sortCriterion = 'points';
    $scope.statsSortDescending = true;

    $scope.$watch('ctrl.fromDate', function() {
        // console.log("from fromdate watch: " + ctrl.fromDate);
        // console.log("from fromdate watch: " + $scope.team_stats);
        if ($scope.team_stats) {
            $scope.filtered_team_stats = $scope.filter_stats($scope.team_stats);
        }
    });

    $scope.$watch('ctrl.toDate', function() {
        // console.log("from todate watch: " + ctrl.toDate);
        // console.log("from todate watch: " + $scope.team_stats);
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
        // console.log("from filter:" + ctrl.fromDate);
        // console.log("from filter:" + ctrl.toDate);
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
                    is_filtered = true;
                }
            } else if (ctrl.fromDate) {
                if (date_to_test >= ctrl.fromDate.startOf('day')) {
                    is_filtered = true;
                }
            } else if (ctrl.toDate) {
                if (date_to_test <= ctrl.toDate.startOf('day')) {
                    is_filtered = true;
                }
            } else {
                is_filtered = true;
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
                element['win_pctg'] = (element['points'] / (element['games_played'] * 3.) * 100).toFixed(2);
            } else {
                element['win_pctg'] = (0).toFixed(2);
            }
            if (element['shots_on_goal']) {
                element['shot_pctg'] = ((element['goals'] / element['shots_on_goal']) * 100).toFixed(2);
                element['opp_save_pctg'] = ((element['opp_saves'] / element['shots_on_goal']) * 100).toFixed(2);
            } else {
                element['shot_pct'] = (0).toFixed(2);
                element['opp_save_pct'] = (0).toFixed(2);
            }
            if (element['opp_shots_on_goal']) {
                element['opp_shot_pctg'] = ((element['opp_goals'] / element['opp_shots_on_goal']) * 100).toFixed(2);
                element['save_pctg'] = ((element['saves'] / element['opp_shots_on_goal']) * 100).toFixed(2);
            } else {
                element['opp_shot_pct'] = (0).toFixed(2);
                element['save_pct'] = (0).toFixed(2);
            }
            element['pdo'] = (parseFloat(element['shot_pctg']) + parseFloat(element['save_pctg'])).toFixed(1);
            element['opp_pdo'] = (parseFloat(element['opp_shot_pctg']) + parseFloat(element['opp_save_pctg'])).toFixed(1);
        });
        
        console.log(filtered_team_stats);

        return filtered_team_stats;
    };

    $scope.changeTable = function () {
        if ($scope.tableSelect === 'standings') {
            $scope.sortCriterion = 'points';
            $scope.statsSortDescending = true;
        } else if ($scope.tableSelect === 'goal_statistics') {
            $scope.sortCriterion = 'goals_diff';
            $scope.statsSortDescending = true;
            console.log("from change: " + $scope.sortCriterion);
        }
    };

    // setting column sort order according to current and new sort criteria, and current sort order 
    $scope.setSortOrder = function (sortCriterion, oldSortCriterion, oldStatsSortDescending) {
        // if current criterion equals the new one
        if (oldSortCriterion === sortCriterion) {
            // just change sort direction
            return !oldStatsSortDescending;
        } else {
            // ascending for a few columns
            if (['team'].indexOf(sortCriterion) !== -1) {
                return false;
            } else {
                // otherwise descending sort order
                return true;
            }
        }
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

});

app.controller('plrController', function($scope, $http, $routeParams) {

    var ctrl = this;

    // loading stats from external json file
    $http.get('data/per_player/' + $routeParams.team + '_' + $routeParams.player_id + '.json').then(function (res) {
        $scope.player_stats = res.data;
        $scope.player_name = res.data[0].full_name;
    });

    $scope.model = {
        team: $routeParams.team,
        player_id: $routeParams.player_id,
        teams: {
            'AEV': 'augsburger-panther', 'KEC': 'koelner-haie',
            'RBM': 'ehc-red-bull-muenchen', 'IEC': 'iserlohn-roosters',
            'DEG': 'duesseldorfer-eg', 'SWW': 'schwenninger-wild-wings',
            'KEV': 'krefeld-pinguine', 'ING': 'erc-ingolstadt',
            'MAN': 'adler-mannheim', 'STR': 'straubing-tigers',
            'EBB': 'eisbaeren-berlin', 'NIT': 'thomas-sabo-ice-tigers',
            'WOB': 'grizzlys-wolfsburg', 'BHV': 'pinguins-bremerhaven'
        },
        countries: {
            'GER': 'de', 'CAN': 'ca', 'SWE': 'se', 'USA': 'us', 'FIN': 'fi',
            'ITA': 'it', 'NOR': 'no', 'FRA': 'fr', 'LVA': 'lv', 'SVK': 'sk',
            'DNK': 'dk', 'RUS': 'ru', 'SVN': 'si', 'HUN': 'hu', 'SLO': 'si',
        }
    }

    $scope.tableSelect = 'basic_game_by_game';
    $scope.sortCriterion = 'date';

    // setting column sort order according to current and new sort criteria, and current sort order 
    $scope.setSortOrder = function (sortCriterion, oldSortCriterion, oldStatsSortDescending) {
        // if current criterion equals the new one
        if (oldSortCriterion === sortCriterion) {
            // just change sort direction
            return !oldStatsSortDescending;
        } else {
            // ascending for a few columns
            if (['date', 'round', 'opp_team'].indexOf(sortCriterion) !== -1) {
                return false;
            } else {
                // otherwise descending sort order
                return true;
            }
        }
    };

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

    $scope.getFilteredTotal = function(list, attribute) {
        if ($scope.player_stats === undefined) {
            return;
        }
        var total = 0;
        for(var i = 0; i < list.length; i++){
            total += list[i][attribute];
        }
        return total;
    }

    $scope.formatTime = function(time_on_ice) {
        return Math.floor(time_on_ice / 60) + ":" + ('00' + (time_on_ice % 60)).slice(-2)
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

});

app.controller('mainController', function ($scope, $http) {

        // default table selection and sort criterion for skater page
        $scope.tableSelect = 'basic_stats';
        $scope.sortCriterion = 'points';
        // default sort order is descending
        $scope.statsSortDescending = true;
    
        // loading stats from external json file
        $http.get('data/del_player_game_stats_aggregated.json').then(function (res) {
            $scope.last_modified = res.data[0];
            $scope.stats = res.data[1];
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

        // setting column sort order according to current and new sort criteria, and current sort order 
        $scope.setSortOrder = function (sortCriterion, oldSortCriterion, oldStatsSortDescending) {
            // if current criterion equals the new one
            if (oldSortCriterion === sortCriterion) {
                // just change sort direction
                return !oldStatsSortDescending;
            } else {
                // ascending for a few columns
                if ([
                    'last_name', 'team', 'position', 'shoots',
                    'date_of_birth', 'iso_country'
                ].indexOf(sortCriterion) !== -1) {
                    return false;
                } else {
                    // otherwise descending sort order
                    return true;
                }
            }
        };

        $scope.greaterThan = function (prop, val) {
            return function (item) {
                return item[prop] > val;
            }
        }

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