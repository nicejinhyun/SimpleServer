import queue
import socket
import sys
import time
import threading

from functools import reduce
from typing import Union, List

SERVER = '127.0.0.1'
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
        self.recvBuffer.extend(data)

        if self.recvBuffer[0] == 0xF7 and self.recvBuffer[-1] == 0xEE:
            if self.recvBuffer[4] == 0x02:
                self.recvBuffer[4] = 0x04
                self.recvBuffer[8] = self.recvBuffer[7]
                self.recvBuffer[9] = self.calcXORChecksum(self.recvBuffer[:-2])
                self.sendData(self.recvBuffer)
                self.recvBuffer.clear()

    def onRecvDisconnected(self):
        self.stopThreadSend()
        self.stopThreadRecv();

    def onManageClient(self, clientSocket:socket.socket, clientAddr: dict):
        print(f'{clientSocket}, {clientAddr}')
        self.startThreadSend(clientSocket)
        self.startThreadRecv(clientSocket, clientAddr)

if __name__ == '__main__':
    simpleClient = SimpleClient()

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

