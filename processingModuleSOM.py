#!/usr/bin/python3

import logging
import argparse
import toml
import trio

from lib import core 

def main():
    args_parser = argparse.ArgumentParser(prog='processingModuleSOM.py', description='Online mastering service. Processing module')
    args_parser.add_argument('-c', '--config', type=str, default='etc/processingModuleSOMconfig.toml')
    args = args_parser.parse_args()

    with open(args.config, 'r') as file:
        config = toml.load(file)

    logging.basicConfig(level=config['LOG']['level'], format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logging.info('Start processing module')

    new_core = core.Core(config) 
    trio.run(new_core.run)

if __name__ == '__main__':
    main()
