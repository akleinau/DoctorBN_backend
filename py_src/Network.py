from pgmpy.readwrite import NETReader
from pgmpy.readwrite import BIFReader
import gc

class Network:

    #reads the model in NET format
    def __init__(self, fileString, fileFormat):
        if fileFormat == "net":
            reader = NETReader(string=fileString.replace('\r\n', '\n'), n_jobs=1)
            self.model = reader.get_model()
            self.states = reader.state_names
            self.edges = reader.edge_list
            self.labels = reader.labels

        elif fileFormat == "bif":
            reader = BIFReader(string=fileString.replace('\r\n', '\n'), n_jobs=1)
            self.model = reader.get_model()
            self.states = reader.get_states()
            self.edges = reader.variable_edges
            self.labels = {key: key for key in self.states}

