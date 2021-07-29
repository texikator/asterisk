from pyzabbix import ZabbixMetric, ZabbixSender, ZabbixAPI
from datetime import datetime
from re import findall

# current_time = datetime.now().strftime("%H:%M:%S %d.%m.%Y")

class ZabbixItem():

    def __init__(self, user, password, ext_group, ext_template, zabbix_host):
        self.user = user
        self.password = password
        self.zabbix_host = zabbix_host
        self.zabbix_api = f"http://{zabbix_host}"

        self.connection = self.connection_init()
        self.template_id = self.get_template(ext_template)
        self.group_id = self.get_group(ext_group)
        # print(self.get_group(EXT_GROUP))

    def connection_init(self):
        '''
        Zabbix connection init
        :return: connection
        '''
        return ZabbixAPI(f"http://{self.zabbix_host}", user=self.user, password=self.password)

    def get_template(self, template_name):
        '''
        Get template id by template name
        :param template_name:
        :return: template id as string
        '''

        ext_template = self.connection.do_request("template.get", {
            "filter": {"host": [template_name]},
            "output": "template_id"
        }).get("result")

        if ext_template:
            result = ext_template[0].get("templateid")
        else:
            result = False
        return result

    def get_group(self, group_name):
        """
        Get group Id
        :param group_name:
        :return: group ID
        """

        group = self.connection.do_request("hostgroup.get", {
            "filter": {"name": [group_name]},
            "output": "extend"
        }).get("result")

        if group:
            result = group[0].get("groupid")
        else:
            # print("create Group")
            result = False
        return result

    def clear_ping(self, value):
        """
        clear ping value from text
        :param value: raw data, 50 ms as example
        :return: integer value
        """

        try:
            result = int(value[:value.find(" ")])
        except IndexError:
            result = False
        except ValueError:
            # print(value)
            result = False
        return result


    def host_create(self, data):
        '''
        Create host item
        :param host_params:
        :return: host id
        '''

        return self.connection.do_request('host.create', data)[0].get("result")
    def assign_template_to_host(self, host_id):
        """
        Assign template to host
        :param host_id: host id
        :return:
        """

        return self.connection.do_request("template.update", teamplateid=self.template_id, hosts=[host_id])

    def send_data(self, data):
        """
        Send data to server
        :param data: data dict
        :return:
        """
        # test_dict = {'ext': '1105', 'ip_address': '192.168.10.55', 'status': 'OK', 'ping': '5 ms', 'user': 'Secretary',
        #              'user_agent': 'Cisco/SPA508G-7.4.9a'}

        sender_data = []
        host_id = data.get("ext")
        # print(ZABBIX_HOST)
        zbx_sender = ZabbixSender(self.zabbix_host)
        extension_ip = ZabbixMetric(host_id, 'extPhoneIpAddress', data.get("ip_address"))
        sender_data.append(extension_ip)

        extension_ping = ZabbixMetric(host_id, "extPhonePing", self.clear_ping(data.get("ping", 10000)))
        sender_data.append(extension_ping)

        extension_status = ZabbixMetric(host_id, "extStatus", data.get("status", ""))
        sender_data.append(extension_status)

        extension_user = ZabbixMetric(host_id, "extUser", data.get("user", ""))
        sender_data.append(extension_user)

        extension_useragent = ZabbixMetric(host_id, "extUserAgent", data.get("user_agent", ""))
        sender_data.append(extension_useragent)
        zbx_sender.send(sender_data)

    def worker(self, data):
        """
        Check host. If extension exists - send new data, otherwise - create extension's host in zabbix and send data.
        :param data: dict with data
        :return: host id
        """
        print(data)
        host_raw = self.connection.do_request('host.get', {
            'filter': {'host': data["ext"]},
            'output': ['hostid']
        }).get("result")
        # print("host_raw", host_raw)
        if host_raw:
            host_id = host_raw[0].get("hostid")

        else:
            host_new = self.connection.do_request('host.create', {"host" : f"{data.get('ext')}",
                                                                    "templates": [
                                                                        {"templateid" : self.template_id}
                                                                    ],
                                                                    "groups": [
                                                                        {"groupid": self.group_id}
                                                                    ]

             })

            host_id = host_new.get("result").get("hostids")[0]
        self.send_data(data)
