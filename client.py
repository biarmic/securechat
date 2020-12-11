import socket
import threading
import sys
from utils import *

serverKey = None
keys = {}
keyShared = False
toSend = None
loggedIn = False
helpMessage = """
          COMMAND           |                    DESCRIPTION
===============================================================================
!help                       |      Prints command list.
                            |
!register                   |      Register to server.
!login                      |      Log in to your account.
!logout                     |      Log out from your account.
!exit                       |      Exits the application.
                            |
@[username] [message]       |      Send message to a user.
                            |
!block      [username]      |      Blocks all messages coming from a user.
!unblock    [username]      |      Starts receiving messages again from a user.
"""

def receive(socket, signal):
    """ Waits for incoming messages and processes them. """
    global serverKey, keys, keyShared, toSend, loggedIn
    while signal:
        data = receivePackets(socket)
        if keyShared is True:
            data = decrypt(keys["private"], data)
        if serverKey is None:
            if data.startswith(b"$server-public-key"):
                serverKey = data[19:].decode()
        else:
            if data.startswith(b"$login"):
                data = data[7:]
                if data == b"nouser":
                    print("No user found with that username.")
                elif data == b"wrongpass":
                    print("Wrong password.")
                elif data == b"success":
                    loggedIn = True
                    keyShared = True
                    sendPackets(socket, encrypt(serverKey, str.encode("$client-public-key " + keys["public"])))
                    print("Successfully logged in.")
            elif data.startswith(b"$register"):
                data = data[10:]
                if data == b"exists":
                    print("There is already a user with that username.")
                elif data == b"success":
                    loggedIn = True
                    keyShared = True
                    sendPackets(socket, encrypt(serverKey, str.encode("$client-public-key " + keys["public"])))
                    print("Successfully registered and logged in.")
            elif data.startswith(b"$logout"):
                loggedIn = False
                keyShared = False
                if len(data) > 7:
                    print("Another session started with this account. Forced to log out.")
                else:
                    print("Successfully logged out.")
            elif data.startswith(b"$block"):
                data = data[7:]
                if data == b"nouser":
                    print("No user found with that username.")
                elif data == b"already":
                    print("User already blocked.")
                elif data == b"success":
                    print("Successfully blocked user.")
            elif data.startswith(b"$unblock"):
                data = data[9:]
                if data == b"nouser":
                    print("No user found with that username.")
                elif data == b"already":
                    print("User is not blocked already.")
                elif data == b"success":
                    print("Successfully unblocked user.")
            elif data.startswith(b"$user-offline"):
                print("User is offline.")
            elif data.startswith(b"$user-notfound"):
                print("No user found.")
            elif data.startswith(b"$user-blocked"):
                print("User blocked all messages from you.")
            elif data.startswith(b"$user-notsecure"):
                print("User's connection is not secure at the moment.")
            elif data.startswith(b"$user-public-key"):
                key = data[17:].decode()
                sendPackets(socket, encrypt(serverKey, str.encode("$sending-to " + username + " ") + encrypt(key, str.encode(toSend))))
            elif data.startswith(b"$coming-from"):
                data = data.split(b" ", 2)
                print("@" + data[1].decode() + ":")
                print(decrypt(keys["private"], data[2]).decode())


def isValidUsername(username):
    """ Checks if a username is valid. """
    if len(username) < 4 or " " in username or "!" in username or "@" in username or "$" in username:
        return False
    return True

if __name__ == "__main__":
    keys = readFile("crypto-client")
    if keys is None:
        keys = generateKeys()
        writeFile("crypto-client", keys)
    print("Welcome to SecureChat.")
    host = input("Host: ")
    port = int(input("Port: "))

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((host, port))
    except:
        print("Could not make a connection to the server. Please check your internet connection and/or firewall settings.")
        input("Press enter to quit.")
        sys.exit(0)

    receiveThread = threading.Thread(target=receive, args=(sock, True), daemon=True)
    receiveThread.start()

    while True:
        command = input()
        if command == "!help":
            print(helpMessage)
        elif command == "!exit":
            sendPackets(sock, encrypt(serverKey, b"$close"))
            sys.exit(0)
        elif not loggedIn:
            if command == "!login" or command == "!register":
                username = input("Username: ")
                if isValidUsername(username):
                    password = input("Password: ")
                    sendPackets(sock, encrypt(serverKey, str.encode("$" + command[1:] + " " + username + " " + password)))
                else:
                    print("Invalid username. A username must be longer than 3 characters and cannot include ' ', '!', '@', or '$'.")
            else:
                print("You need to login or register to proceed. Type !help for more information.")
        else:
            if command == "!logout":
                sendPackets(sock, encrypt(serverKey, b"$logout"))
            elif command.startswith("!block"):
                sendPackets(sock, encrypt(serverKey, b"$block " + str.encode(command[7:])))
            elif command.startswith("!unblock"):
                sendPackets(sock, encrypt(serverKey, b"$unblock " + str.encode(command[9:])))
            elif command.startswith("@"):
                message = command.split(" ", 1)
                username = message[0][1:]
                message = message[1]
                sendPackets(sock, encrypt(serverKey, str.encode("$request-public-key " + username)))
                toSend = message
            else:
                print("Unknown command. Type !help for more infomation.")