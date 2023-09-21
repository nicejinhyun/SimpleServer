import queue
import socket
import sys
import time
import threading

from typing import Union

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
        self.sock = sock
        self.queueRecv = queueRecv
        self.addr = addr

    def run(self):
        while self.keepAlive:
            try:
                data = self.sock.recv(1024)
                if data is not None:
                    self.sig_recv_data.emit(data)
            except ConnectionResetError as e:
                print(f'>>> Disconnect by {self.addr[0]} : {self.addr[1]}')
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

    def __init__(self):
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
        self.startThreadSend()
        self.startThreadManagerClient()

    def disconnect(self):
        self.sock.close()

    def startThreadSend(self):
        if self.threadSend is None:
            self.threadSend = ThreadSend(self.sock, self.queueSend)
            self.threadSend.sig_send_data.connect(self.onSendData)
            self.threadSend.daemon = True
            self.threadSend.start()
        
    def startThreadRecv(self, sock: socket.socket, addr: dict):
        if self.threadRecv is None:
            self.threadRecv = ThreadRecv(sock, addr, self.queueRecv)
            self.threadRecv.sig_recv_data.connect(self.onRecvData)
            self.threadRecv.daemon = True
            self.threadRecv.start()

    def startThreadManagerClient(self):
        if self.threadManagerClient is None:
            self.threadManagerClient = ThreadManagerClient(self.sock)
            self.threadManagerClient.sig_client_connect.connect(self.onManageClient)
            self.threadManagerClient.daemon = True
            self.threadManagerClient.start()

    def stopThread(self):
        if self.threadSend is not None:
            self.threadSend.stop()
        if self.threadRecv is not None:
            self.threadRecv.stop()

    def sendData(self, data: Union[bytes, bytearray]):
        self.queueSend.put(bytes(data))

    def onSendData(self, data: bytes):
        self.sig_send_data.emit(data)
        
    def onRecvData(self, data: bytes):
        print(f'{data}')

    def onManageClient(self, clientSocket:socket.socket, clientAddr: dict):
        print(f'{clientSocket}, {clientAddr}')
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
            simpleClient.sendData(bytearray([0xF7, 0x0B, 0x01, 0x19, 0x02, 0x40, 0x10, 0x01, 0x00, 0xB7, 0xEE]))
            loop()
        elif cmd == 2:
            simpleClient.sendData(bytearray([0xF7, 0x0B, 0x01, 0x19, 0x02, 0x40, 0x10, 0x01, 0x00, 0xB7, 0xEE]))
            loop()
        else:
            loop()
    loop()
