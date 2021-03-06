# coding=utf-8

from random import randint
from time import sleep

from devices.IDevice import IDevice
from utils import run_in_thread


class DemoBand(IDevice):
    """
    Class that simulates a real band, for debugging purposes.
    """

    def __init__(self):
        self.connected = False
        self.end_test = False
        self.ended_test = False
        self.end_acquisition = False
        self.ended_acquisition = False

    # --------------------------------------------------------
    # Follow methods have not any business logic. Only appears
    # because DemoBand class implements IDevice interface.

    @classmethod
    def find(cls):
        pass

    def connect(self, *args):
        self.connected = True

    def disconnect(self):
        self.connected = False

    def run_test(self, notify_window):
        pass

    def finish_test(self):
        pass

    def stabilize(self):
        pass

    # --------------------------------------------------------

    @run_in_thread
    def begin_acquisition(self, writer=None):
        """
        Starts a fake acquisition.
        @param writer: Object that writes all generated data.
        """
        self.end_acquisition = False
        self.ended_acquisition = False
        while not self.end_acquisition:
            wait_value = randint(800, 900)
            sleep(wait_value / 1000.0)
            rr = wait_value
            if writer:
                writer.write_rr_value(rr)
        self.ended_acquisition = True
        if writer:
            writer.close_writer()

    def finish_acquisition(self):
        """
        Finishes acquisition
        """
        self.end_acquisition = True



