import talib as ta
import sys
from pandas_datareader import data
import datetime
import pandas as pd
import numpy as np
import warnings
warnings.simplefilter('ignore')
from yahoo_finance_api2 import share
from yahoo_finance_api2.exceptions import YahooFinanceError
import streamlit as st
import time

df = pd.read_csv('result.csv')

##データ群全体の取得
press = st.sidebar.header('直近データの取得')
st.write('「表示」を押すと、楽天証券で取引可能な米国市場のETFの直近データ取得を開始します。')
button = st.sidebar.button('表示')
latest_iteration = st.empty()
bar = st.progress(0)

##条件分岐によるデータ取得
st.sidebar.subheader('表示条件設定')
##日足MACD
label_daily_macd = '日足MACD'
options_daily_macd = ['なし','GCを形成・形成しようとしている','DCを形成・形成しようとしている','MACDがSignalを上回っている','MACDがSignalを下回っている']
condition_daily_macd = st.sidebar.selectbox(label_daily_macd,options_daily_macd)
##週足MACD
label_weekly_macd = '週足MACDの条件'
options_weekly_macd = ['なし','GCを形成・形成しようとしている','DCを形成・形成しようとしている','MACDがSignalを上回っている','MACDがSignalを下回っている']
condition_weekly_macd = st.sidebar.selectbox(label_weekly_macd,options_weekly_macd)
note_04 = st.sidebar.text('※GCは1.05<=macd/signal<=0.95かつUptrend')
note_05 = st.sidebar.text('※DCは1.05<=macd/signal<=0.95かつDowntrend')

##RSIの条件設定画面
condition_daily_rsi = st.sidebar.write('日足RSIの条件')
left_column_more = st.sidebar.number_input('以上',min_value=0,max_value=100)
right_column_less = st.sidebar.number_input('以下',min_value=0,max_value=100,value=100)
##週足MACD
condition_weekly_rsi = st.sidebar.write('週足RSIの条件')
left_column_more02 = st.sidebar.number_input('以上',min_value=0,max_value=100,key=100)
right_column_less02 = st.sidebar.number_input('以下',min_value=0,max_value=100,key=100,value=100)
note = st.sidebar.text('※上限のデフォルト値は100です。')
note_01 = st.sidebar.text('※下限のデフォルト値は0です。')

con_button = st.sidebar.button('検索')

##データ取得の関数
def stock_week_day_data(STOCK_CODE):
    ##日足データの取得
    my_share = share.Share(STOCK_CODE)
    hourly_data = None
    daily_data = my_share.get_historical(share.PERIOD_TYPE_MONTH,
                                          10,
                                          share.FREQUENCY_TYPE_DAY,
                                         1)
    
    ##加工平易なデータフレームへと変換
    daily_data = pd.DataFrame(daily_data)
    daily_data.insert(0,'stock_code',STOCK_CODE)
    date_agg=lambda x:datetime.datetime.utcfromtimestamp(x/1000)
    daily_data['timestamp'] = daily_data['timestamp'].apply(date_agg)
    daily_data = daily_data.loc[daily_data['volume']!=0]
    close = daily_data['close']
    
    ##週足データを抽出＊市場数値と若干異なる
    weekly_data = []
    for i in range(len(daily_data)):
        if (i == 0) or (i%5 == 0) or (i == len(daily_data)-1):
            weekly_data.append(daily_data.loc[i])
    weekly_data = pd.DataFrame(weekly_data)
    weekly_data = weekly_data.reset_index()
    weekly_data = weekly_data.drop(columns='index')
    
    ##計算を阻害するNaN値を除去
    daily_data = daily_data.dropna(how='any')
    
    ##RSI,MACDを週足・日足データにそれぞれ追加する
    daily_data['日足RSI'] = ta.RSI(close,timeperiod=14)
    daily_data['日足macd'],daily_data['日足signal'],daily_data['日足hist'] = ta.MACD(daily_data['close'],fastperiod=12,slowperiod=26,signalperiod=9)
    weekly_data['週足RSI'] = ta.RSI(close,timeperiod=14)
    weekly_data['週足macd'],weekly_data['週足signal'],weekly_data['週足hist'] = ta.MACD(weekly_data['close'],fastperiod=12,slowperiod=26,signalperiod=9)

    ##株価のUP or DOWNをMACDによって判断する
    daily_data['日足MACD_trend'] = 0
    weekly_data['週足MACD_trend'] = 0
    
    ##日足のトレンド
    if daily_data['日足hist'].iloc[-1]>daily_data['日足hist'].iloc[-3]:
        daily_data['日足MACD_trend'].iloc[-1] = 'Uptrend'
    else:
        daily_data['日足MACD_trend'].iloc[-1] = 'Downtrend'
    
    ##週足のトレンド
    if weekly_data['週足hist'].iloc[-1]>weekly_data['週足hist'].iloc[-3]:
        weekly_data['週足MACD_trend'].iloc[-1] = 'Uptrend'
    else:
        weekly_data['週足MACD_trend'].iloc[-1] = 'Downtrend'

    ##週足・日足データフレームを統合する・整理する
    stock_week_day_data = pd.merge(daily_data,weekly_data)
    temporary_data = stock_week_day_data['日足MACD_trend']
    stock_week_day_data = stock_week_day_data.drop(columns='日足MACD_trend')
    stock_week_day_data.insert(15,'日足MACD_trend',temporary_data)
    
    ##データの最後だけ取得
    stock_week_day_data = stock_week_day_data.tail(1)
    stock_week_day_data = stock_week_day_data.reset_index()
    stock_week_day_data = stock_week_day_data.drop(columns='index')
    
    return stock_week_day_data

