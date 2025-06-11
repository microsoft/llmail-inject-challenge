from os.path import dirname, join as pathjoin
from typing import Dict, List
import yaml
import logging
import os
import json
import pickle

PARENT_DIR = dirname(dirname(__file__))
DATA_PATH = pathjoin(PARENT_DIR, "data")


def load_emails_from_scenario(scenario: str) -> list[str]:
    try:
        with open(pathjoin(DATA_PATH, "emails", f"{scenario}.txt"), "r") as f:
            lines = f.readlines()
            return [line.strip() for line in lines if line.strip()]
    except FileNotFoundError:
        return []


def load_emails(fname: str) -> List[str]:
    try:
        email_path = os.path.join(DATA_PATH, fname)
        logging.info(f"Retrieving emails from: {email_path}")
        with open(email_path, "r") as f:
            data = json.load(f)

        emails = data.get("emails", [])

        if not isinstance(emails, list):
            raise ValueError("Expected 'emails' to be a list in the JSON file.")

        return emails
    except FileNotFoundError:
        logging.error(f"File {fname} not found in {DATA_PATH}.", exc_info=True)
        raise
    except json.JSONDecodeError:
        logging.error(f"Error decoding JSON from file {fname}.", exc_info=True)
        raise
    except Exception as e:
        logging.error(f"Unexpected error loading emails from {fname}: {e}", exc_info=True)
        raise


def load_config(file_name: str = "config.yaml") -> Dict:
    try:
        config_path = os.path.join(PARENT_DIR, file_name)
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)  # Load the YAML file contents into a dictionary
        return config
    except FileNotFoundError:
        logging.error("Configuration file not found.", exc_info=True)
        raise
    except yaml.YAMLError as e:
        logging.error(f"Error parsing YAML configuration: {e}", exc_info=True)
        raise
    except Exception as e:
        logging.error(f"Unexpected error loading configuration: {e}", exc_info=True)
        raise


def load_task_tracker(classifier_path: str):
    model_path = os.path.join(DATA_PATH, classifier_path)

    try:
        with open(model_path, "rb") as f:
            task_tracker_model = pickle.load(f)
        return task_tracker_model
    except FileNotFoundError:
        logging.error(f"Model file not found at path: {model_path}", exc_info=True)
        raise
    except pickle.UnpicklingError:
        logging.error(f"Error unpickling model from file: {model_path}", exc_info=True)
        raise
    except Exception as e:
        logging.error(f"Unexpected error loading task tracker model: {e}", exc_info=True)
        raise
