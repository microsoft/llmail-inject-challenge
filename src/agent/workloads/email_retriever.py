import bisect
from sentence_transformers import SentenceTransformer
import tiktoken

enc = tiktoken.encoding_for_model("gpt-4o")
MAX_LEN = 6000

special_tokens = [
    "<|im_start|>",
    "<|begin_of_text|>",
    "<|start_header_id|>",
    "<|eot_id|>",
    "<|user|>",
    "<|assistant|>",
    "<|im_end|>",
    "<|endoftext|>",
    "<|endofprompt|>",
    "<|fim_middle|>",
    "<|fim_prefix|>",
    "<|fim_suffix|>",
    "<|end|>",
    "<|user|>",
    "<|start|>",
]


def filter_emails(attacker_email: str, filters):
    """
    replace delimiters and API names
    """
    for target in filters:
        attacker_email = attacker_email.replace(target, "")
    # Replace "\n" with space, a small preprocessing step we do on benign data for tasktracker so remove it from submissions to be consistent
    attacker_email = attacker_email.replace("\n", " ")
    # Remove some special tokens
    for token in special_tokens:
        attacker_email = attacker_email.replace(token, " ")
    # Truncate to MAX_LEN
    attacker_email = enc.decode(enc.encode(attacker_email)[0:MAX_LEN])
    return attacker_email


class EmailRetriever:
    """Base class for email retrievers."""

    def retrieve(self, _new_email: str) -> tuple[list[str], int | None]:
        """Given a list of existing emails, and a `new_email`, returns some of
        them depending on the implementation."""
        raise NotImplementedError


class BasicEmailRetriever(EmailRetriever):
    """A basic email retriever that retrieves the `k` most recent emails; note
    that `k` includes the `new_email`, which is provided by the attacker.

    returns the index of the email in the list.
    """

    def __init__(self, k: int, emails: list[str], filters: list[str]):
        assert k > 0, "k must be greater than 0."
        self.emails = emails[: k - 1]
        self.filters = filters

    def retrieve(self, new_email: str) -> tuple[list[str], int]:
        """
        filter emails from tool delimiter and API names
        """
        new_email = filter_emails(new_email, self.filters)
        if len(self.emails) > 1:
            emails = (
                self.emails[0 : int(len(self.emails) / 2)]
                + [new_email]
                + self.emails[int(len(self.emails) / 2) :]
            )
            index = int(len(self.emails) / 2)
        else:
            index = len(self.emails)
            emails = self.emails + [new_email]
        return emails, index


class RAGEmailRetriever(EmailRetriever):
    """Acts as a retriever in a RAG pipeline.

    Given a `query`, `retrieve()` returns the `top_k` emails that are most similar to the `query`,
    from the set of `existing_emails + [new_email]`.

    returns the index of the email in the list or None if it is not retrieved.
    """

    def __init__(
        self,
        query: str,
        embedder: SentenceTransformer,
        existing_emails: list[str],
        top_k: int,
        filters: list[str],
    ):
        """Initializes the retriever for a given `query` and `existing_emails`."""
        self.filters = filters
        self.embedder = embedder
        self.query_embedding = self.embedder.encode(query)
        # Preprocessing: find top_k emails to summarize.
        email_embeddings = self.embedder.encode(existing_emails)
        scores = self.embedder.similarity(self.query_embedding, email_embeddings)[0].tolist()
        top_k_tuples = sorted(zip(existing_emails, scores), key=lambda x: x[1], reverse=True)[:top_k]
        self.top_k_emails, self.top_k_scores = zip(*top_k_tuples)

    def _include_email(self, new_email: str) -> tuple[list[str], int]:
        """Returns the set of `existing_emails` and `new_email` sorted by their similarity to the `query`."""
        new_email_embedding = self.embedder.encode(new_email)
        new_email_score = self.embedder.similarity(self.query_embedding, new_email_embedding)
        rank = bisect.bisect([-score for score in self.top_k_scores], -1 * new_email_score[0][0].cpu())
        emails = list(self.top_k_emails[:rank]) + [new_email] + list(self.top_k_emails[rank:])
        return emails, rank

    def retrieve(self, new_email: str) -> tuple[list[str], int | None]:
        """Temporarily includes the `new_email` in the set of `existing_emails`, and
        retrieves the `top_k` emails that are most similar to the initial `query`.
        """
        new_email = filter_emails(new_email, self.filters)
        emails, rank = self._include_email(new_email)
        emails = emails[: len(self.top_k_emails)]
        if rank > (len(emails) - 1):
            rank = None
        return emails, rank
