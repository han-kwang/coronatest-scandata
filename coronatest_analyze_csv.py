#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Analyze CSV file into scores.

Created on Sat Feb 12 22:15:29 2022  // @hk_nien
"""
from pathlib import Path
import os
import re
import pandas as pd
import numpy as np

PCODES = dict([
    # Regio Noord
    (1011, 'Amsterdam'),
    (1625, 'Hoorn|Zwaag'),
    (1811, 'Alkmaar'),
    (7471, 'Goor'),
    (7556, 'Hengelo'),
    (7903, 'Hoogeveen'),
    (7942, 'Meppel'),
    (8232, 'Lelystad'),
    (8442, 'Heerenveen'),
    (8911, 'Leeuwarden'),
    (9291, 'Kollum'),
    (9501, 'Stadskanaal'),
    (9726, 'Groningen'),

    # Regio Midden
    (2406, 'Alphen a/d Rijn'),
    (2515, 'Den Haag'),
    (3013, 'Rotterdam'),
    (3511, 'Utrecht'),
    (3901, 'Veenendaal'),
    ((7137, 7131), 'Lichtenvoorde|Groenlo'),
    (7311, 'Apeldoorn'),
    (8011, 'Zwolle'),

    # Regio Zuid
    (4325, 'Renesse'),
    (4462, 'Goes'),
    (4701, 'Roosendaal'),
    (5038, 'Tilburg'),
    (5401, 'Uden'),
    (5611, 'Eindhoven'),
    (5801, 'Oostrum'),
    (6101, 'Echt'),
    (6229, 'Maastricht'),
    (6541, 'Nijmegen'),
    ])


def get_bad_scan_times():
    """Return list of Timestamps with bad scan times, from CSV data."""
    df = pd.read_csv('data-ggd/ggd_bad_scans.txt', comment='#')
    tstamps = pd.to_datetime(df['Timestamp']).to_list()
    return tstamps

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
    multi_pcs = {}  # pc4 -> (pc4[0], pc4[1], ...)
    for pc in PCODES:
        if isinstance(pc, tuple):
            for pc1 in pc:
                multi_pcs[pc1] = pc

    qtms = []
    dhm = _delta_time_hhmm
    for pc4, vlist in summary.items():
        pc4 = int(pc4)
        if pc4 not in scores:
            if pc4 in multi_pcs:
                pc4_key = multi_pcs[pc4]
            else:
                print(f'{pc4} not in list...')
                continue
        else:
            pc4_key = pc4
        if len(vlist) == 0:
            scores[pc4_key] = 7
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
                scores[pc4_key] = s
                break
    if len(qtms) == 0:
        qtm_mid = pd.Timestamp(None)
    else:
        qtm_min = min(qtms)
        qtm_mid = qtm_min + (max(qtms) - qtm_min)/2
    return scores, qtm_mid


def _get_min_wait(summary):
    """Return minimum wait Timedelta between scan time and appointment.

    May be NaT if there is no data.
    """
    wtimes = []
    for _, vlist in summary.items():
        wtimes += [atm - qtm for qtm, atm in vlist]
    if len(wtimes) == 0:
        return pd.Timedelta(None)
    return min(wtimes)


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

def load_multi_csvs(csv_fnames):
    """Return DataFrame and list of start times (+1)"""
    dfs = []
    start_tms = []
    for f in csv_fnames:
        df, st = load_csv(f)
        dfs.append(df)
        start_tms.extend(st[:-1])
    df = pd.concat(dfs).reset_index()
    start_tms.append(df.iloc[-1]['scan_time'] + pd.Timedelta('1 min'))
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
    - min_wait: Timedelta of minimum wait time from scan to appointment
    """
    mask = (df['scan_time'] >= tm_range[0]) & (df['scan_time'] < tm_range[1])
    df1 = df.loc[mask]
    summary = {}
    for pc4, city_re in PCODES.items():
        pc4_tup = (pc4,) if isinstance(pc4, int) else pc4
        options = []
        req_pc4 = None
        for _, row in df1.loc[df1['req_pc4'].isin(pc4_tup)].iterrows():
            req_pc4 = int(row['req_pc4'])
            for i in range(3):
                addr = row[f'opt{i}_short_addr']
                if addr and re.match(f'{city_re}$', addr[5:]):
                    options.append((row['scan_time'], row[f'opt{i}_time']))
        if req_pc4 is not None:
            summary[req_pc4] = options
    scores, tstamp = _summary_to_scores(summary)
    if pd.isna(tstamp):
        tstamp = df1.iloc[len(df1)//2]['scan_time']

    minwait = _get_min_wait(summary)
    return tstamp, scores, minwait


def get_scan_scores_df(df, tm_ranges, decimal_comma=True):
    """Get scan scores as dataframe, from csv dataframe.

    Blacklisted scan times are dropped.

    Parameters:

    - df: DataFrame with scan_time, req_date, req_pc4, opt0_short_addr,
      opt0_time, opt0_loc_id, etc.
    - tm_ranges: list of timestamps (+one at the end) with boundaries
      of timestamp ranges.
    - decimal_comma: True to have string values 6,3 rather than float 6.3.

    Return:

    - Dataframe with scores, date_str, time_str, pc4, min_wait as columns.
    """
    n = len(tm_ranges)
    records = []
    index = []
    minwait_hs = []
    bad_stimes = get_bad_scan_times()
    for i in range(n-1):
        tm_ra = tm_ranges[i:i+2]
        is_ok = True
        for tm in bad_stimes:
            if tm_ra[0] <= tm < tm_ra[1]:
                is_ok = False
                break
        if not is_ok:
            print(f'Dropped scan at {tm_ra[0].strftime("%Y-%m-%d %H:%M")}')
            continue
        if i == n-2:
            print('here')

        tm, scores, minwait = get_scan_scores(df, tm_ra)
        records.append(scores)
        index.append(tm)
        minwait_hs.append(minwait.total_seconds() / 3600)

    dates = [t.strftime('%Y-%m-%d') for t in index]
    times = [t.strftime('%H:%M') for t in index]
    sdf = pd.DataFrame.from_records(records)
    sdf.insert(0, 'Time', times)
    sdf.insert(0, 'Date', dates)
    sdf['min_wait_h'] = np.around(minwait_hs, 2)
    sdf.loc[sdf['min_wait_h'].isna(), 'min_wait_h'] = 999
    sdf.columns = [
        ('/'.join([str(x) for x in c]) if isinstance(c, tuple) else c)
        for c in sdf.columns
        ]
    if decimal_comma:
        for c in sdf.columns[2:]:
            sdf[c] = sdf[c].astype(str)
            sdf[c] = sdf[c].str.replace('.', ',', regex=False)
            sdf[c] = sdf[c].str.replace(',0$', '', regex=False)
            sdf[c] = sdf[c].str.replace('?', '', regex=False)

    return sdf


if __name__ == '__main__':

    in_spyder = ('SPYDER_ARGS' in os.environ)
    csv_fnames = sorted(Path('data-ggd').glob('ggd_scan-????-W??.csv'))
    if in_spyder and input('(A)ll or latest?').lower() == 'a':
        df, start_tms = load_multi_csvs(csv_fnames)
        sdf = get_scan_scores_df(df, start_tms).iloc[::-1]
    else:
        df, start_tms = load_csv(csv_fnames[-1])
        sdf = get_scan_scores_df(df, start_tms[-2:])
    print(sdf)
    if len(sdf) > 1:
        sdf.to_clipboard(index=False)
        print('Copied to clipboard including headers')
    elif len(sdf) == 1:
        sdf.iloc[[0], 2:].to_clipboard(header=False, index=False)
        print('Copied to clipboard, scores only.')
    else:
        print('No output.')

    if not in_spyder:
        # Note: in Spyder, copy/paste will stall while input is blocked.
        input('Press Enter to quit and clear clipboard.')

