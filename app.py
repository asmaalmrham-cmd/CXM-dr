"""
الـ API (Space على Hugging Face):  POST /select_tool   و   POST /compose_answer
التوثيق التفاعلي لفريق الباك:  /docs      صفحة تجربة سريعة:  /demo
"""
from typing import Any

import gradio as gr
import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel, Field

from model import LLM
from pipeline import Assistant

assistant = Assistant(LLM())
app = FastAPI(title="CXM Assistant API")


class SelectRequest(BaseModel):
    question: str
    history: list[dict] = Field(default_factory=list)  # [{"role":"user"|"assistant","content":"..."}]


class ComposeRequest(BaseModel):
    question: str
    tool: str
    result: Any  # نتيجة الأداة كما رجعها الباك


@app.get("/health")
def health():
    return {"status": "ok", "model": assistant.llm.model_id}


@app.post("/select_tool")
def select_tool(req: SelectRequest):
    return assistant.select_tool(req.question, req.history)


@app.post("/compose_answer")
def compose_answer(req: ComposeRequest):
    return assistant.compose_answer(req.question, req.tool, req.result)


def _chat(message, history):
    out = assistant.run(message, [{"role": m["role"], "content": str(m["content"])} for m in history])
    text = out["text"]
    if out.get("options"):
        text += "\n\nالخيارات: " + " | ".join(out["options"])
    return text


app = gr.mount_gradio_app(app, gr.ChatInterface(_chat, type="messages", title="CXM — تجربة المساعد"), path="/demo")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=7860)
