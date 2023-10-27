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
        "Light": [0x02, 0x02, 0x02, 0x02],
        "Thermostat": [
            {'state': 0x02, 'currTherm': 0x11, 'setTherm': 0x11},
            {'state': 0x02, 'currTherm': 0x11, 'setTherm': 0x11},
            {'state': 0x02, 'currTherm': 0x11, 'setTherm': 0x11},
            {'state': 0x02, 'currTherm': 0x11, 'setTherm': 0x11}
        ],
        "Airconditioner": [
            {'state': 0x02, 'currTherm': 0x11, 'setTherm': 0x11},
            {'state': 0x02, 'currTherm': 0x11, 'setTherm': 0x11},
            {'state': 0x02, 'currTherm': 0x11, 'setTherm': 0x11},
            {'state': 0x02, 'currTherm': 0x11, 'setTherm': 0x11}
        ],
        "Ventilator": [0x02]
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

        if len(recvBuffer) >= 10 and recvBuffer[0] == 0xF7 and recvBuffer[-1] == 0xEE:
            # Light
            # Command
            #              [0]   [1]   [2]   [3]   [4]   [5]  [6]   [7]   [8]   [9]   [10]
            # 켜짐 명령-> 0xF7, 0x0B, 0x01, 0x19, 0x02, 0x40, 0x10, 0x01, 0x00, 0x86, 0xEE
            # Ack
            # 켜짐 상태-> 0xF7, 0x0B, 0x01, 0x19, 0x04, 0x40, 0x10, 0x00, 0x01, 0x80, 0xEE
            # Command
            # 꺼짐 명령-> 0xF7, 0x0B, 0x01, 0x19, 0x02, 0x40, 0x10, 0x02, 0x00, 0x85, 0xEE
            # Ack
            # 꺼짐 상태-> 0xF7, 0x0B, 0x01, 0x19, 0x04, 0x40, 0x10, 0x00, 0x02, 0x83, 0xEE
            # [0] [1] [2] [3] [4] [5] [6] [7] [8] [9] [10]
            # F7  0B  01  19  02  40  XX  YY  00  ZZ  EE
            # XX: 상위 4비트 = Room Index, 하위 4비트 = Device Index (1-based)
            # YY: 01 = ON, 02 = OFF
            # ZZ: Checksum (XOR SUM)
            # ACK인 경우:
            # [7], [8]이 동일한 상태를 가지면 된다.
            if recvBuffer[3] == 0x19:
                if recvBuffer[4] == 0x01 or recvBuffer[4] == 0x02:
                    packet = bytearray([0xF7, 0x0B, 0x01, 0x19, 0x04, 0x40])
                    deviceIndex = recvBuffer[6] & 0x0F
                    self.Devices['Light'][deviceIndex] = recvBuffer[7] & 0x0F
                    packet.append(recvBuffer[6])
                    packet.append(recvBuffer[7])
                    packet.append(recvBuffer[7])
                    packet.append(self.calcXORChecksum(packet[:-2]))
                    packet.append(0xEE)
                    packet.extend([0xF7, 0x0B, 0x01, 0x19, 0x04, 0x40])
                    packet.append(recvBuffer[6])
                    packet.append(recvBuffer[7])
                    packet.append(recvBuffer[7])
                    packet.append(self.calcXORChecksum(packet[:-2]))
                    packet.append(0xEE)                    
                    self.sendData(packet)

            # Thermostat
            # 상태 요청: 0xF7, 0x0B, 0x01, 0x18, 0x01, 0x45, 0x11, 0x00, 0x00, 0xB0, 0xEE
            # 켜짐 상태: 0xF7, 0x0D, 0x01, 0x18, 0x04, 0x45, 0x11, 0x00, (0x01, 0x1B, 0x17), 0xBE, 0xEE (상태, 현재온도, 설정온도)
            # 꺼짐 상태: 0xF7, 0x0D, 0x01, 0x18, 0x04, 0x45, 0x11, 0x00, (0x04, 0x1B, 0x17), 0xBB, 0xEE (상태, 현재온도, 설정온도)
            # 외출 상태: 0xF7, 0x0D, 0x01, 0x18, 0x04, 0x45, 0x11, 0x00, (0x07, 0x1B, 0x17), 0xB9, 0xEE

            # 켜짐 명령: 0xF7, 0x0B, 0x01, 0x18, 0x02, 0x46, 0x11, 0x01, 0x00, 0xB1, 0xEE
            #      ACK: 0xF7, 0x0D, 0x01, 0x18, 0x04, 0x46, 0x11, 0x01, 0x01, 0x1B, 0x17, 0xBC, 0xEE
            # 꺼짐 명령: 0xF7, 0x0B, 0x01, 0x18, 0x02, 0x46, 0x11, 0x04, 0x00, 0xB4, 0xEE
            #      ACK: 0xF7, 0x0D, 0x01, 0x18, 0x04, 0x46, 0x11, 0x04, 0x04, 0x1B, 0x17, 0xBC, 0xEE
            # 온도 조절: 0xF7, 0x0B, 0x01, 0x18, 0x02, 0x45, 0x11, (0x18), 0x00, 0xA7, 0xEE (온도 24도 설정)
            #      ACK: 0xF7, 0x0D, 0x01, 0x18, 0x04, 0x45, 0x11, (0x18), 0x01, (0x1A, 0x18), 0xA8, 0xEE

            # [0] [1] [2] [3] [4] [5] [6] [7] [8] [9] [10]
            #  F7  0B  01  18  02  46  XX  YY  00  ZZ  EE
            # XX: 상위 4비트 = 1, 하위 4비트 = Room Index
            # YY: 0x01=On, 0x04=Off
            # ZZ: Checksum (XOR SUM)
            # [0] [1] [2] [3] [4] [5] [6] [7] [8] [9] [10]
            #  F7  0B  01  18  02  45  XX  YY  00  ZZ  EE
            # XX: 상위 4비트 = 1, 하위 4비트 = Room Index
            # YY: 온도 설정값
            # ZZ: Checksum (XOR SUM)
            if recvBuffer[3] == 0x18:
                packet = bytearray([0xF7, 0x0D, 0x01, 0x18, 0x04])
                roomIndex = recvBuffer[6] & 0x0F
                if recvBuffer[4] == 0x01:
                    packet.append(0x45)
                    packet.append(recvBuffer[6])
                    packet.append(0x00)
                    packet(self.Devices['Thermostat'][roomIndex-1]['state'])
                    packet(self.Devices['Thermostat'][roomIndex-1]['currTherm'])
                    packet(self.Devices['Thermostat'][roomIndex-1]['setTherm'])
                if recvBuffer[4] == 0x02:
                    if recvBuffer[5] == 0x46:
                        self.Devices['Thermostat'][roomIndex-1]['state'] = recvBuffer[7]
                    else:
                        self.Devices['Thermostat'][roomIndex-1]['setTherm'] = recvBuffer[7]

                    packet.append(recvBuffer[5])
                    packet.append(recvBuffer[6])
                    if recvBuffer[5] == 0x46:
                        packet.append(self.Devices['Thermostat'][roomIndex-1]['state'])
                        packet.append(self.Devices['Thermostat'][roomIndex-1]['state'])
                    else:
                        packet.append(self.Devices['Thermostat'][roomIndex-1]['setTherm'])
                        packet.append(self.Devices['Thermostat'][roomIndex-1]['state'])

                    packet.append(self.Devices['Thermostat'][roomIndex-1]['currTherm'])
                    packet.append(self.Devices['Thermostat'][roomIndex-1]['setTherm'])

                packet.append(self.calcXORChecksum(packet))
                packet.append(0xEE)

            # Ventilator
            # [환기]
            # [0] [1] [2] [3] [4] [5] [6] [7] [8] [9] [10] [11]
            #  F7  0C  01  2B  04  4X  11  XX  YY  XX   ZZ   EE
            # XX: 풍량 (0x01=약, 0x03=중, 0x07=강, 0x02=off)
            # ZZ: Checksum (XOR SUM)
            #                 [0]   [1]   [2]   [3]   [4]   [5]   [6]   [7]   [8]   [9]  [10]  [11]
            # 켜짐(강) 상태-> 0xF7, 0x0C, 0x01, 0x2B, 0x04, 0x42, 0x11, 0x07, 0x01, 0x07, 0x87, 0xEE
            # 켜짐(중) 상태-> 0xF7, 0x0C, 0x01, 0x2B, 0x04, 0x42, 0x11, 0x03, 0x01, 0x03, 0x87, 0xEE
            # 켜짐(약) 상태-> 0xF7, 0x0C, 0x01, 0x2B, 0x04, 0x42, 0x11, 0x01, 0x01, 0x01, 0x87, 0xEE
            # 꺼짐     상태-> 0xF7, 0x0C, 0x01, 0x2B, 0x04, 0x40, 0x11, 0x02, 0x02, 0x01, 0x85, 0xEE
            # [0] [1] [2] [3] [4] [5] [6] [7] [8] [9] [10]
            #  F7  0B  01  2B  02  40  11  XX  00  YY  EE
            # XX: 0x01=On, 0x02=Off
            # YY: Checksum (XOR SUM)
            #                 [0]   [1]   [2]   [3]   [4]   [5]   [6]   [7]   [8]   [9]  [10]
            # 켜짐(강) 명령-> 0xF7, 0x0B, 0x01, 0x2B, 0x02, 0x42, 0x11, 0x07, 0x00, 0x80, 0xEE
            # 켜짐(중) 명령-> 0xF7, 0x0B, 0x01, 0x2B, 0x02, 0x42, 0x11, 0x03, 0x00, 0x84, 0xEE
            # 켜짐(약) 명령-> 0xF7, 0x0B, 0x01, 0x2B, 0x02, 0x42, 0x11, 0x01, 0x00, 0x86, 0xEE
            # 꺼짐     명령-> 0xF7, 0x0B, 0x01, 0x2B, 0x02, 0x40, 0x11, 0x02, 0x00, 0x87, 0xEE
            # [0] [1] [2] [3] [4] [5] [6] [7] [8] [9] [10]
            #  F7  0B  01  2B  02  42  11  XX  00  YY  EE
            # XX: 풍량 (0x01=약, 0x03=중, 0x07=강)
            # YY: Checksum (XOR SUM)

            if recvBuffer[3] == 0x2B:
                if recvBuffer[4] == 0x01 or recvBuffer[4] == 0x02:
                    packet = bytearray([0xF7, 0x0C, 0x01, 0x2B, 0x04])
                    self.Devices['Ventilator'][0] = recvBuffer[7]
                    if self.Devices['Ventilator'][0] != 0x02:
                        packet.append(0x42)
                    else:
                        packet.append(0x40)
                    packet.append(0x11)
                    packet.append(self.Devices['Ventilator'][0])
                    if self.Devices['Ventilator'][0] != 0x02:
                        packet.append(0x01)
                    else:
                        packet.append(0x02)
                    packet.append(self.Devices['Ventilator'][0])
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
            simpleClient.sendData(bytearray([0xF7, 0x0B, 0x01, 0x19, 0x04, 0x40, 0x12, 0x01, 0x01, 0xB2, 0xEE]))
            loop()
        elif cmd == 2:
            simpleClient.sendData(bytearray([0xF7, 0x0B, 0x01, 0x19, 0x02, 0x40, 0x10, 0x01, 0x00, 0xB7, 0xEE]))
            loop()
        else:
            loop()
    loop()

