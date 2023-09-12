'''
Created on 2023/5/24

@author: martinlee
'''
import ctypes
import socket
import threading
import asyncio
import utils
import traceback
from enum import Enum


    
class rp_pkt_hdr_t(ctypes.Structure):
    _pack_ = 1
    _fields_ = [('cmd', ctypes.c_uint32),
                ('len', ctypes.c_uint32),
                ('id', ctypes.c_uint32),
                ('flags', ctypes.c_uint32),
                ('dev', ctypes.c_uint32)
                ]
 
class rp_pkt_cfg_t(ctypes.Structure):
    _pack_ = 1
    _fields_ = [('hdr', rp_pkt_hdr_t),
                ('opt', ctypes.c_uint32),
                ('set', ctypes.c_uint8)
                ]
    
class rp_version_t(ctypes.Structure):
    _pack_ = 1
    _fields_ = [('major', ctypes.c_uint16),
                ('minor', ctypes.c_uint32),
                ]
    
class rp_capabilities_t(ctypes.Structure):
    _pack_ = 1
    _fields_ = [('offset', ctypes.c_uint32),
            ('len', ctypes.c_uint16),
            ('reserved0', ctypes.c_uint16)
            ]   

class rp_pkt_interrupt_t(ctypes.Structure):
    _pack_ = 1
    _fields_ = [('hdr', rp_pkt_hdr_t),
                ('timestamp', ctypes.c_uint64),
                ('vector', ctypes.c_uint64),
                ('line', ctypes.c_uint32),
                ('val', ctypes.c_uint8)
                ]

class rp_pkt_sync_t(ctypes.Structure):
    _pack_ = 1
    _fields_ = [('hdr', rp_pkt_hdr_t),
                ('timestamp', ctypes.c_uint64)
                ]
    
class rp_pkt_ats_t(ctypes.Structure):
    _pack_ = 1
    _fields_ = [('hdr', rp_pkt_hdr_t),
                ('timestamp', ctypes.c_uint64),
                ('attributes', ctypes.c_uint64),
                ('addr', ctypes.c_uint64),
                ('len', ctypes.c_uint64),
                ('result', ctypes.c_uint32),
                ('reserved0', ctypes.c_uint64),
                ('reserved1', ctypes.c_uint64),
                ('reserved2', ctypes.c_uint64),
                ('reserved3', ctypes.c_uint64)
                ]    

class rp_pkt_busaccess_t(ctypes.Structure):
    _pack_ = 1
    _fields_ = [('hdr', rp_pkt_hdr_t),
                ('timestamp', ctypes.c_uint64),
                ('attributes', ctypes.c_uint64),
                ('addr', ctypes.c_uint64),
                ('len', ctypes.c_uint32),
                ('width', ctypes.c_uint32),
                ('stream_width', ctypes.c_uint32),
                ('master_id', ctypes.c_uint16)
                ]    
    
class rp_pkt_busaccess_ext_base_t(ctypes.Structure):
    _pack_ = 1
    _fields_ = [('hdr', rp_pkt_hdr_t),
                ('timestamp', ctypes.c_uint64),
                ('attributes', ctypes.c_uint64),
                ('addr', ctypes.c_uint64),
                ('len', ctypes.c_uint32),
                ('width', ctypes.c_uint32),
                ('stream_width', ctypes.c_uint32),
                ('master_id', ctypes.c_uint16),
                ('master_id_31_16', ctypes.c_uint16),
                ('master_id_63_32', ctypes.c_uint32),
                ('data_offset', ctypes.c_uint32), 
                ('next_offset', ctypes.c_uint32), 
                ('byte_enable_offset', ctypes.c_uint32),
                ('byte_enable_len', ctypes.c_uint32)
                ]    
    
class rp_encode_busaccess_in_t(ctypes.Structure):
    _pack_ = 1
    _fields_ = [('cmd', ctypes.c_uint32),
                ('id', ctypes.c_uint32),
                ('flags', ctypes.c_uint32),
                ('dev', ctypes.c_uint32),
                ('clk', ctypes.c_uint64),
                ('master_id', ctypes.c_uint64),
                ('addr', ctypes.c_uint64),
                ('attr', ctypes.c_uint64),
                ('size', ctypes.c_uint32),
                ('width', ctypes.c_uint32),
                ('stream_width', ctypes.c_uint32),
                ('byte_enable_len', ctypes.c_uint32)
                ]      

