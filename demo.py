"""تجربة سريعة من الطرفية:  python demo.py "كم فرع عندنا في جدة؟" """
import json
import sys

from model import LLM
from pipeline import Assistant

q = " ".join(sys.argv[1:]) or "كم فرع عندنا في جدة؟"
print(json.dumps(Assistant(LLM()).run(q), ensure_ascii=False, indent=2))
