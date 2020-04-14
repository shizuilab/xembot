# coding: utf-8
# レンジ除外MA2 < - 30
# -30 < MA2 < 0 でキャンセルモード
# トレンド（MA2）計算バージョン
# 売り買いをwealth2.pyへ
# 下げ相場では売りを行う
# MACD&ボリンジャーバンド計算
# sqlite導入
# last_priceにask_priceとbid_priceの平均値を使うテスト
# ボラティリティー対策：MACDを% of mean price x 1000で補正
# 同じタイムスタンプで返ってくる＞sqliteエラー
# 動的threshold-sell,buy = +- sigma
# MACD > sigma で順張りに切り替え

import datetime,time
from zaifapi import ZaifPublicStreamApi,ZaifTradeApi
import json
from functools import partial
import random
import numpy as np
import pandas as pd
import sqlite3
from sqlite3 import Error

TARGET_CURRENCY_PAIR = 'xem_jpy'
MY_CURRENCY = 'xem'
HISTORY_LIMIT_COUNT = 1200

ALPHA1 = 0.09524
ALPHA2 = 0.00499
ALPHA3 = 0.00995

def create_connection(db_file):
    try:
        conn = sqlite3.connect(db_file)
        return conn
    except Error as e:
        print(e)
    return None

def create_xemdb(conn, xemdb):
    """
    Create a new history into the xemdbs table
    :param conn:
    :param xemdb:
    :return: project id
    """

    sql = ''' INSERT INTO xemdbs(timestamp, last_price)
            VALUES(?,?) '''
    cur = conn.cursor()
    cur.execute(sql, xemdb)
    return cur.lastrowid

def create_table(conn, create_table_sql):
    try:
        c = conn.cursor()
        c.execute(create_table_sql)
    except Error as e:
        print(e)

def print_colored(code, text, is_bold=False):
    if is_bold:
        code = '1;%s' % code

    print('\033[%sm%s\033[0m' % (code, text))

print_green = partial(print_colored, '32')
print_blue = partial(print_colored, '34')
print_red = partial(print_colored, '31')
print_yellow = partial(print_colored, '33')

class PriceHistory:

    def __init__(self, history_limit_count=HISTORY_LIMIT_COUNT):
        self.price_history = []
        self.history_limit_count = history_limit_count

    def add_history(self, last_price):
        """
        Adds new history
        :param TradeData trade_data:
        :return:
        """
        self.price_history.append(last_price)
        if len(self.price_history) > self.history_limit_count:
            self.price_history = self.price_history[-self.history_limit_count:]
        #print(self.price_history)

class TradeData:
    """
    ある時点での取引情報
    """

    def __init__(self, trade_time, last_price, trades, asks, bids):

        """
        :param trade_time: 情報時刻
        :param last_price: 終値
        :param list trades: 取引実績
        :param list[float float] asks: ask一覧
        :param list[float float] bids: bid一覧
        """
        self.trade_time = trade_time
        self.last_price = last_price
        self.trades = trades
        self.asks = asks
        self.bids = bids

        bid_data = self._get_calculated_trades('bid')
        self.trade_bid_amount = bid_data['amount']
        self.trade_bid_max = bid_data['max_price']
        self.trade_bid_min = bid_data['min_price']
        self.trade_bid_avg = bid_data['avg_price']

        ask_data = self._get_calculated_trades('ask')
        self.trade_ask_amount = ask_data['amount']
        self.trade_ask_max = ask_data['max_price']
        self.trade_ask_min = ask_data['min_price']
        self.trade_ask_avg = ask_data['avg_price']

        self.depth_ask_amount, self.depth_ask_avg = self._get_calculated_depth('ask')
        self.depth_bid_amount, self.depth_bid_avg = self._get_calculated_depth('bid')

    def _get_calculated_trades(self, trade_type):
        """
        トレード情報をまとめて、平均価格や取引量を求める
        :param trade_type:
        :return:
        """
        target_list = [tr for tr in self.trades if tr['trade_type'] == trade_type]

        total = sum([tr['price'] * tr['amount'] for tr in target_list])
        amount = sum([tr['amount'] for tr in target_list])
        # 取引量が0の場合は終値をそのまま採用する
        if amount:
            avg_price = round(total / amount, 3)
            max_price = max([tr['amount'] for tr in target_list])
            min_price = min([tr['amount'] for tr in target_list])
        else:
            avg_price = self.last_price
            max_price = self.last_price
            min_price = self.last_price

        return {
            'amount': amount,
            'max_price': max_price,
            'min_price': min_price,
            'avg_price': avg_price
        }

    def _get_calculated_depth(self, board_type):
        """
        板情報をまとめて、平均価格や取引量を求める
        :param board_type:
        :return:
        """
        target_data = None
        if board_type == 'ask':
            target_data = self.asks
        if board_type == 'bid':
            target_data = self.bids
        trade_amount = sum([tr[1] for tr in target_data])
        trade_total = sum([tr[0] * tr[1] for tr in target_data])
        return trade_amount, round(trade_total/trade_amount, 3)

