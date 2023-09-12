'''
Created on 2023/5/18

@author: martinlee
'''
import os
import logging
import glob
import ctypes
import time
import asyncio
import time 
import argparse
import binascii
import NANDUnit
from core import NANDCore
import NANDCoreUnit
import inspect
import pycstruct
import sys

separator = ", "
def revise_path(path):
    # Replace backslashes with forward slashes
    uni_path = path.replace('\\', '/')
    uni_path = uni_path.replace('\\\\', '/')
    
    if ':' in uni_path:
        drive_letter, uni_path = uni_path.split(':', 1)
    
    uni_path = '/{}{}'.format(*drive_letter, uni_path)
  

    return uni_path

def get_nand_files_list(): 
    # list to store files name
   
    try:
        project_root = os.path.dirname(__file__)
        dir_path = os.path.join(project_root, 'NAND')
        res = []
        for dir_path, dirs_name, files_name in os.walk(dir_path, topdown = True):
            for file_name in files_name:
                if file_name.endswith(".py") and \
                    file_name != "core.py" and \
                    file_name != "NANDUnit.py": \
                    res.append(os.path.splitext(file_name)[0])
        return res
    except Exception as msg:
                raise Exception("get_nand_files_list error : {}".format(msg))    

def get_logger(device_name):
    dev_logger: logging.Logger = logging.getLogger(name=device_name)
    dev_logger.setLevel(logging.DEBUG)
    handler: logging.StreamHandler = logging.StreamHandler()
    formatter: logging.Formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    dev_logger.addHandler(handler)
    return dev_logger

async def loading_animation(title):
    animation_frames = ["|", "/", "-", "\\"]
    # Create the loading animation
    for i in range(20):  # Adjust the range value to change the number of animation frames
        time.sleep(0.1)  # Adjust the sleep duration to control the speed of the animation
        frame = animation_frames[i % len(animation_frames)]
        print(f"\r{title} {frame}", end="", flush=True)
        await asyncio.sleep(0.01)
        
def convert_bytes_to_structure(st, byte):
    # sizoef(st) == sizeof(byte)
    ctypes.memmove(ctypes.addressof(st), byte, ctypes.sizeof(st))


def convert_struct_to_bytes(st):
    buffer = ctypes.create_string_buffer(ctypes.sizeof(st))
    ctypes.memmove(buffer, ctypes.addressof(st), ctypes.sizeof(st))
    return buffer.raw


def convert_int_to_bytes(number, size):
    return (number).to_bytes(size, 'big')    
    

class ByteAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        try:
            byte_value = int(values)
            if byte_value < 0 or byte_value > 255:
                raise argparse.ArgumentError(self, "Byte value must be between 0 and 255.")
            setattr(namespace, self.dest, byte_value)
        except ValueError:
            raise argparse.ArgumentError(self, "Invalid byte value.")
        
def bytes_type(value):
    # Custom type function to parse bytes
    try:
        byte_value = int(value)
        if 0 <= byte_value <= 255:
            return byte_value
    except ValueError:
        pass
    raise argparse.ArgumentTypeError(f"{value} is not a valid byte value (0-255)")

def hex_byte(value):
    try:
        # Convert the hexadecimal string to an integer
        int_value = int(value, 16)

        # Check if the integer value is within the byte range (0-255)
        if 0 <= int_value <= 255:
            # Return the byte value
            return int_value.to_bytes(1, 'big')

        raise argparse.ArgumentTypeError(f"Invalid byte value: {value}")
    except ValueError:
        raise argparse.ArgumentTypeError(f"Invalid hexadecimal value: {value}")
    
def byte_data_type(value):
    try:
        # Convert the input string to bytes
        byte_data = bytes.fromhex(value)
        return byte_data
    except ValueError:
        raise argparse.ArgumentTypeError("Invalid byte data format")

def prefix_type(value):
    try:
        # Convert the input string to bytes
        if len(value) == 2:
            byte_data = bytes.fromhex(value)
        else:
            raise argparse.ArgumentTypeError("Error length.")
        return byte_data
    
    except ValueError as msg:
        raise argparse.ArgumentTypeError(msg)
      
def parse_hex(data):
    try:
        # Remove leading '\x' and convert the remaining hex characters
        data = data.replace("\\x", "")
        binary_data = binascii.unhexlify(data)
        return binary_data
    except binascii.Error:
        raise argparse.ArgumentTypeError("Invalid hexadecimal input")
    
class MaxLengthAction(argparse.Action):
    def __init__(self, option_strings, dest, nargs=None, **kwargs):
        self.max_length = kwargs.pop('max_length', None)
        super(MaxLengthAction, self).__init__(option_strings, dest, nargs=nargs, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        if self.max_length is not None and len(values) > self.max_length:
            parser.error(f"Length of '{self.dest}' argument exceeds maximum length of {self.max_length}")
        setattr(namespace, self.dest, values)

def get_current_function_name():
    return inspect.currentframe().f_code.co_name

def get_filename(block_type_name, lun, plane, block, page):
        
        filename = 'LUN_{}_PLANE_{}_BLOCK_{}_PAGE_{}_TYPE_{}'.format(block_type_name, lun, plane, block, page)
            
        return filename
    
def parse_c_structure(): 
    file = inspect.getfile(sys._getframe(2))   
    nand_root = os.path.dirname(file)
    filename_ext = os.path.basename(file)
    filename = os.path.splitext(filename_ext)[0]
    output_path = os.path.join(nand_root, 'include', f'{filename}.h')
    return pycstruct.parse_file(output_path)