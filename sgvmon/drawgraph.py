from PIL import Image,ImageDraw,ImageFont

class DrawGraph:
    def __init__(self, width, height, bg_color):
        self.image = Image.new('RGB', (width, height), bg_color)
        self.width = width
        self.height = height
        self.draw = ImageDraw.Draw(self.image)
        self.bg_color = bg_color
        self.box_color = (255,255,255)

    def draw_horizontal_dashed_line(self, draw, y, x_start, x_end, dash_length=10, gap_length=5, fill=(255,255,255), width=2):
        """
        水平線専用の破線を描画する関数
        :param draw: ImageDrawオブジェクト
        :param y: 水平線のY座標
        :param x_start: 線の開始X座標
        :param x_end: 線の終了X座標
        :param dash_length: 破線の線部分の長さ
        :param gap_length: 破線の空白部分の長さ
        :param fill: 線の色
        :param width: 線の太さ
        """
        current_x = x_start
        while current_x < x_end:
            # 線部分を描画
            segment_end = min(current_x + dash_length, x_end)  # 線の終端を超えないようにする
            draw.line([(current_x, y), (segment_end, y)], fill=fill, width=width)
            
            # 空白部分をスキップ
            current_x += dash_length + gap_length

    def create_graph(self, data):
        """
        データポイントからグラフを生成する
        
        Args:
            data: (unix_timestamp, value)のタプルのリスト
            width: グラフの幅（ピクセル）
            height: グラフの高さ（ピクセル）
            
        Returns:
            PIL Image オブジェクト
        """
        # グラフの背景をクリア
        self.draw.rectangle([0, 0, self.width-1, self.height-1], fill=self.bg_color)

        # 外側の枠線を描画
        #self.draw.rectangle([0, 0, self.width-1, self.height-1], outline=self.box_color)
        
        # データから値を取得
        timestamps = [point[0] for point in data]  # Unix時間（秒）を直接使用
        values = [point[1] for point in data]
        
        # 時間の範囲を計算
        time_min = min(timestamps)
        time_max = max(timestamps)
        time_range = time_max - time_min if time_max != time_min else 1
        
        # 値の範囲を計算（最低範囲を100とする）
        base_min = min(values)
        base_max = max(values)
        value_range = max(base_max - base_min, self.height)  # 最低範囲を100に設定
        
        if base_min - (value_range - (base_max - base_min)) / 2 < 0:
            # 最小値が0未満になる場合は、0を最小値として最大値を調整
            min_value = 0
            max_value = max(value_range, base_max)
        else:
            # 通常の中央値を基準とした計算
            center = (base_max + base_min) / 2
            min_value = center - (value_range / 2)
            max_value = center + (value_range / 2)

        # 100と200の補助線を引く
        line_dash = [2, 5, 2]
        for idx, value in enumerate([100, 150, 200]):
            if min_value <= value <= max_value:
                y = self.height - 1 - ((value - min_value) / value_range * (self.height - 2) + 1)
                self.draw_horizontal_dashed_line(self.draw, y, 1, self.width-2, line_dash[idx], line_dash[idx], (0,0,200), 2)
        
        # データポイントをプロット
        points = []
        for timestamp, value in data:
            x = ((timestamp - time_min) / time_range * (self.width - 2)) + 1
            y = self.height - 1 - ((value - min_value) / value_range * (self.height - 2) + 1)
            points.append((x, y))
        
        # ポイントを線で接続
        if len(points) > 1:
            self.draw.line(points, fill='green', width=5)
        
        return self.image

