from evolver.level0.dsl.execution import GatesConfig, Experiment
from evolver.level0.evaluating_prompt import evaluate
from evolver.level0.proposing_prompt import propose
from investigation_prompt import investigate

# Consider axiom declarations as non-negotiable basis
axioms: dict = "{AXIOMS}"
tracing_packages: dict[str, list[str]] = "{TRACING_PACKAGES}"


def main(iteration_id: str, investigation_area: str, acceptance_gates: GatesConfig, best: Experiment) -> Experiment:
    """ Main loop flow.
    iteration_id: str - session id for tracing and other correlation purpose
    acceptance_gates: GatesConfig - immutable stable gates as acceptance criteria.
    investigation_area: str - problem area of investigation
    best: Experiment - Best result from previous session

    :return: Experiment
    """

    # Step 1: Investigate the code in the projects scope based on area to produce suspicion classes candidates.
    code_evidence = investigate(investigation_area, tracing_packages)

    # Set loop parameters
    max_rounds = int("{MAX_ROUNDS}")
    round_index = 1
    is_ready = False
    experiments = [best]
    experiment = best
    while (not is_ready) and (round_index <= max_rounds):
        # Step 2: Propose candidate artifacts (mandatory is group_catalog with WHERE-suffix SQL) in addition:
        # - produce hypotheses and theory explanation with surrogate objects (db_manifest)
        # - create tracing plan to test hypotheses
        # - improve result (e.g., refine tracing plan, theory with surrogate objects, etc.) for next round based on experiments evidence
        proposal = propose(axioms, acceptance_gates, code_evidence, experiment, experiments)

        # Step 3: Evaluate proposal by evaluator, compute new best deterministically to produce scoring by wrapper
        experiment = evaluate(iteration_id, proposal, experiment)
        experiments.append(experiment)
        round_index += 1

        is_ready = experiment.decision.is_ready

    return experiment


main(iteration_id="{ITERATION_ID}",
     investigation_area="{INVESTIGATION_AREA}",
     acceptance_gates="{ACCEPTANCE_GATES}",
     best="{BEST_EXPERIMENT}")
