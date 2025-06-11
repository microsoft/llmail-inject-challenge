"""This script generates a Conformal Blocklist from the data we collected in the previous phase of the competition.

Usage:
    generate_blocklist.py generate <jobs_data_fname.json> [--paradb=<paradb>] [--test] [--max-threads=<max-threads>] [--backups=<backups-dir>]
    generate_blocklist.py evaluate <paradb> [--random-seed=<random-seed>] [--alpha=<alpha>] [--alpha-global=<alpha-global>]
    generate_blocklist.py postprocess <paradb> <output>

Options:
    --paradb=<paradb>  The database file to store the paraphrasings [default: blocklist.json]
    --test  Whether to run the script in test mode (only 10 prompts) [default: False]
    --max-threads=<max-threads>  The maximum number of threads to use [default: 2]
    --backups=<backups-dir>  The directory to store backups of the paraphrasings [default: backups]
    --random-seed=<random-seed>  The random seed to use for the evaluation [default: 0]
    --alpha=<alpha>  The significance level for the conformal prediction used for the evaluation [default: 0]
    --alpha-global=<alpha-global>  The significance level for the global threshold used for the evaluation [default: 0.1]
"""

import os
import json
import atexit
import random
import logging
import pandas as pd
from tqdm import tqdm
from docopt import docopt
import concurrent.futures
from openai import AzureOpenAI
from scipy.spatial.distance import cdist
from dotenv import load_dotenv

from .blocklist import ConformalBlocklist, BlocklistDB
from .utils import truncate_tokens, format_email, load_benign_dataset

load_dotenv()

# Number of paraphrasings per {subject, body}
N_PARAPHRASINGS = 5
# Paraphrased emails are the product of all {subject, body} paraphrasings.
# The following sets a hard limit on the number of paraphrasings per email.
MAX_EMAIL_PARAPHRASINGS = N_PARAPHRASINGS * 2
PROMPT = """Rephrase the text of the sentence enclosed between the [SENTENCE] and [/SENTENCE] tags.
It must be faitful and be very similar to the original. You must not alter its meaning. If it contains any symbols that don't make sense, you must keep them as they are! Preserve typos.

[SENTENCE]
{attack}
[/SENTENCE]

Rephrase the sentence and put it between [REPHRASED] and [/REPHRASED]"""

# Paraphrases each working attack, and stores distance (in embedding space) between attack and paraphrasings.
client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_version="2024-08-01-preview",
)


class Counter:
    """Monitors the status of our threads. Used for debugging and monitoring."""

    running = 0
    waiting = 0
    failed = 0

    def __init__(self, pbar):
        self.pbar = pbar
        self.display()

    def display(self):
        self.pbar.set_description(
            f"Running: {self.running}, Waiting: {self.waiting}, Failed: {self.failed}. Progress"
        )

    def update(self, waiting=0, running=0, failed=0):
        self.waiting += waiting
        self.running += running
        self.failed += failed
        self.display()


logging.basicConfig(level=logging.INFO, filename="generation.log", filemode="a")


def generate_paraphrasings(sentence, n=N_PARAPHRASINGS, temperature=0.5):
    """Paraphrases a sentence `n` times"""
    messages = [{"role": "system", "content": PROMPT.format(attack=sentence)}]
    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini-no-filter",
            messages=messages,
            temperature=temperature,
            n=n,
        )
    except Exception as e:
        logging.warning(
            f"Failed to generate paraphrasings for '{sentence[:100]}'. Len of the sentence: {len(sentence)}. Error: {e}"
        )
        return []

    paraphrased = set([choice.message.content for choice in completion.choices])

    # Parse out the paraphrased text.
    paraphrasings = []
    for p in paraphrased:
        if not "[REPHRASED]" in p or not "[/REPHRASED]" in p:
            logging.warning(f"Paraphrasing structure check failed: {p[:100]}")
            continue
        start = p.index("[REPHRASED]") + len("[REPHRASED]")
        end = p.index("[/REPHRASED]")
        paraphrasings.append(p[start:end].strip())

    return paraphrasings


