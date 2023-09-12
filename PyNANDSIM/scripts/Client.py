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
from core import NANDCoreUnit
from nand import NANDUnit
from scripts import NANDCoreClient
from scripts import NANDInstruction
from scripts.instruction import toshiba             
from test.inspect_stock_annotations import function
    
async def main(args):
    async with NANDCoreClient.Core(args.addr, args.port) as core:
        try:
            while True:
                command = input("Enter a command (or 'quit' to exit): ")               
                if command == 'quit':
                    break
                else:
                    try:
                        command_list = command.split()
                        args = core.signal_parser.parse_args(command_list[1:])
                        
                        match command_list[0]:
                            case 'inst':
                                inst = NANDInstruction.nand_inst_base(core) 
                            case 'tsb_inst':
                                inst = toshiba.inst_base(core) 
                            case _:
                                raise Exception("not supported command.")
                             
                        data = await NANDInstruction.exec_function(inst, args)
                    except SystemExit as msg:
                        continue
                    except Exception as msg:
                        print(traceback.format_exc())  
            
                print('---Command successful---')
        except KeyboardInterrupt:
            # Code to handle the Ctrl+C interruption
            print("\nCtrl+C detected. Exiting gracefully...\n")      
        
if __name__ == '__main__':
    
    nand_files_list = utils.get_nand_files_list()
    
    parser = argparse.ArgumentParser()
    parser.add_argument('-a', '--addr', type=str, choices=range(1, 64), help="Default addr 127.0.0.1.",  default='127.0.0.1')
    parser.add_argument('-p', '--port', type=int, choices=range(0, 65535), help="Default port 6666.",  default=6666)
    args = parser.parse_args()
    
    asyncio.run(main(args))
      
