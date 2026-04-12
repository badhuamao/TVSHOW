import requests
import re

# --- 1. 核心逻辑：只盯准这个域名，这是咱们的命根子 ---
SEARCH_URL = "https://raw.githubusercontent.com/FasterVPN-Auto/fastervpn-nodes/main/nodes.txt"

def harvest_fastvpn():
    try:
        # 直接拉取你最信任的 FastVPN 节点列表
        resp = requests.get(SEARCH_URL, timeout=15)
        if resp.status_code == 200:
            # 这里的逻辑非常简单：直接读取，不做协议过滤
            # 因为这个源里的东西，电视上的老 Clash 肯定认得
            content = resp.text.strip()
            nodes = content.split('\n')
            return [n.strip() for n in nodes if n.strip()]
    except:
        pass
    return []

if __name__ == "__main__":
    # 执行收割
    fast_nodes = harvest_fastvpn()
    
    # --- 2. 严格遵循你要求的输出格式 ---
    with open("proxies.yaml", "w", encoding="utf-8") as f:
        f.write(f"# 抓取到 {len(fast_nodes)} 个可用节点\n")
        for node in fast_nodes:
            # 这一版直接输出原始行，不做任何多余的协议拼凑
            f.write(f"- {node}\n")
            
    print(f"✅ 库已恢复！共计收割 {len(fast_nodes)} 个 FastVPN 原厂节点。")
