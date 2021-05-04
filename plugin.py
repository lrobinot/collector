import inspect
import json
import logging
import os
import pkgutil
import sys
import threading
import time

import paho.mqtt.client as mqtt


class Plugin(object):
    """Base class that each plugin must inherit from. within this class
    you must define the methods that all of your plugins must implement
    """

    def __init__(self):
        self.active = False
        self.name = None
        self.version = None
        self.description = None
        self.mqtt_topic = None

        self.config_load()

    def config_load(self):
        dir = sys.modules[self.__class__.__module__].__file__
        file = os.path.join(os.path.dirname(dir), 'config.json')
        # logging.debug(f'reading config from {file}')
        if os.path.exists(file):
            self.config = json.load(open(file))
        else:
            self.config = {}
        # logging.debug('config=' + json.dumps(self.config))

    def config_save(self):
        dir = sys.modules[self.__class__.__module__].__file__
        file = os.path.join(os.path.dirname(dir), 'config.json')
        json.dump(self.config, open(file, 'w'))

    def run_threaded(self, job_func):
        logging.debug('running on thread {}'.format(threading.current_thread()))
        job_thread = threading.Thread(target=job_func)
        job_thread.start()

    def scheduler(self, **options):
        """This method returns a scheduler, ready to be called
        """
        raise NotImplementedError

    def job(self):
        """This method execute the job of the plugin
        """
        raise NotImplementedError

    def mqtt_on_connect(self, mqttc, obj, flags, rc):
        logging.debug('rc: ' + str(rc))

    def mqtt_on_message(self, mqttc, obj, msg):
        logging.debug(msg.topic + ' ' + str(msg.qos) + ' ' + str(msg.payload))

    def mqtt_on_publish(self, mqttc, obj, mid):
        logging.debug('mid: ' + str(mid))
        pass

    def mqtt_on_subscribe(self, mqttc, obj, mid, granted_qos):
        logging.debug('subscribed: ' + str(mid) + ' ' + str(granted_qos))

    def mqtt_on_log(self, mqttc, obj, level, string):
        logging.debug(string)

    def get_mqtt_client(self, app_id):
        mqtt_client = mqtt.Client(app_id)

        mqtt_client.on_message = self.mqtt_on_message
        mqtt_client.on_connect = self.mqtt_on_connect
        mqtt_client.on_publish = self.mqtt_on_publish
        mqtt_client.on_subscribe = self.mqtt_on_subscribe
        mqtt_client.on_log = self.mqtt_on_log

        mqtt_client.username_pw_set(os.getenv('COLLECTOR_MQTT_USER'), os.getenv('COLLECTOR_MQTT_PASS'))
        mqtt_client.connect(os.getenv('COLLECTOR_MQTT_HOST'), port=os.getenv('COLLECTOR_MQTT_PORT'))

        return mqtt_client


class PluginCollection(object):
    """Upon creation, this class will read the plugins package for modules
    that contain a class definition that is inheriting from the Plugin class
    """

    def __init__(self, plugin_package, filter_by_names=None):
        """Constructor that initiates the reading of all available plugins
        when an instance of the PluginCollection object is created
        """
        self.plugin_package = plugin_package

        self.plugins = []
        self.seen_paths = []
        logging.info('looking for plugins')
        self.walk(self.plugin_package)

        if not (filter_by_names is None):
            self.plugins = [p for p in self.plugins if p.name in filter_by_names]

    def list(self):
        """List plugins
        """
        logging.info('list of plugins:')
        for plugin in self.plugins:
            logging.info(f'  * {plugin.description} ({plugin.name}/{plugin.version})')

    def walk(self, package):
        """Recursively walk the supplied package to retrieve all plugins
        """
        imported_package = __import__(package, fromlist=['blah'])

        for _, pluginname, ispkg in pkgutil.iter_modules(imported_package.__path__, imported_package.__name__ + '.'):
            if not ispkg:
                plugin_module = __import__(pluginname, fromlist=['blah'])
                clsmembers = inspect.getmembers(plugin_module, inspect.isclass)
                for (_, c) in clsmembers:
                    # Only add classes that are a sub class of Plugin, but NOT Plugin itself
                    if issubclass(c, Plugin) & (c is not Plugin):
                        logging.debug(f'found plugin class: {c.__module__}.{c.__name__}')
                        self.plugins.append(c())

        # Now that we have looked at all the modules in the current package, start looking
        # recursively for additional modules in sub packages
        all_current_paths = []
        if isinstance(imported_package.__path__, str):
            all_current_paths.append(imported_package.__path__)
        else:
            all_current_paths.extend([x for x in imported_package.__path__])

        for pkg_path in all_current_paths:
            if pkg_path not in self.seen_paths:
                self.seen_paths.append(pkg_path)

                # Get all sub directory of the current package path directory
                child_pkgs = [p for p in os.listdir(pkg_path) if os.path.isdir(os.path.join(pkg_path, p))]

                # For each sub directory, apply the walk method recursively
                for child_pkg in child_pkgs:
                    self.walk(package + '.' + child_pkg)

    def schedule(self):
        schedulers = []

        for plugin in self.plugins:
            if plugin.active:
                sch = plugin.scheduler()
                logging.info(f'running plugin {plugin.name}/{plugin.version}, publishing to {plugin.mqtt_topic}')
                try:
                    sch.run_all()
                except Exception as ex:
                    logging.error(str(ex))

                schedulers.append(sch)

        logging.info('running at scheduled time')
        while True:
            for s in schedulers:
                try:
                    s.run_pending()
                except Exception as ex:
                    logging.error(str(ex))

            time.sleep(1)
