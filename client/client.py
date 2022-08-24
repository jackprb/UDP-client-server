import socket
import sys
import os
import time
import hashlib
import datetime

#######################################################
#   costanti con i valori di default                  #
#######################################################
# porta e IP del server DI DEFAULT, se non specificato da riga di comando
port = 6000
address = 'localhost'

# cartella dove andranno i file ricevuti
dir_path = os.getcwd() + os.path.sep + "files" + os.path.sep

PACKET_SIZE = 32768
TIMEOUT_ERRMSG = "Timeout or some other error"

#######################################################
#   definizione di funzioni utilizzate lato client    #
#######################################################

###########################################################################
# restituisce tempo trascorso per upload/download di un file
def getElapsedTime(timeStart, timeEnd):
    tme = timeEnd - timeStart
    return "Elapsed time: " + str(tme.seconds) + " second(s)"


###########################################################################
# stampa messsaggio per mostrare IP e porta su cui si trova il client
def print_serverIP():
    print("\nServer is running at: \t" + address + ":" + str(port))


###########################################################################
# stampa messaggio nel caso in cui non si specificano IP e porta del server
def print_args():
    print("Server address and port NOT specified \n\n" \
          "Run this file as follows: \n" \
          "\tpython client.py <server address> <server port>")


###########################################################################
# controlla se ci sono tutti gli argomenti necessari passati da riga di comando
def ok_args(): 
    if len(sys.argv) == 3:
    	return True
    return False


###########################################################################
# cancella tutto il contenuto testuale del terminale
def clearScreen():
    os.system('cls' if os.name=='nt' else 'clear')


###########################################################################
# stampa lista con informazioni su come utilizzare i comandi
def showAllCommands():
    return "\nList of all available commands: \n" \
          "help                 : show this help\n" \
          "clear                : clear the terminal\n" \
          "server               : print server IP and port\n" \
          "get <filename>       : downloads the specified file, if available on server\n" \
          "put <path_to_file>   : uploads the specified file to the server\n" \
          "list                 : shows list of all files available on server\n" \
          "shutdown             : switch off both server and client\n" \
          "end                  : close connection to the server"


###########################################################################
# ottiene MD5 del file specificato
def getMD5ofFile(filePath):
    fp = open(filePath, "rb") # apre file in lettura binaria
    filecontent = fp.read()
    return hashlib.md5(filecontent).hexdigest()


###########################################################################
# ottiene MD5 della stringa specificata
def getMD5ofString(stringa):
    return hashlib.md5(stringa).hexdigest()


###########################################################################
# utility per invio di pacchetti
def sendMsg(msgNotEncoded, serverAddr, encode):
    if encode == 'encode':
        s.sendto(msgNotEncoded.encode(), serverAddr)
    else:
        s.sendto(msgNotEncoded, serverAddr)
    
    
###########################################################################
# utility per ricezione di pacchetti
def receiveMsg(decode):
    data, serverAddr = s.recvfrom(PACKET_SIZE)
    if decode == 'decode':
        return data.decode('utf-8'), serverAddr
    else:
        return data, serverAddr
    

###########################################################################
# utility per ottenere numero totale di pacchetti che saranno inviati
def getNumberOfPacketsToSend(fileSize):
    numOfPkt = int(fileSize / PACKET_SIZE)
    if (fileSize % PACKET_SIZE) != 0:
        numOfPkt = numOfPkt + 1
    return numOfPkt


###########################################################################
# gestisce ricezione di lista di file da server (comando list)
def ClientList():
    fileList = ''
    try:
        text, clientAddr = receiveMsg('decode')
    except Exception:
        print(TIMEOUT_ERRMSG)
        sys.exit()
    
    if text == "Valid List command":
        cont = 0 # contatore di pacchetti ricevuti
        try:
            # countPckt: number of packets to be received
            CountPckt, countaddress = receiveMsg('decode')
        except Exception:
            print(TIMEOUT_ERRMSG)
            sys.exit()
    
        pcktNum = int(CountPckt) # numero totale di pacchetti che formano la lista
        
        while cont < pcktNum:
            try:    
                ClientBData, clientbAddr = receiveMsg('NOdecode') # client riceve pacchetto
                md5Pckt = getMD5ofString(ClientBData) # md5 del pacchetto ricevuto
                ClientBDataDecoded = ClientBData.decode('utf-8')
                
                sendMsg("md5 " + md5Pckt, serverAddr, 'encode') # invia md5 del pacchetto ricevuto
                md5Server, clientbAddr = receiveMsg('decode') # client riceve risposta se md5 ok
                
                if md5Server == 'ok':   
                    fileList = fileList + ClientBDataDecoded # concatena i pezzi di lista
                    cont += 1
                    print("\tReceived packet " + str(cont) + " of " + str(pcktNum), end='\r') # cont: ultimo pacchetto ricevuto
                    
            except socket.timeout as ex:
                print("\tan exception occurred (timeout): \t", ex)
                sys.exit()
                
        if cont == pcktNum:  
            sendMsg("finished", serverAddr, 'encode') # indica che tutta la lista è stata ricevuta per intero
        
        print("\n\tChecking list integrity...")
        md5List = getMD5ofString(fileList.encode()) # ottiene md5 di filelist
        sendMsg(md5List, serverAddr, 'encode') # invia al server md5 di lista ricevuta
        try:
            msgListServer, clientbAddr = receiveMsg('decode') # riceve da server msg se lista ok o corrotta
        except Exception:
            print(TIMEOUT_ERRMSG)
            sys.exit()
            
        if msgListServer == "list OK":
            print("\t" + msgListServer)
        else:
            print("\tError: try again...")
       
        print(fileList)
        
    else:
        print("Error. Invalid command.")   
        
        
