#!/usr/bin/python3
import subprocess
import re
from SendExtensionData import ZabbixItem

EXT_GROUP = 'Asterisk Extensions' # name of asterisk extension group
EXT_TEMPLATE = "Template Asterisk Extensions" # template name

API_USER = "*****" # zabbix API user
API_PASSWORD = "*****" # password of Zabbix API user
ZABBIX_HOST = "*****" # zabbix host

ZABBIX_API = f"http://{ZABBIX_HOST}"
user_pattern = r'Callerid\s*:\s*\"(.*)\"'
useragent_pattern = r'Useragent\s*:(.*)\n'

def parse_peer(raw_str):
    arr = raw_str.split()
    if len(arr) < 9:
        status = arr[-1]
        lag = ""
    else:
        status = arr[-3]
        lag = f"{arr[-2]} {arr[-1]}".strip("()")
    # print(arr)
    if "/" in arr[0]:
        peer = arr[0][:arr[0].find("/")]
    else:
        peer = arr[0]
    ip_address = arr[1]

    result = {"ext": peer, "ip_address": ip_address, "status": status, "ping": lag}
    # print(result)
    return result

zabbix_item = ZabbixItem(API_USER, API_PASSWORD, ext_group=EXT_GROUP, ext_template=EXT_TEMPLATE, zabbix_host=ZABBIX_HOST)

get_peers_args = ["/usr/sbin/asterisk", "-rx", "sip show peers"]
subproc_peers = subprocess.Popen(get_peers_args, stdout=subprocess.PIPE)

for line in subproc_peers.stdout:
    line = line.decode("utf8")
    # print(line)
    if line.startswith("Name") or " offline Unmonitored:" in line or len(line) < 10:
        continue
    ext = parse_peer(line)
    # print(ext)
    if ext:
        peer_args = ["/usr/sbin/asterisk", "-rx", f"sip show peer {ext['ext']}"]
        subproc_peer = subprocess.Popen(peer_args, stdout=subprocess.PIPE, encoding="UTF-8")
        peer_inf = subproc_peer.stdout.read()

        user = re.findall(user_pattern, peer_inf)
        user_agent = re.search(useragent_pattern, peer_inf).group(1)

        if user:
            ext["user"] = user[0]
        else:
            ext["user"] = ""

        if user_agent:
            ext["user_agent"] = user_agent

        else:
            ext["user_agent"] = ""

        zabbix_item.worker(ext)
    


