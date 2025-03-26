
from PyQt6.QtWidgets import (QFrame, QVBoxLayout, QLabel, QWidget, QMenu,
                            QSizePolicy,QGraphicsColorizeEffect,QGraphicsOpacityEffect)
from PyQt6.QtCore import Qt, QObject, pyqtSignal
from PyQt6.QtGui import QPixmap
import os
import sys
def get_resource_path(relative_path):
    """获取资源文件的绝对路径"""
    try:
        # 统一使用正斜杠
        relative_path = relative_path.replace('\\', '/')
        
        if hasattr(sys, '_MEIPASS'):
            # PyInstaller 打包后的路径
            base_path = sys._MEIPASS
            full_path = os.path.join(base_path, relative_path)
            print(f"打包环境资源路径: {full_path}")  # 调试输出
        else:
            # 开发环境路径
            base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            full_path = os.path.join(base_path, relative_path)
            print(f"开发环境资源路径: {full_path}")  # 调试输出
            
        return full_path
        
    except Exception as e:
        print(f"获取资源路径失败: {relative_path} - {str(e)}")
        return relative_path
    
class SignalManager(QObject):
    remove_enemy_card = pyqtSignal(str)
    reset_excluded_cards = pyqtSignal()  # 添加新的信号
    
# 创建全局实例
signal_manager = SignalManager()



class CardWidget(QFrame):
    def __init__(self, card):
        super().__init__()
        self.setMinimumSize(80, 100)
        
        self.setObjectName("card-frame")
        self.layout = QVBoxLayout(self)
        # 设置外层边距为0
        self.layout.setContentsMargins(0, 0, 0, 0)
        # 设置组件间距为0
        self.layout.setSpacing(0)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 创建固定比例的容器
        self.image_container = QWidget()
        self.image_container.setObjectName("image-container")
        
        size_policy = QSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding
        )
        size_policy.setHeightForWidth(True)
        self.image_container.setSizePolicy(size_policy)
        
        # 图片标签
        self.image_label = QLabel(self.image_container)
        self.image_label.setObjectName("image-label")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setScaledContents(False)
        
        # 容器布局保持0边距
        container_layout = QVBoxLayout(self.image_container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)
        container_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        container_layout.addWidget(self.image_label)
        
        self.layout.addWidget(self.image_container)
        
        self.card_info = None
        self.pixmap_cache = None
        self.unknown_pixmap_cache = None
        self.last_size = None
        
        # 设置容器的高宽比
        self.image_container.heightForWidth = lambda w: w
        self.image_container.hasHeightForWidth = lambda: True

        # 添加右键菜单支持
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)


        self.update_card(card)

    def show_context_menu(self, position):
        menu = QMenu(self)
        
        # 检查是否是未知卡牌
        if hasattr(self, 'card_info') and self.card_info:
            if self.card_info.get('name') == '未知卡牌':
                # 为未知卡牌添加重置排除列表选项
                reset_action = menu.addAction("重置排除列表")
                action = menu.exec(self.mapToGlobal(position))
                
                if action == reset_action:
                    # 使用全局信号管理器发射新的信号
                    signal_manager.reset_excluded_cards.emit()
            else:
                # 原有的排除卡牌选项
                remove_action = menu.addAction("这不是对手的卡")
                action = menu.exec(self.mapToGlobal(position))
                
                if action == remove_action:
                    signal_manager.remove_enemy_card.emit(self.card_info['name'])


    def resizeEvent(self, event):
        """处理卡片大小变化"""
        super().resizeEvent(event)
        
        # 更新显示
        self.update_card_display()
            

    def calculate_font_size(self, width):
        """计算基于卡片宽度的字体大小"""
        # 基于卡片宽度计算字体大小
        calculated_size = int(width * self.name_font_ratio)
        
        # 确保字体大小在合理范围内
        font_size = max(self.min_font_size, min(self.max_font_size, calculated_size))
        
        return font_size

    def calculate_max_chars(self, width):
        """根据卡片宽度计算最大可显示字符数"""
        # 调整字符数计算逻辑
        if width < 60:  # 非常小的卡片
            return 3
        elif width < 80:  # 小卡片
            return 4
        elif width < 100:  # 中等卡片
            return 5
        elif width < 120:  # 较大卡片
            return 6
        return 7  # 最大卡片

    def format_card_name(self, name, max_chars):
        """格式化卡牌名称"""
        if len(name) > max_chars:
            # 对于较小的卡片，可以考虑进一步缩短名称
            if self.width() < 80:  # 对于非常小的卡片
                return name[-3:] + '..'  # 只显示最后三个字符加省略号
            return name[-max_chars:]
        return name

    def update_card_display(self):
        if self.card_info is None:
            return
            
        container_size = self.image_container.size()
        
        if self.card_info['name'] == '未知卡牌':
            if self.unknown_pixmap_cache is None:
                unknown_image = get_resource_path('卡面/未知.png')
                self.unknown_pixmap_cache = QPixmap(unknown_image)
            pixmap = self.unknown_pixmap_cache
        else:
            if self.pixmap_cache is None and self.card_info.get('image'):
                image_path = get_resource_path(self.card_info['image'])
                try:
                    if os.path.exists(image_path):
                        self.pixmap_cache = QPixmap(image_path)
                    else:
                        self.pixmap_cache = QPixmap()  # 创建空的 QPixmap
                except:
                    self.pixmap_cache = QPixmap()  # 创建空的 QPixmap
            pixmap = self.pixmap_cache
        
        if pixmap and not pixmap.isNull():
            # 显示图片
            scaled_pixmap = pixmap.scaled(
                container_size.width(),
                container_size.height(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            
            x = (container_size.width() - scaled_pixmap.width()) // 2
            y = (container_size.height() - scaled_pixmap.height()) // 2
            self.image_label.setGeometry(x, y, scaled_pixmap.width(), scaled_pixmap.height())
            self.image_label.setPixmap(scaled_pixmap)
        else:
            # 没有图片时显示卡牌名字
            self.image_label.setPixmap(QPixmap())  # 使用空的 QPixmap 而不是 None
            self.image_label.setGeometry(0, 0, container_size.width(), container_size.height())
            
            # 根据容器宽度调整字体大小
            font_size = max(8, min(16, container_size.width() // 6))
            self.image_label.setStyleSheet(f"""
                QLabel {{
                    font-size: {font_size}px;
                    color: white;
                    background-color: rgba(0, 0, 0, 0.7);
                    padding: 4px;
                    border-radius: 4px;
                }}
            """)
            
            # 设置自动换行
            self.image_label.setWordWrap(True)
            self.image_label.setText(self.card_info['name'])
        
        # 设置亮度效果
        if not self.card_info.get('played', False):
            if not self.image_label.graphicsEffect():
                effect = QGraphicsOpacityEffect()
                effect.setOpacity(0.5)
                self.image_label.setGraphicsEffect(effect)
        else:
            self.image_label.setGraphicsEffect(None)

    def update_card(self, card):
        try:
            # 只有在卡牌真正改变时才清除缓存
            if self.card_info is None or self.card_info.get('name') != card.get('name'):
                self.pixmap_cache = None
                print(f"更新卡牌: {card.get('name')}")
            
            self.card_info = card
            self.last_size = None
            self.update_card_display()
            
            if not card.get('known', True):
                self.setProperty("class", "card-frame unknown-card-frame")
            else:
                self.setProperty("class", "card-frame")
                
            self.style().unpolish(self)
            self.style().polish(self)
            self.update()
            
        except Exception as e:
            print(f"更新卡牌失败: {e}")
            import traceback
            traceback.print_exc()
