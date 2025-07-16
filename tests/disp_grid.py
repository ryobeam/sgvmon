import sys
import os
import time
import signal

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../sgvmon/lib')))
from fb import Framebuffer
from nvsend import ImageSender

# ネットワーク設定
HOST = "192.168.1.27"  # ローカルホスト


def cleanup(signum, frame):
    """Ctrl+C時のクリーンアップ処理"""
    if framebuffer:
        # 画面を黒でクリア
        black_screen = Image.new('RGB', (480, 320), (0, 255, 0))
        framebuffer.write_image(black_screen)
    sys.exit(0)

# シグナルハンドラを設定
signal.signal(signal.SIGINT, cleanup)

# メイン処理
framebuffer = Framebuffer()
framebuffer.open()

# バッファ用の画像を作成
buffer_img = Image.new('RGB', (480, 320), (255, 255, 255))
draw = ImageDraw.Draw(buffer_img)

# グリッドの設定
GRID_SIZE = 40  # グリッドのマス目のサイズ
GRID_COLOR = (0, 0, 0)  # グリッドの色（白）

# グリッドを描画
for x in range(0, 480, GRID_SIZE):
    draw.line([(x, 0), (x, 320)], fill=GRID_COLOR, width=2)
for y in range(0, 320, GRID_SIZE):
    draw.line([(0, y), (480, y)], fill=GRID_COLOR, width=2)

# 画面に表示
framebuffer.write_image(buffer_img)
# 画像送信
sender = ImageSender(HOST)
#sender.send_image(buffer_img)

try:
    while True:
        sender.send_image(buffer_img)
        time.sleep(1)  # CPUの使用率を下げるために待機
except KeyboardInterrupt:
    cleanup(None, None) 
