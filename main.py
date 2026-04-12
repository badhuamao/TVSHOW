import requests
import re
import os

# --- 配置区：你的四大老巢和全网搜索关键词 ---
env_search = os.getenv("INPUT_SEARCH_KEY")
SEARCH_QUERY = env_search if env_search else 'fastervpn.world "hysteria2"'
env_url = os.getenv("INPUT_CUSTOM_URL")
TOKEN = os.getenv("MY_GITHUB_TOKEN")

TARGET_URLS = [
    "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/main/BLACK_SS%2BAll_RUS.txt",
    "https://raw.githubusercontent.com/shaoyouvip/free/main/all.yaml",
    "https://raw.githubusercontent.com/ssrsub/ssr/master/singbox.json",
    "https://raw.githubusercontent.com/Whoahaow/rjsxrd/main/githubmirror/default/24.txt"
]

if env_url and env_url.startswith("http"):
    TARGET_URLS.append(env_url)

def search_github():
    if not TOKEN: return []
    search_url = f"https://api.github.com/search/code?q={SEARCH_QUERY}&sort=indexed"
    headers = {"Authorization": f"token {TOKEN}", "Accept": "application/vnd.github.v3+json"}
    found_urls = []
    try:
        r = requests.get(search_url, headers=headers, timeout=10)
        if r.status_code == 200:
            for item in r.json().get('items', []):
                raw_url = item['html_url'].replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/")
                found_urls.append(raw_url)
    except: pass
    return found_urls

def harvest():
    final_nodes = []
    seen_uids = set()
    name_counts = {}
    headers = {'User-Agent': 'Mozilla/5.0'}
    all_sources = list(set(TARGET_URLS + search_github()))
    
    for url in all_sources:
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code != 200: continue
            content = resp.text
            
            # 模式 1：直连链接提取
            links = re.findall(r"hysteria2://([^@]+)@([\w\d\.-]+?\.fastervpn\.world):(\d+)", content, re.I)
            for pwd, host, port in links:
                save_node(host, port, pwd, final_nodes, seen_uids, name_counts)
            
            # 模式 2：针对 YAML/JSON 的块提取
            blocks = re.split(r'-\s+name:|{', content)
            for block in blocks:
                if "fastervpn.world" in block:
                    h = re.search(r"([\w\d\.-]+?\.fastervpn\.world)", block)
                    p = re.search(r"(?:port|server_port)[:\"\s]+(\d+)", block)
                    pw = re.search(r"(?:password|auth_str|auth)[:\"\s]+['\"]?([^'\"\s,{}]+)['\"]?", block)
                    if h and p:
                        save_node(h.group(1), p.group(1), pw.group(1) if pw else "test.+", final_nodes, seen_uids, name_counts)
        except: continue
    return final_nodes

def save_node(host, port, pwd, final_nodes, seen_uids, name_counts):
    pwd = pwd.strip().strip("'").strip('"').split(',')[0]
    uid = f"{host}:{port}:{pwd}"
    if uid not in seen_uids:
        base_name = host.split('.')[0]
        name_counts[base_name] = name_counts.get(base_name, 0) + 1
        display_name = f"{base_name}_{name_counts[base_name]}"
        node = {"name": display_name, "server": host, "port": port, "password": pwd}
        final_nodes.append(node)
        seen_uids.add(uid)

if __name__ == "__main__":
    nodes = harvest()
    
    # --- 构建电视专用 Clash YAML ---
    yaml_lines = [
        "port: 7890",
        "socks-port: 7891",
        "allow-lan: true",
        "mode: rule",
        "proxies:"
    ]
    for n in nodes:
        yaml_lines.append(f"  - {{name: '{n['name']}', server: {n['server']}, port: {n['port']}, type: hysteria2, password: '{n['password']}', sni: {n['server']}, skip-cert-verify: true}}")
    
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

    with open("proxies.yaml", "w", encoding="utf-8") as f:
        f.write("\n".join(yaml_lines))
    print(f"✅ 收割完成，共斩获 {len(nodes)} 个节点。")
