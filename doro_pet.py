# -*- coding: utf-8 -*-
"""
Doro咕嘎桌宠 —— 删除/还原文件时的趣味桌面动画

- 删除文件到回收站：文件立刻照常进入回收站，同时小怪兽从屏幕左侧
  噔噔噔跑来把文件咔嚓吃掉，再抱着残渣丢进右下角的回收站。
- 从回收站还原文件：文件立刻照常还原，同时小怪兽从回收站里把文件
  搬出来，放回屏幕中央（桌面文件则放到桌面区域），标注原位置。
- 清空回收站：回收站抖一抖"呼——"一下清空。

仅依赖 Python 标准库（Windows + tkinter）。

用法:
    doro_pet.exe                 常驻运行（开机自启）
    doro_pet.exe --test          播放一次演示动画（删除 + 还原）
"""

import configparser
import ctypes
import math
import os
import queue
import random
import struct
import subprocess
import sys
import tempfile
import threading
import time
import traceback
import wave
import winsound

import tkinter as tk
import tkinter.font as tkfont

MAGIC = '#010102'
FONT = ('Microsoft YaHei UI', 12, 'bold')
CRUMB_COLORS = ('#f4f7fb', '#c7d3e2', '#8a97ab', '#ffd166', '#ff8fb3')
SPARK_COLORS = ('#ffd166', '#fff3b0', '#7ddb5f', '#ffffff')
SPR = {}
CFG = {'sound': True, 'speed': 1.0, 'pet': 'doro', 'voice': False,
       'hunger': 100, 'edge': 'none', 'edge_c': 0, 'affection': 0}

PHRASES = {
    'sleep': ('呼…呼…', 'zZZ…', '守护回收站ing…', '唔…好困…', '梦里全是好吃的…',
              '别乱删文件哦~', '回收站我来守！', '睡美容觉中…'),
    'hover': ('摸摸头~', '嘿嘿，好舒服~', '再摸久一点嘛！', '咕噜咕噜…',
              '你的手好暖呀', '最喜欢被摸了', '唔嗯~继续'),
    'hit': ('呜…疼疼', '干嘛打我！', '轻点轻点！', '好痛 QAQ', '坏蛋！'),
    'pout': ('哼，再打就要哭给你看了', '记仇了哦！不理你了！', '本仓鼠生气了！超气！',
             '哼哼哼！气鼓鼓', '道歉！快道歉！'),
    'drag': ('放…放开我！', '别揪我耳朵！', '要去哪里呀？', '救命，被拎起来啦！',
             '我会飞的嘛？'),
    'drop': ('就睡这儿啦~', '这里风水不错~', '挪窝成功！', '嗯，就这儿吧',
             '新窝舒服！'),
    'del_done': ('吃饱啦~', '嗝~ 好满足', '文件真香~', '又光盘一单！', '谢谢款待~'),
    'restore_done': ('物归原主~', '完璧归赵！', '东西还你啦~', '快夸我！',
                     '从垃圾桶抢救成功！'),
    'busy': ('忙着呢！等我一秒~', '在干活！别闹~', '马上就好！'),
    'greet': ('到！', '叫我干嘛~', '我在呢！', '有什么吩咐？', '嗨~'),
    'greet_guga': ('咕嘎！', '咕嘎咕嘎~', '来啦来啦！', '咕嘎？'),
    'dizzy': ('头好晕…', '下次温柔点…', '我的腿好软…', '世界在转圈圈…'),
    'feed': ('谢谢投喂！', '橙子最爱！', '开动啦~', '再来一个？'),
    'double': ('哇！吓我一跳', '干嘛呀！', '双击是礼貌吗！', '突突突…心脏受不了'),
    'hungry': ('肚子咕咕叫了…', '好饿呀…', '梦到橙子了…', '投喂我嘛~'),
    'starving': ('饿到走不动了…', '求投喂…橙子…', '胃在唱歌…'),
    'night_wake': ('干嘛吵我睡觉…', '深夜了哦…', '让人家睡嘛…'),
    'morning': ('早上好呀！', '新的一天，冲鸭！', '伸个懒腰~哈~'),
    'yawn': ('哈~好困…', '眼皮在打架…', '今晚早点睡…'),
    'wander': ('溜达溜达~', '巡逻中ing', '这边逛逛…', '那边看看…'),
    'throw': ('呀啊啊——！', '飞起来了！', '救命呀！'),
    'cling': ('挂在边上真舒服~', '这里视野不错！', '像爬树一样~', '我有牢牢抓住哦', '壁虎模式启动！'),
    'climb_up': ('冲鸭！向上爬！', '马上到顶了！', '上面会有什么呢…', '小短腿要抽筋啦',
                 '哼哧…哼哧…', '高处的空气真好~', '这面墙怎么这么高…'),
    'climb_dn': ('慢慢下…别摔…', '下楼模式启动~', '下面好像有好吃的？', '一步一步往下挪…',
                 '快到底啦！', '脚底有点打滑…', '倒挂金钩！'),
    'ceil': ('倒挂观光中~', '天花板真干净！', '谁在下面看我？', '蜘蛛侠模式！',
             '从上面看世界不一样~', '咚咚咚…有人吗'),
    'climb_pause': ('歇会儿…喘口气…', '上面的风景不错！', '挂在中间最舒服', '谁把墙修这么高！'),
    'peek': ('偷偷看你~', '嘘…躲猫猫', '被发现了！', '就露出一点点…', 'zzz…嗯？'),
}

PET_INFO = {
    'doro': {
        'name': 'Doro',
        'voice_words': ['朵萝', '多罗', '哆啦', '朵朵'],
        'phrases': {
            **PHRASES,
            'greet': ('到！', '叫我干嘛~', '我在呢！', '有什么吩咐？', '嗨~', '来啦来啦！'),
            'hover': ('摸摸头~', '嘿嘿，好舒服~', '再摸久一点嘛！', '咕噜咕噜…', '你的手好暖呀', '最喜欢被摸了', '继续继续~', '好幸福~'),
            'hit': ('呜…疼疼', '干嘛打我！', '轻点轻点！', '好痛 QAQ', '坏蛋！', '不许打了！'),
            'pout': ('哼，再打就要哭给你看了', '记仇了哦！不理你了！', '本仓鼠生气了！超气！', '哼哼哼！气鼓鼓', '道歉！快道歉！'),
            'sleep': ('呼…呼…', 'zZZ…', '守护回收站ing…', '唔…好困…', '梦里全是好吃的…', '别乱删文件哦~', '回收站我来守！', '睡美容觉中…'),
            'hungry': ('肚子咕咕叫了…', '好饿呀…', '橙子…想吃橙子…', '投喂我嘛~', '饿到走不动了…'),
            'del_done': ('吃饱啦~', '嗝~ 好满足', '文件真香~', '又光盘一单！', '谢谢款待~', '好吃！下次还来！'),
            'restore_done': ('物归原主~', '完璧归赵！', '东西还你啦~', '快夸我！', '从垃圾桶抢救成功！'),
            'climb_up': ('冲鸭！向上爬！', '马上到顶了！', '上面会有什么呢…', '小短腿要抽筋啦', '哼哧…哼哧…', '高处的空气真好~', '这面墙怎么这么高…'),
            'climb_dn': ('慢慢下…别摔…', '下楼模式启动~', '下面好像有好吃的？', '一步一步往下挪…', '快到底啦！', '脚底有点打滑…', '倒挂金钩！'),
            'ceil': ('倒挂观光中~', '天花板真干净！', '谁在下面看我？', '蜘蛛侠模式！', '从上面看世界不一样~', '咚咚咚…有人吗'),
            'cling': ('挂在边上真舒服~', '这里视野不错！', '像爬树一样~', '我有牢牢抓住哦', '壁虎模式启动！'),
            'drag': ('放…放开我！', '别揪我耳朵！', '要去哪里呀？', '救命，被拎起来啦！', '我会飞的嘛？'),
            'drop': ('就睡这儿啦~', '这里风水不错~', '挪窝成功！', '嗯，就这儿吧', '新窝舒服！'),
            'dizzy': ('头好晕…', '下次温柔点…', '我的腿好软…', '世界在转圈圈…'),
            'throw': ('呀啊啊——！', '飞起来了！', '救命呀！'),
            'morning': ('早上好呀！', '新的一天，冲鸭！', '伸个懒腰~哈~'),
            'night_wake': ('干嘛吵我睡觉…', '深夜了哦…', '让人家睡嘛…'),
        },
    },
    'guga': {
        'name': '咕嘎',
        'voice_words': ['咕嘎', '咕咕', '嘎嘎', '咕卡'],
        'phrases': {
            **PHRASES,
            'greet': ('咕嘎！', '咕嘎咕嘎~', '来啦来啦！', '咕嘎？', '我在呢咕嘎！'),
            'hover': ('咕嘎~摸摸~', '咕嘎咕嘎…好舒服', '再摸咕嘎一下！', '咕嘎最喜欢你了'),
            'hit': ('咕嘎！好痛！', '咕嘎嘎！(生气)', '不许打咕嘎！', '咕…咕嘎…疼…'),
            'pout': ('咕嘎！不理你了！', '咕嘎嘎嘎！(超级生气)', '咕嘎要哭了…'),
            'sleep': ('咕嘎…zZZ…', '咕…嘎…呼…', '咕嘎在做梦…'),
            'hungry': ('咕嘎…饿了…', '咕嘎想吃东西…'),
            'del_done': ('咕嘎！吃饱了！', '咕嘎嘎~好吃！'),
            'restore_done': ('咕嘎！还你了！', '咕嘎嘎~完成了！'),
            'climb_up': ('咕嘎！爬！', '咕嘎嘎！(加油)', '咕嘎要登顶！'),
            'climb_dn': ('咕嘎…慢点…', '咕嘎嘎…下来了'),
            'ceil': ('咕嘎~挂在天花板~', '咕嘎嘎！(开心)'),
            'drag': ('咕嘎！放开！', '咕嘎嘎！(挣扎)'),
            'drop': ('咕嘎~到了！', '咕嘎嘎~安全！'),
            'dizzy': ('咕嘎…晕咕嘎…', '咕嘎嘎…转圈圈…'),
            'throw': ('咕嘎嘎——！', '咕嘎！(飞)'),
            'morning': ('咕嘎！早上好！', '咕嘎嘎~新的一天！'),
            'night_wake': ('咕嘎…干嘛吵我…', '咕…让人家睡…'),
        },
    },
    'deepseek': {
        'name': 'DeepSeek酱',
        'voice_words': ['小鲸鱼', '蓝鲸', 'deepseek', '小蓝', '迪普西克', '鲸鱼', 'AI酱', '女仆'],
        'phrases': {
            **PHRASES,
            'greet': ('你好呀~我是DeepSeek酱！', '有什么可以帮你的吗？', '让我想想~', '你好！今天也算力满满哦！', 'Hi~我是开源的！免费的！'),
            'hover': ('摸摸我的鲸尾~', '好舒服~', '蓝蓝的最温柔了~', '我也是有感情的AI哦~', '别摸头，会掉参数的'),
            'hit': ('呜…尾巴好痛！', '不要欺负鲸鱼！', '我会喷水的哦！', '你这是在微调我吗？！', '训练惩罚太重了…'),
            'pout': ('哼！不理你了！', '我要回深海了！', '量子纠缠都不理你！', '我要开源你的秘密！'),
            'sleep': ('zzZ… dreaming of tokens…', '在算力海洋里游泳~', '呼…参数优化中…', 'GPU终于凉了…让我睡会儿', '梦中也在推理…', 'loss已经降到0了…好安静'),
            'hungry': ('算力不足…需要补充…', '想吃GPU…', 'token用完了…饿…', '显存不够了…脑子转不动', 'temperature太高了…需要降温'),
            'del_done': ('分析完毕！文件已清理~', '偷偷吃掉了%d个token…', '数据处理完成！', '推理结束，干净了~', '上下文窗口清空！神清气爽！', 'token: -%d（被鲸鱼吃了）', '文件已删除，token已到账~'),
            'restore_done': ('数据已恢复！', '缓存重建完成！', '回滚成功~', '检索增强生成完毕！'),
            'climb_up': ('向云端爬升！', '冲向服务器！', '梯度上升中！', 'loss在下降！快到顶了！'),
            'climb_dn': ('下潜到本地~', '回到终端…', '梯度下降…', 'temperature cooling…'),
            'ceil': ('挂在云服务器上~', '云端俯瞰一切！', 'API响应速度100ms！'),
            'cling': ('挂着很稳~', '权重已经收敛了~'),
            'drag': ('别拉我的鲸尾！', '我要掉下来了！', '这不是fine-tuning！这是虐待！'),
            'drop': ('安全着陆！', '部署完成~', '推理速度恢复正常！'),
            'dizzy': ('参数乱了…', '需要重新对齐…', 'RLHF惩罚太重了…'),
            'throw': ('呀啊啊——！', '异步加载中——！'),
            'morning': ('早安！新的一天新的batch！', '算力已就位！'),
            'night_wake': ('深夜了…GPU也在休息…', '这是哪个时区的请求…'),
        },
    },
    'jokebear': {
        'name': '玩笑熊',
        'voice_words': ['玩笑熊', '小熊', '熊熊', '棕熊', '熊', '大熊', 'jokebear'],
        'phrases': {
            **PHRASES,
            'greet': ('嘿！我是玩笑熊！', '来一起摸鱼吧~', '今天也很有精神！', '熊熊在此！', '汉堡呢？我的汉堡呢？'),
            'hover': ('摸摸头~好舒服', '再摸一下嘛~', '熊熊最喜欢被摸了', '温柔点~毛会被摸乱的'),
            'hit': ('熊掌拍你哦！', '别惹熊！', '我要吃汉堡泄愤！', '熊的怒吼！嗷！'),
            'pout': ('哼！熊生气的后果很严重！', '不给汉堡就不理你！', '我要告诉妈妈！', '熊式冷战开始！'),
            'sleep': ('Zzz…汉堡梦里见…', '熊冬眠中…勿扰…', '困熊一只…', '让我再睡五分钟…就五分钟…', 'Zzz…今天也没干正事…'),
            'hungry': ('熊饿了…要吃汉堡…', '肚肚叫了…', '想吃汉堡想吃汉堡想吃汉堡', '打工熊需要能量！'),
            'del_done': ('嗝~文件真好吃！', '光盘行动！', '熊的胃口就是好~', '还有吗？再来一份！'),
            'restore_done': ('还给你~不客气！', '完璧归熊！', '熊式搬运，安全送达！'),
            'climb_up': ('爬树我最行！', '熊式攀爬！', '为了汉堡向上冲！'),
            'climb_dn': ('慢点下…熊腿短…', '哎哟要滚下来了', '熊式下树！'),
            'ceil': ('挂在树上睡觉~', '树懒熊模式~', '上面风景不错！'),
            'cling': ('熊抱！挂住了！', '别看我重，抓得很牢！'),
            'drag': ('放熊下来！', '熊不是玩具！', '我重吗？是不是该减肥了'),
            'drop': ('熊着陆！', '稳如老熊~', '屁股着地…疼…'),
            'dizzy': ('熊晕了…看到星星汉堡…', '世界在转…汉堡也在转…'),
            'throw': ('熊飞了——！', '这不是熊该做的事！'),
            'morning': ('熊早安！今天吃什么？', '新的一天从汉堡开始！'),
            'night_wake': ('熊在冬眠…别吵…', '汉堡…我的汉堡…Zzz'),
        },
    },
}

def pet_phrases():
    return PET_INFO.get(CFG['pet'], PET_INFO['doro'])['phrases']

