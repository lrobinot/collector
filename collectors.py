#!python3

import logging

from plugin import PluginCollection


def main():
    plugins = PluginCollection('plugins')
    plugins.list()
    plugins.schedule()


if __name__ == '__main__':
    logging.getLogger().setLevel(logging.ERROR)
    logging.basicConfig(format='%(asctime)s %(levelname)-8s [%(lineno)-3d]%(filename)-20s: %(message)s')

    main()
