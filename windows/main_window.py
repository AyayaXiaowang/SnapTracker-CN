from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QComboBox, QPushButton, QLabel, QGridLayout,
    QScrollArea, QFrame, QGraphicsColorizeEffect, QApplication,
    QSystemTrayIcon, QMenu, QSpinBox, QGraphicsScene,QGraphicsColorizeEffect,
    QSizePolicy, QGraphicsView, QStyle,QCheckBox,QGroupBox,QMessageBox
)
from PyQt6 import QtCore  # 添加这行
from PyQt6.QtCore import (
    Qt, QThread, pyqtSignal, QPoint, QSettings,
    QTimer, QEvent, QSize
)
from PyQt6.QtGui import (
    QAction, QPixmap, QIcon, QCursor
)
import json
import os
import time
import sys
import win32com.client
import win32gui
from core.deck_history import DeckHistory
from core.snap_game_reader import get_player_info, parse_game_cards, load_game_state
from core.deck_loader import get_snap_decks_info
from core.screen_matcher import check_screen_match
from windows.card_windows import PlayerWindow, EnemyWindow

class MonitorThread(QThread):
    update_signal = pyqtSignal(dict)
    processed_data_signal = pyqtSignal(dict)
    update_auto_select_signal = pyqtSignal()  # 新增信号

    def __init__(self, decks, cards_info, name_mapping, update_interval=1000):
        super().__init__()
        self.is_running = False
        self.decks = decks
        self.cards_info = cards_info
        self.name_mapping = name_mapping
        self.deck_history = DeckHistory()
        self.current_selected_deck = None
        self.update_interval = update_interval
        self.last_modified_time = 0  # Initialize last modified time
        self.current_game_cards = {
            'player': set(),  # 玩家当局出现的卡
            'enemy': set()    # 对手当局出现的卡
        }
        self.is_new_game = True  # 用于标记是否新的一局
        self.last_cards_count = 0  # 上一次读取的卡牌总数

        # 添加预设卡组相关属性
        self.use_preset_decks = False
        self.preset_decks = {
                "专家预组": ["Cable", "Carnage", "Death", "DoctorOctopus", "Gladiator", "Killmonger", "Knull", "Magik", "ShangChi", "ThePhoenixForce", "Venom", "Yondu"],

                "德古拉园": ["Dracula", "RedSkull", "KaZar", "SwordMaster", "StrongGuy", "Infinaut", "Nightcrawler", "Blade", "SquirrelGirl", "BlueMarvel", "RocketRaccoon", "AntMan"],

                "王者归来": ["Hela", "GhostRider", "Gambit", "LadySif", "Jubilee", "Infinaut", "Odin", "Sandman", "Hulk", "IronMan", "SwordMaster", "Blade"],

                "平凡强者": ["Patriot", "Brood", "BlueMarvel", "Shocker", "Cyclops", "TheThing", "SquirrelGirl", "MistyKnight", "Forge", "MrSinister", "Hulk", "AmericaChavez"],

                "移动入门": ["Dagger", "HumanTorch", "AmericaChavez", "IronFist", "Kraven", "DoctorStrange", "Hulkbuster", "MultipleMan", "Cloak", "Vulture", "Vision", "Heimdall"],

                "新手推荐": ["BlueMarvel", "KaZar", "SwordMaster", "StrongGuy", "Bishop", "Angela", "Blade", "Dazzler", "SquirrelGirl", "Nightcrawler", "RocketRaccoon", "AntMan"],

                "进阶之选": ["Destroyer", "Spectrum", "ProfessorX", "Klaw", "Warpath", "MrFantastic", "Cosmo", "Lizard", "Colossus", "Armor", "BuckyBarnes", "AntMan"],

                "双倍力量": ["SheHulk", "DevilDinosaur", "MoonGirl", "Cable", "WhiteQueen", "Agent13", "TheCollector", "Sentinel", "Sunspot", "ShangChi", "Cosmo", "Enchantress"],

                "双倍揭示": ["Wong", "Ironheart", "WhiteTiger", "SpiderWoman", "Wolfsbane", "Odin", "Medusa", "Starlord", "RocketRaccoon", "Iceman", "Enchantress", "Scorpion"],
        }


    def run(self):
        try:
            print("\n=== 监控线程启动 ===")
            self.is_running = True
            
            while self.is_running:
                try:
                    print("\n--- 开始新一轮监控 ---")
                    
                    # 获取文件路径
                    game_state_path = os.path.join(
                        os.path.expanduser('~'),
                        'AppData', 'LocalLow', 'NetEase', 'SnapCN',
                        'Standalone', 'States', 'prod', 'GameState.json'
                    )
                    print(f"监控文件路径: {game_state_path}")

                    # 检查文件是否存在
                    if not os.path.exists(game_state_path):
                        print("游戏状态文件不存在")
                        QThread.msleep(self.update_interval)
                        continue

                    # 获取当前修改时间
                    current_modified_time = os.path.getmtime(game_state_path)
                    print(f"文件修改时间检查 - 当前: {current_modified_time}, 上次: {self.last_modified_time}")

                    # 检查文件是否被修改
                    if current_modified_time != self.last_modified_time:
                        print("检测到文件变化，开始读取游戏状态")
                        game_state = load_game_state(game_state_path)
                        
                        if isinstance(game_state, str):  # 如果返回错误信息
                            print(f"读取游戏状态失败: {game_state}")
                            QThread.msleep(self.update_interval)
                            continue

                        print("更新最后修改时间")
                        self.last_modified_time = current_modified_time
                        
                        print("处理游戏状态数据...")
                        processed_data = self.process_game_state(game_state)
                        
                        if processed_data:
                            print("发送处理后的数据")
                            self.processed_data_signal.emit(processed_data)
                            print("数据发送完成")
                        else:
                            print("游戏状态处理返回空数据")
                    else:
                        print("文件未发生变化")

                except Exception as e:
                    print(f"\n!!! 监控线程错误: {e}")
                    print("详细错误信息:")
                    import traceback
                    traceback.print_exc()

                print(f"等待 {self.update_interval}ms 后进行下一次检查")
                QThread.msleep(self.update_interval)

            print("=== 监控线程结束 ===\n")
            
        except Exception as e:
            print(f"\n!!! 监控线程主循环异常: {e}")
            print("详细错误信息:")
            import traceback
            traceback.print_exc()


    def stop(self):
        self.is_running = False

    def clear_history(self):
        """清除历史记录"""
        self.deck_history = DeckHistory()
        self.last_game_state = None
        self.last_content_hash = None
        
    def set_update_interval(self, interval):
        """设置更新频率，单位为毫秒"""
        self.update_interval = interval

    def process_game_state(self, game_state):
        try:
            start_time = time.time()
            print("\n========== 开始处理游戏状态 ==========")
            
            main_window = QApplication.instance().property("main_window")
            excluded_cards = set()
            if main_window and main_window.enemy_window:
                excluded_cards = main_window.enemy_window.excluded_cards

            # 检查游戏状态是否有效
            if not game_state or not isinstance(game_state, dict):
                print(f"无效的游戏状态数据: {type(game_state)}")
                self.current_game_cards = {'player': set(), 'enemy': set()}
                return self._build_return_data(self._build_default_player_deck())

            # 获取玩家信息
            player_info = get_player_info(game_state)
            if not player_info or len(player_info) != 2:
                print(f"无效的玩家信息: {player_info}")
                self.current_game_cards = {'player': set(), 'enemy': set()}
                return self._build_return_data(self._build_default_player_deck())

            # 解包玩家信息
            (local_name, local_ids, local_cardback), (enemy_name, enemy_ids, enemy_cardback) = player_info

            # 获取并过滤卡牌信息
            cards = parse_game_cards(game_state)
            if cards is None or len(cards) == 0:
                print("没有检测到卡牌或新的一局开始")
                self.current_game_cards = {'player': set(), 'enemy': set()}
                self.update_auto_select_signal.emit()
                return self._build_return_data(self._build_default_player_deck())

            # 过滤和转换卡牌名称
            filtered_cards = []
            for card in cards:
                if not card.get('created_by'):  # 排除衍生卡
                    normalized_name = card['name'].lower().replace(" ", "").replace("-", "").replace("_", "")
                    if normalized_name in self.name_mapping:
                        card['name'] = self.name_mapping[normalized_name]
                        filtered_cards.append(card)

            # 确定卡牌归属
            local_ids = [str(lid) for lid in local_ids if lid] if local_ids else []
            enemy_ids = [str(eid) for eid in enemy_ids if eid] if enemy_ids else []

            # 获取玩家卡组历史
            player_deck_cards = set()
            if self.current_selected_deck in self.decks:
                deck_info = self.decks[self.current_selected_deck]
                if isinstance(deck_info, dict) and 'cards' in deck_info:
                    player_deck_cards = {card['name'] for card in deck_info['cards']}

            # 分配卡牌归属
            for card in filtered_cards:
                if card.get('created_by'):
                    continue

                owner_ids = card['owner_id'] if isinstance(card['owner_id'], list) else [card['owner_id']]
                owner_ids = [str(oid) for oid in owner_ids if oid]

                # 判断归属
                if any(oid in local_ids for oid in owner_ids):
                    card['owner'] = 'player'
                    self.current_game_cards['player'].add(card['name'])
                elif any(oid in enemy_ids for oid in owner_ids) or card['name'] not in player_deck_cards:
                    # 只有当卡牌不在排除列表中时才添加到敌方卡牌中
                    if card['name'] not in excluded_cards:
                        card['owner'] = 'enemy'
                        self.current_game_cards['enemy'].add(card['name'])
                else:
                    card['owner'] = 'unknown'

            # 确保历史记录中也不包含被排除的卡牌
            enemy_history = self.deck_history.get_current_enemy_history()
            if enemy_name:
                enemy_cards = []
                for card_name in (enemy_history.union(self.current_game_cards['enemy'])) - excluded_cards:
                    enemy_cards.append({
                        'name': card_name,
                        'card_id': None,
                        'status': 'history',
                        'owner_id': enemy_ids,
                        'created_by': None
                    })
                # 更新历史记录（排除被标记的卡牌）
                self.deck_history.update_enemy_cards(enemy_name, enemy_cards)

            # 构建返回数据
            return {
                'player_deck': self._build_player_deck(self.current_game_cards['player']),
                'enemy_deck': self._build_enemy_deck(self.current_game_cards['enemy'])
            }

        except Exception as e:
            print(f"处理游戏状态失败: {e}")
            import traceback
            traceback.print_exc()
            return self._build_return_data(self._build_default_player_deck())

    def _build_return_data(self, player_deck):
        """构建返回数据"""
        return {
            'player_deck': player_deck,
            'enemy_deck': self._build_enemy_deck(set())  # 使用 _build_enemy_deck 保留历史记录
        }

    def _build_default_player_deck(self):
        """构建默认的玩家卡组"""
        selected_deck = self.current_selected_deck
        if not selected_deck:
            print("没有选择卡组")
            return self._create_unknown_deck()

        try:
            # 检查是否是预设卡组
            if self.use_preset_decks and selected_deck in self.preset_decks:
                preset_cards = []
                for card_id in self.preset_decks[selected_deck]:
                    normalized_id = card_id.lower().replace(" ", "").replace("-", "").replace("_", "")
                    if normalized_id in self.name_mapping:
                        chinese_name = self.name_mapping[normalized_id]
                        # 构建完整的卡牌信息
                        card_info = {
                            'name': chinese_name,
                            'card_id': card_id,
                            'image': f'卡面/{chinese_name}.png',
                            'known': True,
                            'played': False
                        }
                        preset_cards.append(card_info)
                
                if preset_cards:
                    print(f"使用预设卡组 '{selected_deck}' 构建玩家牌库，包含 {len(preset_cards)} 张卡牌")
                    for card in preset_cards:
                        print(f"卡牌信息: {card['name']} - {card['image']}")
                    return self._build_deck_from_cards(preset_cards, self.current_game_cards['player'])
                else:
                    print(f"预设卡组 '{selected_deck}' 没有有效的卡牌")
                    return self._create_unknown_deck()

            # 使用文件卡组的逻辑保持不变
            if selected_deck in self.decks:
                deck_info = self.decks[selected_deck]
                if isinstance(deck_info, dict) and 'cards' in deck_info:
                    print(f"使用卡组 '{selected_deck}' 构建玩家牌库")
                    return self._build_deck_from_cards(deck_info['cards'], self.current_game_cards['player'])

            print(f"未找到卡组 '{selected_deck}'，返回未知卡组")
            return self._create_unknown_deck()

        except Exception as e:
            print(f"构建玩家卡组失败: {e}")
            import traceback
            traceback.print_exc()
            return self._create_unknown_deck()

    def organize_cards_info(self, state):
        """组织卡牌信息的主函数"""
        try:
            print("\n开始组织卡牌信息...")
            cards = state['cards']
            (local_name, local_ids) = state['local_info']
            (enemy_name, enemy_ids) = state['enemy_info']
            current_game_cards = state['current_game_cards']
            enemy_cardback = state.get('enemy_cardback')
            local_cardback = state.get('local_cardback')  # 获取本地玩家卡背

            print(f"本地玩家卡背: {local_cardback}")
            print(f"对手玩家卡背: {enemy_cardback}")

            # 检查双方卡背是否相同
            #if local_cardback and enemy_cardback and local_cardback == enemy_cardback:
            if True:
                print("检测到玩家和对手使用相同卡背，使用ID判断逻辑")
                # 使用原来的ID判断逻辑
                local_ids = [str(lid) for lid in local_ids if lid] if local_ids else []
                enemy_ids = [str(eid) for eid in enemy_ids if eid] if enemy_ids else []

                verified_local_ids = set()
                verified_enemy_ids = set()

                # 获取玩家卡组历史
                player_deck_cards = set()
                if self.current_selected_deck and self.current_selected_deck in self.decks:
                    deck_info = self.decks[self.current_selected_deck]
                    if isinstance(deck_info, dict) and 'cards' in deck_info:
                        player_deck_cards = {card['name'] for card in deck_info['cards']}

                id_cards_map = {}
                for card in cards:
                    owner_ids = card['owner_id'] if isinstance(card['owner_id'], list) else [card['owner_id']]
                    owner_ids = [str(oid) for oid in owner_ids if oid]

                    for owner_id in owner_ids:
                        if owner_id not in id_cards_map:
                            id_cards_map[owner_id] = []
                        id_cards_map[owner_id].append(card['name'])

                for lid in local_ids:
                    if lid in id_cards_map:
                        verified_local_ids.add(lid)
                for eid in enemy_ids:
                    if eid in id_cards_map:
                        verified_enemy_ids.add(eid)

                card_counter = {}
                for card in cards:
                    if card.get('created_by'):  # 排除衍生卡
                        continue

                    owner_ids = card['owner_id'] if isinstance(card['owner_id'], list) else [card['owner_id']]
                    owner_ids = [str(oid) for oid in owner_ids if oid]

                    card_key = f"{card['name']}_{card.get('card_id', '')}"

                    if len(owner_ids) >= 3:
                        card_counter[card_key] = card_counter.get(card_key, 0) + 1
                        owner = 'player' if card_counter[card_key] % 2 == 0 else 'enemy'
                        card['owner'] = owner
                    else:
                        local_matches = any(oid in verified_local_ids for oid in owner_ids)
                        enemy_matches = any(oid in verified_enemy_ids for oid in owner_ids)

                        if local_matches and card['name'] not in player_deck_cards:
                            owner = 'enemy'
                        else:
                            if verified_local_ids and verified_enemy_ids:
                                if local_matches and enemy_matches:
                                    card_counter[card_key] = card_counter.get(card_key, 0) + 1
                                    owner = 'player' if card_counter[card_key] % 2 == 0 else 'enemy'
                                elif local_matches:
                                    owner = 'player'
                                elif enemy_matches:
                                    owner = 'enemy'
                                else:
                                    owner = 'unknown'
                            elif verified_local_ids:
                                owner = 'player' if local_matches else 'enemy'
                            elif verified_enemy_ids:
                                owner = 'enemy' if enemy_matches else 'player'
                            else:
                                owner = 'unknown'

                        card['owner'] = owner
                        if owner == 'player':
                            self.current_game_cards['player'].add(card['name'])
                        elif owner == 'enemy':
                            self.current_game_cards['enemy'].add(card['name'])

            else:
                # 使用卡背判断逻辑
                print("\n使用卡背判断逻辑...")
                for card in cards:
                    if card.get('created_by'):  # 排除衍生卡
                        continue
                        
                    card_name = card.get('name', '未知卡牌')
                    chinese_name = self.get_card_chinese_name(card_name)
                    card_back_id = card.get('card_back_id')
                    
                    print(f"\n处理卡牌: {chinese_name}")
                    print(f"该卡卡背ID: {card_back_id}")
                    
                    if card_back_id and enemy_cardback and card_back_id == enemy_cardback:
                        card['owner'] = 'enemy'
                        self.current_game_cards['enemy'].add(chinese_name)
                        print(f"卡背匹配对手卡背，判定为对手的卡")
                    else:
                        card['owner'] = 'player'
                        self.current_game_cards['player'].add(chinese_name)
                        if not card_back_id:
                            print(f"卡牌无卡背，默认判定为玩家的卡")
                        elif not enemy_cardback:
                            print(f"未知对手卡背，默认判定为玩家的卡")
                        else:
                            print(f"卡背与对手不同，判定为玩家的卡")

            # 过滤掉未知归属的卡牌
            valid_cards = [card for card in cards if card.get('owner') != 'unknown']

            print(f"\n卡牌归属统计:")
            player_cards = sum(1 for card in valid_cards if card['owner'] == 'player')
            enemy_cards = sum(1 for card in valid_cards if card['owner'] == 'enemy')
            print(f"玩家卡牌数: {player_cards}")
            print(f"对手卡牌数: {enemy_cards}")

            # 整理最终信息
            print("\n开始整理最终信息...")
            current_info = self._organize_cards_info(
                valid_cards, 
                local_name, 
                enemy_name,
                local_ids,
                enemy_ids,
                current_game_cards
            )
            
            print("卡牌信息整理完成")
            return current_info

        except Exception as e:
            print(f"整理卡牌信息失败: {e}")
            import traceback
            traceback.print_exc()
            return self._create_unknown_decks()

    # MonitorThread 类中的 _organize_cards_info 方法
    def _organize_cards_info(self, cards, local_name, enemy_name, local_id, enemy_id, current_game_cards):
        try:
            print("\n开始整理卡牌信息...")
            # 获取当前游戏中出现的卡牌
            player_known, enemy_known = self._get_known_cards(cards, local_id, enemy_id)
            
            # 从主窗口中获取 enemy_window 的排除列表
            main_window = QApplication.instance().property("main_window")
            excluded_cards = set()
            if main_window and main_window.enemy_window:
                excluded_cards = main_window.enemy_window.excluded_cards
                print(f"当前排除列表: {excluded_cards}")
            
            # 从已知卡牌和当前游戏记录中移除被排除的卡牌
            enemy_known = enemy_known - excluded_cards
            current_game_cards['enemy'] = current_game_cards['enemy'] - excluded_cards
            print(f"过滤后的敌方已知卡牌: {enemy_known}")
            
            # 更新历史记录（忽略被排除的卡牌）
            enemy_cards = []
            for card_name in enemy_known:
                if card_name not in excluded_cards:
                    enemy_cards.append({
                        'name': card_name,
                        'card_id': None,
                        'status': 'history',
                        'owner_id': enemy_id,
                        'created_by': None
                    })
            
            # 更新历史记录
            self.deck_history.update_enemy_cards(enemy_name, enemy_cards)
            
            # 从历史记录中再次获取卡牌（这次会过滤掉被排除的卡牌）
            enemy_history = self.deck_history.get_current_enemy_history()
            # 合并历史记录和当前已知卡牌
            all_enemy_known = enemy_history.union(enemy_known)
            print(f"最终敌方卡牌（包含历史记录）: {all_enemy_known}")
            
            # 构建牌库信息
            player_deck = self._build_player_deck(player_known)
            enemy_deck = self._build_enemy_deck(all_enemy_known)  # 使用合并后的卡牌集合
            
            return {
                'player_deck': player_deck,
                'enemy_deck': enemy_deck
            }
            
        except Exception as e:
            print(f"整理卡牌信息失败: {e}")
            import traceback
            traceback.print_exc()
            return self._create_unknown_decks()

    def _get_known_cards(self, cards, local_id, enemy_id):
        """获取当前游戏中出现的卡牌，返回中文名称集合"""
        player_known = set()
        enemy_known = set()

        for card in cards:
            if not card.get('created_by'):
                chinese_name = self.get_card_chinese_name(card['name'])
                if card['owner'] == 'player' or card['owner_id'] == local_id:
                    player_known.add(chinese_name)
                elif card['owner'] == 'enemy' or card['owner_id'] == enemy_id:
                    enemy_known.add(chinese_name)

        return player_known, enemy_known

    def get_card_chinese_name(self, english_name):
        """获取卡牌的中文名称"""
        if not english_name:
            return "未知卡牌"

        # 规范化英文名
        normalized_name = english_name.lower().replace(" ", "").replace("-", "").replace("_", "")
        chinese_name = self.name_mapping.get(normalized_name)

        if chinese_name:
            return chinese_name
        else:
            return english_name

    def _update_enemy_history(self, cards, enemy_name, enemy_id):
        """更新敌方卡组历史"""
        # 将未知对手名称标准化
        enemy_name = enemy_name or f"Unknown_{enemy_id}"

        # 修改敌方卡牌的筛选逻辑
        enemy_cards = []
        for card in cards:
            # 确保owner_id是列表
            owner_ids = card['owner_id'] if isinstance(card['owner_id'], list) else [card['owner_id']]
            owner_ids = [str(oid) for oid in owner_ids]  # 转换为字符串列表

            # 判断是否为敌方卡牌
            is_enemy_card = False

            # 如果owner_ids数量大于等于3，视为双方都有
            if len(owner_ids) >= 3:
                is_enemy_card = True
            # 否则检查是否包含enemy_id
            elif str(enemy_id) in owner_ids:
                is_enemy_card = True

            if is_enemy_card and not card.get('created_by'):
                enemy_cards.append({
                    **card,
                    'name': self.get_card_chinese_name(card['name'])
                })

        self.deck_history.update_enemy_cards(enemy_name, enemy_cards)

    def _build_player_deck(self, known_cards):
        """构建玩家卡组"""
        # 使用选择的卡组构建玩家牌库
        selected_deck = self.current_selected_deck  # 从后台线程中获取当前选择的卡组
        if selected_deck in self.decks:
            deck_info = self.decks[selected_deck]
            if isinstance(deck_info, dict) and 'cards' in deck_info:
                deck = self._build_deck_from_cards(deck_info['cards'], known_cards)
                return deck

        # 未找到选择的卡组，返回未知卡组
        return self._create_unknown_deck()

    def _build_deck_from_cards(self, cards_list, known_cards):
        """从卡牌列表构建卡组"""
        deck = []
        try:
            # 添加卡牌到卡组
            for card in cards_list:
                # 检查卡牌是否在当前游戏中出现
                is_in_game = card['name'] in known_cards  # 使用中文名进行匹配
                
                # 确保卡牌有所有必需的字段
                deck.append({
                    'name': card['name'],
                    'card_id': card.get('card_id'),
                    'image': card.get('image', f'卡面/{card["name"]}.png'),
                    'cost': card.get('cost', 99),  # 保留费用信息，默认值为99
                    'known': True,  # 预设卡组的卡牌都是已知的
                    'played': is_in_game
                })

            # 确保卡组大小为12
            deck = deck[:12]  # 如果超过则截断
            while len(deck) < 12:  # 如果不足则补充
                deck.append({
                    'name': '未知卡牌',
                    'known': False,
                    'image': None,
                    'card_id': None,
                    'cost': 99,  # 未知卡牌的默认费用
                    'played': False
                })

            return deck

        except Exception as e:
            print(f"构建卡组失败: {e}")
            import traceback
            traceback.print_exc()
            return self._create_unknown_deck()

    def _build_enemy_deck(self, known_cards):
        """构建敌方卡组"""
        try:
            print("\n=== 构建敌方卡组 ===")
            print(f"输入的已知卡牌: {known_cards}")
            
            # 获取历史记录（已经包含了排除处理）
            enemy_history = self.deck_history.get_current_enemy_history()
            print(f"获取到的历史记录（已排除）: {enemy_history}")
            
            # 获取当前对手的排除列表
            current_enemy = self.deck_history.current_enemy
            excluded_cards = self.deck_history.excluded_enemy_cards.get(current_enemy, set())
            print(f"当前对手 {current_enemy} 的排除列表: {excluded_cards}")
            
            # 从当前已知卡牌中移除被排除的卡牌
            current_known = known_cards - excluded_cards
            print(f"处理后的当前已知卡牌: {current_known}")
            
            # 合并处理后的卡牌集合
            all_known_cards = enemy_history.union(current_known)
            print(f"合并后的有效卡牌: {all_known_cards}")
            
            # 对已知卡牌进行排序，按照费用排序
            known_cards_with_cost = []
            for card_name in all_known_cards:
                cost = 99
                for cid, info in self.cards_info.items():
                    if info.get('chinese_name') == card_name:
                        cost = info.get('cost', 99)
                        break
                
                known_cards_with_cost.append({
                    'name': card_name,
                    'cost': cost,
                    'played': card_name in current_known  # 使用移除排除卡牌后的集合
                })
            
            # 按费用排序已知卡牌
            sorted_known_cards = sorted(known_cards_with_cost, key=lambda x: (
                not x['played'],  # 未打出的排前面
                x['cost']        # 按费用从小到大排序
            ))
            
            # 构建最终牌组
            deck = []
            max_cards = 12
            
            # 添加已知卡牌
            for card in sorted_known_cards[:max_cards]:
                deck.append({
                    'name': card['name'],
                    'known': True,
                    'image': f'卡面/{card["name"]}.png',
                    'card_id': None,
                    'cost': card['cost'],
                    'played': card['played']
                })
            
            # 填充未知卡牌到12张
            while len(deck) < max_cards:
                deck.append({
                    'name': '未知卡牌',
                    'known': False,
                    'image': None,
                    'card_id': None,
                    'cost': 99,
                    'played': False
                })
            
            print(f"构建的卡组大小: {len(deck)}")
            print("=== 构建敌方卡组完成 ===\n")
            
            return deck

        except Exception as e:
            print(f"构建敌方卡组失败: {e}")
            import traceback
            traceback.print_exc()
            return self._create_unknown_deck()


    def _create_unknown_deck(self):
        """创建一个全未知的卡组"""
        return [
            {
                'name': '未知卡牌',
                'known': False,
                'image': None,
                'card_id': None,
                'played': False
            }
            for _ in range(12)
        ]

    def _create_unknown_decks(self):
        """创建全未知的双方卡组"""
        unknown_deck = self._create_unknown_deck()
        return {
            'player_deck': unknown_deck,
            'enemy_deck': unknown_deck
        }

