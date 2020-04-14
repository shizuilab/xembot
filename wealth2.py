# coding: utf-8
# 現物売り買い逆張りバージョン
# 利確2%
# 損切-1%
# ask = 買い　bid = 売り（zaifAPIは逆）

import datetime,time
from zaifapi import ZaifPublicStreamApi,ZaifTradeApi
import json
from functools import partial
from pprint import pprint
import os

TARGET_CURRENCY_PAIR = 'xem_jpy'
MY_CURRENCY = 'xem'

zaif_keys_json = open('/home/pi/zaif/xem2_keys.json', 'r')
zaif_keys = json.load(zaif_keys_json)

KEY = zaif_keys["key"]
SECRET = zaif_keys["secret"]

def print_colored(code, text, is_bold=False):
    if is_bold:
        code = '1;%s' % code

    print('\033[%sm%s\033[0m' % (code, text))

print_green = partial(print_colored, '32')
print_blue = partial(print_colored, '34')
print_red = partial(print_colored, '31')
print_yellow = partial(print_colored, '33')

def do_trade(my_trade, askbid, last_price, bid_price, ask_price, funds_my_currency, funds_jpy, my_MACD, sigma, upper, lower, mean):
    my_bid_drift = 0.0001
    my_ask_drift = 0.0001

    with open ('/home/pi/zaif/trade-size.txt','r') as f:
        bid_amount = float(f.read())
        if(funds_jpy < (bid_price + my_bid_drift) * bid_amount):
            bid_amount = round(funds_jpy/(bid_price + my_bid_drift) - 0.1, 1)
    #if bid_amount < 0.1:
    #    askbid = 'ask'

    if 'ask' in askbid:
        try:
            my_price = round(0.0001 * int((bid_price + my_bid_drift)*10000),4)
            print_red('◆◆◆ 買いモード (' + str(my_price) + ', ' + str(bid_amount) + ') ◆◆◆')
            if(funds_jpy >= my_price * bid_amount and bid_amount >= 0.1):
                trade_result = my_trade.trade(currency_pair=TARGET_CURRENCY_PAIR, action="bid", price=my_price, amount=bid_amount)
                #print(trade_result)
                with open('/var/tmp/history.txt', 'w') as f:
                    f.write('Buying XEM')
                with open('/var/tmp/timestamp.txt', 'w') as f:
                    f.write(str(my_price) + ' ' + str(bid_amount))
                if(trade_result["order_id"] == 0):
                    print_red('■ 買い成功しました。', is_bold=True)
                    with open('/var/tmp/mylastprice.txt', 'w') as f:
                        f.write(str(my_price))
                else:
                    print_red('■ 買い注文を出しています', is_bold=True)
                    with open('/var/tmp/mylastprice.txt', 'w') as f:
                        f.write(str(my_price))
                    time.sleep(60)
        except Exception as e:
            time.sleep(5)
            print_red(str(e.args))

    elif 'bid' in askbid:
        try:
            my_price = round(0.0001 * int((ask_price - my_ask_drift)*10000), 4)
            with open('/var/tmp/mylastprice.txt', 'r') as f:
                mylastprice = float(f.read())
            ask_amount = round(funds_my_currency - 0.1, 1)
            print_green('◆◆◆ 売りモード (' + str(my_price) + ', ' + str(ask_amount) + ') ◆◆◆')
            if(ask_amount >= 0.0001 and my_price > mylastprice * 1.02):
                trade_result = my_trade.trade(currency_pair=TARGET_CURRENCY_PAIR, action="ask", price=my_price, amount=ask_amount)
                #print(trade_result)
                with open('/var/tmp/history.txt', 'w') as f:
                    f.write('Selling XEM')
                with open('/var/tmp/timestamp.txt', 'w') as f:
                    f.write(str(my_price) + ' ' + str(ask_amount))
                if(trade_result["order_id"] == 0):
                    print_green('■ 売り成功しました。', is_bold=True)
                    #os.system('aplay /home/pi/zaif/sound/chime10.wav > /dev/null 2>&1')
                else:
                    print_green('■ 売り注文を出しました', is_bold=True)
                    #os.system('aplay /home/pi/zaif/sound/chime13.wav > /dev/null 2>&1')
                    time.sleep(60)
            elif(ask_amount >= 0.0001 and my_price < mylastprice * 0.99):
                trade_result = my_trade.trade(currency_pair=TARGET_CURRENCY_PAIR, action="ask", price=my_price, amount=ask_amount)
                #print(trade_result)
                with open('/var/tmp/history.txt', 'w') as f:
                    f.write('Selling XEM')
                with open('/var/tmp/timestamp.txt', 'w') as f:
                    f.write(str(my_price) + ' ' + str(ask_amount))
                if(trade_result["order_id"] == 0):
                    print_green('■ 損切り売り成功しました。', is_bold=True)
                    #os.system('aplay /home/pi/zaif/sound/chime10.wav > /dev/null 2>&1')
                else:
                    print_green('■ 損切り売り注文を出しました', is_bold=True)
                    #os.system('aplay /home/pi/zaif/sound/chime13.wav > /dev/null 2>&1')
                    time.sleep(60)
            else:
                print_red("売り禁止範囲！")
        except Exception as e:
            time.sleep(5)
            print_green(str(e.args))

    elif 'cancel' in askbid:
        print_yellow('◆◆◆ キャンセルモード ◆◆◆')

    else:
        print_yellow('◆◆◆ 待機中 ◆◆◆')


