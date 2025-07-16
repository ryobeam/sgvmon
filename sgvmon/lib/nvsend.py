import logging
import io
import socket
import struct
from PIL import Image

logger = logging.getLogger(__name__)

class ImageSender:
    def __init__(self, host='localhost', port=49011):
        self.host = host
        self.port = port
        logger.debug("Initializing NetView")
        logger.debug(f"host={host}:{port}")

    def send_image_from_file(self, image_path):
        """画像ファイルを読み込んでサーバーに送信"""
        if not self.host:
            return
        try:
            with Image.open(image_path) as img:
                self.send_image(img)
        except FileNotFoundError:
            logger.error(f"エラー: 画像ファイル '{image_path}' が見つかりません")

    def send_image(self, img):
        """画像イメージ(PIL)をサーバーに送信"""
        if not self.host:
            return
        sock = None
        try:
            # Imageオブジェクトをバイナリデータに変換
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format='PNG')
            img_byte_arr = img_byte_arr.getvalue()

            # サーバーに接続
            try:
                logger.debug(f"Connecting Server {self.host}:{self.port} ...")
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect((self.host, self.port))
            except ConnectionRefusedError:
                logger.error(f"接続が拒否されました: {self.host}:{self.port}")
                return
            except socket.gaierror:
                logger.error(f"ホスト名の解決に失敗しました: {self.host}")
                return
            except Exception as e:
                logger.error(f"接続エラー: {str(e)}")
                return

            # データサイズを送信（4バイトのネットワークバイトオーダー）
            size = len(img_byte_arr)
            logger.debug(f"Image Size: {size} bytes")
            sock.send(struct.pack('!I', size))

            # 画像データを送信
            sent_size = 0
            while sent_size < size:
                chunk_size = min(4096, size - sent_size)
                chunk = img_byte_arr[sent_size:sent_size + chunk_size]
                sent = sock.send(chunk)
                sent_size += sent

                # 進捗表示
                progress = (sent_size / size) * 100

            logger.debug("Transmission completed")

        except Exception as e:
            logger.error(f"送信エラー: {str(e)}")
        finally:
            if sock is not None:
                try:
                    sock.close()
                except Exception as e:
                    logger.error(f"ソケットクローズエラー: {str(e)}")

class ImageReceiver:
    def __init__(self, host='0.0.0.0', port=49011):
        self.host = host
        self.port = port

    def receive_image_data(self):
        """サーバとして接続を待ち、画像データ（バイト列）を受信して返す"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_sock:
            server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_sock.bind((self.host, self.port))
            server_sock.listen(1)
            print(f"Listening on {self.host}:{self.port} ...")
            conn, addr = server_sock.accept()
            with conn:
                print(f"Connected by {addr}")

                # 先頭4バイトでデータサイズを受信
                size_data = conn.recv(4)
                if len(size_data) < 4:
                    raise RuntimeError("データサイズの受信に失敗しました")
                size = struct.unpack('!I', size_data)[0]
                print(f"受信データサイズ: {size} bytes")

                # データ本体を受信
                received = b''
                while len(received) < size:
                    chunk = conn.recv(min(4096, size - len(received)))
                    if not chunk:
                        raise RuntimeError("データ受信中に接続が切れました")
                    received += chunk

                print("画像データ受信完了")
                return received

    def save_png(self, data: bytes, filename: str):
        """受信したPNGバイト列をファイルに保存"""
        with open(filename, 'wb') as f:
            f.write(data)
        print(f"PNGファイルとして保存しました: {filename}")

# 画像送信
# sender = ImageSender(host, port)
# sender.send_image(img)
