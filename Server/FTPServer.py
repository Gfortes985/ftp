import socket
from _thread import start_new_thread
import sys
import json
import shutil
import os
from time import ctime
from tabulate import tabulate
import base64



class FTPServer():
    def __init__(self, ip: str = 'localhost', port: int = 25565):
        self.port = port
        self.ip = ip
        self.__socket__ = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.__socket__.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.__socket__.bind((ip, port))
        self.localHostIp = socket.gethostbyname(socket.gethostname())
        self.__socket__.listen()
        self.clients = {}
        self.needCheck = True

    def listen(self) -> None:

        print(f"[INFO] Server started at {self.localHostIp}")
        while True:
            client, ip = self.__socket__.accept()
            print(f"[INFO] {ip[0]}:{ip[1]} connected ")
            self.clients[client] = []
            client.settimeout(60.0*60)
            start_new_thread(self.receiveCommand, (client, ip))



    def receiveData(self, client) -> None:
        json_data = b""
        while True:
            try:
                json_data = json_data + client.recv(1024)
                return json.loads(json_data)
            except ValueError:
                continue

    def closeSockets(self) -> None:
        self.__socket__.close()

    def ls_command(self,path=None) -> str:
        try:
            if path == None:
                dirs = os.listdir()
                parentdir = os.path.curdir+'\\'
            else:
                parentdir = os.path.abspath(path)+'\\'
                dirs = os.listdir(path)

            file_data = []
            output_headers = ['NAME', 'TIME MODIFIED', 'BYTE SIZE']
            for file in dirs:
                showfile = file
                if os.path.isdir(parentdir+file):
                    showfile = "[DIR] "+ file
                if len(showfile) > 70:
                    file_data.append([showfile[:70] + "...", ctime(os.path.getmtime(parentdir+file)), os.path.getsize(parentdir+file)])
                else:
                    file_data.append([showfile, ctime(os.path.getmtime(parentdir+file)), os.path.getsize(parentdir+file)])
            return tabulate(file_data, headers=output_headers)
        except PermissionError:
            return "Недостачно прав"
        except FileNotFoundError:
            return "Путь не найден"

    def cd_command(self, dir) -> str:
        try:
            os.chdir(dir)
            return f""
        except FileNotFoundError:
            return "Папка с данным названием не найдена"
        except OSError:
            return "Папка с данным названием не найдена"

    def get_command(self, file):
        if os.path.isfile(file):
            with open(file, "rb") as f:
                return base64.b64encode(f.read()).decode()
        else:
            return b'0'.decode()

    def put_command(self,filename,data):
        if data != "0":
            with open(filename,"wb") as f:
                f.write(base64.b64decode(data))
                return f"{filename} загружен"
        else:
            return f'{filename} является папкой'

    def cat_command(self,filename):
        if os.path.isfile(filename):
            try:
                with open(filename,"r") as f:
                    return f.read()
            except UnicodeDecodeError:
                return f"{filename} не является текстовым файлом"
        else:
            return f'{filename} является папкой'

    def mkdir_command(self,path):
        if not os.path.isdir(path):
            os.mkdir(path)
            return f"Папка {path} создана"
        else:
            return "Папка с данным названием уже существует"
    def rmdir_command(self,path):
        if os.path.exists(path):
            os.rmdir(path)
            return f"Папка {path} успешно удалена"
        else:
            return "Папка с данным названием не найдена"

    def rename_command(self,oldname,newname):
        try:
            os.rename(oldname,newname)
            return f"Файл переименован {oldname} -> {newname}"
        except FileExistsError:
            return f"Файл с таким названием уже существует"

    def rm_command(self,file):
        if os.path.isdir(file):
            return f'{file} являеться папкой, для удаления используйте rmdir'
        try:
            os.remove(file)
            return f"Файл {file} удалён"
        except FileNotFoundError:
            return f"Файл {file} не найден"

    def pwd_command(self):
        return os.getcwd()

    def login_command(self,login,password,ip,client):
        try:
            with open('credentials.json', 'r') as f:
                json_doc = json.loads(f.read())
                try:
                    if json_doc[f'{login}']['password'] == password:
                        print(f'[INFO] {ip[0]}:{ip[1]} logined as {login}')
                        self.clients[client] = [json_doc[f"{login}"]['password'],json_doc[f"{login}"]['permission']]
                        return '200'
                    else:
                        return '400'
                except:
                    return '300'
        except:
            self.login_command(login,password,ip,client)


    def receiveCommand(self, client, ip) -> None:
        try:
            while True:
                command = self.receiveData(client)
                args = " ".join(command[1:])
                match command[0]:
                    case 'ls':
                        if len(command) >= 2:
                            client.send(json.dumps(self.ls_command(args)).encode())
                        else:
                            client.send(json.dumps(self.ls_command()).encode())
                    case 'cd':
                        client.send(json.dumps(self.cd_command(args)).encode())
                    case 'get':
                        client.send(json.dumps(self.get_command(args)).encode())
                    case 'put':
                        client.send(json.dumps(self.put_command(args, self.receiveData(client))).encode())
                    case 'cat':
                        client.send(json.dumps(self.cat_command(args)).encode())
                    case 'mkdir':
                        client.send(json.dumps(self.mkdir_command(args)).encode())
                    case 'rmdir':
                        client.send(json.dumps(self.rmdir_command(args)).encode())
                    case "rename":
                        client.send(json.dumps(self.rename_command(args.split()[0],args.split()[1])).encode())
                    case 'rm':
                        client.send(json.dumps(self.rm_command(args)).encode())
                    case 'cliexit':
                        raise ConnectionResetError
                    case "pwd":
                        client.send(json.dumps(self.pwd_command()).encode())
                    case "login":
                        client.send(json.dumps(self.login_command(command[1],command[2],ip,client)).encode())
                    case 'whoami':
                        client.send(json.dumps(self.clients[client][1]).encode())
                    case _:
                        client.send(json.dumps("Команда не найдена").encode())


        except ConnectionResetError:
            print(f"[INFO] {ip[0]}:{ip[1]} disconnected")
            self.clients.pop(client)
        except ConnectionAbortedError:
            pass
        except TimeoutError:
            print(f"[INFO] {ip[0]}:{ip[1]} connection time out")
            self.clients.pop(client)


try:
    FTPServer().listen()
except KeyboardInterrupt:
    sys.exit(0)
finally:
    print("[-] Server stoped")



