app.controller('plrCareerController', function ($scope, $http, $routeParams, svc) {

    $scope.svc = svc;
    $scope.player_id = $routeParams.player_id;
    $scope.table_select = 'skater_career_stats';

    // retrieving column headers (and abbreviations + explanations)
    $http.get('./js/player_career_columns.json').then(function (res) {
        $scope.stats_cols = res.data;
    });

    // loading stats from external json file
    $http.get('data/career_stats/per_player/' + $scope.player_id + '.json').then(function (res) {
        $scope.player_stats = res.data;
        $scope.player_first_name = res.data.first_name;
        $scope.player_last_name = res.data.last_name;
        if (res.data.position == 'GK') {
            $scope.table_select = 'goalie_career_stats';
        }
        $scope.seasons = res.data.seasons;
    });

});