# SVG Monitor 2.0
#
# 2025/06/11 First Version For 3.5 LCD
#
import os
import sys
from datetime import datetime, timezone, timedelta
import time
import logging

from pymongo import MongoClient
from PIL import Image,ImageDraw,ImageFont
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BASE_DIR, 'lib'))
from fb import Framebuffer
from nvsend import ImageSender
from drawgraph import DrawGraph

# .env 読み込み
load_dotenv()

# ログ設定
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
numeric_level = getattr(logging, log_level, logging.INFO)

logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
logger.setLevel(numeric_level) 

# 定数
DISP_WIDTH = int(os.getenv('DISP_WIDTH'))
DISP_HEIGHT = int(os.getenv('DISP_HEIGHT'))
TARGET_FPS = 5  # 目標FPS
FRAME_TIME = 1.0 / TARGET_FPS  # 1フレームの目標時間（秒）
#DRAW_INT = int(os.getenv('REFRESH_INTERVAL')) # n秒に1回画面書き換え
NETVIEW_HOST = os.getenv('NETVIEW_HOST')
MAX_RECORDS = 50  # 保持する最大レコード数

logger.info("Start SGV Monitor")

# フォントの読み込み
logger.info("Reading Fonts")
FONT_DIR = os.path.abspath(os.path.join(BASE_DIR, '../fonts'))
FONT_SGV = ImageFont.truetype(os.path.join(FONT_DIR, os.getenv('FONT_PATH_SGV')), 200)
FONT_SGV_S = ImageFont.truetype(os.path.join(FONT_DIR, os.getenv('FONT_PATH_SGV')), 72)
FONT_SYS = ImageFont.truetype(os.path.join(FONT_DIR, os.getenv('FONT_PATH_SYS')), 24)

class GetSGV:
    def __init__(self):
        # MongoDB 接続
        logger.info(f'Connecting MongoDB...')
        logger.info(f'host: {os.getenv("MONGO_URI")}:{os.getenv("MONGO_PORT")}')
        self.mongo_client = MongoClient(os.getenv('MONGO_URI'), int(os.getenv('MONGO_PORT'))\
                , username=os.getenv('MONGO_USER'), password=os.getenv('MONGO_PASS'))
        logger.info(f'OK')

    # 戻値: [データ日時(UnixTime), SGV値]
    def last_sgv_doc(self):
        try:
            col = self.mongo_client.test.entries
            doc = col.find_one(sort=[('date', -1)])  # 最新1件のみ取得
        except:
            return None
        return [doc['date'], doc['sgv']] if doc else None

    # 戻値: [[データ日時(UnixTime), SGV値], ...]
    def init_sgv_docs(self, limit=50):
        logger.info(f"init_sgv_docs called")
        col = self.mongo_client.test.entries
        find = col.find().sort('date', -1).limit(limit)
        ret = [[doc['date'], doc['sgv']] for doc in find]
        logger.info(f"init_sgv_docs end")
        return ret
    
    def close(self):
        self.mongo_client.close()

class DataStore:
    def __init__(self, max_records=50):
        self.max_records = max_records
        self.records = []  # [[timestamp, sgv], ...]
    
    def init_records(self, records):
        """初期データのロード"""
        if not records:
            return
        self.records = records[:self.max_records]
    
    def add_record(self, record):
        """新しいレコードを追加し、古いものを削除"""
        if not record:
            return False
        
        # 重複チェック
        if self.records and record[0] <= self.records[0][0]:
            return False
            
        # 先頭に追加
        self.records.insert(0, record)
        
        # 最大件数を超えた分を削除
        if len(self.records) > self.max_records:
            self.records = self.records[:self.max_records]
            
        return True
    
    def get_records(self):
        """保存されているレコードを返す"""
        return self.records

