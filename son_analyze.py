#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Analyze SON scan csv file. You can run this as a script.

Optional argument of script is a slice (notation 0:) or
list of indices (comma-soparated, e.g. 0,1,-2,-1).

Copyright Han-Kwang Nienhuys (2022) - Twitter: @hk_nien
License: MIT.

Created on Sat Feb  5 23:28:03 2022
"""
import sys
import os
from pathlib import Path
import re
import datetime
import pandas as pd
import numpy as np

def _get_1csv_df(csv_fname):
    """Load csv, return df; handle data without api_version, all_slots column"""
    df = pd.read_csv(csv_fname, comment='#')
    if 'api_version' not in df.columns:
        df['api_version'] = 1
    if 'xfields' not in df.columns:
        df['xfields'] = ''
    else:
        df.loc[df['xfields'].isna(), 'xfields'] = ''
    if 'all_slots' not in df.columns:
        df['all_slots'] = ''
    else:
        df.loc[df['all_slots'].isna(), 'all_slots'] = ''
    return df


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
    if isinstance(csv_fname, (str, Path)):
        csv_fnames = [csv_fname]
    else:
        csv_fnames = list(csv_fname)

    df_list = [_get_1csv_df(fn) for fn in csv_fnames]
    df_list = sorted(df_list, key=lambda df: df.iloc[0]['scan_time'])
    df = pd.concat(df_list).reset_index().drop(columns='index')
    df['scan_time'] = pd.to_datetime(df['scan_time'])
    df['apt_date'] = pd.to_datetime(df['apt_date'])
    # Because of dummy rows, int columns become float.
    for c in df.columns:
        if c.startswith('num') and df[c].dtype != np.int64:
            df.loc[df[c].isna(), c] = 0
            df[c] = df[c].astype(int)

    # figure out scan periods
    dts = df['scan_time'].diff()
    dts.iloc[0] = pd.Timedelta('1d')
    scan_start_tms = df.loc[dts > pd.Timedelta('15min'), 'scan_time'].to_list()

    return df, scan_start_tms


def _analyze_1scan_loc_mutations(df1, prev_addresses, silent=False):
    """Analyze DataFrame for one scan for location mutations.

    Params:

    - df1: 1-scan dataframe slice
    - prev_addresses: set of previous-scan addresess; will be updated.
    - silent: True to suppress output.
    """
    tm0 = df1.iloc[0]['scan_time']
    if np.all(pd.isna(df1['apt_date'])):
        addresses = set()
    else:
        addresses = set(df1['short_addr'].unique())
    if not silent:
        print(f'\n===== scan {tm0.strftime("%Y-%m-%d %H:%M")} =====')
        print(f'* Aantal locaties: {len(addresses)}.')
        if addresses == prev_addresses:
            print('* Geen wijzigingen in locaties.')
        else:
            appeared = sorted(addresses - prev_addresses)
            disappd = sorted(prev_addresses - addresses)
            if appeared:
                print(f'* Nieuw: {", ".join(appeared)}.')
            if disappd:
                print(f'* Verdwenen: {", ".join(disappd)}.')

    prev_addresses.clear()
    prev_addresses.update(addresses)


def _analyze_1scan_slot_stats(df1):
    """Analyze DataFrame for one scan; print output.

    Params:

    - df1: 1-scan dataframe slice
    """
    if  np.all(pd.isna(df1.iloc[0]['apt_date'])):
        return
    # booking categories (name suffix, text label)
    book_cats = [
        ('', 'Geboekt      '),
        ('_2h', 'Geboekt (2h) '),
        ('_45m', 'Geboekt (45m)'),
        ('_15m', 'Geboekt (15m)')
        ]
    if 2 in df1['api_version'].values:
        book_cats = [
            (s, l.replace('Geboekt', 'Volgeboekt'))
            for s, l in book_cats
            ]

    apt_dates = sorted(df1['apt_date'].unique())
    for apt_date in apt_dates:
        apt_date_str = pd.Timestamp(apt_date).strftime('%Y-%m-%d')
        print(f'* Scan afspraak op {apt_date_str}:')
        select1 = df1['apt_date'] == apt_date
        df2 = df1.loc[select1].copy()

        # Special handling of locations with all slots booked.
        # That usually means that the location is not open.
        df2['last_tm'] = pd.to_datetime(f'{apt_date_str}T' + df2['last_tm'])
        suspicious_mask = (
            (df2['last_tm'] - df2['scan_time'] > pd.Timedelta(15, 'min'))
            & (df2['num_slots'] == df2['num_booked'])
            )
        susp_locs = sorted(df2.loc[suspicious_mask, 'short_addr'].unique())
        if susp_locs:
            if len(susp_locs) > 7:
                nlocs = len(df2['short_addr'].unique())
                susp_locs = [f'{len(susp_locs)}/{nlocs} locaties']
            elif len(susp_locs) > 3:
                susp_locs = [x[:8] for x in susp_locs]  # just postcode
            print(f'  - Niet beschikbaar: {", ".join(susp_locs)}.')

        # Detect locations with a limited hours; pattern '----XXXX------'
        partial_mask = df2['all_slots'].str.match('-{4,}X{4,}-*$')
        if partial_mask.sum() > 0:
            locs = sorted(df2.loc[partial_mask, 'short_addr'].unique())
            if len(locs) > 4:
                locs = [f'{x[:8]}' for x in locs]
            print(f'  - Beperkt open: {", ".join(locs)}.')
        suspicious_mask |= partial_mask

        # highest booking rates of the rest
        df3 = df2.loc[~suspicious_mask]
        sums = {}
        for suffix, _ in book_cats:
            sums[f's{suffix}'] = df3[f'num_slots{suffix}'].sum()
            sums[f'b{suffix}'] = df3[f'num_booked{suffix}'].sum()
        ntop = 6
        df4 = df3.loc[df3['num_booked'] > 0].sort_values('num_booked', ascending=False)
        loc_slice = slice(None, None) if len(df4) <= 3 else slice(0, 8)
        topbooks = [
            f'{row["short_addr"][loc_slice]} ({row["num_booked"]}/{row["num_slots"]})'
            for _, row in df4.iloc[:ntop].iterrows()
            ]
        percent = lambda a, b: f'{100*a/b:.1f}%' if b > 0 else '-- %'
        for suffix, label in book_cats:
            a, b = sums[f'b{suffix}'], sums[f's{suffix}']
            if b > 0:
                print(f'  - {label}: {a}/{b} ({percent(a, b)})')
                if a == 0:
                    break

        if topbooks:
            topbooks_str = ", ".join(topbooks)
            print(f'  - Top: {topbooks_str}')


def analyze_son_csv(
        csv_fname='data-son/son_scan-latest.csv',
        islice=(0, None), trange=None,
        ):
    """Analyze SON csv data; print results.

    Parameters:

    - csv_fname: CSV filename (str) OR list of multiple files.
    - islice: index range; as one of:

      - slice(start, stop, step)
      - tuple (start, stop, step) or (start, stop) or (stop,)
      - list/array of indices
    - trange: optional (t_min, t_max) with timezone-naive timestamps.
      (islice will be ignored)
    - first_notnew: True to suppress 'New locations' on first entry.
    """
    df, scan_start_tms = get_csv_as_dataframe(csv_fname)

    if trange is None:
        if isinstance(islice, tuple):
            islice = slice(*islice)
        elif not isinstance(islice, (slice, list, np.ndarray)):
            raise TypeError(f'islice: {type(islice)}')
        iscans = np.arange(len(scan_start_tms))[islice]
        trange = (pd.Timestamp('2000-01-01'), pd.Timestamp('2099-01-01'))
    else:
        iscans = np.arange(len(scan_start_tms))

    scan_start_tms.append(scan_start_tms[-1] + pd.Timedelta('1h'))
    # Add one so that each scan can be treated as interval.

    prev_addresses = set()

    for i_scan in iscans:
        tm0, tm1 = scan_start_tms[i_scan:i_scan+2]
        silent = not (trange[0] <= tm0 < trange[1]) or i_scan == iscans[0]
        select = (df['scan_time'] >= tm0) & (df['scan_time'] < tm1)
        df1 = df.loc[select]
        _analyze_1scan_loc_mutations(df1, prev_addresses, silent=silent)
        if not silent:
            _analyze_1scan_slot_stats(df1)


def analyze_son_csv_autofind(nfiles=3, islice=(-30, None), yearweek=None):
    """Analysis of multiple recent csv files, autodetect them.

    Paremeters:

    - nfiles: number of recent CSV files to load.
    - islice: index range; as one of:

      - slice(start, stop, step)
      - tuple (start, stop, step) or (start, stop) or (stop,)
      - list/array of indices

    - yearweek: optional 'yyyy-Www' string. If specified, ignore islice.
      Produce data for that week.
    """
    glob_pattern = 'son_scan-20??-W??.csv'
    flist = sorted(Path('data-son').glob(glob_pattern))

    if yearweek:
        # This may raise ValueError.
        i = flist.index(Path('data-son') / f'son_scan-{yearweek}.csv')
        if i == 0:
            flist = flist[0:1]
        else:
            flist = flist[i-1:i+1]
        tstart = pd.Timestamp(datetime.datetime.strptime(f'{yearweek}-1', '%G-W%V-%w'))
        tstop = tstart + pd.Timedelta(7, 'd')
        trange = (tstart, tstop)
    else:
        trange = None

    if len(flist) == 0:
        raise FileNotFoundError(f'data-son/{glob_pattern}')
    return analyze_son_csv(flist, islice=islice, trange=trange)


def build_locs_table_by_day():
    """Return DataFrame."""
    fnames = sorted(Path('data-son').glob('son_scan-????-W??.csv'))
    df, scan_tms = get_csv_as_dataframe(fnames)
    # dict; key='yyyy-mm-dd', value=set(loc_names).
    locs_by_date = {}
    all_locs = set()
    for i in range(len(scan_tms)-1):
        mask = (df['scan_time'] >= scan_tms[i]) & (df['scan_time'] < scan_tms[i+1])
        df1 = df.loc[mask]
        apt_date = pd.Timestamp(df1['apt_date'].unique()[0])
        apt_date_str = apt_date.strftime('%Y-%m-%d')
        if apt_date not in locs_by_date:
            locs_by_date[apt_date_str] = set()
        loc_set = locs_by_date[apt_date_str]
        df2 = df1.loc[df1['apt_date'] == apt_date]
        for _, row in df2.iterrows():
            if row['num_slots'] - row['num_booked'] > 0:
                loc_set.add(row['short_addr'])
                all_locs.add(row['short_addr'])

    loc_df = pd.DataFrame(index=sorted(all_locs))
    for ymd, locs in locs_by_date.items():
        loc_df[ymd] = False
        loc_df.loc[locs, ymd] = True

    return loc_df
    # janee = np.array(['n', 'j'])
    # for col in loc_df.columns:
    #     loc_df[col] = janee[loc_df[col].values.astype(int)]



def plot_locs_table(loc_df):
    """Plot table from result of build_locs_table_by_day()."""

    import matplotlib.pyplot as plt
    plt.close('all')
    fig, ax = plt.subplots(
        tight_layout=True,
        figsize=(2+0.2*loc_df.shape[1], 2+0.2*loc_df.shape[0])
        )
    ax.matshow(loc_df, cmap='Greys', vmax=2)
    ax.set_xticks(np.arange(loc_df.shape[1]))
    ax.set_yticks(np.arange(loc_df.shape[0]))
    ax.set_xticklabels(loc_df.columns, rotation=90)
    ax.set_yticklabels(loc_df.index)
    for i in range(loc_df.shape[0]):
        for j in range(loc_df.shape[1]):
            if loc_df.iloc[i, j]:
                ax.text(j, i, 'J', ha='center', va='center')
    for i in range(loc_df.shape[0]-1):
        ax.axhline(i+0.5, color='#bbbbbb')
    for j in range(loc_df.shape[1]-1):
        ax.axvline(j+0.5, color='#bbbbbb')

    fig.show()



def run_cmdline(*args):
    if args:
        argv = ['call'] + [str(x) for x in args]
    else:
        argv = sys.argv
    islice = (-5, None)
    if len(argv) > 2:
        sys.stderr.write(
            f'Use: {argv[0]} [slice|week]\n'
            'slice examples: \'0:-1\' or \'0,-1,-2\'.\n'
            'week example: 2022-W05'
            f'Default: \'{islice}\'.'
        )
        sys.exit(1)

    islice = (-30, None)
    yearweek = None
    if len(argv) == 2:
        arg = argv[1]
        if re.match('\d\d\d\d-W\d\d$', arg):
            yearweek = arg
        elif ':' in arg:
            islice = tuple((int(i) if i else None) for i in arg.split(':'))
        else:
            islice = np.array([int(i) for i in arg.split(',')])

    analyze_son_csv_autofind(islice=islice, yearweek=yearweek)


if __name__ == '__main__':
    if 'SPYDER_ARGS' in os.environ:
        analyze_son_csv_autofind()
        loc_df = build_locs_table_by_day()
        plot_locs_table(loc_df)
    else:
        # command line
        run_cmdline()
