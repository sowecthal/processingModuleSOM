#!/usr/bin/python3

import logging

from lib import CoreProcessingModule

def main():
    core = CoreProcessingModule()
    core.runServe(80)

if __name__ == '__main__':
    main()