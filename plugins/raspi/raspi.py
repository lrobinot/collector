import json
import logging
import plugin
import schedule
import socket
import time


def get_cpu_temp():
    with open('/sys/class/thermal/thermal_zone0/temp') as f:
        data = f.read().strip()
    return float(data) / 1000.


def get_cpu_load_1m():
    with open('/proc/loadavg') as f:
        data = f.read().strip()
    return float(data.split(' ')[0])


def get_cpu_load_5m():
    with open('/proc/loadavg') as f:
        data = f.read().strip()
    return float(data.split(' ')[1])


def get_cpu_load_15m():
    with open('/proc/loadavg') as f:
        data = f.read().strip()
    return float(data.split(' ')[2])


class RasPi(plugin.Plugin):
    def __init__(self):
        super().__init__()
        self.active = True
        self.name = 'raspi'
        self.version = '1.0'
        self.description = 'RaspberryPi SysInfo'
        self.mqtt_topic = '/system/raspi'

    def scheduler(self):
        scheduler = schedule.Scheduler()
        scheduler.every(5).seconds.do(self.run_threaded, self.job)
        return scheduler

    def job(self):
        logging.info('retrieving data from raspberry pi')

        measures = [
            {
                'name': 'cpu_temp',
                'get': get_cpu_temp,
            },
            {
                'name': 'cpu_load_1m',
                'get': get_cpu_load_1m,
            },
            {
                'name': 'cpu_load_5m',
                'get': get_cpu_load_5m,
            },
            {
                'name': 'cpu_load_15m',
                'get': get_cpu_load_15m,
            },
        ]

        fields = {}
        for m in measures:
            fields[m['name']] = m['get']()

        data = []
        data.append({
            'timestamp': int(time.time()),
            'measurement': socket.gethostname().replace('-', '_'),
            'fields': fields,
        })

        mqtt_client = self.get_mqtt_client(self.name)
        logging.debug(json.dumps(data))
        mqtt_client.publish(self.mqtt_topic, json.dumps(data))