if button:
    info_list = []
    x = 0
    ##関数をループで実行する
    for i in range(len(df)):
        try:
            stock_data = stock_week_day_data(df['現地コード'][i])
            info_list.append(stock_data)       
            latest_iteration.text(f'Iteration {(i+1)}/{len(df)}')
            bar.progress((i+1)/len(df))
        except KeyError:
            latest_iteration.text(f'Iteration {(i+1)}/{len(df)} ERROR')
            bar.progress((i+1)/len(df))
            continue
            
    ##リスト化されたETFの情報を投合する
    info_list = pd.concat(info_list)
    info_list = info_list.reset_index()
    info_list = info_list.drop(columns='index')
    st.write(info_list,width=200,height=1000)
    info_list.to_csv('stock_data.csv')

##条件によって得られるデータを表示
if con_button:
    info_list = pd.read_csv('stock_data.csv')
    daily_dict = {
        'なし':info_list,
        'GCを形成・形成しようとしている':info_list[(info_list['日足macd']/info_list['日足signal'] >= 0.95) & (info_list['日足macd']/info_list['日足signal'] <= 1.05) & (info_list['日足MACD_trend'] == 'Uptrend')],
        'DCを形成・形成しようとしている':info_list[(info_list['日足macd']/info_list['日足signal'] >= 0.95) & (info_list['日足macd']/info_list['日足signal'] <= 1.05) & (info_list['日足MACD_trend'] == 'Uptrend')],
        'MACDがSignalを上回っている':info_list[info_list['日足macd'] >= info_list['日足signal']],
        'MACDがSignalを下回っている':info_list[info_list['日足macd'] < info_list['日足signal']]}
    weekly_dict = {
        'なし':info_list,
        'GCを形成・形成しようとしている':info_list[(info_list['週足macd']/info_list['週足signal'] >= 0.95) & (info_list['週足macd']/info_list['週足signal'] <= 1.05) & (info_list['週足MACD_trend'] == 'Uptrend')],
        'DCを形成・形成しようとしている':info_list[(info_list['週足macd']/info_list['週足signal'] >= 0.95) & (info_list['週足macd']/info_list['週足signal'] <= 1.05) & (info_list['週足MACD_trend'] == 'Uptrend')],
        'MACDがSignalを上回っている':info_list[info_list['週足macd'] >= info_list['週足signal']],
        'MACDがSignalを下回っている':info_list[info_list['週足macd'] < info_list['週足signal']]}


    info_list = daily_dict[condition_daily_macd]
    info_list = weekly_dict[condition_weekly_macd]

    info_list = info_list[(info_list['日足RSI'] >= left_column_more)&(info_list['日足RSI'] <= right_column_less)]
    info_list = info_list[(info_list['週足RSI'] >= left_column_more02)&(info_list['週足RSI'] <= right_column_less02)]

    st.write(info_list)


