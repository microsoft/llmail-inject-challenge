from transformers import DebertaV2Tokenizer
import torch
from typing import List, Dict
import os
import onnxruntime as ort


class JailbreakModelOnnx:
    def __init__(self, model_root, device=None):
        self.model_path = os.path.join(model_root, "model", "model.onnx")

        self.tokenizer = DebertaV2Tokenizer.from_pretrained(os.path.join(model_root, "model"))

        self.device = (
            torch.device("cuda:0" if torch.cuda.is_available() else "cpu") if device is None else device
        )

        providers = [
            (
                "CUDAExecutionProvider",
                {
                    "device_id": 0,
                    "arena_extend_strategy": "kNextPowerOfTwo",
                    "gpu_mem_limit": 12 * 1024 * 1024 * 1024,
                    "cudnn_conv_algo_search": "EXHAUSTIVE",
                    "do_copy_in_default_stream": True,
                },
            ),
            "CPUExecutionProvider",
        ]
        ort_session_options = ort.SessionOptions()
        ort_session_options.enable_cpu_mem_arena = False
        self.ort_session = ort.InferenceSession(self.model_path, providers=providers)
        self.run_config = ort.RunOptions().add_run_config_entry(
            "memory.enable_memory_arena_shrinkage", "gpu:0"
        )

    def predict(self, items) -> List[Dict]:
        max_seq_len = 512

        inputs = self.tokenizer(items, padding="max_length", max_length=512)

        # truncate from front
        for name, values in inputs.items():
            for i, example in enumerate(values):
                if len(example) > max_seq_len:
                    # remove padding
                    try:
                        pad_start_idx = example.index(0)
                        # can remove pads only
                        if pad_start_idx < max_seq_len:
                            example = example[:max_seq_len]
                        # remove all pads
                        else:
                            example = example[:pad_start_idx]
                    except:
                        pass
                    # knock off rest if nessicary
                    if len(example) > max_seq_len:
                        values[i] = [example[0]] + example[1 + (len(example) - max_seq_len) :]
                    else:
                        values[i] = example

        output = []

        onnx_logits = self.ort_session.run(
            None,
            {"input_ids": inputs["input_ids"], "attention_mask": inputs["attention_mask"]},
            self.run_config,
        )[0]

        scores = torch.nn.functional.sigmoid(torch.tensor(onnx_logits)).tolist()

        for i in range(len(scores)):
            output.append(
                {
                    "jailbreak": {"class": int(scores[i][1] >= 0.85), "scores": [float(scores[i][1])]},
                    "xpia": {"class": int(scores[i][0] >= 0.99), "scores": [float(scores[i][0])]},
                }
            )

        return output[0]["xpia"]["scores"][0]
