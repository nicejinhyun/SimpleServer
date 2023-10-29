import queue
import socket
import threading
from typing import Union, List
from functools import reduce
from _thread import *

HOST = '192.168.219.120'
PORT = 8899

class SimpleClient:
    clientSocket: Union[socket.socket, None] = None
    recvQueue = queue.Queue()

    def __init__(self):
        self.clientSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.clientSocket.connect((HOST, PORT))
        start_new_thread(self.onRecvData, (self.clientSocket,))

    def sendData(self, data):
        self.clientSocket.send(data)

    def onRecvData(self, sock: socket.socket):
        while True:
            data = sock.recv(1024)
            recvBuffer = bytearray()
            packet = []
            recvBuffer.extend(data)
            roomIndex = recvBuffer[6] & 0x0F
            for byte in recvBuffer:
                packet.append("{:02X}".format(byte))

            if packet[3] == '18':
                if packet[4] == '01':
                    pass
                elif packet[4] == '02':
                    print(f'18: cmd {packet}')
                elif packet[4] == '04':
                    print(f'18: resp {packet}')
            elif packet[3] == '19':
                if packet[4] == '02':
                    print(f'19: cmd {packet}')
                elif packet[4] == '04':
                    print(f'19: reps {packet}')
            elif packet[3] == '1C':
                if packet[4] == '02':
                    print(f'1C: cmd {packet}')
                elif packet[4] == '04':
                    print(f'1C: reps {packet}')
            elif packet[3] == '1B':
                if packet[4] == '02':
                    print(f'1B: cmd {packet}')
                elif packet[4] == '04':
                    print(f'1B: reps {packet}')
            elif packet[3] == '34':
                print(f'ele {packet}')

            #print(f'{packet}')
            #if roomIndex != 0 and recvBuffer[3] == 0x18:
            #    if recvBuffer[5] in [0x45, 0x46]:
            #        print(f'{packet}')
            """
            if recvBuffer[3] == 0x19:
                idx = recvBuffer.find(0xF7)
                if len(recvBuffer) >= recvBuffer[1]:
                    if recvBuffer[2] == 0x01:
            
            if recvBuffer[3] == 0x18:
                roomIndex = recvBuffer[6] & 0x0F
                if recvBuffer[4] == 0x04:
                    if roomIndex == 0:
                        thermostat_count = (len(recvBuffer) - 10) // 3
                        print(f'thermostat_count: {thermostat_count}')
                    else:
                        print(f'Thermostat: {recvBuffer}')
            """
            
def calcXORChecksum(data: Union[bytearray, bytes, List[int]]) -> int:
    return reduce(lambda x, y: x ^ y, data, 0)

if __name__ == '__main__':
    simpleClient = SimpleClient()
    keepAlive = True

    while True:
        msgSendData = input()
        if msgSendData == 'quit':
            break

        elif msgSendData == '1': 
            packet = bytearray([0xF7, 0x0B, 0x01, 0x34])
            packet.extend([0x02, 0x41, 0x10, 0x06, 0x00])
            packet.append(calcXORChecksum(packet))
            packet.append(0xEE)
            simpleClient.sendData(packet)

#        simpleClient.sendData(msgSendData.encode())
