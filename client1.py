import queue
import socket
import threading
from typing import Union
from _thread import *

HOST = '192.168.0.100'
PORT = 9999

class SimpleClient:
    # clientSocket은 socket 또는 None만을 가질 수 있도록 Union을 사용한다.
    # 이런 방법을 사용하면 원하지 않는 다른 type을 가질 수 없기 때문에 좋을 방법이라고 생각한다.(인터넷 참조)
    clientSocket: Union[socket.socket, None] = None
    recvQueue = queue.Queue()

    def __init__(self):
        self.clientSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.clientSocket.connect((HOST, PORT))
        # thread를 만들어서 socket을 통해 들어오는 data를 처리
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