# コンテンツの描画
class DrawContents:
    def __init__(self, image, framebuffer, sender):
        self.image = image
        self.width = image.width
        self.height = image.height
        self.draw = ImageDraw.Draw(self.image)
        self.framebuffer = framebuffer
        self.sender = sender
        self.sgv_color = (255, 255, 255)
        self.draw_graph = DrawGraph(self.width, 140, (0, 0, 0))
        self.draw_time = None

    def display(self):
        self.framebuffer.write_image(self.image)
        self.sender.send_image(self.image)

    def clear(self, color=(0, 0, 0)):
        # 表示エリアのクリア
        self.draw.rectangle((0, 0, self.image.width, self.image.height), fill=color)

    def draw_msg_center(self, msg, font, color, bg_color):
        self.clear(bg_color)
        # テキストのバウンディングボックスを取得（0,0を基準に）
        bbox = self.draw.textbbox((0, 0), msg, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        ascent = bbox[1]  # 上部の余白

        # 中央位置を計算（ベースラインの調整を含む）
        x = (self.image.width - text_width) / 2 - bbox[0]  # 左の余白を考慮
        y = (self.image.height - text_height) / 2 - ascent  # 上部の余白を考慮

        self.draw.text((x, y), msg, fill=color, font=font)
        self.display()

    def draw_sgv(self, sgv, old_sgv):
        # SGVの描画
        sgv_color = (255, 255, 255)
        if sgv >= 200:
            sgv_color = (255, 0, 0)

        ##self.image.paste((0, 0, 0), (0, 0, self.width, self.height))
        sgv_str = f'{sgv:3d}'
        bbox = self.draw.textbbox((0, 0), sgv_str, font=FONT_SGV)
        text_width = bbox[2] - bbox[0]
        self.draw.text((20, 20), sgv_str, fill=sgv_color, font=FONT_SGV)

        # 差分色の決定
        if old_sgv == -1: #アプリ起動初回は白にする
            old_sgv = sgv

        if sgv > old_sgv:
            sgv_diff_color = (255, 128, 128)  # 赤
        elif sgv < old_sgv:
            sgv_diff_color = (128, 128, 255)  # 青
        else:
            sgv_diff_color = (255, 255, 255)  # 白

        self.sgv_diff_color = sgv_diff_color  # 色を保存
        
        # 差分の計算と表示
        if old_sgv != -1 and sgv != old_sgv:  # 初回以外かつ値が変化している場合のみ
            diff = sgv - old_sgv
            diff_str = f"{'+' if diff > 0 else ''}{diff}"
            
            # 差分値の描画（SGV値の右側）
            x = 20 + text_width + 10  # SGV値の右端から10ピクセル空けて
            y = 20 + 70
            self.draw.text((x, y), diff_str, fill=sgv_diff_color, font=FONT_SGV_S)

    def draw_datetime(self):
        # 日時の描画
        self.draw.rectangle((0, self.height-30, self.width, self.height), fill=(0, 0, 200))
        current_time = datetime.now()
        weekday = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][current_time.weekday()]
        date_str = current_time.strftime(f'%Y-%m-%d {weekday} %H:%M:%S')
        self.draw.text((10, self.height-25), date_str, fill=(200, 200, 200), font=FONT_SYS)

    def draw_pass_time(self, seconds_pass):
        # 表示用文字列の作成
        if seconds_pass >= 3600:
            str_pass_time = f'{seconds_pass//3600}h {seconds_pass%3600//60}m {seconds_pass%60}s'
        elif seconds_pass >= 60:
            str_pass_time = f'{seconds_pass//60}m {seconds_pass%60}s'
        else:
            str_pass_time = f'{seconds_pass}s'

        # 経過時間の描画（右詰め）
        bbox = self.draw.textbbox((0, 0), str_pass_time, font=FONT_SYS)
        x = self.width - bbox[2] + bbox[0] - 10
        self.draw.text((x, self.height-25), str_pass_time, fill=(200, 200, 200), font=FONT_SYS)

    def update(self, sgv, old_sgv, data, seconds_pass):
        if seconds_pass > 10*60:  # 10分以上経過
            # データが古い場合はエラー表示
            self.draw_msg_center(
                f"Data Error\n{seconds_pass//60} minutes passed", 
                FONT_SGV_S, 
                (255, 255, 255),  # 白文字
                (128, 0, 0)       # 暗い赤背景
            )
            return

        # 時刻が変化しないときは再描画しない
        current_time = datetime.now().replace(microsecond=0)
        if current_time == self.draw_time:
            logger.debug(f"Skip Drawing: {current_time} == {self.draw_time}")
            return
        logger.debug(f"Drawing: {current_time} != {self.draw_time}")
        self.draw_time = current_time

        # 描画
        self.clear()
        self.draw_sgv(sgv, old_sgv)
        self.draw_datetime()
        self.draw_pass_time(seconds_pass)

        # グラフの描画
        img_graph = self.draw_graph.create_graph(data)
        self.image.paste(img_graph, (0, 150))

        self.display()


