__author__ = 'cmantas'

from ConfigParser import ConfigParser


def load_conf_file(filename):
    config = ConfigParser()
    config.read(filename)
    # print Config.sections()

    input_params = {}

    for section in config.sections():
        input_params.update(dict(config.items(section)))
    return input_params





if __name__ == '__main__':

    d = load_conf_file("config_test.ini")
    for key, value in d.items():
        print key, value