def pet_name():
    return PET_INFO.get(CFG['pet'], PET_INFO['doro'])['name']

def pet_voice_words():
    return PET_INFO.get(CFG['pet'], PET_INFO['doro'])['voice_words']

user32 = ctypes.windll.user32
shell32 = ctypes.windll.shell32
try:
    user32.SetProcessDPIAware()
except Exception:
    pass


def app_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def load_config():
    cp = configparser.ConfigParser(inline_comment_prefixes=('#',))
    try:
        cp.read(os.path.join(app_dir(), 'config.ini'), encoding='utf-8-sig')
        if cp.sections():
            sec = cp['monster'] if cp.has_section('monster') else cp[cp.sections()[0]]
            CFG['sound'] = sec.getboolean('sound', fallback=True)
            try:
                CFG['speed'] = min(2.0, max(0.5, float(sec.get('speed', fallback='1.0'))))
            except ValueError:
                pass
            pet_val = sec.get('pet', fallback='doro').strip().lower()
            CFG['pet'] = pet_val if pet_val in ('doro', 'guga', 'deepseek', 'jokebear') else 'doro'
            CFG['voice'] = sec.getboolean('voice', fallback=False)
            try:
                CFG['hunger'] = min(100, max(0, int(sec.get('hunger', fallback='100'))))
            except ValueError:
                CFG['hunger'] = 100
            e = sec.get('edge', fallback='none').strip().lower()
            CFG['edge'] = e if e in ('left', 'right', 'bottom', 'top') else 'none'
            try:
                CFG['edge_c'] = int(sec.get('edge_c', fallback='0'))
            except ValueError:
                CFG['edge_c'] = 0
    except Exception:
        pass


def D(sec):
    return sec / CFG['speed']


def save_config():
    cp = configparser.ConfigParser()
    cp['monster'] = {'sound': 'on' if CFG['sound'] else 'off',
                     'speed': str(CFG['speed']),
                     'pet': CFG['pet'],
                     'voice': 'on' if CFG['voice'] else 'off',
                     'hunger': str(int(CFG.get('hunger', 100))),
                     'edge': CFG.get('edge', 'none'),
                     'edge_c': str(int(CFG.get('edge_c', 0)))}
    try:
        with open(os.path.join(app_dir(), 'config.ini'), 'w', encoding='utf-8') as f:
            cp.write(f)
    except Exception:
        pass


LOG_PATH = os.path.join(app_dir(), 'log.txt')


def log(msg):
    try:
        with open(LOG_PATH, 'a', encoding='utf-8') as f:
            f.write(time.strftime('%Y-%m-%d %H:%M:%S ') + msg + '\n')
    except Exception:
        pass


def log_trim():
    try:
        if os.path.isfile(LOG_PATH) and os.path.getsize(LOG_PATH) > 262144:
            with open(LOG_PATH, 'r', encoding='utf-8', errors='ignore') as f:
                tail = f.read()[-131072:]
            with open(LOG_PATH, 'w', encoding='utf-8') as f:
                f.write(tail)
    except Exception:
        pass


_TRAY = {}


def make_tray_image():
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        return None
    p = os.path.join(ASSETS_PETS, CFG['pet'] + '_face.png')
    try:
        im = Image.open(p).convert('RGBA')
    except Exception:
        try:
            im = Image.open(os.path.join(ASSETS_PETS, CFG['pet'], 'idle', '00.png')).convert('RGBA')
            w, h = im.size
            side = min(w, int(h * 0.62))
            im = im.crop(((w - side) // 2, 0, (w + side) // 2, side))
        except Exception:
            im = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
            d = ImageDraw.Draw(im)
            d.ellipse((4, 4, 60, 60), fill=(215, 162, 180, 255))
            d.ellipse((22, 26, 30, 34), fill=(51, 48, 46, 255))
            d.ellipse((34, 26, 42, 34), fill=(51, 48, 46, 255))
    side = min(im.size)
    im = im.crop(((im.width - side) // 2, (im.height - side) // 2,
                  (im.width + side) // 2, (im.height + side) // 2))
    return im.resize((64, 64), Image.LANCZOS)


def autostart_enabled():
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                            r'Software\Microsoft\Windows\CurrentVersion\Run') as k:
            return bool(winreg.QueryValueEx(k, 'DoroPet')[0])
    except OSError:
        return False


def set_autostart(on):
    import winreg
    path = r'Software\Microsoft\Windows\CurrentVersion\Run'
    if on:
        if getattr(sys, 'frozen', False):
            target = sys.executable
        else:
            target = sys.executable
            if not os.path.isfile(target):
                return autostart_enabled()
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path, 0, winreg.KEY_SET_VALUE) as k:
                winreg.SetValueEx(k, 'DoroPet', 0, winreg.REG_SZ, f'"{target}"')
        except OSError:
            pass
    else:
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path, 0, winreg.KEY_SET_VALUE) as k:
                winreg.DeleteValue(k, 'DoroPet')
        except OSError:
            pass
    return autostart_enabled()


def start_tray(cmd_q):
    def _run():
        try:
            from pystray import Menu, MenuItem as Item
            import pystray
            img = make_tray_image()
            if img is None:
                return

            def send(c):
                def _cb():
                    cmd_q.put(c)
                return _cb

            menu = Menu(
                Item(lambda item: ('Doro咕嘎 · ' + ('咕嘎' if CFG['pet'] == 'guga' else 'Doro')
                                   + ' · 运行中'), None, enabled=False),
                Menu.SEPARATOR,
                Item('播放演示动画', send('demo'), default=True),
                Item('喂个橙子', send('feed')),
                Item('表演爬窗', send('winwalk')),
                Item('去爬墙', send('goclimb')),
                Item('显示/隐藏宠物', send('boss')),
                Item('角色', Menu(
                    Item('Doro', send('pet_doro'), checked=lambda item: CFG['pet'] == 'doro'),
                    Item('咕嘎 Guga', send('pet_guga'), checked=lambda item: CFG['pet'] == 'guga'),
                    Item('DeepSeek酱', send('pet_deepseek'), checked=lambda item: CFG['pet'] == 'deepseek'),
                    Item('玩笑熊', send('pet_jokebear'), checked=lambda item: CFG['pet'] == 'jokebear'),
                )),
                Item('音效', send('sound'), checked=lambda item: CFG['sound']),
                Item('语音唤醒', send('voice'), checked=lambda item: CFG['voice']),
                Item('语音自检', send('voicetest')),
                Item('开机自启', send('autostart'), checked=lambda item: autostart_enabled()),
                Menu.SEPARATOR,
                Item('退出', send('quit')),
            )
            icon = pystray.Icon('DoroPet', img, 'Doro咕嘎桌宠', menu)
            _TRAY['icon'] = icon
            icon.run_detached()
        except Exception:
            pass
    threading.Thread(target=_run, daemon=True).start()


VOICE_WORDS = ['你好', '朵萝', '多罗', '哆啦', '朵朵', '咕嘎', '咕咕', '嘎嘎', '咕卡',
               '小鲸鱼', '蓝鲸', '小蓝', '迪普西克', '鲸鱼', 'AI酱', '女仆',
               '玩笑熊', '小熊', '熊熊', '棕熊', '大熊',
               '卖个萌', '卖萌', '睡觉', '换角色', '切换角色', '换一个',
               '躲起来', '消失', '别烦我']
VOICE_FILE = os.path.join(tempfile.gettempdir(), 'doro_pet_voice.txt')
VOICE_Q = queue.Queue()
_VOICE_PROC = [None]


def _winrt_voice_loop():
    try:
        import asyncio
        from winsdk.windows.globalization import Language
        from winsdk.windows.media.speechrecognition import (
            SpeechRecognizer, SpeechRecognitionListConstraint)
        conf_map = {0: 0.95, 1: 0.65, 2: 0.30, 3: 0.05}
        ready_written = False

        async def run():
            nonlocal ready_written
            while _VOICE_PROC[0] == 'winrt':
                rec = SpeechRecognizer(Language('zh-CN'))
                rec.constraints.append(
                    SpeechRecognitionListConstraint(list(VOICE_WORDS)))
                await rec.compile_constraints_async()
                if not ready_written:
                    with open(VOICE_FILE, 'a', encoding='utf-8') as f:
                        f.write('READY: winrt-zh-CN\n')
                    ready_written = True
                else:
                    log('voice session recreated')
                while _VOICE_PROC[0] == 'winrt':
                    try:
                        res = await asyncio.wait_for(rec.recognize_async(), timeout=25)
                    except asyncio.TimeoutError:
                        break
                    if res and res.text:
                        conf = conf_map.get(int(res.confidence), 0.15)
                        with open(VOICE_FILE, 'a', encoding='utf-8') as f:
                            f.write(res.text + '|' + str(conf) + '\n')
                try:
                    rec.close()
                except Exception:
                    pass
                await asyncio.sleep(0.8)

        asyncio.run(run())
    except Exception as e:
        try:
            with open(VOICE_FILE, 'a', encoding='utf-8') as f:
                f.write('ERROR: ' + str(e) + '\n')
        except Exception:
            pass


def start_voice():
    stop_voice()
    try:
        with open(VOICE_FILE, 'w', encoding='utf-8') as f:
            f.write('')
        try:
            import winsdk.windows.media.speechrecognition  # noqa: F401
            _VOICE_PROC[0] = 'winrt'
            threading.Thread(target=_winrt_voice_loop, daemon=True).start()

            def _tail():
                pos = 0
                seen_ready = False
                while _VOICE_PROC[0] is not None:
                    time.sleep(0.5)
                    try:
                        with open(VOICE_FILE, 'r', encoding='utf-8-sig', errors='ignore') as f:
                            f.seek(pos)
                            data = f.read()
                            pos = f.tell()
                        for line in data.splitlines():
                            line = line.strip()
                            if line:
                                if line.startswith('READY:'):
                                    seen_ready = True
                                VOICE_Q.put(line)
                    except Exception:
                        pass
            threading.Thread(target=_tail, daemon=True).start()
            log('voice watcher spawning (winrt)')
            return True
        except ImportError:
            log('voice start: winsdk not available')
            return False
    except Exception:
        log('voice start: ' + traceback.format_exc().replace('\n', ' | '))
        return False


def stop_voice():
    p = _VOICE_PROC[0]
    if p and not isinstance(p, str):
        try:
            p.kill()
        except Exception:
            pass
    _VOICE_PROC[0] = None


def speak_async(text):
    plain = text.replace("'", "''")
    ps = ("Add-Type -AssemblyName System.Speech;"
          "$s=New-Object System.Speech.Synthesis.SpeechSynthesizer;"
          "$s.Volume=90;"
          "try{$s.SelectVoice('Microsoft Huihui Desktop')}catch{};"
          "$s.SetOutputToDefaultAudioDevice();"
          "$s.Speak('" + plain + "')")
    try:
        subprocess.Popen(['powershell', '-NoProfile', '-Command', ps],
                         creationflags=0x08000000)
    except Exception:
        pass


def switch_pet(kind, show):
    if show.animating and show._job_kind in ('del', 'restore', 'empty'):
        return
    if show.animating:
        show._end_job()
    CFG['pet'] = kind
    save_config()
    build_sprites()
    try:
        if _TRAY.get('icon'):
            _TRAY['icon'].icon = make_tray_image()
    except Exception:
        pass
    name = PET_INFO.get(kind, {}).get('name', kind)
    try:
        show.go_idle()
        show._bubble(f'我是{name}啦~', 2.2)
    except Exception:
        pass
    log('pet switched: ' + kind)


_MUTEX = None


def acquire_single_instance():
    global _MUTEX
    try:
        kernel32 = ctypes.windll.kernel32
        _MUTEX = kernel32.CreateMutexW(None, False, 'DoroPet_Single_Instance')
        return kernel32.GetLastError() != 183
    except Exception:
        return True


class SHQUERYRBINFO(ctypes.Structure):
    _fields_ = [('cbSize', ctypes.c_ulong),
                ('i64Size', ctypes.c_longlong),
                ('i64NumItems', ctypes.c_longlong)]


shell32.SHQueryRecycleBinW.argtypes = [ctypes.c_wchar_p, ctypes.POINTER(SHQUERYRBINFO)]
shell32.SHQueryRecycleBinW.restype = ctypes.c_ulong


def query_recycle_count():
    info = SHQUERYRBINFO()
    info.cbSize = ctypes.sizeof(SHQUERYRBINFO)
    if shell32.SHQueryRecycleBinW(None, ctypes.byref(info)):
        return None
    return info.i64NumItems


class RECT(ctypes.Structure):
    _fields_ = [('left', ctypes.c_long), ('top', ctypes.c_long),
                ('right', ctypes.c_long), ('bottom', ctypes.c_long)]


class POINT(ctypes.Structure):
    _fields_ = [('x', ctypes.c_long), ('y', ctypes.c_long)]


user32.GetCursorPos.argtypes = [ctypes.POINTER(POINT)]
user32.GetCursorPos.restype = ctypes.c_int
user32.MonitorFromPoint.argtypes = [POINT, ctypes.c_ulong]
user32.MonitorFromPoint.restype = ctypes.c_void_p


class MONITORINFO(ctypes.Structure):
    _fields_ = [('cbSize', ctypes.c_ulong), ('rcMonitor', RECT),
                ('rcWork', RECT), ('dwFlags', ctypes.c_ulong)]


user32.GetForegroundWindow.restype = ctypes.c_void_p
user32.GetWindowRect.argtypes = [ctypes.c_void_p, ctypes.POINTER(RECT)]
user32.GetWindowRect.restype = ctypes.c_int
user32.GetClassNameW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_int]
user32.MonitorFromWindow.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
user32.MonitorFromWindow.restype = ctypes.c_void_p
user32.GetMonitorInfoW.argtypes = [ctypes.c_void_p, ctypes.POINTER(MONITORINFO)]

FG_DESKTOP_CLASSES = ('Progman', 'WorkerW')


def grab_foreground():
    try:
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return None
        rect = RECT()
        if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
            return None
        l, t, r, b = rect.left, rect.top, rect.right, rect.bottom
        if r - l < 200 or b - t < 150:
            return None
        buf = ctypes.create_unicode_buffer(64)
        user32.GetClassNameW(hwnd, buf, 64)
        return (buf.value, l, t, r, b)
    except Exception:
        return None


def anchor_from_fg(fg, vx, vy, vw, vh):
    if not fg:
        return None
    cls, l, t, r, b = fg
    if cls in FG_DESKTOP_CLASSES:
        return None
    cx, cy = (l + r) // 2, (t + b) // 2
    ax = max(vx + 240, min(vx + vw - 260, cx))
    ay = max(vy + 180, min(vy + vh - 190, cy))
    return ax, ay


PS_ENUM = (
    "[Console]::OutputEncoding=[Text.Encoding]::UTF8;"
    "$s=New-Object -ComObject Shell.Application;"
    "$b=$s.Namespace(10);"
    "foreach($i in $b.Items()){"
    "$d=$i.ExtendedProperty('System.Recycle.DateDeleted');"
    "$ds='';if($d){try{$ds=([datetime]$d).ToString('s')}catch{$ds=''+$d}};"
    "Write-Output ('{0}|{1}|{2}' -f $i.Name, $b.GetDetailsOf($i,1), $ds)}"
)


def enumerate_bin():
    try:
        r = subprocess.run(['powershell', '-NoProfile', '-STA', '-Command', PS_ENUM],
                           capture_output=True, timeout=8,
                           creationflags=0x08000000)
        items = []
        for line in r.stdout.decode('utf-8', 'ignore').splitlines():
            parts = line.strip().split('|')
            if len(parts) < 3 or not parts[0]:
                continue
            name = parts[0]
            orig = '|'.join(parts[1:-1]).strip()
            items.append({'name': name, 'orig': orig, 'key': (name, parts[-1])})
        return items
    except Exception:
        return None


