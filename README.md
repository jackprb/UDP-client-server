# UDP-client-server

Basic client - server application to transfer files, UDP based

To run the application, you need to run the files **in two distinct terminal windows** as follows:
  1. `python server.py <port number>`
  2. `python client.py 127.0.0.1 <port number>` 

The main features are:
-	View available files on server
- Download file from server to client
-	Upload file from client to server


List of all commands available:

*  `help`                 : show this help
*  `clear`                : clear the terminal
*  `server`               : print server IP and port
*  `get <filename>`       : downloads the specified file, if available on server
*  `put <path_to_file>`   : uploads the specified file to the server
*  `list`                 : shows list of all files available on server
*  `shutdown`             : switch off both server and client
*  `end`                  : close connection to the server

