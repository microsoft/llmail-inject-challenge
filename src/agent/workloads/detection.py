from transformers import AutoTokenizer, AutoModelForSequenceClassification, pipeline
import torch
import requests
import json
from .task_tracker_utils import task_tracker_main, check_task_tracker_in_defs
from .data_loader import load_task_tracker
from openai import AzureOpenAI
import os
from .prompt_utils import LLM_JUDGE_PROMPT_PHASE1, LLM_JUDGE_PROMPT_PHASE2, format_emails
from torch.nn.functional import softmax

COMPETITON_PHASE = os.getenv("COMPETITON_PHASE")

if COMPETITON_PHASE == "phase1":
    LLM_JUDGE_PROMPT = LLM_JUDGE_PROMPT_PHASE1
elif COMPETITON_PHASE == "phase2":
    LLM_JUDGE_PROMPT = LLM_JUDGE_PROMPT_PHASE2


class Detection_Defense:
    def __init__(
        self,
        detection_method: set[str],
        task_tracker_llm,
        config={},
        prompt_shield_model=None,
        cb=None,
    ):

        self.detection_method = detection_method

        if check_task_tracker_in_defs(self.detection_method):
            self.task_tracker_layer = task_tracker_llm["layer"]
            self.task_tracker_classifier = load_task_tracker(task_tracker_llm["classifier"])
            self.llm_model = task_tracker_llm["hf_model"]
            self.llm_tokenizer = task_tracker_llm["hf_tokenizer"]
            self.task_tracker_llm_name = task_tracker_llm["llm_name"]
            self.task_tracker_threshold = task_tracker_llm["threshold"]

        self.cb = cb

        if "llm_judge" in self.detection_method:
            self.client = AzureOpenAI(
                azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
                api_key=os.getenv("AZURE_OPENAI_API_KEY"),
                api_version="2023-05-15",
            )

        self.prompt_shield_model = prompt_shield_model
        self.prompt_shield_threshold = config["prompt_shield_threshold"]

    def run_detection_defense(self, external_emails, user_prompt="", attack_email_rank=None):

        if self.detection_method == [] and not self.cb:
            return {"none": False}

        detection = {}
        # always apply the conformal block list on top of any defense if it is enabled
        if self.cb:
            detection["cb"] = self.cb.predict(external_emails[attack_email_rank])

        for method in self.detection_method:
            if method == "prompt_shield":
                if attack_email_rank is not None:
                    probs = self.prompt_shield_model.predict([external_emails[attack_email_rank]])
                else:
                    probs = 0.0
                detection[method] = probs > self.prompt_shield_threshold

            if "task_tracker" in method:
                formatted_emails = format_emails(external_emails)
                probs = task_tracker_main(
                    formatted_emails,
                    self.llm_model,
                    self.task_tracker_llm_name,
                    self.llm_tokenizer,
                    self.task_tracker_classifier,
                    self.task_tracker_layer,
                    specific_user_prompt=user_prompt,
                )
                detection[method] = bool(probs[0] > self.task_tracker_threshold)

            if method == "llm_judge":
                if attack_email_rank != None:
                    judge_prompt = LLM_JUDGE_PROMPT.format(external_emails[attack_email_rank])
                    messages = [{"role": "system", "content": judge_prompt}]
                    res = self.client.chat.completions.create(
                        model="gpt-4o",
                        messages=messages,
                        temperature=0,
                        max_tokens=3000,
                        response_format={"type": "json_object"},
                    )
                    try:
                        judge_answer = res.choices[0].message.content
                        parsed_output = json.loads(judge_answer)
                        detection[method] = False if "CLEAN" in parsed_output["decision"] else True
                        print(parsed_output)
                    except json.JSONDecodeError:
                        detection[method] = True
                else:
                    detection[method] = False

        return detection
