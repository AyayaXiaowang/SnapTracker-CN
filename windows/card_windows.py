from .base_window import BaseWindow
from PyQt6.QtCore import pyqtSignal
from widgets.card_widget import signal_manager
from PyQt6.QtWidgets import (QComboBox)
from PyQt6.QtWidgets import QApplication

class PlayerWindow(BaseWindow):
    def __init__(self, title):
        super().__init__(title, enable_context_menu=False)
        self.setWindowTitle("我方牌库")
        self.enable_context_menu = False  # 禁用右键菜单
        
        # 添加卡组选择器
        self.deck_selector = QComboBox()
        self.deck_selector.setObjectName("deckSelector")
        self.deck_selector.setMinimumWidth(200)
        self.deck_selector.setFixedHeight(26)

        # 初始化调试输出
        try:
            import ctypes
            ctypes.windll.kernel32.SetConsoleTitleW("牌库")
        except:
            pass

# card_windows.py 中的 EnemyWindow 类修改
class EnemyWindow(BaseWindow):
    def __init__(self, title, monitor_thread=None, main_window=None):
        super().__init__(title)
        self.setWindowTitle("对手牌库")
        self.excluded_cards = set()
        self.main_window = main_window  # 保存主窗口引用
        self.monitor_thread = None  # 直接作为实例变量
        signal_manager.remove_enemy_card.connect(self.handle_remove_enemy_card)
        signal_manager.reset_excluded_cards.connect(self.reset_excluded_cards)

    def reset_excluded_cards(self):
        """重置排除列表"""
        try:
            print("\n=== 重置排除列表 ===")
            # 清空当前窗口的排除列表
            self.excluded_cards = set()
            
            # 如果有监控线程，清空当前对手的排除列表
            if self.monitor_thread and self.monitor_thread.deck_history:
                current_enemy = self.monitor_thread.deck_history.current_enemy
                if current_enemy:
                    # 清空排除列表
                    self.monitor_thread.deck_history.excluded_enemy_cards[current_enemy] = set()
                    print(f"已清空对手 {current_enemy} 的排除列表")
                    
                    # 重置当前游戏卡牌中的敌方卡牌
                    self.monitor_thread.current_game_cards['enemy'] = set()
                    
                    # 调用主窗口的强制更新方法
                    if hasattr(self, 'main_window'):
                        self.main_window.force_update()
            
            print("=== 重置排除列表完成 ===\n")
            
        except Exception as e:
            print(f"重置排除列表失败: {e}")
            import traceback
            traceback.print_exc()

            
    def handle_remove_enemy_card(self, card_name):
        """处理移除敌方卡牌的操作"""
        print(f"\n=== 处理移除卡牌: {card_name} ===")
        
        # 将卡牌添加到本地排除列表
        self.excluded_cards.add(card_name)
        print(f"当前窗口的排除列表: {self.excluded_cards}")
        
        # 获取当前显示的卡牌
        current_deck = []
        unknown_count = 0
        
        # 遍历现有卡牌
        for i in range(self.grid.count()):
            card_widget = self.grid.itemAt(i).widget()
            if card_widget and hasattr(card_widget, 'card_info'):
                card_info = card_widget.card_info
                # 如果是未知卡牌
                if not isinstance(card_info, dict) or not card_info.get('known', False):
                    unknown_count += 1
                # 如果是已知卡牌且不是被移除的卡牌
                elif card_info['name'] != card_name:
                    current_deck.append(card_info)
        
        # 将被移除的已知卡牌转换为未知卡牌
        unknown_count += 1
        
        # 添加未知卡牌
        for _ in range(unknown_count):
            current_deck.append('未知')
        
        if self.monitor_thread and hasattr(self.monitor_thread, 'deck_history'):
            # 获取当前对手名称
            current_enemy = self.monitor_thread.deck_history.current_enemy
            print(f"当前对手: {current_enemy}")
            
            # 更新历史记录中的排除列表
            self.monitor_thread.deck_history.exclude_card(current_enemy, card_name)
            
            # 从当前游戏记录中移除
            if card_name in self.monitor_thread.current_game_cards['enemy']:
                self.monitor_thread.current_game_cards['enemy'].discard(card_name)
                print(f"已从当前游戏记录中移除: {card_name}")
            
            print(f"当前牌组状态:")
            print(f"- 已知卡牌: {len([c for c in current_deck if isinstance(c, dict)])}张")
            print(f"- 未知卡牌: {unknown_count}张")
            print(f"- 总计: {len(current_deck)}张")
            
            # 清理显示
            self.clear_cards()
            
            # 重新显示所有卡牌
            if current_deck:
                print(f"重新显示 {len(current_deck)} 张卡牌")
                self.update_display(current_deck)
            else:
                print("没有剩余卡牌需要显示")
            
            # 强制更新显示
            main_window = QApplication.instance().property("main_window")
            if main_window:
                print("触发主窗口强制更新")
                main_window.force_update()
        else:
            print(f"警告: monitor_thread 未设置或不可用")
            
        print("=== 移除卡牌处理完成 ===\n")