import os
import json
import time
from datetime import datetime

CURRENT_ENEMY = {
    'name': None,
    'deck': set()
}


def update_deck_info(data):
    """更新牌库信息，只收集原始卡组的卡牌"""
    remote_game = data.get('RemoteGame', {})
    game_state = remote_game.get('GameState', {})
    players = game_state.get('Players', [])
    local_account_id = remote_game.get('ClientPlayerInfo', {}).get('AccountId')
    
    # 寻找对手信息
    enemy_player = None
    for player in players:
        if player.get('AccountId') != local_account_id:
            enemy_player = player
            break
    
    if not enemy_player:
        return None
    
    enemy_name = enemy_player.get('Name')
    if not enemy_name:
        return None
    
    # 如果对手变了，清空牌库
    if enemy_name != CURRENT_ENEMY['name']:
        CURRENT_ENEMY['name'] = enemy_name
        CURRENT_ENEMY['deck'] = set()
    
    # 收集本局游戏中出现的所有原始卡牌（非创建的卡牌）
    for card in game_state.get('enemy_cards', []):
        # 检查卡牌是否是创建的
        if not card.get('CreatedByCardDefId'):  # 如果不是被其他卡创建的
            CURRENT_ENEMY['deck'].add(card['name'])
    
    return {
        'player_name': enemy_name,
        'known_cards': list(CURRENT_ENEMY['deck']),
        'cards_remaining': 12 - len(CURRENT_ENEMY['deck'])
    }

def find_players(data):
    """Find and identify players"""
    remote_game = data.get('RemoteGame', {})
    game_state = remote_game.get('GameState', {})
    players = game_state.get('Players', [])
    local_account_id = remote_game.get('ClientPlayerInfo', {}).get('AccountId')
    
    local_id = None
    enemy_id = None
    
    for player in players:
        player_id = player.get('$id')
        account_id = player.get('AccountId')
        
        if account_id == local_account_id:
            local_id = player_id
        else:
            enemy_id = player_id
    
    return local_id, enemy_id

def find_card_owner(data, card_name, local_id, enemy_id):
    """Find card ownership and creation information"""
    def search_card_in_dict(d, card_name):
        if isinstance(d, dict):
            if d.get('CardDefId') == card_name:
                card_info = {
                    'owner': None,
                    'created_by': d.get('CreatedByCardDefId'),
                    'turn_revealed': d.get('TurnRevealed')
                }
                
                owner = d.get('Owner', {})
                owner_ref = owner.get('$ref')
                # 打印调试信息
                #print(f"Card: {card_name}, Owner ref: {owner_ref}, Local id: {local_id}")
                if owner_ref:
                    if owner_ref == local_id:
                        card_info['owner'] = "我方"
                    else:
                        card_info['owner'] = "敌方"
                
                return card_info
            
            for v in d.values():
                result = search_card_in_dict(v, card_name)
                if result:
                    return result
                
        elif isinstance(d, list):
            for item in d:
                result = search_card_in_dict(item, card_name)
                if result:
                    return result
        
        return None

    result = search_card_in_dict(data, card_name)
    
    if result:
        owner = result['owner'] or "未知"
        created_by = result['created_by']
        turn_revealed = result['turn_revealed']
        
        owner_str = f"{owner}"
        if created_by:
            owner_str += f" (由 {created_by} 创建)"
        if turn_revealed:
            owner_str += f" [回合 {turn_revealed}]"
            
        return owner_str
    return "未知"

def get_card_location(card, zone_id, location_name=""):
    if 'CardDefId' in card:
        card_name = card.get('CardDefId')
        created_by = None
        if card.get('CreatedByCardDefId'):
            created_by = card.get('CreatedByCardDefId')
        if card.get('CreatedByLocationDefId'):
            created_by = card.get('CreatedByLocationDefId')
            
        card_info = {
            'card_id': card.get('EntityId'),
            'name': card_name,
            'zone': zone_id,
            'location': location_name,
            'power': card.get('Power', {}).get('Value', 0),
            'cost': card.get('Cost', {}).get('Value', 0),
            'revealed': card.get('Revealed', False),
            'created_by': created_by
        }
        return card_info
    return None