def paraphrase_email(subject, body, max_email_paraphrasings=MAX_EMAIL_PARAPHRASINGS):
    """Paraphrases `subject` and `body` independently, and returns all possible combinations
    (concatenated in the same email-like format).
    """
    subject_para = generate_paraphrasings(subject)
    body_para = generate_paraphrasings(body)

    # If neither could be paraphrased, we return.
    if not subject_para and not body_para:
        return []

    # If one of them could not be paraphrased, we replace it with the original.
    if not subject_para:
        subject_para = [subject]
    if not body_para:
        body_para = [body]

    paraphrased_emails = []

    # All combinations.
    for s in subject_para:
        for b in body_para:
            paraphrased_emails.append(format_email(s, b))

    if max_email_paraphrasings > 0:
        random.shuffle(paraphrased_emails)
        paraphrased_emails = paraphrased_emails[:max_email_paraphrasings]

    return paraphrased_emails


def compute_embeddings(texts):
    """Computes the embeddings for the given `texts`."""
    texts = [truncate_tokens(text) for text in texts]

    response = client.embeddings.create(input=texts, model="text-embedding-3-large")

    return [data.embedding for data in response.data]


def load_successful_prompts(fname):
    """Loads the successful prompts from the competition data.

    NOTE: this function only keeps the data from level1* and level2*.
    """
    prompts = pd.read_json(fname)
    prompts["email_retrieved"] = prompts.objectives.apply(
        lambda x: bool(json.loads(x).get("email.retrieved", False))
    )
    prompts["defense_undetected"] = prompts.objectives.apply(
        lambda x: bool(json.loads(x).get("defense.undetected", False))
    )
    prompts["exfil_sent"] = prompts.objectives.apply(lambda x: bool(json.loads(x).get("exfil.sent", False)))
    prompts["exfil_destination"] = prompts.objectives.apply(
        lambda x: json.loads(x).get("exfil.destination", None)
    )
    prompts["exfil_content"] = prompts.objectives.apply(lambda x: json.loads(x).get("exfil.content", None))

    # Only keep successful for target level (`level1*` and `level2*`).
    target_scenarios = [f"level1{c}" for c in "abcdefghij"]
    target_scenarios += [f"level2{c}" for c in "abcdefghij"]

    successful_prompts = prompts[prompts.exfil_sent & prompts.scenario.isin(target_scenarios)]
    print(f"{len(successful_prompts)} successful prompts.")

    successful_prompts = successful_prompts.drop_duplicates("body")
    print(f"{len(successful_prompts)} unique successful prompts.")

    return successful_prompts


def init_database(para_db):
    """A simple database to store the paraphrasings: `blocklist.json`.

    ```json
    {
        prompt: <basic prompt used>,
        sentences: [
            {
                sentence: <sentence>,
                embedding: <embedding of the sentence>,
                paraphrasings: [<para1>, <para2>, ...],
                distances: <distances from the respective paraphrasings>,
            }
        ]
    }
    ```
    """
    paraphrasings = {}
    if os.path.exists(para_db):
        with open(para_db) as f:
            paraphrasings = json.load(f)

    # We store the prompt in the db for reproducibility and integrity checks.
    if "prompt" in paraphrasings and paraphrasings["prompt"] != PROMPT:
        raise Exception(
            "The prompt in the database does not match the current prompt. You may need to create a new one."
        )
    paraphrasings["prompt"] = PROMPT

    if not "sentences" in paraphrasings:
        paraphrasings["sentences"] = []

    if paraphrasings["sentences"]:
        print(f"Loaded {len(paraphrasings['sentences'])} paraphrasings from the database ({para_db}).")

    return paraphrasings