###########################################################################
# gestisce trasferimento di file da client a server (comando put)
def ClientPut(path):
    print("\n\tWaiting for server response...")
    try:
        text, clientAddr = receiveMsg('decode')
    except Exception:
        print(TIMEOUT_ERRMSG)
        sys.exit()
    
    if text == "Ready to receive":
        print("\n\tServer is ready to receive")
        if os.path.exists(path):
            filename = os.path.basename(path) # ottiene nome del file dal percorso
            sendMsg(filename, serverAddr, 'encode') # invia "<nomefile.ext>"
            print("\tFile exist. Sending file " + filename + " to the server... ")
    
            c = 0
            sizeOfFile = os.path.getsize(path) # file size
            numOfPkt = getNumberOfPacketsToSend(sizeOfFile)
            sendMsg(str(numOfPkt), serverAddr, 'encode') # invia "<num di pacchetti totali>"
    
            check = int(numOfPkt)
            fileR = open(path, "rb")
            finishedSuccessfully = False
            
            md5File = getMD5ofFile(path) #file da inviare
            timeStart = datetime.datetime.now() # tempo di inizio download
            while not finishedSuccessfully:
                while c < check:
                    content = fileR.read(PACKET_SIZE)
                    sendMsg(content, serverAddr, 'noEncode') # invia pacchetti in sequenza
                    md5Pckt = getMD5ofString(content) # md5 del pacchetto inviato
                    try:
                        md5Client, server = receiveMsg('decode') # riceve md5 del server
                    except Exception:
                        print(TIMEOUT_ERRMSG)
                        sys.exit()
                    md5ClientS = md5Client.split(" ", 1)
                    
                    if md5ClientS[1] == md5Pckt:
                        sendMsg("ok", serverAddr, 'encode') #client conferma pacchetto corretto
                        c += 1
                        print("\tSent packet " + str(c) + " of " + str(numOfPkt), end='\r') # cont: ultimo pacchetto ricevuto
                    else: #se pacchetto corrotto
                        print("\tpacket corrupted number:", c , "\n\n")
                    
                
                # se server invia msg Finished, significa che ha ricevuto tutto il file con successo
                msgFinished = ''
                try:
                    msgFinished, server = receiveMsg('decode') # per sapere se ha ricevuto tutto
                except Exception as ex:
                    print("\tException: \n\n", ex)
                
                if msgFinished == 'finished': 
                    finishedSuccessfully = True
                    fileR.close()
                    try:
                        md5FileServer, server = receiveMsg('decode') # server invia md5 di file ricevuto
                    except Exception:
                        print(TIMEOUT_ERRMSG)
                        sys.exit()
                    
                    print("\n\tChecking file integrity...")
                    msg = ''
                    if md5FileServer == md5File:
                        msg = "file OK"
                        timeEnd = datetime.datetime.now()
                    else:
                        msg = "file CORRUPTED, try again"
                    print("\t" + msg)
                    sendMsg(msg, serverAddr, 'encode')
                    print("\t" + getElapsedTime(timeStart, timeEnd) + " (Upload)") # calcola tempo impiegato per upload di file
            
        else:
            msg = ""
            sendMsg(msg, serverAddr, 'encode')
            print("Error: the file you typed in does not exist on this device")
    else:
            msg = "Error: the server is NOT ready to receive"
            sendMsg(msg, serverAddr, 'encode')
            print(msg)
 
    
