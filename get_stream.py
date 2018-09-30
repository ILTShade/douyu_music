'''
本程序是根据输入来自动调整音频文件的输出
'''
import requests
import json
import time
from PIL import Image, ImageDraw, ImageFont
import copy
import re
import cv2
import threading
import subprocess
import sys
import os
import json

lock = threading.Lock()
# 初始选择的列表为空，但是初始默认列表设定为从history读取，不可为空，至少为'{}'，标记为字典
# music_info_dict是一个字典，
# 字典的key是用户点歌的tag
# 下面也是一个字典，包含songname, singername, path, flag
# flag 0 待下载，-1 下载失败，1 下载成功或者已经存在
music_choose_list = []
music_info_dict = {}
with open('history.txt', 'r') as f:
    music_info_dict = json.loads(f.read().rstrip('\n'))

# 这一部分是根据歌名自动从qq音乐上下载对应的歌，只会搜索列表中第一首，
def download_music(word):
    '''
    从qq音乐来下载某个指定的音乐，由于内存关系，只下载搜索到的第一首，
    这个函数完全参考了https://www.cnblogs.com/dearvee/p/6602677.html
    '''
    global music_choose_list
    global music_info_dict
    try:
        # 搜索歌名
        url_search = 'https://c.y.qq.com/soso/fcgi-bin/client_search_cp?&t=0&aggr=1&cr=1&catZhida=1&lossless=0&flag_qc=0&p=1&n=20&w='
        search_result = requests.get(url_search + word).text
        music_info = json.loads(search_result.strip('callback()[]'))['data']['song']['list'][0]
        # 获取该word下搜索得到的歌名和歌手名，如果该文件已经存在，那么直接指向对应文件就好
        songname = music_info['songname']
        singername = music_info['singer']['name']
        path = f'music/{songname}_{singername}.mp3'
        if os.path.exists(path):
            lock.acquire()
            try:
                music_info_dict[word]['songname'] = songname
                music_info_dict[word]['singername'] = singername
                music_info_dict[word]['path'] = path
                music_info_dict[word]['flag'] = 1
            finally:
                lock.release()
            print(f'{path}已存在')
            sys.stdout.flush()
            return
        # 获取链接并下载
        mid = music_info['media_mid']
        songmid = music_info['songmid']
        url_prefix = 'https://c.y.qq.com/base/fcgi-bin/fcg_music_express_mobile3.fcg?&jsonpCallback=MusicJsonCallback&cid=205361747&songmid='
        url_result = requests.get(url_prefix + songmid +'&filename=C400' + mid + '.m4a&guid=6612300644').text
        url_download = 'http://dl.stream.qqmusic.qq.com/C400' + mid + \
                       '.m4a?vkey=' + json.loads(url_result)['data']['items'][0]['vkey'] + \
                       '&guid=6612300644&uin=0&fromtag=66'
        music = requests.get(url_download).content
        # 写入文件
        f = open(path, 'wb')
        f.write(music)
        f.close()
        # 输出结果
        lock.acquire()
        try:
            music_info_dict[word]['songname'] = songname
            music_info_dict[word]['singername'] = singername
            music_info_dict[word]['path'] = path
            music_info_dict[word]['flag'] = 1
        finally:
            lock.release()
        print(f'{path}下载成功')
        sys.stdout.flush()
    except:
        lock.acquire()
        try:
            music_info_dict[word]['flag'] = -1
        finally:
            lock.release()
        print(f'下载{word}的某个流程出现问题')
        sys.stdout.flush()

# 这一部分是处理弹幕输入的部分，应该持续运行，保证可以接收到正确的弹幕并对相关信息进行处理
def barrage_decision():
    patten = re.compile(u'mc:(\S*)')
    while True:
        barrage = input()
        print(barrage)
        sys.stdout.flush()
        space_index = barrage.find(' ')
        assert space_index != -1
        nickname = barrage[:space_index - 1]
        word = barrage[space_index + 1:]
        music_list = patten.findall(word)
        # add to music_choose_list and music_info_dict
        global music_choose_list
        global music_info_dict
        for music in music_list:
            print('barrage_decision')
            lock.acquire()
            try:
                music_choose_list.append(f'{nickname} 点歌 {music}')
                if music in music_info_dict:
                    music_info_dict[music]['num'] += 1
                else:
                    music_info_dict[music] = {'num': 1, 'songname':"", 'singername':"", 'path': "", 'flag':0}
                    threading.Thread(target = download_music, args = (music,)).start()
                print(music_choose_list[-1])
                print(music_info_dict)
            finally:
                lock.release()
            sys.stdout.flush()

# 这一部分是用来生成随机图片的部分，利用ffmpeg的特性，生成不同的背景图片实现视频的效果，每3秒钟进行一次更新
def generate_background():
    image = Image.open('image/background_background.jpg')
    while True:
        global music_choose_list
        global music_info_dict
        print('generate_background')
        lock.acquire()
        try:
            tmp_music_choose_list = copy.deepcopy(music_choose_list)
            tmp_music_info_dict = copy.deepcopy(music_info_dict)
            music_choose_list = []
            print(music_choose_list)
            print(music_info_dict)
        finally:
            lock.release()
        sys.stdout.flush()
        # 图片处理
        global image_show
        image_show = image.copy()
        draw = ImageDraw.Draw(image_show)
        font = ImageFont.truetype('font/handan.ttf', 40)
        gap = 40
        text_x = 0
        text_y = 600
        for i, text in enumerate(tmp_music_choose_list):
            draw.text((text_x, text_y + i * gap), text, font = font, fill = '#ff0000')
        # 加入已点歌曲，只显示点击量大于0，且存在的歌曲
        f = [(v['num'], k) for k, v in tmp_music_info_dict.items()]
        f = sorted(f, reverse = True)
        text_x = 900
        text_y = 400
        list_count = 0
        for _, k in f:
            if tmp_music_info_dict[k]['flag'] == 1 and tmp_music_info_dict['num'] > 0:
                text = tmp_music_info_dict[k]['songname'] + '_' + tmp_music_info_dict[k]['singername'] + ': ' + \
                       str(tmp_music_info_dict[k]['num'])
                draw.text((text_x, text_y + list_count * gap), text, font = font, fill = '#ff0000')
                list_count = list_count + 1
        image_show.save('image/background.jpg')
        print('保存图片成功')
        sys.stdout.flush()
        # 将现在的tmp_music_info_dict保存
        with open('history.txt', 'w') as f:
            f.write(json.dumps(tmp_music_info_dict))
        time.sleep(5)

# 这一部分用来生成选择的音频
def generate_audio():
    while True:
        print('generate_audio')
        lock.acquire()
        try:
            f = [(v['num'], k) for k, v in music_info_dict.items()]
            f = sorted(f, reverse = True)
            for _, k in f:
                if music_info_dict[k]['flag'] == 1 and music_info_dict['num'] > 0:
                    music_info_dict[k]['num'] = 0
                    audio_name = music_info_dict[k]['path']
                    break
            else:
                audio_name = 'music/hush.mp3'
            print(music_choose_list)
            print(music_info_dict)
        finally:
            lock.release()
        print(f'start play {audio_name}')
        cmd = f'mplayer {audio_name}'
        print(cmd)
        sys.stdout.flush()
        res = subprocess.getstatusoutput(cmd)

p_barrage = threading.Thread(target = barrage_decision)
p_background = threading.Thread(target = generate_background)
p_audio = threading.Thread(target = generate_audio)

p_barrage.start()
p_background.start()
p_audio.start()
