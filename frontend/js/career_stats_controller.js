app.controller('careerStatsController', function ($scope, $http, $routeParams, svc) {
    $scope.svc = svc;
    $scope.table_select = 'career_stats_skaters';
    $scope.season_type = 'ALL';
    $scope.sortConfig = {
        'sortKey': 'pts',
        'sortCriteria': ['pts', 'ptspg', 'g', '-gp'],
        'sortDescending': true
    }
    $scope.sortCriteria = {
        "gp": ['gp', 'pts', 'g'],
        "pts": ['pts', 'ptspg', 'g', '-gp'],
        "ptspg": ['ptspg', '-gp', 'sog'],
        "pim": ['pim', '-gp'],
        "w": ['w', '-gp'],
        "l": ['l', 'gp'],
        "ga": ['ga', 'gp'],
        "teams_cnt": ['teams_cnt', '-teams[0]'],
        "ppg": ['ppg', '-gp'],
        "sog": ['sog', '-gp'],
        "sh_pctg": ['sh_pctg', 'sog', '-gp']
    };

    // retrieving column headers (and abbreviations + explanations)
    $http.get('./js/career_stats_columns.json').then(function (res) {
        $scope.stats_cols = res.data;
    });

    $http.get('./js/teams.json').then(function (res) {
        // only retaining teams that are valid for current season
        $scope.teams = res.data;
        $scope.team_full_name_lookup = $scope.teams.reduce((o, key) => Object.assign(o, {[key.abbr]: key.full_name}), {});
    });
 
    // loading stats from external json file
    $http.get('data/career_stats/career_stats.json').then(function (res) {
        $scope.player_stats = res.data;
        var all_seasons = new Set();
        var all_teams = new Set()
        $scope.player_stats.forEach(element => {
            element['seasons'].forEach(season_stat_line => {
                all_seasons.add(season_stat_line['season']);
                all_teams.add(season_stat_line['team']);
            })
        });
        $scope.min_season = Math.min(...all_seasons);
        $scope.max_season = Math.max(...all_seasons);
        $scope.from_season = $scope.min_season;
        $scope.to_season = $scope.max_season;
        $scope.all_teams = [...all_teams];
    });

    $scope.$watchGroup(['from_season', 'to_season', 'season_type', 'team', 'position'], function() {
        if ($scope.player_stats) {
            $scope.filtered_season_player_stats = $scope.filterCareerStats();
        }
    }, true);

    $scope.to_aggregate = ['gp', 'g', 'a', 'pts', 'plus_minus', 'pim', 'ppg', 'shg', 'gwg', 'sog', 'toi', 'w', 'l', 'sa', 'ga', 'so'];

    $scope.filterCareerStats = function() {
        filtered_career_stats = [];
        if ($scope.player_stats === undefined)
            return filtered_career_stats;
        $scope.player_stats.forEach(player => {
            // setting up filtered cumulated stat line for current player
            filtered_stat_line = {
                'player_id': player['player_id'],
                'first_name': player['first_name'],
                'last_name': player['last_name'],
                'position': player['position'],
                'sh_pctg': 0.0,
                'sv_pctg': 0.0,
                'gpg': 0.0,
                'apg': 0.0,
                'ptspg': 0.0,
                'teams': new Set()
            };
            $scope.to_aggregate.forEach(category => {
                filtered_stat_line[category] = 0;
            })
            player['seasons'].forEach(season_stat_line => {
                in_season_range = false;
                in_season_types = false;
                is_selected_team = false;
                is_selected_position = false;

                // checking if current stat line is from a selected season
                if (season_stat_line['season'] >= $scope.from_season && season_stat_line['season'] <= $scope.to_season)
                    in_season_range = true;
                // checking if current stat line is of a selected season type
                if ($scope.season_type == 'ALL') {
                    in_season_types = true;
                } else {
                    if ($scope.season_type == season_stat_line['season_type'])
                        in_season_types = true;
                };
                // checking if current stat line is for the selected team
                if (!$scope.team) {
                    is_selected_team = true;
                } else {
                    if (season_stat_line['team'] == $scope.team)
                        is_selected_team = true;
                };
                // checking if current stat line is by a selected position
                // TODO: move outside of this loop
                if (!$scope.position) {
                    is_selected_position = true;
                } else {
                    if (player['position'] == $scope.position)
                        is_selected_position = true;
                }
                // finally aggregating values of all season stat lines that have been filtered
                if (in_season_range && in_season_types && is_selected_team && is_selected_position) {
                    filtered_stat_line['teams'].add(season_stat_line['team']);
                    $scope.to_aggregate.forEach(category => {
                        filtered_stat_line[category] += season_stat_line[category];
                    });
                }
            });
            // calculating shooting percentage
            if (filtered_stat_line['sog'])
                filtered_stat_line['sh_pctg'] = filtered_stat_line['g'] / filtered_stat_line['sog'] * 100.;
            // calculating save percentage
            if (filtered_stat_line['sa'])
                filtered_stat_line['sv_pctg'] = 100 - (filtered_stat_line['ga'] / filtered_stat_line['sa'] * 100.);
            // calculating goals against average
            if (filtered_stat_line['toi'])
                filtered_stat_line['gaa'] = filtered_stat_line['ga'] * 3600. / filtered_stat_line['toi'];
            // calculating per-game statistics
            if (filtered_stat_line['gp']) {
                filtered_stat_line['gpg'] = filtered_stat_line['g'] / filtered_stat_line['gp'];
                filtered_stat_line['apg'] = filtered_stat_line['a'] / filtered_stat_line['gp'];
                filtered_stat_line['ptspg'] = filtered_stat_line['pts'] / filtered_stat_line['gp'];
            };
            filtered_stat_line['teams'] = Array.from(filtered_stat_line['teams']);
            filtered_stat_line['teams_cnt'] = filtered_stat_line['teams'].length;
            filtered_career_stats.push(filtered_stat_line);
        });
        return filtered_career_stats;
    };

    $scope.hasCareerFilter = function(a) {
        if (!a['career']['all']) {
            return false;
        }
        return true;
    };

    $scope.setSortOrder = function(sortKey, oldSortConfig) {
        return svc.setSortOrder2(sortKey, oldSortConfig, $scope.sortCriteria, ['last_name']);
    };

    $scope.greaterThanFilter = function (prop, val) {
        return function (item) {
            return item[prop] > val;
        }
    }

});