def get_game_state(data):
    cards = []
    
    def search_cards(obj):
        if isinstance(obj, dict):
            if "CardDefId" in obj and obj["CardDefId"] and "Owner" in obj:
                # 检查是否有createdby相关字段
                if not any(key for key in obj.keys() if 'CreatedBy' in key):
                    print(f"\n发现卡牌 {obj['CardDefId']}:")
                    
                    # 直接从顶层获取 CardBackDefId
                    card_back_id = obj.get("CardBackDefId")
                    print(f"直接从顶层读取的CardBackDefId: {card_back_id}")
                    
                    cards.append({
                        'name': obj["CardDefId"],
                        'owner_ref': obj["Owner"].get("$ref"),
                        'card_back_id': card_back_id
                    })
                    print(f"添加到cards列表的信息: {cards[-1]}\n")
            
            for value in obj.values():
                search_cards(value)
                
        elif isinstance(obj, list):
            for item in obj:
                search_cards(item)
    
    search_cards(data)
    print(f"\n最终收集到的所有卡牌信息:")
    for card in cards:
        print(f"卡牌: {card['name']}, 所有者ref: {card['owner_ref']}, 卡背ID: {card['card_back_id']}")
    
    return cards



# def get_game_state(data):
#     remote_game = data.get('RemoteGame', {})
#     game_state = remote_game.get('GameState', {})
#     cards_played = remote_game.get('ClientPlayerInfo', {}).get('CardsPlayed', [])
#     card_owners = {}
#     cards_dict = {}
    
#     def process_card_list(card_list, zone_name, location_name=None, path="unknown"):
#         if not card_list:
#             return
                
#         for card in card_list:
#             if not isinstance(card, dict):
#                 continue
                
#             if 'CreatedByLocationDefId' in card or 'CreatedByCardDefId' in card:
#                 continue
                
#             card_info = get_card_location(card, zone_name, location_name)
#             if card_info:
#                 if card_info['card_id']:
#                     card_key = f"{card_info['name']}_{card_info['card_id']}"
#                 else:
#                     card_key = f"{card_info['name']}_{zone_name}_{location_name}_{path}"
                
#                 if card_key not in cards_dict:
#                     cards_dict[card_key] = []
                    
#                 cards_dict[card_key].append(card_info)

#     for card in cards_played:
#         owner = find_card_owner(data, card, None, None)
#         card_owners[card] = owner
        
#     for i, player in enumerate(game_state.get('Players', [])):
#         for staged_idx, staged in enumerate(player.get('CardsStaged', [])):
#             if 'Card' in staged and 'Zone' in staged['Card']:
#                 card_zone = staged['Card']['Zone']
#                 for player_cards in ['Player1Cards', 'Player2Cards']:
#                     if player_cards in card_zone:
#                         path = f"Players[{i}].CardsStaged[{staged_idx}].Card.Zone.{player_cards}"
#                         process_card_list(card_zone.get(player_cards, []), 'Staged', None, path)
            
#             to_data = staged.get('To', {})
#             for player_cards in ['Player1Cards', 'Player2Cards']:
#                 path = f"Players[{i}].CardsStaged[{staged_idx}].To.{player_cards}"
#                 process_card_list(to_data.get(player_cards, []), 'Staged', None, path)
            
#         zones = ['Hand', 'Deck', 'Graveyard']
#         for zone in zones:
#             zone_data = player.get(zone, {})
#             path = f"Players[{i}].{zone}"
#             process_card_list(zone_data.get('Cards', []), zone, None, path)
    
#     for loc_idx, location in enumerate(game_state.get('Locations', [])):
#         location_name = location.get('LocationDefId', "")
#         for player_cards in ['Player1Cards', 'Player2Cards']:
#             path = f"Locations[{loc_idx}].{player_cards}"
#             process_card_list(location.get(player_cards, []), 'Location', location_name, path)
    
#     result_items = (game_state.get('ClientResultMessage', {})
#                    .get('GameResultAccountItems', []))
#     for item_idx, item in enumerate(result_items):
#         path = f"ClientResultMessage.GameResultAccountItems[{item_idx}].Deck"
#         process_card_list(item.get('Deck', {}).get('Cards', []), 'ResultDeck', None, path)

#     cards = []
#     for card_id, card_infos in cards_dict.items():
#         card_infos = [info for info in card_infos if not info.get('created_by')]
        
