'''
Created on 2023/5/12

@author: martinlee
'''

import logging
import utils
import copy
from enum import Enum

NAND_MANUFACTURES = ['micron', 'samsung', 'sandisk', 'toshiba']
# Define state machine states
STATE_IDLE = 0
STATE_WAIT_COMMAND = 1
STATE_WAIT_ADDRESS = 2
STATE_WAIT_DATA = 3
STATE_WAIT_DATA_TO_NAND = 4
STATE_WAIT_DATA_FROM_NAND = 5
STATE_TRASFERRING_DATA_TO_NAND = 6
STATE_TRASFERRING_DATA_FROM_NAND = 7
STATE_TRASFERRING_DATA_OUT = 8

MAX_XLC_LEVEL = 4

class WL_PAGE_t(Enum):  
    LEVEL_ONE = 0
    LEVEL_TWO = 1
    LEVEL_THREE = 2
    
class PAGE_REG_NUM_t(Enum):  
    ORIGINAL = 0  
    LOWER = 1
    MIDDLE = 2
    UPPER = 3
    
class FILE_FORMATE(Enum):  
    RAW_FILE = 0  
    RAM_DISK = 1
    
class PAGE_STATUS(Enum):  
    EMPTY = 0  
    PROGRAMMED = 1
    OVER_PROGRAMMED = 2

class WL_STATUS_t(Enum):  
    EMPTY = 0  
    PROGRAMMED = 1
    OVER_PROGRAMMED = 2
      
class BLOCK_STATUS(Enum):
    GOOD = 0
    BAD = 1
    
class BLOCK_TYPE_t(Enum):
    SLC = 0
    XLC = 1
    
       
class TARGET_STATE(Enum):
    IDLE = 0
    WAIT_COMMAND = 1
    WAIT_ADDRESS = 2
    WAIT_DATA = 3
    

class TARGET_SIGNAL(Enum):
    CLE = 0
    ALE = 1
    CE = 2
    RB = 3
    DQS = 4
    RE = 5
    WE = 6
    WP = 7
    DQ = 8


    
class TARGET_STATUS(Enum):
    GOOD = 0
    BAD = 1

class WLCache:
    def __init__(self, block_type, lun, plane, block, page, data):
        self.data = data
        self.lun = lun
        self.block = block
        self.plane = plane
        self.page = page
        self.block_type = block_type
        
class MPAddress:
    def __init__(self, prefix, addr):
        self.prefix = prefix
        self.addr = addr
            
class Page:
    def __init__(self):
        self.status = PAGE_STATUS.EMPTY

class WL:
    def __init__(self, num_wl):
        self.status = WL_STATUS_t.EMPTY
        self.page = [Page()] * num_wl
        
class Block:
    def __init__(self, num_page):
        self.status = BLOCK_STATUS.GOOD
        self.erase_count = 0
        self.type = BLOCK_TYPE_t.XLC
        self.page = [Page()] * num_page

class Plane:
    def __init__(self, num_block, num_page):
        self.cache_register = b''
        self.data_register = b''
        self.page_register =[b''] * len(PAGE_REG_NUM_t)
        
        self.status = BLOCK_STATUS.GOOD
        self.erase_count = 0
        self.block = [Block(num_page)] * num_block
        
    def erase(self, prefix, block_id, block_type = BLOCK_TYPE_t.XLC):
        self.block[block_id].type = block_type
        for page in self.block[block_id].page :
            page.status = PAGE_STATUS.EMPTY 
        
class Lun:
    def __init__(self, num_plane, num_block, num_page):
        self.plane = [Plane(num_block, num_page)] * num_plane
                 
