#!/usr/bin/env python3.8
# ----------------------------
# Author: Peter Zdravecký
# Date: 22.2.2021
# Description: Filget for fsp protocl
# Name: fileget.py
# Version: 1.0
# Python 3.8
# ----------------------------

from socket import *
import argparse
import re
import os
import sys

LOGIN = "xzdrav00"

# ------------------------------------------------------


def whereis(server_name, server_ip, server_port):
    try:
        _socket = socket(AF_INET, SOCK_DGRAM)
    except:
        print("Error: creating socket", file=sys.stderr)
        sys.exit(1)

    _socket.settimeout(30)

    try:
        _socket.sendto(f"WHEREIS {server_name}\r\n".encode(
            "utf-8"), (server_ip, server_port))
    except:
        print("Error: sending data", file=sys.stderr)
        sys.exit(1)

    try:
        recv = _socket.recv(4096)
    except:
        print("Error: reciving data", file=sys.stderr)
        sys.exit(1)

    _socket.close()

    status = recv[:recv.find(b" ")]
    result = recv[recv.find(b" ") + 1:]
    if status != b"OK":
        print(
            f"Error: WHEREIS server response for '{server_name}' is '{result}'", file=sys.stderr)
        sys.exit(1)

    return result


def get(filename, domain_name, domain_ip, domain_port, full_path=False):
    try:
        _socket = socket(AF_INET, SOCK_STREAM)
    except:
        print("Error: creating socket", file=sys.stderr)
        sys.exit(1)

    _socket.settimeout(30)

    try:
        _socket.connect((domain_ip, domain_port))
    except:
        print(
            f"Problem with connection to '{domain_ip}:{domain_port}'", file=sys.stderr)
        sys.exit(1)

    try:
        _socket.send(
            f"GET {filename} FSP/1.0\r\nHostname: {domain_name}\r\nAgent: {LOGIN}\r\n\r\n".encode("utf-8"))
    except:
        print("Error: sending data", file=sys.stderr)
        sys.exit(1)

    try:
        recv = _socket.recv(4096)
        header = recv[:recv.find(b"\r\n\r\n")]
        data = recv[recv.find(b"\r\n\r\n")+4:]
    except:
        print("Error: reciving data", file=sys.stderr)
        sys.exit(1)

    if re.search(b"Not Found", header):
        print(
            f"Error: the specified file '{filename}' was not found.", file=sys.stderr)
        sys.exit(1)
        return

    if re.search(b"Bad Request", header):
        print(f"Error: bad request", file=sys.stderr)
        sys.exit(1)
        return

    if re.search(b"Server Error", header):
        print(f"Error: server error", file=sys.stderr)
        sys.exit(1)
        return
    
    length = 0
    excpectedLength = header[header.find(b":")+1:].strip().decode("utf-8")
    if not excpectedLength.isnumeric():
        sys.exit(1)

    try:
        if full_path:
            _file = open(filename, "wb")
        else:
            _file = open(os.path.basename(filename), "wb")
    except:
        print("Error: opening file", file=sys.stderr)
        sys.exit(1)

    # write data from header
    _file.write(data)
    length += len(data)
    while 1:
        try:
            recv = _socket.recv(4096)
        except:
            print("Error: reciving data", file=sys.stderr)
            sys.exit(1)
        if not recv:
            break
        _file.write(recv)
        length += len(recv)

    _file.close()
    _socket.close()

    if(length != int(excpectedLength)):
        print(f"Error: Actual legnth: {length} | Expected legnth: {excpectedLength}")
        sys.exit(1)

    # ------------------------------------------------------


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-n', dest='n', required=True)
    parser.add_argument('-f', dest='f', required=True)
    args = parser.parse_args()

    if re.search("[^\d.:]", args.n) or not re.search(":", args.n):
        print(f"Error: server name argument is not valid", file=sys.stderr)
        sys.exit(1)

    SERVER_IP, SERVER_PORT = args.n.split(":")
    SERVER_PORT = int(SERVER_PORT)

    if not re.match("^fsp://", args.f):
        print(
            f"Invalid usage: 'fsp' protocol required. '{args.f}'", file=sys.stderr)
        sys.exit(1)

    args.f = args.f.replace("fsp://", "")
    SERVER_NAME = args.f[:args.f.find("/")]

    if re.search("[^A-Za-z0-9-_.]", SERVER_NAME):
        print(f"Invalid usage: server name contain invalid characters. '{SERVER_NAME}'",
              file=sys.stderr)
        sys.exit(1)

    FILE_PATH = args.f[args.f.find("/") + 1:]

    DOMAIN = whereis(SERVER_NAME, SERVER_IP, SERVER_PORT)
    DOMAIN_IP, DOMAIN_PORT = DOMAIN.split(b":")
    DOMAIN_PORT = int(DOMAIN_PORT)

    if os.path.basename(FILE_PATH) == "*":  # get all
        get("index", SERVER_NAME, DOMAIN_IP, DOMAIN_PORT)
        try:
            index = open("index", "r")
        except:
            print("Error: opening file 'index'", file=sys.stderr)
            sys.exit(1)

        for _file in index:
            _file = _file.strip()
            print(f"GET: {_file}")
            if FILE_PATH == "*":  # get all files from server
                if os.path.dirname(_file) != "":
                    os.makedirs(os.path.dirname(_file), exist_ok=True)

                get(_file, SERVER_NAME, DOMAIN_IP, DOMAIN_PORT, True)
            else:                 # get all from subdirectory
                if re.match(f"^{os.path.dirname(FILE_PATH)}", _file):
                    get(_file, SERVER_NAME, DOMAIN_IP, DOMAIN_PORT)

        index.close()
    else:  # get file from server
        print(f"GET: {FILE_PATH}")
        get(FILE_PATH, SERVER_NAME, DOMAIN_IP, DOMAIN_PORT)
    
    print("SUCCESS")


if __name__ == '__main__':
    main()