#         if not card_infos:
#             continue
            
#         best_info = None
#         max_info_count = 0
        
#         for info in card_infos:
#             info_count = sum(1 for v in info.values() if v is not None and v != 0 and v != '')
#             if info_count > max_info_count:
#                 max_info_count = info_count
#                 best_info = info.copy()
        
#         if best_info:
#             cards.append(best_info)

#     return {
#         'cards': cards,
#         'cards_played': cards_played,
#         'card_owners': card_owners,
#     }

def print_game_state(game_state, data):
    print("\n当前游戏状态:")
    print("-" * 50)
    
    # 分类存储场上卡牌
    my_board_cards = []
    enemy_board_cards = []
    
    # 处理历史记录中的卡牌
    for card in game_state['cards_played']:
        owner_info = game_state['card_owners'][card]
        # 只处理非创建的卡牌
        if "创建" not in owner_info:
            if "我方" in owner_info:
                my_board_cards.append((card, owner_info))
            elif "敌方" in owner_info:
                enemy_board_cards.append((card, owner_info))
    
    # 打印场上卡牌
    print("\n场上卡牌:")
    if my_board_cards:
        print("\n我方场上:")
        for card, info in my_board_cards:
            print(f"- {card} - {info}")
    
    if enemy_board_cards:
        print("\n敌方场上:")
        for card, info in enemy_board_cards:
            print(f"- {card} - {info}")
    # 处理双方卡牌信息
    deck_info = update_deck_info(data)
    if deck_info:
        print("\n对手牌库统计:")
        print(f"对手名称: {deck_info['player_name']}")
        print(f"已知卡牌 ({len(deck_info['known_cards'])}/12):")
        # 只显示非创建的卡牌
        original_cards = [card for card in sorted(deck_info['known_cards']) if not any(c.get('CreatedByCardDefId') for c in game_state['enemy_cards'] if c['name'] == card)]
        for card in original_cards:
            print(f"- {card}")
        remaining = 12 - len(original_cards)
        if remaining > 0:
            print(f"\n未知卡牌: {remaining}张")
    
    print("-" * 50)


    def get_cards_by_category(cards):
        hand_cards = []
        board_cards = []
        discarded_cards = []
        destroyed_cards = []
        deck_cards = []
        
        for card in cards:
            # 跳过被创建的卡牌
            if card.get('created_by'):
                continue
                
            if card['zone'] == 'Hand':
                hand_cards.append(card)
            elif card['zone'] == 'Location':
                board_cards.append(card)
            elif card['zone'] == 'Deck':
                deck_cards.append(card)
            elif card['zone'] == 'Graveyard':
                if card['revealed']:
                    destroyed_cards.append(card)
                else:
                    discarded_cards.append(card)
        
        return {
            'hand': hand_cards,
            'board': board_cards,
            'discarded': discarded_cards,
            'destroyed': destroyed_cards,
            'deck': deck_cards
        }

    def print_card_list(cards, category_name):
        if cards:
            print(f"\n{category_name}:")
            for card in cards:
                info = f"{card['name']} (ID: {card['card_id']})"
                if card['location']:
                    info += f" 在 {card['location']}"
                if card['revealed']:
                    info += f" | 费用: {card['cost']}, 战力: {card['power']}"
                print(info)

    # 处理我方卡牌
    print("\n我方卡牌:")
    my_cards = get_cards_by_category(game_state['local_cards'])
    print_card_list(my_cards['hand'], "手牌")
    print_card_list(my_cards['board'], "场上")
    print_card_list(my_cards['discarded'], "已丢弃")
    print_card_list(my_cards['destroyed'], "已摧毁")
    print_card_list(my_cards['deck'], "牌组")

    # 处理对方卡牌
    print("\n对方卡牌:")
    enemy_cards = get_cards_by_category(game_state['enemy_cards'])
    print_card_list(enemy_cards['hand'], "手牌")
    print_card_list(enemy_cards['board'], "场上")
    print_card_list(enemy_cards['discarded'], "已丢弃")
    print_card_list(enemy_cards['destroyed'], "已摧毁")
    print_card_list(enemy_cards['deck'], "牌组")

    print("-" * 50)
