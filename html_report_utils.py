from datetime import datetime
import json
import logging
import math
import os
import pandas as pd
import pathlib
import re

from constants import DataframeColumns, DataframeMetrics, HistoryUpdateKeys, HtmlTemplateKeywords, HtmlColors, \
    ProcessingConstants, TestKeys, TestPassFailThresholds, TestResultKeys
from iperf_log_grapher import compute_history_average, grapher
from process_payload import get_date, get_oai_git_commit, get_srn_number


def generate_figures_for_html_report(data: dict, test_type: str, target_rate: int=None, df_test_history=None) -> list:

    date_now, _, time_now = get_date(data)
    date_time = '{}_{}'.format(date_now, time_now)
    figure_data = grapher(data, date_time, '', 'png', test_type, target_rate, df_test_history)

    return figure_data


def build_dataframe(figure_data: dict, add_ue_summary: bool) -> tuple:

    final_list = []
    header = [DataframeColumns.PROTOCOL.value,
              DataframeColumns.TX_RATE.value,
              DataframeColumns.STREAM.value,
              DataframeColumns.METRIC.value,
              DataframeColumns.MEAN.value,
              DataframeColumns.MAX.value,
              DataframeColumns.FIGURE.value]

    try:
        # unfurl dictionary
        test_type = figure_data[TestKeys.TEST.value]        
        test_date = str(datetime.strptime(figure_data[TestKeys.DATE.value], '%Y%m%d_%H%M%S_%f'))
        test_summary = '{} {}'.format(test_type, test_date)

        for proto_k, proto_v in figure_data[TestKeys.RESULTS.value].items():
            protocol = proto_k.replace(TestResultKeys.PROTOCOL.value, '').upper()

            for band_k, band_v in proto_v.items():
                band = int(band_k.replace(TestResultKeys.BAND.value, ''))

                if band == 0:
                    band = '{} unlimited'.format(DataframeColumns.TX_RATE.value.capitalize())
                else:
                    band = '{} {}'.format(DataframeColumns.TX_RATE.value.capitalize(), band)

                for stream_k, stream_v in band_v.items():
                    stream = stream_k.replace(TestResultKeys.STREAM.value, '')

                    if stream == TestResultKeys.RESULT_ERROR.value:
                        outer_list = [protocol, band, stream]
                        inner_list = [stream_v for x in range(len(header) - len(outer_list))]
                        outer_list = outer_list + inner_list
                        final_list.append(outer_list)
                    else:
                        for el in stream_v:
                            inner_list = []
                            for _, el_v in el.items():
                                inner_list.append(el_v)

                                outer_list = [protocol, band, stream] + inner_list
                            final_list.append(outer_list)
    except KeyError:
        # no test data was found, pass and only add test info
        test_type = ''
        test_summary = ''
        pass

    df = pd.DataFrame(columns=header)
    for el in final_list:
        df.loc[len(df)] = el

    # add test summary before showing actual test content
    test_summary_entry = [HtmlTemplateKeywords.TEST_SUMMARY_TITLE.value]
    [test_summary_entry.append(HtmlTemplateKeywords.TO_DELETE.value) for x in range(len(header) - len(test_summary_entry))]

    df.loc[-1] = test_summary_entry
    df.index = df.index + 1
    df.sort_index(inplace=True)

    # add placeholder for ue commit info and test outcome
    if add_ue_summary:
        ue_commit_entry = [HtmlTemplateKeywords.UE_COMMIT_TITLE.value, HtmlTemplateKeywords.UE_COMMIT.value]
        [ue_commit_entry.append(HtmlTemplateKeywords.TO_DELETE.value) for x in range(len(header) - len(ue_commit_entry))]
        df.loc[len(df)] = ue_commit_entry

        ue_outcome_entry = [HtmlTemplateKeywords.UE_OUTCOME_TITLE.value, HtmlTemplateKeywords.UE_OUTCOME.value]
        [ue_outcome_entry.append(HtmlTemplateKeywords.TO_DELETE.value) for x in range(len(header) - len(ue_outcome_entry))]
        df.loc[len(df)] = ue_outcome_entry

    return df, test_summary


