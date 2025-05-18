import os
import re
import queue

import pushbullet

from pb_listener import Listener


def get_otp_manual():
    val = input('Enter OTP: ')
    return val.strip()

pb_client = None

def get_otp_from_msg(data):
    if data['type'] != 'push':
        return None
    push = data['push']
    if push['type'] != 'mirror':
        return None
    title = push.get('title', '')
    body  = push.get('body', '')
    if title.find('NAKSHE') == -1:
        return None
    otps = []
    for m in re.finditer(r"(\d+)\s+is\s+your\s+OTP", body):
        otps.append(m.group(1))
    if len(otps) == 0:
        return None
    return otps[-1]

def get_pb_client():
    global pb_client
    if pb_client is None:
        pb_token = os.environ.get('PB_TOKEN', '')
        if pb_token == '':
            raise Exception('PB_TOKEN environment variable not set or empty')
        pb_client = pushbullet.PushBullet(pb_token)
    return pb_client


def setup_otp_listener():
    pb = get_pb_client()
    listener = Listener(pb)
    listener.start()
    return listener

def get_otp_pb(listener, timeout=60):
    otp = None
    while True:
        try:
            data = listener.q.get(timeout=timeout)
            otp = get_otp_from_msg(data)
            if otp is not None:
                break
        except queue.Empty:
            break
    listener.close()
    return otp


if __name__ == '__main__':
    listener = setup_otp_listener()
    print('done setting up listener')
    otp =  get_otp_pb(listener, timeout=600)
    print(f'got {otp=}')


