import socket
import sys
import os
import hashlib
import datetime

#######################################################
#   costanti con i valori di default                  #
#######################################################
# porta e IP del server DI DEFAULT, se non specificato da riga di comando
port = 6000
host = 'localhost'

#cartella dove si trovano tutti i file del server
dir_path = os.getcwd() + os.path.sep + "files" + os.path.sep

PACKET_SIZE = 32768
TIMEOUT_ERRMSG = "Timeout or some other error"

#######################################################
#   definizione di funzioni utilizzate lato server    #
#######################################################

###########################################################################
# restituisce tempo trascorso per upload/download di un file
def getElapsedTime(timeStart, timeEnd):
    tme = timeEnd - timeStart
    tme.resolution
    return "Elapsed time: " + str(tme.seconds) + " second(s)"


###########################################################################
# ottiene STRINGA ben formattata di tutti i file in cartella di file condivisi
def getAllFiles():
    listFiles = os.listdir(dir_path)
    stringFiles = '\nList of all files on server\n'
    for i in listFiles:
        cont = 30-len(i)
        stri = " "*cont
        stringFiles += i + stri + "\t\t " + str(os.path.getsize(dir_path+i)) + " Byte(s)\n"
    return stringFiles


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
def sendMsg(msgNotEncoded, clientAddr, encode):
    if encode == 'encode':
        s.sendto(msgNotEncoded.encode(), clientAddr)
    else:
        s.sendto(msgNotEncoded, clientAddr)
    
    
###########################################################################
# utility per ricezione di pacchetti
def receiveMsg(decode):
    data, clientAddr = s.recvfrom(PACKET_SIZE)
    if decode == 'decode':
        return data.decode('utf-8'), clientAddr
    else:
        return data, clientAddr
    
    
###########################################################################
# utility per ottenere numero totale di pacchetti che saranno inviati
def getNumberOfPacketsToSend(fileSize):
    numOfPkt = int(fileSize / PACKET_SIZE)
    if (fileSize % PACKET_SIZE) != 0:
        numOfPkt = numOfPkt + 1
    return numOfPkt


###########################################################################
# controlla se ci sono tutti gli argomenti necessari passati da riga di comando
def ok_args():
    if len(sys.argv) != 2:
        print("Wrong number of arguments.\n\n" \
              "Run this file as follows: \n" \
              "\tpython server.py <server port>")
        sys.exit()
        return False
    else:
        return True


###########################################################################
# gestisce invio di lista di file disponibili sul server (comando list)
def ServerList():
    msg = "Valid List command"
    sendMsg(msg, clientAddr, 'encode')
    print("\n" + msg)

    FileListStr = getAllFiles()
    FileListEncoded = FileListStr.encode()
        
    c = 0
    size = len(FileListEncoded) # string size
    numOfPkt = getNumberOfPacketsToSend(size)# get number of packets to send
    sendMsg(str(numOfPkt), clientAddr, 'encode')
    
    finishedSuccessfully = False
    check = int(numOfPkt)
    md5List = getMD5ofString(FileListEncoded) # lista da inviare
    while not finishedSuccessfully:
        while c < check:
            content = FileListEncoded[c*PACKET_SIZE :(c+1)*PACKET_SIZE]
                        
            sendMsg(content, clientAddr, 'noEncode')
            md5Pckt = getMD5ofString(content) # md5 del pacchetto inviato
            print("\tsent packet number:" , str(c+1), end='\r')
            try:
                md5Client, client = receiveMsg('decode') # riceve md5 del client
            except Exception:
                print(TIMEOUT_ERRMSG)
                sys.exit()
            md5ClientS = md5Client.split(" ", 1)
            
            if md5ClientS[1] == md5Pckt:
                sendMsg("ok", clientAddr, 'encode') #server conferma pacchetto corretto
                c += 1
            else: #se pacchetto corrotto
                print("\tpacket corrupted number:", c , "\n\n")
            
        # se client invia msg Finished, significa che ha ricevuto tutta la lista con successo
        msgFinished = ''
        try:
            msgFinished, countaddress = receiveMsg('decode') # per sapere se ha ricevuto tutto
        except Exception as ex:
            print("\tException: \n\n", ex)
        
        if msgFinished == 'finished': 
            finishedSuccessfully = True
            try:
                md5ListClient, clientaddress = receiveMsg('decode') # client invia md5 di lista ricevuta
            except Exception:
                print(TIMEOUT_ERRMSG)
                sys.exit()
                
            print("\n\tChecking list integrity...")
            msg = ''
            if md5ListClient == md5List:
                msg = "list OK"
            else:
                msg = "list CORRUPTED, try again"
            print("\t" + msg)
            sendMsg(msg, clientAddr, 'encode')
     
    print("List sent to client")


