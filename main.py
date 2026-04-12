import requests
import re
import os
import base64

# --- 配置区保持原样 ---
env_search = os.getenv("INPUT_SEARCH_KEY")
SEARCH_QUERY = env_search if env_search else 'fastervpn.world "hysteria2"'
TOKEN = os.getenv("MY_GITHUB_TOKEN")

TARGET_URLS = [
    "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/main/BLACK_SS%2BAll_RUS.txt",
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
            
            # --- 关键改动：Base64 自动嗅探 ---
            content = resp.text.strip()
            # 逻辑：如果没有空格且长度较大，大概率是编码后的订阅
            if len(content) > 30 and ' ' not in content and '\n' not in content:
                try:
                    # 自动补齐等号并解码
                    content = base64.b64decode(content + '=' * (-len(content) % 4)).decode('utf-8')
                    print(f"🔓 解码成功: {url[:40]}...")
                except: pass # 解码失败就当普通文本处理

            # 模式 1：直连链接提取 (锁定域名，过滤 17b)
            links = re.findall(r"hysteria2://([^@]+)@([\w\d\.-]+?\.fastervpn\.world):(\d+)", content, re.I)
            for pwd, host, port in links:
                save_node(host, port, pwd, final_nodes, seen_uids, name_counts)
            
            # 模式 2：YAML/JSON 块提取
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
    
    # 后面构建 YAML 的逻辑保持不变...
    yaml_lines = [
        "port: 7890", "socks-port: 7891", "allow-lan: true", "mode: rule", "proxies:"
    ]
    for n in nodes:
        yaml_lines.append(f"  - {{name: '{n['name']}', server: {n['server']}, port: {n['port']}, type: hysteria2, password: '{n['password']}', sni: {n['server']}, skip-cert-verify: true}}")
    
    yaml_lines.append("\nproxy-groups:\n  - name: 📺 电视自动故障转移\n    type: fallback\n    url: 'http://www.gstatic.com/generate_204'\n    interval: 300\n    proxies:")
    for n in nodes: yaml_lines.append(f"      - '{n['name']}'")
    
    yaml_lines.append("\nrules:\n  - GEOIP,CN,DIRECT\n  - MATCH,📺 电视自动故障转移")

    with open("proxies.yaml", "w", encoding="utf-8") as f:
        f.write("\n".join(yaml_lines))
    print(f"✅ 收割完成，当前库内节点总数：{len(nodes)}")
