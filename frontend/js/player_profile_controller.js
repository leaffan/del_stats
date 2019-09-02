app.controller('plrProfileController', function($scope, $http, $routeParams, $location, svc) {

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
        seen = [];
        $scope.all_players = []
        // de-duplicating array with players
        res.data[1].forEach(element => {
            if (!seen[element.player_id]) {
                $scope.all_players.push(element);
                seen[element.player_id] = true;
            }
        });
        // $scope.all_players = res.data[1];
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

    $scope.changePlayer = function() {
        $scope.model.player_id = $scope.model.new_player_id;
        $location.path('/player_profile/' + $scope.model.new_team + '/' + $scope.model.player_id);
    };
});
