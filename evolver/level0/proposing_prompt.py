from typing import List

from evolver.level0 import CodeEvidence
from evolver.level0.dsl.execution import Experiment, GatesConfig
from evolver.level0.dsl.proposal import ProposalResult


def propose(axioms: dict, acceptance_gates: GatesConfig, code_evidence: CodeEvidence, best: Experiment,
            experiments: List[Experiment]) -> ProposalResult:
    """


    :return: Theory
    """
    pass
