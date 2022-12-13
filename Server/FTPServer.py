import socket
import _thread
import json
import shutil
import os
from time import ctime
from tabulate import tabulate
import base64
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, filename="latest.log",filemode="w",
                    format="%(asctime)s %(levelname)s %(message)s")
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
        self.threads={}
        self.needCheck = True

    def listen(self) -> None:
        now = datetime.now().time()
        now = str(now).split('.')[0]
        logging.info(f"Server started at {self.localHostIp}")
        print(f"{now} [INFO] Server started at {self.localHostIp}")
        while True:
            client, ip = self.__socket__.accept()
            now = datetime.now().time()
            now = str(now).split('.')[0]
            logging.info(f"{ip[0]}:{ip[1]} connected ")
            print(f"{now} [INFO] {ip[0]}:{ip[1]} connected ")
            self.clients[client] = []
            client.settimeout(60.0*60)
            self.threads[ip] = _thread.start_new_thread(self.receiveCommand, (client, ip))

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

    def ls_command(self,client,path=None) -> str:
        try:
            if path == None:
                path = self.clients[client][3]
                parent=path
                dirs = os.listdir(path)
            else:
                path = self.clients[client][3]+path+'\\'
                parent = path
                dirs = os.listdir(path)

            file_data = []
            output_headers = ['NAME', 'TIME MODIFIED', 'BYTE SIZE']
            for file in dirs:
                showfile = file
                if os.path.isdir(path+file):
                    showfile = "[DIR] "+ file
                if len(showfile) > 70:
                    file_data.append([showfile[:70] + "...", ctime(os.path.getmtime(parent+file)), os.path.getsize(parent+file)])
                else:
                    file_data.append([showfile, ctime(os.path.getmtime(parent+file)), os.path.getsize(parent+file)])
            return tabulate(file_data, headers=output_headers)
        except PermissionError:
            return "Недостачно прав"
        except FileNotFoundError:
            return "Путь не найден"
        except OSError:
            return "Путь не найден"

    def cd_command(self, dir,client) -> str:
            path = self.clients[client]
            splitdir = dir.split('/')
            if splitdir[0] == '' and splitdir[1] != '':
                if os.path.exists(os.path.abspath(os.path.pardir + '\\fileenv')+'\\'+path[2] +'\\'.join(splitdir)):
                    path[3] = os.path.abspath(os.path.pardir + '\\fileenv')+'\\'+path[2] +'\\'.join(splitdir)
                    path[4] = '/'.join(splitdir) + '/'
                else:
                    return "Данной папки не существует"
            elif splitdir[0] == '' and splitdir[1] == '':#/
                path[3] = os.path.abspath(os.path.pardir + '\\fileenv')+'\\'+path[2]+"\\"
                path[4] = '/'
            elif splitdir[0] != '':#path
                if dir == "..":#path up
                    path[3] = "\\".join(path[3].split('\\')[:-2])
                    path[3] += "\\"
                    path[4] = "/".join(path[4].split('/')[:-2])
                    if path[4] == '':
                        path[4]='/'
                        path[3]=os.path.abspath(os.path.pardir + '\\fileenv')+'\\'+path[2]+"\\"
                    print(path[3])
                elif os.path.exists(path[3]+'\\'.join(splitdir)):
                    path[3] += '\\'.join(splitdir)+'\\'
                    path[4] += '/'.join(splitdir)+'/'
                else:
                    return "Данной папки не существует"
            return f""

    def get_command(self, file,client):
        file = self.clients[client][3] + file
        if os.path.isfile(file):
            with open(file, "rb") as f:
                return base64.b64encode(f.read()).decode()
        elif os.path.isdir(file):
            return '0'
        else:
            return '1'

    def put_command(self,filename,data,client):
        name = filename
        filename = self.clients[client][3]+filename
        if data != "0":
            with open(filename,"wb") as f:
                f.write(base64.b64decode(data))
                return f"{name} загружен"
        else:
            return f'{name} является папкой'

    def cat_command(self,filename,client):
        name = filename
        filename = self.clients[client][3]+name
        if os.path.isfile(filename):
            try:
                with open(filename,"r") as f:
                    return f.read()
            except UnicodeDecodeError:
                return f"{name} не является текстовым файлом"
        elif not os.path.exists(filename):
            return f'{name} не найден'
        else:
            return f'{name} является папкой'

    def mkdir_command(self,path,client):
        name = path
        path = self.clients[client][3]+path
        if not os.path.isdir(path):
            os.mkdir(path)
            return f"Папка {name} создана"
        else:
            return "Папка с данным названием уже существует"

    def rmdir_command(self,path,client):
        name = path
        path = self.clients[client][3]+path
        try:
            if os.path.exists(path):
                os.rmdir(path)
                return f"Папка {name} успешно удалена"
            else:
                return "Папка с данным названием не найдена"
        except OSError:
            return 'Папка не пуста'

    def rename_command(self,oldname,newname,client):
        oname = oldname
        nname = newname
        oldname = self.clients[client][3]+oldname
        newname = self.clients[client][3]+newname
        try:
            os.rename(oldname,newname)
            return f"Файл переименован {oname} -> {nname}"
        except FileExistsError:
            return f"Файл с таким названием уже существует"

    def rm_command(self,file,client):
        name = file
        file = self.clients[client][3]+file
        if os.path.isdir(file):
            return f'{name} являеться папкой, для удаления используйте rmdir'
        try:
            os.remove(file)
            return f"Файл {name} удалён"
        except FileNotFoundError:
            return f"Файл {name} не найден"

    def pwd_command(self,client):
        try:
            return f"{self.clients[client][4]}"
        except IndexError:
            return '/'

    def login_command(self,login,password,ip,client):

            with open('C:\\Users\\Gfortes\\Desktop\\Encryption\\Server\\credentials.json', 'r') as f:
                json_doc = json.loads(f.read())
                try:
                    if json_doc[f'{login}']['password'] == password:
                        now = datetime.now().time()
                        now = str(now).split('.')[0]
                        logging.info(f'{ip[0]}:{ip[1]} logined as {login}')
                        print(f'{now} [INFO] {ip[0]}:{ip[1]} logined as {login}')
                        clientdict = json_doc[f'{login}']
                        self.clients[client] = [clientdict['password'],clientdict['permission'],clientdict['homefolder']]
                        self.clients[client].append(os.path.abspath(os.path.pardir + '\\fileenv') + '\\' + self.clients[client][2] + '\\')
                        self.clients[client].append('/')
                        return '200'
                    else:
                        return '400'
                except:
                    return '300'

    def register_command(self,login,password,client):
            json_doc={}
            with open('credentials.json', 'r') as f:
                json_doc = json.loads(f.read())
            with open('credentials.json', 'w') as f:
                    if login in json_doc.keys():
                        return '300'
                    else:
                        json_doc[f'{login}'] = {}
                        json_doc[f'{login}']['password'] = password
                        json_doc[f'{login}']['permission'] = 'user'
                        json_doc[f'{login}']['homefolder'] = login
                        f.write(json.dumps(json_doc, sort_keys=True, ensure_ascii=False, indent=4))
                        self.mkdir_command(os.path.abspath(os.path.pardir)+"\\fileenv\\"+login,client)
                        return "200"






    def receiveCommand(self, client, ip) -> None:
        try:
            while True:
                command = self.receiveData(client)
                args = " ".join(command[1:])
                match command[0]:
                    case 'ls':
                        if len(command) >= 2:
                            client.send(json.dumps(self.ls_command(client,path=args)).encode())
                        else:
                            client.send(json.dumps(self.ls_command(client)).encode())
                    case 'cd':
                        client.send(json.dumps(self.cd_command(args,client=client)).encode())
                    case 'get':
                        client.send(json.dumps(self.get_command(args,client)).encode())
                    case 'put':
                        client.send(json.dumps(self.put_command(args, self.receiveData(client),client)).encode())
                    case 'cat':
                        client.send(json.dumps(self.cat_command(args,client)).encode())
                    case 'mkdir':
                        client.send(json.dumps(self.mkdir_command(args,client)).encode())
                    case 'rmdir':
                        client.send(json.dumps(self.rmdir_command(args,client)).encode())
                    case "rename":
                        client.send(json.dumps(self.rename_command(args.split()[0],args.split()[1],client)).encode())
                    case 'rm':
                        client.send(json.dumps(self.rm_command(args,client)).encode())
                    case 'cliexit':
                        raise ConnectionResetError
                    case "pwd":
                        client.send(json.dumps(self.pwd_command(client)).encode())
                    case "login":
                        client.send(json.dumps(self.login_command(command[1],command[2],ip,client)).encode())
                    case 'whoami':
                        client.send(json.dumps(self.clients[client][1]).encode())
                    case 'register':
                        client.send(json.dumps(self.register_command(command[1],command[2],ip,client)).encode())
                    case _:
                        client.send(json.dumps("Команда не найдена").encode())

        except ConnectionResetError:
            now = datetime.now().time()
            now = str(now).split('.')[0]
            logging.info(f"{ip[0]}:{ip[1]} disconnected")
            print(f"{now} [INFO] {ip[0]}:{ip[1]} disconnected")
            self.clients.pop(client)
        except ConnectionAbortedError:
            now = datetime.now().time()
            now = str(now).split('.')[0]
            logging.info(f"{ip[0]}:{ip[1]} disconnected")
            print(f"{now} [INFO] {ip[0]}:{ip[1]} disconnected")
            self.clients.pop(client)
        except TimeoutError:
            now = datetime.now().time()
            now = str(now).split('.')[0]
            logging.info(f"{ip[0]}:{ip[1]} connection time out")
            print(f"{now} [INFO] {ip[0]}:{ip[1]} connection time out")
            self.clients.pop(client)



FTPServer().listen()




