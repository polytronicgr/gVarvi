# coding=utf-8
import shutil
import os

from dao.XMLMapper import XMLMapper
from utils import Singleton, unpack_tar_file_and_remove, open_file, TarFileNotValid
from facade.AcquisitionFacade import AcquisitionFacade
from devices.PolariWL import PolariWL
from devices.DemoBand import DemoBand
from devices.ANTDevice import ANTDevice
from facade.Writer import TextWriter
from config import DEVICE_CONNECTED_MODE, DEMO_MODE, CONF_DIR, RECENT_ACQUISITIONS_FILE
from logger import Logger
from devices.BTDevice import BTDevice
from utils import run_in_thread


class MainFacade:
    """
    Class that manages all view operations and delegates
    their execution to specific classes.
    @param activ_file: Path to activities file.
    @param conf_file: Path to configuration file.
    """
    __metaclass__ = Singleton

    def __init__(self, activ_file, conf_file):
        self.logger = Logger()

        self.act_file_path = activ_file
        self.conf_file_path = conf_file
        self.xml_mapper = XMLMapper(self.act_file_path, self.conf_file_path)
        self.activities = self.parse_activities_file()
        self.recent_acquisitions = self.get_recent_acquisitions()
        self.valid_devices = ["Polar iWL", "ANT+ HR Band"]
        self.conf = None
        self.test_thread = None
        self.acquisition_path = None
        self.testing_device = None

    def activate_remote_debug(self, ip, port):
        self.logger.activate_datagram_logging(ip, port)

    def deactivate_remote_debug(self):
        self.logger.deactivate_datagram_logging()

    def parse_activities_file(self):
        self.activities = self.xml_mapper.read_activities_file()
        map(self.logger.debug, self.activities)
        return self.activities

    def check_acquisition_result_files_exists(self):
        if os.path.isfile(self.acquisition_path + ".tag.txt") and os.path.isfile(self.acquisition_path + ".rr.txt"):
            return True
        else:
            return False

    def get_recent_acquisitions(self):
        with open(RECENT_ACQUISITIONS_FILE) as f:
            return [line for line in f.read().split(os.linesep) if line != ""]

    def refresh_activities(self):
        self.activities = self.parse_activities_file()

    def parse_config_file(self):
        self.conf = self.xml_mapper.read_config_file()
        return self.conf

    def reset_config(self):
        self.xml_mapper.reset_config()
        self.parse_config_file()

    def save_config(self):
        self.xml_mapper.save_config(self.conf.__dict__)

    def get_activity(self, activity_id):
        return self.xml_mapper.get_activity(activity_id)

    def add_activity(self, activity_class, *args, **kwargs):
        activity = activity_class(*args, **kwargs)
        self.xml_mapper.save_activity(activity)
        self.refresh_activities()

    def update_activity(self, activity_class, *args, **kwargs):
        activity = activity_class(*args, **kwargs)
        self.xml_mapper.update_activity(activity.id, activity)
        self.refresh_activities()

    def remove_activity(self, activity_id):
        self.xml_mapper.remove_activity(activity_id)
        self.refresh_activities()

    def import_activity_from_file(self, activity_file):
        from activities.PhotoPresentation import PhotoPresentation
        from activities.SoundPresentation import SoundPresentation
        from activities.VideoPresentation import VideoPresentation
        from activities.AssociatedKeyActivity import AssociatedKeyActivity
        from activities.ManualDefinedActivity import ManualDefinedActivity
        try:
            activity_folder = CONF_DIR
            unpack_tar_file_and_remove(activity_file, activity_folder)
            files = os.listdir(os.path.join(activity_folder, "activity_auxiliary_folder"))
            class_dict = {"photo.xml": PhotoPresentation,
                          "sound.xml": SoundPresentation,
                          "video.xml": VideoPresentation,
                          "key.xml": AssociatedKeyActivity,
                          "manual.xml": ManualDefinedActivity}
            for file_name in class_dict.keys():
                if file_name in files:
                    shutil.rmtree(os.path.join(activity_folder, "activity_auxiliary_folder"))
                    activity = class_dict[file_name].import_from_file(activity_file)
                    self.xml_mapper.save_activity(activity)
                    self.refresh_activities()
                    break
        except OSError:
            raise TarFileNotValid()

    def get_nearby_devices(self):
        devices = []
        if self.conf.bluetoothSupport == "Yes":
            self.logger.debug("Searching for Bluetooth devices")
            devices += BTDevice.find()
        if self.conf.antSupport == "Yes":
            self.logger.debug("Searching for ANT+ Devices")
            devices += ANTDevice.find()
        return devices

    def run_test(self, notify_window, name, mac, dev_type):
        if dev_type == "BT" and name == "Polar iWL":
            device = PolariWL(mac)
            print "Mac: {}".format(mac)
        elif dev_type == "ANT+":
            device = ANTDevice()
        device.connect()
        self.test_thread = device.run_test(notify_window)
        self.testing_device = device

    def end_device_test(self):
        if self.testing_device:
            self.testing_device.finish_test()
        if self.test_thread.is_alive():
            self.test_thread.join()
        if self.testing_device:
            self.testing_device.disconnect()
            self.testing_device = None

    @staticmethod
    def get_supported_devices():
        return ["Polar iWL", "ANT+ HR Band"]

    def is_demo_mode(self):
        return self.conf.defaultMode == "Demo mode"

    def begin_acquisition(self, file_path, activity_id, mode, dev_name, dev_type, dev_dir=None):
        from config import RECENT_ACQUISITIONS_COUNT
        self.acquisition_path = file_path
        writer = TextWriter(file_path + ".tag.txt", file_path + ".rr.txt")
        if mode == DEMO_MODE:
            device = DemoBand()
            activity = self.xml_mapper.get_activity(activity_id)
            ad = AcquisitionFacade(activity, device, writer)
            ad.start()
        elif mode == DEVICE_CONNECTED_MODE:
            if dev_type == "BT" and dev_name == "Polar iWL":
                device = PolariWL(dev_dir)
                activity = self.xml_mapper.get_activity(activity_id)
                ad = AcquisitionFacade(activity, device, writer)
                ad.start()
            elif dev_type == "ANT+" and dev_name == "ANT+ HR Band":
                device = ANTDevice()
                activity = self.xml_mapper.get_activity(activity_id)
                ad = AcquisitionFacade(activity, device, writer)
                ad.start()
        # Save recent acquisition
        while len(self.recent_acquisitions) >= RECENT_ACQUISITIONS_COUNT:
            del self.recent_acquisitions[-1]
        self.recent_acquisitions.insert(0, self.acquisition_path.encode('utf-8'))
        # Save recent acquisitions to file
        with open(RECENT_ACQUISITIONS_FILE, "w") as f:
            f.write("{}".format(os.linesep).join(self.recent_acquisitions))

    @run_in_thread
    def open_ghrv(self):
        """
        Show result data in gHRV application
        """
        rr_file = "{}.rr.txt".format(self.acquisition_path.encode('utf-8'))
        tag_file = "{}.tag.txt".format(self.acquisition_path.encode('utf-8'))
        os.system("/usr/bin/gHRV -loadBeatTXT {0} -loadEpTXT {1}".format(rr_file, tag_file))

    def plot_results(self):
        """
        Plots acquisition results in a new window
        """
        from utils import plot

        rr_file = "{}.rr.txt".format(self.acquisition_path.encode('utf-8'))
        tag_file = "{}.tag.txt".format(self.acquisition_path.encode('utf-8'))
        plot(rr_file, tag_file)

    def open_rr_file(self):
        rr_file = "{}.rr.txt".format(self.acquisition_path.encode('utf-8'))
        open_file(rr_file)

    def open_tag_file(self):
        tag_file = "{}.tag.txt".format(self.acquisition_path.encode('utf-8'))
        open_file(tag_file)
