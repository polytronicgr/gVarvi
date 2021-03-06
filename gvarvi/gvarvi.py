# coding=utf-8

import os
from shutil import copyfile
import wx
import sys
import traceback

from config import CONF_DIR, DEFAULT_CONF_FILE, DEFAULT_ACTIV_FILE, CONF_FILE, ACTIV_FILE, LOG_FILE, \
    RECENT_ACQUISITIONS_FILE
from logger import Logger





# Creating necessary files and dirs if not exist
if not os.path.isdir(CONF_DIR):
    os.mkdir(CONF_DIR)
if not os.path.isfile(CONF_FILE):
    copyfile(DEFAULT_CONF_FILE, CONF_FILE)
if not os.path.isfile(ACTIV_FILE):
    copyfile(DEFAULT_ACTIV_FILE, ACTIV_FILE)
if not os.path.isfile(LOG_FILE):
    open(LOG_FILE, 'a').close()
if not os.path.isfile(RECENT_ACQUISITIONS_FILE):
    open(RECENT_ACQUISITIONS_FILE, 'a').close()

from facade.MainFacade import MainFacade
# Application logger initialization
logger = Logger()
main_facade = MainFacade(ACTIV_FILE, CONF_FILE)
conf = main_facade.parse_config_file()
if conf.remoteDebugger == "Yes":
    logger.activate_datagram_logging(conf.rdIP, int(conf.rdPort))

from utils import set_language
set_language(conf.language)


class GVarviApp(wx.App):
    def OnInit(self):
        def exception_hook(exc_type, value, trace):
            """
            Handler for all unhandled exceptions
            @param exc_type: Exception type
            @param value: Error value
            @param trace: Trace back info
            """

            # Format the traceback
            exc = traceback.format_exception(exc_type, value, trace)
            ftrace = "".join(exc)
            app = wx.GetApp()
            if app:
                msg = "An unexpected error has ocurred: {0}".format(ftrace)
                logger.exception(msg)
            else:
                sys.stderr.write(ftrace)

        if conf.checkForUpdatesOnStart == "Yes":
            self.check_for_update()
        logger.debug("Starting app")
        sys.excepthook = exception_hook

        return True

    @staticmethod
    def check_for_update():
        """
        Check if there is a new version of gVARVI available at GitHub repositories
        """
        from config import VERSION

        import urllib2
        import subprocess

        sys_plat = sys.platform

        try:
            data = urllib2.urlopen("https://github.com/milegroup/gVarvi/raw"
                                   "/develop/dist/lastversion.txt")
            last_version = data.read()
            if last_version > VERSION:
                from view.wxutils import ConfirmDialog
                message = "New version of gVARVI ({}) is available for download\n".format(last_version)
                if sys_plat == 'linux2':
                    message += "Do you want to download it?"
                elif sys_plat == "win32" or sys_plat == "darwin":
                    message += "Do you want to open gVARVI repositories webpage?"

                result = ConfirmDialog(message, "New version available").get_result()
                if result == wx.ID_YES:
                    if sys_plat == 'linux2':
                        deb_url = "https://github.com/milegroup/gVarvi/blob" \
                                  "/develop/dist/gvarvi-{0}.deb?raw=true".format(
                            last_version)
                        deb_data = urllib2.urlopen(deb_url)
                        from tempfile import gettempdir
                        with open(os.path.join(gettempdir(), "gvarvi_last.deb"), "wb") as f:
                            f.write(deb_data.read())
                            subprocess.call(["xdg-open", f.name])
                        sys.exit(0)
                    elif sys_plat == "win32" or sys_plat == "darwin":
                        import webbrowser
                        webbrowser.open('https://github.com/milegroup/gVarvi')

            elif last_version == VERSION:
                logger.debug("Last version of gVARVI ({}) is already installed".format(VERSION))
        except urllib2.HTTPError as e:
            logger.info(e.message)
        except urllib2.URLError as e:
            logger.info(e.message)


# Application initialization
from view.MainWindow import MainWindow
app = GVarviApp()
frame = MainWindow("gVARVI", main_facade)
frame.Show()
app.MainLoop()
