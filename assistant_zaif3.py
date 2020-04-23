#!/usr/bin/python3
# coding: utf-8
# Copyright 2017 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Zaif Modification
# LED Matrixバージョン
# 自動売りモード　自動買いモード
# ボリンジャーバンド連動モード追加
# 起動時にボリンジャーでthresholdを補正（タイマーで追随可能）> Googleのtoo many requestエラー
# 売り買い判断指数をRAMディスクに退避 > xem3.pyで直接コントロール
# Voiceでコントロールするのは取引量のみ auto0:取引量０で取引停止

"""Run a recognizer using the Google Assistant Library.

The Google Assistant Library has direct access to the audio API, so this Python
code doesn't need to record audio. Hot word detection "OK, Google" is supported.

It is available for Raspberry Pi 2/3 only; Pi Zero is not supported.
"""

import logging
import platform
import subprocess
import sys
import os
import time
import threading

from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont

from Adafruit_LED_Backpack import BicolorMatrix8x8

from google.assistant.library.event import EventType

from aiy.assistant import auth_helpers
from aiy.assistant.library import Assistant
from aiy.board import Board, Led
from aiy.voice import tts

# Create display instance on default I2C address (0x70) and bus number.
display = BicolorMatrix8x8.BicolorMatrix8x8()

# Initialize the display. Must be called once before using the display.
display.begin()
display.clear()
font = ImageFont.load_default()
font1 = ImageFont.truetype("/home/pi/fonts/misaki_gothic.ttf", 8, encoding='unic')

with open('/var/tmp/message.txt', 'w') as f:
    f.write("準備中")

def led_ready():
    with open('/var/tmp/message.txt', 'w') as f:
        f.write("準備完了")

def led_listening():
    with open('/var/tmp/message.txt', 'w') as f:
        f.write("質問をどうぞ")

def led_thinking():
    with open('/var/tmp/message.txt', 'w') as f:
        f.write("考え中")

class MyThread(threading.Thread):

    def __init__(self):
        threading.Thread.__init__(self)
        self.counter = 0
        self.is_running = True

    def run(self):

        # Clear the display buffer.
        display.clear()

        # First create an 8x8 RGB image.
        image = Image.new('RGB', (8, 8))

        # Then create a draw instance.
        draw = ImageDraw.Draw(image)

        while self.is_running:
            with open('/var/tmp/last_price.txt', 'r') as f:
                price = f.read()

            with open('/var/tmp/ask-bid.txt', 'r') as f:
                askbid = f.read()

            if askbid == "ask":
                fontcolor = (255, 0, 0)
            elif askbid == "bid":
                fontcolor = (0, 255, 0)
            else:
                fontcolor = (255, 255, 0)

            with open('/var/tmp/MACD.txt', 'r') as f:
                MACD = float(f.read())

            draw.line((0, 7, 7, 7), fill=(0, 0, 0))
            if MACD < -100:
                width = -int(MACD/100)
                draw.line((4, 7, 5-width, 7), fill=(255, 0, 0))
            elif MACD > 100:
                width = int(MACD/100)
                draw.line((3, 7, 2+width, 7), fill=(0, 255, 0))

            try:
                with open('/home/pi/zaif/trade-size.txt', 'r') as f:
                    trade_size = int(f.read())
            except ValueError:
                    print("failed to get trade size.")
                    trade_size = 0

            scroll_on = True
            startpos = 7
            pos = startpos
            while scroll_on:
                maxwidth, maxheight = draw.textsize(price, font=font)

                display.clear()
                draw.rectangle((0, 0, 7, 6), outline=(0, 0, 0), fill=(0, 0, 0))
                x = pos
                for i, c in enumerate(price):
                    if x > 7:
                        break
                    if x < -8:
                        char_width, char_height = draw.textsize(c, font=font)
                        x += char_width
                        continue
                    draw.text((x, -2), c, font=font, fill=fontcolor)
                    char_width, char_height = draw.textsize(c, font=font)
                    x += char_width
                # Draw the image on the display buffer.
                display.set_image(image)

                # Draw the buffer to the display hardware.
                display.write_display()

                pos += -1
                if pos < -maxwidth:
                    scroll_on = False

                time.sleep(0.1)

    def stop(self):
        if self.is_alive():
            self.is_running = False
            self.join()

def led_stop():

    # Clear the display buffer.
    display.clear()

    # Draw the buffer to the display hardware.
    display.write_display()