class rp_pkt_hello(ctypes.Structure):
    _pack_ = 1
    _fields_ = [('hdr', rp_pkt_hdr_t),
                ('version', rp_version_t),
                ('caps', rp_capabilities_t)
                ]

class rp_pkt_t(ctypes.Union):

    _fields_ = [('hdr', rp_pkt_hdr_t),
                ('hello', rp_pkt_hello),
                ('busaccess', rp_pkt_busaccess_t),
                ('busaccess_ext_base', rp_pkt_busaccess_ext_base_t),
                ('interrupt', rp_pkt_interrupt_t),
                ('sync', rp_pkt_sync_t),
                ('ats', rp_pkt_ats_t)
                ]

    
class RP_RESP(Enum):
    OK                  =  0x0
    BUS_GENERIC_ERROR   =  0x1
    ADDR_ERROR          =  0x2
    MAX                 =  0xF

class RP_BUS(Enum):
    ATTR_EOP        =  1 << 0
    ATTR_SECURE     =  1 << 1
    ATTR_EXT_BASE   =  1 << 2
    ATTR_PHYS_ADDR  =  1 << 3
    ATTR_IO_ACCESS  =  (1 << 4)
    RESP_SHIFT      =  8
    RESP_MASK  =  (RP_RESP.MAX.value << RESP_SHIFT)

class RP_CMD(Enum):
    NOP         = 0
    HELLO       = 1
    CFG         = 2
    READ        = 3
    WRITE       = 4
    INTERRUPT   = 5
    SYNC        = 6
    ATS_REQ     = 7
    ATS_INV     = 8
    MAX         = 8

class RP_PKT_FLAGS(Enum):
    OPTIONAL    = 1 << 0
    RESPONSE    = 1 << 1
    POSTED      = 1 << 2

class MEMTX(Enum):
    OK = 0
    ERROR = (1 << 0) 
    DECODE_ERROR = (1 << 1)

class RP_LOGGER_LV(Enum):
    DEBUG = 0
    INFO = 1
    WARNING = 2
    ERROR = 3
    
high = b'\x01'
low = b'\x00'
empty_data = b''

