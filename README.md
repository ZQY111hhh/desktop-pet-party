# Doro Guga Desktop Pet | Doro咕嘎桌宠

一只住在屏幕右下角的桌面宠物。删除文件时跑来吃掉，还原时搬回来，平时打盹、爬墙、等你投喂。支持 4 个角色切换，每个角色有专属台词和行为风格。

![License](https://img.shields.io/badge/license-MIT-blue)
![Platform](https://img.shields.io/badge/platform-Windows-0078D6)
![Python](https://img.shields.io/badge/Python-3.11-3776AB)

## v2.0 更新

- 新增 2 个角色：**DeepSeek酱**（AI 梗台词：算力不足、偷吃 token）和**玩笑熊**（吃货台词：汉堡！汉堡！）
- 每个角色 **18 种场景 × 5~7 条专属台词**（说话风格完全不同）
- 动作连贯性优化：smoothstep 加减速、入睡/醒来过渡动画、空闲转睡眠缓冲
- 天降食物系统：12 种 Twemoji 彩色图标（橙子/苹果/汉堡/披萨等），带弹跳+滚动物理
- 独立窗口架构：每只宠物一个小窗口（Shimeji 同款），互不遮挡，支持未来多宠同屏
- 语音按钮：固定在屏幕右下角，点一下说话再点一下取消（不再需要键盘按键）
- 精灵边缘抗锯齿：预乘 alpha 缩放，消除色键透明窗口的黑边问题

## 功能一览

### 回收站联动
- **删除文件** → 小怪兽惊醒，跑到你删除时所在的窗口，坐在文件旁边一口口吃掉，然后走回去睡觉
- **还原文件** → 它从屏幕角落把文件搬出来，送到你当前看的窗口，标注原位置
- **清空回收站** → 它吓得一抖，"呼~"的一下全没了

### 桌宠养成
- **打盹系统** → 平时坐在右下角睡觉冒 Zzz，按作息时间活动
- **作息时间** → 深夜沉睡 / 早晨伸懒腰问好 / 晚上犯困打哈欠
- **饱食度** → 随时间下降，饿了会讨食；托盘"喂个橙子"恢复
- **心情反应** → 摸头卖萌 / 被打装可怜 / 双击吓一跳 / 拖拽搬家

### 爬墙 & 躲猫猫
- **白天** → 吸附屏幕四边，旋转 90° 贴墙攀爬，或倒挂天花板巡逻
- **夜晚** → 藏到屏幕边缘后面，只露小脑袋偷偷看你，探头张望又缩回去

### 语音控制
- 屏幕右下角有麦克风按钮，**点一下说话**（再点取消）
- 4 个角色各有专属唤醒词（中文）：
  - Doro：喊"朵萝" / "朵朵"
  - Guga：喊"咕嘎" / "嘎嘎"
  - DeepSeek酱：喊"小鲸鱼" / "蓝鲸" / "小蓝"
  - 玩笑熊：喊"玩笑熊" / "小熊"
- 喊"换角色"按顺序轮换
- 喊"卖个萌"、"睡觉"、"躲起来"触发对应反应
- 每个角色的台词风格完全不同（DeepSeek 说 AI 梗，玩笑熊说汉堡梗）

### 其他玩法
- **甩飞** → 抓住快速甩出，抛物线飞行+弹跳+头晕
- **天降食物** → 每 1~5 分钟随机掉落橙子/苹果/汉堡/披萨等 12 种食物（Twemoji 彩色图标）
- **自由漫游** → 白天偶尔自己出门溜达、跳上你的窗口顶散步
- **老板键** → 托盘"显示/隐藏宠物"一键消失/恢复

## 快速开始

### 方式一：下载可执行文件（推荐）

> **点击右侧 [Releases](https://github.com/ZQY111hhh/doro-guga-desktop-pet/releases) → 下载 `DoroPet_v1.0.zip` → 解压 → 双击 exe 即可运行**

> 注意：不要点绿色的 "Code" 按钮下载，那只有源代码没有可执行文件

> 需要 Windows 10+，语音功能需安装中文语言包

### 方式二：从源码运行

```bash
git clone https://github.com/你的用户名/FileMonster.git
cd FileMonster
pip install pillow pystray winsdk
python file_monster.py
```

### 打包为 exe

```bash
pip install pyinstaller
pyinstaller --onedir --windowed --name FileMonster ^
    --icon=assets/doro.ico ^
    --hidden-import=pystray._win32 ^
    --collect-all winsdk ^
    --contents-directory _internal ^
    file_monster.py
```

## 使用说明

| 操作 | 效果 |
|---|---|
| 鼠标悬停 | 惊醒卖萌，冒爱心 |
| 鼠标点击 | 被打装可怜 |
| 快速双击 | 吓一跳 |
| 按住拖拽 | 搬到新位置安家 |
| 快速甩出 | 抛物线飞行+弹跳 |
| 拖到屏幕边缘 | 吸附爬墙（白天）/ 躲猫猫（夜晚） |
| 点麦克风按钮 | 开始/停止语音识别 |
| 托盘右键 | 喂食、爬墙、演示、角色切换、退出等 |

## 配置

编辑 `config.ini`：

```ini
[monster]
sound = on          ; 音效开关
speed = 1.0         ; 动画速度 (0.5~2.0)
pet = doro          ; 默认角色 (doro / guga)
voice = on          ; 语音按钮开关
hunger = 100        ; 饱食度
edge = none         ; 吸附边缘 (left/right/bottom/top/none)
```

## 项目结构

```
FileMonster/
├── FileMonster.exe      # 主程序（PyInstaller 打包）
├── file_monster.py      # 源代码（~2900 行，纯标准库+Pillow）
├── _internal/           # PyInstaller 运行时依赖
├── assets/
│   ├── doro/            # Doro 精灵帧（走/跑/吃/睡/爬墙等）
│   ├── guga/            # Guga 精灵帧
│   ├── foods/           # 掉落食物图标（Twemoji）
│   ├── doro_face.png    # 托盘头像
│   └── doro.ico         # 程序图标
├── config.ini           # 用户配置
└── 使用说明.txt          # 中文说明
```

## 技术栈

- **Python 3.11** + tkinter（GUI）
- **Pillow**（精灵加载、alpha 处理、旋转翻转）
- **pystray**（系统托盘）
- **winsdk**（WinRT 语音识别）
- **ctypes**（Windows API：窗口管理、回收站监控、鼠标轮询）
- **PyInstaller**（打包分发）

## 素材来源

- Doro & Guga 精灵：[hxsworrk-lab/doro-guga-desktop](https://github.com/hxsworrk-lab/doro-guga-desktop)
- 食物图标：[Twemoji](https://github.com/twitter/twemoji)（CC-BY 4.0）
- 音效：程序合成（纯 Python 波形生成）

## License

MIT

## Acknowledgements

灵感来自 [Shimeji](https://shimeji.xyz/) 桌面宠物系列。
