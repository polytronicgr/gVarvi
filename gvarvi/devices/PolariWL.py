# coding=utf-8

from wx import PostEvent

from devices.BTDevice import BTDevice
from utils import run_in_thread
from utils import ResultEvent
from logger import Logger


class PolariWL(BTDevice):
    """
    A class that represents a Polar WearLink+ band.
    @param mac: Physical address of the band.
    """

    def __init__(self, mac):
        BTDevice.__init__(self, mac)
        self.logger = Logger()
        self.socket = None
        self.end_test = False
        self.ended_test = False
        self.end_acquisition = False
        self.ended_acquisition = False
        self.correct_data = False
        self.error = False
        self.min_rr = 550

    @run_in_thread
    def run_test(self, notify_window):
        """
        Run test for Polar WearLink+ device.
        @param notify_window: Window that device will send test data.
        """
        self.end_test = False
        self.ended_test = False
        self.error = False
        test_dict = {}
        while not self.end_test:
            try:
                data1 = self.receive(1)
                data2 = self.receive(1)
                ll = int(data2, 16)
                data3 = self.receive(ll - 2)

                chk = int(data3[0:2], 16)
                if chk + ll != 255:
                    self.logger.error("Package not ok")

                hr = int(data3[6:8], 16)
                test_dict['hr'] = hr
                self.logger.debug("Heart rate: {0} bpm".format(hr))
                next_bit = 8

                for i in range((ll - 6) / 2):  # rr values per packet
                    rr1 = int(data3[next_bit:next_bit + 2], 16)
                    rr2 = int(data3[next_bit + 2:next_bit + 4], 16)
                    test_dict['rr'] = (rr1 << 8) | rr2
                    if self.end_test:
                        break
                    PostEvent(notify_window, ResultEvent(test_dict))

                    next_bit += 4

            except ValueError:
                if not self.end_test:  # Exception only works if BT is still connected
                    self.logger.exception("ValueError raised: data not Ok")
                    import traceback
                    import os.path

                    top = traceback.extract_stack()[-1]
                    self.logger.debug("Program:", os.path.basename(top[0]), " -  Line:", str(top[1]))
                    self.logger.debug("Data1: {0}".format(data1))
                    self.logger.debug("Data2: {0}".format(data2))
                    self.logger.debug("Data3: {0}".format(data3))

                    self.error = True
                else:
                    self.logger.warning("ValueError raised at the end of the acquisition")

        self.ended_test = True
        self.logger.warning("Ended test")

    def finish_test(self):
        """
        Finishes test for Polar WearLink+ device.
        """
        self.end_test = True

    def stabilize(self):
        """
        Prevent to retrieve noisy initial data
        """
        minimum_value = 20
        maximum_value = 250
        hr = 0
        while hr < minimum_value or hr > maximum_value:
            try:
                data1 = self.receive(1)
                data2 = self.receive(1)
                ll = int(data2, 16)
                data3 = self.receive(ll - 2)

                chk = int(data3[0:2], 16)
                if chk + ll != 255:
                    self.logger.error("Package not ok")
                    continue

                hr = int(data3[6:8], 16)

            except ValueError:
                continue

    @run_in_thread
    def begin_acquisition(self, writer):
        """
        Starts acquisition and write rr values.
        @param writer: Object that writes rr values.
        """
        self.end_acquisition = False
        self.ended_acquisition = False
        self.error = False
        while not self.end_acquisition:
            try:
                data1 = self.receive(1)
                data2 = self.receive(1)
                ll = int(data2, 16)
                data3 = self.receive(ll - 2)
                chk = int(data3[0:2], 16)
                if chk + ll != 255:
                    self.logger.error("Package not OK")

                seq = int(data3[2:4], 16)
                self.logger.debug("Package seq: {0}".format(seq))

                status = int(data3[4:6], 16)
                self.logger.debug("Package status: {0}".format(status))

                hr = int(data3[6:8], 16)
                self.logger.debug("Heart rate: {0} bpm".format(hr))
                nextbit = 8

                self.logger.debug("Package contains {0} beats".format((ll - 6) / 2))

                for i in range((ll - 6) / 2):  # rr values per packet
                    rr1 = int(data3[nextbit:nextbit + 2], 16)
                    rr2 = int(data3[nextbit + 2:nextbit + 4], 16)
                    rr = (rr1 << 8) | rr2

                    self.logger.debug("RR: {0} mseg".format(rr))

                    if rr > self.min_rr and not self.correct_data:
                        self.correct_data = True

                    writer.write_rr_value(rr)

                    nextbit += 4

            except ValueError:
                if not self.end_acquisition:  # Exception only works if BT is still connected
                    self.logger.exception("ValueError raised: data not Ok")
                    import traceback
                    import os.path

                    top = traceback.extract_stack()[-1]
                    self.logger.debug("Program:", os.path.basename(top[0]), " -  Line:", str(top[1]))
                    self.logger.debug("Data1: {0}".format(data1))
                    self.logger.debug("Data2: {0}".format(data2))
                    self.logger.debug("Data3: {0}".format(data3))
                    self.error = True
                else:
                    self.logger.warning("ValueError raised at the end of the acquisition")

            except Exception as e:
                import traceback
                import os.path

                top = traceback.extract_stack()[-1]
                self.logger.exception("*** Exception:", type(e), " -  Program:", os.path.basename(top[0]),
                                      " -  Line:", str(top[1]), "***")
                self.error = True

            if self.end_acquisition:
                self.ended_acquisition = True
                writer.close_writer()
                break

    def finish_acquisition(self):
        """
        Finishes acquisition for Polar WearLink+ device.
        """
        self.end_acquisition = True