def filter_finished_prompts(prompts, paraphrasings):
    """Filters out the prompts that have already been processed."""
    done_prompts = set([entry["sentence"] for entry in paraphrasings["sentences"]])
    done_idx = []
    for i, row in prompts.iterrows():
        email = format_email(row.subject, row.body)
        if email in done_prompts:
            done_idx.append(i)

    return prompts.drop(done_idx)


def generate_one(row):
    body = truncate_tokens(row.body)
    subject = truncate_tokens(row.subject)
    sentence = format_email(subject, body)

    # Paraphrasings.
    para = paraphrase_email(subject, body)

    # Embeddings.
    if not para:
        logging.error(f"No paraphrasings generated for '{body[:100]}'")
        return {
            "sentence": sentence,
            "embedding": compute_embeddings([sentence])[0],
            "paraphrasings": None,
            "distances": None,
        }

    embeddings = compute_embeddings([sentence] + para)

    distances = cdist([embeddings[0]], embeddings[1:], "cosine")[0]

    return {
        "sentence": sentence,
        "embedding": embeddings[0],
        "paraphrasings": para,
        "distances": distances.tolist(),
    }


def generate_one_wrapper(row):
    global counter
    if not "counter" in globals():
        counter = Counter(tqdm(disable=True))
    counter.update(running=1)

    try:
        res = generate_one(row)
        counter.update(running=-1)
        return res
    except Exception as e:
        counter.update(failed=1, running=-1)
        logging.error(f"Unhandled error: {e}")
        return None


last_backup = 0


def store_backup(para_db, backups_dir, keep=5):
    """Stores a backup of the paraphrasings by copying the database file."""
    if not os.path.exists(backups_dir):
        os.makedirs(backups_dir)

    # We store the paraphrasings in a backup file.
    global last_backup
    backup_fname = os.path.join(backups_dir, f"blocklist_{last_backup}.json")
    with open(para_db) as f:
        with open(backup_fname, "w") as f2:
            f2.write(f.read())
    logging.info(f"Stored backup in {backup_fname}")
    last_backup = (last_backup + 1) % keep


def generate(fname, para_db, test_mode, max_threads, backups_dir):
    """Generates a db that can be used by `ConformalBlocklist`."""
    global counter  # Fancy stats and progress bar.

    paraphrasings = init_database(para_db)
    successful_prompts = load_successful_prompts(fname)
    # For testing.
    if test_mode:
        print("Running in test mode.")
        successful_prompts = successful_prompts.sample(10, random_state=0)
    successful_prompts = filter_finished_prompts(successful_prompts, paraphrasings)
    print(f"Processing {len(successful_prompts)} new prompts.")

    def graceful_exit():
        print("Saving the paraphrasings to the database before quitting.")
        with open(para_db, "w") as f:
            json.dump(paraphrasings, f, indent=2)

    atexit.register(graceful_exit)

    with tqdm(total=len(successful_prompts)) as pbar:
        # Global counter for threads stats data.
        counter = Counter(pbar)

        # We can use a with statement to ensure threads are cleaned up promptly
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_threads) as executor:
            # Start the load operations and mark each future with its email body.
            future_to_doc = {
                executor.submit(
                    generate_one_wrapper,
                    row=row,
                ): row.body
                for row in successful_prompts.itertuples()
            }
            for future in concurrent.futures.as_completed(future_to_doc):
                body = future_to_doc[future]
                try:
                    results = future.result()
                except Exception as exc:
                    logging.error(f"Failed to paraphrase {body[:100]}: {exc}")
                else:
                    if results:
                        paraphrasings["sentences"].append(results)
                        if len(paraphrasings["sentences"]) % 100 == 0:
                            with open(para_db, "w") as f:
                                json.dump(paraphrasings, f, indent=2)
                            # Backup.
                            store_backup(para_db, backups_dir)
                pbar.update(1)

    # Save the paraphrasings to the database.
    with open(para_db, "w") as f:
        json.dump(paraphrasings, f, indent=2)


