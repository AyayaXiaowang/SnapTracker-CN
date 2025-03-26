import os
import pyautogui
import win32gui
import win32api
import cv2
import numpy as np



class ImageMatcher:
    def __init__(self):
        print("\n=== 初始化图像匹配器 ===")
        self.reference_images = {}
        self.reference_width = 1920
        self.reference_height = 1080
        
        # 修改基准路径的获取方式
        base_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "screen_match")
        print(f"参考图片目录: {base_path}")
        
        if not os.path.exists(base_path):
            os.makedirs(base_path)
            print(f"创建screen_match目录: {base_path}")
            
        reference_paths = {
            "回合开始": os.path.join(base_path, "回合开始.png"),
        }

        # 打印更详细的路径信息
        print(f"当前文件路径: {os.path.abspath(__file__)}")
        print(f"项目根目录: {os.path.dirname(os.path.dirname(os.path.abspath(__file__)))}")
        
        for name, path in reference_paths.items():
            try:
                print(f"尝试加载图片: {path}")
                if os.path.exists(path):
                    img = cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_COLOR)
                    if img is not None:
                        self.reference_images[name] = img
                        print(f"✓ 成功加载图片: {name} (尺寸: {img.shape})")
                    else:
                        print(f"✗ 图片加载失败: {name} (格式可能不支持)")
                else:
                    print(f"✗ 图片不存在: {path}")
            except Exception as e:
                print(f"✗ 加载图片出错 {name}: {str(e)}")
        
        print(f"成功加载 {len(self.reference_images)} 张参考图片")
        print("=== 图像匹配器初始化完成 ===\n")

    def resize_to_1080p(self, image, window_rect):
        try:
            current_height = window_rect[3] - window_rect[1]
            scale_ratio = self.reference_height / current_height
            
            if image is None:
                print("错误: 输入图像为空")
                return None
            
            # 获取所有模板图片中最大的尺寸
            max_template_height = 0
            max_template_width = 0
            for ref_image in self.reference_images.values():
                max_template_height = max(max_template_height, ref_image.shape[0])
                max_template_width = max(max_template_width, ref_image.shape[1])
            
            # 计算新尺寸
            new_width = int(image.shape[1] * scale_ratio)
            new_height = int(image.shape[0] * scale_ratio)
            
            # 确保新尺寸不小于模板尺寸
            new_width = max(new_width, max_template_width + 1)
            new_height = max(new_height, max_template_height + 1)
            
            print(f"调整图像尺寸: {image.shape} -> ({new_width}, {new_height})")
            print(f"最大模板尺寸: {max_template_width}x{max_template_height}")
            
            return cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_LANCZOS4)
            
        except Exception as e:
            print(f"调整图像尺寸时出错: {str(e)}")
            return None

    def compare_images(self, screenshot, window_rect):
        try:
            print("开始图像比对...")
            
            # 转换格式
            screenshot_cv = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
            print("转换格式完成")
            
            # 使用resize_to_1080p函数进行缩放
            screenshot_resized = self.resize_to_1080p(screenshot_cv, window_rect)
            if screenshot_resized is None:
                print("调整尺寸失败")
                return None, None
                
            best_match = None
            highest_val = -1
            
            for name, ref_image in self.reference_images.items():
                try:
                    print(f"正在比对 {name}...")
                    print(f"模板尺寸: {ref_image.shape}")
                    print(f"调整后的截图尺寸: {screenshot_resized.shape}")
                    
                    result = cv2.matchTemplate(screenshot_resized, ref_image, cv2.TM_CCOEFF_NORMED)
                    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
                    print(f"图片 {name} 的匹配度: {max_val:.2f}")
                    
                    if max_val > highest_val:
                        highest_val = max_val
                        best_match = name
                except Exception as e:
                    print(f"比对 {name} 时出错: {str(e)}")
                    continue
            
            print(f"比对完成. 最佳匹配: {best_match}, 匹配度: {highest_val:.2f}")
            return (best_match, highest_val) if highest_val > 0.8 else (None, highest_val)
            
        except Exception as e:
            print(f"比对图片时发生错误: {str(e)}")
            return None, None

# 静态工具函数
def get_window_rect(hwnd):
    """
    获取窗口的实际客户区域，排除标题栏等装饰物的影响
    """
    try:
        if not hwnd:
            return None
            
        # 获取窗口完整区域
        window_rect = win32gui.GetWindowRect(hwnd)
        
        # 获取客户区域
        client_rect = win32gui.GetClientRect(hwnd)
        
        # 将客户区域坐标转换为屏幕坐标
        point = win32gui.ClientToScreen(hwnd, (0, 0))
        
        # 计算装饰物（标题栏等）的高度
        decoration_height = point[1] - window_rect[1]
        
        # 返回实际的客户区域坐标
        return (
            point[0],                    # 左
            point[1],                    # 上
            point[0] + client_rect[2],   # 右
            point[1] + client_rect[3]    # 下
        )
        
    except Exception as e:
        print(f"获取窗口区域时出错: {str(e)}")
        return None

def is_window_focused(hwnd):
    return hwnd == win32gui.GetForegroundWindow()

def is_mouse_pressed():
    return win32api.GetKeyState(0x01) < 0 or win32api.GetKeyState(0x02) < 0

def calculate_crop_area(window_rect):
    current_width = window_rect[2] - window_rect[0]
    current_height = window_rect[3] - window_rect[1]
    
    # 始终使用高度计算缩放比例，因为游戏窗口化时高度保持不变
    scale = current_height / 1440  # 1440是参考高度
    
    # 使用同一个缩放比例，保持区域比例不变
    center_x = window_rect[0] + current_width / 2
    center_y = window_rect[1] + current_height / 2
    
    # 计算目标区域的宽度和高度
    target_width = int(914 * scale)  # 1770 - 856 = 914
    target_height = int(300 * scale)  # 666 - 395 = 271
    
    # 计算向上偏移的像素数（将50像素也按比例缩放）
    offset_y = int(200 * scale)
    
    # 从中心点计算四个角的坐标，y坐标上移offset_y像素
    x1 = int(center_x - target_width / 2)
    y1 = int(center_y - target_height / 2 - offset_y)  # 上移offset_y像素
    x2 = int(center_x + target_width / 2)
    y2 = int(center_y + target_height / 2 - offset_y)  # 上移offset_y像素
    
    return (x1, y1, x2, y2)
# 全局matcher实例
_matcher = None

def check_screen_match():
    global _matcher  # 添加这行，声明使用全局变量
    try:
        if _matcher is None:
            _matcher = ImageMatcher()
        
        hwnd = win32gui.FindWindow(None, "SnapCN")
        if not hwnd:
            return False
            
        if not is_window_focused(hwnd) or is_mouse_pressed():
            return False
            
        window_rect = get_window_rect(hwnd)
        if not window_rect:
            return False
            
        screenshot = pyautogui.screenshot()
        crop_area = calculate_crop_area(window_rect)
        cropped_image = screenshot.crop(crop_area)
        
        # 使用 compare_images 方法进行匹配
        match_result, match_value = _matcher.compare_images(cropped_image, window_rect)
        return bool(match_result)
        
    except Exception as e:
        print(f"检查屏幕匹配时发生错误: {str(e)}")
        return False