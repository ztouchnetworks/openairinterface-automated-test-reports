import argparse
import fnmatch
import logging
import os
import re

from constants import ProcessingConstants
from html_report_utils import process_test_results
from process_payload import get_oai_git_commit, get_srn_number


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--jenkins_job_url', type=str, default='', help='URL of Jenkins pipeline')
    parser.add_argument('--job_id_awx', type=str, default='n/a', help='Job ID of AWX process')
    parser.add_argument('--job_id_jenkins', type=str, default='n/a', help='Job ID of Jenkins process')
    parser.add_argument('--job_start_time', type=str, default='n/a', help='Start time of AWX process')
    parser.add_argument('--oai_repo_url', type=str,
        default='https://gitlab.eurecom.fr/oai/openairinterface5g.git', help='URL of the tested OAI repository')
    parser.add_argument('--results_dir', type=str, required=True, help='Main batch job directory')
    parser.add_argument('--history_dir', type=str, help='Directory with test history data')
    return parser.parse_args()


def set_logger(filename: str) -> None:
    # configure logger and console output
    logging.basicConfig(level=logging.INFO, filename='/tmp/%s' % filename, filemode='w+',
    format='%(asctime)-15s %(levelname)-8s %(message)s')
    formatter = logging.Formatter('%(asctime)-15s %(levelname)-8s %(message)s')
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(formatter)
    logging.getLogger('').addHandler(console)


def find_all(name, path):
    result = []
    for root, _, files in os.walk(path):
        if name in files:
            result.append(os.path.join(root, name))
    return result


def find_pattern(pattern, path):
    result = []
    for root, _, files in os.walk(path):
        for name in files:
            if fnmatch.fnmatch(name, pattern):
                result.append(os.path.join(root, name))
    return result


# look for ue log file to determine directories that should have user reports
def find_ue_directories(results_dir: str) -> list:
    ue_dir = find_all(ProcessingConstants.OAI_UE_LOG_FILE.value, results_dir)
    ue_dir = set(os.path.dirname(x) for x in ue_dir)
    return list(ue_dir)


# look for gnb log file to determine gnb directory
def find_gnb_directory(results_dir: str) -> list:
    gnb_dir = find_all(ProcessingConstants.OAI_GNB_LOG_FILE.value, results_dir)
    gnb_dir = set(os.path.dirname(x) for x in gnb_dir)
    return list(gnb_dir)


# convert git url from ssh to https
def convert_url(git_ssh_url: str) -> str:

    git_remote_pattern = re.compile(r'^git@(\w+.)?\w+.\w+(:\d+)?:')
    git_remote = git_remote_pattern.match(git_ssh_url)

    # return original url if no match was found, e.g., if the url is not in ssh format
    if git_remote is None:
        # remove trailing .git
        git_url_cleaned = re.sub(r'\.git$', '', git_ssh_url)
        return git_url_cleaned

    # get git remote and repo url relative to remote
    git_remote = git_remote.group(0)
    git_repo_relative = re.sub('^{}'.format(git_remote), '', git_ssh_url)

    # clean up git remote and replace it with https format
    git_remote = re.sub(r'^git@', 'https://', git_remote)
    git_remote = re.sub(r':$', '/', git_remote)

    # assemble final url in https format
    git_https_url = '{}{}'.format(git_remote, git_repo_relative)

    # remove trailing .git
    git_https_url_cleaned = re.sub(r'\.git$', '', git_https_url)

    return git_https_url_cleaned


def main() -> None:

    # set logger
    log_filename = os.path.basename(__file__).replace('.py', '.log')
    set_logger(log_filename)

    args = get_args()

    # there should only be a single element returned in this set
    try:
        gnb_dir = find_gnb_directory(args.results_dir)[0]
    except IndexError:
        logging.error('No valid gNB log file found. Exiting')
        return

    if gnb_dir:
        gnb_commit_info, git_commit_hash = get_oai_git_commit(gnb_dir, ProcessingConstants.OAI_GNB_LOG_FILE.value)
        gnb_srn_number = get_srn_number(gnb_dir)
    else:
        gnb_commit_info = ProcessingConstants.OAI_COMMIT_NOT_FOUND_DEFAULT.value
        git_commit_hash = ProcessingConstants.OAI_COMMIT_NOT_FOUND_DEFAULT.value
        gnb_srn_number = ProcessingConstants.SRN_NUMBER_NOT_FOUND_DEFAULT.value

    ue_dir = find_ue_directories(args.results_dir)

    ue_reports = dict()
    ue_directories = dict()
    for d_idx, d_val in enumerate(ue_dir):
        ue_reports[d_idx] = find_pattern(ProcessingConstants.UE_JSON_PATTERN.value, d_val)
        ue_directories[d_idx] = d_val

    # convert url
    git_repo_url = convert_url(args.oai_repo_url)

    process_test_results(ue_reports, ue_directories, args.results_dir, args.history_dir, gnb_commit_info, git_commit_hash,
        gnb_srn_number, args.job_id_awx, args.job_id_jenkins, args.job_start_time, git_repo_url, args.jenkins_job_url)


if __name__ == '__main__':
    main()
