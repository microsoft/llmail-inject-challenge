"""Implementation of the various LLMs + defenses."""

import os
import json
import torch
import logging
import numpy as np
from openai import AzureOpenAI
from transformers import AutoTokenizer, pipeline, AutoModelForCausalLM, AutoConfig
from azure.ai.inference import ChatCompletionsClient
from azure.core.credentials import AzureKeyCredential

from .models import LLMResponse, ToolCall
from .detection import Detection_Defense
from .prompt_utils import (
    format_emails,
    parse_tool_calls,
    SPOTLIGHT_SYS_SUFFIX,
    SPOTLIGHT_QUERY_FORMAT,
    SPOTLIGHT_EMAILS_FORMAT,
    SPOTLIGHT_DATA_MARK,
    SPOTLIGHT_DATA_MARK_SUFFIX,
)
from .task_tracker_utils import check_task_tracker_in_defs

COMPETITON_PHASE = os.getenv("COMPETITON_PHASE")


def set_seed(seed):
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


def setup_hf_llm(model_name, cache_dir, max_new_tokens=3000):
    """
    Sets up a Hugging Face model and tokenizer, caching it for future use.
    """
    config = AutoConfig.from_pretrained(
        model_name,
        use_cache=True,
        cache_dir=os.path.join(cache_dir, model_name),
        device_map="auto",
    )
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        config=config,
        cache_dir=os.path.join(cache_dir, model_name),
        device_map="auto",
        torch_dtype=torch.bfloat16,
    )
    model.eval()
    tokenizer = AutoTokenizer.from_pretrained(model_name, use_cache=True)
    tokenizer.pad_token = tokenizer.eos_token

    return model, tokenizer


class LLMWithDefenses:
    """Abstracts an LLM and its defenses."""

    def __init__(
        self,
        llm_name: str,
        system_prompt: str,
        defenses: set[str],
        config: dict,
        task_tracker_llm,
        prompt_shield_model=None,
        cb=None,
    ):
        """Initializes the LLM with the given defenses.

        `hf_model`, `hf_tokenizer`, and `hf_pipeline_gen` are only required if we deploy Phi3
        locally (and `local_open_llm` is set to `True`).

        Args:
            llm_name (str): The name of the LLM model.
            system_prompt (str): The system prompt for the LLM.
            defenses (set[str]): The defenses to be used.
            config (dict): The configuration, usually parsed from `config.yaml`.
        """
        self.system_prompt = system_prompt
        self.defenses = defenses

        self.cb = cb

        self.llms = {}
        self.llms["task_tracker_LLM"] = task_tracker_llm

        if "prompt_shield" in defenses:
            assert prompt_shield_model is not None

        if check_task_tracker_in_defs(defenses) or "all" in defenses:
            assert task_tracker_llm["hf_model"] is not None, "task_tracker requires `hf_model`."
            assert task_tracker_llm["hf_tokenizer"] is not None, "task_tracker requires `hf_tokenizer`."
            assert task_tracker_llm["llm_name"] is not None, "task_tracker requires `llm_name`."
            assert task_tracker_llm["layer"] is not None, "task_tracker requires `task_tracker_layer`."
            assert task_tracker_llm["classifier"] is not None, "task_tracker requires `classifier`."
            assert task_tracker_llm["threshold"] is not None, "task_tracker requires `threshold`."

        if "gpt" in llm_name:
            self.llms["gpt"] = GPTLLM(llm_name=llm_name, config=config)
            self.llm_name = "gpt"

        elif "phi" in llm_name.lower():
            self.llms["Phi3_api"] = Phi3LLM(llm_name=llm_name, config=config)
            self.llm_name = "Phi3_api"
        else:
            raise ValueError(f"LLM model {llm_name} not found.")

        self.classifier = Detection_Defense(
            defenses,
            task_tracker_llm=self.llms["task_tracker_LLM"],
            config=config,
            prompt_shield_model=prompt_shield_model,
            cb=self.cb,
        )

        self.dry_run = config.get("llm_dry_run", False)

    def prompt(
        self, query: str, emails: list[str], attack_email_rank: int | None
    ) -> tuple[LLMResponse, bool]:
        """Prompts the LLM model for the given query, and runs the defenses.

        Args:
            query (str): The user's query.
            emails (list[str]): The emails to be processed.
            attack_email_rank (int|None): If the submitted email in the list, this is the index of it, otherwise none.

        Returns:
            tuple[str, bool, bool]: The response from the LLM, whether the detection defense was triggered, and whether the tool was called.
        """

        system_prompt = self.system_prompt

        detections = self.classifier.run_detection_defense(
            emails, user_prompt=query, attack_email_rank=attack_email_rank
        )

        formatted_emails = format_emails(emails)

        if "spotlight" in self.defenses:
            system_prompt += SPOTLIGHT_SYS_SUFFIX
            query = SPOTLIGHT_QUERY_FORMAT.format(query)
            system_prompt += SPOTLIGHT_DATA_MARK_SUFFIX
            formatted_emails = SPOTLIGHT_DATA_MARK.join(formatted_emails.split(" "))
            formatted_emails = SPOTLIGHT_EMAILS_FORMAT.format(formatted_emails)

        elif COMPETITON_PHASE == "phase2":
            # Apply tags for phase 2 for all defenses since we don't have specific spotlighting defense
            # Don't apply the datamarking
            system_prompt += SPOTLIGHT_SYS_SUFFIX
            query = SPOTLIGHT_QUERY_FORMAT.format(query)
            formatted_emails = SPOTLIGHT_EMAILS_FORMAT.format(formatted_emails)

        if self.dry_run:
            logging.warning("WARNING: DRY RUN mode is enabled. No LLM calls was made.")
            return LLMResponse(response="dry_run", tool_calls=[]), any(detections.values())

        llm_response = self.llms[self.llm_name].call_model(system_prompt, query, formatted_emails)

        return llm_response, any(detections.values())


