'''
Created on 2023/6/15

@author: martinlee
'''
import asyncio
import utils
import packet
import argparse
import packet
import ctypes
import threading
import traceback
from core import NANDCoreUnit
from nand import NANDUnit
from core import NANDCore
from enum import Enum       
from scripts import NANDInstruction 
       
class nand_inst_t(Enum):
    CE_OUT = 0
    CLE_OUT = 1
    ALE_OUT = 2
    DQ_OUT = 3
    DQ_IN = 4
    READ_ID_10 = 5
    READ_ID_40 = 6
    MULTI_PLANE_ERASE = 7        
    ERASE = 8
    PAGE_PROGRAM = 9
    MULTI_PLANE_PAGE_PROGRAM = 10
    PAGE_READ = 11
    RADOM_DATA_OUTPUT = 12
    PREFIX_01 = 13
    PREFIX_02 = 14
    PREFIX_03 = 15
    PREFIX_A2 = 16
    
async def exec_function(inst, args):
    # Function name as a string
    try:
        function_name = NANDInstruction.nand_inst_t(args.inst).name.lower()
        function_param = 'args.channel, args.chip_enable'
        
   
        if args.address:
            function_param += ', args.address' 
        if args.hex:
            function_param += ', args.hex' 
        elif args.file:
            function_param += ', data'
            data = []
            # Open the file in read mode
            for filepath in args.file:
                with open(filepath, "rb") as file:
                    # Read the contents of the file
                    data.append(file.read())
                
        if args.prefix:
            function_param += ', prefix = args.prefix'    
                 
        function_call = f'inst.{function_name}({function_param})'
        
        result = await eval(function_call)
        
        return result
    except Exception as msg:
        print(traceback.format_exc())  

def get_function_call(args):
    # Function name as a string
    function_name = NANDInstruction.nand_inst_t(args.inst).name.lower()
    function_param = 'args.channel, args.chip_enable'
    
    if args.prefix:
        function_param += ', prefix = args.prefix' 
    if args.address:
        function_param += ', args.address' 
    if args.hex:
        function_param += ', args.hex' 
    elif args.file:
        function_param += ', prefix = args.prefix' 
            
    function_call = f'inst.{function_name}({function_param})'
    
    return function_call

class nand_inst_base:
    def __init__(self, core):
        try:
            if not hasattr(core, 'rp'):
                raise ValueError("There have no remote port controller.")
            self.core = core
        except ValueError as msg:
            print("{}".format(msg))
            
    async def ce_out(self, channel, ce, value):
        pin = NANDCoreUnit.get_die_pin(NANDUnit.TARGET_SIGNAL.CE.value, channel, ce)
        data = await self.core.rp.send_signal(packet.RP_CMD.WRITE.value, pin, value)
        return data
    
    async def cle_out(self, channel, ce, value):
        pin = NANDCoreUnit.get_die_pin(NANDUnit.TARGET_SIGNAL.CLE.value, channel, ce)
        data = await self.core.rp.send_signal(packet.RP_CMD.WRITE.value, pin, value)
        return data
    
    async def ale_out(self, channel, ce, value):
        pin = NANDCoreUnit.get_die_pin(NANDUnit.TARGET_SIGNAL.ALE.value, channel, ce)
        data = await self.core.rp.send_signal(packet.RP_CMD.WRITE.value, pin, value)
        return data

    async def dq_out(self, channel, ce, value):
        pin = NANDCoreUnit.get_die_pin(NANDUnit.TARGET_SIGNAL.DQ.value, channel, ce)
        data = await self.core.rp.send_signal(packet.RP_CMD.WRITE.value, pin, value)
        return data
        
    async def dq_in(self, channel, ce):
        pin = NANDCoreUnit.get_die_pin(NANDUnit.TARGET_SIGNAL.DQ.value, channel, ce)
        data = await self.core.rp.send_signal(packet.RP_CMD.READ.value, pin, packet.empty_data)
        return data


      
