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
from core import NANDCoreUnit
from nand import NANDUnit
from scripts import NANDInstruction


class inst_base(NANDInstruction.nand_inst_base):
    
    async def prefix(self, channel, ce, prefix):
        if prefix:
            await self.cle_out( channel, ce, packet.high)
            await self.dq_out( channel, ce, prefix)
            await self.cle_out( channel, ce, packet.low)
           
    async def read_id_10(self, channel, ce):
        await self.ce_out( channel, ce, packet.high)
        await self.cle_out( channel, ce, packet.high)
        await self.dq_out( channel, ce, b'\x90')
        await self.cle_out( channel, ce, packet.low)
        await self.ale_out( channel, ce, packet.high)
        await self.dq_out( channel, ce, b'\x10')
        await self.ale_out( channel, ce, packet.low)
        data = await self.dq_in( channel, ce)
        await self.ce_out( channel, ce, packet.low)
        
        return data
    
    async def read_id_40(self, channel, ce):
        await self.ce_out( channel, ce, packet.high)
        await self.cle_out( channel, ce, packet.high)
        await self.dq_out( channel, ce, b'\x90')
        await self.cle_out( channel, ce, packet.low)
        await self.ale_out( channel, ce, packet.high)
        await self.dq_out( channel, ce, b'\x40')
        await self.ale_out( channel, ce, packet.low)
        data = await self.dq_in( channel, ce)
        await self.ce_out( channel, ce, packet.low)
        
        return data   
    
    async def multi_plane_erase(self, channel, ce, row_addr_list, prefix = None):
        await self.ce_out( channel, ce, packet.high)
        
        await self.prefix(channel, ce, prefix)
            
        for row_addr in row_addr_list:
            await self.cle_out( channel, ce, packet.high)
            await self.dq_out( channel, ce, b'\x60')
            await self.cle_out( channel, ce, packet.low)
            await self.ale_out( channel, ce, packet.high)
            await self.dq_out( channel, ce, row_addr)
            await self.ale_out( channel, ce, packet.low)
            
        await self.cle_out( channel, ce, packet.high)
        await self.dq_out( channel, ce, b'\xd0')
        await self.cle_out( channel, ce, packet.low)
        await self.ce_out( channel, ce, packet.low)
        
    
    async def erase(self, channel, ce, row_addr, prefix = None):
        
        await self.ce_out( channel, ce, packet.high)
        
        await self.prefix(channel, ce, prefix)
            
        
        await self.cle_out( channel, ce, packet.high)
        await self.dq_out( channel, ce, b'\x60')
        await self.cle_out( channel, ce, packet.low)
        await self.ale_out( channel, ce, packet.high)
        await self.dq_out( channel, ce, row_addr)
        await self.ale_out( channel, ce, packet.low)
        await self.cle_out( channel, ce, packet.high)
        await self.dq_out( channel, ce, b'\xd0')
        await self.cle_out( channel, ce, packet.low)
        await self.ce_out( channel, ce, packet.low)
        
    async def page_program(self, channel, ce, addr, data, prefix = None):  
        await self.ce_out( channel, ce, packet.high)
                
        await self.prefix(channel, ce, prefix)
            

        await self.cle_out( channel, ce, packet.high)
        await self.dq_out( channel, ce, b'\x80')
        await self.cle_out( channel, ce, packet.low)
        await self.ale_out( channel, ce, packet.high)
        await self.dq_out( channel, ce, addr)
        await self.ale_out( channel, ce, packet.low)
        await self.dq_out( channel, ce, data)
        await self.cle_out( channel, ce, packet.high)
        await self.dq_out( channel, ce, b'\x10')
        await self.cle_out( channel, ce, packet.low)
        await self.ce_out( channel, ce, packet.low)
        
    
    async def multi_plane_page_program(self, channel, ce, addr_list, data, prefix = None):
        
        await self.ce_out( channel, ce, packet.high)
        
        await self.prefix(channel, ce, prefix)
        
        for index in range(len(addr_list)):
            await self.cle_out( channel, ce, packet.high)
            await self.dq_out( channel, ce, b'\x80')
            await self.cle_out( channel, ce, packet.low)
            await self.ale_out( channel, ce, packet.high)
            await self.dq_out( channel, ce, addr_list[index])
            await self.ale_out( channel, ce, packet.low)
            await self.dq_out( channel, ce, data[index])
            await self.cle_out( channel, ce, packet.high)
            if index < ( len(addr_list) - 1 ):  
                await self.dq_out( channel, ce, b'\x11')
            else:
                await self.dq_out( channel, ce, b'\x10')
            await self.cle_out( channel, ce, packet.low)
        
        await self.ce_out( channel, ce, packet.low)
        
    
    async def page_read(self, channel, ce, addr, data, prefix = None):
        
        await self.ce_out( channel, ce, packet.high)
        
        await self.prefix(channel, ce, prefix)
            
        await self.cle_out( channel, ce, packet.high)
        await self.dq_out( channel, ce, b'\x00')
        await self.cle_out( channel, ce, packet.low)
        await self.ale_out( channel, ce, packet.high)
        await self.dq_out( channel, ce, addr)
        await self.ale_out( channel, ce, packet.low)
        await self.cle_out( channel, ce, packet.high)
        await self.dq_out( channel, ce, b'\x30')
        await self.cle_out( channel, ce, packet.low)
        await self.ce_out( channel, ce, packet.low)
        
    
    async def radom_data_output(self, channel, ce, addr):
        
        await self.ce_out( channel, ce, packet.high)
        await self.cle_out( channel, ce, packet.high)
        await self.dq_out( channel, ce, b'\x05')
        await self.cle_out( channel, ce, packet.low)
        await self.ale_out( channel, ce, packet.high)
        await self.dq_out( channel, ce, addr)
        await self.ale_out( channel, ce, packet.low)
        await self.cle_out( channel, ce, packet.high)
        await self.dq_out( channel, ce, b'\xe0')
        await self.cle_out( channel, ce, packet.low)
        data = await self.dq_in( channel, ce)
        await self.ce_out( channel, ce, packet.low)
        
        return data