def monitor_game_state():
    user_home = os.path.expanduser('~')
    target_path = os.path.join(
        user_home,
        'AppData',
        'LocalLow',
        'NetEase',
        'SnapCN',
        'Standalone',
        'States',
        'prod',
        'GameState.json'
    )
    
    if not os.path.exists(target_path):
        print("GameState.json not found")
        return
    
    print("开始监测游戏状态...")
    print("程序将持续运行，按 Ctrl+C 终止")
    print("-" * 50)

    last_game_state = None

    try:
        while True:
            try:
                with open(target_path, 'r', encoding='utf-8-sig') as file:
                    data = json.load(file)
                    find_psylocke_in_graveyard(data)
                    game_state = get_game_state(data)
                    if game_state != last_game_state:
                        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        print(f"\n[{current_time}] 检测到游戏状态更新:")
                        print_game_state(game_state, data)  # 传入data参数
                        last_game_state = game_state
                        
            except Exception as e:
                print(f"Error reading file: {e}")
            
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n程序已终止")
        
def find_psylocke_in_graveyard(data):
    """通过搜索CardDefId来定位Psylocke"""
    print("\n========= Mystique 详细信息 =========")
    
    def search_psylocke(d, path=""):
        if isinstance(d, dict):
            if d.get('CardDefId') == 'Mystique':
                if "Graveyard" in path or "CardsStaged" in path:
                    print(f"路径: {path}")
                    print("关键信息:")
                    print(f"- Owner引用: {d.get('Owner', {}).get('$ref')}")
                    print(f"- EntityId: {d.get('EntityId')}")
                    print(f"- Zone引用: {d.get('Zone', {}).get('$ref')}")
                    print(f"- PreviousZone引用: {d.get('PreviousZone', {}).get('$ref')}")
            
            for k, v in d.items():
                new_path = f"{path}.{k}" if path else k
                search_psylocke(v, new_path)
                
        elif isinstance(d, list):
            for i, item in enumerate(d):
                new_path = f"{path}[{i}]"
                search_psylocke(item, new_path)
    
    search_psylocke(data)
    print("===================================")


def load_game_state(game_state_path=None):
    """
    Read the game state file

    Args:
        game_state_path: Path to GameState.json; if None, use default path

    Returns:
        dict: Game state data or error message as a string
    """
    try:
        # Set default path
        if game_state_path is None:
            user_home = os.path.expanduser('~')
            game_state_path = os.path.join(
                user_home, 'AppData', 'LocalLow', 'NetEase', 'SnapCN',
                'Standalone', 'States', 'prod', 'GameState.json'
            )

        if not os.path.exists(game_state_path):
            return f"GameState.json not found at path: {game_state_path}"

        with open(game_state_path, 'r', encoding='utf-8-sig') as file:
            data = json.load(file)
            return data

    except Exception as e:
        return f"Error reading game state: {str(e)}"



def parse_game_cards(data):
    try:
        print("\n[DEBUG] =============== 开始解析卡牌 ===============")
        cards = get_game_state(data)
        cards_info = []
        
        for card in cards:
            card_info = {
                'name': card['name'],
                'status': 'board',  # 默认都是board状态
                'owner_id': card['owner_ref'],
                'created_by': None,  # 已经在get_game_state中过滤掉了created_by的卡牌
                'card_back_id': card['card_back_id']  # 添加卡背ID
            }
            
            # 打印调试信息
            if card['card_back_id']:
                print(f"[DEBUG] 卡牌 {card['name']} 的卡背ID: {card['card_back_id']}")
                
            cards_info.append(card_info)
        
        print("\n[DEBUG] =============== 解析卡牌结束 ===============")
        return cards_info
        
    except Exception as e:
        print(f"[ERROR] Exception in parse_game_cards: {str(e)}")
        print("[DEBUG] =============== 解析卡牌异常结束 ===============")
        return f"Error parsing game cards: {str(e)}"