def rp_decode_payload(pkt):
    rp_pkt = ctypes.cast(pkt, ctypes.POINTER(rp_pkt_t)).contents
    used = 0
    match rp_pkt.hdr.cmd: 
        case RP_CMD.HELLO.value:
            #assert(rp_pkt.hdr.len >= sizeof rp_pkt.hello.version);
            rp_pkt.hello.version.major = socket.ntohs(rp_pkt.hello.version.major)
            rp_pkt.hello.version.minor = socket.ntohs(rp_pkt.hello.version.minor)
            used += ctypes.sizeof(rp_pkt.hello.version)
    
            if rp_pkt.hdr.len - used >= ctypes.sizeof(hdr.hello.caps):
                rp_pkt.hello.caps.offset = socket.ntohl(rp_pkt.hello.caps.offset)
                rp_pkt.hello.caps.len = socket.ntohs(rp_pkt.hello.caps.len)
    
                for i in range(rp_pkt.hello.caps.len):
                    cap = ctypes.cast(ctypes.byref(rp_pkt, rp_pkt.hello.caps.offset +  i * ctypes.sizeof(ctypes.c_uint32)), ctypes.POINTER(ctypes.c_uint32)).contents
                    cap = ntohl(cap)
                    used += ctypes.sizeof(rp_pkt.hello.caps);
            else:
                rp_pkt.hello.caps.offset = 0
    
            used = rp_pkt.hdr.len

        case RP_CMD.WRITE.value | RP_CMD.READ.value:
            #assert(rp_pkt.hdr.len >= sizeof rp_pkt.busaccess - sizeof rp_pkt.hdr);
            rp_pkt.busaccess.timestamp = socket.ntohl(rp_pkt.busaccess.timestamp)
            rp_pkt.busaccess.addr = socket.ntohl(rp_pkt.busaccess.addr)
            rp_pkt.busaccess.attributes = socket.ntohl(rp_pkt.busaccess.attributes)
            rp_pkt.busaccess.len = socket.ntohl(rp_pkt.busaccess.len)
            rp_pkt.busaccess.width = socket.ntohl(rp_pkt.busaccess.width)
            rp_pkt.busaccess.stream_width = socket.ntohl(rp_pkt.busaccess.stream_width)
            master_id = socket.ntohs(rp_pkt.busaccess.master_id)
    
            used += ctypes.sizeof(rp_pkt_busaccess_t) -  ctypes.sizeof(rp_pkt_hdr_t)
    
            if rp_pkt.busaccess.attributes & RP_BUS.ATTR_EXT_BASE.value:
                #assert(rp_pkt.hdr.len >= sizeof *pext - sizeof rp_pkt.hdr)
                master_id |= socket.ntohs(rp_pkt.busaccess_ext_base.master_id_31_16) << 16
                master_id |= socket.ntohl(rp_pkt.busaccess_ext_base.master_id_63_32) << 32
                rp_pkt.busaccess_ext_base.data_offset = socket.ntohl(rp_pkt.busaccess_ext_base.data_offset)
                rp_pkt.busaccess_ext_base.next_offset = socket.ntohl(rp_pkt.busaccess_ext_base.next_offset)
                rp_pkt.busaccess_ext_base.byte_enable_offset = socket.ntohl(rp_pkt.busaccess_ext_base.byte_enable_offset)
                rp_pkt.busaccess_ext_base.byte_enable_len = socket.ntohl(rp_pkt.busaccess_ext_base.byte_enable_len)
    
                used += ctypes.sizeof(rp_pkt_busaccess_ext_base_t) - ctypes.sizeof(rp_pkt_busaccess_t)
            
            rp_pkt.busaccess.master_id = master_id

        case RP_CMD.INTERRUPT.value:
            rp_pkt.interrupt.timestamp = socket.ntohl(rp_pkt.interrupt.timestamp)
            rp_pkt.interrupt.vector = socket.ntohl(rp_pkt.interrupt.vector)
            rp_pkt.interrupt.line = socket.ntohl(rp_pkt.interrupt.line)
            rp_pkt.interrupt.val = rp_pkt.interrupt.val
            used += rp_pkt.hdr.len

        case RP_CMD.SYNC.value:
            rp_pkt.sync.timestamp = socket.ntohl(rp_pkt.interrupt.timestamp)
            used += rp_pkt.hdr.len

        case RP_CMD.ATS_REQ.value | RP_CMD.ATS_INV.value:
            rp_pkt.ats.attributes = socket.ntohl(rp_pkt.ats.attributes)
            rp_pkt.ats.addr = socket.ntohl(rp_pkt.ats.addr)
            rp_pkt.ats.len = socket.ntohl(rp_pkt.ats.len)
            rp_pkt.ats.result = socket.ntohl(rp_pkt.ats.result)
            
        case _:
            raise Exception('decodepayload cmd error!')
    
    return used

def rp_decode_hdr(pkt):
    hdr = ctypes.cast(pkt, ctypes.POINTER(rp_pkt_hdr_t)).contents
    used = 0
    hdr.cmd = socket.ntohl(hdr.cmd)
    hdr.len = socket.ntohl(hdr.len)
    hdr.id = socket.ntohl(hdr.id)
    hdr.dev = socket.ntohl(hdr.dev)
    hdr.flags = socket.ntohl(hdr.flags)
    used += ctypes.sizeof(rp_pkt_hdr_t)
    return hdr, used
    
def rp_busaccess_rx_dataptr(pkt):
    rp_pkt_busaccess = ctypes.cast(pkt, ctypes.POINTER(rp_pkt_busaccess_t)).contents
    if rp_pkt_busaccess.attributes & RP_BUS.ATTR_EXT_BASE.value:
        return pkt[pkt.data_offset:]
    else:
        return pkt[ctypes.sizeof(rp_pkt_busaccess_t):]
    
def rp_encode_hdr(hdr, cmd, id, dev, len, flags):
    hdr.cmd = socket.htonl(cmd)
    hdr.len = socket.htonl(len)
    hdr.id = socket.htonl(id)
    hdr.dev = socket.htonl(dev)
    hdr.flags = socket.htonl(flags)
    
def rp_encode_busaccess_common(pkt, clk, master_id, addr, attr, size, width, stream_width):
    pkt.timestamp = socket.htonl(clk)
    pkt.master_id = socket.htons(master_id)
    pkt.addr = socket.htonl(addr)
    pkt.attributes = socket.htonl(attr)
    pkt.len = socket.htonl(size)
    pkt.width = socket.htonl(width)
    pkt.stream_width = socket.htonl(stream_width)
 