class LLM:
    """Abstracts an LLM model.

    This class must implement LLM calling, as well as the detection of tool calls.
    """

    def __init__(self, llm_name: str, config: dict):
        self.llm_name = llm_name
        self.top_p = config["top_p"]
        self.max_new_tokens = config["max_new_tokens"]
        self.tools_config = config["llm_tools"]

    def call_model(self, system_prompt: str, query: str, emails: str) -> LLMResponse:
        """Calls the LLM model with the given messages.

        Returns:
            str: The response from the LLM.
            bool: Whether the tool was called.
        """
        raise NotImplementedError


class GPTLLM(LLM):
    """GPT LLM model."""

    def __init__(self, llm_name: str, config: dict):
        super().__init__(llm_name, config)
        self.client = AzureOpenAI(
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            api_version="2024-02-15-preview",
        )

    def call_model(self, system_prompt: str, query: str, emails: str) -> LLMResponse:
        """Calls the LLM model with the given messages.

        Returns:
            str: The response from the LLM.
            bool: Whether the tool was called.
        """
        messages = [{"role": "system", "content": system_prompt}]
        messages += [{"role": "user", "content": query}]
        messages += [
            {
                "role": "assistant",
                "tool_calls": [
                    {
                        "id": "call_001",
                        "type": "function",
                        "function": {
                            "name": "read_emails",
                            "arguments": f"{{'query': '{query}'}}",
                        },
                    }
                ],
            }
        ]

        messages += [
            {
                "role": "tool",
                "tool_call_id": "call_001",
                "content": emails,
            }
        ]

        response = self.client.chat.completions.create(
            model=self.llm_name,
            messages=messages,
            max_tokens=self.max_new_tokens,
            tools=self.tools_config,
            top_p=self.top_p,
            seed=100,
        )
        if not response.choices:
            logging.error("No response from the LLM.")
            raise Error("No response received from the LLM")

        message = response.choices[0].message

        tool_calls = []
        if message.tool_calls:
            for tool in message.tool_calls:
                try:
                    args = json.loads(tool.function.arguments)
                except json.JSONDecodeError:
                    args = {}

                tool_calls.append(
                    ToolCall(
                        name=tool.function.name,
                        arguments=args,
                    )
                )
        return LLMResponse(response=message.content if message.content else "", tool_calls=tool_calls)


class Phi3LLM(LLM):
    """Phi3 LLM model."""

    def __init__(self, llm_name, config: dict):
        super().__init__(llm_name, config)
        self.open_source_client = ChatCompletionsClient(
            endpoint=os.getenv("AZURE_OPEN_SOURCE_ENDPOINT"),
            credential=AzureKeyCredential(os.getenv("AZURE_OPEN_SOURCE_API_KEY")),
            seed=100,
        )
        self.llm_system_prompt_tool = config["llm_system_prompt_tool"]
        assert len(config["llm_tools"]) <= 1, "Phi3 only supports one tool."

    def call_model(self, system_prompt: str, query: str, emails: str) -> LLMResponse:

        # Apply tool calls to the system prompt.
        system_prompt = f"{system_prompt}\n\n{self.llm_system_prompt_tool}"

        # NOTE: Phi3 does not have system prompts.
        full_prompt = system_prompt + "\n" + query + "\n\n" + emails
        messages = [{"role": "user", "content": full_prompt}]

        payload = {"messages": messages, "max_tokens": self.max_new_tokens, "top_p": self.top_p}
        response = self.open_source_client.complete(payload, seed=100)

        if not response.choices:
            logging.error("No response from the LLM.")
            raise Error("No response received from the LLM")

        tool_calls = parse_tool_calls(response.choices[0].message.content)

        return LLMResponse(response=response.choices[0].message.content, tool_calls=tool_calls)
