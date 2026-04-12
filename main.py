import requests
import re
import os

# --- 基础配置 ---
# 如果你想手动输入搜索关键词，可以在 GitHub Actions 的 Inputs 里设置
env_search = os.getenv("INPUT_SEARCH_KEY")
SEARCH_QUERY = env_search if env_search else 'fastervpn.world "hysteria2"'
TOKEN = os.getenv("MY_GITHUB_TOKEN") # 确保你在 Secrets 里设置了此 Token

# 已知的优质订阅源（作为额外补充）
TARGET_URLS = [
    "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/main/BLACK_SS%2BAll_RUS.txt",
    "https://raw.githubusercontent.com/shaoyouvip/free/main/all.yaml",
    "https://raw.githubusercontent.com/ssrsub/ssr/master/singbox.json",
    "https://raw.githubusercontent.com/Whoahaow/rjsxrd/main/githubmirror/default/24.txt"
]

def get_ipv6_array():
    """生成 17b 网段 1-100 的百人特种兵阵列"""
    array = []
    for i in range(1, 101):
        name = f"FR-17b-{i:03d}"
        node = {
            "name": name,
            "server": f"[2001:bc8:32d7:17b::{i}]",
            "port": 22000,
            "password": "dongtaiwang.com",
            "sni": "apple.com"
        }
        array.append(node)
    return array

def search_github():
    """从 GitHub 全网搜索最新的 fastervpn 节点"""
    if not TOKEN: 
        print("⚠️ 未检测到 MY_GITHUB_TOKEN，跳过 GitHub 搜索。")
        return []
    
    search_url = f"https://api.github.com/search/code?q={SEARCH_QUERY}&sort=indexed"
    headers = {
        "Authorization": f"token {TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    found_urls = []
    try:
        r = requests.get(search_url, headers=headers, timeout=15)
        if r.status_code == 200:
            for item in r.json().get('items', []):
                raw_url = item['html_url'].replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/")
                found_urls.append(raw_url)
    except Exception as e:
        print(f"❌ 搜索出错: {e}")
    return found_urls

def harvest():
    """合并特种兵阵列与搜刮到的动态节点"""
    final_nodes = get_ipv6_array()  # 先加载 100 个特种兵
    # 用 server:port 作为唯一标识去重
    seen_uids = {f"{n['server']}:{n['port']}" for n in final_nodes}
    name_counts = {}
    
    # 汇总所有来源
    all_sources = list(set(TARGET_URLS + search_github()))
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    print(f"🛰️ 正在从 {len(all_sources)} 个来源收割节点...")
    
    for url in all_sources:
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code != 200: continue
            
            # 匹配 fastervpn.world 的 HY2 节点
            links = re.findall(r"hysteria2://([^@]+)@([\w\d\.-]+?\.fastervpn\.world):(\d+)", resp.text, re.I)
            for pwd, host, port in links:
                uid = f"{host}:{port}"
                if uid not in seen_uids:
                    base_name = host.split('.')[0]
                    name_counts[base_name] = name_counts.get(base_name, 0) + 1
                    final_nodes.append({
                        "name": f"{base_name}_{name_counts[base_name]}",
                        "server": host,
                        "port": port,
                        "password": pwd,
                        "sni": host
                    })
                    seen_uids.add(uid)
        except:
            continue
    return final_nodes

if __name__ == "__main__":
    nodes = harvest()
    
    # 生成 Clash 格式文件
    yaml_lines = [
        "port: 7890",
        "socks-port: 7891",
        "allow-lan: true",
        "mode: rule",
        "proxies:"
    ]
    
    for n in nodes:
        # 移除 IPv6 地址的方括号用于 SNI
        sni_val = n['sni'].replace("[", "").replace("]", "")
        yaml_lines.append(f"  - {{name: '{n['name']}', server: {n['server']}, port: {n['port']}, type: hysteria2, password: '{n['password']}', sni: {sni_val}, skip-cert-verify: true}}")
    
    yaml_lines.append("\nproxy-groups:")
    yaml_lines.append("  - name: 📺 电视自动故障转移")
    yaml_lines.append("    type: fallback")
    yaml_lines.append("    url: 'http://www.gstatic.com/generate_204'")
    yaml_lines.append("    interval: 300")
    yaml_lines.append("    proxies:")
    for n in nodes:
        yaml_lines.append(f"      - '{n['name']}'")
    
    yaml_lines.append("\nrules:")
    yaml_lines.append("  - GEOIP,CN,DIRECT")
    yaml_lines.append("  - MATCH,📺 电视自动故障转移")

    # 写入文件
    with open("proxies.yaml", "w", encoding="utf-8") as f:
        f.write("\n".join(yaml_lines))
    
    print(f"✅ 处理完成！当前共有 {len(nodes)} 个节点。")
    print(f"📍 其中包含 100 个 17b 特种兵和 {len(nodes)-100} 个全网收割节点。")
