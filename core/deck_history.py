from PyQt6.QtWidgets import QApplication
class DeckHistory:
    def __init__(self):
        self.current_enemy = None
        self.enemy_history = set()
        self.player_deck = None
        self.player_deck_cards = set()  # 用于存储玩家卡组的卡牌集合
        self.excluded_enemy_cards = {}  # 修改为字典，键是对手名称，值是该对手被排除的卡牌集合

    def is_player_deck_changed(self, new_deck):
        """检查新的卡组是否与历史记录不同"""
        if not new_deck:
            return self.player_deck is not None
        
        if not self.player_deck:
            return True
            
        # 提取新卡组的卡牌集合
        new_cards = {card['name'] for card in new_deck.get('cards', [])}
        
        # 比较与当前记录的卡牌集合
        return new_cards != self.player_deck_cards

    def exclude_card(self, enemy_name, card_name):
        """为特定对手添加一张卡到排除列表"""
        enemy_name = enemy_name or "Unknown"
        print(f"\n=== 添加排除卡牌 ===")
        print(f"对手: {enemy_name}")
        print(f"卡牌: {card_name}")
        print(f"排除前的列表: {self.excluded_enemy_cards}")
        
        if enemy_name not in self.excluded_enemy_cards:
            self.excluded_enemy_cards[enemy_name] = set()
            print(f"为对手 {enemy_name} 创建新的排除列表")
        
        self.excluded_enemy_cards[enemy_name].add(card_name)
        
        # 从当前历史记录中移除
        if enemy_name == self.current_enemy:
            self.enemy_history.discard(card_name)
            print(f"从当前历史记录中移除卡牌: {card_name}")
        
        print(f"当前所有对手的排除列表:")
        for enemy, cards in self.excluded_enemy_cards.items():
            print(f"- {enemy}: {cards}")
        print("=== 排除卡牌完成 ===\n")
    
    def update_enemy_cards(self, enemy_name, cards):
        """更新敌方卡组历史"""
        print(f"\n=== 更新敌方卡组 ===")
        enemy_name = enemy_name or "Unknown"
        print(f"对手名称: {enemy_name}")
        print(f"当前对手: {self.current_enemy}")
        
        # 获取当前对手的排除列表
        excluded_cards = self.excluded_enemy_cards.get(enemy_name, set())
        print(f"对手 {enemy_name} 的排除列表: {excluded_cards}")
        print(f"所有对手的排除列表: {self.excluded_enemy_cards}")
        
        # 提取卡牌名称并打印详细信息
        print("\n处理输入的卡牌:")
        for card in cards:
            print(f"- 卡牌: {card['name']}, "
                  f"是否被排除: {card['name'] in excluded_cards}")
        
        # 过滤被排除的卡牌
        card_names = {card['name'] for card in cards if card['name'] not in excluded_cards}
        print(f"\n过滤后的卡牌: {card_names}")
        
        # 处理对手更换
        if enemy_name != self.current_enemy and enemy_name != "Unknown":
            print(f"\n检测到新对手:")
            print(f"- 旧对手: {self.current_enemy}")
            print(f"- 新对手: {enemy_name}")
            print(f"- 旧历史记录: {self.enemy_history}")
            self.current_enemy = enemy_name
            self.enemy_history = set()  # 清空历史记录
            
            # 通知 MonitorThread 重置当前游戏卡牌记录
            monitor_thread = QApplication.instance().property("main_window").monitor_thread
            if monitor_thread:
                monitor_thread.current_game_cards['enemy'] = set()
                # 强制更新显示
                monitor_thread.processed_data_signal.emit({
                    'player_deck': monitor_thread._build_player_deck(monitor_thread.current_game_cards['player']),
                    'enemy_deck': monitor_thread._build_enemy_deck(set())  # 传入空集合强制清空显示
                })
            
            print(f"- 清空后的历史记录: {self.enemy_history}")
        elif self.current_enemy is None:
            print(f"\n首次设置对手: {enemy_name}")
            self.current_enemy = enemy_name
        
        # 更新历史记录
        print("\n更新历史记录:")
        print(f"- 更新前: {self.enemy_history}")
        self.enemy_history.update(card_names)
        print(f"- 更新后: {self.enemy_history}")
        
        print("=== 更新敌方卡组完成 ===\n")

    def get_current_enemy_history(self):
        """获取当前对手的历史记录（排除已标记的卡牌）"""
        print(f"\n=== 获取当前对手历史记录 ===")
        print(f"当前对手: {self.current_enemy}")
        print(f"原始历史记录: {self.enemy_history}")
        
        if not self.enemy_history:
            print("警告: 当前没有敌方卡牌历史记录")
            print("=== 获取历史记录完成 ===\n")
            return set()
            
        # 获取当前对手的排除列表
        excluded_cards = self.excluded_enemy_cards.get(self.current_enemy, set())
        print(f"当前对手的排除列表: {excluded_cards}")
        
        # 过滤后的历史记录
        filtered_history = self.enemy_history - excluded_cards
        print(f"过滤后的历史记录: {filtered_history}")
        print("=== 获取历史记录完成 ===\n")
        
        return filtered_history
    
    def update_player_deck(self, deck):
        """更新玩家卡组，返回是否发生变化"""
        if self.is_player_deck_changed(deck):
            self.player_deck = deck
            if deck and 'cards' in deck:
                self.player_deck_cards = {card['name'] for card in deck['cards']}
            else:
                self.player_deck_cards = set()
            print("玩家卡组已更新:")
            for card_name in sorted(self.player_deck_cards):
                print(f"  - {card_name}")
            return True
        return False