'''
Created on 2023/5/22

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
from scripts import NANDInstruction      
        
        
class Core:
    def __init__(self, addr, port):
        self.logger = utils.get_logger('NANDCoreClient')
        self.addr = addr
        self.port = port
        self.connected = False
        self.reader = None
        self.writer = None
        self.id = 0
        self.id_lock = threading.Lock()
        self.rp = packet.rp_controller(self)
        self.signal_parser = argparse.ArgumentParser(description='NAND Flash Command-line program.')
        self.signal_parser.add_argument('-i', '--inst', required=True, type=int, help='NAND instruction set. '+ utils.separator.join('{}:{}'.format(item.name, item.value) for item in NANDInstruction.nand_inst_t))
        self.signal_parser.add_argument('-ch', '--channel', required=True, type=int, help='Channel.')
        self.signal_parser.add_argument('-ce', '--chip-enable', required=True, type=int, help='Chip enable.')
        self.signal_parser.add_argument('-addr', '--address', nargs='+', type=utils.parse_hex, help='NAND address. cycle0 cycle1 cycle2 cycle3 cycle4')
        self.signal_parser.add_argument('-p', '--prefix', type=utils.prefix_type, help='Prefix command.')
        self.signal_parser.add_argument('-f', '--file', nargs='+', help='File.')
        self.signal_parser.add_argument('-d', '--data', default=b'' , type=utils.byte_data_type, help='Signal high or low and Binary data.')
        self.signal_parser.add_argument('-x', '--hex', type=utils.parse_hex, help='Signal high or low and Binary data. Example: "\x48\x65"')
        
    async def __aenter__(self):
        self.conn_ani = asyncio.create_task(utils.loading_animation('Connecting...'))
        await self.connect_and_handle(self.addr, self.port)
        return self
    
    async def __aexit__(self, exc_type, exc_value, traceback):
        await self.rp.core.writer.drain()
        # Closing the connection
        self.rp_controller.core.writer.close()
        await self.rp_controller.writer.wait_closed()
        print("Connection closed")
        
    async def connect_and_handle(self, host, port):
        # Establish the connection
        try:
            self.reader, self.writer = await asyncio.open_connection(host, port)
            self.conn_ani.cancel()
            print("\nConnect successfully.")   
        except Exception as msg:
            raise Exception('Connect error : {}'.format(msg))
        # Call the callback function to handle the connection