import queue
import socket
import sys
import threading

SERVER = '127.0.0.1'
#SERVER = '192.168.0.100'
PORT = 9999

deviceList = [0x18, 0x19, 0x1B, 0x1C, 0x1E, 0x1F, 0x2A, 0x2B, 0x34, 0x43, 0x44]

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

class PacketCollector:
    threadRecv = None

    def __init__(self):
        self.recvBuffer = bytearray()
        self.sig_recv_data = Callback(bytes)
        self.queueRecv = queue.Queue()
        self.connect()

    def connect(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.connect((SERVER, PORT))
        self.startThreadRecv(self.sock, (SERVER, PORT))
        
    def startThreadRecv(self, sock: socket.socket, addr: dict):
        if self.threadRecv is None:
            self.threadRecv = ThreadRecv(sock, addr, self.queueRecv)
            self.threadRecv.sig_recv_data.connect(self.onRecvData)
            self.threadRecv.sig_terminated.connect(self.onRecvDisconnected)
            self.threadRecv.daemon = True
            self.threadRecv.start()

    def onRecvData(self, data: bytes):
        recvBuffer = bytearray()
        recvBuffer.extend(data)

        if recvBuffer[0] == 0xF7 and recvBuffer[-1] == 0xEE:
            print(f'recv: {recvBuffer}')

    def onRecvDisconnected(self):
        self.stopThreadRecv();

    def stopThreadRecv(self):
        if self.threadRecv is not None:
            self.threadRecv.stop()
            self.threadRecv = None

    def disconnect(self):
        self.sock.close()

if __name__ == '__main__':
    packetCollector = PacketCollector()

    print(f'Simple Server Start {SERVER}:{PORT}')

    def loop():
        sysin = sys.stdin.readline()
        try:
            cmd = int(sysin.split('\n')[0])
        except Exception:
            loop()
            return

        if cmd == 0:
            packetCollector.disconnect()
            pass
        else:
            loop()
    loop()