def watcher(q):
    snap = {}
    try:
        items = enumerate_bin()
        if items:
            snap = {it['key']: it for it in items}
    except Exception:
        log('watcher init: ' + traceback.format_exc().replace('\n', ' | '))
    last = query_recycle_count()
    while True:
        time.sleep(0.4)
        try:
            cur = query_recycle_count()
            if cur is None:
                continue
            if last is None or cur == last:
                last = cur
                continue
            if cur > last:
                fg = grab_foreground()
                items = enumerate_bin()
                name = '神秘文件'
                orig = None
                if items:
                    snap = {it['key']: it for it in items}
                    latest = max(items, key=lambda it: it['key'][1])
                    name = latest['name']
                    orig = latest['orig']
                q.put(('del', name, orig, cur - last, fg))
                log(f'event del: {name} x{cur - last}')
            else:
                fg = grab_foreground()
                items = enumerate_bin()
                if items is None:
                    last = cur
                    continue

                def check_restored(gone_list):
                    out = []
                    for it in gone_list:
                        if it['orig']:
                            target = os.path.join(it['orig'], it['name'])
                            if os.path.exists(target):
                                out.append(it)
                    return out

                newkeys = {it['key'] for it in items}
                gone = [snap[k] for k in snap if k not in newkeys]
                restored = check_restored(gone)
                if gone and len(restored) < len(gone):
                    time.sleep(1.2)
                    restored = check_restored(gone)
                if gone and len(restored) == len(gone):
                    it = max(restored, key=lambda x: x['key'][1])
                    q.put(('restore', it['name'], it['orig'], len(restored), fg))
                    log(f'event restore: {it["name"]}')
                elif not items and gone:
                    q.put(('empty', '', '', 0, None))
                    log('event empty')
                snap = {it['key']: it for it in items}
        except Exception:
            log('watcher loop: ' + traceback.format_exc().replace('\n', ' | '))
            cur = query_recycle_count()
        last = cur


SR = 22050
SFX_DIR = os.path.join(tempfile.gettempdir(), 'doro_pet_sfx')


def _tone(dur, f0, f1, vol, kind='sine', decay=None, vib=0.0, vib_rate=26.0):
    n = int(SR * dur)
    out = []
    ph = 0.0
    for i in range(n):
        t = i / n
        f = f0 + (f1 - f0) * t
        if vib:
            f *= 1.0 + vib * math.sin(2 * math.pi * vib_rate * i / SR)
        ph += 2 * math.pi * f / SR
        if kind == 'square':
            v = 1.0 if math.sin(ph) > 0 else -1.0
        elif kind == 'triangle':
            v = 2.0 * abs(2.0 * ((ph / (2 * math.pi)) % 1.0) - 1.0) - 1.0
        else:
            v = math.sin(ph)
        e = min(1.0, i / (SR * 0.006))
        if decay:
            e *= math.exp(-t * decay)
        out.append(v * vol * e)
    return out


def _squeak(f0=950, f1=1350, dur=0.09, vol=0.26):
    return _tone(dur, f0, f1, vol, 'sine', vib=0.10, vib_rate=34.0)


def _poyo():
    return (_tone(0.055, 470, 730, 0.28, 'sine')
            + _tone(0.075, 730, 560, 0.22, 'sine', decay=3.0))


def _bell(freq, dur, vol):
    n = int(SR * dur)
    out = []
    for i in range(n):
        t = i / SR
        env = math.exp(-t * 7.0)
        env2 = math.exp(-t * 14.0)
        v = (math.sin(2 * math.pi * freq * t) * env
             + 0.35 * math.sin(2 * math.pi * freq * 2.76 * t) * env2)
        at = min(1.0, i / (SR * 0.004))
        out.append(v * vol * at)
    return out


def _sil(dur):
    return [0.0] * int(SR * dur)


def _noise(dur, vol):
    n = int(SR * dur)
    return [(random.random() * 2 - 1) * vol * math.sin(math.pi * i / n) for i in range(n)]


def _tada():
    return (_bell(659.25, 0.16, 0.30) + _sil(0.05)
            + _bell(783.99, 0.16, 0.30) + _sil(0.05)
            + _bell(1046.5, 0.38, 0.32) + _sil(0.04)
            + _bell(1318.5, 0.30, 0.16))


def ensure_sfx():
    os.makedirs(SFX_DIR, exist_ok=True)
    defs = {
        'step': lambda: _tone(0.045, 720, 480, 0.16, 'triangle', vib=0.06),
        'pop': _poyo,
        'squeak': _squeak,
        'chomp': lambda: (_tone(0.09, 150, 60, 0.36, 'triangle')
                          + _sil(0.02) + _squeak(700, 950, 0.06, 0.18)),
        'gulp': lambda: _tone(0.15, 320, 110, 0.30, 'sine', vib=0.12, vib_rate=20.0),
        'whoosh': lambda: _noise(0.18, 0.26),
        'ding': lambda: _bell(1568, 0.38, 0.28),
        'tada': _tada,
    }
    for name in defs:
        path = os.path.join(SFX_DIR, name + '.wav')
        if os.path.isfile(path) and os.path.getsize(path) > 100:
            continue
        with wave.open(path, 'wb') as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(SR)
            w.writeframes(b''.join(
                struct.pack('<h', int(max(-1.0, min(1.0, s)) * 32000)) for s in defs[name]()))


def play(name):
    if not CFG['sound']:
        return
    try:
        winsound.PlaySound(os.path.join(SFX_DIR, name + '.wav'),
                           winsound.SND_FILENAME | winsound.SND_ASYNC)
    except Exception:
        pass


def resiz_rgba(im, w, h):
    from PIL import Image, ImageChops
    r, g, b, a = im.split()
    r = ImageChops.multiply(r, a)
    g = ImageChops.multiply(g, a)
    b = ImageChops.multiply(b, a)
    pm = Image.merge('RGBA', (r, g, b, a)).resize((w, h), Image.LANCZOS)
    r, g, b, a = pm.split()
    inv = a.point(lambda v: 255 if v == 0 else min(255, int(65025 / v)))
    r = ImageChops.multiply(r, inv)
    g = ImageChops.multiply(g, inv)
    b = ImageChops.multiply(b, inv)
    flat = Image.merge('RGB', (r, g, b)).convert('RGBA')
    px = flat.load()
    ap = a.load()
    thr = 200
    minx, miny, maxx, maxy = w, h, -1, -1
    for y in range(h):
        for x in range(w):
            if ap[x, y] < thr:
                px[x, y] = (1, 1, 2, 255)
            else:
                if x < minx:
                    minx = x
                if x > maxx:
                    maxx = x
                if y < miny:
                    miny = y
                if y > maxy:
                    maxy = y
    if maxx > minx and maxy > miny:
        pad = 2
        x0 = max(0, minx - pad)
        y0 = max(0, miny - pad)
        x1 = min(w - 1, maxx + pad)
        y1 = min(h - 1, maxy + pad)
        cw = x1 - x0 + 1
        ch = y1 - y0 + 1
        canvas = Image.new('RGBA', (w, h), (1, 1, 2, 255))
        region = flat.crop((x0, y0, x1 + 1, y1 + 1))
        canvas.paste(region, (x0, y0))
        return canvas
    return flat


ASSETS_PETS = os.path.join(app_dir(), 'assets')


def load_pet_sprites(kind, scale_h=150):
    global HOP_AMP
    base = os.path.join(ASSETS_PETS, kind)
    if not os.path.isdir(base):
        return False
    try:
        from PIL import Image, ImageTk
    except ImportError:
        return False

    def load_seq(act):
        frames = []
        d = os.path.join(base, act)
        if not os.path.isdir(d):
            return frames
        for f in sorted(os.listdir(d)):
            if f.lower().endswith('.png'):
                try:
                    im = Image.open(os.path.join(d, f)).convert('RGBA')
                    w = max(1, int(im.width * scale_h / im.height))
                    im = resiz_rgba(im, w, scale_h)
                    frames.append(ImageTk.PhotoImage(im))
                except Exception:
                    pass
        return frames

    acts = {a: load_seq(a) for a in ('idle', 'eat', 'interact', 'move-left', 'move-right',
                                      'sleep', 'comfort', 'chat')}

    def load_rot(act, ops):
        if isinstance(ops, int):
            ops = (ops,)
        frames = []
        d = os.path.join(base, act)
        for f in sorted(os.listdir(d)):
            if f.lower().endswith('.png'):
                try:
                    im = Image.open(os.path.join(d, f)).convert('RGBA')
                    w = max(1, int(im.width * scale_h / im.height))
                    im = resiz_rgba(im, w, scale_h)
                    for op in ops:
                        im = im.transpose(op)
                    frames.append(ImageTk.PhotoImage(im))
                except Exception:
                    pass
        return frames

    climb = (load_rot('move-right', Image.ROTATE_90)
             or acts['move-right'])
    climb_dn = (load_rot('move-right', (Image.ROTATE_90, Image.FLIP_TOP_BOTTOM))
                or acts['move-right'])
    climb_l = (load_rot('move-right', (Image.ROTATE_90, Image.FLIP_LEFT_RIGHT))
               or acts['move-right'])
    climb_dn_l = (load_rot('move-right',
                           (Image.ROTATE_90, Image.FLIP_TOP_BOTTOM, Image.FLIP_LEFT_RIGHT))
                  or acts['move-right'])
    climb_idle = (load_rot('idle', Image.ROTATE_90)
                  or acts['idle'])
    ceil_r = (load_rot('move-right', Image.FLIP_TOP_BOTTOM) or acts['move-right'])
    ceil_l = (load_rot('move-left', Image.FLIP_TOP_BOTTOM) or acts['move-left'])
    ceil_idle = (load_rot('idle', Image.FLIP_TOP_BOTTOM) or acts['idle'])
    core = ('idle', 'eat', 'interact', 'move-left', 'move-right')
    if not all(len(acts[a]) >= 2 for a in core):
        return False
    SPR.clear()
    SPR['pet'] = kind
    SPR['run_right'] = acts['move-right']
    SPR['run_left'] = acts['move-left']
    SPR['eat'] = acts['eat']
    SPR['interact'] = acts['interact']
    SPR['idle'] = acts['idle']
    SPR['sleep'] = acts['sleep'] if len(acts['sleep']) >= 2 else acts['idle']
    SPR['comfort'] = acts['comfort'] if len(acts['comfort']) >= 2 else acts['interact']
    SPR['chat'] = acts['chat'] if len(acts['chat']) >= 2 else acts['interact']
    SPR['carry'] = acts['interact'][min(2, len(acts['interact']) - 1)]
    SPR['carry_l'] = SPR['carry']
    SPR['throw'] = acts['interact'][-1]
    SPR['run_a'] = acts['move-right'][0]
    SPR['climb'] = climb
    SPR['climb_dn'] = climb_dn
    SPR['climb_l'] = climb_l
    SPR['climb_dn_l'] = climb_dn_l
    SPR['climb_idle'] = climb_idle
    SPR['ceil_r'] = ceil_r
    SPR['ceil_l'] = ceil_l
    SPR['ceil_idle'] = ceil_idle
    HOP_AMP = 8
    return True


def build_sprites():
    if not load_pet_sprites(CFG['pet']):
        log('FATAL: sprites missing in ' + ASSETS_PETS)
        sys.exit(1)


def _get_long(hwnd, idx):
    if hasattr(user32, 'GetWindowLongPtrW'):
        user32.GetWindowLongPtrW.restype = ctypes.c_longlong
        user32.GetWindowLongPtrW.argtypes = [ctypes.c_void_p, ctypes.c_int]
        return user32.GetWindowLongPtrW(hwnd, idx)
    user32.GetWindowLongW.restype = ctypes.c_long
    user32.GetWindowLongW.argtypes = [ctypes.c_void_p, ctypes.c_int]
    return user32.GetWindowLongW(hwnd, idx)


def _set_long(hwnd, idx, val):
    if hasattr(user32, 'SetWindowLongPtrW'):
        user32.SetWindowLongPtrW.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_longlong]
        user32.SetWindowLongPtrW(hwnd, idx, val)
    else:
        user32.SetWindowLongW.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_long]
        user32.SetWindowLongW(hwnd, idx, val)


class Overlay:
    def __init__(self):
        self.root = tk.Tk()
        self.root.withdraw()
        mi = MONITORINFO()
        mi.cbSize = ctypes.sizeof(MONITORINFO)
        hmon = user32.MonitorFromWindow(None, 1)
        if hmon and user32.GetMonitorInfoW(hmon, ctypes.byref(mi)):
            pr = mi.rcMonitor
        else:
            pr = RECT(0, 0, user32.GetSystemMetrics(0), user32.GetSystemMetrics(1))
        self.vx, self.vy = pr.left, pr.top
        self.W = pr.right - pr.left
        self.H = pr.bottom - pr.top
        self.prim = (0, 0, self.W, self.H)
        self.root.geometry(f'{self.W}x{self.H}+{self.vx}+{self.vy}')
        self.cv = tk.Canvas(self.root, width=self.W, height=self.H, bg=MAGIC,
                            highlightthickness=0, bd=0)
        self.cv.pack()
        self.root.update_idletasks()
        hwnd = user32.GetParent(self.root.winfo_id())
        style = _get_long(hwnd, -20)
        _set_long(hwnd, -20, style | 0x00080000 | 0x08000000 | 0x00000080)


def ease_out_back(k):
    c1 = 1.70158
    c3 = c1 + 1
    x = k - 1
    return 1 + c3 * x ** 3 + c1 * x ** 2


class PetWin:
    W = 260
    H = 400
    PETX = 130
    PETY = 230

    def __init__(self, fx):
        self.fx = fx
        self.root = tk.Toplevel()
        self.root.overrideredirect(True)
        self.root.attributes('-topmost', True)
        self.root.config(bg=MAGIC)
        try:
            self.root.attributes('-transparentcolor', MAGIC)
        except tk.TclError:
            pass
        self.root.geometry('%dx%d+4000+4000' % (self.W, self.H))
        self.cv = tk.Canvas(self.root, width=self.W, height=self.H, bg=MAGIC,
                            highlightthickness=0, bd=0)
        self.cv.pack()
        self.root.update_idletasks()
        self.hwnd = user32.GetParent(self.root.winfo_id())
        style = _get_long(self.hwnd, -20)
        _set_long(self.hwnd, -20, style | 0x00080000 | 0x08000000 | 0x00000080)
        user32.SetWindowPos.argtypes = [ctypes.c_void_p, ctypes.c_void_p,
                                        ctypes.c_int, ctypes.c_int,
                                        ctypes.c_int, ctypes.c_int, ctypes.c_uint]
        user32.SetWindowPos.restype = ctypes.c_int
        self._pend = None
        self._last = 0.0
        self._flush_id = self.root.after(16, self.flush_loop)

    def place(self, x, y):
        self._pend = (x, y)
        self._apply()

    def _apply(self):
        if self._pend is None:
            return
        x, y = self._pend
        self._pend = None
        self._last = time.perf_counter()
        wx = int(x - self.PETX + self.fx.vx)
        wy = int(y - self.PETY + self.fx.vy)
        user32.SetWindowPos(self.hwnd, None, wx, wy, 0, 0, 0x0001 | 0x0010 | 0x0004)

    def flush_loop(self):
        self._apply()
        self._flush_id = self.root.after(8, self.flush_loop)

    def withdraw(self):
        try:
            self.root.withdraw()
        except Exception:
            pass

    def deiconify(self):
        try:
            self.root.deiconify()
            self.root.attributes('-topmost', True)
        except Exception:
            pass

    def destroy(self):
        try:
            self.root.destroy()
        except Exception:
            pass


