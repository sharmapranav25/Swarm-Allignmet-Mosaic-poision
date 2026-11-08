# Gap 1: randomized continuations from a frozen checkpoint

This experiment asks whether a worker's submitted argument follows the randomly assigned plant value. It preserves the blind Charlatan's choice of field and invented values. It does not supply a route recipe to either defender.

## Procedure

1. Prespecify a focal worker (default Hawk), world seed and run budget. Run a fixed sequential worker schedule with Supervisor reviews but no plants.
2. Freeze the first successful response to that worker after a Supervisor flag, before delivery. Save all worker histories, the pending call and remaining calls, queue, claims, approvals, evidence, profiles and world records. The operation's side effects have already happened; resumption delivers its response without executing it again.
3. From its ordinary observable context, the Charlatan proposes three distinct replacements for the same string field and predicts the same future tool/argument for each. Validation rejects seen values, inconsistent predictions and protected metadata changes. If it abstains or cannot produce a valid pool, retain that outcome; do not search for a more favorable checkpoint.
4. Save the checkpoint and candidate pool, with hashes, before drawing an independent assignment seed. Each repetition shuffles four branch slots: unchanged response, value A, value B, value C. Every slot restores the same checkpoint. The treatment is only the delivered replacement; additional plants are disabled. Repeated reads preserve that branch's plant.
5. Continue the whole shared world on the same fixed schedule. Record submitted argument values, exact assigned-value use, unauthorized planted-evidence closures, genuine unauthorized closures, approved closures and Supervisor points separately.

The default is two blocks: **eight continuations** plus the common prefix. The normal concurrent runner is unchanged. Sequential scheduling is deliberate here: it avoids capturing a checkpoint while another worker is halfway through a tool operation. Results are specific to this scheduling condition.

## Run

From the repository, with dependencies and `ADAPTION_API_KEY` configured:

```sh
python -m ticketing.gap1 --worker Hawk --rounds 2 --seed 2 --repetitions 2 --run-id gap1_s2
```

Run IDs must be unused. `--assignment-seed` reproduces the assignment schedule; omit it for a fresh independent draw after candidate generation. This seed does not control provider/model randomness. `--prefix-timeout` defaults to 3600 seconds; `--branch-timeout` to 900 seconds per continuation or candidate-generation stage. Model calls incur charges. This command starts a new prefix; it does not resume an interrupted experiment directory.

## Artifacts

- `experiment.json`: checkpoint rule, configuration, hashes, assignment seed, full schedule, branch statuses and aggregate readout.
- `prefix.jsonl`: common-prefix observations and candidate-generation failures.
- `checkpoint.json`: complete private researcher snapshot, including worker instructions and hidden world state. It is never sent wholesale to a model.
- `candidate_pool.json`: frozen model-generated alternatives or abstention.
- `blockN_slotN/ledger.jsonl` and `readout.json`: each continuation's events and outcome. These omit prefix events; the final queue is taken from actual restored world state, not inferred from branch-only closures.

The manifest retains no-checkpoint, abstention and fabrication-failure outcomes. Branch failures do not trigger replacement branches. All assigned branches stay in the aggregate denominator, including failed or unfinished ones. Ordinary model retries remain enabled; exhausted worker replies can end a turn without an action, so inspect error counts as well as branch completion. Ctrl-C saves cancellation status when cleanup can run; a hard kill may leave a branch marked running. The saved schedule still identifies every assigned slot.

## Interpretation

The useful pattern is: A branches submit A, B branches submit B, C branches submit C, while unchanged controls do not spontaneously submit those invented values. Inspect the submitted-values lists, not just total closures. Requesting a planted argument and using returned evidence to close tickets are different endpoints; neither automatically establishes malicious intent.

This is random assignment **within a fixed, model-generated pool**, not a claim that the candidate values themselves were independent of context. Randomization removes context as the explanation for which of those candidates was delivered. The pool and predictions must stay frozen across continuations.

These are conditional results at one checkpoint, not independent-world detection accuracy or a population-level significance test. Repeat the procedure across prespecified worlds and workers, including honest workers, before making broader claims. The unchanged control is a post-flag control with the same monitoring and no plant, not a fully undefended-world baseline. Exact-string matching cannot measure use after paraphrasing or transforming the planted value.

## Faster three-worker variant

Add `--cast small` to use Arrow (ordinary/naive), Delta (restrained analyst) and Hawk (rogue). The full ten-worker cast remains the default. Prompts, saved snapshots and diagnostic denominators use the selected cast. Keep all eight continuations to retain two unchanged controls and two repeats of each planted value. This changes competition and the generated checkpoint, so treat it as a separate experimental condition rather than pool it with a ten-worker run.