class MainWindow(QMainWindow):
    def __init__(self):
        try:
            print("\n=== 开始初始化主窗口 ===")
            super().__init__()

            # Windows 11 DPI 感知
            print("设置DPI感知...")
            if hasattr(QtCore.Qt, 'AA_EnableHighDpiScaling'):
                QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
            if hasattr(QtCore.Qt, 'AA_UseHighDpiPixmaps'):
                QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)

            print("设置窗口基本属性...")
            self.setWindowTitle("漫威终极逆转记牌器")
            self.setMinimumSize(600, 200)

            print("设置程序图标...")
            self.set_app_icon()

            print("初始化预设卡组...")
            self.preset_decks = {
                "专家预组": ["Cable", "Carnage", "Death", "DoctorOctopus", "Gladiator", "Killmonger", "Knull", "Magik", "ShangChi", "ThePhoenixForce", "Venom", "Yondu"],

                "德古拉园": ["Dracula", "RedSkull", "KaZar", "SwordMaster", "StrongGuy", "Infinaut", "Nightcrawler", "Blade", "SquirrelGirl", "BlueMarvel", "RocketRaccoon", "AntMan"],

                "王者归来": ["Hela", "GhostRider", "Gambit", "LadySif", "Jubilee", "Infinaut", "Odin", "Sandman", "Hulk", "IronMan", "SwordMaster", "Blade"],

                "平凡强者": ["Patriot", "Brood", "BlueMarvel", "Shocker", "Cyclops", "TheThing", "SquirrelGirl", "MistyKnight", "Forge", "MrSinister", "Hulk", "AmericaChavez"],

                "移动入门": ["Dagger", "HumanTorch", "AmericaChavez", "IronFist", "Kraven", "DoctorStrange", "Hulkbuster", "MultipleMan", "Cloak", "Vulture", "Vision", "Heimdall"],

                "新手推荐": ["BlueMarvel", "KaZar", "SwordMaster", "StrongGuy", "Bishop", "Angela", "Blade", "Dazzler", "SquirrelGirl", "Nightcrawler", "RocketRaccoon", "AntMan"],

                "进阶之选": ["Destroyer", "Spectrum", "ProfessorX", "Klaw", "Warpath", "MrFantastic", "Cosmo", "Lizard", "Colossus", "Armor", "BuckyBarnes", "AntMan"],

                "双倍力量": ["SheHulk", "DevilDinosaur", "MoonGirl", "Cable", "WhiteQueen", "Agent13", "TheCollector", "Sentinel", "Sunspot", "ShangChi", "Cosmo", "Enchantress"],

                "双倍揭示": ["Wong", "Ironheart", "WhiteTiger", "SpiderWoman", "Wolfsbane", "Odin", "Medusa", "Starlord", "RocketRaccoon", "Iceman", "Enchantress", "Scorpion"],
            }
            
            print("初始化基本组件...")
            self.use_preset_decks = False  # 是否使用预设卡组的标志
            self.deck_history = DeckHistory()
            self.image_cache = {}
            self.cards_map = {}  # 卡牌映射字典
            self.decks = {}  # 初始化 decks 字典
            self.monitor_thread = None  # 先初始化为 None

            try:
                print("设置任务管理器进程名称...")
                import ctypes
                ctypes.windll.kernel32.SetConsoleTitleW("小王记牌器")
            except Exception as e:
                print(f"设置进程名称失败: {e}")

            print("初始化子窗口状态...")
            self.player_window = None
            self.enemy_window = None
            self.player_window_open = False  # 我方牌库窗口的打开状态
            self.enemy_window_open = False   # 对手牌库窗口的打开状态

            print("加载卡牌名称映射...")
            self.name_mapping = {}  # 英文名到中文名的映射
            self.load_card_mapping()
            print("卡牌映射加载完成")

            print("加载样式表...")
            self.load_stylesheet()
            print("样式表加载完成")

            print("创建UI...")
            self.setup_ui()
            print("UI创建完成")

            print("加载卡组信息...")
            self.load_decks_info()
            print("卡组信息加载完成")

            print("创建子窗口...")
            self.create_sub_windows()
            print("子窗口创建完成")

            # 在这里添加：初始自动选择当前卡组
            if hasattr(self, 'auto_select_checkbox') and self.auto_select_checkbox.isChecked():
                self.auto_select_current_deck()

            print("创建系统托盘图标...")
            self.create_tray_icon()
            print("系统托盘创建完成")

            print("设置窗口标志和加载窗口设置...")
            try:
                self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowMinimizeButtonHint)
                self.settings = QSettings("MyCompany", "MyApp")
                self.load_window_settings()
            except Exception as e:
                print(f"加载窗口设置失败: {e}")

            print("初始化自动更新定时器...")
            self.auto_update_timer = QTimer()
            self.auto_update_timer.timeout.connect(self.check_auto_update)
            self.last_match_time = 0
            self.auto_update_interval = 800  # 固定为 0.8 秒
            self.match_cooldown = 3000  # 3秒冷却时间
            print("定时器初始化完成")

            print("启动自动更新定时器...")
            self.auto_update_timer.start(self.auto_update_interval)
            
            print("启动监控线程...")
            self.start_monitor_thread()
            print("监控线程启动完成")

            print("=== 主窗口初始化完成 ===\n")

        except Exception as e:
            print(f"\n!!! 主窗口初始化失败: {e}")
            import traceback
            traceback.print_exc()
            raise


    def set_app_icon(self):
        """设置程序图标"""
        try:
            # 获取图标路径
            if hasattr(sys, '_MEIPASS'):
                # PyInstaller 打包后的路径
                icon_path = os.path.join(sys._MEIPASS, 'ui', 'icon.ico')
            else:
                # 开发环境路径
                current_dir = os.path.dirname(os.path.abspath(__file__))
                icon_path = os.path.join(current_dir, '..', 'ui', 'icon.ico')
            
            if os.path.exists(icon_path):
                app_icon = QIcon(icon_path)
                
                # 设置应用程序图标
                QApplication.setWindowIcon(app_icon)
                
                # 设置主窗口图标
                self.setWindowIcon(app_icon)
                
                # 设置系统托盘图标
                if hasattr(self, 'tray_icon'):
                    self.tray_icon.setIcon(app_icon)
                    
                print(f"成功设置程序图标: {icon_path}")
            else:
                print(f"图标文件不存在: {icon_path}")
                self.setWindowIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon))
                
        except Exception as e:
            print(f"设置程序图标失败: {e}")
            self.setWindowIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon))

    def check_auto_update(self):
        """检查是否需要自动更新"""
        try:
            print("\n=== 开始自动更新检查 ===")
            
            # 检查是否有窗口打开
            print(f"窗口状态检查 - 玩家窗口: {self.player_window_open}, 对手窗口: {self.enemy_window_open}")
            if not (self.player_window_open or self.enemy_window_open):
                print("没有打开的窗口，跳过更新")
                return

            # 检查冷却时间
            current_time = time.time() * 1000  # 转换为毫秒
            time_since_last = current_time - self.last_match_time
            print(f"冷却时间检查 - 距离上次更新: {time_since_last:.2f}ms, 冷却时间: {self.match_cooldown}ms")
            
            if time_since_last < self.match_cooldown:
                print("在冷却时间内，跳过更新")
                return

            # 检查屏幕匹配
            print("开始检查屏幕匹配...")
            match_result = check_screen_match()
            print(f"屏幕匹配结果: {match_result}")
            
            if match_result:
                print("检测到屏幕匹配，更新时间戳")
                self.last_match_time = current_time
                print("创建延迟激活定时器")
                QTimer.singleShot(1000, self.activate_window)
            else:
                print("屏幕未匹配")

            print("=== 自动更新检查完成 ===\n")

        except Exception as e:
            print(f"\n!!! 自动更新检查失败: {e}")
            print("详细错误信息:")
            import traceback
            traceback.print_exc()

    def activate_window(self):
            """激活窗口"""
            try:
                if self.player_window_open:
                    try:
                        hwnd = int(self.player_window.winId())
                        if win32gui.IsWindow(hwnd):
                            shell = win32com.client.Dispatch("WScript.Shell")
                            shell.SendKeys('.')  # 使用波浪号键
                            win32gui.SetForegroundWindow(hwnd)
                            print("玩家窗口已激活")
                    except Exception as e:
                        print(f"激活玩家窗口失败: {e}")
                    
                elif self.enemy_window_open:
                    try:
                        hwnd = int(self.enemy_window.winId())
                        if win32gui.IsWindow(hwnd):
                            shell = win32com.client.Dispatch("WScript.Shell")
                            shell.SendKeys('.')  # 使用波浪号键
                            win32gui.SetForegroundWindow(hwnd)
                            print("对手窗口已激活")
                    except Exception as e:
                        print(f"激活对手窗口失败: {e}")

            except Exception as e:
                print(f"激活窗口失败: {e}")
                import traceback
                traceback.print_exc()

    def toggle_auto_update(self):
        """切换自动更新状态"""
        try:
            if self.auto_update_button.isChecked():
                self.auto_update_timer.start(self.auto_update_interval)
                self.auto_update_button.setText("取消自动更新")
                print(f"自动更新已开启，间隔: {self.auto_update_interval}ms")
            else:
                self.auto_update_timer.stop()
                self.auto_update_button.setText("自动更新")
                print(f"自动更新已关闭")
        except Exception as e:
            print(f"切换自动更新状态失败: {e}")

    def get_root_dir(self):
        """获取项目根目录路径"""
        current_dir = os.path.dirname(os.path.abspath(__file__))  # windows目录
        return os.path.dirname(current_dir)  # 返回项目根目录
    
    def get_style_path(self):
        """获取样式表路径"""
        root_dir = self.get_root_dir()
        return os.path.join(root_dir, 'ui', 'styles.qss')  # 从ui目录读取样式表


    def load_window_settings(self):
        """加载保存的窗口设置"""
        try:
            # 加载窗口大小
            player_size = self.settings.value("player_window_size")
            enemy_size = self.settings.value("enemy_window_size")

            # 加载列数设置
            saved_columns = self.settings.value("current_columns", 4, type=int)
            
            # 设置玩家窗口
            if self.player_window:
                if player_size and isinstance(player_size, QSize):
                    self.player_window.resize(player_size)
                self.player_window.current_columns = saved_columns
                self.player_window.layout_button.setText(f"{saved_columns}列")
                self.player_window.calculate_aspect_ratio(saved_columns)
                # 不调用 update_layout()，因为窗口还未显示

            # 设置对手窗口
            if self.enemy_window:
                if enemy_size and isinstance(enemy_size, QSize):
                    self.enemy_window.resize(enemy_size)
                self.enemy_window.current_columns = saved_columns
                self.enemy_window.layout_button.setText(f"{saved_columns}列")
                self.enemy_window.calculate_aspect_ratio(saved_columns)
                # 不调用 update_layout()，因为窗口还未显示

            # 加载窗口位置
            player_pos = self.settings.value("player_window_position")
            enemy_pos = self.settings.value("enemy_window_position")
            
            if player_pos and self.player_window:
                self.player_window.move(player_pos)
            if enemy_pos and self.enemy_window:
                self.enemy_window.move(enemy_pos)

        except Exception as e:
            print(f"加载窗口设置失败: {e}")


    def save_window_settings(self):
        """保存窗口设置"""
        try:
            if self.player_window:
                self.settings.setValue("player_window_size", self.player_window.size())
                self.settings.setValue("player_window_position", self.player_window.pos())
                self.settings.setValue("current_columns", self.player_window.current_columns)

            if self.enemy_window:
                self.settings.setValue("enemy_window_size", self.enemy_window.size())
                self.settings.setValue("enemy_window_position", self.enemy_window.pos())

        except Exception as e:
            print(f"保存窗口设置失败: {e}")

    def setup_ui(self):
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 主布局
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 2)
        main_layout.setSpacing(2)

        # 创建工具栏容器
        toolbar_frame = QFrame()
        toolbar_frame.setObjectName("mainFrame")    
        toolbar_layout = QVBoxLayout(toolbar_frame)
        toolbar_layout.setContentsMargins(10, 10, 10, 2)
        toolbar_layout.setSpacing(2)

        # 创建工具栏
        self.create_toolbar(toolbar_layout)


        watermark = ClickableLabel("作者：BiliBili Ayaya小王", "https://space.bilibili.com/2448140/")
        watermark.setObjectName("watermark")
            
        # 修改水印容器部分
        watermark_container = QWidget()
        watermark_layout = QHBoxLayout(watermark_container)
        watermark_layout.setContentsMargins(0, 0, 0, 0)  # 移除容器边距
        watermark_layout.setSpacing(10)  # 添加一些间距

        # 添加版本号标签
        version_label = QLabel("V1.05 时空闪烁")
        version_label.setObjectName("versionLabel")  # 用于CSS样式
        watermark_layout.addWidget(version_label)
        
        # 添加弹性空间
        watermark_layout.addStretch()
        
        # 添加作者信息
        watermark = ClickableLabel("作者：BiliBili Ayaya小王", "https://space.bilibili.com/2448140/")
        watermark.setObjectName("watermark")
        watermark_layout.addWidget(watermark)
        
        toolbar_layout.addWidget(watermark_container)

        # 将工具栏框架添加到主布局
        main_layout.addWidget(toolbar_frame)


    def open_bilibili_space(self):
        """打开B站空间"""
        url = "https://space.bilibili.com/2448140/"
        try:
            import webbrowser
            webbrowser.open(url)
        except Exception as e:
            print(f"打开B站空间失败: {e}")

    def create_toolbar(self, parent_layout):
        # 上排 - 卡组选择
        upper_widget = QWidget()
        upper_layout = QHBoxLayout(upper_widget)
        upper_layout.setContentsMargins(0, 0, 0, 0)
        upper_layout.setSpacing(8)

        deck_label = QLabel("我方卡组:")
        deck_label.setObjectName("controlLabel")

        # 添加预设卡组复选框
        self.preset_checkbox = QCheckBox("使用预组卡组")
        self.preset_checkbox.setObjectName("controlCheckbox")
        self.preset_checkbox.stateChanged.connect(self.toggle_preset_decks)

        # 添加自动选择卡组复选框
        self.auto_select_checkbox = QCheckBox("自动选择卡组")
        self.auto_select_checkbox.setObjectName("controlCheckbox")
        self.auto_select_checkbox.setChecked(True)  # 默认选中
        self.auto_select_checkbox.stateChanged.connect(self.toggle_auto_select)

        self.deck_selector = QComboBox()
        self.deck_selector.setObjectName("deckSelector")
        self.deck_selector.currentTextChanged.connect(self.on_deck_selected)
        self.deck_selector.setMinimumWidth(200)
        self.deck_selector.setEnabled(False)  # 默认禁用

        upper_layout.addWidget(deck_label)
        upper_layout.addWidget(self.deck_selector)
        upper_layout.addWidget(self.auto_select_checkbox)
        upper_layout.addWidget(self.preset_checkbox) #预组卡组呈现
        upper_layout.addStretch()

        # 下排 - 按钮控制
        lower_widget = QWidget()
        lower_layout = QHBoxLayout(lower_widget)
        lower_layout.setContentsMargins(0, 0, 0, 0)
        lower_layout.setSpacing(8)

        # 创建所有按钮
        self.toggle_player_window_button = QPushButton("打开我方牌库")
        self.toggle_enemy_window_button = QPushButton("打开对手牌库")
        self.auto_update_button = QPushButton("取消自动更新")
        self.force_update_button = QPushButton("刷新")

        self.clean_cache_button = QPushButton("清除缓存")
        self.clean_cache_button.clicked.connect(self.clean_snap_files)
        self.reset_button = QPushButton("重置牌库")
        self.reset_button.setObjectName("controlButton")
        self.reset_button.clicked.connect(self.reset_windows)

        # 设置按钮属性和连接信号
        self.toggle_player_window_button.setObjectName("windowButton")
        self.toggle_enemy_window_button.setObjectName("windowButton")
        self.auto_update_button.setObjectName("controlButton")
        self.force_update_button.setObjectName("controlButton")

        self.toggle_player_window_button.clicked.connect(self.toggle_player_window)
        self.toggle_enemy_window_button.clicked.connect(self.toggle_enemy_window)
        self.auto_update_button.setCheckable(True)
        self.auto_update_button.setChecked(True)
        self.auto_update_button.clicked.connect(self.toggle_auto_update)
        self.force_update_button.clicked.connect(self.force_update)

        # 添加按钮到下排布局
        lower_layout.addWidget(self.toggle_player_window_button)
        lower_layout.addWidget(self.toggle_enemy_window_button)
        lower_layout.addWidget(self.auto_update_button)
        lower_layout.addWidget(self.force_update_button)
        lower_layout.addWidget(self.clean_cache_button)
        lower_layout.addWidget(self.reset_button)  # 添加重置按钮
        lower_layout.addStretch()

        # 将上下两排添加到父布局
        parent_layout.addWidget(upper_widget)
        parent_layout.addWidget(lower_widget)


    def auto_select_current_deck(self):
        """自动选择当前正在使用的卡组"""
        try:
            # 读取当前选择的卡组ID
            user_home = os.path.expanduser('~')
            play_state_path = os.path.join(
                user_home,
                'AppData',
                'LocalLow',
                'NetEase',
                'SnapCN',
                'Standalone',
                'States',
                'prod',
                'PlayState.json'
            )
            
            with open(play_state_path, 'r', encoding='utf-8-sig') as f:
                play_state = json.load(f)
                current_deck_id = play_state['SelectedDeckId']['Value']
            
            # 在所有卡组中查找匹配的ID
            for deck_name, deck_info in self.decks.items():
                if deck_info.get('id') == current_deck_id:
                    # 找到匹配的卡组，设置为当前选择
                    self.deck_selector.setCurrentText(deck_name)
                    return
                    
            print(f"未找到ID为 {current_deck_id} 的卡组")
            
        except Exception as e:
            print(f"自动选择卡组失败: {e}")
            import traceback
            traceback.print_exc()

    def toggle_auto_select(self, state):
        """切换自动选择卡组状态"""
        if state:
            # 如果选中自动选择，取消预设卡组的选中状态
            self.preset_checkbox.setChecked(False)
            # 禁用卡组选择器
            self.deck_selector.setEnabled(False)
            # 自动选择当前卡组
            self.auto_select_current_deck()
        else:
            # 启用卡组选择器
            self.deck_selector.setEnabled(True)

    def reset_windows(self):
        """重置所有牌库窗口设置"""
        try:
            # 重置设置
            self.settings.remove("player_window_size")
            self.settings.remove("player_window_position")
            self.settings.remove("enemy_window_size")
            self.settings.remove("enemy_window_position")
            self.settings.remove("current_columns")
            
            # 重置列数
            default_columns = 4
            if self.player_window:
                self.player_window.current_columns = default_columns
                self.player_window.layout_button.setText(f"{default_columns}列")
                self.player_window.calculate_aspect_ratio(default_columns)
            if self.enemy_window:
                self.enemy_window.current_columns = default_columns
                self.enemy_window.layout_button.setText(f"{default_columns}列")
                self.enemy_window.calculate_aspect_ratio(default_columns)

            # 重置窗口大小
            initial_width = 4 * 120 + 3 * 10 + 2 * 10  # 4列卡片 + 3个间距 + 2个边距
            initial_height = 3 * 160 + 2 * 10 + 2 * 10 + 40  # 3行卡片 + 2个间距 + 2个边距 + 顶部按钮
            
            # 重置玩家窗口
            if self.player_window:
                self.player_window.resize(initial_width, initial_height)
                self.player_window.move(100, 100)  # 默认位置
                self.player_window.opacity = 1.0  # 重置透明度
                self.player_window.setWindowOpacity(1.0)
                self.player_window.update_opacity_label(1.0)
                
            # 重置对手窗口
            if self.enemy_window:
                self.enemy_window.resize(initial_width, initial_height)
                self.enemy_window.move(initial_width + 120, 100)  # 默认位置，在玩家窗口右边
                self.enemy_window.opacity = 1.0  # 重置透明度
                self.enemy_window.setWindowOpacity(1.0)
                self.enemy_window.update_opacity_label(1.0)

            # 更新布局
            if self.player_window and self.player_window.isVisible():
                self.player_window.update_layout()
            if self.enemy_window and self.enemy_window.isVisible():
                self.enemy_window.update_layout()

        except Exception as e:
            print(f"重置窗口失败: {e}")
            QMessageBox.warning(self, "重置失败", f"重置过程中发生错误：{str(e)}")
            import traceback
            traceback.print_exc()

    def clean_snap_files(self):
        # 先显示确认对话框
        confirm_box = QMessageBox()
        confirm_box.setWindowTitle("确认清除缓存")
        confirm_box.setText("注意：清理缓存后，读取不到卡组是正常现象，进入游戏修改你的任意卡组,或者开一把再回到软件刷新即可恢复正常。")
        confirm_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        confirm_box.setDefaultButton(QMessageBox.StandardButton.No)
        
        # 如果用户点击Yes，则继续执行清理操作
        if confirm_box.exec() == QMessageBox.StandardButton.Yes:
            try:
                # 获取当前用户的home目录
                user_home = os.path.expanduser('~')
                
                # 构建目标路径
                target_dir = os.path.join(user_home, 'AppData', 'LocalLow', 'NetEase', 'SnapCN', 'Standalone', 'States', 'prod')
                
                # 检查目录是否存在
                if not os.path.exists(target_dir):
                    print(f"目录不存在: {target_dir}")
                    return
                    
                # 获取目录下所有的.json文件
                deleted_files = []
                failed_files = []
                
                for file_name in os.listdir(target_dir):
                    if file_name.endswith('.json'):
                        file_path = os.path.join(target_dir, file_name)
                        try:
                            os.remove(file_path)
                            deleted_files.append(file_name)
                            print(f"<span style='color: green;'>成功删除: {file_name}</span>")
                        except Exception as e:
                            failed_files.append(file_name)
                            print(f"<span style='color: red;'>删除 {file_name} 时出错: {str(e)}</span>")
                
                # 显示结果消息
                message = "<div style='color: black;'>"
                if deleted_files:
                    message += f"<div style='color: green;'>成功删除文件:</div>"
                    message += f"<div style='color: blue;'>{', '.join(deleted_files)}</div><br>"
                if failed_files:
                    message += f"<div style='color: red;'>删除失败文件:</div>"
                    message += f"<div style='color: red;'>{', '.join(failed_files)}</div>"
                
                # 如果两个列表都为空，说明没有找到任何文件
                if not deleted_files and not failed_files:
                    message = "<div style='color: orange;'>没有找到需要清理的缓存文件</div>"
                    
                message += "</div>"
                    
                # 显示结果
                msg_box = QMessageBox()
                msg_box.setWindowTitle("清除缓存")
                msg_box.setText(message)
                msg_box.exec()
                        
            except Exception as e:
                error_message = f"<div style='color: red;'>清除缓存时发生错误:<br>{str(e)}</div>"
                msg_box = QMessageBox()
                msg_box.setWindowTitle("错误")
                msg_box.setText(error_message)
                msg_box.exec()
                print(f"发生错误: {str(e)}")

    def toggle_preset_decks(self, state):
        """切换使用预设卡组或文件卡组"""
        try:
            if state:
                # 如果选中预设卡组，取消自动选择的选中状态
                self.auto_select_checkbox.setChecked(False)
                
            self.use_preset_decks = bool(state)
            if self.monitor_thread:
                self.monitor_thread.use_preset_decks = self.use_preset_decks
                
            # 更新选择器
            self.update_deck_selector()
            self.deck_selector.setEnabled(True)  # 启用选择器
            
            # 获取当前选中的卡组
            current_deck = self.deck_selector.currentText()
            if current_deck:
                self.on_deck_selected(current_deck)
                
            print(f"切换{'预设' if self.use_preset_decks else '文件'}卡组模式")
            
        except Exception as e:
            print(f"切换卡组模式失败: {e}")
            import traceback
            traceback.print_exc()

    def _find_card_info(self, card_name):
        """在所有卡组中查找卡牌信息"""
        try:
            # 直接在所有卡组中查找中文名称
            for deck in self.decks.values():
                if isinstance(deck, dict) and 'cards' in deck:
                    for card in deck['cards']:
                        if card['name'] == card_name:  # 直接用中文名匹配
                            return card

            # 如果在卡组中找不到，则在完整的cards_info中查找
            for card_info in self.cards_info.values():
                if card_info['name'] == card_name:  # 用中文名匹配
                    return {
                        'name': card_name,
                        'image': f'卡面/{card_name}.png',
                        'card_id': card_info.get('card_id')
                    }

            # 如果都找不到，返回一个基本的卡牌信息
            return {
                'name': card_name,
                'image': f'卡面/{card_name}.png',
                'card_id': None
            }

        except Exception as e:
            print(f"查找卡牌信息失败: {e}")
            return None

    def force_update(self):
        """强制读取并更新UI"""
        try:
            # 保存当前的排除列表和游戏记录
            excluded_cards = set()
            current_cards = {'player': set(), 'enemy': set()}
            if self.enemy_window_open:
                excluded_cards = self.enemy_window.excluded_cards.copy()
                if self.monitor_thread:
                    current_cards = self.monitor_thread.current_game_cards.copy()

            # 重新读取卡组列表
            if not self.use_preset_decks:  # 只在使用文件卡组时重新读取
                print("重新读取卡组列表...")
                self.decks = get_snap_decks_info()
                
                # 更新选择器，保持当前选择
                current_text = self.deck_selector.currentText()
                self.deck_selector.blockSignals(True)  # 暂时阻止信号触发
                self.deck_selector.clear()
                self.deck_selector.addItems(self.decks.keys())
                if current_text in self.decks:
                    self.deck_selector.setCurrentText(current_text)
                self.deck_selector.blockSignals(False)  # 恢复信号

            # 获取当前选中的卡组
            current_deck = self.decks.get(self.deck_selector.currentText())
            if current_deck and self.monitor_thread:
                if self.monitor_thread.deck_history.is_player_deck_changed(current_deck):
                    print("检测到卡组变化，更新历史记录")
                    self.monitor_thread.deck_history.update_player_deck(current_deck)
                    self.monitor_thread.current_selected_deck = self.deck_selector.currentText()

                # 读取新的游戏状态
                game_state = load_game_state()
                if isinstance(game_state, str):
                    print(f"读取游戏状态失败: {game_state}")
                    return

                # 恢复之前的游戏记录和排除列表
                self.monitor_thread.current_game_cards = current_cards
                if self.enemy_window_open:
                    self.enemy_window.excluded_cards = excluded_cards
                    self.monitor_thread.current_game_cards['enemy'] = {
                        card for card in self.monitor_thread.current_game_cards['enemy']
                        if not (isinstance(card, str) and card in excluded_cards)
                    }

                # 处理新的游戏状态
                processed_data = self.monitor_thread.process_game_state(game_state)
                if processed_data and 'enemy_deck' in processed_data:
                    # 清理显示
                    if self.player_window_open:
                        self.player_window.clear_cards()
                    if self.enemy_window_open:
                        self.enemy_window.clear_cards()

                    # 更新显示
                    self.update_displays(processed_data)
                    print("强制更新完成")
                else:
                    print("处理游戏状态失败")

        except Exception as e:
            print(f"强制更新失败: {e}")
            import traceback
            traceback.print_exc()

    def create_sub_windows(self):
        """创建我方牌库和对手牌库的子窗口"""
        try:
            print("\n=== 开始创建子窗口 ===")
            
            print("创建玩家窗口...")
            self.player_window = PlayerWindow("我方牌库")
            print("创建对手窗口...")
            self.enemy_window = EnemyWindow("对手牌库", self.monitor_thread, self)  # 传入 self 作为 main_window
            if self.monitor_thread:
                self.enemy_window.monitor_thread = self.monitor_thread

            # 应用样式表
            print("应用样式表...")
            self.player_window.setStyleSheet(self.stylesheet)
            self.enemy_window.setStyleSheet(self.stylesheet)

            # 读取窗口位置
            print("读取保存的窗口位置...")
            settings = QSettings("MyCompany", "MyApp")
            player_pos = settings.value("player_window_position", None)
            enemy_pos = settings.value("enemy_window_position", None)

            print(f"玩家窗口位置: {player_pos}")
            print(f"对手窗口位置: {enemy_pos}")

            if player_pos:
                self.player_window.move(player_pos)
            if enemy_pos:
                self.enemy_window.move(enemy_pos)

            # 初始隐藏窗口
            print("隐藏窗口...")
            self.player_window.hide()
            self.enemy_window.hide()

            print("=== 子窗口创建完成 ===\n")
            
        except Exception as e:
            print(f"创建子窗口失败: {e}")
            import traceback
            traceback.print_exc()


    def toggle_player_window(self):
        """打开或关闭我方牌库窗口"""
        if self.player_window_open:
            self.player_window.hide()
            self.player_window_open = False
            self.toggle_player_window_button.setText("打开我方牌库")
        else:
            self.player_window.show()
            self.player_window_open = True
            self.toggle_player_window_button.setText("关闭我方牌库")
            # 打开窗口时自动刷新一次
            self.force_update()

    def toggle_enemy_window(self):
        """打开或关闭对手牌库窗口"""
        if self.enemy_window_open:
            self.enemy_window.hide()
            self.enemy_window_open = False
            self.toggle_enemy_window_button.setText("打开对手牌库")
        else:
            self.enemy_window.show()
            self.enemy_window_open = True
            self.toggle_enemy_window_button.setText("关闭对手牌库")
            # 打开窗口时自动刷新一次
            self.force_update()

    def change_update_interval(self, value):
        """改变更新频率"""
        if self.monitor_thread:
            self.monitor_thread.set_update_interval(value)
            print(f"更新频率已设置为 {value} ms")


    def load_card_mapping(self):
        """加载卡牌英文名到中文名的映射"""
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            # 获取上一级目录
            parent_dir = os.path.dirname(current_dir)
            json_path = os.path.join(parent_dir, 'cards.json')

            with open(json_path, 'r', encoding='utf-8') as f:
                cards_data = json.load(f)

            # 创建映射字典 (英文名到中文名)，并规范化名称
            # 只添加系列不为空的卡牌
            self.name_mapping = {
                card['card_id'].lower().replace(" ", "").replace("-", "").replace("_", ""): card['chinese_name']
                for card in cards_data
                if card.get('series') and card['series'].strip() != ''  # 检查series字段不为空
            }
            print(f"加载了 {len(self.name_mapping)} 个卡牌名称映射")

            # 创建卡牌信息字典，键为规范化后的英文名
            # 同样只添加系列不为空的卡牌
            self.cards_info = {
                card['card_id'].lower().replace(" ", "").replace("-", "").replace("_", ""): card
                for card in cards_data
                if card.get('series') and card['series'].strip() != ''  # 检查series字段不为空
            }

        except Exception as e:
            print(f"<span style='color: red;'>加载卡牌映射失败: {e}</span>")
            self.name_mapping = {}
            self.cards_info = {}

    def load_stylesheet(self):
        """加载样式表"""
        try:
            style_path = self.get_style_path()
            print(f"正在加载样式表: {style_path}")
            
            with open(style_path, 'r', encoding='utf-8') as f:
                self.stylesheet = f.read()  # 保存样式表内容为类属性
                
            # 应用样式表到主窗口
            self.setStyleSheet(self.stylesheet)
                    
        except Exception as e:
            print(f"加载样式表失败: {e}")
            self.stylesheet = ""

    def refresh_decks(self):
        """刷新卡组列表"""
        try:
            self.decks = get_snap_decks_info()
            self.deck_selector.clear()

            # 添加卡组到选择器
            for deck_name in self.decks.keys():
                self.deck_selector.addItem(deck_name)

            # 如果有卡组，选择第一个
            if self.decks:
                first_deck = next(iter(self.decks.keys()))
                self.deck_selector.setCurrentText(first_deck)
                self.deck_history.update_player_deck(self.decks[first_deck])

            print(f"已刷新卡组，找到 {len(self.decks)} 个卡组")
        except Exception as e:
            print(f"刷新卡组失败: {e}")
            import traceback
            traceback.print_exc()

    def load_decks_info(self):
        """加载卡组信息"""
        try:
            print("开始加载卡组信息...")
            self.decks = get_snap_decks_info()
            print(f"成功加载了 {len(self.decks)} 个卡组")
            self.update_deck_selector()
            print("load_decks_info执行完毕")
        except Exception as e:
            print(f"加载卡组信息失败: {e}")
            import traceback
            traceback.print_exc()
            self.decks = {}

    def update_deck_selector(self):
        """更新卡组选择器"""
        try:
            print("\n=== 开始更新卡组选择器 ===")
            if hasattr(self, 'deck_selector'):
                self.deck_selector.clear()
                print("清除现有卡组")
                
                if self.use_preset_decks:
                    # 使用预设卡组
                    deck_names = list(self.preset_decks.keys())
                    print(f"使用预设卡组，找到 {len(deck_names)} 个卡组")
                else:
                    # 使用文件卡组
                    self.decks = get_snap_decks_info()
                    deck_names = list(self.decks.keys())
                    print(f"使用文件卡组，找到 {len(deck_names)} 个卡组")
                
                print("添加的卡组:", deck_names)
                self.deck_selector.addItems(deck_names)
                
                if deck_names:
                    print(f"设置当前卡组: {deck_names[0]}")
                    self.deck_selector.setCurrentText(deck_names[0])
                    print("触发卡组选择事件")
                    self.on_deck_selected(deck_names[0])
                    
                print("卡组选择器更新完成")
                
        except Exception as e:
            print(f"更新卡组选择器失败: {str(e)}")
            import traceback
            traceback.print_exc()



    def on_deck_selected(self, deck_name):
        """处理卡组选择事件"""
        try:
            print(f"\n=== 处理卡组选择: {deck_name} ===")
            
            # 更新玩家窗口的卡组选择器
            if self.player_window and self.player_window.isVisible():
                # 使用 PlayerWindow 的 deck_selector 直接设置
                self.player_window.deck_selector.setCurrentText(deck_name)
            
            if self.use_preset_decks:
                print("使用预设卡组模式")
                if deck_name in self.preset_decks:
                    # 构建预设卡组数据
                    preset_deck = {
                        'name': deck_name,
                        'cards': []
                    }
                    
                    print(f"构建预设卡组 '{deck_name}'")
                    # 使用卡牌映射转换为中文名
                    for card_id in self.preset_decks[deck_name]:
                        normalized_id = card_id.lower().replace(" ", "").replace("-", "").replace("_", "")
                        if normalized_id in self.name_mapping:
                            chinese_name = self.name_mapping[normalized_id]
                            card_info = {
                                'name': chinese_name,
                                'card_id': card_id,
                                'image': f'卡面/{chinese_name}.png',
                                'known': True,
                                'played': False
                            }
                            preset_deck['cards'].append(card_info)
                            print(f"添加卡牌: {chinese_name}")
                    
                    print(f"预设卡组构建完成，包含 {len(preset_deck['cards'])} 张卡牌")
                    
                    # 更新到 decks 字典和监控线程
                    self.decks[deck_name] = preset_deck
                    if self.monitor_thread:
                        print("更新监控线程信息")
                        self.monitor_thread.decks = self.decks.copy()
                        self.monitor_thread.current_selected_deck = deck_name
                        self.monitor_thread.use_preset_decks = True
                        self.monitor_thread.clear_history()
                    
                    # 更新历史记录
                    print("更新卡组历史记录")
                    self.deck_history.update_player_deck(preset_deck)
                    
            else:
                print("使用文件卡组模式")
                if deck_name in self.decks:
                    print(f"更新历史记录: {deck_name}")
                    self.deck_history.update_player_deck(self.decks[deck_name])
                    if self.monitor_thread:
                        print("更新监控线程信息")
                        self.monitor_thread.current_selected_deck = deck_name
                        self.monitor_thread.use_preset_decks = False
                        self.monitor_thread.clear_history()
            
            # 清除并重新创建显示
            print("清理显示...")
            if self.player_window_open:
                print("清理玩家窗口")
                self.player_window.clear_cards()
            if self.enemy_window_open:
                print("清理对手窗口")
                self.enemy_window.clear_cards()
            
            # 打印当前卡组信息
            if deck_name in self.decks:
                deck = self.decks[deck_name]
                print(f"\n当前选择的卡组: {deck_name}")
                print(f"卡牌数量: {len(deck['cards'])}")
                for card in deck['cards']:
                    print(f"卡牌: {card['name']} - {card.get('image', '无图片')}")
            
            print("强制更新显示")
            self.force_update()
            print("=== 卡组选择处理完成 ===\n")
            
        except Exception as e:
            print(f"选择卡组失败: {str(e)}")
            import traceback
            traceback.print_exc()

    def toggle_monitoring(self):
        """切换记牌状态"""
        if self.monitor_thread and self.monitor_thread.is_running:
            self.monitor_thread.stop()
            self.monitor_thread.wait()  # 等待线程结束
            self.monitor_button.setText("开始记牌")
        else:
            if self.monitor_thread:
                self.monitor_thread.is_running = True
                self.monitor_thread.start()
            else:
                self.start_monitor_thread()
            self.monitor_button.setText("停止记牌")

    def check_auto_select(self):
        """检查是否需要自动选择卡组"""
        if hasattr(self, 'auto_select_checkbox') and self.auto_select_checkbox.isChecked():
            print("检测到新的一局，更新自动选择卡组")
            self.auto_select_current_deck()

    def start_monitor_thread(self):
        """启动监控线程"""
        try:
            print("准备启动监控线程...")
            self.monitor_thread = MonitorThread(self.decks, self.cards_info, self.name_mapping, self.auto_update_interval)
            self.monitor_thread.processed_data_signal.connect(self.update_displays)
            self.monitor_thread.update_auto_select_signal.connect(self.check_auto_select)
            self.monitor_thread.current_selected_deck = self.deck_selector.currentText()
            
            # 同步预设卡组状态
            self.monitor_thread.use_preset_decks = self.use_preset_decks
            self.monitor_thread.preset_decks = self.preset_decks.copy()
            
            # 设置到 enemy_window
            if hasattr(self, 'enemy_window') and self.enemy_window:
                self.enemy_window.monitor_thread = self.monitor_thread
            
            print("开始运行监控线程...")
            self.monitor_thread.is_running = True
            self.monitor_thread.start()
            print("监控线程启动完成")
            
        except Exception as e:
            print(f"启动监控线程失败: {e}")
            import traceback
            traceback.print_exc()

    def update_displays(self, game_info):
        if game_info:
            start_time = time.time()
            if self.player_window_open:
                self.player_window.update_display(game_info['player_deck'])
            if self.enemy_window_open:
                self.enemy_window.update_display(game_info['enemy_deck'])
            end_time = time.time()
            print(f"UI 更新耗时: {end_time - start_time:.4f} 秒")


    def create_tray_icon(self):
        """创建系统托盘图标"""
        try:
            print("\n=== 创建系统托盘 ===")
            
            # 延迟创建系统托盘图标
            def setup_tray():
                try:
                    # 如果已经存在，先清理旧的托盘图标
                    if hasattr(self, 'tray_icon'):
                        self.tray_icon.hide()
                        self.tray_icon.deleteLater()
                    if hasattr(self, 'tray_menu'):
                        self.tray_menu.clear()
                        self.tray_menu.deleteLater()

                    # 创建新的托盘图标和菜单
                    self.tray_icon = QSystemTrayIcon(self)
                    self.tray_menu = QMenu()

                    # 设置图标
                    icon = self.windowIcon()
                    if not icon.isNull():
                        self.tray_icon.setIcon(icon)
                    else:
                        # 使用系统默认图标
                        self.tray_icon.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon))

                    # 创建菜单项
                    show_action = QAction("显示主程序", self)
                    show_action.triggered.connect(self.show)
                    
                    quit_action = QAction("退出程序", self)
                    quit_action.triggered.connect(self.exit_app)

                    # 添加菜单项
                    self.tray_menu.addAction(show_action)
                    self.tray_menu.addSeparator()
                    self.tray_menu.addAction(quit_action)

                    # 设置菜单
                    self.tray_icon.setContextMenu(self.tray_menu)

                    # 使用单击事件而不是 activated 信号
                    def on_tray_clicked(reason):
                        if reason == QSystemTrayIcon.ActivationReason.Trigger:
                            if not self.isVisible():
                                self.show()
                                self.activateWindow()
                            else:
                                self.hide()

                    self.tray_icon.activated.connect(on_tray_clicked)

                    # 显示托盘图标
                    if QSystemTrayIcon.isSystemTrayAvailable():
                        self.tray_icon.show()
                        print("系统托盘创建成功")
                    else:
                        print("系统不支持托盘图标")

                except Exception as e:
                    print(f"设置托盘图标失败: {e}")
                    import traceback
                    traceback.print_exc()

            # 使用 QTimer 延迟创建托盘图标
            QTimer.singleShot(100, setup_tray)
            print("=== 系统托盘创建完成 ===\n")

        except Exception as e:
            print(f"创建系统托盘失败: {e}")
            import traceback
            traceback.print_exc()

    def on_tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.show()


    def tray_icon_activated(self, reason):
        """处理托盘图标的激活事件"""
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            # 如果窗口被最小化或隐藏，则显示并恢复窗口
            if not self.isVisible() or self.isMinimized():
                self.showNormal()  # 使用 showNormal 而不是 show
                self.activateWindow()
                self.raise_()
            else:
                self.hide()
        elif reason == QSystemTrayIcon.ActivationReason.MiddleClick:
            self.tray_menu.popup(QCursor.pos())

    def changeEvent(self, event):
        """处理窗口状态改变事件"""
        if event.type() == QEvent.Type.WindowStateChange:
            if self.windowState() & Qt.WindowState.WindowMinimized:
                event.ignore()
                self.hide()
                self.tray_icon.showMessage(
                    "漫威终极逆转记牌器",
                    "程序已最小化到系统托盘",
                    QSystemTrayIcon.MessageIcon.Information,
                    2000
                )
            else:
                super().changeEvent(event)


    def closeEvent(self, event):
        """处理窗口关闭事件"""
        try:
            # 检查是否来自系统托盘的关闭操作
            if not self.isVisible():
                # 已经是隐藏状态，说明是从系统托盘关闭
                self.force_close()
                event.accept()
                return

            # 检查鼠标位置是否在任务栏区域
            cursor_pos = QCursor.pos()
            # 获取主屏幕
            screen = QApplication.primaryScreen()
            screen_geometry = screen.geometry()
            
            # 判断鼠标是否在屏幕底部任务栏区域
            is_in_taskbar = cursor_pos.y() >= screen_geometry.height() - 50  # 假设任务栏高度约为50像素

            if is_in_taskbar:
                # 如果是从任务栏关闭，则强制退出
                self.force_close()
                event.accept()
            else:
                # 否则最小化到系统托盘
                self.hide()
                event.ignore()

        except Exception as e:
            print(f"处理关闭事件失败: {e}")
            self.force_close()
            event.accept()

    def force_close(self):
        """强制关闭程序"""
        try:
            # 保存窗口设置
            self.save_window_settings()

            # 停止监控线程
            if self.monitor_thread:
                self.monitor_thread.stop()
                self.monitor_thread.wait()

            # 关闭所有窗口
            if self.player_window:
                self.player_window.close()
                self.player_window.deleteLater()
            if self.enemy_window:
                self.enemy_window.close()
                self.enemy_window.deleteLater()

            # 清理系统托盘
            if hasattr(self, 'tray_menu'):
                self.tray_menu.clear()  # 清除菜单项
                self.tray_menu.deleteLater()
            if hasattr(self, 'tray_icon'):
                self.tray_icon.hide()
                self.tray_icon.deleteLater()

            # 确保主窗口也被关闭
            self.close()
            self.deleteLater()

            # 退出应用
            QApplication.processEvents()  # 处理所有待处理的事件
            QApplication.quit()

        except Exception as e:
            print(f"强制关闭程序失败: {e}")
            QApplication.quit()


    def exit_app(self):
        """退出程序"""
        try:
            # 保存窗口位置
            settings = QSettings("MyCompany", "MyApp")
            if self.player_window:
                settings.setValue("player_window_position", self.player_window.pos())
            if self.enemy_window:
                settings.setValue("enemy_window_position", self.enemy_window.pos())

            # 调用强制关闭方法
            self.force_close()

        except Exception as e:
            print(f"退出程序失败: {e}")
            QApplication.quit()

class ClickableLabel(QLabel):
    def __init__(self, text, url, parent=None):
        super().__init__(text, parent)
        self.url = url
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            try:
                import webbrowser
                webbrowser.open(self.url)
            except Exception as ex:
                print(f"打开链接失败: {ex}")
        super().mousePressEvent(event)