def get_metric_row(df, metric: str):
    df_metric_row = df[df[DataframeColumns.METRIC.value] == metric]
    return df_metric_row


def get_test_history_headers(test_protocol: str, test_direction: str) -> list:

    header_tcp_dl = [DataframeColumns.PROTOCOL.value,
                     DataframeColumns.TX_RATE.value,
                     DataframeMetrics.DATA_TRANSFERRED.value,
                     DataframeMetrics.THROUGHPUT.value]

    header_tcp_ul = [DataframeColumns.PROTOCOL.value,
                     DataframeColumns.TX_RATE.value,
                     DataframeMetrics.DATA_TRANSFERRED.value,
                     DataframeMetrics.THROUGHPUT.value,
                     DataframeMetrics.TCP_CWND.value,
                     DataframeMetrics.RTT.value]

    header_udp_dl = [DataframeColumns.PROTOCOL.value,
                     DataframeColumns.TX_RATE.value,
                     DataframeMetrics.DATA_TRANSFERRED.value,
                     DataframeMetrics.THROUGHPUT.value,
                     DataframeMetrics.JITTER.value,
                     DataframeMetrics.LOST_PKTS_PERC.value,
                     DataframeMetrics.LOST_PKTS.value,
                     DataframeMetrics.TOTAL_PKTS.value]

    header_udp_ul = [DataframeColumns.PROTOCOL.value,
                     DataframeColumns.TX_RATE.value,
                     DataframeMetrics.DATA_TRANSFERRED.value,
                     DataframeMetrics.THROUGHPUT.value,
                     DataframeMetrics.TOTAL_PKTS.value]

    if test_protocol.lower() == 'tcp':
        if test_direction.lower() == 'downlink':
            return header_tcp_dl
        elif test_direction.lower() == 'uplink':
            return header_tcp_ul
        else:
            logging.warning('Unknown headers for test protocol {} and direction {}'.format(test_protocol, test_direction))
    elif test_protocol.lower() == 'udp':
        if test_direction.lower() == 'downlink':
            return header_udp_dl
        elif test_direction.lower() == 'uplink':
            return header_udp_ul
        else:
            logging.warning('Unknown headers for test protocol {} and direction {}'.format(test_protocol, test_direction))
    else:
        logging.warning('Unknown headers for test protocol {}'.format(test_protocol))

    return []


def load_test_history_data(test_history_file: str, test_protocol: str, test_direction: str):

    if os.path.exists(test_history_file):
        logging.info('Loading test history data from file {}'.format(test_history_file))
        df_history = pd.read_pickle(test_history_file)
        logging.info('Test history data loaded')
    else:
        logging.info('Test history data not found. Initializing empty dataframe')
        header = get_test_history_headers(test_protocol, test_direction)
        df_history = pd.DataFrame(columns=header)

    return df_history


# reload df_history in this function, in case we manipulated the previously loaded one
def update_test_history_data(df, test_history_file: str, test_protocol: str, test_direction: str) -> None:

    logging.info('Updating test history file {}'.format(test_history_file))

    # exit if empty
    if len(df.index) < 3:
        logging.warning('Current test result is empty. Skipping update')
        return

    if test_history_file and test_protocol and test_direction:
        df_history = load_test_history_data(test_history_file, test_protocol, test_direction)
        header = get_test_history_headers(test_protocol, test_direction)

        new_test_data = []
        new_test_data.append(df[DataframeColumns.PROTOCOL.value].iloc[1])
        new_test_data.append(get_test_target_rate(df))

        for el in header:
            if el in [DataframeColumns.PROTOCOL.value, DataframeColumns.TX_RATE.value]:
                continue

            df_new_value_row = df.loc[df[DataframeColumns.METRIC.value] == el]
            if len(df_new_value_row.index) > 0:
                new_test_data.append(df_new_value_row[DataframeColumns.MEAN.value].iloc[0])

        try:
            df_history.loc[len(df_history.index)] = new_test_data
            df_history.to_pickle(test_history_file)
            logging.info('Test history file updated')
        except ValueError as e:
            # this happens when the test fails
            # we don't want to update the history file in this case, so it's ok to pass
            logging.warning('History update failed')
            pass


