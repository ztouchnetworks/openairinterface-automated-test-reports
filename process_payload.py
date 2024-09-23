from datetime import datetime
import logging
import os.path
import re
from trace_dkey import trace

from constants import ProcessingConstants
from iperf_log_grapher import grapher


def get_date(data: dict) -> tuple:

    # get timestamp
    paths = trace(data, 'time')
    if paths:
        for path in paths:
            timestamp_dict = data
            for key in path:
                timestamp_dict = timestamp_dict[key]
            break

        logging.info(timestamp_dict)
        timestamp = datetime.strptime(timestamp_dict, '%a, %d %b %Y %H:%M:%S %Z')

        date_now = timestamp.strftime('%Y%m%d')
        time_hms = timestamp.strftime('%H%M%S')
        time_now = timestamp.strftime('%H%M%S_%f')
    else:
        logging.warning('Timestamp not found in data. Computing using current time')
        date_now = datetime.today().strftime('%Y%m%d')
        time_hms = datetime.today().strftime('%H%M%S')
        time_now = '{}_{}'.format(time_hms, datetime.today().strftime('%f'))  # add microsecond

    return date_now, time_hms, time_now


# get git commit data and hash by inspecting OAI gNB or UE log file
def get_oai_git_commit(dir_path: str, log_file: str) -> tuple:

    abs_log_filename = '{}/{}'.format(dir_path, log_file)

    if os.path.exists(abs_log_filename):
        with open(abs_log_filename, 'r') as f:
            for line in f:
                git_commit = re.search(ProcessingConstants.OAI_COMMIT_REGEX.value, line)
                if git_commit is not None:

                    # get commit data, in the form of
                    # Version: Branch: HEAD Abrev. Hash: bd721c3bd Date: Tue Jul 30 16:24:27 2024 +0000
                    git_commit_data = re.sub(ProcessingConstants.OAI_LOG_LAYER_INFO.value, '', line).strip()
                    
                    # getcommit hash
                    git_commit_hash = git_commit.group()
                    git_commit_hash = git_commit_hash.split(' ')[-1]

                    break
        if git_commit_data is None:
            git_commit_data = ProcessingConstants.OAI_COMMIT_NOT_FOUND_DEFAULT.value

        if git_commit_hash is None:
            git_commit_hash = ProcessingConstants.OAI_COMMIT_NOT_FOUND_DEFAULT.value
    else:
        git_commit_data = ProcessingConstants.OAI_COMMIT_NOT_FOUND_DEFAULT.value
        git_commit_hash = ProcessingConstants.OAI_COMMIT_NOT_FOUND_DEFAULT.value

    return git_commit_data, git_commit_hash


# get srn number from the log directory
def get_srn_number(log_dir: str) -> str:
    srn_number = re.search(ProcessingConstants.SRN_NUMBER.value, log_dir)
    if srn_number:
        srn_number = srn_number.group().replace('srn', '')
        srn_number = srn_number.zfill(3)
    else:
        srn_number = ProcessingConstants.SRN_NUMBER_NOT_FOUND_DEFAULT.value

    return srn_number
