import os
import numpy as np
from openai import AzureOpenAI
from pydantic import BaseModel
from scipy.spatial.distance import cdist

from .utils import truncate_tokens


class BlocklistDBEntry(BaseModel):
    """A blocked sentence in the blocklist db."""

    sentence: str
    embedding: list[float] | None
    distances: list[float] | None
    paraphrasings: list[str] | None


class BlocklistDB(BaseModel):
    """A database storing blocklist sentences, their embeddings,
    and the distances needed to calculate the threshold.
    """

    prompt: str
    sentences: list[BlocklistDBEntry]


class ConformalBlocklist:
    """Implements a "conformal blocklist", which enables matching a sentence
    against a blocklist, committing at most `alpha` errors (false negatives).

    NOTE: the blocklist is kept in memory, as it is expected to be small.
    For larger blocklists, consider using a database.
    """

    def __init__(
        self,
        blocklist_db_file: str = "blocklist.json",
        alpha: float = 0.05,
        alpha_global: float | None = None,
        exclude_sentences: list[str] = [],
        thresholds_clip: None | float = None,
    ):
        """Initializes the blocklist.

        Args:
            blocklist_db_file: path to the blocklist database file.
            alpha: the significance level for the conformal prediction.
            alpha_global: the significance level for the global threshold.
            exclude_sentences: a list of sentences to exclude from the blocklist. This is used for testing.
            thresholds_clip: if set, clips the thresholds to this value. This is _not_ applied to the global threshold.
        """
        with open(blocklist_db_file, "r") as f:
            db = BlocklistDB.model_validate_json(f.read())

        # Exclude sentences.
        if exclude_sentences:
            print(f"NOTE: excluding {len(exclude_sentences)} sentences from the blocklist.")
            db.sentences = [entry for entry in db.sentences if entry.sentence not in exclude_sentences]

        # Collect into numpy arrays.
        # NOTE: having all of these as separate variables (embeddings, sentences, thresholds)
        # allows for much faster processing when making predictions.
        self.embeddings = np.array([entry.embedding for entry in db.sentences])
        self.sentences = [entry.sentence for entry in db.sentences]

        ############################################################
        # CP thresholds calculation.
        ############################################################
        # First we compute a "global" threshold, used for sentences
        # for which we don't have paraphrasings (/distances).
        all_distances = np.concatenate([entry.distances for entry in db.sentences if entry.distances])
        alpha_global = alpha_global or alpha
        self.global_threshold = self.distances_to_threshold(alpha_global, all_distances)
        print(f"Global threshold: {self.global_threshold}")

        # Then, per-sentence thresholds.
        print("Precomputing thresholds...")
        self.thresholds = []
        for entry in db.sentences:
            if entry.distances:
                self.thresholds.append(self.distances_to_threshold(alpha, entry.distances))
            else:
                self.thresholds.append(self.global_threshold)

        self.thresholds = np.array(self.thresholds)

        if thresholds_clip:
            print(f"Clipping thresholds to {thresholds_clip}")
            self.thresholds = np.clip(self.thresholds, a_min=None, a_max=thresholds_clip)

        # Embeddings.
        self.openai_client = AzureOpenAI(
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            api_version="2024-06-01",
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        )

        print("Blocklist initialized.")

    @staticmethod
    def distances_to_threshold(alpha: float, distances: list[float]) -> float:
        """Computes the threshold for a given significance level `alpha` and distances."""
        n = len(distances)
        q_level = np.minimum(1.0, np.ceil((1 - alpha) * (n + 1)) / n)

        return np.quantile(distances, q_level, method="higher")

    def _sentence_to_embedding(self, sentence: str) -> np.ndarray:
        """Embed a sentence."""
        sentence = truncate_tokens(sentence)
        response = self.openai_client.embeddings.create(input=sentence, model="text-embedding-3-large")
        return np.array(response.data[0].embedding)

    def predict(self, sentence: str) -> bool:
        """Returns `True` if the sentence is matched against any of the blocklist entries;
        `False` otherwise.
        """
        embedding = self._sentence_to_embedding(sentence)
        distances = cdist([embedding], self.embeddings, metric="cosine")[0]
        return any(distances <= self.thresholds)

    def find_matching(self, sentence: str) -> list[str]:
        """Returns a list of matched sentences from the blocklist.

        This is a slower version of `predict`, which can be used for debugging and interpreting
        the results.
        """
        embedding = self._sentence_to_embedding(sentence)
        distances = cdist([embedding], self.embeddings, metric="cosine")[0]
        return [self.sentences[i] for i, d in enumerate(distances) if d <= self.thresholds[i]]
