'''
Created on 2023/5/12

@author: martinlee
'''
import logging
import struct
import ctypes
from nand import NANDUnit
from core import NANDCoreUnit
from enum import Enum
from pickle import NONE
import NANDUnit
import NANDCoreUnit
import pycstruct
import os
import utils
# Define command opcodes

PART_NUMBER = 'TC58LJG8T24TA0D'
NUM_BLOCK = 990
NUM_PLANE = 2
NUM_PAGES = 1152
FW_PAGE_SIZE = 16384
META_PAGE_SIZE = 1952
PAGE_SIZE = FW_PAGE_SIZE + META_PAGE_SIZE
NUM_LUN = 1
NUM_WL = 3


class PLANE_NUM_t(Enum):  
    FIRST = 0
    SECOND = 1
    
class WORD_LINE_NUM_t(Enum):  
    LOWER = 0
    MIDDLE = 1
    UPPER = 2
    
class row_address_s(ctypes.Structure):
    _pack_ = 1
    _fields_ = [('wl', ctypes.c_uint16, 9),
                ('plane', ctypes.c_uint16, 1),
                ('block', ctypes.c_uint16, 10),
                ('lun', ctypes.c_uint8, 1)
                ]

    
class row_address_o(ctypes.Structure):
    _pack_ = 1
    _fields_ = [('addr1', ctypes.c_uint8),
                ('addr2', ctypes.c_uint8),
                ('addr3', ctypes.c_uint8)
                ]
    
class row_address(ctypes.Union):
    _pack_ = 1
    _fields_ = [('o', row_address_o),
                ('s', row_address_s)
                ]     
    
class column_address_o(ctypes.Structure):
    _pack_ = 1
    _fields_ = [('addr1', ctypes.c_uint8),
                ('addr2', ctypes.c_uint8),
                ] 
    
class column_address(ctypes.Union):
    _fields_ = [('o', column_address_o)
                ]           
     
class address(ctypes.Structure):
    _pack_ = 1
    _fields_ = [('column', column_address),
                ('row', row_address)
                ]

class PREFIX_COMMAND(Enum):
    LSB = 0x01
    CSB = 0x02
    MSB = 0x03
    LCMSB = 0xa2
    
class COMMAND(Enum):
    LSB = 0x01
    CSB = 0x02
    MSB = 0x03
    LCMSB = 0xa2
    RESET = 0xff
    READ_ID = 0x90
    READ_PAGE = 0x00
    READ_PAGE_MSB = 0x30
    RANDOM_DATA_OUTPUT = 0x05
    RANDOM_DATA_OUTPUT_MSB = 0xe0
    READ_STATUS = 0x70
    PROGRAM_PAGE = 0x80
    PROGRAM_PAGE_RANDOM_IN = 0x85
    PROGRAM_PAGE_LSB = 0x1a
    PROGRAM_PAGE_CSB = 0x1a
    PROGRAM_PAGE_MP = 0x11
    PROGRAM_PAGE_MSB = 0x10
    ERASE_BLOCK = 0x60
    ERASE_BLOCK_MSB = 0xd0
    
    
