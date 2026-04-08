"""
權限驗證測試 — 不需啟動 server，不呼叫 LLM
直接測試 load_access_control() 的輸出是否符合預期
"""
import sys
from pathlib import Path

# 讓 Python 找到 config 模組
sys.path.insert(0, str(Path(__file__).parent))

from config import load_access_control, _discover_all_groups
from config import config as cfg

# ── 預期結果（依 access_control.csv 與 _discover_all_groups 邏輯） ──
# Boss 的 ReadGroups=All，動態展開為所有群組目錄（排除 chroma_db）
# 所有人自動包含 Public

EXPECTED = {
    'Boss':      {'read': {'Developer', 'RD_ME', 'Public'}, 'write': {'Public'}},
    'User_All':  {'read': {'Developer', 'RD_ME', 'Public'}, 'write': {'Developer', 'RD_ME'}},
    'User_RD':   {'read': {'RD_ME', 'Public'},              'write': {'RD_ME'}},
    'User_Dev':  {'read': {'Developer', 'Public'},          'write': {'Developer'}},
    'User_None': {'read': {'Public'},                       'write': set()},
}

PASS = '✅'
FAIL = '❌'

def run():
    print('=' * 65)
    print('  權限驗證測試')
    print('=' * 65)

    # 顯示實際探索到的群組
    all_groups = _discover_all_groups()
    print(f'\n[資訊] 資料目錄探索到的群組：{all_groups}')
    print(f'[資訊] PUBLIC_GROUP = {cfg.PUBLIC_GROUP}')
    print(f'[資訊] ALL_GROUPS_KEYWORD = {cfg.ALL_GROUPS_KEYWORD}\n')

    whitelist, permissions = load_access_control()

    if whitelist is None:
        print(f'{FAIL} 無法載入 access_control.csv')
        return

    print(f'[資訊] 白名單：{sorted(whitelist)}\n')

    results = []

    for username, expected in EXPECTED.items():
        perm = permissions.get(username)
        if perm is None:
            results.append((username, FAIL, f'找不到此帳號'))
            continue

        actual_read  = set(perm['read'])
        actual_write = set(perm['write'])
        exp_read     = expected['read']
        exp_write    = expected['write']

        read_ok  = actual_read  == exp_read
        write_ok = actual_write == exp_write

        tag = PASS if (read_ok and write_ok) else FAIL

        details = []
        if not read_ok:
            missing_r  = exp_read  - actual_read
            extra_r    = actual_read  - exp_read
            if missing_r:  details.append(f'Read 缺少: {missing_r}')
            if extra_r:    details.append(f'Read 多出: {extra_r}')
        if not write_ok:
            missing_w  = exp_write - actual_write
            extra_w    = actual_write - exp_write
            if missing_w:  details.append(f'Write 缺少: {missing_w}')
            if extra_w:    details.append(f'Write 多出: {extra_w}')

        results.append((username, tag, actual_read, actual_write, details))

    # ── 輸出結果表 ──
    print(f'{"帳號":<12} {"結果":<4} {"Read 群組":<40} {"Write 群組"}')
    print('─' * 90)
    for row in results:
        username, tag = row[0], row[1]
        if tag == FAIL and len(row) == 3:
            print(f'{username:<12} {tag:<4} {row[2]}')
            continue
        actual_read, actual_write, details = row[2], row[3], row[4]
        print(f'{username:<12} {tag:<4} {str(sorted(actual_read)):<40} {sorted(actual_write)}')
        for d in details:
            print(f'  ⚠️  {d}')

    # ── 統計 ──
    passed = sum(1 for r in results if r[1] == PASS)
    failed = len(results) - passed
    print('─' * 90)
    print(f'\n{PASS} {passed} 通過 | {FAIL} {failed} 失敗 | 共 {len(results)} 個帳號')

    # ── 也列出不在測試清單中的帳號（例如 Herch）──
    other = set(permissions.keys()) - set(EXPECTED.keys())
    if other:
        print(f'\n[略過] 以下帳號未納入測試：{sorted(other)}')
        for u in sorted(other):
            p = permissions[u]
            print(f'  {u}: read={sorted(p["read"])}, write={sorted(p["write"])}')


if __name__ == '__main__':
    run()
