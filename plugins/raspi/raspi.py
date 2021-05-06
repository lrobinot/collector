import json
import logging
import plugin
import schedule
import socket
import time


def trasnform_temp(v):
    return float(v) / 1000.


class RasPi(plugin.Plugin):
    def __init__(self):
        super().__init__()
        self.active = True
        self.name = 'raspi'
        self.version = '1.0'
        self.description = 'RaspberryPi information'
        self.mqtt_topic = '/system/raspi'

    def scheduler(self):
        scheduler = schedule.Scheduler()
        scheduler.every(5).seconds.do(self.run_threaded, self.job)
        return scheduler

    def job(self):
        logging.info('retrieving data from raspberry pi')

        measures = [
            {
                'name': 'temp',
                'file': '/sys/class/thermal/thermal_zone0/temp',
                'trasnform': trasnform_temp,
            }
        ]

        fields = {}
        for m in measures:
            with open(m['file']) as f:
                value = f.read().strip()
            fields[m['name']] = m['trasnform'](value)

        data = []
        data.append({
            'timestamp': int(time.time()),
            'measurement': socket.gethostname().replace('-', '_'),
            'fields': fields,
        })

        mqtt_client = self.get_mqtt_client(self.name)
        logging.debug(json.dumps(data))
        mqtt_client.publish(self.mqtt_topic, json.dumps(data))
