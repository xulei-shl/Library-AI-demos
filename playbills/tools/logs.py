import os
import logging
from datetime import datetime

def setup_logger(log_folder_path):
    if not os.path.exists(log_folder_path):
        os.makedirs(log_folder_path)

    log_file = os.path.join(log_folder_path, f"logs_{datetime.now().strftime('%Y-%m-%d')}.txt")
    filemode = 'a' if os.path.exists(log_file) else 'w'

    logging.basicConfig(
        filename=log_file,
        filemode=filemode,
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    return logging.getLogger(__name__)