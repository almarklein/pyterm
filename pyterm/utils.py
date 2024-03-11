import socket
import logging

logger = logging.getLogger("pyterm")
logger.setLevel(logging.INFO)

PORT = 12013


class UDPHandler(logging.Handler):
    udp_address = ("127.0.0.1", PORT)

    def __init__(self):
        super().__init__()
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def emit(self, record):
        msg = self.format(record)
        bb = msg.encode()
        size = 2**10
        while bb:
            bb1 = bb[:size]
            bb = bb[size:]
            self._socket.sendto(bb1, self.udp_address)


logger.addHandler(UDPHandler())
# logger.addHandler(logging.StreamHandler())


def listen_to_logs():
    """Called from ``pyterm --listen```

    This way we can see the logs from another process, so it does not get mixed up in the handling of error streams.
    """

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("127.0.0.1", PORT))

    while True:
        data, addr = sock.recvfrom(2**20)
        print(data.decode())