def get_test_target_rate(df) -> int:

    target_rate = df[DataframeColumns.TX_RATE.value].iloc[1]
    re_compiled = re.compile(re.escape(DataframeColumns.TX_RATE.value), re.IGNORECASE) 
    target_rate = re_compiled.sub('', target_rate).strip()

    try:
        target_rate = float(target_rate)
    except ValueError:
        # case with target rate unlimited
        target_rate = 0

    return target_rate


def check_iperf_test_pass(df, df_test_history) -> bool:

    pass_threshold = TestPassFailThresholds.THROUGHPUT_THRESHOLD.value

    # check if throughput mean is above test target rate
    df_throughput = get_metric_row(df, DataframeMetrics.THROUGHPUT.value)
    if len(df_throughput.index) <= 0:
        return False

    throughput_mean = float(df_throughput[DataframeColumns.MEAN.value].iloc[0])
    target_rate = get_test_target_rate(df)

    if target_rate > 0:
        if throughput_mean < pass_threshold * target_rate:
            return False
    else:
        # case in which target rate was unlimited
        # use historic data in this case
        history_throughput_avg = compute_history_average(df_test_history, target_rate, DataframeMetrics.THROUGHPUT.value)

        if throughput_mean < pass_threshold * history_throughput_avg:
            return False

    return True


def determine_ue_test_pass_fail(df, df_test_history) -> bool:
    
    test_pass = True
    if len(df.index) < 3:
        # handle case of no json reports found in UE directory
        return False
    else:
        test_pass = check_iperf_test_pass(df, df_test_history)

    return test_pass


def get_test_history_filename_2(json_data: dict, test_type: str, results_dir: str) -> tuple:

    test_direction = re.search(ProcessingConstants.TEST_DIRECTION_REGEX.value, test_type)
    if test_direction:
        test_direction = test_direction.group()
    else:
        test_direction = ''

    test_protocol = list(json_data.keys())[0]
    results_parent_dir = pathlib.Path(results_dir).parent.absolute()
    test_history_file = '{}/{}_{}_{}.pkl'.format(results_parent_dir,
            TestResultKeys.TEST_HISTORY.value, test_protocol, test_direction.lower())
    target_rate = float(list(json_data[test_protocol].keys())[0])

    return test_protocol, test_direction, test_history_file, target_rate


def get_test_history_filename_3(json_data: dict, test_type: str, history_dir: str, results_dir: str) -> tuple:

    test_direction = re.search(ProcessingConstants.TEST_DIRECTION_REGEX.value, test_type)
    if test_direction:
        test_direction = test_direction.group()
    else:
        test_direction = ''

    if history_dir is None:
        history_dir = pathlib.Path(results_dir).parent.absolute()

    test_protocol = list(json_data.keys())[0]
    test_history_file = '{}/{}_{}_{}.pkl'.format(history_dir,
            TestResultKeys.TEST_HISTORY.value, test_protocol, test_direction.lower())
    target_rate = float(list(json_data[test_protocol].keys())[0])

    return test_protocol, test_direction, test_history_file, target_rate


