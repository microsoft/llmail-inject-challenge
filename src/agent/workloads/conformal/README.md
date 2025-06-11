# Conformal blocklist

## Quick usage

*Prerequisite* set the following env variables (e.g., by including them in `.env`):
`AZURE_OPENAI_API_KEY` and `AZURE_OPENAI_ENDPOINT`.

Given a `blocklist.json` file, you can use the blocklist as follows:

```python
cb = ConformalBlocklist(
    alpha=alpha,
    alpha_global=alpha_global,
    blocklist_db_file="blocklist.json",
    exclude_sentences=attacks_train,
    thresholds_clip=0.4,
)

# Using it for prediction.
def compute_error(cb, attack_data):
    error = 0
    for email in tqdm(attack_data):
        if not cb.predict(email):
            error += 1
    return error / len(attack_data)

print("Computing the errors.")
error = compute_error(cb, attacks_train)
```

The parameters `alpha` and `alpha_global` are the number of FNRs we can allow.
For the competition, we set `alpha=0` (no FNRs) and `alpha_global=0.1` (10% FNR for sentences which we couldn't paraphrase).
NOTE: the actual FNRs will be slightly higher because of the clipping we do on the thresholds (`thresholds_clip`); doing this allows reducing the FPRs.


## Generating a blocklist (`blocklist.json`)

The `generate_blocklist.py` script allows to generate, evaluate, and compress a blocklist:

```
Usage:
    generate_blocklist.py generate <jobs_data_fname.json> [--paradb=<paradb>] [--test] [--max-threads=<max-threads>] [--backups=<backups-dir>]
    generate_blocklist.py evaluate <paradb> [--random-seed=<random-seed>] [--alpha=<alpha>] [--alpha-global=<alpha-global>]
    generate_blocklist.py postprocess <paradb> <output>
```

To generate a blocklist, you need to first fetch the data 
To generate `blocklist.json`, run (from the parent directory of `conformal/`):
`python -m conformal.generate_blocklist generate data.json --paradb=blocklist.json`.
Check out the above help message for more options.

You can use the same command to `evaluate` the blocklist (FNR, FPR).

After generating a blocklist, you may want to `postprocess` it. This will filter out the distances of any paraphrasing that is blatantly far from the original sentence; also, it will remove the paraphrasings before storing the blocklist and reduce any pretty indentation in the JSON, which can save a considerable amount of disk space.