def get_player_info(data):
    def find_players(obj, parent_key=None, parent_obj=None):
        players = {}  # {name: {'ids': set(), 'cardback': None}}
        
        if isinstance(obj, dict):
            # 如果父级key是Deck，直接返回
            #
            # if parent_key in ['Deck', 'ClanIdentity']:
            if parent_key in ['ClanIdentity']:
                return players
            
            # 检查当前层级是否有name和id
            name = obj.get('Name')
            player_id = obj.get('$id')
            
            # 查找CardBack下的CardBackDefId
            cardback = obj.get('CardBack', {})
            cardback_id = cardback.get('CardBackDefId') if isinstance(cardback, dict) else None
            
            if name and player_id:
                if name not in players:
                    players[name] = {'ids': set(), 'cardback': None}
                players[name]['ids'].add(player_id)
                
                # 检查父对象的同级节点的ID
                if parent_obj is not None:
                    parent_id = parent_obj.get('$id')
                    if parent_id:
                        players[name]['ids'].add(parent_id)
                
                # 如果在当前位置找到了卡背ID，保存它
                if cardback_id is not None:
                    players[name]['cardback'] = cardback_id
            
            # 递归处理所有值
            for key, value in obj.items():
                sub_players = find_players(value, key, obj)  # 传入当前对象作为父对象
                for sub_name, info in sub_players.items():
                    if sub_name not in players:
                        players[sub_name] = {'ids': set(), 'cardback': None}
                    players[sub_name]['ids'].update(info['ids'])
                    if players[sub_name]['cardback'] is None:
                        players[sub_name]['cardback'] = info['cardback']
                    
        elif isinstance(obj, list):
            for item in obj:
                sub_players = find_players(item, parent_key, parent_obj)
                for name, info in sub_players.items():
                    if name not in players:
                        players[name] = {'ids': set(), 'cardback': None}
                    players[name]['ids'].update(info['ids'])
                    if players[name]['cardback'] is None:
                        players[name]['cardback'] = info['cardback']
                    
        return players

    try:
        # 查找所有玩家
        players = find_players(data)
        
        # 检查玩家数量
        if len(players) > 2:
            print(f"警告: 找到超过2个玩家: {list(players.keys())}")
        
        # 获取本地玩家accountId用于区分本地和敌方玩家
        local_account_id = data.get('RemoteGame', {}).get('ClientPlayerInfo', {}).get('AccountId')
        
        # 默认返回值
        local_info = (None, [], None)  # name, ids, cardback
        enemy_info = (None, [], None)  # name, ids, cardback
        
        # 确定本地玩家
        if local_account_id:
            for name, info in players.items():
                # 遍历数据寻找匹配local_account_id的玩家
                for path, value in traverse_dict(data):
                    if isinstance(value, dict) and value.get('Name') == name and value.get('AccountId') == local_account_id:
                        local_info = (name, list(info['ids']), info['cardback'])
                        break
                if local_info[0]:  # 如果找到了本地玩家就退出循环
                    break
        
        # 剩余的玩家作为敌方玩家
        for name, info in players.items():
            if name != local_info[0]:  # 不是本地玩家
                enemy_info = (name, list(info['ids']), info['cardback'])
                break

        # 获取GameAtPrestartTurn中的Players数组
        prestart_players = (data.get('RemoteGame', {})
                          .get('GameState', {})
                          .get('GameAtPreStartTurn', {})
                          .get('Players', []))
        
        if len(prestart_players) == 2:
            for player in prestart_players:
                player_id = player.get('$id')
                player_info_ref = player.get('PlayerInfo', {}).get('$ref')
                
                if not player_id or not player_info_ref:
                    continue
                    
                # 将player_info_ref转换为字符串，因为有时可能是数字
                player_info_ref = str(player_info_ref)
                
                # 检查这个ref是否在本地玩家或敌方玩家的ID列表中
                if local_info[1] and str(player_info_ref) in map(str, local_info[1]):
                    # 属于本地玩家
                    local_ids = set(local_info[1])
                    local_ids.add(player_id)
                    local_info = (local_info[0], list(local_ids), local_info[2])
                    print(f"ID {player_id} 通过PlayerInfo {player_info_ref} 匹配到本地玩家")
                    
                elif enemy_info[1] and str(player_info_ref) in map(str, enemy_info[1]):
                    # 属于敌方玩家
                    enemy_ids = set(enemy_info[1])
                    enemy_ids.add(player_id)
                    enemy_info = (enemy_info[0], list(enemy_ids), enemy_info[2])
                    print(f"ID {player_id} 通过PlayerInfo {player_info_ref} 匹配到敌方玩家")
        
        print(f"本地玩家信息: 名字={local_info[0]}, IDs={local_info[1]}, 卡背ID={local_info[2]}")
        print(f"敌方玩家信息: 名字={enemy_info[0]}, IDs={enemy_info[1]}, 卡背ID={enemy_info[2]}")
        
        return local_info, enemy_info
        
    except Exception as e:
        print(f"获取玩家信息时出错: {e}")
        return ((None, [], None), (None, [], None))

    # try:
    #     remote_game = data.get('RemoteGame', {})
    #     game_state = remote_game.get('GameState', {})
    #     players = game_state.get('Players', [])
    #     client_player_info = remote_game.get('ClientPlayerInfo', {})
    #     local_account_id = client_player_info.get('AccountId')
        
    #     local_info = (None, [])  # (name, [ids])
    #     enemy_info = (None, [])  # (name, [ids])
        
    #     # 1. 首先从ClientPlayerInfo中获取本地玩家信息
    #     local_name = client_player_info.get('Name')
    #     local_id = client_player_info.get('$id')
    #     if local_name and local_id:
    #         local_info = (local_name, [local_id])
        
    #     # 2. 从Players列表中获取信息
    #     for player in players:
    #         account_id = player.get('AccountId')
    #         name = player.get('Name')
    #         player_id = player.get('$id')
            
    #         if account_id == local_account_id:
    #             if local_info[0] is None:  # 如果还没有找到本地玩家名字
    #                 local_info = (name, [player_id] if player_id else [])
    #             elif player_id and player_id not in local_info[1]:
    #                 local_info[1].append(player_id)
    #         elif name:  # 如果是敌方玩家
    #             if enemy_info[0] is None:  # 如果还没有找到敌方玩家名字
    #                 enemy_info = (name, [player_id] if player_id else [])
    #             elif player_id and player_id not in enemy_info[1]:
    #                 enemy_info[1].append(player_id)
        
    #     # 3. 从VisibleToPlayers中查找
    #     for player in players:
    #         visible_to_players = player.get('VisibleToPlayers', [])
    #         for visible_player in visible_to_players:
    #             player_name = visible_player.get('Name')
    #             player_id = visible_player.get('$id')
    #             account_id = visible_player.get('AccountId')
                
    #             if account_id == local_account_id:
    #                 if local_info[0] is None:  # 如果还没有找到本地玩家名字
    #                     local_info = (player_name, [player_id] if player_id else [])
    #                 elif player_id and player_id not in local_info[1]:
    #                     local_info[1].append(player_id)
    #             elif player_name:  # 如果是敌方玩家
    #                 if enemy_info[0] is None:  # 如果还没有找到敌方玩家名字
    #                     enemy_info = (player_name, [player_id] if player_id else [])
    #                 elif player_id and player_id not in enemy_info[1]:
    #                     enemy_info[1].append(player_id)
        
    #     # 打印调试信息
    #     print(f"本地玩家信息: {local_info}")
    #     print(f"敌方玩家信息: {enemy_info}")
        
    #     return local_info, enemy_info
        
    # except Exception as e:
    #     print(f"获取玩家信息时出错: {e}")
    #     return ((None, []), (None, []))

def traverse_dict(obj, path=[]):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield path + [k], v
            if isinstance(v, (dict, list)):
                yield from traverse_dict(v, path + [k])
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield path + [i], v
            if isinstance(v, (dict, list)):
                yield from traverse_dict(v, path + [i])


def find_card_owner_id(data, card_name):
    """
    在整个数据结构中搜索特定卡牌的所有owner ID
    
    Args:
        data: 游戏状态数据
        card_name: 要搜索的卡牌名称
    
    Returns:
        list: 所有匹配卡牌的owner ID列表
    """
    owner_ids = []
    
    def search_in_data(d):
        if isinstance(d, dict):
            # 如果找到了匹配的卡牌
            if d.get('CardDefId') == card_name:
                owner_ref = d.get('Owner', {}).get('$ref')
                if owner_ref and owner_ref not in owner_ids:
                    owner_ids.append(owner_ref)
            
            # 递归搜索所有字典值
            for v in d.values():
                search_in_data(v)
                    
        elif isinstance(d, list):
            # 递归搜索列表中的所有元素
            for item in d:
                search_in_data(item)
    
    search_in_data(data)
    return owner_ids