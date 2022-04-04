#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
from threading import *

class Idler(object):

    def __init__(self, oConnection, fnCallback, oLogger):

        self.oThread = Thread(target=self.idle)
        self.oConnection = oConnection
        self.oEvent = Event()
        self.fnCallback = fnCallback
        self.bNeedSync = False
        self.oLogger = oLogger
        self.bAborted = False

    def start(self):

        self.oThread.start()

    def stop(self):

        if self.oConnection.oImap is not None:
            try:
                # Send a NOOP command to interrupt the IDLE mode and free the blocked thread
                self.oConnection.oImap.noop()
            except:
                pass
        self.oEvent.set()

    def join(self):

        self.oThread.join()

    def idle(self):

        while True:

            if self.oEvent.isSet():
                break

            self.bNeedSync = False
            self.bAborted = False

            def callback(lstArgs):

                if (lstArgs[2] != None) and (lstArgs[2][0] is self.oConnection.oImap.abort):

                    self.oLogger.info('"{0}:{1}" has been closed by the server.'.format(self.oConnection.strLogin, self.oConnection.strFolder))
                    self.bAborted = True

                else:

                    self.bNeedSync = True

                # We may need to skip the condition
                # if not self.oEvent.isSet():
                self.oEvent.set()

            while not self.oConnection.isOpen():

                self.oLogger.info('"{0}:{1}" IDLE is waiting for a connection.'.format(self.oConnection.strLogin, self.oConnection.strFolder))
                time.sleep(10)

            self.oConnection.oImap.idle(callback=callback, timeout=600)
            self.oEvent.wait()

            if self.bNeedSync:

                self.oEvent.clear()
                self.fnCallback(self.oConnection, False)

        try:

            if self.oConnection.oImap != None:
                self.oConnection.oImap.noop()

        except:

            pass

        if self.bAborted:
            self.fnCallback(self.oConnection, True)
