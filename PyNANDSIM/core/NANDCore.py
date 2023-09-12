'''
Created on 2023/5/12

@author: martinlee
'''
import asyncio
import argparse
import struct
import socket
import NANDCoreUnit
import ctypes
from nand import NANDUnit
import os
import utils
import logging
import packet
import re
import sys
import fnmatch
import inspect
import traceback
from numpy.random.mtrand import choice
        

def die_task_cb(task):
    try:
        result = task.result()
        result.logger.debug('Die task done:{}.'.format(task.get_name()))
        """
        match = re.match(r"Packa(\d+)_Channel_(\d+)_Target_(\d+)", task.get_name())

        if match:
            package_ce = 0
            for ce in range(NANDCoreUnit.SIM_CE):
                if ce != 0 and (ce % self.args.package_target) == 0:
                    package_ce += args.sim_ch // args.package_channel
                package_ch = 0
                for ch in range(NANDCoreUnit.SIM_CHANNEL):
                    if ch < self.args.sim_ch:
                        if ch != 0 and (ch % args.package_channel) == 0:
                            package_ch += 1
                        package = package_ch + package_ce
                        ch_in_package = ch % self.args.package_channel
                        target_in_package = ce % self.args.package_target
                        self.target_mapping.append(NANDCoreUnit.Target_mapping(package, ch_in_package, target_in_package)) 
                    else:
                        self.target_mapping.append(None)
            die_num = int(match.group(1)) * result.args.package_channel * result.args.package_target + \
                      int(match.group(2)) * result.args.package_target +\
                      int(match.group(3))
            """
        die_num = int(task.get_name())
        result.target_mapping[die_num].task = None 
    except Exception as msg:
        print(traceback.format_exc())          
               
