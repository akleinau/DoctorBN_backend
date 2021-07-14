from pgmpy.readwrite import NETReader
import gc

class Network:

    #reads the model in BIF format
    def __init__(self, name):
        reader = NETReader(string=name, n_jobs=1)
        self.model = reader.get_model()
        self.states = reader.get_states()
        self.edges = reader.variable_edges

