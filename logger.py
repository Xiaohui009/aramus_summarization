# /usr/bin/env python

"""
@author: Xiaohui
@date: 2023/10/18
@filename: logger.py
@description:
"""

import os
import logging
import logging.handlers
from colorlog import ColoredFormatter

LOG_PATH = ""
LOG_LEVEL = 'info'


LOG_LEVEL_MAPPINGS = {
    'notset': logging.NOTSET,
    'debug': logging.DEBUG,
    'info': logging.INFO,
    'warning': logging.WARNING,
    'error': logging.ERROR,
    'critical': logging.CRITICAL
}


def get_logger(name):
    logger = logging.getLogger(name)
    logger.setLevel(LOG_LEVEL_MAPPINGS[LOG_LEVEL])
    LOGFORMAT = '%(log_color)s%(asctime)s-%(name)s-%(levelname)s: %(message)s'
    format_str = ColoredFormatter(LOGFORMAT, log_colors={'DEBUG': 'white',
                                                         'INFO': 'bold_white',
                                                         'WARNING': 'bold_yellow',
                                                         "ERROR": 'bold_red'})

    sh = logging.StreamHandler()
    sh.setFormatter(format_str)

    if LOG_PATH:
        os.makedirs(LOG_PATH, exist_ok=True)
        th = logging.handlers.RotatingFileHandler(
            os.path.join(LOG_PATH, '{}.log'.format(name)), mode='a',
            maxBytes=1024 * 1024 * 100,
            backupCount=10, encoding='utf-8')
        format_str = logging.Formatter(
            '%(asctime)s-%(name)s-%(levelname)s:  %(message)s')
        th.setFormatter(format_str)
        logger.addHandler(th)

    logger.addHandler(sh)
    return logger


if __name__ == '__main__':
    pass