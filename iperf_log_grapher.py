import base64
from io import BytesIO
import math
import matplotlib
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

from constants import DataframeColumns, DataframeMetrics, TestKeys, TestResultKeys

# to use matplotlib outside of the main thread
matplotlib.use('agg')

metrics = {
    'tcp': ['bytes', 'bits_per_second', 'snd_cwnd', 'rtt'],
    'udp': ['bytes', 'bits_per_second', 'jitter_ms', 'lost_packets', 'packets', 'lost_percent']
}

metrics_dfcolumns_map = {
    'bits_per_second': DataframeMetrics.THROUGHPUT.value,
    'bytes': DataframeMetrics.DATA_TRANSFERRED.value,
    'jitter_ms': DataframeMetrics.JITTER.value,
    'lost_packets': DataframeMetrics.LOST_PKTS.value,
    'lost_percent': DataframeMetrics.LOST_PKTS_PERC.value,
    'packets': DataframeMetrics.TOTAL_PKTS.value,
    'rtt': DataframeMetrics.RTT.value,
    'snd_cwnd': DataframeMetrics.TCP_CWND.value
}


def create_stream_df(intervals_dict, stream_id):
    temp_dict = [line['streams'][stream_id] for line in intervals_dict]
    df = pd.DataFrame(temp_dict)
    return df


def create_plots(df, date_time, protocol, band, stream_name, dir_path, figure_extension, target_rate: int=None, df_test_history=None) -> list:
    saved_figure_path = []
    for metric in metrics[protocol]:
        if metric in df.columns:
            # compute history average and generate plot
            history_avg = compute_history_average(df_test_history, target_rate, metrics_dfcolumns_map[metric])
            saved_figure_path.append(plot_and_save(df, date_time, protocol, band, stream_name, metric, dir_path, figure_extension, history_avg))
    return saved_figure_path


def compute_history_average(df, target_rate: int, metric: str) -> float:

    if len(df.index) <= 0:
        return float('nan')

    # filter df by target rate
    df_test_target = df.loc[df[DataframeColumns.TX_RATE.value] == int(target_rate)]

    try:
        history_mean = df_test_target.loc[:, metric].mean()
    except KeyError:
        print('Metric {} not in history dataframe. Skipping it'.format(metric))
        return float('nan')

    return history_mean


def plot_and_save(df, date_time, protocol, band, stream_name, metric, dir_path, figure_extension, history_avg: float) -> dict:

    name_key = 'name'
    correction_key = 'correction'
    plot_adjustments = {'bits_per_second': {name_key: 'Throughput [Mbps]', correction_key: 1e-6},
                        'bytes': {name_key: 'Data Transferred [Mbit]', correction_key: 8e-6},
                        'jitter_ms': {name_key: 'Jitter [ms]', correction_key: 1},
                        'lost_packets': {name_key: 'Number of Lost Packets', correction_key: 1},
                        'lost_percent': {name_key: 'Percentage of Lost Packets (%)', correction_key: 1},
                        'packets': {name_key: 'Total Packets', correction_key: 1},
                        'snd_cwnd': {name_key: 'TCP Congestion Window [MB]', correction_key: 1e-6},
                        'rtt': {name_key: 'Round-trip Time [ms]', correction_key: 1e-3}
    }

    # check if metric needs to be adjusted
    if metric in plot_adjustments.keys():
        y_label = plot_adjustments[metric][name_key]
        df[metric] *= plot_adjustments[metric][correction_key]
    else:
        y_label = metric

    sns.set_theme()
    sns.set_context("paper")

    plt.subplot(1, 1, 1)
    sns.lineplot(data=df, x='end', y=metric)
    plt.axhline(y=df[metric].mean(), color='b', linestyle='--')
    sns.despine(top=True, right=True, left=True, bottom=True)
    legend_entries = ['Test', '_Hidden', 'Test Average']

    # plot test history average, if passed
    if history_avg is not None and not math.isnan(history_avg):
        plt.axhline(y=history_avg, color='r', linestyle='--')
        legend_entries.append('Test History Average')

        top_margin = max(df[metric].max(), history_avg) * 1.05 + 0.001
    else:
        top_margin = df[metric].max() * 1.05 + 0.001

    plt.xlabel('Time [s]')
    plt.ylabel(y_label)
    plt.legend(legend_entries)
    plt.ylim(top=top_margin, bottom=-0.01)

    plot_name = '{}_{}_band{}Mbps_stream{}_{}'.format(
        date_time, protocol, band, stream_name, metric)
    
    if dir_path:
        save_path = '{}/{}.{}'.format(dir_path, plot_name, figure_extension)
        plt.title(plot_name)
    else:
        save_path = BytesIO()

    plt.savefig(save_path, format=figure_extension)
    plt.clf()

    # encode figure and embed it within html tags
    encoded_figure = base64.b64encode(save_path.getvalue()).decode('utf-8')
    html_figure = '<img src=\'data:image/png;base64,{}\'>'.format(encoded_figure)

    metric_mean = df.loc[:, metric].mean()
    metric_max = df.loc[:, metric].max()

    output_dict = {TestKeys.METRIC.value: plot_adjustments[metric][name_key],
                   TestKeys.METRIC_MEAN.value: metric_mean,
                   TestKeys.METRIC_MAX.value: metric_max,
                   TestKeys.FIGURE.value: html_figure
    }

    return output_dict


def grapher(json_dict, date_time, dir_path, figure_extension='pdf', test_type='', target_rate: int=None, df_test_history=None) -> dict:
    protocol_dict = dict()
    for protocol in json_dict:
        band_dict = dict()
        for band in json_dict[protocol]:
            stream_dict = dict()
            try:
                n_streams = len(json_dict[protocol][band]
                                ['intervals'][0]['streams'])

                for stream_id in range(n_streams):
                    df = create_stream_df(json_dict[protocol][band]['intervals'], stream_id)

                    stream_key = '{}{}'.format(TestResultKeys.STREAM.value, stream_id)
                    stream_dict[stream_key] = create_plots(df, date_time, protocol, band, stream_id, dir_path, figure_extension, target_rate, df_test_history)
            except KeyError:
                # this is to handle iperf error and to mark the test as failed
                stream_key = '{}{}'.format(TestResultKeys.STREAM.value, TestResultKeys.RESULT_ERROR.value)
                stream_dict[stream_key] = json_dict[protocol][band]

        band_key = '{}{}'.format(TestResultKeys.BAND.value, band)
        band_dict[band_key] = stream_dict
    
    protocol_key = '{}{}'.format(TestResultKeys.PROTOCOL.value, protocol)
    protocol_dict[protocol_key] = band_dict
                
    output_dict = {TestKeys.TEST.value: test_type,
       TestKeys.DATE.value: date_time,
       TestKeys.RESULTS.value: protocol_dict
    }

    return output_dict
