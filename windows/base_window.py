from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QGridLayout, QFrame,QApplication,QGraphicsColorizeEffect
)
from PyQt6.QtCore import (
    Qt, QPoint, QTimer, QEvent, QSize,QSettings
)
from PyQt6.QtGui import QCursor
from widgets.card_widget import CardWidget
import os

class BaseWindow(QMainWindow):
    """基础窗口类，提供无边框、任意位置拖动、始终置顶、锁定位置等功能"""
    def __init__(self, title, enable_context_menu=True):  # 添加参数
        super().__init__()
        self.setWindowTitle(title)
        self.load_stylesheet()
        self.enable_context_menu = enable_context_menu    # 保存设置
        
        # 从设置中加载列数，默认为4
        self.settings = QSettings("MyCompany", "MyApp")
        self.current_columns = self.settings.value("current_columns", 4, type=int)
        
        # 计算初始宽高比例
        # 原始比例：4列时，宽=(4*120 + 3*10 + 2*10), 高=(3*160 + 2*10 + 2*10 + 40)
        self.calculate_aspect_ratio(self.current_columns)
        
        # 设置初始大小
        initial_width = 4 * 120 + 3 * 10 + 2 * 10  # 4列卡片 + 3个间距 + 2个边距
        initial_height = 3 * 145 + 2 * 10 + 2 * 10 + 40  # 3行卡片 + 2个间距 + 2个边距 + 顶部按钮
        
        self.setMinimumSize(100, 100)
        self.update_minimum_size()  # 根据当前列数更新最小尺寸
        self.resize(initial_width, initial_height)
            
        # 保存原始尺寸用于缩放计算
        self.original_width = initial_width
        self.original_height = initial_height
        self.image_cache = {}

        # 只使用最基本的窗口标志
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |  # 无边框
            Qt.WindowType.WindowStaysOnTopHint | # 保持在最上层
            Qt.WindowType.Window                 # 普通窗口，而不是工具窗口
        )

        # 移除所有特殊渲染属性
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)

        self.setAttribute(Qt.WidgetAttribute.WA_PaintOnScreen, False)

        # 拖动相关变量
        self.is_dragging = False
        self.drag_position = QPoint()

        # 锁定位置标志
        self.is_locked = False

        # 缩放比例
        self.scale_factor = 1.0

        # 调整大小相关变量
        self.is_resizing = False
        self.resize_direction = None
        # 增大边缘检测区域
        self.resize_margin = 8  # 从5改为8像素
        self.settings = QSettings("MyCompany", "MyApp")
        self.opacity = 1.0  # 默认不透明度

        self.card_widgets = []  # 存储卡牌小部件的列表

        self.lock_text = "解锁"
        self.unlock_text = "锁定"
        self.is_locked = False    # 默认锁定状态

        self.setup_ui()

        self.opacity = self.load_opacity()
        self.setWindowOpacity(self.opacity)
        self.update_opacity_label(self.opacity)  # 确保标签更新

        self.resize_timer = QTimer()
        self.resize_timer.setSingleShot(True)
        self.resize_timer.timeout.connect(self.on_resize_timeout)

        # 确保开启鼠标追踪
        self.setMouseTracking(True)
        self.central_widget.setMouseTracking(True)
        self.deck_widget.setMouseTracking(True)

        # 添加用于控制底部菜单显示的计时器
        self.hide_timer = QTimer(self)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self.hide_bottom_bar)
        
        # 跟踪鼠标是否在底部菜单上
        self.mouse_on_bottom_bar = False

    def calculate_aspect_ratio(self, columns):
        try:
            # 基础卡片尺寸
            card_width = 120
            card_height = 145  # 从160改为140，减小高度
            
            # 最小边距和间距
            min_margin = 1
            min_spacing = 1
            
            # 计算行数
            if columns == 2:
                rows = 6
            elif columns == 3:
                rows = 4
            else:  # 4列
                rows = 3
                
            # 计算总宽度和总高度（使用最小边距）
            total_width = (columns * card_width) + ((columns - 1) * min_spacing) + (2 * min_margin)
            total_height = (rows * card_height) + ((rows - 1) * min_spacing) + (2 * min_margin)
            
            # 设置最小窗口大小
            min_window_width = columns * 40  # 每列最小40像素
            min_window_height = int(min_window_width * (total_height / total_width))
            self.setMinimumSize(min_window_width, min_window_height)
            
            # 计算宽高比
            self.aspect_ratio = total_width / total_height
            
        except Exception as e:
            print(f"计算宽高比失败: {e}")


    def resizeEvent(self, event):
        """处理窗口大小变化事件"""
        try:
            super().resizeEvent(event)
            
            # 获取当前尺寸
            current_width = self.width()
            current_height = self.height()
            
            # 计算理想高度
            ideal_height = int(current_width / self.aspect_ratio)
            
            # 如果当前高度与理想高度的差异超过2像素
            if abs(current_height - ideal_height) > 2:
                # 确保不小于最小尺寸
                new_height = max(ideal_height, self.minimumHeight())
                self.resize(current_width, new_height)
            
            # 更新卡片布局
            self.update_layout()
            self.update_bottom_bar_position()
            
            # 重置定时器
            self.resize_timer.start(500)
            
        except Exception as e:
            print(f"处理窗口大小变化失败: {e}")

    def on_resize_timeout(self):
        """延迟处理窗口设置保存"""
        # 只保存窗口设置，不更新布局
        main_window = QApplication.instance().property("main_window")
        if main_window:
            main_window.save_window_settings()


    def load_opacity(self):
        """加载保存的不透明度设置"""
        key = f"{self.windowTitle()}_opacity"
        return self.settings.value(key, 1.0, type=float)

    def save_opacity(self):
        """保存当前不透明度设置"""
        key = f"{self.windowTitle()}_opacity"
        self.settings.setValue(key, self.opacity)

    def update_opacity_label(self, opacity):
        """更新不透明度标签显示"""
        if hasattr(self, 'opacity_label'):  # 检查标签是否存在
            percentage = int(opacity * 100)
            self.opacity_label.setText(f"{percentage}%")

    def increase_opacity(self):
        """增加不透明度"""
        self.opacity = min(1.0, self.opacity + 0.1)
        self.setWindowOpacity(self.opacity)
        self.update_opacity_label(self.opacity)
        self.save_opacity()

    def decrease_opacity(self):
        """减少不透明度"""
        self.opacity = max(0.1, self.opacity - 0.1)
        self.setWindowOpacity(self.opacity)
        self.update_opacity_label(self.opacity)
        self.save_opacity()

    def setup_ui(self):
        # 创建中央部件
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.central_widget.setObjectName("mainContainer")

        # 主布局
        # 主布局
        main_layout = QVBoxLayout(self.central_widget)
        main_layout.setContentsMargins(1, 1, 1, 1)  # 改为1像素边距
        main_layout.setSpacing(0)  # 确保为0

        # 卡组网格容器 - 包含实际的卡牌网格
        self.deck_widget = QWidget()
        self.deck_widget.setObjectName("deckWidget")
        self.grid = QGridLayout(self.deck_widget)
        self.grid.setSpacing(1)
        self.grid.setContentsMargins(0, 0, 0, 0)
        
        # 设置列宽的伸缩性
        for i in range(4):
            self.grid.setColumnStretch(i, 1)

        # 将卡组网格添加到主布局，设置为可伸缩
        main_layout.addWidget(self.deck_widget, 1)  # 1表示可伸缩

        # 初始化卡片列表
        self.card_widgets = []

        # 在底部布局中添加不透明度控制按钮
        opacity_layout = QHBoxLayout()
        opacity_layout.setSpacing(2)
        
        self.decrease_opacity_btn = QPushButton("-")
        self.decrease_opacity_btn.setObjectName("opacityButton")
        self.decrease_opacity_btn.setFixedSize(26, 26)
        self.decrease_opacity_btn.clicked.connect(self.decrease_opacity)

            # 添加显示不透明度的标签
        self.opacity_label = QLabel("100%")
        self.opacity_label.setObjectName("opacityLabel")
        self.opacity_label.setFixedWidth(40)
        self.opacity_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.increase_opacity_btn = QPushButton("+")
        self.increase_opacity_btn.setObjectName("opacityButton")
        self.increase_opacity_btn.setFixedSize(26, 26)
        self.increase_opacity_btn.clicked.connect(self.increase_opacity)
        
        opacity_layout.addWidget(self.decrease_opacity_btn)
        opacity_layout.addWidget(self.opacity_label)
        opacity_layout.addWidget(self.increase_opacity_btn)

        # 创建底部菜单栏（独立窗口）
        self.bottom_bar = QWidget(None)
        self.bottom_bar.setObjectName("bottomBar")
        self.bottom_bar.setFixedHeight(30)
        self.bottom_bar.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        
        self.bottom_bar.setStyleSheet(self.stylesheet)

        # 底部菜单栏的布局
        bottom_layout = QHBoxLayout(self.bottom_bar)
        bottom_layout.setContentsMargins(4, 2, 4, 2)
        bottom_layout.setSpacing(4)

        # 锁定按钮
        self.lock_button = QPushButton(self.unlock_text)  # 修改初始文本
        self.lock_button.setObjectName("lockButton")
        self.lock_button.setCheckable(True)
        self.lock_button.setChecked(False)  # 修改为默认未选中状态
        self.lock_button.clicked.connect(self.toggle_lock)
        self.lock_button.setFixedHeight(26)
        


        # 关闭按钮
        self.close_button = QPushButton("×")
        self.close_button.setObjectName("closeButton")
        self.close_button.setFixedHeight(26)
        self.close_button.clicked.connect(self.close_windows)
        
        self.decrease_opacity_btn.setObjectName("opacityButton")
        self.increase_opacity_btn.setObjectName("opacityButton")
        self.opacity_label.setObjectName("opacityLabel")


        # 添加布局选择按钮
        self.layout_button = QPushButton(f"{self.current_columns}列")
        self.layout_button.setObjectName("layoutButton")
        self.layout_button.setFixedHeight(26)
        self.layout_button.clicked.connect(self.toggle_layout)

        # 添加按钮到底部布局
        bottom_layout.addWidget(self.lock_button)
        bottom_layout.addWidget(self.layout_button)  # 添加新按钮
        bottom_layout.addLayout(opacity_layout)
        bottom_layout.addStretch()
        bottom_layout.addWidget(self.close_button)

        # 添加底部菜单的鼠标事件
        self.bottom_bar.mousePressEvent = self.bottom_bar_mouse_press_event
        self.bottom_bar.mouseMoveEvent = self.bottom_bar_mouse_move_event
        self.bottom_bar.enterEvent = self.bottom_bar_enter_event
        self.bottom_bar.leaveEvent = self.bottom_bar_leave_event

        self.mouse_track_timer = QTimer(self)
        self.mouse_track_timer.timeout.connect(self.check_mouse_position)
        self.mouse_track_timer.setInterval(100)  # 100ms检查一次


        for widget in [self.central_widget, self.deck_widget]:
            widget.setMouseTracking(True)


    def toggle_layout(self):
        """切换布局列数"""
        if self.current_columns == 4:
            self.current_columns = 2
            self.layout_button.setText("2列")
        elif self.current_columns == 2:
            self.current_columns = 3
            self.layout_button.setText("3列")
        else:
            self.current_columns = 4
            self.layout_button.setText("4列")
        
        # 更新最小尺寸
        self.update_minimum_size()
        
        # 保存当前列数设置
        self.settings.setValue("current_columns", self.current_columns)
        
        self.calculate_aspect_ratio(self.current_columns)
        self.adjust_window_size()
        self.update_layout()


    def update_minimum_size(self):
        """根据列数更新窗口最小尺寸"""
        if self.current_columns == 2:
            # 2列时使用更小的最小尺寸
            min_card_width = 40  # 更小的卡片最小宽度
            min_spacing = 1
            min_margin = 1
            min_width = (self.current_columns * min_card_width) + \
                    ((self.current_columns - 1) * min_spacing) + \
                    (2 * min_margin)
            min_height = int(min_width / self.aspect_ratio)
            self.setMinimumSize(min_width, min_height)
        else:
            # 3列和4列时使用正常的最小尺寸
            min_card_width = 60
            min_spacing = 1
            min_margin = 2
            min_width = (self.current_columns * min_card_width) + \
                    ((self.current_columns - 1) * min_spacing) + \
                    (2 * min_margin)
            min_height = int(min_width / self.aspect_ratio)
            self.setMinimumSize(min_width, min_height)

    def adjust_window_size(self):
        """根据列数调整窗口大小，保持底部菜单位置不变"""
        try:
            # 保存底部菜单的位置
            bottom_bar_pos = self.bottom_bar.pos()
            
            # 获取当前窗口宽度
            current_width = self.width()
            
            # 计算新的高度
            new_height = int(current_width / self.aspect_ratio)
            
            # 计算新的窗口顶部位置，使底部菜单位置保持不变
            new_y = bottom_bar_pos.y() - new_height
            
            # 调整窗口大小和位置
            self.setGeometry(self.x(), new_y, current_width, new_height)
            
            # 更新布局
            self.update_layout()
            self.update_bottom_bar_position()
            
        except Exception as e:
            print(f"调整窗口大小失败: {e}")


    def get_root_dir(self):
        """获取项目根目录路径"""
        current_dir = os.path.dirname(os.path.abspath(__file__))  # windows目录
        return os.path.dirname(current_dir)  # 返回项目根目录
    
    def get_style_path(self):
        """获取样式表路径"""
        root_dir = self.get_root_dir()
        return os.path.join(root_dir, 'ui', 'styles.qss')  # 从ui目录读取样式表

    def load_stylesheet(self):
        """加载样式表"""
        try:
            style_path = self.get_style_path()
            print(f"正在加载样式表: {style_path}")
            
            with open(style_path, 'r', encoding='utf-8') as f:
                self.stylesheet = f.read()
                
            # 应用样式表到主窗口和底部菜单
            self.setStyleSheet(self.stylesheet)
            if hasattr(self, 'bottom_bar'):
                self.bottom_bar.setStyleSheet(self.stylesheet)
                
        except Exception as e:
            print(f"加载样式表失败: {e}")
            self.stylesheet = ""

    def start_mouse_tracking(self):
        """开始监控鼠标位置"""
        self.mouse_track_timer.start()

    def stop_mouse_tracking(self):
        """停止监控鼠标位置"""
        self.mouse_track_timer.stop()

    def check_mouse_position(self):
        """检查鼠标位置并控制底部菜单显示"""
        if not self.isVisible():
            return
            
        cursor_pos = QCursor.pos()
        window_rect = self.geometry()
        bottom_bar_rect = self.bottom_bar.geometry()
        
        # 扩大检测区域（在窗口底部增加一个小区域）
        window_rect.setHeight(window_rect.height() + 10)
        
        in_window = window_rect.contains(cursor_pos)
        in_bottom_bar = bottom_bar_rect.contains(cursor_pos)
        
        if in_window or in_bottom_bar:
            self.show_bottom_bar()
            self.hide_timer.stop()
        else:
            if not self.hide_timer.isActive():
                self.hide_timer.start(500)

    def bottom_bar_enter_event(self, event):
        """鼠标进入底部菜单"""
        self.mouse_on_bottom_bar = True
        self.hide_timer.stop()  # 停止隐藏计时器
        event.accept()

    def bottom_bar_leave_event(self, event):
        """鼠标离开底部菜单"""
        self.mouse_on_bottom_bar = False
        cursor_pos = QCursor.pos()
        main_geo = self.geometry()
        
        # 如果鼠标既不在主窗口也不在底部菜单区域内，启动隐藏计时器
        if not main_geo.contains(cursor_pos) and not self.bottom_bar.geometry().contains(cursor_pos):
            self.hide_timer.start(500)
        event.accept()

    def bottom_bar_mouse_press_event(self, event):
        """处理底部菜单栏的鼠标按下事件"""
        if event.button() == Qt.MouseButton.LeftButton and not self.is_locked:
            self.drag_position = event.globalPosition().toPoint() - self.pos()
            event.accept()

    def bottom_bar_mouse_move_event(self, event):
        """处理底部菜单栏的鼠标移动事件"""
        if event.buttons() & Qt.MouseButton.LeftButton and not self.is_locked:
            new_pos = event.globalPosition().toPoint() - self.drag_position
            self.move(new_pos)
            self.update_bottom_bar_position()
            event.accept()

    def close_windows(self):
        """关闭窗口时清理并保存设置"""
        self.save_opacity()
        self.hide_timer.stop()
        self.mouse_track_timer.stop()
        self.bottom_bar.hide()
        self.hide()



    def show(self):
        """显示主窗口，但不显示底部菜单（等待鼠标移入）"""
        if self.isMinimized():
            self.showNormal()
        else:
            super().show()
        self.activateWindow()
        self.raise_()
        # 初始状态下不显示底部菜单
        self.bottom_bar.hide()

    def hide(self):
        """隐藏主窗口和底部菜单"""
        super().hide()
        self.bottom_bar.hide()

    def resize_window(self, global_pos):
        """调整窗口大小时同时调整卡片大小"""
        try:
            if not self.start_geometry or not self.resize_start_position:
                return
                
            delta = global_pos - self.resize_start_position
            
            # 保存底部菜单位置
            bottom_bar_pos = self.bottom_bar.pos()
            
            # 计算新的宽度
            if 'left' in self.resize_direction:
                proposed_width = self.start_geometry.width() - delta.x()
            elif 'right' in self.resize_direction:
                proposed_width = self.start_geometry.width() + delta.x()
            else:
                proposed_width = self.width()
            
            # 确保最小宽度
            proposed_width = max(self.minimumWidth(), proposed_width)
            
            # 根据宽度计算相应的高度
            proposed_height = int(proposed_width / self.aspect_ratio)
            
            # 计算新位置
            new_x = self.x()
            if 'left' in self.resize_direction:
                new_x = self.start_geometry.right() - proposed_width
                
            # 在更新布局之前设置新的几何形状
            self.setGeometry(new_x, self.y(), proposed_width, proposed_height)
            
            # 计算卡片尺寸
            margin = 1
            spacing = 1
            available_width = proposed_width - (2 * margin) - ((self.current_columns - 1) * spacing)
            card_width = available_width // self.current_columns
            card_height = int(card_width * (145/120))  # 使用相同的比例
            
            # 批量更新所有卡片的大小
            for card_widget in self.card_widgets:
                card_widget.setFixedSize(card_width, card_height)
            
            # 更新底部菜单位置
            self.update_bottom_bar_position()
                
        except Exception as e:
            print(f"调整窗口大小失败: {e}")

    def moveEvent(self, event):
        """处理窗口移动事件"""
        super().moveEvent(event)
        self.update_bottom_bar_position()

    def update_bottom_bar_position(self):
        """更新底部菜单栏位置"""
        if self.isVisible():
            main_geo = self.geometry()
            
            # 获取所有底部菜单中的按钮和标签
            widgets = []
            total_width = 0
            for child in self.bottom_bar.children():
                if isinstance(child, (QPushButton, QLabel)):
                    widgets.append(child)
                    total_width += child.sizeHint().width() + 4  # 4是按钮间距
            
            # 计算最小需要的宽度
            min_width = main_geo.width()  # 使用主窗口宽度作为参考
            
            # 判断是否需要两行显示
            needs_two_rows = total_width > (min_width - 20)  # 20是左右边距
            
            if needs_two_rows:
                # 重新创建两行布局
                old_layout = self.bottom_bar.layout()
                if old_layout:
                    # 保存所有部件的引用
                    saved_widgets = []
                    while old_layout.count():
                        widget = old_layout.takeAt(0)
                        if widget.widget():
                            saved_widgets.append(widget.widget())
                    # 删除旧布局
                    QWidget().setLayout(old_layout)
                
                # 创建新的垂直布局
                v_layout = QVBoxLayout(self.bottom_bar)
                v_layout.setContentsMargins(4, 2, 4, 2)
                v_layout.setSpacing(2)
                
                # 创建两个水平布局
                top_row = QHBoxLayout()
                bottom_row = QHBoxLayout()
                
                # 分配控件到两行
                mid_point = len(widgets) // 2
                for i, widget in enumerate(widgets):
                    if i < mid_point:
                        top_row.addWidget(widget)
                    else:
                        bottom_row.addWidget(widget)
                
                # 添加到垂直布局
                v_layout.addLayout(top_row)
                v_layout.addLayout(bottom_row)
                
                # 调整底部菜单高度
                self.bottom_bar.setFixedHeight(60)  # 两行高度
                
            else:
                # 单行布局
                if not isinstance(self.bottom_bar.layout(), QHBoxLayout):
                    # 如果不是水平布局，重新创建
                    old_layout = self.bottom_bar.layout()
                    if old_layout:
                        # 保存所有部件的引用
                        saved_widgets = []
                        while old_layout.count():
                            widget = old_layout.takeAt(0)
                            if widget.widget():
                                saved_widgets.append(widget.widget())
                        # 删除旧布局
                        QWidget().setLayout(old_layout)
                    
                    # 创建新的水平布局
                    h_layout = QHBoxLayout(self.bottom_bar)
                    h_layout.setContentsMargins(4, 2, 4, 2)
                    h_layout.setSpacing(4)
                    
                    # 重新添加所有部件
                    for widget in widgets:
                        h_layout.addWidget(widget)
                
                # 恢复单行高度
                self.bottom_bar.setFixedHeight(30)
            
            # 计算并设置底部菜单的位置
            x_pos = main_geo.x()
            y_pos = main_geo.y() + main_geo.height()
            
            # 更新底部菜单的大小和位置
            self.bottom_bar.setFixedWidth(main_geo.width())
            self.bottom_bar.move(x_pos, y_pos)
            self.bottom_bar.raise_()

    def toggle_lock(self):
        """锁定或解锁窗口位置"""
        self.is_locked = self.lock_button.isChecked()
        if self.is_locked:
            self.lock_button.setText(self.lock_text)
            self.setWindowFlags(
                self.windowFlags() | Qt.WindowType.WindowTransparentForInput
            )
            self.start_mouse_tracking()
        else:
            self.lock_button.setText(self.unlock_text)
            self.setWindowFlags(
                self.windowFlags() & ~Qt.WindowType.WindowTransparentForInput
            )
            self.stop_mouse_tracking()

        # 重新显示窗口
        self.show()
        self.update_bottom_bar_position()
        
        # 检查当前鼠标位置决定是否显示底部菜单
        self.check_mouse_position()

    def mousePressEvent(self, event):
        """鼠标按下事件，开始拖动或调整大小"""
        if event.button() == Qt.MouseButton.LeftButton and not self.is_locked:
            # 首先检查是否在边缘
            if self.is_on_edge(event.pos()):
                self.is_resizing = True
                self.is_dragging = False  # 确保不会同时拖动
                self.resize_start_position = event.globalPosition().toPoint()
                self.start_geometry = self.geometry()
            else:
                self.is_dragging = True
                self.is_resizing = False  # 确保不会同时缩放
                self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        """鼠标移动事件，拖动窗口或调整大小"""
        if not self.is_locked:
            if self.is_resizing and event.buttons() == Qt.MouseButton.LeftButton:
                self.resize_window(event.globalPosition().toPoint())
                event.accept()
            elif self.is_dragging and event.buttons() == Qt.MouseButton.LeftButton:
                self.move(event.globalPosition().toPoint() - self.drag_position)
                event.accept()
            else:
                self.update_cursor(event.pos())
        # 无论是否锁定都显示底部菜单
        self.show_bottom_bar()
        self.hide_timer.stop()

    def mouseReleaseEvent(self, event):
        """鼠标释放事件，结束拖动和调整大小"""
        if event.button() == Qt.MouseButton.LeftButton:
            # 重置所有状态
            self.is_dragging = False
            self.is_resizing = False
            self.resize_direction = None
            self.unsetCursor()
            event.accept()



    def is_on_edge(self, pos):
        """检查鼠标是否在窗口边缘，用于调整大小"""
        margin = 5  # 边缘宽度
        rect = self.rect()
        x = pos.x()
        y = pos.y()
        w = rect.width()
        h = rect.height()
        bottom_height = 10  # 底部菜单栏的高度
        
        # 如果鼠标在底部菜单栏区域，不触发缩放
        if y >= h - bottom_height:
            self.resize_direction = None
            return False
            
        resizing = False
        
        # 检查左边缘
        if x <= margin:
            self.resize_direction = 'left'
            resizing = True
        # 检查右边缘
        elif x >= w - margin:
            self.resize_direction = 'right'
            resizing = True
        else:
            self.resize_direction = None
            
        return resizing

    def resize_window(self, global_pos):
        """调整窗口大小时同时调整卡片大小"""
        try:
            if not self.start_geometry or not self.resize_start_position:
                return
                
            delta = global_pos - self.resize_start_position
            
            # 计算新的宽度
            if 'left' in self.resize_direction:
                proposed_width = self.start_geometry.width() - delta.x()
            elif 'right' in self.resize_direction:
                proposed_width = self.start_geometry.width() + delta.x()
            else:
                proposed_width = self.width()
            
            # 确保最小宽度
            proposed_width = max(self.minimumWidth(), proposed_width)
            
            # 根据宽度计算相应的高度
            proposed_height = int(proposed_width / self.aspect_ratio)
            
            # 限制单次调整的最大变化量
            max_change = 50
            current_width = self.width()
            if abs(proposed_width - current_width) > max_change:
                if proposed_width > current_width:
                    proposed_width = current_width + max_change
                else:
                    proposed_width = current_width - max_change
                proposed_height = int(proposed_width / self.aspect_ratio)
            
            # 计算新位置
            new_x = self.x()
            if 'left' in self.resize_direction:
                new_x = self.start_geometry.right() - proposed_width
            
            # 使用统一的卡片尺寸计算方法
            card_width, card_height = self.calculate_card_size()
            
            # 更新所有卡片的大小
            for card_widget in self.card_widgets:
                card_widget.setFixedSize(card_width, card_height)
            
            # 应用新的几何属性
            self.setGeometry(new_x, self.y(), proposed_width, proposed_height)
            
        except Exception as e:
            print(f"调整窗口大小失败: {e}")

    def update_card_sizes(self, window_width, window_height):
        """更新卡片尺寸"""
        try:
            available_width = window_width - 8
            card_width = (available_width - 6) // 4
            card_height = int(card_width * 1.4)
            
            # 设置最小卡片尺寸限制
            if card_width < 50 or card_height < 70:
                return
                
            for card_widget in self.card_widgets:
                card_widget.setFixedSize(card_width, card_height)
        except Exception as e:
            print(f"更新卡片尺寸失败: {e}")


    def update_cursor(self, pos):
        """改进的光标更新逻辑"""
        if not self.is_locked and self.is_on_edge(pos):
            if self.resize_direction in ['left', 'right']:
                self.setCursor(Qt.CursorShape.SizeHorCursor)
            elif self.resize_direction in ['top', 'bottom']:
                self.setCursor(Qt.CursorShape.SizeVerCursor)
            elif self.resize_direction in ['top-left', 'bottom-right']:
                self.setCursor(Qt.CursorShape.SizeFDiagCursor)
            elif self.resize_direction in ['top-right', 'bottom-left']:
                self.setCursor(Qt.CursorShape.SizeBDiagCursor)
        else:
            self.unsetCursor()

    def enterEvent(self, event):
        """鼠标进入主窗口"""
        if not self.is_locked:
            self.update_cursor(self.mapFromGlobal(QCursor.pos()))
        # 显示底部菜单
        self.show_bottom_bar()
        self.hide_timer.stop()  # 停止隐藏计时器
        super().enterEvent(event)

    def leaveEvent(self, event):
        """鼠标离开主窗口"""
        self.unsetCursor()
        self.resize_direction = None
        # 启动隐藏计时器，但要考虑鼠标是否在底部菜单上
        if not self.mouse_on_bottom_bar:
            self.hide_timer.start(500)
        super().leaveEvent(event)

    def show_bottom_bar(self):
        """显示底部菜单"""
        self.bottom_bar.show()
        self.bottom_bar.raise_()  # 确保底部菜单在最顶层
        self.update_bottom_bar_position()

    def hide_bottom_bar(self):
        """隐藏底部菜单"""
        cursor_pos = QCursor.pos()
        window_rect = self.geometry()
        bottom_bar_rect = self.bottom_bar.geometry()
        
        # 扩大检测区域
        window_rect.setHeight(window_rect.height() + 10)
        
        # 只有当鼠标真正离开所有区域时才隐藏
        if not window_rect.contains(cursor_pos) and not bottom_bar_rect.contains(cursor_pos):
            self.bottom_bar.hide()

    def update_layout(self):
        try:
            # 清除现有布局中的所有部件
            for card_widget in self.card_widgets:
                self.grid.removeWidget(card_widget)
            
            # 设置极小的边距和间距
            margin = 1  # 边距为1像素
            spacing = 1  # 间距为1像素
            
            # 设置布局参数
            self.grid.setContentsMargins(margin, margin, margin, margin)
            self.grid.setHorizontalSpacing(spacing)  # 水平间距
            self.grid.setVerticalSpacing(spacing)    # 垂直间距
            
            # 计算卡片尺寸
            window_width = self.width()
            available_width = window_width - (2 * margin) - ((self.current_columns - 1) * spacing)
            card_width = available_width // self.current_columns
            card_height = int(card_width * (145/120))  # 从160/120改为140/120
            
            # 重新布局卡片
            for i, card_widget in enumerate(self.card_widgets):
                row = i // self.current_columns
                col = i % self.current_columns
                card_widget.setFixedSize(card_width, card_height)
                self.grid.addWidget(card_widget, row, col)
                
        except Exception as e:
            print(f"更新布局失败: {e}")

    def clear_cards(self):
        """清除所有卡片部件"""
        # 从网格布局中移除所有卡片
        for card_widget in self.card_widgets:
            self.grid.removeWidget(card_widget)
            card_widget.deleteLater()
        
        # 清空卡片列表
        self.card_widgets.clear()


    def calculate_card_size(self):
        """统一计算卡片尺寸的方法"""
        window_width = self.width()
        margin = 1  # 统一的边距值
        spacing = 1  # 统一的间距值
        
        # 计算可用宽度
        available_width = window_width - (1 * margin)
        total_spacing = (self.current_columns - 1) * spacing
        
        # 计算卡片尺寸
        card_width = (available_width - total_spacing) // self.current_columns
        card_height = int(card_width * (145/120))  # 保持3:4比例
        
        return card_width, card_height

    def update_display(self, cards):
        """更新卡组显示"""
        self.clear_cards()
        
        # 使用统一的尺寸计算方法
        card_width, card_height = self.calculate_card_size()
        
        # 分离已知卡牌和未知卡牌
        known_cards = [card for card in cards if isinstance(card, dict)]
        unknown_cards = [card for card in cards if isinstance(card, str)]
        
        # 排序已知卡牌
        sorted_known_cards = sorted(known_cards, key=lambda x: (
            not x.get('played', False),
            not x.get('known', False),
            x.get('known', False),
            x.get('cost', 99) if x.get('known', False) else 0
        ))
        
        # 合并已排序的已知卡牌和未知卡牌
        sorted_cards = sorted_known_cards + unknown_cards
        
        # 创建卡片部件
        for i, card in enumerate(sorted_cards):
            row = i // self.current_columns
            col = i % self.current_columns
            
            # 为未知卡牌创建特殊的卡片信息
            if isinstance(card, str):
                card_info = {'name': '未知卡牌', 'known': False}
            else:
                card_info = card
            
            card_widget = CardWidget(card_info)
            # 根据窗口设置决定是否启用右键菜单
            if not self.enable_context_menu:
                card_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
                
            card_widget.setFixedSize(card_width, card_height)
            self.grid.addWidget(card_widget, row, col)
            self.card_widgets.append(card_widget)
        
        self.update_bottom_bar_position()