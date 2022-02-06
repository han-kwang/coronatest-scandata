#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Analyze SON scan csv file. You can run this as a script.

Copyright Han-Kwang Nienhuys (2022) - Twitter: @hk_nien
License: MIT.

Created on Sat Feb  5 23:28:03 2022
"""
from pathlib import Path
import pandas as pd

def get_csv_as_dataframe(csv_fname='data-son/son_scan-latest.csv'):
    """Load CSV file(s) and do minor preprocessing.

    Parameters:

    - csv_fname: CSV filename (str) or list of str.

    Return:

    - df: DataFrame with CSV contents; timestamps converted to pandas Timestamp.
    - scan_times: list of scan start times (Timestamps). Use this for
      slicing the DataFrame into separate scans.

    Note: csv files will be put into chronological order, but it won't handle
    overlapping ranges for 'scan_time'.
    """
    if isinstance(csv_fname, str):
        csv_fnames = [csv_fname]
    else:
        csv_fnames = list(csv_fname)

    df_list = [
        pd.read_csv(fn, comment='#')
        for fn in csv_fnames
        ]
    df_list = sorted(df_list, key=lambda df: df.iloc[0]['scan_time'])
    df = pd.concat(df_list).reset_index().drop(columns='index')
    df['scan_time'] = pd.to_datetime(df['scan_time'])
    df['apt_date'] = pd.to_datetime(df['apt_date'])

    # figure out scan periods
    dts = df['scan_time'].diff()
    dts.iloc[0] = pd.Timedelta('1d')
    scan_start_tms = df.loc[dts > pd.Timedelta('15min'), 'scan_time'].to_list()

    return df, scan_start_tms

def analyze_son_csv(
        csv_fname='data-son/son_scan-latest.csv', irange=(0, None),
        first_notnew=True
        ):
    """Analyze SON csv data; print results.

    Parameters:

    - csv_fname: CSV filename (str) OR list of multiple files.
    - irange: index range, like a slice [a:b] or default [0:].
    - first_notnew: True to suppress 'New locations' on first entry.
    """
    df, scan_start_tms = get_csv_as_dataframe(csv_fname)
    prev_addresses = set()
    iscans = list(range(len(scan_start_tms)))[irange[0]:irange[1]]
    scan_start_tms.append(scan_start_tms[-1] + pd.Timedelta('1h'))
    # Add one so that each scan can be treated as interval.

    for i_scan in iscans:
        tm0, tm1 = scan_start_tms[i_scan:i_scan+2]
        print(f'\n===== scan {tm0.strftime("%Y-%m-%d %H:%M")} =====')
        select = (df['scan_time'] >= tm0) & (df['scan_time'] < tm1)
        df1 = df.loc[select]
        addresses = set(df1['short_addr'].unique())
        print(f'* Aantal locaties: {len(addresses)}.')
        if addresses == prev_addresses:
            print(f'* Geen wijzigingen in locaties.')
        else:
            appeared = sorted(addresses - prev_addresses)
            disappd = sorted(prev_addresses - addresses)
            prev_addresses = addresses
            if appeared and (not first_notnew or i_scan != iscans[0]):
                print(f'* Nieuw: {", ".join(appeared)}.')
            if disappd:
                print(f'* Verdwenen: {", ".join(disappd)}.')

        apt_dates = sorted(df1['apt_date'].unique())
        for apt_date in apt_dates:
            apt_date_str = pd.Timestamp(apt_date).strftime('%Y-%m-%d')
            print(f'* Scan afspraak op {apt_date_str}:')
            select1 = df['apt_date'] == apt_date
            df2 = df1.loc[select1]
            captot = df2['num_slots'].sum()
            capused = df2['num_booked'].sum()
            cap2tot = df2['num_slots_2h'].sum()
            cap2used = df2['num_booked_2h'].sum()
            cap45tot = df2['num_slots_45m'].sum()
            cap45used = df2['num_booked_45m'].sum()
            # biggest bookings
            ntop = 3
            df3 = df2.sort_values('num_booked', ascending=False)
            topbooks = [
                f'{row["short_addr"]} ({row["num_booked"]}/{row["num_slots"]})'
                for _, row in df3.iloc[:ntop].iterrows()
                ]
            topbooks = ", ".join(topbooks)
            percent = lambda a, b: f'{100*a/b:.1f}%' if b > 0 else '-- %'

            print(
                f'  - Gebruikt:          {capused}/{captot} ({percent(capused, captot)})\n'
                f'  - Gebruikt (2h):     {cap2used}/{cap2tot} ({percent(cap2used, cap2tot)})\n'
                f'  - Gebruikt (45m):    {cap45used}/{cap45tot} ({percent(cap45used, cap45tot)})\n'
                f'  - Top-{ntop}: {topbooks}'
                )

def analyze_son_csv_autofind(nfiles=3, irange=(-30, None)):
    """Analysis of multiple recent csv files, autodetect them.

    Paremeters:

    - nfiles: number of recent CSV files to load.
    - irange: index range, like a slice [a:b] or default [0:].
    """
    glob_pattern = 'son_scan-20??-W??.csv'
    flist = list(Path('data-son').glob(glob_pattern))
    if len(flist) == 0:
        raise FileNotFoundError(f'data-son/{glob_pattern}')
    return analyze_son_csv(flist, irange=irange)
            
if __name__ == '__main__':
    analyze_son_csv_autofind()
