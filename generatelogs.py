__author__ = 'pranaysuresh'

import logging
import logging.handlers

logger = logging.getLogger("application_logger")
logger.setLevel(logging.DEBUG)
max_file_size = 1024 * 1024
max_file_count = 0
fh = logging.handlers.RotatingFileHandler("./application.log", maxBytes=max_file_size,
                                          backupCount=max_file_count)
fh.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s', '%Y-%m-%d %H:%M:%S')
fh.setFormatter(formatter)
logger.addHandler(fh)

def log_data():
    import time
    import random
    app_number = random.randint(1,10)
    while 1:
        random_log_level = random.choice([10, 20, 30, 40, 50])
        logger.log(random_log_level, "This is a log message from Application {0}".format(app_number))
        time.sleep(2)

if __name__ == '__main__':
    log_data()