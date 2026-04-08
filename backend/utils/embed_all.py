"""
重新 Embedding 所有知識庫群組

用法：
  cd backend
  python utils/embed_all.py              # 僅建立尚未存在的索引
  python utils/embed_all.py --force      # 強制重建所有索引
  python utils/embed_all.py --group RD_ME             # 僅建立指定群組
  python utils/embed_all.py --group Public --force     # 強制重建指定群組
"""

import argparse
import sys
from pathlib import Path

# 確保 backend/ 在 sys.path 中，讓 config / utils 能正確 import
_backend_dir = Path(__file__).resolve().parent.parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

from utils.knowledge_base import kb


def main():
    parser = argparse.ArgumentParser(description='重新 Embedding 知識庫')
    parser.add_argument(
        '--force', action='store_true',
        help='強制重建索引（刪除舊索引後重新建立）',
    )
    parser.add_argument(
        '--group', type=str, default=None,
        help='僅重建指定群組（預設重建所有群組）',
    )
    args = parser.parse_args()

    if args.group:
        print(f'[embed_all] 目標群組：{args.group}，force={args.force}')
        kb.build_group_index(args.group, force_rebuild=args.force)
    else:
        print(f'[embed_all] 重建所有群組，force={args.force}')
        kb.build_all_indexes(force_rebuild=args.force)

    print('[embed_all] 完成')


if __name__ == '__main__':
    main()
