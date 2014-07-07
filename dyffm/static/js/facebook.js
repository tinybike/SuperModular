window.fbAsyncInit = function () {
    var graph_url, picture_large;
    graph_url = window.location.protocol + '//graph.facebook.com/';
    picture_large = '/picture?type=large';
    FB.init({
        appId      : '807459499283753',
        status     : true, // check login status
        cookie     : true, // enable cookies
        xfbml      : true  // parse XFBML
    });
    // FB Graph API reference:
    // https://developers.facebook.com/docs/graph-api/reference/v2.0
    FB.Event.subscribe('auth.authResponseChange', function (res) {
        var uid, accessToken, getToken;
        if (res.status === 'connected') {
            uid = res.authResponse.userID;
            accessToken = res.authResponse.accessToken;
            getToken = '//graph.facebook.com/oauth/access_token?client_id=' + uid + '&client_secret=' + accessToken + '&grant_type=client_credentials';
            if (window.page === 'bar') {
                $('#awesomer-error').hide();
                $('#awesomer-game').show();
            }
            // Get user info + friend list from FB graph
            FB.api('/me', function (response) {
                if (window.socket && !window.fb_connect) {
                    socket.emit('facebook-profile-data', {
                        'id': response.id,
                        'username': response.username || '',
                        'first_name': response.first_name,
                        'last_name': response.last_name,
                        'gender': response.gender,
                        'location_id': response.location.id,
                        'location_name': response.location.name,
                        'bio': response.bio,
                        'link': response.link,
                        'picture': graph_url + response.id + picture_large
                    });
                }
                if (window.page === 'bar') {
                    // Get FB friend list
                    FB.api('/me/friends', function (res) {
                        var select_left, select_right, url_left, url_right, max_index;
                        function load_pix() {
                            select_left = get_random_int(0, max_index);
                            do {
                                select_right = get_random_int(0, max_index)
                            } while (select_left === select_right);
                            id_left = res.data[select_left].id;
                            id_right = res.data[select_right].id;
                            url_left = graph_url + id_left + picture_large;
                            url_right = graph_url + id_right + picture_large;
                            name_left = res.data[select_left].name;
                            name_right = res.data[select_right].name;
                            $('#fb-friend-name-left').empty().append(
                                $('<a />')
                                    .attr('href', 'https://facebook.com/' + id_left)
                                    .append(
                                        $('<h2 />')
                                            .addClass('centered')
                                            .text(name_left)
                                    )
                            ).show();
                            $('#fb-friend-name-right').empty().append(
                                $('<a />')
                                    .attr('href', 'https://facebook.com/' + id_right)
                                    .append(
                                        $('<h2 />')
                                            .addClass('centered')
                                            .text(name_right)
                                    )
                            ).show();
                            $('#fb-friend-pic-left').empty().append(
                                $('<img />')
                                    .attr('src', url_left)
                                    .attr('alt', name_left)
                                    .attr('title', name_left)
                            ).click(function () {
                                socket.emit('select-pic', {
                                    target: id_left,
                                    untarget: id_right
                                });
                                load_pix();
                            }).show();
                            $('#fb-friend-pic-right').empty().append(
                                $('<img />')
                                    .attr('src', url_right)
                                    .attr('alt', name_right)
                                    .attr('title', name_right)
                            ).click(function () {
                                socket.emit('select-pic', {
                                    target: id_right,
                                    untarget: id_left
                                });
                                load_pix();
                            }).show();
                        }
                        // Record friend list + ids in database
                        socket.emit('record-facebook-friends', {
                            friends: res.data
                        });
                        // Select two random pics, make sure they're different
                        max_index = res.data.length - 1;
                        if (max_index > 1) {
                            load_pix();
                        }
                    });
                }
            });
        } else {
            if (window.page === 'bar') {
                $('#awesomer-game').hide();
                $('#awesomer-error').show();
            }
            FB.login();
        }
    });
    FB.getLoginStatus(function (res) {
        console.log('FB.getLoginStatus: ' + res.status);
        if (res.status !== 'connected' && window.page === 'bar') {
            $('#awesomer-game').hide();
            $('#awesomer-error').show();
        }
    });
};
// Load the Facebook SDK asynchronously
(function(d){
    var js, id = 'facebook-jssdk', ref = d.getElementsByTagName('script')[0];
    if (d.getElementById(id)) {return;}
    js = d.createElement('script'); js.id = id; js.async = true;
    js.src = "//connect.facebook.net/en_US/all.js";
    ref.parentNode.insertBefore(js, ref);
}(document));