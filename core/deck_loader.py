import os
import json
import sys

def get_resource_path(relative_path):
    """获取资源文件的绝对路径，兼容开发环境和打包环境"""
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller 打包后的路径
        base_path = sys._MEIPASS
    else:
        # 开发环境路径
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative_path)

def get_snap_decks_info():
    """读取漫威终极逆转的卡组信息，返回所有卡组数据"""
    try:
        # 读取卡组信息
        user_home = os.path.expanduser('~')
        collection_path = os.path.join(
            user_home,
            'AppData',
            'LocalLow',
            'NetEase',
            'SnapCN',
            'Standalone',
            'States',
            'prod',
            'CollectionState.json'
        )
        
        # 使用资源路径获取卡牌信息文件路径
        cards_info_path = get_resource_path('cards.json')
        
        # 加载文件
        with open(collection_path, 'r', encoding='utf-8-sig') as f:
            collection_data = json.load(f)
        with open(cards_info_path, 'r', encoding='utf-8-sig') as f:
            cards_info = json.load(f)
            
        # 创建卡牌ID到信息的映射
        cards_map = {card['card_id']: card for card in cards_info}
        
        # 解析卡组数据
        decks_info = {}
        for deck in collection_data['ServerState']['Decks']:
            deck_name = deck['Name']
            deck_id = deck['Id']  # 添加卡组ID
            cards = []
            
            # 处理卡组中的每张卡
            for card in deck['Cards']:
                card_id = card['CardDefId']
                card_info = cards_map.get(card_id, {})
                card_name = card_info.get('chinese_name', card_id)
                
                # 直接使用中文名构建图片路径
                image_path = f'卡面/{card_name}.png'
                
                cards.append({
                    'card_id': card_id,
                    'name': card_name,
                    'image': image_path,
                    'cost': card_info.get('cost', 99)
                })
            
            decks_info[deck_name] = {
                'name': deck_name,
                'id': deck_id,  # 保存卡组ID
                'cards': cards
            }
        
        return decks_info
        
    except Exception as e:
        print(f"读取卡组信息失败: {e}")
        import traceback
        traceback.print_exc()
        return {}