def rp_encode_busaccess(buf, rsp_in):
    hsize = 0
    ret_size = 0
    #pkt = ctypes.cast(buf, ctypes.POINTER(rp_pkt_busaccess_t)).contents
    pkt = rp_pkt_busaccess_t.from_buffer(buf)
    resp_flags = rsp_in.flags & RP_PKT_FLAGS.RESPONSE.value
    attr_flags = rsp_in.attr & RP_BUS.ATTR_EXT_BASE.value
    if rsp_in.cmd == RP_CMD.WRITE.value and not resp_flags:
        hsize = rsp_in.size
    
    if rsp_in.cmd == RP_CMD.READ.value and resp_flags:
        hsize = rsp_in.size
        ret_size = rsp_in.size
        
    if not attr_flags:

        rp_encode_hdr(pkt.hdr, rsp_in.cmd, rsp_in.id, rsp_in.dev,
                      ctypes.sizeof(rp_pkt_busaccess_t) - ctypes.sizeof(rp_pkt_hdr_t) + hsize, rsp_in.flags);
        rp_encode_busaccess_common(pkt, rsp_in.clk, rsp_in.master_id,
                                   rsp_in.addr, rsp_in.attr,
                                   rsp_in.size, rsp_in.width, rsp_in.stream_width)
        return  ctypes.sizeof(rp_pkt_busaccess_t) + ret_size
    
    pkt.master_id_31_16 = socket.htons(rsp_in.master_id >> 16)
    pkt.master_id_63_32 = socket.htonl(rsp_in.master_id >> 32)

    pkt.data_offset = socket.htonl(ctypes.sizeof(rp_pkt_busaccess_t))
    pkt.next_offset = 0

    pkt.byte_enable_offset = socket.htonl(ctypes.sizeof(rp_pkt_busaccess_t) + hsize)
    pkt.byte_enable_len = socket.htonl(rsp_in.byte_enable_len)
    hsize += rsp_in.byte_enable_len

    rp_encode_hdr(pkt.hdr, rsp_in.cmd, rsp_in.id, rsp_in.dev,
                      ctypes.sizeof(rp_pkt_busaccess_t) - ctypes.sizeof(rp_pkt_hdr_t) + hsize, rsp_in.flags)
    
    rp_encode_busaccess_common(pkt, rsp_in.clk, rsp_in.master_id,
                                   rsp_in.addr, rsp_in.attr | RP_BUS.ATTR_EXT_BASE.value,
                                   rsp_in.size, rsp_in.width, rsp_in.stream_width)
    
    return  ctypes.sizeof(rp_pkt_busaccess_t) + ret_size

def rp_encode_busaccess_ba(buf, rsp_in):
    buf_bytes = (ctypes.c_char * ctypes.sizeof(rp_pkt_busaccess_ext_base_t)).from_buffer(buf)
    return  rp_encode_busaccess(buf_bytes, rsp_in)     

def rp_get_busaccess_response(pkt):
    rp_pkt_busaccess = ctypes.cast(pkt, ctypes.POINTER(rp_pkt_busaccess_t)).contents
    return (rp_pkt_busaccess.attributes & RP_BUS.RESP_MASK.value) >> RP_BUS.RESP_SHIFT.value

class rp_encode_busaccess_in_rsp(rp_encode_busaccess_in_t):
    def __init__(self, pkt):
        super().__init__( pkt.hdr.cmd, pkt.hdr.id, pkt.hdr.flags | RP_PKT_FLAGS.RESPONSE.value, pkt.hdr.dev, 0, pkt.busaccess.master_id, \
                          pkt.busaccess.addr, 0, pkt.busaccess.len, pkt.busaccess.width, pkt.busaccess.stream_width, 0)
        
class rp_encode_busaccess_base_dpkt(rp_pkt_busaccess_ext_base_t):
    def __init__(self, pkt):
        super().__init__( pkt.hdr.cmd, pkt.hdr.id, pkt.hdr.flags | RP_PKT_FLAGS.RESPONSE.value, pkt.hdr.dev, 0, pkt.busaccess.master_id, \
                          pkt.busaccess.addr, 0, pkt.busaccess.len, pkt.busaccess.width, pkt.busaccess.stream_width, 0)

def rp_dpkt_alloc(st, data_size):
    buffer = ctypes.create_string_buffer(ctypes.sizeof(st) + data_size)
    return buffer

