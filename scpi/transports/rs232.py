"""Serial port transport layer"""
import serial
import serial.threaded

from .baseclass import BaseTransport

WRITE_TIMEOUT = 1.0


class RS232SerialProtocol(serial.threaded.LineReader):
    """PySerial "protocol" class for handling stuff"""
    ENCODING = 'ascii'

    def connection_made(self, transport):
        """Overridden to make sure we have write_timeout set"""
        super().connection_made(transport)
        # Make sure we have a write timeout of expected size
        self.transport.write_timeout = WRITE_TIMEOUT

    def handle_line(self, line):
        raise RuntimeError("This should have been overloaded by RS232Transport")


class RS232Transport(BaseTransport):
    """Uses PySerials ReaderThread in the background to save us some pain"""
    serialhandler = None

    def __init__(self, serial_device):
        self.serialhandler = serial.threaded.ReaderThread(serial_device, RS232SerialProtocol)
        self.serialhandler.start()
        self.serialhandler.protocol.handle_line = self.message_received

    async def send_command(self, command):
        """Wrapper for send_line on the protocol"""
        if not self.serialhandler or not self.serialhandler.is_alive():
            raise RuntimeError("Serial handler not ready")
        with (await self.lock):
            self.serialhandler.protocol.write_line(command)

    async def abort_command(self):
        """Uses the break-command to issue "Device clear", from the SCPI documentation (for HP6632B): The status registers, the error queue, and all configuration states are left unchanged when a device clear message is received. Device clear performs the following actions:
 - The input and output buffers of the dc source are cleared.
 - The dc source is prepared to accept a new command string."""
        with (await self.lock):
            self.serialhandler.serial.send_break()

    async def quit(self):
        """Closes the port and background threads"""
        self.serialhandler.close()


def get(serial_url, **serial_kwargs):
    """Shorthand for creating the port from url and initializing the transport"""
    port = serial.serial_for_url(serial_url, **serial_kwargs)
    return RS232Transport(port)
