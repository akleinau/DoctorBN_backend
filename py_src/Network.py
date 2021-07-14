from pgmpy.readwrite import NETReader
import gc

class Network:

    #reads the model in NET format
    def __init__(self, name):
        reader = NETReader(string=name, n_jobs=1)
        self.model = reader.get_model()
        self.states = reader.state_names
        self.edges = reader.edge_list
        self.labels = reader.labels

