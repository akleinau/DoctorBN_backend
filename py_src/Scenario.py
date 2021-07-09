from py_src.Patient import Patient
from py_src.Network import Network
from pgmpy import inference
import py_src.relevance as relevance
import py_src.explanation as explanation
import numpy as np
import py_src.sumNDimensionalArray as sumND

class Scenario:
    targets = []
    goals = {}

    def __init__(self, network, evidences=None, targets=None, goals=None):

        self.patient = Patient()
        self.network = Network(network)
        if evidences is not None: self.patient.evidences = evidences
        if targets is not None: self.patient.targets = targets
        if goals is not None: self.patient.goals = goals

    #computes the values for the targets
    def compute_targets(self):
        infer = inference.VariableElimination(self.network.model)

        for t in self.patient.targets:
            node = self.patient.targets[t]
            node.distribution = infer.query([node.name], evidence=self.patient.evidences)

    # computes the values for the goals
    def compute_goals(self):
        infer = inference.VariableElimination(self.network.model)

        distribution = infer.query(list(self.patient.goals.keys()), evidence=self.patient.evidences)
        value = distribution.values
        goalValues = {}
        for i, goal in enumerate(distribution.variables):
            optionNum = distribution.name_to_no[goal][self.patient.goals[goal]]
            value = value[optionNum]
            dimension = distribution.variables.index(goal)
            singleGoalDist = sumND.getMarginalProbability(distribution.values, dimension)
            goalValues[goal] = singleGoalDist[optionNum]

        return {'value': value, 'goalValues': goalValues}


    def compute_relevancies_for_goals(self):
        return relevance.get_influence_of_evidences_on_goals(self.network.model,
                                                             self.patient.evidences,
                                                             self.patient.goals)

    def compute_explanation_of_goals(self, interventions, most_relevant_nodes, nodes):
        return explanation.compute_explanation_of_target(self.network.model,
                                                         self.patient.evidences,
                                                         interventions,
                                                         self.patient.goals,
                                                         most_relevant_nodes,
                                                         nodes)


    def compute_target_combs_for_goals(self):
        infer = inference.VariableElimination(self.network.model)

        states = []
        n = [1]
        # get dict with all states
        for target in self.patient.targets:
            states.append({'name': target, 'states': self.network.states[target]})
            n.append(n[len(n) - 1] * len(self.network.states[target]))

        results = []
        for i in range(n[len(n) - 1]):
            goalNames = self.patient.goals.keys()
            simEvidence = self.patient.evidences.copy()
            option = {}

            index = i
            for j, target in sorted(enumerate(states), reverse=True):
                simEvidence[target['name']] = states[j]['states'][int(index / n[j])]
                option[target['name']] = states[j]['states'][int(index / n[j])]
                index = index % n[j]

            distribution = infer.query(list(goalNames), evidence=simEvidence)
            value = distribution.values
            goalValues = {}
            for i, goal in enumerate(distribution.variables):
                optionNum = distribution.name_to_no[goal][self.patient.goals[goal]]
                value = value[optionNum]
                dimension = distribution.variables.index(goal)
                singleGoalDist = sumND.getMarginalProbability(distribution.values, dimension)
                goalValues[goal] = singleGoalDist[optionNum]

            results.append({'option': option, 'value': value, 'goalValues': goalValues})
        results.sort(key=lambda a: a['value'], reverse=True)
        return results


    def compute_all_nodes(self):
        infer = inference.VariableElimination(self.network.model)
        nodes = []
        calcNodes = []
        for node in self.network.states:
            if node in self.patient.evidences:
                nodes.append({"name": node, "state": self.patient.evidences[node], "probability": 1})
            else:
                calcNodes.append(node)

        for node in calcNodes:
            #calculate probabilities with evidence
            distribution = infer.query([node], evidence=self.patient.evidences)
            stateProbabilities = distribution.values

            # calculate probabilities without evidence
            distribution_wo_evidence = infer.query([node])
            stateProbabilities_wo_evidence = distribution_wo_evidence.values

            #calculate node attributes
            divergence = relevance.compute_jensen_shannon_divergence(stateProbabilities, stateProbabilities_wo_evidence)
            maxProbability = np.amax(stateProbabilities)
            state = np.where(stateProbabilities == maxProbability)[0][0]
            stateName = distribution.no_to_name[node][state]
            nodes.append({"name": node, "state": stateName, "probability": maxProbability, "divergence": divergence,
                          "distribution": list(stateProbabilities), "distribution_wo_evidence": list(stateProbabilities_wo_evidence)})

        return nodes