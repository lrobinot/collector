import json
from lifxlan import LifxLAN
import logging
import plugin
import schedule
import time
import os


class Lifx(plugin.Plugin):
    def __init__(self):
        super().__init__()
        self.active = True
        self.name = 'lifx'
        self.version = '1.0'
        self.description = 'Lifx Light'
        self.mqtt_topic = '/iot/lifx'

    def scheduler(self):
        scheduler = schedule.Scheduler()
        scheduler.every().minutes.do(self.run_threaded, self.job)
        return scheduler

    def job(self):
        lifx = LifxLAN()
        logging.info('retrieving data from Lifx')

        data = []
        for device in lifx.get_lights():
            logging.debug('Lifx light: ' + device.get_label())

            measurement = 'lifx_' + device.get_location_label() + '_' + device.get_label()
            color = device.get_color()

            data.append({
                'timestamp': int(time.time()),
                'measurement': measurement.lower(),
                'fields': {
                    'powered': 1 if device.get_power() != 0 else 0,
                    'hue': color[0],
                    'saturation': color[1],
                    'brightness': color[2],
                    'kelvin': color[3],
                },
            })

        mqtt_client = self.get_mqtt_client(self.name)
        logging.debug(json.dumps(data))
        mqtt_client.publish(self.mqtt_topic, json.dumps(data))