def main():
    """
    メイン
    """

    database = "/home/pi/zaif/zaif_xem.db"

    sql_create_xemdb_table = """ CREATE TABLE IF NOT EXISTS xemdbs (
                                        timestamp text,
                                        last_price real
                                    ); """

    conn = create_connection(database)
    if conn is not None:
        create_table(conn, sql_create_xemdb_table)
    else:
        print("Error, could not create database")

    zaif_stream = ZaifPublicStreamApi()
    ph = PriceHistory()
    count = 0
    old_trade20 = 0.0
    old_trade200 = 0.0
    old_MACD2 = 0.0
    last_time_str = ""

    cur = conn.execute('SELECT * FROM xemdbs')

    for row in cur:
         ph.add_history(row[1])
         count = count + 1
         trade20 = old_trade20 + ALPHA1 * (row[1] - old_trade20)
         trade200 = old_trade200 + ALPHA2 * (row[1] - old_trade200)
         MACD = trade20 - trade200
         MACD2 = old_MACD2 + ALPHA3 * (MACD - old_MACD2)
         old_trade20 = trade20
         old_trade200 = trade200
         old_MACD2 = MACD2
    cur.close()
    print(count)

    try:
        # StreamAPIはジェネレータを戻しているのでこれでずっといける
        for stream in zaif_stream.execute(currency_pair=TARGET_CURRENCY_PAIR):
            time_str = stream['timestamp']
            if time_str == last_time_str:
                continue
            try:
                trade_time = datetime.datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S.%f')
            except:
                trade_time = datetime.datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')
            trade_unixtime = int(trade_time.strftime('%s'))
            current_unixtime = int(time.time())
            delay_time = current_unixtime - trade_unixtime
            last_price = stream['last_price']['price']
            trades = stream['trades']
            asks = stream['asks']
            bids = stream['bids']

            bid_price = bids[0][0]
            ask_price = asks[0][0]
            mean_price = (ask_price + bid_price)/2

            last_time_str = time_str

            with conn:
                xemdb = (time_str, mean_price);
                xemdb_id = create_xemdb(conn, xemdb)

            ph.add_history(mean_price)
            count = count + 1
            #print(count, time_str, mean_price)
            #continue

            with open('/var/tmp/price.txt', 'w') as f:
                f.write(str(round(mean_price, 3)))
            with open('/var/tmp/last_price.txt', 'w') as f:
                f.write(str(round(last_price, 4)))

            trade_data = TradeData(trade_time, mean_price, trades, asks, bids)

            trade20 = old_trade20 + ALPHA1 * (mean_price - old_trade20)
            trade200 = old_trade200 + ALPHA2 * (mean_price - old_trade200)
            MACD = trade20 - trade200
            MACD2 = old_MACD2 + ALPHA3 * (MACD - old_MACD2)

            with open('/var/tmp/MA20.txt', 'w') as f:
                f.write(str(trade20))
            with open('/var/tmp/MA200.txt', 'w') as f:
                f.write(str(trade200))
            with open('/var/tmp/MACD.txt', 'w') as f:
                f.write(str(100000*(MACD - MACD2)/mean_price))

            total_pressure = round(trade_data.depth_ask_amount+trade_data.depth_bid_amount)
            ask_pressure = round((trade_data.depth_ask_amount/total_pressure) * 100)

            print(count,time_str,'(', delay_time, '秒)')

            mystr = '  ■ 終値: ' + str(last_price)
            print_yellow(mystr, 1)

            if ask_pressure >= 50:
                mystr = '  ■ ゼムの価格は' + str(round(mean_price,2)) + '円で、買いが強く' + str(ask_pressure) + '%です'

                print_red(mystr)
            else:
                mystr = '  ■ ゼムの価格は' + str(round(mean_price,2)) + '円で、売りが強く' + str(100-ask_pressure) + '%です'
                print_green(mystr)

            if (MACD-MACD2)*10000 < 0:
                mystr = mystr + 'マックディーは、マイナス' + str(round((MACD - MACD2)*100000/last_price)) + 'です'
            else:
                mystr = mystr + 'マックディーは' + str(round((MACD - MACD2)*10000)) + 'です'

            with open('/var/tmp/pressure.txt', 'w') as f:
                f.write(mystr)

            old_trade20 = trade20
            old_trade200 = trade200
            old_MACD2 = MACD2

            mystr = '  ■ MACD - MACD2 = ' + str((MACD - MACD2)*10/mean_price)
            if MACD - MACD2 > 0:
                print_red(mystr)
            elif MACD - MACD2 < 0:
                print_green(mystr)
            else:
                print_yellow(mystr)

            if count > HISTORY_LIMIT_COUNT:
                #Bolinger Band
                s = pd.Series(ph.price_history)
                sigma = s.std() #σの計算
                mean = s.mean() #移動平均値
                mystr = '  ■ sigma = ' + str(sigma)
                print_yellow(mystr)

                with open('/home/pi/zaif/threshold-base-buy.txt', 'r') as f:
                    threshold_base_buy = float(f.read())
                with open('/home/pi/zaif/threshold-base-sell.txt', 'r') as f:
                    threshold_base_sell = float(f.read())
                buy_threshold = threshold_base_buy * sigma;
                sell_threshold = threshold_base_sell * sigma;

                with open('/var/tmp/mean.txt', 'w') as f:
                    f.write(str(mean))
                with open('/var/tmp/sigma.txt', 'w') as f:
                    f.write(str(sigma))
                with open('/var/tmp/upper.txt', 'w') as f:
                    f.write(str(mean + (2 * sigma)))
                with open('/var/tmp/lower.txt', 'w') as f:
                    f.write(str(mean - (2 * sigma)))
                with open('/var/tmp/threshold-buy.txt', 'w') as f:
                    f.write(str(buy_threshold))
                with open('/var/tmp/threshold-sell.txt', 'w') as f:
                    f.write(str(sell_threshold))

            #トレード判断を書き込む
            if count < 2000:
                with open('/var/tmp/ask-bid.txt', 'w') as f:
                    f.write('wait' + str(2000-count))
                print_blue('◆◆◆ 準備中 ◆◆◆', 1)

            elif (MACD - MACD2)*10/mean_price < -1 * sigma:
                with open('/var/tmp/ask-bid.txt', 'w') as f:
                    f.write('bid')
                print_green('◆◆◆ XEM 順売りモード ◆◆◆', 1)

            elif (MACD - MACD2)*10/mean_price > sigma:
                with open('/var/tmp/ask-bid.txt', 'w') as f:
                    f.write('ask')
                print_red('◆◆◆ XEM 順買いモード ◆◆◆', 1)

            elif (MACD - MACD2)*10/mean_price < buy_threshold:
                with open('/var/tmp/ask-bid.txt', 'w') as f:
                    f.write('ask')
                print_red('◆◆◆ XEM 逆買いモード ◆◆◆', 1)

            elif (MACD - MACD2)*10/mean_price > sell_threshold:
                with open('/var/tmp/ask-bid.txt', 'w') as f:
                    f.write('bid')
                print_green('◆◆◆ XEM 逆売りモード ◆◆◆', 1)

            else:
                with open('/var/tmp/ask-bid.txt', 'w') as f:
                    f.write('cancel')
                print_blue('◆◆◆ キャンセルモード ◆◆◆', 1)

            # 売り圧を書き込む
            with open('/var/tmp/ask-pressure.txt', 'w') as f:
                    f.write(str(ask_pressure))

    except KeyboardInterrupt:
        print('Bye')


if __name__ == '__main__':
    main()