class Target:
    def __init__(self, logger, channel_signal, num_lun, num_plane, num_block, num_page, num_wl):
        self.logger = logger
        self.signal = [0] * len(TARGET_SIGNAL)
        self.channel_signal = channel_signal
        self.state = STATE_IDLE
        self.current_prefix =  b''
        self.current_command = b''
        self.check_prefix_idx =  PAGE_REG_NUM_t.ORIGINAL.value
        self.check_plane_idx =  0
        self.mp_address = [[]] * len(PAGE_REG_NUM_t)
        self.mp_command = []
        self.current_address =  b''
        self.address_cycle_count = 0
        self.current_data = b''
        self.status = TARGET_STATUS.GOOD
        self.num_lun = num_lun
        self.num_plane = num_plane
        self.num_block = num_block
        self.num_page = num_page
        self.lun = [Lun(num_plane, num_block, num_page)] * num_lun
        self.num_wl = num_wl
        self.wl_cache = []
        self.logger.info('Init Target , LUN : {}, PLANE : {}, BLOCK : {}, PAGE : {}.'.format(num_lun, num_plane, num_block, num_page))
        self.struct = utils.parse_c_structure()
        self.init_prefix_mapping({ '1': WL_PAGE_t.LEVEL_ONE, '2': WL_PAGE_t.LEVEL_TWO, 'age': WL_PAGE_t.LEVEL_THREE })
        
    def prefix_to_block_type(self, prefix):
        raise NotImplementedError( "prefix_to_block_type(self, prefix)" )
    
    def init_prefix_mapping(self, dict):
        self.prefix_mapping = dict
        
    def get_page_index(self, prefix, row_addr):
        return row_addr.wl
    
    def get_num_wl(self):
        
        return self.num_wl
        
    def get_page_status(self, lun, plane, block, page):
        return self.lun[lun].plane[plane].block[block].page[page].status
    
    def set_page_status(self, lun, plane, block, page, status):
        self.lun[lun].plane[plane].block[block].page[page].status = status
    
    def get_block_type(self, row_addr):
        return self.lun[row_addr.lun].plane[row_addr.plane].block[row_addr.block].type
    
    def erase(self, prefix, row_addr):
        block = self.lun[row_addr.lun].plane[row_addr.plane].block[row_addr.block]
        block_type = self.prefix_to_block_type(prefix)
        block.type = block_type
        temp_addr = copy.deepcopy(row_addr)
        for page in range(0, self.num_page):
            temp_addr.page = page
            self.set_page_status(temp_addr, PAGE_STATUS.EMPTY)
            
    def append_wl_cache(self, block_type, lun, plane, block, page, data):    
        self.wl_cache.append(WLCache(block_type, lun, plane, block, page, data))
    
    def get_wl_cache(self):    
        return self.wl_cache
           
    def reset_register(self):
        self.current_prefix = b''
        self.current_command = b''
        self.current_address = b''
    def get_data_register(self, prefix, addr):
        if prefix:
            cmd_prefix = int.from_bytes(prefix, byteorder='big')
        else:
            cmd_prefix = 0    
            
        return self.lun[addr.row.s.lun].plane[addr.row.s.plane].page_register[cmd_prefix]   
    
    def set_data_register(self, prefix, addr, data):
        if prefix:
            cmd_prefix = int.from_bytes(prefix, byteorder='big')
        else:
            cmd_prefix = 0    
            
        self.lun[addr.row.s.lun].plane[addr.row.s.plane].page_register[cmd_prefix] = data[:]
    
    def append_mp_address(self, prefix, addr):
        if prefix:
            cmd_prefix = int.from_bytes(prefix, byteorder='big')
        else:
            cmd_prefix = 0    
            
        self.mp_address[cmd_prefix].append(addr)
             
    def get_signal(self, pin):
        return self.signal[pin]
    
    def set_signal_high(self, pin):
        self.signal[pin] = 1
        
    def set_signal_low(self, pin):
        self.signal[pin] = 0
        
    def busy_done(self):
        self.state = STATE_IDLE
        self.get_wl_cache().clear()
        self.set_signal_low(TARGET_SIGNAL.RB.value)
        self.mp_address.clear()
    
        
    async def process_signal(self, data):
                        
        return await self.process_data(data)           
 
        
    async def process_busy(self, channel, data):#virtual function.
        raise NotImplementedError( "process_busy is virutal! Must be overwrited." )
     
    async def process_data(self, channel, data):#virtual function.
        raise NotImplementedError( "process_data is virutal! Must be overwrited." )