def power_off_pi():
    tts.say('Good bye!')
    subprocess.call('sudo shutdown now', shell=True)


def reboot_pi():
    tts.say('See you in a bit!')
    subprocess.call('sudo reboot', shell=True)

def say_ip():
    ip_address = subprocess.check_output("hostname -I | cut -d' ' -f1", shell=True)
    tts.say('My IP address is %s' % ip_address.decode('utf-8'))

def auto0_xem():
    with open('/home/pi/zaif/trade-size.txt', 'w') as f:
        f.write('0')
    os.system("/home/pi/aquestalkpi/AquesTalkPi -g 80 '取引を中止します' | aplay")
    #tts.say('OK, I am going to start automatic trading with mild threshold')

def auto_xem():
    with open('/home/pi/zaif/trade-size.txt', 'w') as f:
        f.write('500')
    os.system("/home/pi/aquestalkpi/AquesTalkPi -g 80 '自動取引モードに切り替えます' | aplay")
    #tts.say('OK, I am going to start automatic trading with mild threshold')

def situation_xem():
    with open('/var/tmp/pressure.txt', 'r') as f:
        mystr = f.read()
        if "-" in mystr:
            mystr.replace('-', 'マイナス')
    os.system("/home/pi/aquestalkpi/AquesTalkPi -g 50 '" + mystr + "' | aplay") 

def process_event(assistant, led, event):
    logging.info(event)
    if event.type == EventType.ON_START_FINISHED:
        led.state = Led.BEACON_DARK  # Ready.
        led_ready()
        print('Say "OK, Google" then speak, or press Ctrl+C to quit...')
    elif event.type == EventType.ON_CONVERSATION_TURN_STARTED:
        led.state = Led.ON  # Listening.
        led_listening()
    elif event.type == EventType.ON_RECOGNIZING_SPEECH_FINISHED and event.args:
        print('You said:', event.args['text'])
        text = event.args['text'].lower()
        if 'シャットダウン' in text:
            assistant.stop_conversation()
            power_off_pi()
        elif 'リブート' in text:
            assistant.stop_conversation()
            reboot_pi()
        elif 'アドレス' in text:
            assistant.stop_conversation()
            say_ip()
        elif '再起動' in text:
            assistant.stop_conversation()
            os.system("sudo systemctl restart zaif")
        elif '仮想通貨' in text or '暗号通貨' in text:
            if '買' in text:
                assistant.stop_conversation()
                auto_xem()
            elif '売' in text:
                assistant.stop_conversation()
                auto_xem()
            else:
                assistant.stop_conversation()
                situation_xem()
        elif 'ゼム' in text:
            if '買' in text:
                assistant.stop_conversation()
                auto_xem()
            elif '売' in text:
                assistant.stop_conversation()
                auto_xem()
        elif '自動' in text:
            if '開' in text:
                assistant.stop_conversation()
                auto_xem()
            elif '始' in text:
                assistant.stop_conversation()
                auto_xem()
            elif 'ゼロ' in text:
                assistant.stop_conversation()
                auto0_xem()
            elif '0' in text:
                assistant.stop_conversation()
                auto0_xem()
            elif '止' in text:
                assistant.stop_conversation()
                auto0_xem()
            elif '辞' in text:
                assistant.stop_conversation()
                auto0_xem()
            else:
                assistant.stop_conversation()
                auto_xem()

    elif event.type == EventType.ON_END_OF_UTTERANCE:
        led.state = Led.PULSE_QUICK  # Thinking.
        led_thinking()
    elif (event.type == EventType.ON_CONVERSATION_TURN_FINISHED
          or event.type == EventType.ON_CONVERSATION_TURN_TIMEOUT
          or event.type == EventType.ON_NO_RESPONSE):
        led.state = Led.BEACON_DARK  # Ready.
        led_ready()
    elif event.type == EventType.ON_ASSISTANT_ERROR and event.args and event.args['is_fatal']:
        led_stop()
        sys.exit(1)


def main():
    logging.basicConfig(level=logging.INFO)
    credentials = auth_helpers.get_assistant_credentials()
    displaytext = MyThread()
    displaytext.start()
    #auto_xem()

    #while True:
    #    continue

    with Board() as board, Assistant(credentials) as assistant:
        for event in assistant.start():
            process_event(assistant, board.led, event)

    displaytext.stop()
    led_stop()

if __name__ == '__main__':
    main()
