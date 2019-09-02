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
        // ...for playoff participation indicator
        $scope.team_playoff_lookup = $scope.teams.reduce((o, key) => Object.assign(o, {[key.abbr]: key.po}), {});
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
