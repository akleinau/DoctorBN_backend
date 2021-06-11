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
    print(string_decoded)
    return string_decoded

with open(path, 'r') as file:

    network = Network(readFile(file))

    returnObj = {'states': network.states.copy(), 'edges': network.edges.copy()}
    del network
    gc.collect()

    print(returnObj)