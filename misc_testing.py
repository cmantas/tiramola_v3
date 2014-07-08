__author__ = 'cmantas'

import ConfigParser

config = ConfigParser.ConfigParser()
config.read("config_test.ini")
# print Config.sections()

input_params = {}


for section in config.sections():
    input_params.update(dict(config.items(section)))


for key, value in input_params.items():
    print key, value