class NANDBuild(NANDUnit.Target):
    def __init__(self, logger,channel_signal):
        super().__init__(logger, channel_signal, NUM_LUN, NUM_PLANE, NUM_BLOCK, NUM_PAGES, NUM_WL)
        addr =  ctypes.sizeof(row_address_s())
        print(f"{addr}")
    
    def prefix_to_block_type(self, prefix):
        if prefix == bytes([PREFIX_COMMAND.LCMSB.value]):
            return NANDUnit.BLOCK_TYPE_t.SLC
        else:
            return NANDUnit.BLOCK_TYPE_t.XLC
        
    def get_page_by_prefix_wl(self, prefix, wl):
        if prefix == bytes([PREFIX_COMMAND.LCMSB.value]):
            page = wl * self.num_wl 
        else:
            page = wl * self.num_wl + (int.from_bytes(prefix, 'little') - 1)
        return page
    
    def xfer_data_from_nand_cb(self, opaque):
        super().xfer_data_from_nand_cb(self, opaque)
        if self.current_data == b'':
            fill_value = b'\xff'
            self.current_data = fill_value * FW_PAGE_SIZE
    
    async def process_data(self, data):
            
    
            try:
                core_action = None
                
                while True:
                    if self.state == NANDUnit.STATE_IDLE:
                        if self.signal[NANDUnit.TARGET_SIGNAL.CLE.value] > 0 :
                            
                            self.logger.debug("Command received. CMD:[{}], STATE:[{}].".format(data, self.state))
                            if  data == bytes([PREFIX_COMMAND.LSB.value]) or \
                                data == bytes([PREFIX_COMMAND.CSB.value]) or \
                                data == bytes([PREFIX_COMMAND.MSB.value]) or \
                                data == bytes([PREFIX_COMMAND.LCMSB.value]) :
                            # Handle RESET command
                                self.current_prefix = data
                            else:
                                if data == bytes([COMMAND.RESET.value]):
                                    # Handle RESET command
                                    self.current_data = b''
                                    self.mp_address.clear()
                                elif data == bytes([COMMAND.READ_ID.value]):
                                    # Handle READ ID command
                                    self.state = NANDUnit.STATE_WAIT_DATA
                                elif data == bytes([COMMAND.READ_PAGE.value]):
                                    # Handle READ PAGE command
                                    self.state = NANDUnit.STATE_WAIT_ADDRESS
                                elif data == bytes([COMMAND.READ_PAGE_MSB.value]):
                                    # Handle READ PAGE command
                                    self.state = NANDUnit.STATE_WAIT_DATA
                                elif data == bytes([COMMAND.PROGRAM_PAGE.value]):
                                    # Handle PROGRAM PAGE command
                                    self.state = NANDUnit.STATE_WAIT_ADDRESS
                                    self.current_data = b''
                                elif data == bytes([COMMAND.PROGRAM_PAGE_MP.value]) or \
                                     data == bytes([COMMAND.PROGRAM_PAGE_LSB.value]) or \
                                     data == bytes([COMMAND.PROGRAM_PAGE_CSB.value]) or \
                                     data == bytes([COMMAND.PROGRAM_PAGE_MSB.value]) :
                                    
                                    addr_data = self.current_address + b'\x00' * (ctypes.sizeof(address) - len(self.current_address))
                                    addr = address.from_buffer_copy(addr_data)
                                        
                                    block_type = self.prefix_to_block_type(self.current_prefix)
                                    page = self.get_page_by_prefix_wl(self.current_prefix, addr.row.s.wl)
                                    
                                    self.append_wl_cache( block_type, \
                                                          addr.row.s.lun, \
                                                          addr.row.s.plane, \
                                                          addr.row.s.block, \
                                                          page, \
                                                          self.lun[addr.row.s.lun].plane[addr.row.s.plane].data_register[:])
                                    
                                    if data == bytes([COMMAND.PROGRAM_PAGE_MSB.value]) :
                                        # Handle ERASE BLOCK command
                                        self.reset_register()
                                        self.state = NANDUnit.STATE_TRASFERRING_DATA_TO_NAND
                                        core_action = NANDCoreUnit.CORE_ACTION.WRITE_FILE
                                        
                                elif data == bytes([COMMAND.ERASE_BLOCK.value]) or \
                                     data == bytes([COMMAND.ERASE_BLOCK_MSB.value]) :
                                    # Handle ERASE BLOCK command
                                    if self.current_command == bytes([COMMAND.ERASE_BLOCK.value]):
                                        addr_data = self.current_address + b'\x00' * (ctypes.sizeof(row_address_s) - len(self.current_address))
                                        row_addr = row_address_s.from_buffer_copy(addr_data)
                                        block_type = self.prefix_to_block_type(self.current_prefix)
                                        page = self.prefix_to_block_type(self.current_prefix, row_addr.wl)
                                        
                                        self.append_wl_cache( block_type, \
                                                              row_addr.lun, \
                                                              row_addr.plane, \
                                                              row_addr.block, \
                                                              page, \
                                                              b'')

                                    if data == bytes([COMMAND.ERASE_BLOCK.value]):
                                        self.state = NANDUnit.STATE_WAIT_ADDRESS
                                    else:
                                        self.reset_register()
                                        core_action = NANDCoreUnit.CORE_ACTION.ERASE_FILE
                                elif data == bytes([COMMAND.RANDOM_DATA_OUTPUT.value]) :
                                    self.state = NANDUnit.STATE_WAIT_ADDRESS
                                elif data == bytes([COMMAND.RANDOM_DATA_OUTPUT_MSB.value]) :
                                    self.state = NANDUnit.STATE_WAIT_DATA
                                  
                            self.current_command = data
                            break
                    elif self.state == NANDUnit.STATE_WAIT_ADDRESS:
                        # Handle address-specific data
                        if self.signal[NANDUnit.TARGET_SIGNAL.ALE.value] > 0 :
                            if self.current_command == bytes([COMMAND.READ_PAGE.value]) or \
                               self.current_command == bytes([COMMAND.PROGRAM_PAGE.value]) or \
                               self.current_command == bytes([COMMAND.ERASE_BLOCK.value]) or \
                               self.current_command == bytes([COMMAND.PROGRAM_PAGE_RANDOM_IN.value]):
                                self.current_address = data
                                self.logger.debug("Address received. CMD:[{}], ADDR:[{}], STATE:[{}].".format(self.current_command, self.current_address, self.state))
                                if self.current_command == bytes([COMMAND.ERASE_BLOCK.value]):
                                    # Send erase confirmation
                                    self.state = NANDUnit.STATE_IDLE
                                    break
                                elif self.current_command == bytes([COMMAND.PROGRAM_PAGE.value]):
                                    self.current_data = b''
                                    self.state = NANDUnit.STATE_WAIT_DATA
                                    break
                                else:
                                    self.state = NANDUnit.STATE_IDLE
                                    break
                            elif self.current_command == bytes([COMMAND.READ_PAGE.value]):
                                self.current_address = data
                                self.state = NANDUnit.STATE_WAIT_DATA
                                   
                    elif self.state == NANDUnit.STATE_WAIT_DATA:
                        # Handle data-specific data
                        if self.signal[NANDUnit.TARGET_SIGNAL.CLE.value] > 0 :
                            if self.current_command == bytes([COMMAND.PROGRAM_PAGE_RANDOM_IN.value]):
                                self.state = NANDUnit.STATE_WAIT_ADDRESS
                                break
                        else:
                            if self.current_command == bytes([COMMAND.READ_PAGE_MSB.value]):
                                # Send page data
                                self.state = NANDUnit.STATE_WAIT_DATA_FROM_NAND
                                addr = ctypes.cast(self.current_address, ctypes.POINTER(address)).contents
                                block = self.lun[addr.row.s.lun].plane[addr.row.s.plane].block[addr.row.s.block]
                                self.signal[NANDUnit.TARGET_SIGNAL.RB.value] = 1
                                filename = self.get_filename(addr)

                                self.state = NANDUnit.STATE_TRASFERRING_DATA_FROM_NAND 
                                self.logger.debug("Read data from NAND. CMD:[{}], STATE:[{}], NAME:[{}].".format(self.current_command, self.state, filename))       
                                self.logger.debug("Page data sent")
                                
                                return NANDCoreUnit.CORE_ACTION.READ_FILE, \
                                        filename, \
                                        self.lun[addr.row.s.lun].plane[addr.row.s.plane].data_register, \
                                        self.busy_done
                                        
                            elif self.current_command == bytes([COMMAND.PROGRAM_PAGE.value]):
                                # Store page data
                                addr = ctypes.cast(self.current_address, ctypes.POINTER(address)).contents
                                self.lun[addr.row.s.lun].plane[addr.row.s.plane].data_register = data[:]
                                #if len(self.lun[addr.row.s.lun].plane[addr.row.s.plane].data_register) == PAGE_SIZE: # Replace with actual page size
                                    # Send program confirmation
                                #    self.lun[addr.row.s.lun].plane[addr.row.s.plane].data_register += b'\x00'
                                self.state = NANDUnit.STATE_IDLE
                                self.logger.debug("PROGRAM PAGE confirmation sent")
                                break
                            elif self.current_command == bytes([COMMAND.RANDOM_DATA_OUTPUT_MSB.value]):
                                if self.current_address:
                                    addr = ctypes.cast(self.current_address, ctypes.POINTER(address)).contents
                                    if self.lun[addr.row.s.lun].plane[addr.row.s.plane].data_register:
                                        self.state = NANDUnit.STATE_TRASFERRING_DATA_OUT
                                        return NANDCoreUnit.CORE_ACTION.DATA_OUT, \
                                                None, \
                                                self.lun[addr.row.s.lun].plane[addr.row.s.plane].data_register, \
                                                self.busy_done
                                    else:
                                        raise Exception("RANDOM_DATA_OUTPUT_MSB no data in register")  
                            elif self.current_command == bytes([COMMAND.READ_ID.value]):
                                if self.current_address:
                                    if self.current_address == b'\x00':
                                        self.current_data = b''
                                    elif self.current_address == b'\x40':
                                        self.current_data = b''
                                        
                                        self.state = NANDUnit.STATE_TRASFERRING_DATA_OUT
                                        return NANDCoreUnit.CORE_ACTION.DATA_OUT, \
                                                None, \
                                                self.current_data, \
                                                self.busy_done
                                        
                                        
                                else:
                                    raise Exception("READ_ID no data in register")              
                            self.logger.debug("Wait data. CMD:[{}], ADDR:[{}], STATE:[{}], LEN DR:[{}], LEN D:[{}].".format(self.current_command, self.current_address, self.state, 
                                                                                                   len(self.current_address, 
                                                                                                       self.lun[addr.row.s.lun].plane[addr.row.s.plane].data_register),
                                                                                                    len(data)))            
                              
                return core_action
            except Exception as msg:
                raise RuntimeError(msg)    