#!/usr/bin/python3
# coding: utf-8
# 資産計算専用ボット
# 約24時間（86000秒）で強制解除<なんで？

import datetime,time
from zaifapi import *
import json
from functools import partial
from pprint import pprint
import os
import sys

TARGET_CURRENCY_PAIR = 'xym_jpy'
MY_CURRENCY = 'xym'

zaif_keys_json = open('/home/pi/zaif/xym1_keys.json', 'r')
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
    old_my_currency = 0.0

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

            if(delay_time > 60):
                sys.exit()

            try:
                print('◆◆◆',time_str, '(', delay_time,'秒)','◆◆◆')
                print_yellow(' ■ 終値:' + str(last_price),1)
                with open('/var/tmp/xym_price.txt', 'w') as f:
                    f.write(str(round(last_price,4)))

            except Exception as e:
                print(str(e))
                time.sleep(5)

    except KeyboardInterrupt:
        print_green("Bye")


if __name__ == '__main__':
    main()