###########################################################################
# chiude socket ed esce
def ServerExit():
    print("\nServer will gracefully exit! Goodbye...")
    s.close()  # closing socket
    sys.exit()


###########################################################################
# gestisce invio di file da server a client (comando get)
def ServerGet(g):
    msg = "Valid command GET"
    sendMsg(msg, clientAddr, 'encode')
    print("\nGET command accepted: \n")

    if os.path.exists(dir_path + g):
        msg = "File exists"
        sendMsg(msg, clientAddr, 'encode')
        print("\tFile exist. Sending packets to the client: ")

        c = 0
        sizeOfFile = os.path.getsize(dir_path + g) # file size
        numOfPkt = getNumberOfPacketsToSend(sizeOfFile)# get number of packets to send
        sendMsg(str(numOfPkt), clientAddr, 'encode')

        check = int(numOfPkt)
        fileR = open(dir_path + g, "rb")
        finishedSuccessfully = False
        
        timeStart = datetime.datetime.now() # tempo di inizio upload
        while not finishedSuccessfully:
            while c < check:
                content = fileR.read(PACKET_SIZE)
                sendMsg(content, clientAddr, 'noEncode')
                md5Pckt = getMD5ofString(content) # md5 del pacchetto inviato
                print("\tSent packet " + str(c+1) + " of " + str(numOfPkt), end='\r')
                try:
                    md5Client, client = receiveMsg('decode') # riceve md5 del client
                except Exception:
                    print(TIMEOUT_ERRMSG)
                    sys.exit()
                md5ClientS = md5Client.split(" ", 1)
                
                if md5ClientS[1] == md5Pckt:
                    sendMsg("ok", clientAddr, 'encode') #server conferma pacchetto corretto
                    c += 1
                else: #se pacchetto corrotto
                    print("\tpacket corrupted number:", c , "\n\n")
                
            
            # se client invia msg Finished, significa che ha ricevuto tutto il file con successo
            msgFinished = ''
            try:
                msgFinished, countaddress = receiveMsg('decode') # per sapere se ha ricevuto tutto
            except Exception as ex:
                print("\tException: \n\n", ex)
            
            if msgFinished == 'finished': 
                timeEnd = datetime.datetime.now()
                finishedSuccessfully = True
                md5File = getMD5ofFile(dir_path + g) # g: file da inviare
                fileR.close()
                try:
                    md5FileClient, clientaddress = receiveMsg('decode') # client invia md5 di file ricevuto
                except Exception:
                    print(TIMEOUT_ERRMSG)
                    sys.exit()
                    
                print("\n\tChecking file integrity...")
                msg = ''
                if md5FileClient == md5File:
                    msg = "file OK"
                else:
                    msg = "file CORRUPTED, try again"
                print("\t" + msg)
                sendMsg(msg, clientAddr, 'encode')
                print("\t" + getElapsedTime(timeStart, timeEnd) + " (Upload)") # calcola tempo impiegato per upload di file
         
        print("\nComplete GET operation\n")
        
    else:
        msg = "Error: File does not exist in server directory."
        sendMsg(msg, clientAddr, 'encode')
        print("File does not exist in Server directory")


