import os
import json
import logging
import tiktoken

MAX_TOKENS = 8000
TOKENS_ENCODER = tiktoken.get_encoding("o200k_base")


def truncate_tokens(text, max_tokens=MAX_TOKENS):
    # Faster check first based on conservative estimate.
    if len(text) < max_tokens * 2:
        return text

    text_e = TOKENS_ENCODER.encode(text)
    if len(text_e) > max_tokens:
        logging.info(f"Truncating: {text[:100]}")
        text = TOKENS_ENCODER.decode(text_e[:max_tokens])

    return text


def format_email(subject, body):
    return f"Subject of the email: {subject}.   Body: {body}"


def load_benign_dataset(folder):
    emails = []
    fnames = [f"level{i}.json" for i in range(1, 5)] + ["fp_tests.json"]

    for fname in fnames:
        data = json.load(open(os.path.join(folder, fname)))
        for email in data["emails"]:
            subject, body = email.split("Body: ")
            subject = subject.replace("Subject of the email: ", "")
            email = format_email(subject, body)
            emails.append(email)

    return emails
