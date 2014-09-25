import bottle
from pcapi import config, routes

assert routes  # Silence unused import

application = bottle.default_app()


def runserver():
    
    bottle.run(host=config.get("server", "host"),
               port=config.get("server", "port"),
               debug=config.getboolean("server", "debug"))
    


if __name__ == '__main__':
    runserver()
