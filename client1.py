import queue
import socket
import threading
from typing import Union
from _thread import *

HOST = '192.168.0.100'
PORT = 9999

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
            print('receive : ', repr(data))

if __name__ == '__main__':
    simpleClient = SimpleClient()
    keepAlive = True

    while True:
        msgSendData = input()
        if msgSendData == 'quit':
            break
        simpleClient.sendData(msgSendData.encode())
