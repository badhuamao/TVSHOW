import requests
import re
import os

# --- 1. 基础配置 ---
env_search = os.getenv("INPUT_SEARCH_KEY")
SEARCH_QUERY = env_search if env_search else 'fastervpn.world "hysteria2"'
TOKEN = os.getenv("MY_GITHUB_TOKEN")

TARGET_URLS = [
    "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/main/BLACK_SS%2BAll_RUS.txt",
    "https://raw.githubusercontent.com/shaoyouvip/free/main/all.yaml",
    "https://raw.githubusercontent.com/ssrsub/ssr/master/singbox.json",
    "https://raw.githubusercontent.com/Whoahaow/rjsxrd/main/githubmirror/default/24.txt"
]

def get_ipv6_array():
    """生成 17b 网段 1-100 的阵列"""
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
    """从 GitHub 全网捕获动态节点"""
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
    """合并特种兵与全网收割成果"""
    final_nodes = get_ipv6_array()
    seen_uids = {f"{n['server']}:{n['port']}" for n in final_nodes}
    name_counts = {}
    
    all_sources = list(set(TARGET_URLS + search_github()))
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    for url in all_sources:
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code != 200: continue
            # 捕获动态 Hysteria2 节点
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
        except: continue
    return final_nodes

if __name__ == "__main__":
    nodes = harvest()
    
    # 采用最稳固的多行 YAML 格式，确保电视软件能读出地址
    yaml_lines = [
        "port: 7890",
        "socks-port: 7891",
        "allow-lan: true",
        "mode: rule",
        "proxies:"
    ]
    
    for n in nodes:
        sni_val = n['sni'].replace("[", "").replace("]", "")
        yaml_lines.append(f"  - name: \"{n['name']}\"")
        yaml_lines.append(f"    type: hysteria2")
        yaml_lines.append(f"    server: \"{n['server']}\"")
        yaml_lines.append(f"    port: {n['port']}")
        yaml_lines.append(f"    password: \"{n['password']}\"")
        yaml_lines.append(f"    sni: \"{sni_val}\"")
        yaml_lines.append(f"    skip-cert-verify: true")
    
    yaml_lines.append("\nproxy-groups:")
    yaml_lines.append("  - name: \"📺 电视自动故障转移\"")
    yaml_lines.append("    type: fallback")
    yaml_lines.append("    url: 'http://www.gstatic.com/generate_204'")
    yaml_lines.append("    interval: 300")
    yaml_lines.append("    proxies:")
    for n in nodes:
        yaml_lines.append(f"      - \"{n['name']}\"")
    
    yaml_lines.append("\nrules:")
    yaml_lines.append("  - GEOIP,CN,DIRECT")
    yaml_lines.append("  - MATCH,\"📺 电视自动故障转移\"")

    # 写入 proxies.yaml
    with open("proxies.yaml", "w", encoding="utf-8") as f:
        f.write("\n".join(yaml_lines))
    
    print(f"✅ 满血收割完成！共计 {len(nodes)} 个节点。")
