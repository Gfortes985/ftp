import socket
import json
import sys
import base64
import os


class FTPClient:

    def __init__(self, ip: str, port: int):
        self.port = port
        self.ip = ip
        self.__socket__ = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.__socket__.connect((ip, port))
        self.pwd_path = ''
        self.is_login = False


    def get_command(self, filename, data):
        if data != "0":
            with open(filename, "wb") as f:
                print(data)
                f.write(base64.b64decode(data))
            print(f"Скачан файл {filename}")
        else:
            print(f"{filename} является папкой")

    def put_command(self,file):
        if os.path.isfile(file):
            with open(file,'rb') as f:
                return base64.b64encode(f.read()).decode()
        else:
            return b'0'.decode()

    def sendData(self):
        self.__socket__.send(json.dumps(['pwd']).encode())
        self.pwd_path = self.receiveData()
        while True:
            if self.is_login:
                i = input("ftp@shell$"+self.pwd_path+">").split()
                args = " ".join(i[1:])
                match i[0]:
                    case 'exit':
                        raise KeyboardInterrupt
                    case 'get':
                        self.__socket__.send(json.dumps(i).encode())
                        self.get_command(args, self.receiveData())
                    case 'put':
                        self.__socket__.send(json.dumps(i).encode())
                        self.__socket__.send(json.dumps(self.put_command(args)).encode())
                        print(self.receiveData())
                    case 'cd':
                        self.__socket__.send(json.dumps(i).encode())
                        printdata = self.receiveData()
                        if len(printdata) == 0:
                            pass
                        else:
                            print(printdata)
                        self.__socket__.send(json.dumps(['pwd']).encode())
                        self.pwd_path = self.receiveData()
                    case _:
                        self.__socket__.send(json.dumps(i).encode())
                        printdata = self.receiveData()
                        if len(printdata) == 0:
                            pass
                        else:
                            print(printdata)
            else:
                i=input("ftp@shell$>").split()
                args=" ".join(i[1:])
                match i[0]:
                    case "login":
                        if len(i) < 3:
                            print("Вы не ввели пароль или имя пользователя")
                            continue
                        else:
                            self.__socket__.send(json.dumps(i).encode())
                            data = self.receiveData()
                        if data == '200':
                            self.is_login = True
                            print("ВЫ успешно вошли")
                        elif data == '300':
                            print("Пользователь с таким именем не найден")
                        else:
                            print("Введеный пароль не верен")




    def receiveData(self):
        json_data = b""

        while True:
            try:
                jdata = json_data
                return json.loads(jdata)
            except ValueError:
                json_data = json_data + self.__socket__.recv(1024**2)
                continue

    def exit(self):
        self.__socket__.send(json.dumps(['cliexit']).encode())
        self.__socket__.close()
        print("\n[-] FTP client closed")
        sys.exit(0)
        pass




try:
    cli = FTPClient('localhost', 25565)
    cli.sendData()
except KeyboardInterrupt:
    sys.exit(0)
finally:
    cli.exit()





# cli = FTPClient('localhost',25565)
# cli.sendData()