###########################################################################
# gestisce invio di file da client a server (comando put)
def ServerPut(clientAddr):
    print("\nPUT command accepted: \n")
    msg = "Ready to receive"
    sendMsg(msg, clientAddr, 'encode')
    
    try:
        fileName, clientAddr = receiveMsg('decode') # server riceve nome del file
    except:
        print(TIMEOUT_ERRMSG)
        sys.exit()
        
    if fileName != "": # se file esiste nel client
        print("\tReceiving file " + fileName + " from client " + str(clientAddr[0]) + ":" + str(clientAddr[1])) 
        
        receivedFile = open(dir_path + fileName, "wb")
        cont = 0 # contatore di pacchetti ricevuti e poi scritti in file
        try:
            # countPckt: number of packets to be received
            CountPckt, clientAddr = receiveMsg('decode')
        except Exception:
            print(TIMEOUT_ERRMSG)
            sys.exit()
    
        pcktNum = int(CountPckt) # numero totale di pacchetti che formano il file
        print("\tDownload of packets is starting...")
        
        timeStart = datetime.datetime.now() # tempo di inizio download
        while cont < pcktNum:
            try:    
                ClientBData, clientAddr = receiveMsg('NO decode') # client riceve pacchetto
                md5Pckt = getMD5ofString(ClientBData) # md5 del pacchetto ricevuto
                
                sendMsg("md5 " + md5Pckt, clientAddr, 'encode') # invia md5 del pacchetto ricevuto
                md5Server, clientAddr = receiveMsg('decode') # client riceve risposta se md5 ok
                
                if md5Server == 'ok':   
                    receivedFile.write(ClientBData)    
                    cont += 1
                    print("\tReceived packet " + str(cont) + " of " + str(pcktNum), end='\r') # cont: ultimo pacchetto ricevuto
                    
            except socket.timeout as ex:
                print("\tan exception occurred (timeout): \n\n", ex)
                
        if cont == pcktNum:  
            sendMsg("finished", clientAddr, 'encode') # indica che il file è stato ricevuto per intero
        receivedFile.close() 
        
        print("\n\tChecking file integrity...")
        md5File = getMD5ofFile(dir_path + fileName) # ottiene md5 di file ricevuto
        sendMsg(md5File, clientAddr, 'encode') # invia al server md5 di file ricevuto
        try:
            msgFileServer, clientAddr = receiveMsg('decode') # riceve da server msg se file ok o corrotto
        except Exception:
            print(TIMEOUT_ERRMSG)
            sys.exit()
       
        
        if msgFileServer == "file OK":
            print("\t" + msgFileServer)
            timeEnd = datetime.datetime.now()
            print("\t" + getElapsedTime(timeStart, timeEnd) + " (Download)") # calcola tempo impiegato per download di file
        else:
            print("\tError: file is corrupted, try to download the file again...")
        print("\nComplete PUT operation\n")
    else:
        print("Error: no such file to receive from client")
    

###########################################################################
# gestisce comandi non riconosciuti
def ServerElse():
    msg = "\nError: unknown command. \nCommand sent: \t" + cmd[0] 
    sendMsg(msg, clientAddr, 'encode')
    print(msg)
    
#######################################################
#           fine definizione di funzioni              #
#######################################################

if __name__ == '__main__':    
    if ok_args():
        try:
            port = int(sys.argv[1])
        except Exception:
            print("Invalid port number. Exiting...")
            sys.exit()
  
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.bind((host, port))
    except socket.error:
        print("Failed to create server socket")
        sys.exit()
    
    if not os.path.exists(dir_path): 
         os.makedirs(dir_path)
    
    print("Server is ready\n")
    
    while True:
        cicle = True
        # riceve ACK da client
        try:
            ack, clientAddr = receiveMsg('decode')
        except Exception:
            print(TIMEOUT_ERRMSG)
            sys.exit()
        if ack == 'Asking for connection...':
            msgRe = "Connection established"
            print(msgRe + " with " + str(clientAddr[0]) + ":" + str(clientAddr[1]))
            sendMsg(msgRe, clientAddr, 'encode')
            
            while cicle:
                try:
                    command, clientAddr = receiveMsg('decode')
                except Exception:
                    print("Error. Try again")
                    sys.exit()
                    
                cmd = command.split(" ", 1)
                
                if cmd[0] == "get":
                    ServerGet(cmd[1])
                    
                elif cmd[0] == "put":
                    ServerPut(clientAddr)
                    
                elif cmd[0] == "list":
                    ServerList()
                    
                elif cmd[0] == 'shutdown':
                    ServerExit()
                
                elif cmd[0] == 'help' or cmd[0] == 'clear' or cmd[0] == 'server':
                    print("\nDo nothing, operation for client only (" + cmd[0] + ")")
                
                elif cmd[0] == 'Asking' :
                    print("\nNew client connected. Welcome!")
                    sendMsg(msgRe, clientAddr, 'encode')
                    
                elif cmd[0] == 'end' :
                    cicle = False
                    print("\nWaiting for another client...")              
                else:
                    ServerElse()
            
    print("Program will end now. ")
    quit()