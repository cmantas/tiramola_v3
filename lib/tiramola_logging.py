__author__ = 'cmantas'

import logging, sys, logging.handlers

configured_loggers = []


def get_logger(name, level, show_level=False, show_time=False, logfile=None):
    new_logger = logging.getLogger(name)
    #skip configuration if already configured
    if name in configured_loggers:
        return new_logger

    new_logger.setLevel(logging.DEBUG)

    console_handler = logging.StreamHandler(sys.stdout)

    #construct format
    console_format = '|%(name)23s: %(message)s'
    if show_level: console_format = '[%(levelname)s] ' + console_format
    if show_time: console_format = '%(asctime)-15s  - ' + console_format
    formatter = logging.Formatter(console_format, "%b%d %H:%M:%S")

    #add console handler
    console_handler.setFormatter(formatter)
    eval("console_handler.setLevel(logging.%s)" % level)
    new_logger.addHandler(console_handler)
    
    #Different handler for logfile
    if not logfile is None:
        file_handler = logging.FileHandler(logfile)
        file_handler.setLevel(logging.DEBUG)
        fformat = '%(asctime)-15s[%(levelname)5s] %(name)20s: %(message)s'
        fformatter = logging.Formatter(fformat, "%b%d %H:%M:%S")
        file_handler.setFormatter(fformatter)
        #print "adding handler for %s" % logfile
        new_logger.addHandler(file_handler)

    new_logger.propagate = False
    #logging.root.disabled = True
    configured_loggers.append(name)
    return new_logger


def get_logger_test(name):
    new_logger = logging.getLogger(name)
    new_logger.name = name
    new_logger.setLevel(logging.DEBUG)
    #create console handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter('[%(levelname)s] - %(name)s: %(message)s')
    handler.setFormatter(formatter)

    #add console handler
    new_logger.addHandler(handler)

    #create file handler
    handler = logging.FileHandler('test.log')
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('[%(levelname)s] %(asctime)s - %(name)s: %(message)s')
    handler.setFormatter(formatter)
    new_logger.addHandler(handler)
    return  new_logger



if __name__ == "__main__":

    logger = get_logger("tralalo")
    logger.debug("debug message")
    logger.info("this is an info message")