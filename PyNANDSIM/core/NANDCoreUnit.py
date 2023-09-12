'''
Created on 2023/5/12

@author: martinlee
'''
import asyncio
import struct
from nand import NANDUnit
import logging
import utils
from enum import Enum
from nand import micron
from nand import samsung
from nand import sandisk
from nand import toshiba

SIM_CHANNEL = 64
SIM_CE = 64

class CORE_ACTION(Enum):
    READ_FILE = 0
    WRITE_FILE = 1
    ERASE_FILE = 2
    DATA_OUT = 3
    
    
class CHANNEL_SIGNAL(Enum):
    CLE = 0
    ALE = 1
    DQ = 2
    DQS = 3
    RE = 4
    WE = 5
    WP = 6

class Target_mapping():
    def __init__(self, package, channel, target):
        self.package = package
        self.channel = channel
        self.target = target
        self.task = None
        
def get_die_pin(signal, channel, ce):
    
    return len(NANDUnit.TARGET_SIGNAL) * ce * SIM_CHANNEL  + len(NANDUnit.TARGET_SIGNAL) * channel + signal

def create_target(logger, channel_signal, manufacturer, part_number):
    try:
        function_call = "{}.{}.NANDBuild({}, {})".format(manufacturer, part_number, 'logger', 'channel_signal')
        logger.debug('create_target, nand path : {}.'.format(function_call))
        nand = eval(function_call)
    except Exception as msg:
        raise ValueError("Error msg : {}".format(msg))
    
    return nand

class NANDFile:
    def __init__(self, filename, page_register):
        self.filename = filename
        self.page_register = page_register
        
        
class Channel:
    def __init__(self, logger, manufacturer, part_number, num_target):
        self.logger = logger
        self.signal = [0] * len(CHANNEL_SIGNAL)
        self.num_target = num_target
        self.active_target = None
        self.target = [create_target(utils.get_logger('{}_Target_{}'.format(logger.name, i)), self.signal,  manufacturer, part_number) for i in range(num_target)]
    
    def enable_signal(self, signal_num):
        if self.get_active_target() is not None:
            if self.signal[signal_num] == 0:
                self.signal[signal_num] = 1
            else:
                raise Exception("{} Signal[{}] is enabled.".format(self.logger.name, signal_num))
        else:
            raise Exception("There is no target enabled.")
        
    def disable_signal(self, signal_num):
        if self.get_active_target() is not None:
            if self.signal[signal_num] == 1:
                self.signal[signal_num] = 0
            else:
                raise Exception("{} Signal[{}] is disabled.".format(self.logger.name, signal_num))
        else:
            raise Exception("There is no target enabled.")
           
    def enable_target(self, target_num):
        if self.active_target is None:
            self.active_target = target_num
            self.target[target_num].signal[NANDUnit.TARGET_SIGNAL.CE.value] = 1
        else:
            raise Exception("Chips enable error!! Too many chips enabled.")
        
    def disable_target(self, target_num):
        if self.active_target is not None:
            self.active_target = None
            self.target[target_num].signal[NANDUnit.TARGET_SIGNAL.CE.value] = 0
        else:
            raise Exception("Chips disable error!! No active target.")                               
    def get_active_target(self):   
        return self.active_target   
                
    async def handle_signal(self, data):
        act_target = self.get_active_target()
        if self.active_target is not None:
            action, filename, data, cb = await self.target[act_target].process_data(data) or [None, None, None, None]
                        
            return action, filename, data, cb             
        else:
            raise Exception("There is no target enabled.")
        
class Package:
    def __init__(self, logger, manufacturer, part_number, num_target, num_channel):
        self.logger = logger
        self.num_channel = num_channel
        self.num_target = num_target
        self.manufacture = manufacturer
        self.part_number = part_number
        self.channel = [Channel(utils.get_logger('{}_Channel_{}'.format(logger.name, i)), manufacturer, part_number, num_target) for i in range(num_channel)]
            
class NANDCard:
    def __init__(self, manufacturer, part_number, num_package, package_num_channel, package_num_target):
        self.logger = utils.get_logger('NANDCard')
        self.num_package = num_package
        self.num_die = num_package * package_num_channel * package_num_target
        self.package = [Package(utils.get_logger('Package_{}'.format(i)), manufacturer, part_number, package_num_channel, package_num_target) for i in range(num_package)]
        self.logger.info("num_package:{}, package_num_channel:{}, package_num_target:{}".format(num_package, package_num_channel, package_num_target))    
        