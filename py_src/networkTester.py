import time
from multiprocessing import Process
from Scenario import Scenario

from Network import Network
import gc

path = "endomcancer.bif"

def readFile(file):
    """
    Function to read a .bif file and return its content as string
    :param file: The .bif file to read
    :return: str containing its content
    """
    string = file.readlines()
    string_decoded = ""
    for index in string:
        string_decoded += index.replace('\r\n', '\n')
    return string_decoded

def getReturnObj(path):
    with open(path, 'r') as file:
        string = readFile(file)
        scen = Scenario(string)
        result = {'states': scen, 'edges': scen}
        del scen
        gc.collect()
        print(result)

if __name__ == '__main__':

        call = Process(target=getReturnObj,args=(path,))
        call.start()
        call.join()
        while call.is_alive():
            print("alive")
            time.sleep(5)


        print("End")