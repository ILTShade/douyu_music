'''
本程序是根据输入来自动调整音频文件的输出
'''
import requests
import json
import time
from PIL import Image, ImageDraw, ImageFont
import copy
import re
import os
import threading

lock = threading.Lock()
music_choose_list = []
music_info_dict = {'雨蝶':{'num':1, 'path':'music/雨蝶.mp3', 'length':20}}

# 这一部分是根据歌名自动从qq音乐上下载对应的歌
def download_music(word):
    '''
    从qq音乐来下载某个指定的音乐，由于内存关系，只下载搜索到的第一首，
    这个函数完全参考了https://www.cnblogs.com/dearvee/p/6602677.html
    '''
    try:
        # 搜索歌名
        url_search = 'https://c.y.qq.com/soso/fcgi-bin/client_search_cp?&t=0&aggr=1&cr=1&catZhida=1&lossless=0&flag_qc=0&p=1&n=20&w='
        search_result = requests.get(url_search + word).text
        music_info = json.loads(search_result.strip('callback()[]'))['data']['song']['list'][0]
        mid = music_info['media_mid']
        songmid = music_info['songmid']
        # 获取链接
        url_prefix = 'https://c.y.qq.com/base/fcgi-bin/fcg_music_express_mobile3.fcg?&jsonpCallback=MusicJsonCallback&cid=205361747&songmid='
        url_result = requests.get(url_prefix + songmid +'&filename=C400' + mid + '.m4a&guid=6612300644').text
        url_download = 'http://dl.stream.qqmusic.qq.com/C400' + mid + \
                       '.m4a?vkey=' + json.loads(url_result)['data']['items'][0]['vkey'] + \
                       '&guid=6612300644&uin=0&fromtag=66'
        music = requests.get(url_download).content
        f = open(f'music/{word}.mp3', 'wb')
        f.write(music)
        f.close()
        print(f'下载{word}成功')
        music_info_dict[word]['path'] = f'music/{word}.mp4'
        music_info_dict[word]['length'] = 20
    except:
        print(f'下载{word}失败')

# 这一部分是处理弹幕输入的部分，应该持续运行，保证可以接收到正确的弹幕并对相关信息进行处理
def barrage_decision():
    patten = re.compile(u'mc:(\S*)')
    while True:
        barrage = input()
        space_index = barrage.find(' ')
        assert space_index != -1
        nickname = barrage[:space_index - 1]
        word = barrage[space_index + 1:]
        music_list = patten.findall(word)
        # add to music_choose_list and music_info_dict
        global music_choose_list
        global music_info_dict
        for music in music_list:
            lock.acquire()
            try:
                music_choose_list.append(f'{nickname} 点歌 {music}')
                if music in music_info_dict:
                    music_info_dict[music]['num'] += 1
                else:
                    music_info_dict[music] = {'num': 1, 'path': "", 'length':0}
                    threading.Thread(target = download_music, args = (music,)).start()
                print('barrage_decision')
                print(music_choose_list[-1])
                print(music_info_dict)
            finally:
                lock.release()

# 这一部分是用来生成随机图片的部分，利用ffmpeg的特性，生成不同的背景图片实现视频的效果，每3秒钟进行一次更新
def generate_background():
    image = Image.open('image/background_background.jpg')
    while True:
        global music_choose_list
        global music_info_dict
        lock.acquire()
        try:
            tmp_music_choose_list = copy.deepcopy(music_choose_list)
            tmp_music_info_dict = copy.deepcopy(music_info_dict)
            music_choose_list = []
            print('generate_background')
            print(music_choose_list)
            print(music_info_dict)
        finally:
            lock.release()
        # 图片处理
        image_show = image.copy()
        draw = ImageDraw.Draw(image_show)
        font = ImageFont.truetype('font/handan.ttf', 40)
        text_x = 0
        text_y = 500
        gap = 30
        for i, text in enumerate(tmp_music_choose_list):
            draw.text((text_x, text_y + i * gap), text, font = font, fill = '#ff0000')
        # 加入已点歌曲
        f = [(v['num'], k) for k, v in tmp_music_info_dict.items()]
        f = sorted(f, reverse = True)
        text_x = 800
        text_y = 500
        gap = 30
        for i, (_, k) in enumerate(f):
            text = k + ': ' + str(tmp_music_info_dict[k]['num'])
            draw.text((text_x, text_y + i * gap), text, font = font, fill = '#ff0000')
        # 图片写入固定的background
        image_show.save('image/background.jpg')
        time.sleep(5)

# 这一部分用来生成选择的音频
def generate_audio():
    while True:
        lock.acquire()
        try:
            f = [(v['num'], k) for k, v in music_info_dict.items()]
            f = sorted(f, reverse = True)
            for _, k in f:
                if music_info_dict[k]['length'] > 0:
                    break
            music_info_dict[k]['num'] = 0
            audio_name = music_info_dict[k]['path']
            audio_length = music_info_dict[k]['length']
            print('generate_audio')
            print(music_choose_list)
            print(music_info_dict)
            print(f'start play {audio_name}')
        finally:
            lock.release()
        # rtmp_url = 'rtmp://send3.douyu.com/live' + \
        #            '3200597rtM2e3368?wsSecret=0f4067b91510dc5ba8fe7724ce575194&wsTime=5baecdd4&wsSeek=off&wm=0&tw=0'
        rtmp_url = 'rtmp://10.2.9.89:1935/mytv/'
        cmd = f"ffmpeg -re -loop 1 -i image/background.jpg -i {audio_name} -r 25 -t 200 -f flv '{rtmp_url}'"
        print(cmd)
        print('dadad')
        time.sleep(20)

p_image = threading.Thread(target = generate_background)
p_audio = threading.Thread(target = generate_audio)
p_barrage = threading.Thread(target = barrage_decision)
p_image.start()
p_audio.start()
p_barrage.start()
