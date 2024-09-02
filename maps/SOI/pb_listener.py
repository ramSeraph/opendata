
# Copyright © 2013 Richard Borcsik <borcsikrichard@gmail.com>
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import time
import json
import queue
import logging
from threading import Thread

import websocket

__author__ = "Igor Maculan <n3wtron@gmail.com>"

# modified by ramSeraph to use queues instaed of callbacks

log = logging.getLogger("pushbullet.Listener")

WEBSOCKET_URL = "wss://stream.pushbullet.com/websocket/"


class Listener(Thread, websocket.WebSocketApp):
    def __init__(self, account):
        """
        :param account: Pushbullet object
        """
        self._account = account
        self._api_key = self._account.api_key

        self.q = queue.Queue()
        self.error_q = queue.Queue()

        Thread.__init__(self)
        websocket.WebSocketApp.__init__(
            self,
            WEBSOCKET_URL + self._api_key,
            on_open=self._on_open(),
            on_error=self._on_error(),
            on_message=self._on_message(),
            on_close=self._on_close(),
        )

        self.connected = False
        self.last_update = time.time()

        # History
        self.history = None
        self.clean_history()


    def clean_history(self):
        self.history = []

    def _on_open(self):
        def callback(*_):
            self.connected = True
            self.last_update = time.time()

        return callback

    def _on_close(self):
        def callback(*_):
            log.debug("Listener closed")
            self.connected = False

        return callback

    def _on_message(self):
        def callback(*args):
            message = args[1] if len(args) > 1 else args[0]
            log.debug("Message received:" + message)
            try:
                json_message = json.loads(message)
                if json_message["type"] != "nop":
                    self.q.put(json_message)
            except Exception as e:
                logging.exception(e)

        return callback

    def _on_error(self):
        def callback(*args):
            err = args[1] if len(args) > 1 else args[0]
            try:
                self.error_q.put(err)
            except Exception as e:
                logging.exception(e)

        return callback

    def run_forever(self, sockopt=None, sslopt=None, ping_interval=0, ping_timeout=None, *args, **kwargs):
        websocket.WebSocketApp.run_forever(
            self,
            sockopt=sockopt,
            sslopt=sslopt,
            ping_interval=ping_interval,
            ping_timeout=ping_timeout,
        )

    def run(self):
        self.run_forever()


