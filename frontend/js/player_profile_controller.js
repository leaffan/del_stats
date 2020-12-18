app.controller('plrProfileController', function($scope, $http, $routeParams, $location, svc) {

    var ctrl = this;
    $scope.svc = svc;

    $scope.season = $routeParams.season;
    $scope.player_id = $routeParams.player_id;
    $scope.seasonTypeFilter = 'RS';
    $scope.fromRoundSelect = '1';
    $scope.shootoutParticipation = false;

    // retrieving column headers (and abbreviations + explanations)
    $http.get('./js/player_profile_columns.json').then(function (res) {
        $scope.stats_cols = res.data;
    });

    // retrieving players
    $http.get('./data/del_players.json').then(function (res) {
        $scope.players = res.data;
    });

    // retrieving current season's teams as well currently selected team and its colors
    $http.get('./js/teams.json').then(function (res) {
        $scope.all_teams = res.data.filter(team => team.valid_from <= $scope.season && team.valid_to >= $scope.season);
        $scope.team_lookup = $scope.all_teams.reduce((o, key) => Object.assign(o, {[key.abbr]: key.url_name}), {});
        $scope.currentTeam = $scope.all_teams.filter(team => team.abbr == $routeParams.team);
        $scope.colors = $scope.currentTeam[0].colors;
    });
    
    // loading stats from external json file
    $http.get('data/' + $scope.season + '/per_player/' + $routeParams.team + '_' + $routeParams.player_id + '.json').then(function (res) {
        $scope.player_stats = res.data;
        $scope.player_name = res.data[0].full_name;
        if ($scope.player_stats[0]['position'] == 'GK') {
            $scope.tableSelect = 'goalie_stats'
        } else {
            $scope.tableSelect = 'basic_game_by_game'
        }
        // retrieving maximum round played
        $scope.maxRoundPlayed = Math.max.apply(Math, $scope.player_stats.map(function(o) { return o.round; })).toString();
        // retrieving all weekdays a game was played by the current team
        $scope.weekdaysPlayed = [...new Set($scope.player_stats.map(item => item.weekday))].sort();
        // retrieving all months a game was played by the current team
        $scope.monthsPlayed = [...new Set($scope.player_stats.map(item => moment(item.game_date).month()))];
        // setting to round selection to maximum round played
        $scope.toRoundSelect = $scope.maxRoundPlayed;
        // retrieving all numbers a player used
        $scope.numbersWorn = [...new Set($scope.player_stats.map(item => item.no))].sort();
        // retrieving indication whether player took part in a shootout
        $scope.shootoutParticipationGames = $scope.player_stats.filter(item => item.so_attempts);
        if ($scope.shootoutParticipationGames.length > 0) {
            $scope.shootoutParticipation = true;
        }
    });

    // loading goalie stats
    $http.get('./data/'+ $scope.season + '/del_goalie_game_stats.json').then(function (res) {
        $scope.goalie_stats = res.data;
        $scope.goalie_so_stats = $scope.goalie_stats.filter(item => item.so_attempts_a);
    });

    $http.get('data/'+ $scope.season + '/del_player_game_stats_aggregated.json').then(function (res) {
        seen = [];
        $scope.all_players = []
        // de-duplicating array with players because they usually will appear with
        // both aggregated regular season and playoff statistics
        res.data[1].forEach(element => {
            // using a combination of player id and team abbreviation to account for players that
            // changed teams during the season
            player_team_key = element.player_id + '_' + element.team;
            if (!seen[player_team_key]) {
                $scope.all_players.push(element);
                seen[player_team_key] = true;
            }
        });
        // $scope.all_players = res.data[1];
    });

    $scope.model = {
        team: $routeParams.team,
        new_team: $routeParams.team,
        player_id: $routeParams.player_id,
        new_player_id: $routeParams.player_id
    }

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

    $scope.fromRoundFilter = function (a) {
        if ($scope.fromRoundSelect) {
            if (a.round >= $scope.fromRoundSelect) {
                return true;
            } else {
                return false;
            }
        } else {
            return true;
        }
    };

    $scope.toRoundFilter = function (a) {
        if ($scope.toRoundSelect) {
            if (a.round <= $scope.toRoundSelect) {
                return true;
            } else {
                return false;
            }
        } else {
            return true;
        }
    };

    $scope.weekdayFilter = function (a) {
        if ($scope.weekdaySelect) {
            if (a.weekday == $scope.weekdaySelect) {
                return true;
            } else {
                return false;
            }
        } else {
            return true;
        }
    };

    $scope.changeTeam = function() {
        $scope.filtered_players = $scope.all_players.filter(player => player.team == $scope.model.new_team);
        $scope.model.new_player_id = $scope.filtered_players[0].player_id;
        $location.path('/player_profile/' + $scope.season + '/' + $scope.model.new_team + '/' + $scope.model.new_player_id);
    }

    $scope.changePlayer = function() {
        $scope.model.player_id = $scope.model.new_player_id;
        $location.path('/player_profile/' + $scope.season + '/' + $scope.model.new_team + '/' + $scope.model.player_id);
    };

    $scope.changeTimespan = function() {
        if (!$scope.timespanSelect) {
            ctrl.fromDate = null;
            ctrl.toDate = null;
            return;
        }
        timespanSelect = parseInt($scope.timespanSelect) + 1;
        if (timespanSelect < 9) {
            season = parseInt($scope.season) + 1;
        } else {
            season = parseInt($scope.season);
        }
        ctrl.fromDate = moment(season + '-' + timespanSelect + '-1', 'YYYY-M-D');
        ctrl.toDate = moment(season + '-' + timespanSelect + '-1', 'YYYY-M-D').endOf('month');
    }

});
