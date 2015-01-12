""" Back-end server for the Cyclog app.

Run it via:
    python cyclog.py --webhost=[webhost_ip:]webhost_port --feedhost=[feedhost_ip:]feedhost_port

    if hosts or ports are not specified, the defaults will be used:
        0.0.0.0: 34580  for HTTP web server
        0.0.0.0: 34590  for TCP server receiving feeds

    Make sure the ports are open in firewall.
    Note: Amazon servers block virtually all ports by default.

Server receives TCP streams of data from multiple feeders. It's up to you how you will feed data.
For example via netcat on Linux:
     tail -f your_log_file | nc 127.0.0.1 34590

Updates from a feed are pushed to web apps that had subscribed to the feed. To subscribe to available feeds use web app
    http://127.0.0.1:34580/   or whatever host/port you specified

Feeds are named by feeder's outgoing host:port.
"""

import getopt
import sys
import logging
import logging.handlers
import json

from tornado import iostream, ioloop, tcpserver, web
from sockjs.tornado import SockJSRouter, SockJSConnection

import brukva
import redis

def create_logger(name, level=logging.DEBUG, to_file=True, to_console=False):
    """ Create and configure logger

    @param name:        logger name
    @param level:       logging level for files and console output
    @param to_file:     True/False, write log output to "cyclog.log" file or not
    @param to_console:  True/False, print log output to stderr or not
    @return:            log object
    """
    _log = logging.getLogger(name)
    _log.propagate = False
    _log.setLevel(level)

    # output format
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # create console handler
    if to_console:
        ch = logging.StreamHandler()
        ch.setFormatter(formatter)
        ch.setLevel(level)
        _log.addHandler(ch)

    # create file handler
    if to_file:
        # each log file is up to 10Mb
        fh = logging.handlers.RotatingFileHandler("cyclog.log", maxBytes=10*1024*1024)
        fh.setFormatter(formatter)
        fh.setLevel(level)
        _log.addHandler(fh)

    return _log


log = create_logger("cyclog", to_console=True)

# create async redis client
redis_client = brukva.Client()
redis_client.connect()

#create a sync client
redis_sync_client = redis.StrictRedis(host='localhost', port=6379, db=0)

class WebAppConnection(SockJSConnection):
    """ Connection between web app and server

        Accepted messages from web app:
            ("subscribe", feedname)     web app subscribes to feed `feedname`
            ("unsubscribe", feedname)   web app un-subscribes from feed `feedname`

        Accepted messages from server:
            ("add", feedname)       new feed `feedname` is available
            ("remove", feedname)    feed `feedname` is not available anymore
            (feedname, data)        feed `feedname` was updated with `data`
    """
    def __init__(self, session):
        super(WebAppConnection, self).__init__(session)
        self.ip = None
        self.client = brukva.Client()
        self.client.connect()
        self.client.subscribe('broadcast_channel')

    def on_open(self, request):
        """ Handles opened web app connection"""
        self.ip = request.ip
        self.client.listen(self.on_pubsub_message)
        log.debug("Connected new webapp from %s" % self.ip)

        # push list of available feeds to web app
        for feedname in redis_sync_client.lrange('feedlist', 0, -1):
            print("channel list name is: ", feedname)
            self.send(json.dumps(["add", feedname]))

    def on_pubsub_message(self, message):
        """Callback for redis pusub updates"""
        print("Inside pubsub message: ", message.body) 
        self.send(message.body)

    def on_message(self, msg):
        """ Handles incoming message"""
        try:
            command, feedname = json.loads(msg)
        except Exception as e:
            log.error("Can't decode message '%s' from webapp at %s. Exception: %s" % (msg, self.ip, e))
            return

        if command == "subscribe":
            self.client.subscribe(feedname)
        elif command == "unsubscribe":
            self.client.unsubscribe(feedname)
        else:
            log.error("Unknown command %s from webapp %s" % (command, self.ip))

    def on_close(self):
        """ Handles closed web app connection"""
        log.debug("Disconnected webapp from %s" % self.ip)

        for feedname in redis_sync_client.lrange('feedlist', 0, -1):
            try:
                self.client.unsubscribe(feedname)
            except Exception:
                continue
        self.client.disconnect()

