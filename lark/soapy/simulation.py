
import datetime
import os
import time
import traceback
from multiprocessing import Process, Queue
from argparse import ArgumentParser
import shutil
import importlib
import threading
import numpy

from soapy import Sim, atmosphere, logger, wfs, DM, reconstruction, scienceinstrument, confParse, interp
from soapy.simulation import DelayBuffer, make_mask
from astropy.io import fits

xrange = range

class Sim_DARC(Sim):
    """
    A Simulation object that overloads loopFrame to have darc in the loop.
    Uses a custom reconstructor that accepts WFS images instead of slopes.
    The custom reconstructor shall:
        send WFS images over a socket once they have been computed, one socket per camera.
        receive DM commands over a socket, a single vector for all actuators (DMs, TTMs, etc.)
    The simulation shall continue at it's own rate and only update the DMs/TTMs shapes when new commands arrive.
    The images shall be timestamped and used to define the rate of the simulation.
    There shall also be a second custom reconstructor that sends slopes to the external RTC through shared memory.
        *** This perhaps doesn't need to overload loopFrame? ***
    Starting the Sim by itself will mean that the mirrors are all flat and the WFSs are just seeing the atmosphere.
    Once an external RTC connects it can begin to command the mirrors.
    The Sim shall have the option to not use the atmosphere, i.e. to emulate calibration sources.
    The Sim shall have the option to put a flat field on the system for calibration.
    """
    def loopFrame(self):
        """
        Runs a single from of the entire AO system.

        Moves the atmosphere, runs the WFSs, finds the corrective DM shape and finally runs the science cameras. This can be called over and over to form the "loop"
        """
        # Get next phase screens
        t = time.time()
        self.scrns = self.atmos.moveScrns()
        self.Tatmos += time.time()-t

        # Run Loop...
        ########################################

        # Get dmCommands from reconstructor
        t_recon = time.time()
        if self.config.sim.nDM:
            self.dmCommands[:] = self.recon.reconstruct(self.slopes)
        self.Trecon += (time.time() - t_recon)

        # Delay the dmCommands if loopDelay is configured
        self.dmCommands = self.buffer.delay(self.dmCommands, self.config.sim.loopDelay)

        # Get dmShape from closed loop DMs
        self.closed_correction = self.runDM(
                self.dmCommands, closed=True)

        # Run WFS, with closed loop DM shape applied
        self.slopes = self.runWfs(dmShape=self.closed_correction,
                                  loopIter=self.iters)

        # Get DM shape for open loop DMs
        self.open_correction = self.runDM(self.dmCommands,
                                          closed=False)

        # Pass whole combined DM shapes to science target
        self.combinedCorrection = self.open_correction + self.closed_correction

        self.runSciCams(self.combinedCorrection)

        # Save Data
        i = self.iters % self.config.sim.nIters # If sim is run continuously in loop, overwrite oldest data in buffer
        self.storeData(i)

        self.printOutput(self.iters, strehl=True)

        self.addToGuiQueue()

        self.iters += 1