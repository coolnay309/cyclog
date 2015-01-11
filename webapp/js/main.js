(function(){
    var sock = new SockJS('/sockjs');

    sock.onopen = function () {
        console.log('open');
    };

    sock.onmessage = function (event) {
        console.log('incoming', event.data.substr(0,60));

        var feedname;
        var feedId;
        var data = JSON.parse(event.data);
        switch (data[0]) {
            case "add":
                /** new feed available */
                feedname = data[1];
                feedId = "feed-" + feedname.replace(/\.|:/g,"-");

                // add feedname to list of currently available feeds
                $("#feeds-list").append('<li id="' + feedId + '" class="ui-widget-content" name="' + feedname + '">' + feedname + '</li>');
                break;
            case "remove":
                /** feed stopped */
                feedname = data[1];
                feedId = "feed-" + feedname.replace(/\.|:/g,"-");

                // remove feedname from list of currently available feeds and close related tab
                $("#" + feedId).remove();
                removeTab(feedname);
                break;
            default:
                /** new data came for a feed */
                feedname = data[0];
                var tabId = "tab-" + feedname.replace(/\.|:/g,"-");

                // add data to feed feedname
                var html = data[1].replace(/\r?\n/g, "<br />");
                $("#" + tabId).append(html);
                tabs.tabs("refresh");
        }
    };

    sock.onclose = function () {
        console.log('close');
    };


    var tabs = $("#main").tabs();

    /** list of feeds is based on jQueryUI "selectable" */
    $( "#feeds-list" ).selectable({
        selected: function( event, ui ) {
            var feedname = $(ui.selected).attr("name");
            var tabId = "tab-" + feedname.replace(/\.|:/g,"-");

            // skip already selected feeds
            if ($("." + tabId).length > 0) return;

            // subscribe to updates on this feed
            sock.send(JSON.stringify(["subscribe", feedname]));
            console.log("send: " + JSON.stringify(["subscribe", feedname]));

            addTab(feedname);
        },
        unselected: function( event, ui ) {
            var feedname = $(ui.unselected).attr("name");

            // un-subscribe from updates on this feed
            sock.send(JSON.stringify(["unsubscribe", feedname]));
            console.log("send: " + JSON.stringify(["unsubscribe", feedname]));

            removeTab(feedname);
        }
    });

    function addTab(feedname) {
        var tabId = "tab-" + feedname.replace(/\.|:/g,"-");
        var li = "<li class='" + tabId + "'><a href='#" + tabId + "'>" + feedname + "</a></li>";

        // add tab header
        tabs.find(".ui-tabs-nav").append(li);
        // add tab itself
        tabs.append('<div id="' + tabId + '" class="' + tabId + ' tab-content"></div>');
        tabs.tabs("refresh");
        tabs.tabs("option", "active", 0);
    }

    function removeTab(feedname) {
        var tabId = "tab-" + feedname.replace(/\.|:/g,"-");
        // both tab and tab header to be removed
        $("." + tabId).remove();
        tabs.tabs("refresh");
        tabs.tabs("option", "active", 0);
    }
})();
