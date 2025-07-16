import sys
import os
import time
import signal

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../sgvmon/lib')))
from fb import Framebuffer

def cleanup(signum, frame):
    """Ctrl+C時のクリーンアップ処理"""
    if framebuffer:
        # 画面を黒でクリア
        black_screen = Image.new('RGB', (480, 320), (0, 0, 0))
        framebuffer.write_image(black_screen)
    sys.exit(0)

# シグナルハンドラを設定
signal.signal(signal.SIGINT, cleanup)

# メイン処理
framebuffer = Framebuffer()
framebuffer.open()

# バッファ用の画像を1回だけ作成
buffer_img = Image.new('RGB', (480, 320), (0, 0, 0))
img_file = Image.open('rk480320.png').convert('RGB')

count = 0
SCREEN_WIDTH = 480
IMAGE_WIDTH = img_file.width

while True:  # 無限ループに変更
    # 位置が画像幅を超えたら0に戻す
    x = count % IMAGE_WIDTH
    y = 0
    # 既存の画像を黒で塗りつぶし
    buffer_img.paste((0, 0, 0), (0, 0, buffer_img.width, buffer_img.height))
    
    # 1枚目の画像を配置
    buffer_img.paste(img_file, (-x, y))
    # 2枚目の画像を右側に配置
    buffer_img.paste(img_file, (IMAGE_WIDTH - x, y))
    
    framebuffer.write_image(buffer_img)
    count += 1
    time.sleep(0.001)  # より高速なアニメーション