class Core:
    def __init__(self, args):
        try:
            self.args = args
            # get the current working directory
            self.current_dir = os.getcwd()
            self.file_dir = os.path.join(os.getcwd(), 'nand_data')
            self.reader = None
            self.writer = None
            self.target_mapping = []
            self.rp_controller = packet.rp_controller(self)
            if (args.sim_ch * args.sim_ce) != ( args.num_package * args.package_channel * args.package_target):
                raise Exception("Package can't fit NANDCard configuration.")
            self.logger = utils.get_logger('NANDCore')
            self.package_channel_signal = len(NANDCoreUnit.CHANNEL_SIGNAL) * args.package_channel
            self.total_channel_signal = len(NANDCoreUnit.CHANNEL_SIGNAL) * NANDCoreUnit.SIM_CHANNEL
            self.total_packgage_signal = self.total_channel_signal * args.package_channel
            self.nand_card = NANDCoreUnit.NANDCard(args.manufacturer, args.part_number, args.num_package, args.package_channel, args.package_target)
            self.init_target_mapping()
            self.die_task = [None] * ( NANDCoreUnit.SIM_CE * NANDCoreUnit.SIM_CHANNEL )
        except Exception as msg:
            print(traceback.format_exc())             
        
    def init_target_mapping(self):
        package_ce = 0
        for ce in range(NANDCoreUnit.SIM_CE):
            if ce != 0 and (ce % self.args.package_target) == 0:
                package_ce += args.sim_ch // args.package_channel
            package_ch = 0
            for ch in range(NANDCoreUnit.SIM_CHANNEL):
                if ch < self.args.sim_ch:
                    if ch != 0 and (ch % args.package_channel) == 0:
                        package_ch += 1
                    package = package_ch + package_ce
                    ch_in_package = ch % self.args.package_channel
                    target_in_package = ce % self.args.package_target
                    self.target_mapping.append(NANDCoreUnit.Target_mapping(package, ch_in_package, target_in_package)) 
                else:
                    self.target_mapping.append(None)
                    
    # Disconnect callback function
    def disconnect_handler(self):
    # Perform cleanup for the disconnected client
        print('Client disconnected')
        self.writer.close()
    async def __aenter__(self):
        print(f"Server started on {self.args.addr}:{self.args.port}")
        self.connect_ani = asyncio.create_task(self.wait_connect_animation())
        self.server = await asyncio.start_server(self.handle_client, self.args.addr, self.args.port)
        
        return self
    
    async def __aexit__(self, exc_type, exc_value, traceback):
        if self.server is not None:
            self.server.close()
            await self.server.wait_closed()
            print("Server stopped")

    async def write_file(self, filename, data):
        filepath = os.path.join(self.file_dir, f'{filename}.bin')
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        with open(filepath, 'wb') as file:
            file.write(data)
            file.flush()
        
    async def read_file(self, filename, data):
        data = b''
        filepath = '{}.bin'.format(filename)
        if os.path.exists(filepath) :
            with open(filepath, 'rb') as file:
                data = await file.read()  
    
    async def remove_file(self, filename):
        for root, dirs, files in os.walk(self.file_dir):
            for name in files:
                if fnmatch.fnmatch(name, filename):
                    await os.remove(os.path.join(root, dirs, name)) 
                                 
    async def core_process_result(self, target, pkt, action):
        try:
            
            if action is not None:
                
                if action == NANDCoreUnit.CORE_ACTION.WRITE_FILE:
                    target.set_signal_high(NANDUnit.TARGET_SIGNAL.RB.value)
                    await self.rp_controller.write_rsp_packet(pkt, packet.empty_data)
                    for wl_cache in target.get_wl_cache():
                        
                        filename = utils.get_filaename( wl_cache.block_type.name,\
                                                       wl_cache.lun,\
                                                       wl_cache.plane,\
                                                       wl_cache.block,\
                                                       wl_cache.page)
                        
                        page_status = target.get_page_status(wl_cache.lun, wl_cache.plane, wl_cache.block, wl_cache.page)
                        
                        if page_status.value == NANDUnit.PAGE_STATUS.EMPTY.value:
                            target.set_page_status( wl_cache.lun, \
                                                    wl_cache.plane, \
                                                    wl_cache.block, \
                                                    wl_cache.page, \
                                                    NANDUnit.PAGE_STATUS.PROGRAMMED)  
                        else:
                            target.logger.warning(f"Over programed. Filename:{filename}. status:{page_status}.")
                            target.set_page_status( wl_cache.lun, \
                                                    wl_cache.plane, \
                                                    wl_cache.block, \
                                                    wl_cache.page, \
                                                    NANDUnit.PAGE_STATUS.OVER_PROGRAMMED)
                        
                        await self.write_file(filename, wl_cache.data)
                        
                    target.busy_done()
                elif action == NANDCoreUnit.CORE_ACTION.READ_FILE:
                    target.set_signal_high(NANDUnit.TARGET_SIGNAL.RB.value)
                    await self.rp_controller.write_rsp_packet(pkt, packet.empty_data)
                    for wl_cache in target.get_wl_cache():
                        addr = wl_cache.addr
                        filename = utils.get_filename(addr.lun, addr.plane, addr.block, page = addr.page)
                        await self.read_file(filename, wl_cache.data)
                    target.busy_done()
                elif action == NANDCoreUnit.CORE_ACTION.DATA_OUT:
                    target.set_signal_high(NANDUnit.TARGET_SIGNAL.RB.value)
                    for wl_cache in target.get_wl_cache():
                        await self.rp_controller.write_rsp_packet(pkt, wl_cache.data)
                    target.busy_done()
                elif action == NANDCoreUnit.CORE_ACTION.ERASE_FILE:
                    target.set_signal_high(NANDUnit.TARGET_SIGNAL.RB.value)
                    await self.rp_controller.write_rsp_packet(pkt, packet.empty_data)
                    plane = None
                    for wl_cache in target.get_wl_cache():
                        addr = wl_cache.addr
                        if plane is None:
                            plane = addr.plane
                        else:
                            plane += 1
                            
                        if addr.plane != plane:
                            raise ValueError(f'Erase error. Plane mismatch. Current:{plane}, Addr:{addr.plane}')
                        
                        filename = utils.get_filename(addr.lun, addr.plane, addr.block)
                        
                        await self.remove_file(filename)
                                
                        target.erase(wl_cache.prefix, addr)
                    target.busy_done()
                    
                    
            else:
                await self.rp_controller.write_rsp_packet(pkt, packet.empty_data)
            
        except Exception as msg:
            print(traceback.format_exc())            
        
    async def core_process_signal(self, target, pkt):
        try:
            dpkt = ctypes.cast(pkt, ctypes.POINTER(packet.rp_pkt_busaccess_t)).contents
            action= await target.process_signal(pkt[-dpkt.len:])
            await self.core_process_result(target, pkt, action)
            
            return self
        
        except Exception as msg:
            print(traceback.format_exc())       
        
    async def handle_client(self, reader, writer):
        self.reader = reader
        self.writer = writer
        self.connect_ani.cancel()
        print("\nClient connected")
        
        while True:
            try:
                pkt = await self.rp_controller.read_packet()
                if not pkt:
                    break
                dpkt = ctypes.cast(pkt, ctypes.POINTER(packet.rp_pkt_busaccess_t)).contents
                num_target = dpkt.hdr.dev // len(NANDUnit.TARGET_SIGNAL)
                pin = dpkt.hdr.dev % len(NANDUnit.TARGET_SIGNAL)
                target_mapping = self.target_mapping[num_target]
                target = self.nand_card.package[target_mapping.package].channel[target_mapping.channel].target[target_mapping.target]
                
                if pin < NANDUnit.TARGET_SIGNAL.DQ.value:
                    current_value = target.get_signal(pin)
                    value = pkt[-1:]
                    if dpkt.len == 1 :
                        if pkt[-1:] == current_value :
                            raise RuntimeError("Package:{}, channel:{}, target:{},  pin value : {} is same .".format(target_mapping.package, target_mapping.channel, target_mapping.target, value))
                        else:
                            if value == packet.high:
                                target.set_signal_high(pin)
                            elif value == packet.low:
                                target.set_signal_low(pin)
                            else:
                                raise RuntimeError("Target signal value error : {} should be low or high.".format(value))
                            
                            await self.rp_controller.write_rsp_packet(pkt, packet.empty_data)
                    else:
                        raise RuntimeError("Enable target data size : {} should be a byte.".format(dpkt.len))
                elif pin >= NANDUnit.TARGET_SIGNAL.DQ.value:   
                    if pin == NANDUnit.TARGET_SIGNAL.DQ.value :
                        task_name = '{}'.format(num_target)
                        task = asyncio.create_task(self.core_process_signal(target, pkt), name=task_name)
                        task.add_done_callback(die_task_cb)
                        self.target_mapping[num_target].task = task
                else:
                    raise RuntimeError("Error pin : {}.".format(pin))        
                        
            
            except Exception as msg:
                print(traceback.format_exc())       
             
        writer.close()
        await writer.wait_closed()
        self.connect_ani = asyncio.create_task(self.wait_connect_animation())
        print("\nClient disconnected")    

    async def wait_connect_animation(self):
        while True:
            await utils.loading_animation('Waiting for connection...')
            