###########################################################################
# gestisce trasferimento di file da server a client (comando get)
def ClientGet(filename):
    print("\n\tWaiting for server response...")
    try:
        text, clientAddr = receiveMsg('decode')
    except Exception:
        print(TIMEOUT_ERRMSG)
        sys.exit()
    print("\n\tServer is ready to send")
    
    try:
        text2, clientAddr2 = receiveMsg('decode')
    except:
        print(TIMEOUT_ERRMSG)
        sys.exit()
    
    if text2 == "File exists": # se file esiste in server
        receivedFile = open(dir_path + "Received-" + filename, "wb")
        cont = 0 # contatore di pacchetti ricevuti e poi scritti in file
        try:
            # countPckt: number of packets to be received
            CountPckt, countaddress = receiveMsg('decode')
        except Exception:
            print(TIMEOUT_ERRMSG)
            sys.exit()
    
        pcktNum = int(CountPckt) # numero totale di pacchetti che formano il file
        print("\tFile exists. Download of packets is starting...")
        
        timeStart = datetime.datetime.now() # tempo di inizio download
        while cont < pcktNum:
            try:    
                ClientBData, clientbAddr = receiveMsg('NO decode') # client riceve pacchetto
                md5Pckt = getMD5ofString(ClientBData) # md5 del pacchetto ricevuto
                
                sendMsg("md5 " + md5Pckt, serverAddr, 'encode') # invia md5 del pacchetto ricevuto
                md5Server, clientbAddr = receiveMsg('decode') # client riceve risposta se md5 ok
                
                if md5Server == 'ok':   
                    receivedFile.write(ClientBData)    
                    cont += 1
                    print("\tReceived packet " + str(cont) + " of " + str(pcktNum), end='\r') # cont: ultimo pacchetto ricevuto
                    
            except socket.timeout as ex:
                print("\tan exception occurred (timeout): \n\n", ex)
                
        if cont == pcktNum:  
            timeEnd = datetime.datetime.now()
            sendMsg("finished", serverAddr, 'encode') # indica che il file è stato ricevuto per intero
        receivedFile.close() 
        
        print("\n\tChecking file integrity...")
        md5File = getMD5ofFile(dir_path + "Received-" + filename) # ottiene md5 di file ricevuto
        sendMsg(md5File, serverAddr, 'encode') # invia al server md5 di file ricevuto
        try:
            msgFileServer, clientbAddr = receiveMsg('decode') # riceve da server msg se file ok o corrotto
        except Exception:
            print(TIMEOUT_ERRMSG)
            sys.exit()
            
        if msgFileServer == "file OK":
            print("\t" + msgFileServer)
            
            print("\t" + getElapsedTime(timeStart, timeEnd) + " (Download)") # calcola tempo impiegato per download di file
        else:
            print("\tError: file is corrupted, try to download the file again...")
            if os.path.exists(dir_path + "Received-" + filename):
                os.remove(dir_path + "Received-" + filename)
    else:
        print("\tError: File does not exist in server directory")
    
    
###########################################################################
# chiude socket ed esce
def ClientExit():
    print("Client will gracefully exit!")
    time.sleep(1)
    print("Goodbye...")
    s.close()
    sys.exit(0)
    
    
#######################################################
#           fine definizione di funzioni              #
#######################################################

if __name__ == '__main__':
    if ok_args():
    	 #usa IP e porta del server ottenuti da riga di comando
         address = sys.argv[1]
         port = int(sys.argv[2])
    else:
         print_args()
         sys.exit(0)
    
    serverAddr = (address, port)
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.setblocking(0)
    except socket.error:
        print("Failed to create socket")
        sys.exit()
     
    if not os.path.exists(dir_path): 
       os.makedirs(dir_path)
       
    msgACK = 'Asking for connection...' # msg per ack
    print(msgACK + "\n")
    
    try:
        sendMsg(msgACK, serverAddr, 'encode')
    except Exception as ex:
        print("Error: ", ex)
        sys.exit()
        
    try:
        s.settimeout(5)
        msgEstablished, clienAddr = receiveMsg('decode')
        print(msgEstablished)
    except Exception:
        print("Server not found")
        sys.exit()
        
    print("\nWELCOME!")
    print_serverIP()
    print(showAllCommands()) # stampa info su tutti i comandi
    
    while True:
        command = input("\nType in a command: \n> ")
        try:
            sendMsg(command, serverAddr, 'encode')
        except Exception:
            print("Error. Restart client.")
            sys.exit()
        
        cmdArgs = command.split(' ', 1)   
        commd = cmdArgs[0]
                
        if commd == "get":
            ClientGet(cmdArgs[1])
                              
        elif commd == "put":
            ClientPut(cmdArgs[1])
            
        elif commd == "list":
           ClientList()

        elif commd == 'shutdown' or commd == 'end':
            ClientExit()
            
        elif commd == "help":
            print(showAllCommands())
                
        elif commd == 'clear':
            clearScreen()
            
        elif commd == 'server':
            print_serverIP()
            
        else:
            try:
                text, clientAddr = receiveMsg('decode')
            except Exception:
                print(TIMEOUT_ERRMSG)
                sys.exit()
            print(text)
            
            