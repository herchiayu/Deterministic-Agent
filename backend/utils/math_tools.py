"""
工程計算工具模組

定義所有可供 Gemini Automatic Function Calling (AFC) 呼叫的計算函數。

新增工具步驟：
  1. 在此檔案新增計算函數（必須有 type hints 和 docstring）
  2. 將函數加入底部的 TOOL_FUNCTIONS 列表
  3. 重啟伺服器
"""


# ============================================================
# 計算函數
# ============================================================

def isentropic_pressure_ratio(mach: float, gamma: float = 1.4) -> dict:
    """
    等熵流壓力比 (Total/Static Pressure Ratio)
    PR = (1 + (γ-1)/2 * M²) ^ (γ/(γ-1))
    """
    pr = (1 + (gamma - 1) / 2 * mach ** 2) ** (gamma / (gamma - 1))
    return {
        'mach': mach,
        'gamma': gamma,
        'pressure_ratio': round(pr, 6),
        'formula': 'PR = (1 + (γ-1)/2 × M²) ^ (γ/(γ-1))'
    }


def isentropic_temperature_ratio(mach: float, gamma: float = 1.4) -> dict:
    """
    等熵流溫度比 (Total/Static Temperature Ratio)
    TR = 1 + (γ-1)/2 * M²
    """
    tr = 1 + (gamma - 1) / 2 * mach ** 2
    return {
        'mach': mach,
        'gamma': gamma,
        'temperature_ratio': round(tr, 6),
        'formula': 'TR = 1 + (γ-1)/2 × M²'
    }


# ============================================================
# 工具註冊表（新增函數後加到這裡即可）
# ============================================================

TOOL_FUNCTIONS = [
    isentropic_pressure_ratio,
    isentropic_temperature_ratio,
]
