import json
import re

def parse_planner_json(content: str) -> dict:
    content = content.strip()

    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?\s*", "", content)
        content = re.sub(r"\s*```$", "", content)

    start = content.find("{")
    end = content.rfind("}")

    if start != -1 and end != -1 and end > start:
        return json.loads(content[start:end + 1])

    return {
        "status": "done",
        "intent": "chat",
        "tickers": [],
        "company_names": [],
        "start_date": None,
        "end_date": None,
        "answer": content,
    }