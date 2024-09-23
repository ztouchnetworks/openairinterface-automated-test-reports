from enum import Enum


class ProcessingConstants(Enum):
    OAI_COMMIT_NOT_FOUND_DEFAULT = 'n/a'
    OAI_COMMIT_REGEX = r'Hash:\s+(\d|\w)+'
    OAI_GNB_LOG_FILE = 'nr-gnb.log'
    OAI_LOG_LAYER_INFO = r'^.*\[HW\]\s+(I\s)*'
    OAI_UE_LOG_FILE = 'nr-ue.log'
    SRN_NUMBER = r'srn\d+'
    SRN_NUMBER_NOT_FOUND_DEFAULT = 'n/a'
    TEST_DIRECTION_REGEX = r'(\w{2,})link'
    UE_JSON_PATTERN = 'iperf3_result_*.json'


class HtmlTemplateKeywords(Enum):
    ANSIBLE_BUILD_START_TIME = 'PLACEHOLDER_ANSIBLE_BUILD_START_TIME'
    ANSIBLE_JOB_ID = 'PLACEHOLDER_ANSIBLE_JOB_ID'
    FINAL_TEST_OUTCOME = 'PLACEHOLDER_FINAL_TEST_OUTCOME'
    GNB_COMMIT = 'PLACEHOLDER_GNB_TEST_COMMIT'
    GNB_SRN_NUMBER = 'PLACEHOLDER_GNB_SRN_NUMBER'
    JENKINS_BUILD_URL = 'PLACEHOLDER_JENKINS_BUILD_URL'
    JENKINS_JOB_ID = 'PLACEHOLDER_JENKINS_JOB_ID'
    OAI_REPO_URL = 'PLACEHOLDER_OAI_REPO_URL'
    RESULTS_TABLE = 'PLACEHOLDER_TABLE'
    TEST_PASS_CRITERION = 'PLACEHOLDER_TEST_PASS_CRITERION'
    TEST_SUMMARY_TITLE = 'PLACEHOLDER_TEST_SUMMARY'
    TO_DELETE = 'PLACEHOLDER_DELETE'
    UE_COMMIT = 'PLACEHOLDER_UE_TEST_COMMIT'
    UE_COMMIT_TITLE = 'PLACEHOLDER_UE_TEST_COMMIT_TITLE'
    UE_OUTCOME = 'PLACEHOLDER_UE_TEST_OUTCOME'
    UE_OUTCOME_TITLE = 'PLACEHOLDER_UE_TEST_OUTCOME_TITLE'


class HtmlColors(Enum):
    FINAL_TEST_FAILED = 'red'
    FINAL_TEST_PASSED = 'green'
    UE_COMMIT = 'lightcyan'
    UE_SINGLE_TEST_FAILED = 'orange'
    UE_SINGLE_TEST_PASSED = '#F0F0F0'
    UE_TEST_OUTCOME = '#33CCFF'


class TestKeys(Enum):
    DATE = 'date'
    FIGURE = 'figure'
    METRIC = 'metric'
    METRIC_MAX = 'max'
    METRIC_MEAN = 'mean'
    RESULTS = 'results'
    TEST = 'test'


class TestResultKeys(Enum):
    BAND = 'band_'
    PROTOCOL = 'protocol_'
    RESULT_ERROR = 'n/a'
    STREAM = 'stream_'
    TEST_HISTORY = 'test_mean_history'


class DataframeColumns(Enum):
    FIGURE = 'Figure'
    MAX = 'Max'
    MEAN = 'Mean'
    METRIC = 'Metric'
    PROTOCOL = 'Protocol'
    STREAM = 'Stream'
    TX_RATE = 'Transmit Rate'


class DataframeMetrics(Enum):
    DATA_TRANSFERRED = 'Data Transferred [Mbit]'
    JITTER = 'Jitter [ms]'
    LOST_PKTS = 'Number of Lost Packets'
    LOST_PKTS_PERC = 'Percentage of Lost Packets (%)'
    RTT = 'Round-trip Time [ms]'
    TCP_CWND = 'TCP Congestion Window [MB]'
    THROUGHPUT = 'Throughput [Mbps]'
    TOTAL_PKTS = 'Total Packets'


class TestPassFailThresholds(Enum):
    THROUGHPUT_THRESHOLD = 0.9


class HistoryUpdateKeys(Enum):
    TEST_DATAFRAME = 'test_df'
    TEST_DIRECTION = 'test_direction'
    TEST_HISTORY_FILE = 'test_history_file'
    TEST_PASS_STATUS = 'test_passed'
    TEST_PROTOCOL = 'test_protocol'
