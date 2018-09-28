'''
本程序大部分参考了简书上的代码，具体可见https://www.jianshu.com/p/346f30f176ff
'''
import socket
import time
import threading
import re
import sys

# 配置socket的ip和端口
client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
host = socket.gethostbyname("openbarrage.douyutv.com")
port = 8601
client.connect((host, port))
# print('连接服务器成功')

def sendmsg(msgstr):
    '''
    客户端向服务器发送请求的函数，集成发送协议头的功能，msgstr必须以\0结尾
    msgHead: 发送数据前的协议头，消息长度的两倍，及消息类型、加密字段和保密字段
    使用while循环发送具体数据，保证将数据都发送出去
    '''
    # 输入数据编码
    msg = msgstr.encode('utf-8')
    # 消息长度，消息类型，加密字段，保留字段
    data_length = len(msg) + 8
    type_code = 689
    secret_code = 0
    keep_code = 0
    msgHead = int.to_bytes(data_length, 4, 'little') + \
              int.to_bytes(data_length, 4, 'little') + \
              int.to_bytes(type_code, 2, 'little') + \
              int.to_bytes(secret_code, 1, 'little') + \
              int.to_bytes(keep_code, 1, 'little')
    client.send(msgHead)
    sent = 0
    while sent < len(msg):
        tn = client.send(msg[sent:])
        sent = sent + tn

def get_barrage(roomid):
    '''
    发送登录验证请求后，获取服务器返回的弹幕信息，同时提取昵称及弹幕内容
    登陆请求消息及入组消息末尾要加入\0
    '''
    # 登陆房间，加入分组
    msgstr = f'type@=loginreq/roomid@={roomid}/\0'
    sendmsg(msgstr)
    msgstr = f'type@=joingroup/rid@={roomid}/gid@=-9999/\0'
    sendmsg(msgstr)
    # 接受弹幕
    barrage = re.compile(b'type@=chatmsg.*?/nn@=(.*?)/txt@=(.*?)/')
    while True:
        data = client.recv(1024)
        if not data:
            break
        barrage_list = barrage.findall(data)
        for barrage_slice in barrage_list:
            nickname = barrage_slice[0].decode(encoding = 'utf-8')
            word = barrage_slice[1].decode(encoding = 'utf-8')
            print(f'{nickname}: {word}')
            sys.stdout.flush()

def keeplive():
    '''
    发送心跳信息，维持TCP长连接
    心跳消息末尾加入\0
    '''
    while True:
        time.sleep(30)
        msgstr = 'type@=keeplive/tick@=' + str(int(time.time())) + '/\0'
        sendmsg(msgstr)

t1 = threading.Thread(target = get_barrage, args = ('288016',))
t2 = threading.Thread(target = keeplive)
t1.start()
t2.start()