class FeedConnection(iostream.IOStream):
    """ Connection between feeder and server"""

    def __init__(self, sock, address, close_callback=None, io_loop=None):
        """
        @param sock:            connected socket
        @param address:         where it comes from
        @param close_callback:  optional, callback to call when connection is closed
        @param io_loop:         optional, event loop to use
        """
        super(FeedConnection, self).__init__(sock, io_loop=io_loop)

        self.address = address
        self.close_callback = close_callback
        self.io_loop = io_loop or ioloop.IOLoop.current()

        try:
            self.id = "%s:%s" % self.address
        except Exception as e:
            log.error("Can't parse address. Exception: %s" % e)
            return

        log.debug("Connected new feed %s" % self.id)
        self.read_until_close(self.handle_close, streaming_callback=self.handle_streaming)

        # broadcast "new feed is available" to all webapps
        redis_client.publish('broadcast_channel', json.dumps(["add", self.id]))
        # add to redis list of feeds
        redis_sync_client.rpush('feedlist', self.id)

    def handle_close(self, data):
        """ Handles connection close

        @param data:    not used when it's in conjunction with `handle_streaming`
        """
        log.debug("Closed feed %s" % self.id)

        # broadcast "feed is closed" to all webapps
        redis_client.publish('broadcast_channel', json.dumps(["remove", self.id]))

        redis_sync_client.lrem('feedlist', 1, self.id)
        if self.close_callback:
            self.close_callback(self)

    def handle_streaming(self, data):
        """ Handles incoming chunk of data"""
        log.debug("-> Server    ; feed: %s : %s" % (self.id, repr(data[:60])))

        # forward received data to all subscribed web apps via redis pubsub
        redis_client.publish(self.id, json.dumps([self.id, data]))

class Receiver(tcpserver.TCPServer):
    """ TCP server receiving incoming feeds"""

    def __init__(self, io_loop=None):
        super(Receiver, self).__init__(io_loop=io_loop)
        self.io_loop = io_loop or ioloop.IOLoop.current()

    def handle_stream(self, stream, address):
        """ Handles new incoming feed"""
        connection = FeedConnection(stream.socket, address, io_loop=self.io_loop)


class MainHandler(web.RequestHandler):
    """ Handles incoming get/head/post HTTP requests"""

    def get(self):
        """ Serves main web app page"""
        self.render("webapp/index.html")


def print_help():
    print "python cyclog.py --webhost=[webhost_ip:]webhost_port --feedhost=[feedhost_ip:]feedhost_port"


if __name__ == '__main__':
    # default address for web server
    web_host = "0.0.0.0"
    web_port = 34580

    # default address for feed receiving TCP server
    feed_host = "0.0.0.0"
    feed_port = 34590

    # parse cmd line args
    try:
        opts, args = getopt.getopt(sys.argv[1:], "hx:", ["webhost=", "feedhost="])
    except getopt.GetoptError as e:
        print "Got error while parsing args: %s " % e
        print_help()
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print_help()
            sys.exit()

        elif opt == "--webhost":
            addr = arg.split(":")
            try:
                web_port = int(addr[1])
                web_host = addr[0]
            except IndexError:
                # given port only
                web_port = int(addr[0])

        elif opt == "--feedhost":
            addr = arg.split(":")
            try:
                feed_port = int(addr[1])
                feed_host = addr[0]
            except IndexError:
                # given port only
                feed_port = int(addr[0])

    # setup feed receiving TCP server
    receiver = Receiver()
    receiver.listen(feed_port, address=feed_host)

    redis_sync_client.ltrim('feedlist', 10, 0)

    # setup web server
    WebAppRouter = SockJSRouter(WebAppConnection, '/sockjs')
    app = web.Application(WebAppRouter.urls + [
        (r"/", MainHandler),
        (r'/(.*)', web.StaticFileHandler, {'path': 'webapp/'}),
    ])
    app.listen(web_port, address=web_host)

    ioloop.IOLoop.instance().start()