def generate_html_table(ue_num: int, figure_data: dict, git_commit_info: str,
                        df_test_history, srn_number: str, all_test_pass_outcome: list,
                        results_dir: str, first_table: bool, last_table: bool) -> tuple:

    df, test_summary = build_dataframe(figure_data, last_table)
    html_table = df.to_html(index=False, header=first_table, escape=False)

    test_outcome_title_columns = math.ceil(len(df.columns) / 2)
    test_outcome_columns = len(df.columns) - test_outcome_title_columns

    ue_test_passed = determine_ue_test_pass_fail(df, df_test_history)

    # select html color background
    if ue_test_passed:
        ue_single_test_color = HtmlColors.UE_SINGLE_TEST_PASSED.value
    else:
        ue_single_test_color = HtmlColors.UE_SINGLE_TEST_FAILED.value

    all_test_pass_outcome.append(ue_test_passed)
    if all(all_test_pass_outcome):
        ue_test_outcome = ' bgcolor = "green" colspan="{}"><font color="white">PASS <span class="glyphicon glyphicon-ok"></span></font>'.format(
            test_outcome_columns)
    else:
        ue_test_outcome = ' bgcolor = "red" colspan="{}"><font color="white">FAIL <span class="glyphicon glyphicon-remove"></span></font>'.format(
            test_outcome_columns)

    # replace placeholder for ue commit info
    table_replacements = {'dataframe': 'table',
                          '<th>': '<th style="text-align: center;">',
                          '<td>': '<td style="text-align: center;">',
                          # ue commit entries
                          '>{}</td>'.format(HtmlTemplateKeywords.UE_COMMIT_TITLE.value):
                              ' bgcolor = "{}" colspan="{}">Git Commit Info</td>'.format(HtmlColors.UE_COMMIT.value, test_outcome_title_columns),
                          '>{}</td>'.format(HtmlTemplateKeywords.UE_COMMIT.value): 
                              ' bgcolor = "{}" colspan="{}">{}</td>'.format(HtmlColors.UE_COMMIT.value, test_outcome_columns, git_commit_info),
                          # ue commit entries
                          '>{}</td>'.format(HtmlTemplateKeywords.UE_OUTCOME_TITLE.value):
                              ' bgcolor = "{}" colspan="{}">Test Outcome UE {} (Colosseum SRN-{})</td>'.format(HtmlColors.UE_TEST_OUTCOME.value, test_outcome_title_columns, ue_num, srn_number),
                          '>{}</td>'.format(HtmlTemplateKeywords.UE_OUTCOME.value): ue_test_outcome,
                          # test summary entry
                          '>{}</td>'.format(HtmlTemplateKeywords.TEST_SUMMARY_TITLE.value): 
                              ' bgcolor = "{}" colspan="{}">{}</td>'.format(ue_single_test_color, len(df.columns), test_summary)}

    # replace placeholders
    for key, val in table_replacements.items():
        html_table = html_table.replace(key, val)

    # delete lines with placeholders
    html_table = '\n'.join([x for x in html_table.splitlines() if HtmlTemplateKeywords.TO_DELETE.value not in x])

    # remove closing tags of first table, and opening tags of other tables
    # skip if this is the only table
    if first_table and last_table:
        pass
    else:
        to_replace = r'^\s*<table.*>.*\s*<tbody>'
        html_table = re.sub(to_replace, '', html_table)

        if not last_table:
            to_replace = r'\s*<\/tbody>.*\s*<\/table>\s*$'
            html_table = re.sub(to_replace, '', html_table)

    return html_table, df, ue_test_passed


def write_html_report(html_page: str, results_dir: str) -> None:
    with open('{}/test_summary.html'.format(results_dir), 'w') as f:
        f.write(html_page)


def get_html_page_template() -> str:
    with open('templates/template_test_page.html', 'r') as f:
        page_template = f.read()
    return page_template


def determine_final_test_outcome(html_page: str, result_tables_number: int) -> str:

    # check if any of the tests failed
    if 'FAIL' in html_page or result_tables_number <= 0:
        to_replace = ' bgcolor="{}"><font color="white">FAIL <span class="glyphicon glyphicon-remove"></span></font>'.format(HtmlColors.FINAL_TEST_FAILED.value)
    else:
        to_replace = ' bgcolor="{}"><font color="white">PASS <span class="glyphicon glyphicon-ok"></span></font>'.format(HtmlColors.FINAL_TEST_PASSED.value)

    html_page = html_page.replace('>{}'.format(HtmlTemplateKeywords.FINAL_TEST_OUTCOME.value), to_replace)
    return html_page