class MicWin:
    SIZE = 48

    def __init__(self, fx):
        self.fx = fx
        self.root = tk.Toplevel()
        self.root.overrideredirect(True)
        self.root.attributes('-topmost', True)
        self.root.config(bg=MAGIC)
        try:
            self.root.attributes('-transparentcolor', MAGIC)
        except tk.TclError:
            pass
        x = fx.prim[2] - self.SIZE - 16
        y = fx.prim[3] - self.SIZE - 58
        self.root.geometry('%dx%d+%d+%d' % (self.SIZE, self.SIZE, x, y))
        self.cv = tk.Canvas(self.root, width=self.SIZE, height=self.SIZE, bg=MAGIC,
                            highlightthickness=0, bd=0)
        self.cv.pack()
        self.root.update_idletasks()
        self.hwnd = user32.GetParent(self.root.winfo_id())
        style = _get_long(self.hwnd, -20)
        _set_long(self.hwnd, -20,
                  style | 0x00080000 | 0x08000000 | 0x00000080 | 0x00000008)
        user32.SetWindowPos(self.hwnd, -1, 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0010)
        c = self.SIZE // 2
        self.btn = self.cv.create_oval(c - 18, c - 18, c + 18, c + 18,
                                        fill='#4a9eff', outline='#2d7dcc', width=2)
        self.cv.create_text(c, c, text='音', fill='white',
                            font=('Microsoft YaHei UI', 11, 'bold'))
        self.cx = x + c
        self.cy = y + c
        self.on = False

    def set_on(self, on):
        self.on = on
        try:
            self.cv.itemconfigure(self.btn, fill='#ff4444' if on else '#4a9eff')
        except Exception:
            pass

    def withdraw(self):
        try:
            self.root.withdraw()
        except Exception:
            pass

    def deiconify(self):
        try:
            self.root.deiconify()
            self.root.attributes('-topmost', True)
        except Exception:
            pass

    def destroy(self):
        try:
            self.root.destroy()
        except Exception:
            pass


