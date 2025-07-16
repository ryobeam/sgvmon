import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import threading
import time
from PIL import Image
from sgvmon.lib.nvsend import ImageSender, ImageReceiver

HOST = '127.0.0.1'
PORT = 49011

# テスト用画像生成関数
def create_test_image():
    img = Image.new('RGB', (100, 100), (255, 255, 0))
    return img

def sender_thread():
    sender = ImageSender(host=HOST, port=PORT)
    img = create_test_image()
    time.sleep(1)  # サーバ起動待ち
    sender.send_image(img)
    print('送信完了')

def receiver_thread():
    receiver = ImageReceiver(host=HOST, port=PORT)
    data = receiver.receive_image_data()
    receiver.save_png(data, 'received_test.png')
    print('受信・保存完了')

if __name__ == '__main__':
    # 受信側スレッド
    t_recv = threading.Thread(target=receiver_thread)
    t_recv.start()
    # 送信側スレッド
    t_send = threading.Thread(target=sender_thread)
    t_send.start()
    t_recv.join()
    t_send.join()
    print('テスト終了') 
