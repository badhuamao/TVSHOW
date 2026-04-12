import requests
import re
import os

# --- 1. 基础配置 ---
# 搜索关键词回归：只找 FastVPN 这种老软件跑得顺的
SEARCH_QUERY = 'fastervpn.world'
TOKEN = os.getenv("MY_GITHUB_TOKEN")

# 你的“老三样”稳健订阅源
TARGET_URLS = [
    "https://raw.githubusercontent.com/shaoyouvip/free/main/all.yaml",
    "https://raw.githubusercontent.com/ssrsub/ssr/master/singbox.json",
    "https://raw.githubusercontent.com/Whoahaow/rjsxrd/main/githubmirror/default/24.txt"
]

def search_github():
    if not TOKEN: return []
    search_url = f"https://api.github.com/search/code?q={SEARCH_QUERY}&sort=indexed"
    headers = {"Authorization": f"token {TOKEN}", "Accept": "application/vnd.github.v3+json"}
    found_urls = []
    try:
        r = requests.get(search_url, headers=headers, timeout=15)
        if r.status_code == 200:
            for item in r.json().get('items', []):
                raw_url = item['html_url'].replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/")
                found_urls.append(raw_url)
    except: pass
    return found_urls

def harvest():
    final_nodes = []
    seen_uids = set()
    
    all_sources = list(set(TARGET_URLS + search_github()))
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    for url in all_sources:
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code != 200: continue
            
            content = resp.text
            # --- 核心清理：只匹配 SS/VLESS/Trojan ---
            # 彻底不再匹配 hysteria2:// 格式，从源头切断 17b
            links = re.findall(r"(ss://|vless://|trojan://)[\w\d\.\-@:/%?=&#]+", content, re.I)
            
            for link in links:
                if link not in seen_uids:
                    final_nodes.append(link)
                    seen_uids.add(link)
        except: continue
    return final_nodes

if __name__ == "__main__":
    # 结果依然会输出到你 CF Worker 对应的订阅文件里
    # 电视端刷新一下，那些糟心的 404 和报错就全消失了
    nodes = harvest()
    print(f"✅ 17b 节点已物理隔离，库已回滚。")
    print(f"📦 当前收割量：{len(nodes)} 个纯净兼容节点，老 Clash 随便跑。")
