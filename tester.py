#!python3

import argparse
import logging

from plugin import PluginCollection


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--plugin')
    args = parser.parse_args()

    plugins = PluginCollection('plugins', filter_by_names=[args.plugin])
    for plugin in plugins.plugins:
        logging.info(f'running plugin {plugin.name}/{plugin.version}')
        plugin.job()


if __name__ == '__main__':
    logging.getLogger().setLevel(logging.DEBUG)
    logging.basicConfig(format='%(asctime)s %(levelname)-8s [%(lineno)-3d]%(filename)-20s: %(message)s')

    main()