# メイン処理クラス
class SGVMonitor:
    def __init__(self):
        self.image = Image.new('RGB', (DISP_WIDTH, DISP_HEIGHT), (0, 0, 0))
        self.sgv = -1
        self.old_sgv = -1
        self.last_data_read = 0
        self.last_record_time = 0
        self.get_sgv = GetSGV()
        self.data_store = DataStore(MAX_RECORDS)
        
        self.framebuffer = Framebuffer()
        self.framebuffer.open()
        self.sender = ImageSender(NETVIEW_HOST)
        self.draw_contents = DrawContents(self.image, self.framebuffer, self.sender)
        self.draw_contents.draw_msg_center("Hello", FONT_SGV, (255, 255, 255), (0, 0, 200))

        self._load_initial_data()

    def _load_initial_data(self):
        """初期データの読み込み"""
        init_records = self.get_sgv.init_sgv_docs(MAX_RECORDS)
        self.data_store.init_records(init_records)
        if init_records:  # 初期データがある場合
            self.sgv = init_records[0][1]  # 最新のSGVを設定
            self.last_record_time = init_records[0][0]
        logger.info(f"Initial data loaded: {self.sgv}")

    def _pass_time(self, record_time):
        date_ut = int(record_time/1000)
        spec_date = datetime.fromtimestamp(date_ut)
        current_date = datetime.now().replace(microsecond=0)
        diff_date = current_date - spec_date

        return int(diff_date.total_seconds())

    def update_data(self):
        """データの更新（1秒に1回）"""
        current_time = time.time()
        if current_time - self.last_data_read < 1.0:  # 1秒経過していない
            return

        record = self.get_sgv.last_sgv_doc()
        if not record:
            return

        # データストアに追加（重複チェックも行われる）
        result = self.data_store.add_record(record)
        if not result:
            return

        self.last_data_read = current_time
        record_time = record[0]
        
        # sgv取得            
        read_sgv = record[1]
        logger.debug(f"read_sgv: {read_sgv}")
        self.old_sgv = self.sgv
        # SGV値が変化した場合にログ出力
        if self.sgv != read_sgv:
            logger.info(f"SGV changed: {self.sgv} -> {read_sgv}")
        self.sgv = read_sgv
        self.last_record_time = record_time


    def update(self):
        """フレームの更新"""
        self.update_data()  # データの更新と鮮度チェック
        if not self.data_store.get_records():  # データがない場合はスキップ
            return

        seconds_pass = self._pass_time(self.last_record_time)
        self.draw_contents.update(
            self.sgv, 
            self.old_sgv, 
            self.data_store.get_records(),  # 保存されている全レコードを渡す
            seconds_pass
        )

    def term_proc(self):
        # 画面クリア
        self.draw_contents.clear()
        self.draw_contents.draw_msg_center("Terminate", FONT_SGV_S, (255, 255, 255), (0, 0, 0))
        self.framebuffer.write_image(self.image)
        self.get_sgv.close()

def main():
    """メイン関数"""
    sgv_monitor = SGVMonitor()
    frame_count = 0
    fps_update_time = time.time()
    logger.info("Start Main Loop") 
    try:
        while True:
            loop_start = time.time()
            
            # メイン処理
            sgv_monitor.update()
            
            # FPS計算（1秒ごとに更新）
            frame_count += 1
            current_time = time.time()
            if current_time - fps_update_time >= 1.0:
                fps = frame_count
                frame_count = 0
                fps_update_time = current_time
                logger.debug(f"FPS: {fps}")
            
            # 次のフレームまでスリープ
            process_time = (time.time() - loop_start) * 1000  # 秒からミリ秒に変換
            logger.debug(f"Process time: {process_time:.2f}ms")
            sleep_time = max(0, FRAME_TIME - (process_time/1000))  # ミリ秒から秒に戻して計算
            time.sleep(sleep_time)

    except:
        logger.info('--stop--')
        sgv_monitor.term_proc()

if __name__ == "__main__":
    main()
