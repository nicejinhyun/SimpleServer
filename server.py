import queue
import socket
import sys
import time
import threading

from functools import reduce
from typing import Union, List

#SERVER = socket.gethostbyname(socket.gethostname())
SERVER = '127.0.0.1'
#SERVER = '192.168.0.100'
PORT = 9999

class ThreadSend(threading.Thread):
    keepAlive = True
    sock: Union[socket.socket, None] = None
    def __init__(self, sock: socket.socket, queueSend: queue.Queue):
        threading.Thread.__init__(self, name='ThreadSend')
        self.sig_send_data = Callback(bytes)
        self.sock = sock
        self.queueSend = queueSend
    
    def run(self):
        while self.keepAlive:
            try:
                if not self.queueSend.empty():
                    data = self.queueSend.get()
                    self.sock.send(data)
                    self.sig_send_data.emit(data)
                else:
                    time.sleep(1e-3)
            except Exception as e:
                print(f'{e}')
    
    def stop(self):
        self.keepAlive = False

class ThreadRecv(threading.Thread):
    keepAlive = True

    def __init__(self, sock: socket.socket, addr: dict, queueRecv: queue.Queue):
        threading.Thread.__init__(self, name='ThreadRecv')
        self.sig_recv_data = Callback(bytes)
        self.sig_terminated = Callback()
        self.sock = sock
        self.queueRecv = queueRecv
        self.addr = addr

    def run(self):
        while self.keepAlive:
            try:
                data = self.sock.recv(1024)
                if data is not None:
                    self.sig_recv_data.emit(data)
                else:
                    print(f'>>> Disconnect by {self.addr[0]} : {self.addr[1]}')
                    self.sig_terminated.emit()
                    self.keepAlive = False
            except ConnectionResetError as e:
                print(f'>>> Disconnect by {self.addr[0]} : {self.addr[1]}')
                self.sig_terminated.emit()
                self.keepAlive = False

    def stop(self):
        self.keepAlive = False

class ThreadManagerClient(threading.Thread):
    keepAlive = True
    def __init__(self, sock: socket.socket):
        threading.Thread.__init__(self, name="ThreadManagerClient")
        self.sig_client_connect = Callback()
        self.sock = sock
    
    def run(self):
        while self.keepAlive:
            clientSocket, clientAddr = self.sock.accept()
            print(f'{clientAddr}')
            self.sig_client_connect.emit(clientSocket, clientAddr)

class Callback(object):
    _args = None
    _callback = None

    def __init__(self, *args):
        self._args = args

    def connect(self, callback):
        self._callback = callback
    
    def emit(self, *args):
        if self._callback is not None:
            self._callback(*args)

