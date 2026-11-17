"""تحميل النموذج من Hugging Face وتشغيله (يدعم Tool Calling عبر chat template)."""
import os
import threading

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from config import DEFAULT_MODEL


class LLM:
    def __init__(self, model_id=None):
        self.model_id = model_id or DEFAULT_MODEL
        self.tok = AutoTokenizer.from_pretrained(self.model_id)
        kwargs = dict(device_map="auto")
        if os.getenv("LOAD_4BIT") == "1":  # لو الـ GPU صغير: pip install bitsandbytes
            from transformers import BitsAndBytesConfig
            kwargs["quantization_config"] = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_compute_dtype=torch.float16)
        else:
            kwargs["torch_dtype"] = "auto"
        self.model = AutoModelForCausalLM.from_pretrained(self.model_id, **kwargs)
        self._lock = threading.Lock()  # طلب واحد في نفس الوقت على النموذج

    def chat(self, messages, tools=None, max_new_tokens=300) -> str:
        kw = dict(add_generation_prompt=True, return_tensors="pt", return_dict=True,
                  enable_thinking=False)  # Qwen3: يوقف وضع التفكير. النماذج الثانية تتجاهله.
        if tools:
            kw["tools"] = tools
        inputs = self.tok.apply_chat_template(messages, **kw).to(self.model.device)
        with self._lock, torch.no_grad():
            out = self.model.generate(**inputs, max_new_tokens=max_new_tokens, do_sample=False)
        return self.tok.decode(out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True).strip()