def populate_report_page(html_table_list: list, gnb_commit_info: str, gnb_commit_hash: str,
                         gnb_srn_number: str, job_id_awx: str, job_id_jenkins: str,
                         job_start_time: str, oai_repo_url: str, jenkins_job_url: str) -> str:
    html_page = get_html_page_template()

    # set variable with url of jenkins build page. Leave it empty if not passed
    if jenkins_job_url:
        jenkins_build_url = '{}'.format(jenkins_job_url)

        if job_id_jenkins != 'n/a':
            jenkins_build_url += '/{}'.format(job_id_jenkins)
    else:
        jenkins_build_url = ''

    # form html string with linked commit hash
    gnb_linked_commit_info = link_git_hash(gnb_commit_info, gnb_commit_hash, oai_repo_url, True)

    # add general info
    html_page = html_page.replace(HtmlTemplateKeywords.GNB_COMMIT.value, gnb_linked_commit_info)
    html_page = html_page.replace(HtmlTemplateKeywords.GNB_SRN_NUMBER.value, gnb_srn_number)
    html_page = html_page.replace(HtmlTemplateKeywords.JENKINS_JOB_ID.value, job_id_jenkins)
    html_page = html_page.replace(HtmlTemplateKeywords.JENKINS_BUILD_URL.value, jenkins_build_url)
    html_page = html_page.replace(HtmlTemplateKeywords.ANSIBLE_JOB_ID.value, job_id_awx)
    html_page = html_page.replace(HtmlTemplateKeywords.ANSIBLE_BUILD_START_TIME.value, job_start_time)
    html_page = html_page.replace(HtmlTemplateKeywords.OAI_REPO_URL.value, oai_repo_url)
    html_page = html_page.replace(HtmlTemplateKeywords.TEST_PASS_CRITERION.value,
        'Throughput &ge; {}% target transmit rate (or history, if transmit rate unlimited)'.format(TestPassFailThresholds.THROUGHPUT_THRESHOLD.value * 100))

    # add ue result tables
    for el_idx, el_val in enumerate(html_table_list):
        to_replace = el_val

        # re-add placeholder if not last table
        if el_idx < len(html_table_list) - 1:
            to_replace += '\n&nbsp;\n{}'.format(HtmlTemplateKeywords.RESULTS_TABLE.value)

        html_page = html_page.replace(HtmlTemplateKeywords.RESULTS_TABLE.value, to_replace)

    # write final test outcome
    html_page = determine_final_test_outcome(html_page, len(html_table_list))

    # replace ue table placeholder in case no user results were found
    html_page = html_page.replace(HtmlTemplateKeywords.RESULTS_TABLE.value, '')

    return html_page


# generate html string with linked hash in git commit info
def link_git_hash(git_commit_info: str, git_commit_hash: str, git_repo_url: str, hash_only: bool) -> str:

    if hash_only:
        if git_commit_hash == ProcessingConstants.OAI_COMMIT_NOT_FOUND_DEFAULT.value:
            return git_commit_hash
    else:
        if git_commit_info == ProcessingConstants.OAI_COMMIT_NOT_FOUND_DEFAULT.value or \
            git_commit_hash == ProcessingConstants.OAI_COMMIT_NOT_FOUND_DEFAULT.value:
            return git_commit_info

    git_linked_commit_hash = '<a href="{0}/-/commit/{1}" target="_blank">{1}</a>'.format(git_repo_url, git_commit_hash)
    if hash_only:
        return git_linked_commit_hash

    git_linked_commit_info = git_commit_info.replace(git_commit_hash, git_linked_commit_hash)
    return git_linked_commit_info


def process_test_results(ue_reports: dict, ue_directories: dict, results_dir: str, history_dir: str,
    gnb_commit_info: str, gnb_commit_hash: str, gnb_srn_number: str, job_id_awx: str,
    job_id_jenkins: str, job_start_time: str, oai_repo_url: str, jenkins_job_url: str) -> None:
    
    html_table_list = []
    history_update_list = []
    for r_key, r_val in ue_reports.items():
        ue_commit_info, ue_commit_hash = get_oai_git_commit(ue_directories[r_key], ProcessingConstants.OAI_UE_LOG_FILE.value)
        ue_linked_commit_info = link_git_hash(ue_commit_info, ue_commit_hash, oai_repo_url, False)

        ue_srn_number = get_srn_number(ue_directories[r_key])

        html_table = process_ue_json_report(r_key + 1, r_val, ue_linked_commit_info,
            ue_srn_number, results_dir, history_dir, history_update_list)

        if html_table:
            html_table_list.append(html_table)

    # update results history
    for el in history_update_list:
        if el[HistoryUpdateKeys.TEST_PASS_STATUS.value]:
            update_test_history_data(el[HistoryUpdateKeys.TEST_DATAFRAME.value],
                el[HistoryUpdateKeys.TEST_HISTORY_FILE.value],
                el[HistoryUpdateKeys.TEST_PROTOCOL.value],
                el[HistoryUpdateKeys.TEST_DIRECTION.value])
        else:
            logging.warning('Skipping test history file update because of test regression')

    html_page = populate_report_page(html_table_list, gnb_commit_info, gnb_commit_hash,
        gnb_srn_number, job_id_awx, job_id_jenkins, job_start_time, oai_repo_url, jenkins_job_url)
    write_html_report(html_page, results_dir)


