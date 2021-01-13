from socket import socket, AF_INET, SOCK_STREAM

from polybar_clockify.settings import UNIX_PORT, UNIX_HOST


def send_to_socket(message):
    s = socket(AF_INET, SOCK_STREAM)
    s.connect((UNIX_HOST, UNIX_PORT))
    s.send(message)
    s.close()
