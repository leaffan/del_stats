app.controller('homeController', function ($scope, $http, $cacheFactory) {

    // this is certainly not the way to do it but
    // I can't get this working as a function with season
    // as parameter (which then would be called from the HTML)
    $http.get('data/2020/del_player_game_stats_aggregated.json', {cache: true}).then(function (res) {
        var team_players = [...new Set(res.data[1].map(item => item.team + '/' + item.player_id))];
        $scope.random_team_player_2020 = team_players[Math.floor(Math.random() * team_players.length)];
    });
    $http.get('data/2019/del_player_game_stats_aggregated.json', {cache: true}).then(function (res) {
        var team_players = [...new Set(res.data[1].map(item => item.team + '/' + item.player_id))];
        $scope.random_team_player_2019 = team_players[Math.floor(Math.random() * team_players.length)];
    });
    $http.get('data/2018/del_player_game_stats_aggregated.json', {cache: true}).then(function (res) {
        var team_players = [...new Set(res.data[1].map(item => item.team + '/' + item.player_id))];
        $scope.random_team_player_2018 = team_players[Math.floor(Math.random() * team_players.length)];
    });

});