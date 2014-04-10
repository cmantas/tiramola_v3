__author__ = 'cmantas'

import logging
import logging.handlers
import sys

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
logger.name = "test"

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('[%(levelname)s] - %(name)s: %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
handler = logging.handlers.RotatingFileHandler('files/logs/test.log', maxBytes=2 * 1024 * 1024, backupCount=5)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('[%(levelname)s] %(asctime)s - %(name)s: %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

logger.error("helloo")

print "%02d" % 2 + str("hello")