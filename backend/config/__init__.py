import csv
from config import config as cfg


def load_access_control():
    """
    載入白名單與讀寫群組對照。

    CSV 格式：Username,ReadGroups,WriteGroups
    - ReadGroups / WriteGroups 以 GROUP_SEPARATOR 分隔多個群組
    - ReadGroups 為 'All' 時，代表可讀取所有群組（動態解析）
    - 所有使用者的 read_groups 自動包含 PUBLIC_GROUP
    - ReadGroups 與 WriteGroups 皆可留空

    回傳：(whitelist_set, permissions_dict) 或 (None, {})
      permissions_dict: {username: {'read': [group, ...], 'write': [group, ...]}}
    """
    if not cfg.ACCESS_CONTROL_CSV.exists():
        return None, {}

    whitelist = set()
    permissions = {}

    with open(cfg.ACCESS_CONTROL_CSV, 'r', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            username = row.get('Username', '').strip()
            if not username:
                continue

            whitelist.add(username)

            raw_read = row.get('ReadGroups', '').strip()
            raw_write = row.get('WriteGroups', '').strip()

            # 解析讀取群組
            if raw_read == cfg.ALL_GROUPS_KEYWORD:
                read_groups = _discover_all_groups()
            elif raw_read:
                read_groups = [
                    g.strip() for g in raw_read.split(cfg.GROUP_SEPARATOR) if g.strip()
                ]
            else:
                read_groups = []

            # 確保 PUBLIC_GROUP 一定在讀取列表中
            if cfg.PUBLIC_GROUP not in read_groups:
                read_groups.append(cfg.PUBLIC_GROUP)

            # 解析寫入群組
            if raw_write:
                write_groups = [
                    g.strip() for g in raw_write.split(cfg.GROUP_SEPARATOR) if g.strip()
                ]
            else:
                write_groups = []

            permissions[username] = {
                'read': read_groups,
                'write': write_groups,
            }

    return whitelist, permissions


def _discover_all_groups():
    """掃描 KNOWLEDGE_BASE_DIR 下的所有子目錄作為群組（排除 chroma_db）"""
    groups = []
    if cfg.KNOWLEDGE_BASE_DIR.exists():
        for d in sorted(cfg.KNOWLEDGE_BASE_DIR.iterdir()):
            if d.is_dir() and d.name != 'chroma_db':
                groups.append(d.name)
    return groups
