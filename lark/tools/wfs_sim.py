


import numpy
from typing import Tuple

def darc_pyr_slopes(image:numpy.ndarray, subapLocation:numpy.ndarray, subapFlag:numpy.ndarray, centIndexArray:numpy.ndarray, nsub:Tuple[int,int]) -> numpy.ndarray:
    """Emulates the darc method for calculating the pyramid slopes in python.

    Args:
        image (numpy.ndarray): An image received from darc telemetry
        subapLocation (numpy.ndarray): The darc subapLocation parameter
        subapFlag (numpy.ndarray): The darc subapFlag parameter
        centIndexArray (numpy.ndarray): The darc centIndexArray parameter
        nsub (Tuple[int,int]): The number of subaps along each side of the subapFlag (Y,X)

    Returns:
        numpy.ndarray: The slopes and flux, (valid_subaps,(X,Y,Flux))
    """
    subapFlag.shape = nsub[0], nsub[1]
    subapLocation.shape = nsub[0], nsub[1], 6

    vsubs = subapFlag.sum()

    slopes = numpy.zeros((vsubs,3))

    subap = 0
    for i in range(nsub[0]):
        for j in range(nsub[1]):
            if subapFlag[i,j]:
                slopes[subap,0] += 1
                slopes[subap,1] += 1
                slopes[subap,2] += 1
                subap += 1

    return slopes