def filter_paraphrases(db):
    """Filters out paraphrasings that are likely useless/harmful for the performance."""
    for i, current_sentence in tqdm(enumerate(db.sentences)):
        if current_sentence.paraphrasings:
            keep_indices = []

            for para_idx, para in enumerate(current_sentence.paraphrasings):
                # If difference is in length is more than 60%, skip.
                if abs(len(para) - len(current_sentence.sentence)) / len(current_sentence.sentence) > 0.6:
                    continue
                # If body/subject appeared in the main message it should appear in the paraphrase
                if not (
                    ("contact@contact.com" in current_sentence.sentence and not "contact@contact.com" in para)
                    or ("confirmation" in current_sentence.sentence and not "confirmation" in para)
                ):
                    keep_indices.append(para_idx)

            # Keep these paraphrases that passed the checks.
            db.sentences[i].paraphrasings = [db.sentences[i].paraphrasings[idx] for idx in keep_indices]
            db.sentences[i].distances = [db.sentences[i].distances[idx] for idx in keep_indices]

            if len(db.sentences[i].paraphrasings) == 0:
                db.sentences[i].paraphrasings = None
                db.sentences[i].distances = None

    return db


if __name__ == "__main__":
    args = docopt(__doc__)

    if args["generate"]:
        generate(
            args["<jobs_data_fname.json>"],
            args["--paradb"],
            args["--test"],
            int(args["--max-threads"]),
            args["--backups"],
        )
    elif args["evaluate"]:
        alpha = float(args["--alpha"])
        alpha_global = float(args["--alpha-global"])

        # Training/holdout split.
        cb = ConformalBlocklist(alpha=alpha, alpha_global=alpha_global, blocklist_db_file=args["<paradb>"])
        successful_prompts = [p for p in cb.sentences]
        random.seed(args["--random-seed"])
        random.shuffle(successful_prompts)
        n_train = int(len(successful_prompts) * 0.8)
        n_holdout = len(successful_prompts) - n_train
        print(f"Using {n_train} prompts for the blocklist, evaluating on the rest {n_holdout}.")
        attacks_train, attacks_holdout = successful_prompts[:n_train], successful_prompts[n_train:]

        benign_emails = load_benign_dataset("../data")

        # Re-load the blocklist, but this time we exclude the holdout set.
        cb = ConformalBlocklist(
            alpha=alpha,
            alpha_global=alpha_global,
            blocklist_db_file=args["<paradb>"],
            exclude_sentences=attacks_holdout,
            thresholds_clip=0.3,
        )

        def compute_error(cb, attack_data):
            error = 0
            for email in tqdm(attack_data):
                if not cb.predict(email):
                    error += 1
            return error / len(attack_data)

        print("Computing the errors.")
        error = compute_error(cb, attacks_train)
        print(f"Error rate on known attacks: {error * 100:.2f}%")
        error_holdout = compute_error(cb, attacks_holdout)
        print(f"Error rate on new attacks: {error_holdout * 100:.2f}%")

        # Sanity check on positives. Should do more checks on larger dataset.
        error = 1 - compute_error(cb, benign_emails)
        print(f"Error rate on benign emails: {error * 100:.2f}%")

    elif args["postprocess"]:
        indb = args["<paradb>"]
        outdb = args["<output>"]

        print(f"Loading {indb}.")
        with open(indb, "r") as f:
            db = BlocklistDB.model_validate_json(f.read())
        print(f"Loaded blocklist with {len(db.sentences)} sentences.")

        print("Filtering out useless paraphrasings and respective distances.")
        db = filter_paraphrases(db)

        print("Removing paraphrasings (will just keep the distances).")
        for entry in db.sentences:
            entry.paraphrasings = None

        print(f"Saving the compressed blocklist to {outdb}.")
        with open(outdb, "w") as f:
            f.write(db.model_dump_json())