async def main(args):
    
    async with Core(args) as core:
        
        try:
            
            await core.server.serve_forever()
            print('5')
        except KeyboardInterrupt:
            # Code to handle the Ctrl+C interruption
            print("\nCtrl+C detected. Exiting gracefully...\n")
        except Exception as msg:
            print(traceback.format_exc())      
            sys.exit(1)    
            
if __name__ == '__main__':
    
    nand_files_list = utils.get_nand_files_list()
    
    parser = argparse.ArgumentParser()
    parser.add_argument('-sch', '--sim-ch', type=int, choices=range(1, 64), help="Range 1 - 64 channels.",  default=1)
    parser.add_argument('-sce', '--sim-ce', type=int, choices=range(1, 64), help="Range 1 - 64 chips enable.",  default=1)
    parser.add_argument('-pch', '--package-channel', type=int, choices=range(1, 4), help="Range 1 - 4 channels.",  default=1)
    parser.add_argument('-ptar', '--package-target', type=int, choices=range(1, 4), help="Range 1 - 4 targets.",  default=1)
    parser.add_argument('-pkg', '--num-package', type=int, choices=[1 << i for i in range(5)], help=utils.separator.join(str(item) for item in [1 << i for i in range(5)]), default=1)
    parser.add_argument('-m', '--manufacturer', type=str.lower, choices=NANDUnit.NAND_MANUFACTURES, help=utils.separator.join(str(item) for item in NANDUnit.NAND_MANUFACTURES), required=True)
    parser.add_argument('-pn', '--part-number', type=str.upper, choices=nand_files_list, help=utils.separator.join(str(item) for item in nand_files_list), required=True)
    parser.add_argument('-a', '--addr', type=str, choices=range(1, 64), help="Default addr 127.0.0.1.",  default='127.0.0.1')
    parser.add_argument('-p', '--port', type=int, choices=range(0, 65535), help="Default port 6666.",  default=6666)
    args = parser.parse_args()
    
    asyncio.run(main(args))