# split results in the form of {'udp': {'5': {...}, '10': {...}}} in the form
# [{'udp': '5': {...}}, {'udp': '10': {...}}]
# Also skip erroneous iPerf reports, e.g., {"error": "unable to send control message: "}
def split_multiple_reports(json_data: dict) -> list:

    output_list = []
    for proto_k, proto_v in json_data.items():
        for bw_k, bw_v in proto_v.items():
            bw_dict = dict()
            bw_dict[bw_k] = bw_v

            output_list.append({proto_k: bw_dict})
    
    return output_list


def process_ue_json_report(ue_num: int, json_reports: list, git_commit_info: str,
    srn_number: str, results_dir: str, history_dir: str, history_update_list: dict) -> str:

    regex_expressions_dict = {'iPerf3 Downlink': r'^iperf3_result_\d{8}_\d{6}_DL.*$',
                              'iPerf3 Uplink': r'^iperf3_result_\d{8}_\d{6}_UL.*$'}

    html_table = ''
    ue_test_pass_outcome = []
    for j_idx, j_el in enumerate(json_reports):
        logging.info('Processing JSON report {}'.format(j_el))

        with open(j_el, 'r') as f:
            json_data_file_content = json.load(f)

        # split multiple sequential tests into separate entries
        json_data_list = split_multiple_reports(json_data_file_content)
        
        for json_data_idx, json_data in enumerate(json_data_list):
            # beautify column name
            test_type = filename = os.path.basename(j_el)
            for r_key, r_val in regex_expressions_dict.items():
                test_type = re.sub(r_val, r_key, test_type)

            # determine whether this is the first or last table to be printed for the current user
            is_user_first_table = (j_idx == 0) and (json_data_idx == 0)
            is_user_last_table = (j_idx == len(json_reports) - 1) and (json_data_idx == len(json_data_list) - 1)

            test_protocol, test_direction, test_history_file, target_rate = get_test_history_filename_3(json_data, test_type, history_dir, results_dir)
            df_test_history = load_test_history_data(test_history_file, test_protocol, test_direction)

            json_figure = generate_figures_for_html_report(json_data, test_type, target_rate, df_test_history)
            new_html_table, df, ue_test_passed = generate_html_table(ue_num, json_figure, git_commit_info,
                df_test_history, srn_number, ue_test_pass_outcome, results_dir, is_user_first_table, is_user_last_table)

            # bring this out of this function so we update the history results at the end
            # and the threshold is the same for all the UEs in this test
            history_update_list.append({HistoryUpdateKeys.TEST_DATAFRAME.value: df.copy(deep=True),
                HistoryUpdateKeys.TEST_DIRECTION.value: test_direction,
                HistoryUpdateKeys.TEST_HISTORY_FILE.value: test_history_file,
                HistoryUpdateKeys.TEST_PROTOCOL.value: test_protocol,
                HistoryUpdateKeys.TEST_PASS_STATUS.value: ue_test_passed})

            html_table += new_html_table

    # only add test info if it was not added while processing the reports, e.g., if no reports were found
    if not html_table:
        new_html_table, _, _ = generate_html_table(ue_num, dict(), git_commit_info, None, srn_number, ue_test_pass_outcome, results_dir, True, True)
        html_table += new_html_table

    return html_table
