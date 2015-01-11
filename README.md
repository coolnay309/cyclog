GetThat
=======

GetThat is a service that allows you to monitor multiple logs (or any other files) in real-time.
It is similar to Graphite, Cube etc. in a sense that you send various data to one server (or multiple load balanced servers) and access it via Web App.

Automated deployment
--------------------

Requirements:  `fabric` package installed. Have sudo access on remote sever
	
Modify fabfile.py for your deployments needs. Use `fab --list` to see all available commands.

Manual Installation
-------------------

Make sure you have Python >=2.6 and `virtualenv` installed. Virtualenv is not strictly required but is strongly suggested.
If you don't have one, follow it's [installation instructions](http://www.virtualenv.org/en/latest/virtualenv.html#installation ):
	
* Create new virtual environment

    	virtualenv getthat
    	cd getthat
    	$ source bin/activate

* Unpack GetThat there and install needed requirements

        pip install -r requirements.txt
	
Running the service
-------------------

Run it via:

    python getthat.py --webhost=[webhost_ip:]webhost_port --feedhost=[feedhost_ip:]feedhost_port

if hosts or ports are not specified, the defaults will be used:
* **0.0.0.0: 34580**  for HTTP web server
* **0.0.0.0: 34590**  for TCP server receiving feeds

Make sure the ports are open in firewall.

Note: Amazon servers block virtually all ports by default.

Feeding the data
----------------

Server receives TCP streams of data from multiple feeders. It's up to you how you will feed data.
For example to feed data via netcat on Linux:

	 tail -f your_log_file | nc 127.0.0.1 34590

Feeds are named by feeder's outgoing host:port. 
	 
Using Web App
-------------
		 
Updates from a feed are pushed to web apps that had subscribed to the feed. To subscribe to available feeds use web app
	http://127.0.0.1:34580/   or whatever host/port you specified

On the left you see the list of available feeds, named by the feeder's outgoing host:port. Blue are the available feeds. Click a feed to subscribe to it (Ctrl-click to subscribe to multiple feeds). Subscribed feeds are Red and have a tab on the right where updates are posted.
	
From the moment you've subscribed to a feed you'll start receiving updates. As of now neither back-end server nor Web App has means of storing received updates. If you unsubscribe, updates disappear from Web App.