def main():
    """
    Mainです
    """
    zaif_stream = ZaifPublicStreamApi()
    old_jpy = 0.0
    old_my_currency = 0.0
    my_trade_size = 0.1

    try:
        with open('/var/tmp/history.txt', 'w') as f:
            f.write('Starting UP')
        with open('/var/tmp/timestamp.txt', 'w') as f:
            f.write('No Trade yet')
        # StreamAPIはジェネレータを戻しているのでこれでずっといける
        for stream in zaif_stream.execute(currency_pair=TARGET_CURRENCY_PAIR):
            time_str = stream['timestamp']
            trade_time = datetime.datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S.%f')
            trade_unixtime = int(trade_time.strftime('%s'))
            current_unixtime = int(time.time())
            delay_time = current_unixtime - trade_unixtime
            last_price = stream['last_price']['price']
            bid_price = stream['bids'][0][0]
            ask_price = stream['asks'][0][0]
            print('bid_price:', bid_price, 'ask_price', ask_price)

            try:
                if(delay_time < 60):
                    zaif_trade = ZaifTradeApi(KEY,SECRET)

                    funds_my_currency = zaif_trade.get_info2()['funds'][MY_CURRENCY]
                    funds_jpy = zaif_trade.get_info2()['funds']['jpy']
                    print(
                        '◆◆◆',time_str, '(', delay_time, '秒)','◆◆◆')
                    print_yellow(' ■ 終値:' + str(last_price), 1)
                    mystr = ' ■ JPY 残高:' + str(funds_jpy)
                    print_blue(mystr, 1)

                    mystr = " ■ XEM 残高:" + str(funds_my_currency)
                    print_blue(mystr, 1)

                    with open('/var/tmp/MACD.txt', 'r') as f:
                        my_MACD = float(f.read())
                    with open('/var/tmp/sigma.txt','r') as f:
                        sigma = float(f.read())
                    with open('/var/tmp/mean.txt','r') as f:
                        mean = float(f.read())
                    with open('/var/tmp/upper.txt','r') as f:
                        upper = float(f.read())
                    with open('/var/tmp/lower.txt','r') as f:
                        lower = float(f.read())
                    with open('/var/tmp/ask-bid.txt', 'r') as f:
                        my_ask_bid = f.read()

                    with open('/var/tmp/ask-price.txt', 'w') as f:
                        f.write(str(ask_price))
                    with open('/var/tmp/bid-price.txt', 'w') as f:
                        f.write(str(bid_price))
                    #print_yellow('tmpファイル読み込み終了',1)

                    do_trade(zaif_trade, my_ask_bid, last_price, bid_price, ask_price, funds_my_currency, funds_jpy, my_MACD, sigma, upper, lower, mean)

                    my_trade_history = zaif_trade.trade_history(count=1, currency_pair = TARGET_CURRENCY_PAIR)
                    with open('/var/tmp/history.txt', 'w') as f:
                        for k in my_trade_history:
                            f.write(my_trade_history[k]['your_action'] +' '+ str(my_trade_history[k]['price']) +' '+ str(my_trade_history[k]['amount']))
                    with open('/var/tmp/timestamp.txt', 'w') as f:
                        for k in my_trade_history:
                            trade_time = datetime.datetime.fromtimestamp(float(my_trade_history[k]['timestamp']))
                        f.write(str(trade_time))

                    try:
                        remaining_orders = zaif_trade.active_orders(currency_pair = TARGET_CURRENCY_PAIR)
                        if remaining_orders:
                            print_yellow("注文中:", 1)
                            for id in remaining_orders.keys():
                                print(" ◆",id, remaining_orders[id]['price'])
                                print_yellow("    をキャンセルします",1)
                                zaif_trade.cancel_order(order_id = int(id))
                                os.system('aplay /home/pi/zaif/chime13.wav > /dev/null 2>&1')
                        else:
                            print_yellow(' ◆◆◆ 未決注文はありません ◆◆◆')

                    except Exception as e:
                        time.sleep(1)
                        print_yellow(str(e.args))

            except Exception as e:
                print_yellow(str(e.args), 1)
                time.sleep(5)

    except KeyboardInterrupt:
        print_green('Bye', 1)

if __name__ == '__main__':
    main()