class SimpleClient:
    sock: Union[socket.socket, None] = None
    threadSend: Union[ThreadSend, None] = None
    threadRecv: Union[ThreadRecv, None] = None
    threadManagerClient: Union[ThreadManagerClient, None] = None
    recvBuffer: bytearray

    Devices = {
        'Thermostat': [
            {'state': 0x04, 'currTherm': 0x19, 'targetTherm': 0x11},
            {'state': 0x04, 'currTherm': 0x19, 'targetTherm': 0x11},
            {'state': 0x04, 'currTherm': 0x19, 'targetTherm': 0x11},
            {'state': 0x04, 'currTherm': 0x19, 'targetTherm': 0x11}
        ],
        'Light': [0x02, 0x02, 0x02, 0x02],
        'Airconditioner': [
            {'state': 0x02, 'currTherm': 0x11, 'targetTherm': 0x11},
            {'state': 0x02, 'currTherm': 0x11, 'targetTherm': 0x11},
            {'state': 0x02, 'currTherm': 0x11, 'targetTherm': 0x11},
            {'state': 0x02, 'currTherm': 0x11, 'targetTherm': 0x11}
        ],
        'GasValve': [0x03],
        'Ventilator': [0x02]
    }

    def __init__(self):
        self.recvBuffer = bytearray()
        self.sig_send_data = Callback(bytes)
        self.sig_recv_data = Callback(bytes)
        self.queueSend = queue.Queue()
        self.queueRecv = queue.Queue()
        self.connect()
    
    def connect(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((SERVER, PORT))
        self.sock.listen()
        self.startThreadManagerClient()

    def disconnect(self):
        self.sock.close()

    def startThreadSend(self, sock: socket.socket):
        if self.threadSend is None:
            self.threadSend = ThreadSend(sock, self.queueSend)
            self.threadSend.sig_send_data.connect(self.onSendData)
            self.threadSend.daemon = True
            self.threadSend.start()
        
    def startThreadRecv(self, sock: socket.socket, addr: dict):
        if self.threadRecv is None:
            self.threadRecv = ThreadRecv(sock, addr, self.queueRecv)
            self.threadRecv.sig_recv_data.connect(self.onRecvData)
            self.threadRecv.sig_terminated.connect(self.onRecvDisconnected)
            self.threadRecv.daemon = True
            self.threadRecv.start()

    def startThreadManagerClient(self):
        if self.threadManagerClient is None:
            self.threadManagerClient = ThreadManagerClient(self.sock)
            self.threadManagerClient.sig_client_connect.connect(self.onManageClient)
            self.threadManagerClient.daemon = True
            self.threadManagerClient.start()

    def stopThreadSend(self):
        if self.threadSend is not None:
            self.threadSend.stop()
            self.threadSend = None

    def stopThreadRecv(self):
        if self.threadRecv is not None:
            self.threadRecv.stop()
            self.threadRecv = None

    def sendData(self, data: Union[bytes, bytearray]):
        print(f'sendData: {data}')
        self.queueSend.put(bytes(data))

    def onSendData(self, data: bytes):
        self.sig_send_data.emit(data)

    def convert(byte_str: str):
        return bytearray([int(x, 16) for x in byte_str.split(' ')])        

    @staticmethod
    def calcXORChecksum(data: Union[bytearray, bytes, List[int]]) -> int:
        return reduce(lambda x, y: x ^ y, data, 0)

    def onRecvData(self, data: bytes):
        recvBuffer = bytearray()
        recvBuffer.extend(data)

        deviceId = recvBuffer[3]

        print(f'deviceId {deviceId}')
        print(f'state: {recvBuffer[3]}')

        if recvBuffer[4] == 0x02:
            print(f'{recvBuffer}')
            if deviceId == 0x18: # Thermostat
                # F7 0B 01 18 02 45 XX YY 00 ZZ EE
                # F7 0D 01 18 04 45 XX 18 01 1A 18 A8 EE
                # XX: 상위 4비트 = 1, 하위 4비트 = Room Index
                # YY: 온도 설정값
                print(f'{recvBuffer}')
                thermCmd = recvBuffer[5]
                if thermCmd == 0x45:
                    roomIndex = recvBuffer[6] >> 4
                    targetTherm = recvBuffer[7]
                    self.Devices['Thermostat'][roomIndex]['targetTherm'] = targetTherm
                    if targetTherm > self.Devices['Thermostat'][roomIndex]['currTherm']:
                        self.Devices['Thermostat'][roomIndex]['state'] = 0x01
                    packet = bytearray([0xF7, 0x0D, 0x01, 0x18, 0x04, 0x45])
                    packet.append(recvBuffer[6])
                    packet.append(recvBuffer[7])
                    packet.append(0x01)
                    packet.append(self.Devices['Thermostat'][roomIndex]['currTherm'])
                    packet.append(self.Devices['Thermostat'][roomIndex]['targetTherm'])
                    packet.append(self.calcXORChecksum(packet))
                    packet.append(0xEE)
                    self.sendData(packet)
                elif thermCmd == 0x46:
                    #   F7    0B    01    18    02    46    XX    YY    00    ZZ    EE
                    # 0xF7, 0x0B, 0x01, 0x18, 0x02, 0x46, 0x11, 0x01, 0x00, 0xB1, 0xEE
                    # XX: 상위 4비트 = 1, 하위 4비트 = Room Index
                    # YY: 0x01=On, 0x04=Off
                    # ZZ: Checksum (XOR SUM)
                    stateCmd = recvBuffer[7]
                    roomIndex = recvBuffer[6] >> 4
                    onOffCmd = recvBuffer[7]
                    if self.Devices['Thermostat'][roomIndex]['targetTherm'] < self.Devices['Thermostat'][roomIndex]['currTherm']:
                        onOffCmd = 0x04

                    packet = bytearray([0xF7, 0x0D, 0x01, 0x18, 0x04, 0x46, recvBuffer[6], onOffCmd, onOffCmd,
                                self.Devices['Thermostat'][roomIndex]['currTherm'], self.Devices['Thermostat'][roomIndex]['targetTherm']])
                    
                    packet.append(self.calcXORChecksum(packet))
                    packet.append(0xEE)
                    self.sendData(packet)

            elif deviceId == 0x19: # Light
                # F7 0B 01 19 02 40 XX YY 00 ZZ EE
                # XX: 상위 4비트 = Room Index, 하위 4비트 = Device Index (1-based)
                # YY: 02 = OFF, 01 = ON
                # ZZ: Checksum (XOR SUM)
                deviceIndex = (recvBuffer[6] & 0x0F) - 1
                lightState = recvBuffer[7]
                self.Devices['Light'][deviceIndex] = lightState
                packet = ([0xF7, 0x0B, 0x01, 0x19, 0x04, 0x40])
                packet.append(recvBuffer[6])
                packet.append(recvBuffer[7])
                packet.append(recvBuffer[7])
                packet.append(self.calcXORChecksum(packet))
                packet.append(0xEE)
                self.sendData(packet)

            elif deviceId == 0x1B: # GasValve
                self.Devices['GasValve'][0] = recvBuffer[7]
                packet = bytearray([0xF7, 0x0B, 0x01, 0x1B, 0x04, 0x43, 0x11])
                packet.append(recvBuffer[7])
                packet.append(recvBuffer[7])
                packet.append(self.calcXORChecksum(packet))
                packet.append(0xEE)
                self.sendData(packet)
            elif deviceId == 0x1C: # Airconditioner
                pass
            elif deviceId == 0x1E: # Doorlock
                pass
            elif deviceId == 0x2A: # BatchOffSwitch
                pass
            elif deviceId == 0x2B: # Ventilator
                packet = bytearray([0xF7, 0x0C, 0x01, 0x2B, 0x04])
                if recvBuffer[7] == 0x02:
                    packet.extend([0x40, 0x11, 0x02, 0x02, 0x01])
                else:
                    packet.extend([0x42, 0x11, recvBuffer[7], 0x01, recvBuffer[7]])
                packet.append(self.calcXORChecksum(packet))
                packet.append(0xEE)
                self.sendData(packet)
                pass
            elif deviceId == 0x34: # Elivator
                packet = bytearray([0xF7, 0x0B, 0x01, 0x34])
                packet.extend([0x04, 0x41, 0x10, 0x06, 0x00])
                packet.append(self.calcXORChecksum(packet))
                packet.append(0xEE)
                self.sendData(packet)

    def onRecvDisconnected(self):
        self.stopThreadSend()
        self.stopThreadRecv();

    def onManageClient(self, clientSocket:socket.socket, clientAddr: dict):
        print(f'{clientSocket}, {clientAddr}')
        self.startThreadSend(clientSocket)
        self.startThreadRecv(clientSocket, clientAddr)

@staticmethod
def calcXORChecksum(data: Union[bytearray, bytes, List[int]]) -> int:
    return reduce(lambda x, y: x ^ y, data, 0)

if __name__ == '__main__':
    simpleClient = SimpleClient()

    print(f'Simple Server Start {SERVER}:{PORT}')
    def convert(byte_str: str):
        return bytearray([int(x, 16) for x in byte_str.split(' ')])

    def loop():
        sysin = sys.stdin.readline()
        try:
            cmd = int(sysin.split('\n')[0])
        except Exception:
            loop()
            return

        if cmd == 0:
            simpleClient.disconnect()
            pass
        elif cmd == 1: 
            packet = bytearray([0xF7, 0x0B, 0x01, 0x34])
            packet.extend([0x02, 0x41, 0x10, 0x06, 0x00])
            packet.append(calcXORChecksum(packet))
            packet.append(0xEE)
            simpleClient.sendData(packet)
            loop()
        elif cmd == 2:
            simpleClient.sendData(bytearray([0xF7, 0x0B, 0x01, 0x19, 0x02, 0x40, 0x10, 0x01, 0x00, 0xB7, 0xEE]))
            loop()
        else:
            loop()
    loop()

