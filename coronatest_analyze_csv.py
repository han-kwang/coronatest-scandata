#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Analyze CSV file into scores.

Created on Sat Feb 12 22:15:29 2022  // @hk_nien
"""
from pathlib import Path
import os
import pandas as pd
import numpy as np

PCODES = dict([
    (3511, 'Utrecht'),
    (5611, 'Eindhoven'),
    (5038, 'Tilburg'),
    (9726, 'Groningen'),
    (8011, 'Zwolle'),
    (6041, 'Roermond'),
    (1011, 'Amsterdam'),
    (3013, 'Rotterdam'),
    (2515, 'Den Haag'),
    (7311, 'Apeldoorn'),
    (6229, 'Maastricht'),
    (7556, 'Hengelo'),
    (6541, 'Nijmegen'),
    (8911, 'Leeuwarden'),
    (8232, 'Lelystad'),
    (4462, 'Goes'),
    (9501, 'Stadskanaal'),
    (1625, 'Hoorn'),
    (9291, 'Kollum'),
    (5401, 'Uden'),
    (7903, 'Hoogeveen'),
    (7942, 'Meppel'),
    (7471, 'Goor'),
    (5801, 'Oostrum'),
    ])


def _mean_time(ts_list):
    """Return mean timestamp value from list of timestamps."""
    ts0 = ts_list[0]
    delta_sum = pd.Timedelta(0)
    for ts in ts_list:
        delta_sum += (ts -ts0)
    ts_mean = ts0 + delta_sum / len(ts_list)
    return ts_mean


def _delta_time_hhmm(hm):
    """Convert 'hh:mm' string to TimeDelta."""
    return pd.Timedelta(f'{hm}:00')


def _summary_to_scores(summary):
    """Convert summary from _read_log to scores dict and effective timestamp.

    Parameters:

    - summary: dict with int(pc4) -> [(query_time, appt_time), ...]

    Return:

    - scores dict: int(pc4) -> score (int or float or '?')
    - timestamp: middle query timestamp of this run.
    """

    # Convert to number codes.
    scores = {k: '?' for k in PCODES}
    qtms = []
    dhm = _delta_time_hhmm
    for pc4, vlist in summary.items():
        pc4 = int(pc4)
        if pc4 not in scores:
            print(f'{pc4} not in list...')
            continue
        if len(vlist) == 0:
            scores[pc4] = 7
            continue
        qtm = _mean_time([v[0] for v in vlist]) # query time
        qtms.append(qtm)
        atm = min(v[1] for v in vlist) # earliest appointment time
        qtm_00 = pd.Timestamp(qtm.strftime('%Y-%m-%dT00:00'))
        thresholds = [
            (3, qtm_00 + dhm('23:59')),
            (4, qtm + dhm('24:00')),
            (5, qtm_00 + dhm('48:00')),
            (6, qtm + dhm('48:00')),
            (6.3, qtm_00 + dhm('72:00')),
            (6.7, qtm + dhm('72:00')),
            (7, atm)
            ]
        if qtm.hour < 9:
            thresholds.insert(0, (1, qtm_00 + dhm('13:00')))
        elif qtm.hour < 13:
            thresholds.insert(0, (1, qtm + dhm('4:00')))
        elif qtm.hour < 17:
            thresholds.insert(0, (1, qtm_00 + dhm('24:00')))
            thresholds.insert(1, (2, qtm + dhm('20:00')))
        else:
            thresholds.insert(0, (1, qtm_00 + dhm('24:00')))
            thresholds.insert(1, (2, qtm_00 + dhm('37:00')))

        for s, tm in thresholds:
            if atm < tm:
                scores[pc4] = s
                break
    if len(qtms) == 0:
        qtm_mid = pd.Timestamp('1900-01-01')
    else:
        qtm_min = min(qtms)
        qtm_mid = qtm_min + (max(qtms) - qtm_min)/2
    return scores, qtm_mid


def load_csv(csv_fname):
    """Return DataFrame and list of start times (+1)."""
    df = pd.read_csv(csv_fname, comment='#')
    df['req_pc4'] = df['req_pc4'].astype(int)

    for c in df.columns:
        if c.endswith('_time') or c.endswith('_date'):
            df[c] = pd.to_datetime(df[c])
        else:
            df.loc[df[c].isna(), c] = None

    # start_tms: list of scan start times (plus one extra at the end)
    start_tms = df.loc[df['scan_time'].diff() > pd.Timedelta('10 min'), 'scan_time']
    start_tms = [df.iloc[0]['scan_time']] + list(start_tms)
    start_tms += [df.iloc[-1]['scan_time'] + pd.Timedelta('1 min')]
    return df, start_tms

def get_scan_scores(df, tm_range):
    """Get scan scores as pc4 -> score dict.

    Parameters:

    - df: DataFrame with scan_time, req_date, req_pc4, opt0_short_addr,
      opt0_time, opt0_loc_id, etc.
    - tm_range: (tm_start, tm_stop) timestamps.

    Return:

    - tstamp: timestamp of the scan (mid-point)
    - scores: dict of pc4->score
    """
    mask = (df['scan_time'] >= tm_range[0]) & (df['scan_time'] < tm_range[1])
    df1 = df.loc[mask]
    summary = {}
    for pc4, city in PCODES.items():
        options = []
        for _, row in df1.loc[df1['req_pc4'] == pc4].iterrows():
            for i in range(3):
                addr = row[f'opt{i}_short_addr']
                if addr and addr[5:] == city:
                    options.append((row['scan_time'], row[f'opt{i}_time']))
        summary[pc4] = options
    scores, tstamp = _summary_to_scores(summary)
    return tstamp, scores


def get_scan_scores_df(df, tm_ranges, decimal_comma=True):
    """Get scan scores as dataframe, from csv dataframe.

    Parameters:

    - df: DataFrame with scan_time, req_date, req_pc4, opt0_short_addr,
      opt0_time, opt0_loc_id, etc.
    - tm_ranges: list of timestamps (+one at the end) with boundaries
      of timestamp ranges.
    - decimal_comma: True to have string values 6,3 rather than float 6.3.

    Return:

    - Dataframe with scores, date_str, time_str, pc4 as columns.
    """
    n = len(tm_ranges)
    records = []
    index = []
    for i in range(n-1):
        tm, scores = get_scan_scores(df, tm_ranges[i:i+2])
        records.append(scores)
        index.append(tm)

    dates = [t.strftime('%Y-%m-%d') for t in index]
    times = [t.strftime('%H:%M') for t in index]
    sdf = pd.DataFrame.from_records(records)
    sdf.insert(0, 'Time', times)
    sdf.insert(0, 'Date', dates)
    if decimal_comma:
        for c in sdf.columns[2:]:
            if np.any(sdf[c] != sdf[c].astype(int)):
                # To be pasted into lang-nl spreadsheet that uses
                # decimal comma.
                print(f'{c}: {sdf[c].values}')
                sdf[c] = sdf[c].astype(str)
                sdf[c] = sdf[c].str.replace('.', ',', regex=False)
                sdf[c] = sdf[c].str.replace(',0', '', regex=False)

    return sdf



if __name__ == '__main__':

    csv_fnames = sorted(Path('data-ggd').glob('ggd_scan-????-W??.csv'))
    df, start_tms = load_csv(csv_fnames[-1])
    sdf = get_scan_scores_df(df, start_tms[-2:])
    # sdf = get_scan_scores_df(df, start_tms).iloc[::-1]
    print(sdf)
    if len(sdf) > 1:
        sdf.to_clipboard(index=False)
        print('Copied to clipboard including headers')
    elif len(sdf) == 1:
        sdf.iloc[[0], 2:].to_clipboard(header=False, index=False)
        print('Copied to clipboard, scores only.')
    else:
        print('No output.')

    if 'SPYDER_ARGS' not in os.environ:
        input('Press Enter to quit and clear clipboard.')