def rp_dpkt_alloc_ba(st, offset):
    buffer_size = ctypes.sizeof(st) + offset
    byte_array = bytearray(buffer_size)
    address = id(byte_array) + offset
    char_array = (ctypes.c_char * ctypes.sizeof(st)).from_address(address)
    return char_array
 
class rp_controller:
    def __init__(self, core):
        if not hasattr(core, 'reader') or not hasattr(core, 'writer'):
            raise ValueError("There have no reader or writer.")
        self.core = core
        self.id = 0
        self.id_lock = threading.Lock()
        
    
    def new_id(self):
        with self.id_lock:
            temp_id = self.id
            self.id += 1
            
        return temp_id
    
    async def read_packet(self):
        try:
            pkt = await self.core.reader.read(ctypes.sizeof(rp_pkt_hdr_t))
            if pkt:
                #hdr = rp_pkt_hdr.from_buffer(pkt)
                hdr, used = rp_decode_hdr(pkt)
                self.core.logger.debug('read_packet, pkt dev:{}, pkt len:{}.'.format(hdr.dev, hdr.len))
                
                #hdr = rp_pkt_hdr.from_buffer(pkt)
                if hdr.len > 0 :
                    data = await self.core.reader.read(hdr.len)
                    pkt+=data
                    rp_decode_payload(pkt)
                
            return pkt
        except asyncio.IncompleteReadError:
            pass  # Client disconnected abruptly 
        except Exception as msg:
            print("{}".format(msg))
    
    async def write_rsp_packet(self, pkt, data):
        try:
            rp_pkt = ctypes.cast(pkt, ctypes.POINTER(rp_pkt_t)).contents
            rsp = rp_encode_busaccess_in_rsp(rp_pkt)
            dpkt_buf = bytearray(ctypes.sizeof(rp_pkt_busaccess_t))
            pkt_len = rp_encode_busaccess(dpkt_buf, rsp)
            
            if rp_pkt.hdr.cmd == RP_CMD.READ.value:
                pkt_len += len(data)
                dpkt_buf.extend(data)
                
            self.core.writer.write(bytes(dpkt_buf))
            await self.core.writer.drain()
        except ValueError as msg:
            print("Value error : {}".format(msg))
        except Exception as msg:
            print("Exception : {}".format(msg))
                    
    async def send_signal(self, cmd, pin, data):
        try:
            rsp_data = b''
            pkt_len = 0
            dpkt_buf = bytearray(ctypes.sizeof(rp_pkt_busaccess_t))
    
            #dpkt_buf = rp_dpkt_alloc(rp_pkt_busaccess_ext_base_t, len(data))
            #dpkt = ctypes.cast(dpkt_buf, ctypes.POINTER(rp_pkt_busaccess_ext_base)).contents
            #buf_bytes = (ctypes.c_char * ctypes.sizeof(rp_pkt_busaccess_t)).from_buffer(dpkt_buf)
    
            pkt_in = rp_encode_busaccess_in_t()
            pkt_in.cmd = cmd
            pkt_in.id = self.new_id()
            pkt_in.dev = pin
            pkt_in.clk = 0
            pkt_in.master_id = 0
            pkt_in.addr = 0
            pkt_in.attr = 0
            pkt_in.size = len(data)
            pkt_in.stream_width = len(data)
            pkt_len = rp_encode_busaccess(dpkt_buf, pkt_in)
        
            if pkt_in.cmd == RP_CMD.WRITE.value:  
                pkt_len += len(data)
                dpkt_buf.extend(data)
            
             
            
            self.core.writer.write(bytes(dpkt_buf))
            await self.core.writer.drain()
            
            rsp_pkt = await self.read_packet()
            
            
            resp = rp_get_busaccess_response(rsp_pkt)
            
            match resp:
                case RP_RESP.OK.value:
                    ret = MEMTX.OK
                case RP_RESP.ADDR_ERROR.value:
                    ret = MEMTX.DECODE_ERROR
                    raise Exception("MEMTX.DECODE_ERROR")
                case _:
                    ret = MEMTX.ERROR
                    raise Exception("MEMTX.ERROR")
            
            if pkt_in.cmd == RP_CMD.READ:
                rsp_data = rp_busaccess_rx_dataptr(rsp_pkt);
            
            return rsp_data
        except Exception as msg:
            print(traceback.format_exc())  