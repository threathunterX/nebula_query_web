from nebula_website import app
import logging
from logging.handlers import RotatingFileHandler
logging.basicConfig()
Rthandler = RotatingFileHandler('/data/logs/web/query_web_log', maxBytes=20*1024*1024,backupCount=5)
Rthandler.setLevel(logging.DEBUG)
app.logger = logging.geLogger("").addHandler(Rthandler)
app.run()
