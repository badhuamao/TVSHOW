import requests
import re
import os
import base64

# --- 配置区：去掉 "hysteria2" 限制，扩大包围圈 ---
env_search = os.getenv("INPUT_SEARCH_KEY")
# 咱们直接搜域名，凡是带这个域名的文件一个都不放过
SEARCH_QUERY = env_search if env_search else 'fastervpn.world'
TOKEN = os.getenv("MY_GITHUB_TOKEN")

TARGET_URLS = [
    "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/main/BLACK_SS%2BAll_RUS.txt",
    "https://raw.githubusercontent.com/shaoyouvip/free/main/all.yaml",
    "https://raw.githubusercontent.com/ssrsub/ssr/master/singbox.json",
    "https://raw.githubusercontent.com/Whoahaow/rjsxrd/main/githubmirror/default/24.txt"
]

def search_github():
    if not TOKEN: return []
    # 增加按索引时间排序，确保抓到的是最新的
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
            
            content = resp.text.strip()
            
            # Base64 自动识别逻辑（保留，以防万一）
            if len(content) > 30 and ' ' not in content and '\n' not in content:
                try:
                    content = base64.b64decode(content + '=' * (-len(content) % 4)).decode('utf-8')
                except: pass

            # 模式 1：链接提取（只要带域名，我们就认为它是 hy2，因为这是咱们的目的）
            # 注意：即便明文里没写 hysteria2，只要链接格式对，咱们就把它按 hy2 处理
            links = re.findall(r"(\w+)://([^@]+)@([\w\d\.-]+?\.fastervpn\.world):(\d+)", content, re.I)
            for proto, pwd, host, port in links:
                # 即使原链接是别的协议，我们也强行尝试以 hy2 运行，因为原厂节点基本都是这个
                save_node(host, port, pwd, final_nodes, seen_uids, name_counts)
            
            # 模式 2：块提取（不再硬性要求 block 里包含 hysteria2 关键字）
            blocks = re.split(r'-\s+name:|{', content)
            for block in blocks:
                if "fastervpn.world" in block:
                    h = re.search(r"([\w\d\.-]+?\.fastervpn\.world)", block)
                    p = re.search(r"(?:port|server_port)[:\"\s]+(\d+)", block)
                    # 密码提取更激进一点
                    pw = re.search(r"(?:password|auth_str|auth|auth-str)[:\"\s]+['\"]?([^'\"\s,{}]+)['\"]?", block)
                    if h and p:
                        save_node(h.group(1), p.group(1), pw.group(1) if pw else "test.+", final_nodes, seen_uids, name_counts)
        except: continue
    return final_nodes

def save_node(host, port, pwd, final_nodes, seen_uids, name_counts):
    pwd = pwd.strip().strip("'").strip('"').split(',')[0]
    uid = f"{host}:{port}:{pwd}"
    if uid not in seen_uids:
        # 优化命名，保留地区信息
        base_name = host.split('.')[0]
        name_counts[base_name] = name_counts.get(base_name, 0) + 1
        display_name = f"{base_name}_{name_counts[base_name]}"
        node = {"name": display_name, "server": host, "port": port, "password": pwd}
        final_nodes.append(node)
        seen_uids.add(uid)

if __name__ == "__main__":
    nodes = harvest()
    # ... 后面的 YAML 生成逻辑和之前完全一致 ...
    yaml_lines = ["port: 7890", "socks-port: 7891", "allow-lan: true", "mode: rule", "proxies:"]
    for n in nodes:
        yaml_lines.append(f"  - {{name: '{n['name']}', server: {n['server']}, port: {n['port']}, type: hysteria2, password: '{n['password']}', sni: {n['server']}, skip-cert-verify: true}}")
    
    yaml_lines.append("\nproxy-groups:\n  - name: 📺 电视自动故障转移\n    type: fallback\n    url: 'http://www.gstatic.com/generate_204'\n    interval: 300\n    proxies:")
    for n in nodes: yaml_lines.append(f"      - '{n['name']}'")
    
    yaml_lines.append("\nrules:\n  - GEOIP,CN,DIRECT\n  - MATCH,📺 电视自动故障转移")

    with open("proxies.yaml", "w", encoding="utf-8") as f:
        f.write("\n".join(yaml_lines))
    print(f"✅ 广撒网完成！共斩获 {len(nodes)} 个疑似原厂节点。")
