import mmap

class Framebuffer:
    """フレームバッファクラス"""
    
    def __init__(self, width=480, height=320):
        self.width = width
        self.height = height
        self.fb_file = None
        self.fb = None
    
    def open(self):
        """フレームバッファを開く"""
        self.fb_file = open('/dev/fb0', 'r+b')
        self.fb = mmap.mmap(self.fb_file.fileno(), self.width * self.height * 4)

    def close(self):
        if self.fb:
            self.fb.close()
            self.fb = None
        if self.fb_file:
            self.fb_file.close()
            self.fb_file = None

    def write_image(self, img):
        """PIL画像をフレームバッファに書き込み"""
        # RGBAモードに変換
        rgba_img = img.convert('RGBA')
        rgba_data = rgba_img.tobytes()
        
        # RGBAからBGRAに変換（R <-> B を交換）
        bgra_data = bytearray(rgba_data)
        for i in range(0, len(bgra_data), 4):
            bgra_data[i], bgra_data[i + 2] = bgra_data[i + 2], bgra_data[i]
        
        # フレームバッファに書き込み
        self.fb[:] = bgra_data
