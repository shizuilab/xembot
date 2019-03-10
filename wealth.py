# coding: utf-8
# 資産計算専用ボット
# 約24時間（86000秒）で強制解除<なんで？

import datetime,time
from zaifapi import *
import json
from functools import partial
from pprint import pprint
import os

TARGET_CURRENCY_PAIR = 'xem_jpy'
MY_CURRENCY = 'xem'

zaif_keys_json = open('/home/pi/zaif/xem1_keys.json', 'r')
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

def main():
    """
    Main
    """
    zaif_stream = ZaifPublicStreamApi()
    old_jpy = 0.0
    old_my_currency = 0.0
    my_trade_size = 0.0001

    with open('/var/tmp/starttime.txt', 'w') as f:
        f.write(str(time.time()))

    try:
        # StreamAPIはジェネレータを戻しているのでこれでずっといける
        for stream in zaif_stream.execute(currency_pair=TARGET_CURRENCY_PAIR):
            time_str = stream['timestamp']
            trade_time = datetime.datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S.%f')
            trade_unixtime = int(trade_time.strftime('%s'))
            current_unixtime = int(time.time())
            delay_time = current_unixtime - trade_unixtime
            last_price = stream['last_price']['price']

            try:
                if(delay_time < 2):
                    zaif_trade = ZaifTradeApi(KEY,SECRET)
                    funds_my_currency = zaif_trade.get_info2()['funds'][MY_CURRENCY]
                    funds_jpy = zaif_trade.get_info2()['funds']['jpy']
                    new_jpy = round(funds_my_currency * last_price + funds_jpy, 4)
                    new_my_currency = round(funds_my_currency + funds_jpy/last_price, 4)
                    time.sleep(1)


                    #with open('/var/tmp/blynkaskbid.txt', 'r') as f:
                    #    blynkstatus = f.read()
                    #if 'ready' in blynkstatus:
                    #    with open('/var/tmp/starttime.txt', 'w') as f:
                    #        f.write(str(time.time()))
                    #else:
                    #    with open('/var/tmp/starttime.txt', 'r') as f:
                    #        starttime = float(f.read())

                    with open('/var/tmp/blynkaskbid.txt', 'w') as f:
                        f.write('ready')

                    print('◆◆◆',time_str, '(', delay_time,'秒)','◆◆◆')
                    print_yellow(' ■ 終値:' + str(last_price),1)
                    mystr = ' ■ JPY資産:' + str(round(new_jpy,4))
                    with open('/var/tmp/my-fund.txt', 'w') as f:
                        f.write(str(round(new_jpy,4)))
                    with open('/var/tmp/my-xem.txt', 'w') as f:
                        f.write(str(round(funds_my_currency,4)))

                    if (new_jpy - old_jpy) > 0:
                       print_green(mystr, 1)
                       #os.system('mpg321 /home/pi/zaif/correct2.mp3 > /dev/null 2>&1')
                    elif (new_jpy - old_jpy) < 0:
                       print_red(mystr, 1)
                       #os.system('aplay /home/pi/zaif/chime07.wav > /dev/null 2>&1')
                    else :
                       #os.system('mpg321 /home/pi/zaif/button51.mp3 > /dev/null 2>&1')
                       print_blue(mystr, 1)
                    mystr = " ■ XEM資産:" + str(round(new_jpy/last_price, 4))
                    print_blue(mystr, 1)

                    old_jpy = new_jpy
                    old_my_currency = new_my_currency
                    time.sleep(1.2)

            except Exception as e:
                print(str(e))
                time.sleep(5)

    except KeyboardInterrupt:
        print_green("Bye")


if __name__ == '__main__':
    main()

