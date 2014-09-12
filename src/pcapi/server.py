import bottle
from pcapi import config, routes

assert routes  # Silence unused import

application = bottle.default_app()

def runserver():
    bottle.run(host=config.get("server", "host"),
               port=config.get("server", "port"),
               debug=config.get("server", "host"))