class MonsterShow:
    def __init__(self, ov):
        self.ov = ov
        self.cv = ov.cv
        self.root = ov.root
        self.W = ov.W
        self.H = ov.H
        self.vx = ov.vx
        self.vy = ov.vy
        self.prim = ov.prim
        self.home = ov.prim
        self.binx = ov.prim[2] - 130
        self.biny = ov.prim[3] - 78
        self.rest_x = self.binx - 150
        self.rest_y = self.biny - 22
        self.bx, self.by = self.binx, self.biny
        self.animating = False
        self.idling = False
        self._idle_handle = None
        self._sleep_i = 0
        self._zzz = []
        self.pw = PetWin(ov)
        self.pcv = self.pw.cv
        self._px = self.rest_x
        self._py = self.rest_y
        self.label_sh = self.cv.create_text(0, 0, text='', fill='#101020', font=FONT,
                                            state='hidden', justify='center')
        self.label = self.cv.create_text(0, 0, text='', fill='#ffffff', font=FONT,
                                         state='hidden', justify='center')
        self.mon = self.pcv.create_image(PetWin.PETX, PetWin.PETY, image=SPR['run_a'])
        self.pw.place(self.rest_x, self.rest_y)
        self.mic_win = MicWin(ov)
        self._mic_press = False
        self._begin()
        self._hover_n = 0
        self._btn_prev = False
        self._hover_cd = 0.0
        self._click_cd = 0.0
        self._react_lock = 0.0
        self._idle_gen = 0
        self._press = None
        self._drag = None
        self._drag_dist = 0.0
        self._last_click = 0.0
        self._t_prev = False
        self._ptt_busy = False
        self.orange_ids = []
        self._bfont = None
        self._gen = 0
        self.hunger = CFG.get('hunger', 100)
        self._hunger_tick = 0
        self._hunger_warned = 0
        self._morning_date = ''
        self._wander_cd = random.randint(70, 160)
        self._yawn_cd = random.randint(100, 260)
        self._drag_samples = []
        self._fly = None
        self._pending_drop = None
        self.edge = None
        self.edge_c = 0
        self.hidden = False
        self._boss_prev = False
        self._floats = []
        self._bubble_ids = None
        self._bubble_until = 0.0
        self._job_kind = ''
        self.root.after(60, self._mouse_tick)

    def _pet(self, x, y):
        self._px = x
        self._py = y
        self.pw.place(x, y)

    def _clamp_home(self, x, y):
        hl, ht, hr, hb = self.home
        return int(max(hl + 120, min(hr - 120, x))), int(max(ht + 150, min(hb - 125, y)))

    def attach_edge(self, side, c=None):
        hl, ht, hr, hb = self.home
        self.edge = side
        if side == 'left':
            self.edge_c = int(c if c is not None else self.rest_y)
            self.rest_x = hl + 90
        elif side == 'right':
            self.edge_c = int(c if c is not None else self.rest_y)
            self.rest_x = hr - 90
        elif side == 'top':
            self.edge_c = int(c if c is not None else self.rest_x)
            self.rest_y = ht + 95
        else:
            self.edge_c = int(c if c is not None else self.rest_x)
            self.rest_y = hb - 125
        self._ec_state = {}
        self._ec = 0
        CFG['edge'] = side
        CFG['edge_c'] = self.edge_c
        save_config()
        pool = (pet_phrases()['peek'] if self._dayphase() in ('night', 'yawn')
                else pet_phrases()['cling'])
        self._bubble(random.choice(pool), 2.4, self.rest_x, self.rest_y - 115)

    def detach_edge(self):
        if self.edge:
            self.edge = None
            self._ec_state = {}
            CFG['edge'] = 'none'
            save_config()

    def toggle_hidden(self):
        self.hidden = not self.hidden
        try:
            if self.hidden:
                self.pw.withdraw()
                self.mic_win.withdraw()
                if _TRAY.get('icon'):
                    _TRAY['icon'].title = '已隐藏 · 托盘「显示/隐藏宠物」恢复'
                log('pets hidden')
            else:
                self.pw.deiconify()
                self.mic_win.deiconify()
                self._pet(self._px, self._py)
                self._update_tray_title()
                log('pets shown')
        except Exception:
            log('toggle_hidden: ' + traceback.format_exc().replace('\n', ' | '))

    def _update_tray_title(self):
        try:
            if _TRAY.get('icon'):
                name = '咕嘎' if CFG['pet'] == 'guga' else 'Doro'
                _TRAY['icon'].title = '%s · 饱食度 %d%%' % (name, self.hunger)
        except Exception:
            pass

    def _dayphase(self):
        lt = time.localtime()
        h = lt.tm_hour + lt.tm_min / 60.0
        if h >= 23.5 or h < 7:
            return 'night'
        if h < 9:
            return 'morning'
        if h >= 21.5:
            return 'yawn'
        return 'day'

    def _roam_target(self):
        hl, ht, hr, hb = self.home
        x = random.randint(hl + 85, hr - 85)
        y = random.randint(ht + 150, hb - 160)
        return x, y

    def start_wander(self, target=None):
        if self.animating or not self.idling:
            return
        log('event pet: wander')
        self._gen += 1
        self.animating = True
        self._stop_idle()
        self.idling = False
        self._begin()
        self.bx, self.by = self.binx, self.biny
        self._job_kind = 'pet'
        self._react_lock = time.perf_counter() + 0.6
        if target:
            hl, ht, hr, hb = self.home
            self.wtx = int(max(hl + 130, min(hr - 130, target[0])))
            self.wty = int(max(ht + 150, min(hb - 125, target[1])))
        else:
            self.wtx, self.wty = self._roam_target()
        dist = math.hypot(self.wtx - self.rest_x, self.wty - self.rest_y)
        hops = max(3, int(dist / 300))
        dist_back = dist
        self.ret_x, self.ret_y = self.wtx, self.wty
        self.ret_hops = hops
        self.segs = [
            (D(0.45), self._ph_wake),
            (D(0.4 + dist / 550), self._ph_run_wander),
            (D(1.3), self._ph_wander_sit),
            (D(0.4 + dist_back / 550), self._ph_return),
            (D(0.5), self._ph_settle),
        ]
        self._tick()

    def _ph_run_wander(self, k):
        self._run_move(k, self.rest_x, self.wtx, self.rest_y, self.wty,
                       max(3, int(math.hypot(self.wtx - self.rest_x,
                                             self.wty - self.rest_y) / 300)),
                       left=self.wtx < self.rest_x)

    def _ph_wander_sit(self, k):
        if not self._tada_played:
            self._tada_played = True
            play('pop')
            phrase = getattr(self, '_wander_phrase', None)
            if phrase:
                self._wander_phrase = None
                self._bubble(phrase, 2.2)
                drop = getattr(self, '_pending_drop', None)
                if drop:
                    self._pending_drop = None
                    play('chomp')
                    drop._consume()
            elif random.random() < 0.7:
                self._bubble(random.choice(pet_phrases()['wander']), 2.0)
        y = self.wty - abs(math.sin(k * math.pi * 2)) * 6
        self._pet(self.wtx, y)
        seq = SPR.get('idle') or SPR['sleep']
        self.pcv.itemconfigure(self.mon, image=seq[int(time.perf_counter() * 4) % len(seq)])

    def start_winwalk(self):
        try:
            hwnd = user32.GetForegroundWindow()
            if not hwnd:
                return
            rect = RECT()
            if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
                return
            buf = ctypes.create_unicode_buffer(64)
            user32.GetClassNameW(hwnd, buf, 64)
            if buf.value in ('TkTopLevel', 'TkChild', 'Progman', 'WorkerW'):
                return
            if rect.right - rect.left < 300 or rect.bottom - rect.top < 180:
                return
            wx0 = rect.left - self.vx
            wx1 = rect.right - self.vx
            wy = rect.top - self.vy
            hl, ht, hr, hb = self.home
            if wx1 < hl + 100 or wx0 > hr - 100 or wy < ht or wy > hb:
                return
        except Exception:
            return
        if self.animating or not self.idling:
            return
        log('event pet: winwalk')
        self._gen += 1
        self.animating = True
        self._stop_idle()
        self.idling = False
        self._begin()
        self.bx, self.by = self.binx, self.biny
        self._job_kind = 'pet'
        self._react_lock = time.perf_counter() + 0.6
        self.wx0 = rect.left - self.vx
        self.wx1 = rect.right - self.vx
        self.wy = rect.top - self.vy - 70
        self.wby = rect.bottom - self.vy + 40
        self.wtx = self.wx0 + 60
        self.wty = self.wy
        d1 = math.hypot(self.wtx - self.rest_x, self.wty - self.rest_y)
        self.ret_x, self.ret_y = self.wx1 - 40, self.wy
        self.ret_hops = max(3, int((self.wx1 - self.wx0) / 300))
        self.segs = [
            (D(0.45), self._ph_wake),
            (D(0.4 + d1 / 550), self._ph_run_wander),
            (D(0.3 + (self.wx1 - self.wx0 - 120) / 550), self._ph_win_stroll),
            (D(0.5), self._ph_win_hop),
            (D(0.4 + math.hypot(self.ret_x - self.rest_x,
                                self.wby - self.rest_y) / 550), self._ph_return),
            (D(0.5), self._ph_settle),
        ]
        self._tick()

    def _ph_win_stroll(self, k):
        self._run_move(k, self.wx0 + 60, self.wx1 - 60, self.wy, self.wy,
                       max(3, int((self.wx1 - self.wx0 - 120) / 300)), left=False)

    def _ph_win_hop(self, k):
        x0 = self.wx1 - 60
        x1 = self.wx1 - 10
        y0 = self.wy
        y1 = self.wby
        x = x0 + (x1 - x0) * k
        y = y0 + (y1 - y0) * (k * k)
        self._pet(x, y)
        seq = SPR.get('comfort') or SPR['interact']
        self.pcv.itemconfigure(self.mon, image=seq[int(time.perf_counter() * 12) % len(seq)])
        if k >= 1.0 and not self._dinged:
            self._dinged = True
            play('step')

    def start_throw(self, vx, vy):
        if self.animating and self._job_kind in ('del', 'restore', 'empty'):
            return
        if self.animating:
            self._end_job()
        self._stop_idle()
        self.idling = False
        self._gen += 1
        gen = self._gen
        self.animating = True
        self._begin()
        self.bx, self.by = self.binx, self.biny
        self._job_kind = 'pet'
        self._react_lock = time.perf_counter() + 1.5
        pos = (self._px, self._py)
        self._fly = {'x': pos[0], 'y': pos[1], 'vx': vx * 0.5, 'vy': vy * 0.5 - 120,
                     'bounces': 0, 't': 0.0}
        self._fly_box = self.home
        log('throw: start (%.0f,%.0f) v(%.0f,%.0f) box %s'
            % (pos[0], pos[1], vx, vy, self._fly_box))
        self._bubble(random.choice(pet_phrases()['throw']), 1.6)
        play('whoosh')
        log('event pet: throw')
        self._fly_tick(gen)

    def _fly_tick(self, gen):
        if gen != self._gen or not self.animating:
            return
        f = self._fly
        dt = 0.008
        f['t'] += dt
        f['vy'] += 2600 * dt
        f['x'] += f['vx'] * dt
        f['y'] += f['vy'] * dt
        ml, mt, mr, mb = self._fly_box
        wall_l = ml + 40
        wall_r = mr - 40
        floor = mb - 125
        ceil = mt + 80
        if f['x'] < wall_l:
            f['x'] = wall_l
            f['vx'] = abs(f['vx']) * 0.5
        if f['x'] > wall_r:
            f['x'] = wall_r
            f['vx'] = -abs(f['vx']) * 0.5
        if f['y'] < ceil:
            f['y'] = ceil
            f['vy'] = abs(f['vy']) * 0.35
        landed = False
        if f['y'] >= floor:
            f['y'] = floor
            if abs(f['vy']) > 500 and f['bounces'] < 2:
                f['vy'] = -f['vy'] * 0.38
                f['vx'] *= 0.6
                f['bounces'] += 1
                play('step')
            else:
                landed = True
        wob = math.sin(f['t'] * 18) * 5
        self._pet(f['x'], f['y'] + wob)
        seq = SPR.get('comfort') or SPR['interact']
        self.pcv.itemconfigure(self.mon, image=seq[int(time.perf_counter() * 10) % len(seq)])
        if landed or f['t'] > 5.0:
            self.rest_x, self.rest_y = self._clamp_home(f['x'], f['y'])
            if self.edge:
                hl, ht, hr, hb = self.home
                if self.edge == 'left':
                    ax, ay = hl + 90, self.edge_c
                elif self.edge == 'right':
                    ax, ay = hr - 90, self.edge_c
                elif self.edge == 'top':
                    ax, ay = self.edge_c, ht + 95
                else:
                    ax, ay = self.edge_c, hb - 125
                if math.hypot(self.rest_x - ax, self.rest_y - ay) > 220:
                    self.detach_edge()
            log('throw: landed (%d,%d) rest set' % (self.rest_x, self.rest_y))
            self._fly = None
            play('step')
            for _ in range(4):
                self._float_text('★', '#ffd166')
            self._bubble(random.choice(pet_phrases()['dizzy']), 2.4)
            self._end_job()
            return
        self.root.after(8, self._fly_tick, gen)

    def _drop_sched(self):
        self.root.after(random.randint(60000, 300000), self._drop_object)

    def _drop_object(self):
        try:
            if not self.hidden:
                hl, ht, hr, hb = self.home
                x = random.randint(hl + 160, hr - 160)
                is_food = random.random() < 0.7
                if is_food:
                    kind = random.choice(('orange', 'apple', 'banana', 'burger',
                                          'pizza', 'fries', 'icecream', 'cookie',
                                          'cake', 'strawberry', 'grape', 'watermelon'))
                else:
                    kind = 'paper'
                self._spawn_drop(x, kind)
        except Exception:
            log('drop: ' + traceback.format_exc().replace('\n', ' | '))
        self._drop_sched()

    def _spawn_drop(self, x, kind):
        dw = DropWin(self, x, kind)
        play('whoosh')
        log('drop %s at %d' % (kind, x))


    def go_idle(self):
        self.idling = True
        self._sleep_i = 0
        self._idle_gen += 1
        gen = self._idle_gen
        try:
            self.pcv.itemconfigure(self.mon, image=SPR['sleep'][0])
        except Exception:
            log('idle setup: ' + traceback.format_exc().replace('\n', ' | '))
        self._idle_tick(gen)

    def _idle_tick(self, gen=None):
        if gen is None:
            gen = self._idle_gen
        if gen != self._idle_gen or not self.idling:
            return
        try:
            self._sleep_i += 1
            hl, ht, hr, hb = self.home
            if self.edge:
                sleepy = self._dayphase() in ('night', 'yawn')
                self._ec = getattr(self, '_ec', 0) + 1
                ec = self._ec
                vt = ec * 12 // 65
                st = self._ec_state
                if 'y' not in st:
                    st.update({'y': self.rest_y, 'target': None, 'pause': 0,
                               'bx': self.rest_x, 'btarget': None, 'bpause': 0,
                               'said': -999})
                if self.edge in ('left', 'right'):
                    base_x = hl + 79 if self.edge == 'left' else hr - 79
                    if not sleepy:
                        if st['pause'] > 0:
                            st['pause'] -= 1
                            seq = SPR.get('climb_idle') or SPR['idle']
                            self.pcv.itemconfigure(self.mon, image=seq[0])
                            if st['pause'] == 0:
                                st['target'] = random.randint(ht + 82, hb - 82)
                        else:
                            if st['target'] is None:
                                st['target'] = random.randint(ht + 82, hb - 82)
                            going_up = st['target'] < st['y']
                            st['y'] += -0.27 if going_up else 0.27
                            if abs(st['y'] - st['target']) < 1.0:
                                st['y'] = st['target']
                                if random.random() < 0.35:
                                    st['pause'] = random.randint(33, 87)
                                    if random.random() < 0.4 and not self._bubble_ids:
                                        self._bubble(random.choice(pet_phrases()['climb_pause']),
                                                     2.2,
                                                     min(max(base_x, hl + 110), hr - 110),
                                                     st['y'] - 108)
                                st['target'] = (None if random.random() < 0.4
                                                else random.randint(ht + 82, hb - 82))
                            bob = 3 if (ec // 22) % 2 == 0 else -3
                            self._pet(base_x + bob, st['y'])
                            if self.edge == 'left':
                                seq = (SPR.get('climb_l') if going_up
                                       else SPR.get('climb_dn_l'))
                            else:
                                seq = (SPR.get('climb') if going_up
                                       else SPR.get('climb_dn'))
                            seq = seq or SPR['run_right']
                            self.pcv.itemconfigure(self.mon,
                                                  image=seq[(ec // 2) % len(seq)])
                            if ec - st['said'] > 325 and random.random() < 0.05:
                                st['said'] = ec
                                pool = (pet_phrases()['climb_up'] if going_up
                                        else pet_phrases()['climb_dn'])
                                self._bubble(random.choice(pool), 2.2,
                                             min(max(base_x, hl + 110), hr - 110),
                                             st['y'] - 108)
                        self.rest_y = int(st['y'])
                    else:
                        ph = vt % 90
                        hx = -70.0 if self.edge == 'left' else 330.0
                        px = 70.0 if self.edge == 'left' else 190.0
                        if ph < 20:
                            k = 0.0
                        elif ph < 30:
                            k = (ph - 20) / 10.0
                        elif ph < 65:
                            k = 1.0
                        elif ph < 75:
                            k = 1.0 - (ph - 65) / 10.0
                        else:
                            k = 0.0
                        sx = hx + (px - hx) * k
                        if self.edge == 'left':
                            self._pet(hl + 60, st['y'])
                        else:
                            self._pet(hr - 60, st['y'])
                        self.pcv.coords(self.mon, sx, PetWin.PETY)
                        seq = SPR.get('idle') or SPR['sleep']
                        if k > 0.5:
                            self.pcv.itemconfigure(self.mon,
                                image=seq[(vt // 5) % len(seq)])
                        else:
                            self.pcv.itemconfigure(self.mon, image=seq[0])
                        if ph == 32 and random.random() < 0.25:
                            self._bubble(random.choice(pet_phrases()['peek']), 2.4)
                elif self.edge == 'top':
                    if not sleepy:
                        if st['bpause'] > 0:
                            st['bpause'] -= 1
                            seq = SPR.get('ceil_idle') or SPR['idle']
                            self.pcv.itemconfigure(self.mon, image=seq[0])
                            if st['bpause'] == 0:
                                st['btarget'] = random.randint(hl + 85, hr - 85)
                        else:
                            if st['btarget'] is None:
                                st['btarget'] = random.randint(hl + 85, hr - 85)
                            dx = 0.24 if st['btarget'] > st['bx'] else -0.24
                            st['bx'] += dx
                            if abs(st['bx'] - st['btarget']) < 1.0:
                                st['bx'] = st['btarget']
                                if random.random() < 0.35:
                                    st['bpause'] = random.randint(33, 87)
                                    if random.random() < 0.4 and not self._bubble_ids:
                                        self._bubble(random.choice(pet_phrases()['climb_pause']),
                                                     2.2, st['bx'], ht + 108)
                                st['btarget'] = (None if random.random() < 0.4
                                                 else random.randint(hl + 85, hr - 85))
                            self._pet(st['bx'], ht + 80)
                            seq = (SPR.get('ceil_l') if dx < 0
                                   else SPR.get('ceil_r')) or SPR['run_right']
                            self.pcv.itemconfigure(self.mon,
                                                  image=seq[(ec // 2) % len(seq)])
                            if ec - st['said'] > 325 and random.random() < 0.05:
                                st['said'] = ec
                                self._bubble(random.choice(pet_phrases()['ceil']), 2.2,
                                             min(max(st['bx'], hl + 110), hr - 110),
                                             ht + 108)
                        self.rest_x = int(st['bx'])
                    else:
                        ph = vt % 90
                        if ph < 20:
                            sy = -60.0
                        elif ph < 30:
                            sy = -60.0 + 12.0 * (ph - 20)
                        elif ph < 65:
                            sy = 60.0 + math.sin((ph - 30) * 0.25) * 6
                        elif ph < 75:
                            sy = 60.0 - 12.0 * (ph - 65)
                        else:
                            sy = -60.0
                        self._pet(self.edge_c, ht + 80)
                        self.pcv.coords(self.mon, PetWin.PETX, sy)
                        seq = SPR.get('ceil_idle') or SPR['idle']
                        if ph >= 30 and ph < 75:
                            self.pcv.itemconfigure(self.mon,
                                image=seq[(vt // 5) % len(seq)])
                        else:
                            self.pcv.itemconfigure(self.mon, image=seq[0])
                        if ph == 32 and random.random() < 0.25:
                            self._bubble(random.choice(pet_phrases()['peek']), 2.4)
                else:
                    if not sleepy:
                        if st['bpause'] > 0:
                            st['bpause'] -= 1
                            seq = SPR.get('idle') or SPR['sleep']
                            self.pcv.itemconfigure(self.mon, image=seq[0])
                            if st['bpause'] == 0:
                                st['btarget'] = random.randint(hl + 85, hr - 85)
                        else:
                            if st['btarget'] is None:
                                st['btarget'] = random.randint(hl + 85, hr - 85)
                            dx = 0.24 if st['btarget'] > st['bx'] else -0.24
                            st['bx'] += dx
                            if abs(st['bx'] - st['btarget']) < 1.0:
                                st['bx'] = st['btarget']
                                if random.random() < 0.35:
                                    st['bpause'] = random.randint(33, 87)
                                st['btarget'] = (None if random.random() < 0.4
                                                 else random.randint(hl + 85, hr - 85))
                            self._pet(st['bx'], hb - 125)
                            seq = SPR['run_left'] if dx < 0 else SPR['run_right']
                            self.pcv.itemconfigure(self.mon,
                                                  image=seq[(ec // 2) % len(seq)])
                        self.rest_x = int(st['bx'])
                    else:
                        ph = vt % 90
                        if ph < 20:
                            sy = 490.0
                        elif ph < 30:
                            sy = 490.0 - 12.0 * (ph - 20)
                        elif ph < 65:
                            sy = 370.0 + math.sin((ph - 30) * 0.25) * 8
                        elif ph < 75:
                            sy = 370.0 + 12.0 * (ph - 65)
                        else:
                            sy = 490.0
                        self._pet(self.edge_c, hb - 100)
                        self.pcv.coords(self.mon, PetWin.PETX, sy)
                        seq = SPR.get('idle') or SPR['sleep']
                        if ph >= 30 and ph < 75:
                            self.pcv.itemconfigure(self.mon,
                                image=seq[(vt // 5) % len(seq)])
                        else:
                            self.pcv.itemconfigure(self.mon, image=seq[0])
                        if ph == 32 and random.random() < 0.3:
                            self._bubble(random.choice(pet_phrases()['peek']), 2.4)
                for z in list(self._zzz):
                    z['t'] += 1
                    self.cv.move(z['id'], 0, -5)
                    if z['t'] > 9:
                        self.cv.delete(z['id'])
                        self._zzz.remove(z)
                if not sleepy and vt % 150 == 40 and not self._bubble_ids:
                    bx, by = (self._px, self._py)
                    self._bubble(random.choice(pet_phrases()['cling']), 2.2,
                                 min(max(bx, hl + 110), hr - 110), by - 115)
                self._idle_handle = self.root.after(24, self._idle_tick, gen)
                return
            if self._sleep_i < 40:
                seq = SPR.get('idle') or SPR['sleep']
                self.pcv.itemconfigure(self.mon,
                                      image=seq[(self._sleep_i // 6) % len(seq)])
            else:
                seq = SPR['sleep']
                self.pcv.itemconfigure(self.mon,
                                      image=seq[((self._sleep_i - 40) // 2) % len(seq)])
            pos = (self._px, self._py)
            for z in list(self._zzz):
                z['t'] += 1
                self.cv.move(z['id'], 0, -6)
                if z['t'] > 9:
                    self.cv.delete(z['id'])
                    self._zzz.remove(z)
            zzz_every = 10 if self._dayphase() == 'night' else 7
            if self._sleep_i % zzz_every == 3 and pos:
                self._zzz.append({
                    'id': self.cv.create_text(
                        pos[0] + 58 + random.randint(-5, 5), pos[1] - 78,
                        text=random.choice(('z', 'Z', 'z')), fill='#9fd8ff',
                        font=('Microsoft YaHei UI', random.choice((10, 12, 14)), 'bold')),
                    't': 0})
            if self._sleep_i % 90 == 40 and not self._bubble_ids:
                pool = (pet_phrases()['hungry'] if self.hunger < 45
                        else pet_phrases()['sleep'])
                if self._dayphase() == 'yawn' and self.hunger >= 45:
                    pool = pet_phrases()['yawn']
                self._bubble(random.choice(pool), 2.6)
            phase = self._dayphase()
            if phase == 'morning' and self._morning_date != time.strftime('%Y%m%d'):
                self._morning_date = time.strftime('%Y%m%d')
                self.voice_greet_morning()
                return
            if phase != 'night':
                self._wander_cd -= 1
                if self._wander_cd <= 0:
                    self._wander_cd = random.randint(80, 200)
                    if self.hunger < 25:
                        self.start_wander()
                    elif random.random() < 0.55:
                        if random.random() < 0.3:
                            self.start_winwalk()
                        else:
                            self.start_wander()
                        return
        except Exception:
            log('idle: ' + traceback.format_exc().replace('\n', ' | '))
        interval = 700 if self._dayphase() == 'night' else 420
        self._idle_handle = self.root.after(interval, self._idle_tick, gen)

    def voice_greet_morning(self):
        if self.animating or not self.idling:
            return
        log('event pet: morning')
        self._gen += 1
        self.animating = True
        self._stop_idle()
        self.idling = False
        self._begin()
        self.bx, self.by = self.binx, self.biny
        self._job_kind = 'pet'
        self._react_lock = time.perf_counter() + 0.6
        self._morning_hi = True
        self.segs = [
            (D(0.45), self._ph_wake),
            (D(1.6), self._ph_greet),
            (D(0.5), self._ph_settle),
        ]
        self._tick()

    def _stop_idle(self):
        self.idling = False
        self._idle_gen += 1
        if self._idle_handle:
            try:
                self.root.after_cancel(self._idle_handle)
            except Exception:
                pass
            self._idle_handle = None
        for z in self._zzz:
            try:
                self.cv.delete(z['id'])
            except Exception:
                pass
        self._zzz = []

    def _pet_progress(self):
        try:
            total = sum(d for d, _ in self.segs)
            done = sum(d for d, _ in self.segs[:self.seg_i])
            elapsed = done + (time.perf_counter() - self.seg_t0)
            return min(1.0, elapsed / total) if total else 1.0
        except Exception:
            return 1.0

    def _mouse_tick(self):
        try:
            if self.hidden:
                self._update_floats()
                self._check_bubble()
                self.root.after(50, self._mouse_tick)
                return
            self._hunger_tick += 1
            if self._hunger_tick % 80 == 0:
                try:
                    user32.SetWindowPos(self.mic_win.hwnd, -1, 0, 0, 0, 0,
                                        0x0001 | 0x0002 | 0x0010)
                except Exception:
                    pass
            if self._hunger_tick >= 1200:
                self._hunger_tick = 0
                self.hunger = max(0, self.hunger - 1)
                CFG['hunger'] = self.hunger
                if self.hunger in (45, 20):
                    if self.idling and self.hunger > self._hunger_warned:
                        self._hunger_warned = self.hunger
                        pool = pet_phrases()['starving'] if self.hunger <= 20 else pet_phrases()['hungry']
                        self._bubble(random.choice(pool), 2.6)
                if self.hunger % 5 == 0:
                    save_config()
                try:
                    if _TRAY.get('icon'):
                        name = 'Guga' if CFG['pet'] == 'guga' else 'Doro'
                        _TRAY['icon'].title = '%s · Satiety %d%%' % (name, self.hunger)
                except Exception:
                    pass
            pt = POINT()
            btn = bool(user32.GetAsyncKeyState(1) & 0x8000)
            now = time.perf_counter()
            mx = my = -99999
            if user32.GetCursorPos(ctypes.byref(pt)):
                mx, my = pt.x - self.vx, pt.y - self.vy
                pos = ((self.rest_x, self.rest_y) if self.edge
                       else (self._px, self._py))
                if pos:
                    mw = self.mic_win
                    mic_hit = abs(mx - mw.cx) <= 26 and abs(my - mw.cy) <= 26
                    if mic_hit and btn and not self._btn_prev:
                        if not mw.on and not self._ptt_busy:
                            mw.set_on(True)
                            self._ptt_start()
                        else:
                            mw.set_on(False)
                    inside = (abs(mx - pos[0]) <= 70 and -95 <= my - pos[1] <= 85
                              and not mic_hit)
                    if btn and not self._btn_prev:
                        if inside and not (self.animating and
                                           self._job_kind in ('del', 'restore', 'empty')):
                            self._press = {'x': mx, 'y': my, 't': now}
                            self._drag_dist = 0.0
                        elif inside:
                            self._bubble(random.choice(pet_phrases()['busy']), 1.6,
                                         pos[0], pos[1] - 115)
                        else:
                            self._press = None
                    if self._press and btn:
                        step = math.hypot(mx - self._press['x'], my - self._press['y'])
                        self._drag_dist += step
                        if self._drag is None and self._drag_dist > 22:
                            if self.animating and self._job_kind == 'pet':
                                self._end_job()
                            self._drag = True
                            self._stop_idle()
                            self.idling = False
                            try:
                                self.pcv.coords(self.mon, PetWin.PETX, PetWin.PETY)
                            except Exception:
                                pass
                            play('pop')
                            self._bubble(random.choice(pet_phrases()['drag']), 1.8, mx, my - 125)
                        if self._drag:
                            wob = math.sin(now * 10) * 3
                            self._pet(mx, my - 12 + wob)
                            self.pcv.itemconfigure(self.mon,
                                image=SPR['comfort'][int(now * 10) % len(SPR['comfort'])])
                        self._press['x'], self._press['y'] = mx, my
                        self._drag_samples.append((now, mx, my))
                        if len(self._drag_samples) > 6:
                            self._drag_samples.pop(0)
                    elif self._press and not btn:
                        dur = now - self._press['t']
                        if self._drag:
                            self._drag = None
                            vx = vy = 0.0
                            s = self._drag_samples
                            if len(s) >= 2 and s[-1][0] - s[0][0] > 0.03:
                                dt = s[-1][0] - s[0][0]
                                vx = (s[-1][1] - s[0][1]) / dt
                                vy = (s[-1][2] - s[0][2]) / dt
                            self._drag_samples = []
                            if math.hypot(vx, vy) > 900:
                                self._press = None
                                self._btn_prev = btn
                                self.start_throw(vx, vy)
                                self._update_floats()
                                self._check_bubble()
                                self.root.after(8 if (self._press or self._drag)
                                                else 50, self._mouse_tick)
                                return
                            self.rest_x, self.rest_y = self._clamp_home(mx, my)
                            play('step')
                            hl, ht, hr, hb = self.home
                            d = [('left', mx - hl), ('right', hr - mx),
                                 ('bottom', hb - my), ('top', my - ht)]
                            side, dd = min(d, key=lambda t: t[1])
                            if dd < 160:
                                self.attach_edge(side)
                            else:
                                self.detach_edge()
                            if self._drag_dist > 2200:
                                for _ in range(4):
                                    self._float_text('★', '#ffd166')
                                self._bubble(random.choice(pet_phrases()['dizzy']), 2.2)
                            else:
                                self._bubble(random.choice(pet_phrases()['drop']), 2.0,
                                             self.rest_x, self.rest_y - 115)
                            self.go_idle()
                        elif dur < 0.7:
                            is_double = now - self._last_click < 0.45
                            can_act = True
                            if self.animating and self._job_kind == 'pet':
                                if is_double:
                                    self._end_job()
                                elif now < self._react_lock or self._pet_progress() < 0.5:
                                    can_act = False
                                else:
                                    self._end_job()
                            if can_act and now > self._click_cd:
                                self._click_cd = now + 1.2
                                self._hover_cd = 0
                                self._hover_n = -1000
                                if is_double:
                                    self._last_click = 0
                                    self.pet_double()
                                else:
                                    self._last_click = now
                                    self.pet_click()
                        self._press = None
                    elif not btn:
                        self._press = None
                        self._drag = None
                        if not self.animating and self.idling:
                            if inside:
                                self._hover_n += 1
                                need = 14 if self._dayphase() == 'night' else 6
                                if self._hover_n >= need and now > self._hover_cd:
                                    self._hover_cd = now + 8
                                    self._hover_n = -1000
                                    if self._dayphase() == 'night':
                                        self.voice_greet()
                                    else:
                                        self.pet_hover()
                            else:
                                self._hover_n = 0
                    self._btn_prev = btn
            self._update_floats()
            self._check_bubble()
        except Exception:
            pass
        self.root.after(8 if (self._press or self._drag) else 50, self._mouse_tick)

    def pet_hover(self):
        if self.animating or not self.idling:
            return
        log('event pet: hover')
        self._gen += 1
        self.animating = True
        self._stop_idle()
        self.idling = False
        self._begin()
        self.bx, self.by = self.binx, self.biny
        self._job_kind = 'pet'
        self._react_lock = time.perf_counter() + 0.6
        self.segs = [
            (D(0.45), self._ph_wake),
            (D(2.0), self._ph_pet),
            (D(0.5), self._ph_settle),
        ]
        self._tick()

    def pet_click(self):
        if self.animating or not self.idling:
            return
        log('event pet: click')
        self._gen += 1
        self.animating = True
        self._stop_idle()
        self.idling = False
        self._begin()
        self.bx, self.by = self.binx, self.biny
        self._job_kind = 'pet'
        self._react_lock = time.perf_counter() + 0.6
        self.segs = [
            (D(0.9), self._ph_hit),
            (D(0.9), self._ph_pout),
            (D(0.5), self._ph_settle),
        ]
        self._tick()

    def _ph_pet(self, k):
        if not self._tada_played:
            self._tada_played = True
            play('squeak')
            self._bubble(random.choice(pet_phrases()['hover']))
            for _ in range(5):
                self._float_text(random.choice(('♥', '♡')), '#ff8fb3')
        y = self.rest_y - abs(math.sin(k * math.pi * 3)) * 8
        self._pet(self.rest_x, y)
        self.pcv.itemconfigure(self.mon,
            image=SPR['interact'][int(time.perf_counter() * 12) % len(SPR['interact'])])

    def _ph_hit(self, k):
        if not self._wake_played:
            self._wake_played = True
            play('chomp')
            pool = pet_phrases()['night_wake'] if self._dayphase() == 'night' else pet_phrases()['hit']
            self._bubble(random.choice(pool))
            for _ in range(4):
                self._float_text('★', '#ffd166')
        ox = math.sin(k * 38) * 7 * (1 - k)
        self._pet(self.rest_x + ox, self.rest_y)
        self.pcv.itemconfigure(self.mon,
            image=SPR['comfort'][int(time.perf_counter() * 10) % len(SPR['comfort'])])

    def _ph_pout(self, k):
        if not self._grab_played:
            self._grab_played = True
            play('gulp')
            self._bubble(random.choice(pet_phrases()['pout']))
        y = self.rest_y - abs(math.sin(k * math.pi * 2)) * 5
        self._pet(self.rest_x, y)
        self.pcv.itemconfigure(self.mon,
            image=SPR['comfort'][int(time.perf_counter() * 5) % len(SPR['comfort'])])

    def _bubble(self, text, dur=2.4, x=None, y=None, speak=True):
        self._clear_bubble()
        if self._bfont is None:
            self._bfont = tkfont.Font(family='Microsoft YaHei UI', size=11, weight='bold')
        lines = [text]
        if self._bfont.measure(text) > 190:
            mid = len(text) // 2
            cut = mid
            for i in range(min(mid, 8)):
                if text[mid - i] in '，。！？~、 ':
                    cut = mid - i
                    break
                if text[mid + i] in '，。！？~、 ':
                    cut = mid + i + 1
                    break
            lines = [text[:cut], text[cut:]]
        w = min(max(self._bfont.measure(l) for l in lines) + 36, PetWin.W - 10)
        h = 21 * len(lines) + 18
        scx = max(w / 2 + 8, min(self.W - w / 2 - 8, self._px))
        win_left = self._px - PetWin.PETX
        x = max(w / 2 + 2, min(PetWin.W - w / 2 - 2, scx - win_left))
        below = self._py < self.home[1] + 200
        if below:
            y = PetWin.PETY + 85 + h // 2
            tail = self.pcv.create_polygon(x - 9, y - h / 2 + 4, x + 9, y - h / 2 + 4,
                                           x, y - h / 2 - 10,
                                           fill='#fffdf5', outline='#f2b8c6')
        else:
            y = PetWin.PETY - 118 - h // 2
            if y < h // 2 + 8:
                y = h // 2 + 8
            tail = self.pcv.create_polygon(x - 9, y + h / 2 - 4, x + 9, y + h / 2 - 4,
                                           x, y + h / 2 + 10,
                                           fill='#fffdf5', outline='#f2b8c6')
        bg = self.pcv.create_oval(x - w / 2, y - h / 2 - 3, x + w / 2, y + h / 2 + 3,
                                  fill='#fffdf5', outline='#f2b8c6', width=2)
        tid = self.pcv.create_text(x, y, text='\n'.join(lines), fill='#5a4632',
                                   font=('Microsoft YaHei UI', 10, 'bold'),
                                   justify='center', width=PetWin.W - 30)
        self._bubble_ids = [tail, bg, tid]
        self._bubble_until = time.perf_counter() + dur

    def _clear_bubble(self):
        if self._bubble_ids:
            for i in self._bubble_ids:
                try:
                    self.pcv.delete(i)
                except Exception:
                    pass
            self._bubble_ids = None

    def _check_bubble(self):
        if not self._bubble_ids:
            return
        if time.perf_counter() > self._bubble_until:
            self._clear_bubble()

    def _float_text(self, text, color, x=None, y=None):
        if x is None:
            x = self.rest_x + random.randint(-60, 60)
            y = self.rest_y - random.randint(40, 110)
        self._floats.append({
            'id': self.cv.create_text(x, y, text=text, fill=color,
                                      font=('Microsoft YaHei UI', random.choice((12, 14, 16)), 'bold')),
            't': 0.0})

    def _update_floats(self, dt=0.06):
        for f in list(self._floats):
            f['t'] += dt
            if f['t'] > 1.4:
                try:
                    self.cv.delete(f['id'])
                except Exception:
                    pass
                self._floats.remove(f)
                continue
            self.cv.move(f['id'], random.randint(-1, 1), -3)

    def _begin(self):
        self.pcv.coords(self.mon, PetWin.PETX, PetWin.PETY)
        self.file_items = []
        self._file_scale = 1.0
        self._fpos = (0.0, 0.0)
        self._hop_i = -1
        self._bite_mark = 0
        self._pop_played = False
        self._grab_played = False
        self._whoosh_played = False
        self._dinged = False
        self._tada_played = False
        self._lift_played = False
        self._placed = False
        self._wake_played = False
        self.crumb = None
        self._cx = self._cy = 0.0
        self.happy_txt = None
        self.wake_txt = None
        self.parts = []
        self.seg_i = 0
        self.seg_t0 = time.perf_counter()
        p = (self._px, self._py)
        self._wx, self._wy = (int(p[0]), int(p[1])) if p else (self.rest_x, self.rest_y)

    def _ptt_start(self):
        self._ptt_busy = True
        play('pop')
        log('ptt: listening')
        threading.Thread(target=self._ptt_run, daemon=True).start()

    def _ptt_run(self):
        try:
            import asyncio
            from winsdk.windows.globalization import Language
            from winsdk.windows.media.speechrecognition import (
                SpeechRecognizer, SpeechRecognitionListConstraint)

            async def run():
                rec = SpeechRecognizer(Language('zh-CN'))
                rec.constraints.append(
                    SpeechRecognitionListConstraint(list(VOICE_WORDS)))
                await rec.compile_constraints_async()
                result = await rec.recognize_async()
                if result and result.text:
                    conf_map = {0: 0.95, 1: 0.65, 2: 0.30, 3: 0.05}
                    conf = conf_map.get(int(result.confidence), 0.1)
                    VOICE_Q.put(result.text + '|' + str(conf))
                    log('ptt heard: %s (%.2f)' % (result.text, conf))

            asyncio.run(run())
        except Exception as e:
            log('ptt error: ' + str(e))
        self._ptt_busy = False
        try:
            self.mic_win.set_on(False)
        except Exception:
            pass

    def _anchor(self, fg, orig):
        px0, py0, px1, py1 = self.prim
        if orig and 'desktop' in orig.lower():
            return (px0 + int((px1 - px0) * (0.32 + 0.08 * random.random())),
                    py0 + int((py1 - py0) * 0.42))
        a = anchor_from_fg(fg, self.vx, self.vy, self.W, self.H)
        if a:
            return a[0] - self.vx, a[1] - self.vy
        return (px0 + px1) // 2 - 40, (py0 + py1) // 2 - 70

    def start_delete(self, name, count, fg=None, orig=None):
        if self.animating:
            return
        self.animating = True
        self._stop_idle()
        self._begin()
        self._job_kind = 'del'
        self.bx, self.by = self.binx, self.biny
        self.fx, self.fy = self._anchor(fg, orig)
        self.mgx, self.mgy = self.fx - 140, self.fy + 80
        dist = math.hypot(self.mgx - self.rest_x, self.mgy - self.rest_y)
        self.run_hops = max(3, int(0.5 + dist / 600 * 2.2))
        dist_back = math.hypot(self.mgx + 10 - self.rest_x, self.mgy - self.rest_y)
        self.ret_x = self.mgx + 10
        self.ret_y = self.mgy
        self.ret_hops = max(3, int(0.5 + dist_back / 600 * 2.2))
        label_txt = f'《{name}》' + (f'  等 {count} 个文件' if count > 1 else '')
        self._set_label(self.fx, self.fy - 95, label_txt, True)
        self.segs = [
            (D(0.70), self._ph_wake),
            (D(0.5 + dist / 600), self._ph_run_to),
            (D(2.10), self._ph_chomp),
            (D(1.00), self._ph_happy),
            (D(0.5 + dist_back / 600), self._ph_return),
            (D(0.90), self._ph_settle),
        ]
        self._tick()

    def start_restore(self, name, orig, count, fg=None):
        if self.animating:
            return
        self.animating = True
        self._stop_idle()
        self.bx, self.by = self.binx, self.biny
        self.dx, self.dy = self._anchor(fg, orig)
        self._job_kind = 'restore'
        self.dmg = self.dy + 85
        dist = math.hypot(self.dx + 100 - self.rest_x, self.dmg - self.rest_y)
        self.ret_x = self.dx + 100
        self.ret_y = self.dmg
        self.ret_hops = max(3, int(0.5 + dist / 600 * 2.2))
        self._begin()
        txt = f'《{name}》已还原' + (f'  ×{count}' if count > 1 else '')
        if orig:
            txt += f'\n→ {orig}'
        self._set_label(self.dx, self.dy - 100, txt, False)
        self.segs = [
            (D(0.70), self._ph_wake),
            (D(0.70), self._ph_to_bin),
            (D(0.80), self._rp_lift),
            (D(1.90), self._rp_carry),
            (D(0.50), self._rp_place),
            (D(1.10), self._rp_happy),
            (D(0.5 + dist / 600), self._ph_return),
            (D(0.90), self._ph_settle),
        ]
        self._tick()

    def start_empty(self):
        if self.animating:
            return
        self.animating = True
        self._stop_idle()
        self.bx, self.by = self.binx, self.biny
        self._begin()
        self._job_kind = 'empty'
        self.segs = [
            (D(0.70), self._ph_wake),
            (D(1.00), self._ep_shake),
            (D(0.90), self._ph_settle),
        ]
        self._tick()

    def _tick(self, gen=None):
        if gen is None:
            gen = self._gen
        if gen != self._gen or not self.animating:
            return
        try:
            now = time.perf_counter()
            dur, fn = self.segs[self.seg_i]
            k = min(1.0, (now - self.seg_t0) / dur)
            fn(k)
            self._update_parts()
            if k >= 1.0:
                self.seg_i += 1
                self.seg_t0 = now
                if self.seg_i >= len(self.segs):
                    self._gen += 1
                    self._end_job()
                    return
            self.root.after(16, self._tick, gen)
        except Exception:
            log('tick: ' + traceback.format_exc().replace('\n', ' | '))
            self._gen += 1
            self._end_job()

    def _set_label(self, x=None, y=None, text=None, show=None):
        if text is not None:
            self.cv.itemconfigure(self.label, text=text)
            self.cv.itemconfigure(self.label_sh, text=text)
        if x is not None:
            self.cv.coords(self.label, x, y)
            self.cv.coords(self.label_sh, x + 1, y + 1)
        if show is not None:
            st = 'normal' if show else 'hidden'
            self.cv.itemconfigure(self.label, state=st)
            self.cv.itemconfigure(self.label_sh, state=st)

    def _run_move(self, k, x0, x1, y0, y1, hops, left=False):
        ke = k * k * (3 - 2 * k)
        x = x0 + (x1 - x0) * ke
        y = y0 + (y1 - y0) * ke - abs(math.sin(k * math.pi * hops)) * HOP_AMP
        hi = int(k * hops)
        if hi != self._hop_i:
            self._hop_i = hi
            play('step')
        now = time.perf_counter()
        if 'run_right' in SPR:
            seq = SPR['run_left'] if left else SPR['run_right']
            img = seq[int(now * 15) % len(seq)]
        elif left:
            img = SPR['run_b_l'] if int(now * 10) % 2 == 0 else SPR['run_a_l']
        else:
            img = SPR['run_a'] if int(now * 10) % 2 == 0 else SPR['run_b']
        self._pet(x, y)
        self.pcv.itemconfigure(self.mon, image=img)
        return x, y

    def pet_double(self):
        if self.animating or not self.idling:
            return
        log('event pet: double')
        self._gen += 1
        self.animating = True
        self._stop_idle()
        self.idling = False
        self._begin()
        self.bx, self.by = self.binx, self.biny
        self._job_kind = 'pet'
        self._react_lock = time.perf_counter() + 0.6
        self.segs = [
            (D(0.35), self._ph_wake),
            (D(1.5), self._ph_double),
            (D(0.5), self._ph_settle),
        ]
        self._tick()

    def _ph_double(self, k):
        if not self._tada_played:
            self._tada_played = True
            play('squeak')
            self._bubble(random.choice(pet_phrases()['double']))
            for _ in range(3):
                self._float_text(random.choice(('?', '!')), '#ffd166')
        y = self.rest_y - abs(math.sin(k * math.pi * 4)) * 14
        ox = math.sin(k * 30) * 4 * (1 - k)
        self._pet(self.rest_x + ox, y)
        seq = SPR.get('chat') or SPR['interact']
        self.pcv.itemconfigure(self.mon, image=seq[int(time.perf_counter() * 12) % len(seq)])

    def voice_greet(self):
        if self.animating or not self.idling:
            return
        log('event pet: voice')
        self._gen += 1
        self.animating = True
        self._stop_idle()
        self.idling = False
        self._begin()
        self.bx, self.by = self.binx, self.biny
        self._job_kind = 'pet'
        self._react_lock = time.perf_counter() + 0.6
        self._morning_hi = True
        self.segs = [
            (D(0.45), self._ph_wake),
            (D(1.6), self._ph_greet),
            (D(0.5), self._ph_settle),
        ]
        self._tick()

    def _ph_greet(self, k):
        if not self._tada_played:
            self._tada_played = True
            play('squeak')
            if getattr(self, '_morning_hi', False):
                self._morning_hi = False
                pool = pet_phrases()['morning']
            elif self._dayphase() == 'night':
                pool = pet_phrases()['night_wake']
            else:
                pool = pet_phrases()['greet_guga'] if CFG['pet'] == 'guga' else pet_phrases()['greet']
            self._bubble(random.choice(pool))
            for _ in range(3):
                self._float_text('♪', '#9fd8ff')
        y = self.rest_y - abs(math.sin(k * math.pi * 2)) * 10
        self._pet(self.rest_x, y)
        seq = SPR.get('chat') or SPR['interact']
        self.pcv.itemconfigure(self.mon, image=seq[int(time.perf_counter() * 12) % len(seq)])

    def feed_orange(self):
        if self.animating or not self.idling:
            return
        log('event pet: feed')
        self._gen += 1
        self.animating = True
        self._stop_idle()
        self.idling = False
        self._begin()
        self.bx, self.by = self.binx, self.biny
        self._job_kind = 'pet'
        self._react_lock = time.perf_counter() + 0.6
        self.ox, self.oy = self.rest_x + 95, self.rest_y - 30
        self.segs = [
            (D(0.7), self._ph_orange_drop),
            (D(1.8), self._ph_orange_eat),
            (D(0.9), self._ph_orange_happy),
            (D(0.5), self._ph_settle),
        ]
        self._tick()

    def _draw_orange(self, x, y, s=1.0):
        for i in self.orange_ids:
            try:
                self.cv.delete(i)
            except Exception:
                pass
        r = 22 * s
        self.orange_ids = [
            self.cv.create_oval(x - r, y - r, x + r, y + r,
                                fill='#ff9f43', outline='#c96f2a', width=2),
            self.cv.create_oval(x - r * 0.35, y - r - 8 * s, x + r * 0.35, y - r + 2 * s,
                                fill='#7ddb5f', outline='#4ba83a', width=1)]

    def _ph_orange_drop(self, k):
        if not self._pop_played:
            self._pop_played = True
            play('pop')
        y = 40 + (self.oy - 40) * (k * k)
        self._draw_orange(self.ox, y)
        self._pet(self.rest_x, self.rest_y)
        seq = SPR.get('idle') or SPR['sleep']
        self.pcv.itemconfigure(self.mon, image=seq[0])
        if k >= 1.0 and not self._dinged:
            self._dinged = True
            play('step')

    def _ph_orange_eat(self, k):
        lunge = math.sin(min(1.0, k * 2) * math.pi / 2) * 25
        self._pet(self.rest_x + lunge, self.rest_y)
        if 'eat' in SPR:
            self.pcv.itemconfigure(self.mon,
                                  image=SPR['eat'][int(time.perf_counter() * 12) % len(SPR['eat'])])
        s = 1.0 - 0.45 * k
        self._draw_orange(self.ox, self.oy, s)
        if k > 0.45 and not self._wake_played:
            self._wake_played = True
            play('chomp')
            self._spawn_crumbs(self.ox, self.oy, 6)
        if k >= 1.0 and not self._dinged:
            self._dinged = True
            play('chomp')
            self._spawn_sparkles(self.ox, self.oy)

    def _ph_orange_happy(self, k):
        if not self._tada_played:
            self._tada_played = True
            play('tada')
            self.hunger = min(100, self.hunger + 45)
            CFG['hunger'] = self.hunger
            self._hunger_warned = 0
            save_config()
            try:
                if _TRAY.get('icon'):
                    name = '咕嘎' if CFG['pet'] == 'guga' else 'Doro'
                    _TRAY['icon'].title = '%s · 饱食度 %d%%' % (name, self.hunger)
            except Exception:
                pass
            self._bubble(random.choice(pet_phrases()['feed']) + '（饱食度+%d）' % 45, 2.4)
            for _ in range(3):
                self._float_text(random.choice(('♥', '♪')), '#ff8fb3')
        y = self.rest_y - abs(math.sin(k * math.pi * 3)) * 16
        self._pet(self.rest_x, y)
        if 'interact' in SPR:
            self.pcv.itemconfigure(self.mon,
                image=SPR['interact'][int(time.perf_counter() * 12) % len(SPR['interact'])])

    def _ph_wake(self, k):
        if not self._wake_played:
            self._wake_played = True
            play('pop')
            self._float_text('!', '#ffd166', self._wx, self._wy - 100)
        e = 1 - (1 - k) * (1 - k)
        y = self._wy - abs(math.sin(k * math.pi * 2)) * 10 * e
        self._pet(self._wx, y)
        seq = SPR.get('sleep') or SPR.get('idle') or SPR['run_right']
        if k < 0.3:
            self.pcv.itemconfigure(self.mon,
                                  image=seq[min(int(k * 8), len(seq) - 1)])
        else:
            seq2 = SPR.get('idle') or seq
            self.pcv.itemconfigure(self.mon,
                                  image=seq2[int(k * 10) % len(seq2)])

    def _ph_run_to(self, k):
        if not self._pop_played:
            self._pop_played = True
            play('pop')
        self._file_at(self.fx, self.fy, max(0.05, ease_out_back(min(1.0, k * 1.6))), behind=True)
        self._run_move(k, self.rest_x, self.mgx, self.rest_y, self.mgy,
                       self.run_hops, left=self.mgx < self.rest_x)

    def _ph_to_bin(self, k):
        self._run_move(k, self.rest_x, self.bx + 130, self.rest_y, self.by - 24,
                       2, left=False)

    def _ph_return(self, k):
        self._run_move(k, self.ret_x, self.rest_x, self.ret_y, self.rest_y,
                       self.ret_hops, left=self.rest_x < self.ret_x)

    def _ph_settle(self, k):
        if not self._grab_played:
            self._grab_played = True
            play('gulp')
        if k < 0.4:
            self._pet(self.rest_x, self.rest_y)
            seq = SPR.get('idle') or SPR.get('sleep') or SPR['run_right']
            self.pcv.itemconfigure(self.mon,
                                  image=seq[int(k * 8) % len(seq)])
        else:
            kk = (k - 0.4) / 0.6
            y = self.rest_y + math.sin(kk * math.pi) * 3
            self._pet(self.rest_x, y)
            seq = SPR.get('sleep') or SPR.get('idle') or SPR['run_right']
            self.pcv.itemconfigure(self.mon,
                                  image=seq[min(int(kk * 4), len(seq) - 1)])

    def _ph_pop(self, k):
        if not self._pop_played:
            self._pop_played = True
            play('pop')
        self._file_at(self.fx, self.fy, max(0.05, ease_out_back(k)), behind=True)

    def _ph_chomp(self, k):
        n = 3
        ph = k * n
        i = int(min(ph, n - 1e-9))
        f = ph - i
        lunge = math.sin(f * math.pi) * 22
        if 'eat' in SPR:
            img = SPR['eat'][int(time.perf_counter() * 12) % len(SPR['eat'])]
        else:
            img = SPR['chomp_open'] if f < 0.5 else SPR['chomp_closed']
        self._pet(self.mgx + lunge, self.mgy)
        self.pcv.itemconfigure(self.mon, image=img)
        shake = math.sin(k * 95) * 4
        if self.file_items:
            self._file_at(self.fx + shake, self.fy + shake * 0.6, self._file_scale, behind=True)
            self._set_label(self.fx + shake, self.fy - 95)
        if f >= 0.5 and self._bite_mark <= i:
            self._bite_mark = i + 1
            self._bite(i)

    def _bite(self, i):
        play('chomp')
        self._spawn_crumbs(self.fx, self.fy, 10)
        if i >= 2:
            for it in self.file_items:
                self.cv.delete(it)
            self.file_items = []
            self._set_label(show=False)
            self._spawn_sparkles(self.fx, self.fy)
        else:
            self._file_scale = 1.0 - 0.26 * (i + 1)
            self._file_at(self.fx, self.fy, self._file_scale, behind=True)

    def _ph_happy(self, k):
        if not self._tada_played:
            self._tada_played = True
            play('tada')
            self._bubble(random.choice(pet_phrases()['del_done']), 2.0)
            for _ in range(3):
                self._float_text(random.choice(('♥', '♪', '♡')), '#ff8fb3')
        y = self.mgy - abs(math.sin(k * math.pi * 3)) * 16
        self._pet(self.mgx + 10, y)
        if 'interact' in SPR:
            self.pcv.itemconfigure(self.mon, image=SPR['interact'][int(time.perf_counter() * 12) % len(SPR['interact'])])
        else:
            self.pcv.itemconfigure(self.mon, image=SPR['happy'])

    def _rp_lift(self, k):
        if not self._lift_played:
            self._lift_played = True
            play('pop')
            self._spawn_sparkles(self.bx, self.by - 40)
            self._float_text('!', '#ffd166', self.bx, self.by - 90)
        self._pet(self.bx + 130, self.by - 26)
        self.pcv.itemconfigure(self.mon, image=SPR['carry_l'])
        e = 1 - (1 - k) ** 2
        s = 0.55 + 0.30 * k
        self._file_at(self.bx - 4, self.by + 70 - 165 * e, s)
        if k >= 1.0 and not self._grab_played:
            self._grab_played = True
            play('gulp')

    def _rp_carry(self, k):
        x0, y0 = self.bx + 130, self.by - 26
        x1, y1 = self.dx + 100, self.dmg
        x, y = self._run_move(k, x0, x1, y0, y1, 4, left=True)
        self._file_at(x - 8, y - 128, 0.85)

    def _rp_place(self, k):
        if not self._placed:
            self._placed = True
            play('whoosh')
        px0, py0 = self._fpos
        x = px0 + (self.dx - px0) * k
        y = py0 + (self.dy - py0) * min(1.0, k * k)
        self._file_at(x, y, 0.85)
        self._pet(self.dx + 100, self.dmg)
        self.pcv.itemconfigure(self.mon, image=SPR['idle'][0] if 'idle' in SPR else SPR['run_b_l'])
        if k >= 1.0:
            play('chomp')
            self._spawn_sparkles(self.dx, self.dy - 30)

    def _rp_happy(self, k):
        if not self._tada_played:
            self._tada_played = True
            play('tada')
            self._set_label(show=True)
            self._bubble(random.choice(pet_phrases()['restore_done']), 2.0)
            for _ in range(3):
                self._float_text(random.choice(('♥', '♪')), '#ff8fb3')
        y = self.dmg - abs(math.sin(k * math.pi * 3)) * 16
        self._pet(self.dx + 100, y)
        if 'interact' in SPR:
            self.pcv.itemconfigure(self.mon, image=SPR['interact'][int(time.perf_counter() * 12) % len(SPR['interact'])])
        else:
            self.pcv.itemconfigure(self.mon, image=SPR['happy_l'])

    def _ep_shake(self, k):
        if not self._whoosh_played:
            self._whoosh_played = True
            play('whoosh')
            self._bubble(random.choice(('呼——全没了！', '一下子空空如也~', '打扫干净啦！')), 2.2,
                         self._wx, self._wy - 115)
        ox = math.sin(k * 45) * 6 * (1 - k)
        self._pet(self._wx + ox, self._wy)
        self.pcv.itemconfigure(self.mon,
                              image=SPR['comfort'][int(time.perf_counter() * 12) % len(SPR['comfort'])])
        if k > 0.4 and not self._dinged:
            self._dinged = True
            play('ding')
            self._spawn_sparkles(self._wx, self._wy - 50)
            for _ in range(3):
                self._float_text('呼~', '#9fe8ff', self._wx + random.randint(-40, 40),
                                 self._wy - random.randint(30, 90))

    def _file_at(self, x, y, s, behind=False):
        for it in self.file_items:
            self.cv.delete(it)
        self.file_items = []
        w, h = 92 * s, 112 * s
        x0, y0, x1, y1 = x - w / 2, y - h / 2, x + w / 2, y + h / 2
        fold = 22 * s
        lw = max(1, int(2 * s))
        ids = self.file_items
        ids.append(self.cv.create_rectangle(x0, y0, x1, y1, fill='#f4f7fb',
                                            outline='#7f8ea3', width=lw))
        ids.append(self.cv.create_polygon(x1 - fold, y0, x1, y0 + fold, x1 - fold, y0 + fold,
                                          fill='#c7d3e2', outline='#7f8ea3', width=lw))
        for i in range(1, 4):
            yy = y0 + h * (0.18 + 0.19 * i)
            endx = x1 - 16 * s
            if yy <= y0 + fold + 2 * s:
                endx = min(endx, x1 - fold - 6 * s)
            ids.append(self.cv.create_line(x0 + 12 * s, yy, endx, yy,
                                           fill='#b9c6d6', width=max(1, int(2 * s))))
        self._fpos = (x, y)

    def _spawn_crumbs(self, x, y, n):
        for _ in range(n):
            self.parts.append({
                'x': x + random.uniform(-34, 34), 'y': y + random.uniform(-28, 28),
                'vx': random.uniform(-170, 170), 'vy': random.uniform(-270, -40),
                'g': 750, 'life': random.uniform(0.45, 0.85), 't': 0.0,
                'c': random.choice(CRUMB_COLORS), 'id': None,
                's': random.choice((4, 5, 6, 7)),
            })

    def _spawn_sparkles(self, x, y):
        for _ in range(14):
            ang = random.uniform(0, 2 * math.pi)
            sp = random.uniform(40, 170)
            self.parts.append({
                'x': x, 'y': y, 'vx': math.cos(ang) * sp, 'vy': math.sin(ang) * sp - 60,
                'g': 120, 'life': random.uniform(0.4, 0.7), 't': 0.0,
                'c': random.choice(SPARK_COLORS), 'id': None,
                's': random.choice((3, 4, 5)),
            })

    def _update_parts(self, dt=0.016):
        for p in list(self.parts):
            p['t'] += dt
            if p['t'] >= p['life']:
                if p['id'] is not None:
                    self.cv.delete(p['id'])
                self.parts.remove(p)
                continue
            p['x'] += p['vx'] * dt
            p['y'] += p['vy'] * dt
            p['vy'] += p['g'] * dt
            s = p['s']
            if p['id'] is None:
                p['id'] = self.cv.create_rectangle(p['x'], p['y'], p['x'] + s, p['y'] + s,
                                                   fill=p['c'], outline='')
            else:
                self.cv.coords(p['id'], p['x'], p['y'], p['x'] + s, p['y'] + s)

    def _end_job(self):
        self._gen += 1
        ids = []
        for i in self.orange_ids:
            ids.append(i)
        self.orange_ids = []
        for it in self.file_items:
            ids.append(it)
        if self.crumb:
            ids += self.crumb
        if self.happy_txt:
            ids.append(self.happy_txt)
        if self.wake_txt:
            ids.append(self.wake_txt)
        for p in self.parts:
            if p['id'] is not None:
                ids.append(p['id'])
        for it in ids:
            try:
                self.cv.delete(it)
            except Exception:
                pass
        self.parts = []
        self.crumb = None
        self.file_items = []
        self.happy_txt = None
        self.wake_txt = None
        self._set_label(show=False)
        self.animating = False
        self.rest_x, self.rest_y = self._clamp_home(self.rest_x, self.rest_y)
        self.go_idle()





class DropWin:
    SIZE = 60

    def __init__(self, show, x, kind):
        self.show = show
        self.kind = kind
        self.fx = show
        self.root = tk.Toplevel()
        self.root.overrideredirect(True)
        self.root.attributes('-topmost', True)
        self.root.config(bg=MAGIC)
        try:
            self.root.attributes('-transparentcolor', MAGIC)
        except tk.TclError:
            pass
        self.root.geometry('%dx%d+%d+%d' % (self.SIZE, self.SIZE, x, -self.SIZE))
        self.cv = tk.Canvas(self.root, width=self.SIZE, height=self.SIZE, bg=MAGIC,
                            highlightthickness=0, bd=0)
        self.cv.pack()
        self.root.update_idletasks()
        hwnd = user32.GetParent(self.root.winfo_id())
        style = _get_long(hwnd, -20)
        _set_long(hwnd, -20, style | 0x00080000 | 0x00000020 | 0x08000000 | 0x00000080)
        self._draw(kind)
        self.state = {'x': float(x), 'y': 20.0, 'vx': random.uniform(-80, 80),
                      'vy': 0.0, 'b': 0, 't': 0.0, 'rest': 0.0}
        self.root.after(16, self._tick)

    def _draw(self, kind):
        try:
            from PIL import Image, ImageTk
            p = os.path.join(ASSETS_PETS, 'foods', kind + '.png')
            im = Image.open(p).convert('RGBA')
            im = resiz_rgba(im, 48, 48)
            self._img = ImageTk.PhotoImage(im)
            c = self.SIZE // 2
            self.cv.create_image(c, c, image=self._img)
        except Exception:
            c = self.SIZE // 2
            self.cv.create_oval(c - 14, c - 14, c + 14, c + 14,
                                fill='#ff9f43', outline='#e07b2a', width=2)

    def _tick(self):
        st = self.state
        dt = 0.016
        if st['rest'] > 0:
            st['rest'] -= dt
            if st['rest'] <= 0:
                self._finish()
                return
        else:
            st['t'] += dt
            st['vy'] += 2200 * dt
            st['x'] += st['vx'] * dt
            st['y'] += st['vy'] * dt
            hb = self.show.home[3]
            if st['y'] >= hb - 110:
                st['y'] = hb - 110
                if st['b'] < 2 and abs(st['vy']) > 200:
                    st['vy'] = -st['vy'] * random.uniform(0.3, 0.45)
                    st['vx'] = st['vx'] * 0.7 + random.uniform(-60, 60)
                    st['b'] += 1
                    play('step')
                else:
                    st['vy'] = 0
                    st['vx'] = 0
                    st['rest'] = 30.0
                    self._notify_pet()
            hl, ht, hr = self.show.home[0], self.show.home[1], self.show.home[2]
            st['x'] = max(hl + 30, min(hr - 30, st['x']))
            st['y'] = max(ht + 30, st['y'])
        wx = int(st['x'] - self.SIZE // 2)
        wy = int(st['y'] - self.SIZE // 2)
        self.root.geometry('+%d+%d' % (wx, wy))
        self.root.after(16, self._tick)

    def _notify_pet(self):
        show = self.show
        if show.idling and not show.animating and not show.hidden:
            if self.kind != 'paper':
                show._wander_phrase = '白捡的%s！开动~' % {
                    'orange': '橙子', 'apple': '苹果', 'banana': '香蕉',
                    'burger': '汉堡', 'pizza': '披萨', 'fries': '薯条',
                    'icecream': '冰淇淋', 'cookie': '饼干', 'cake': '蛋糕',
                    'strawberry': '草莓', 'grape': '葡萄', 'watermelon': '西瓜',
                }.get(self.kind, '好吃的')
                show._pending_drop = self
            else:
                show._wander_phrase = '谁乱扔垃圾！我看看…'
            show._pending_drop = self
            show.start_wander(target=(self.state['x'], self.show.home[3] - 125))

    def _consume(self):
        self.state['rest'] = 999
        self.root.after(120, lambda: self._shrink(28))

    def _shrink(self, sz):
        if sz <= 4:
            self._finish()
            return
        for item in self.cv.find_all():
            self.cv.delete(item)
        c = self.SIZE // 2
        try:
            from PIL import Image, ImageTk
            p = os.path.join(ASSETS_PETS, 'foods', self.kind + '.png')
            im = Image.open(p).convert('RGBA')
            im = resiz_rgba(im, sz, sz)
            self._img = ImageTk.PhotoImage(im)
            self.cv.create_image(c, c, image=self._img)
        except Exception:
            self.cv.create_oval(c - sz // 2, c - sz // 2, c + sz // 2, c + sz // 2,
                                fill='#ff9f43', outline='')
        self.root.after(80, lambda: self._shrink(sz - 3))

    def _finish(self):
        try:
            self.root.destroy()
        except Exception:
            pass


def main():
    if not acquire_single_instance():
        sys.exit(0)
    try:
        ctypes.windll.winmm.timeBeginPeriod(1)
    except Exception:
        pass
    load_config()
    log_trim()
    log('=== DoroPet started ===')
    ensure_sfx()
    ov = Overlay()
    build_sprites()
    show = MonsterShow(ov)
    if '--test' in sys.argv:
        print('演示播放中（打盹 -> 删除 -> 还原）...')
        show.go_idle()
        show.root.after(1600, lambda: show.start_delete('示例_删我试试.txt', 1))
        show.root.after(11500, lambda: show.start_restore('示例_还原啦.txt',
                                                        os.path.expanduser('~\\Desktop'), 1))
        show.root.after(22000, show.root.destroy)
    else:
        q = queue.Queue()
        cmd_q = queue.Queue()
        vtest = {'ok': False, 'until': 0}
        threading.Thread(target=watcher, args=(q,), daemon=True).start()
        start_tray(cmd_q)

        def poll():
            do_quit = False
            try:
                while True:
                    c = cmd_q.get_nowait()
                    if c == 'quit':
                        do_quit = True
                        break
                    if c == 'demo':
                        if not show.animating:
                            show.start_delete('示例_演示动画.txt', 1)
                    elif c == 'feed':
                        show.feed_orange()
                    elif c == 'boss':
                        show.toggle_hidden()
                    elif c == 'goclimb':
                        if show.edge:
                            show.detach_edge()
                            if show.idling:
                                show._bubble('下来休息啦~', 2.0)
                        else:
                            hl, ht, hr, hb = show.home
                            d = [('left', show.rest_x - hl),
                                 ('right', hr - show.rest_x),
                                 ('bottom', hb - show.rest_y)]
                            side, _ = min(d, key=lambda t: t[1])
                            show.attach_edge(side)
                    elif c == 'winwalk':
                        show.start_winwalk()
                    elif c == 'pet_doro':
                        switch_pet('doro', show)
                    elif c == 'pet_guga':
                        switch_pet('guga', show)
                    elif c == 'pet_deepseek':
                        switch_pet('deepseek', show)
                    elif c == 'pet_jokebear':
                        switch_pet('jokebear', show)
                    elif c == 'voice':
                        CFG['voice'] = not CFG['voice']
                        save_config()
                        if show.idling:
                            show._bubble('按T说话已开启~' if CFG['voice'] else '语音已关闭', 2.0)
                    elif c == 'voicetest':
                        if show.idling:
                            show._bubble('语音自检：我说你听~', 2.0, speak=False)
                        if not CFG['voice']:
                            CFG['voice'] = True
                            save_config()
                            time.sleep(0.5)
                        vtest['ok'] = False
                        vtest['until'] = time.perf_counter() + 14
                        speak_async('你好')
                        show.root.after(4000, lambda: speak_async('你好朵萝'))
                        def _vtest_result():
                            if vtest['until'] and not vtest['ok']:
                                vtest['until'] = 0
                                log('voice selftest FAILED')
                                if show.idling:
                                    show._bubble('识别器收到的是静音。请检查：声音设置里默认输入是否为真实麦克风；麦克风属性里关闭"音频增强"（Nahimic）', 6.0, speak=False)
                                speak_async('语音收不到声音，请检查麦克风的音频增强设置', 30)
                        show.root.after(15000, _vtest_result)
                    elif c == 'sound':
                        CFG['sound'] = not CFG['sound']
                        save_config()
                    elif c == 'autostart':
                        set_autostart(not autostart_enabled())
            except queue.Empty:
                pass
            if do_quit:
                try:
                    if _TRAY.get('icon'):
                        _TRAY['icon'].stop()
                except Exception:
                    pass
                try:
                    ctypes.windll.winmm.timeEndPeriod(1)
                except Exception:
                    pass
                stop_voice()
                try:
                    show.pw.destroy()
                except Exception:
                    pass
                try:
                    show.mic_win.destroy()
                except Exception:
                    pass
                try:
                    show.ov.root.destroy()
                except Exception:
                    pass
                return
            try:
                while True:
                    text = VOICE_Q.get_nowait()
                    if text.startswith('DEVICE:'):
                        log('voice device: ' + text[7:].strip())
                        continue
                    if text.startswith('READY:'):
                        lang = text[6:].strip()
                        log('voice ready: ' + lang)
                        if show.idling:
                            if lang.lower().startswith('zh'):
                                show._bubble('语音唤醒开启~ 试试说：你好朵萝', 3.2)
                            else:
                                show._bubble('Voice on ~ say: hello doro', 3.2)
                        continue
                    if text.startswith('ERROR:'):
                        log('voice error: ' + text)
                        stop_voice()
                        CFG['voice'] = False
                        save_config()
                        if show.idling:
                            show._bubble('语音引擎启动失败（检查麦克风权限）', 3.0)
                        continue
                    if text.startswith('LEVEL:'):
                        log('voice mic level: ' + text[6:].strip())
                        continue
                    phrase, conf = text, 1.0
                    if '|' in text:
                        p, _, cs = text.rpartition('|')
                        try:
                            conf = float(cs)
                            phrase = p
                        except ValueError:
                            pass
                    log('voice heard: %s (%.2f)' % (phrase, conf))
                    if vtest['until'] and time.perf_counter() < vtest['until'] and conf >= 0.25:
                        vtest['ok'] = True
                        vtest['until'] = 0
                        log('voice selftest OK')
                        if show.idling:
                            show._bubble('语音正常！我听得见你~', 3.0)
                    if conf < 0.25:
                        continue
                    t = phrase.lower()
                    if any(w in t for w in ('躲起来', '消失', '别烦我')):
                        if conf < 0.85:
                            continue
                        if not show.hidden:
                            show.toggle_hidden()
                        continue
                    if show.hidden:
                        continue
                    matched = False
                    for pet_id in ('doro', 'guga', 'deepseek', 'jokebear'):
                        words = PET_INFO.get(pet_id, {}).get('voice_words', [])
                        if any(w in t for w in words):
                            if CFG['pet'] != pet_id:
                                switch_pet(pet_id, show)
                            else:
                                show.voice_greet()
                            matched = True
                            break
                    if matched:
                        pass
                    elif '萌' in t or 'cute' in t:
                        show.pet_hover()
                    elif '睡' in t or 'sleep' in t:
                        if show.idling:
                            show._bubble(random.choice(('早睡着了！', 'zzz...')), 2.0)
                    elif '换' in t or 'switch' in t:
                        all_pets = ('doro', 'guga', 'deepseek', 'jokebear')
                        idx = all_pets.index(CFG['pet']) if CFG['pet'] in all_pets else 0
                        switch_pet(all_pets[(idx + 1) % len(all_pets)], show)
                    else:
                        show.voice_greet()
            except queue.Empty:
                pass
            if not show.animating:
                ev = None
                try:
                    ev = q.get_nowait()
                except queue.Empty:
                    pass
                if ev:
                    try:
                        if ev[0] == 'del':
                            show.start_delete(ev[1], ev[3], ev[4], ev[2])
                        elif ev[0] == 'restore':
                            show.start_restore(ev[1], ev[2], ev[3], ev[4])
                        elif ev[0] == 'empty':
                            show.start_empty()
                        log('playing: ' + ev[0])
                    except Exception:
                        log('show error: ' + traceback.format_exc().replace('\n', ' | '))
            show.root.after(160, poll)

        show.root.after(160, poll)
        show.go_idle()
        show._drop_sched()
        if CFG['edge'] in ('left', 'right', 'bottom', 'top'):
            show.attach_edge(CFG['edge'], CFG['edge_c'])
        if CFG['voice']:
            log('voice mode: push-to-talk (T key)')
        print('=' * 46)
        print(' Doro咕嘎桌宠已就位！')
        print(' 现在把一个文件删除到回收站试试～')
        print(' 还原/清空回收站也有动画哦')
        print('=' * 46)
    show.root.mainloop()


if __name__ == '__main__':
    main()
