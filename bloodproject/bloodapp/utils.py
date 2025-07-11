from openai import OpenAI
from django.conf import settings
import os

import json
import re

from .models import Marker, HealthCondition


def load_health_conditions_data():
    return {"health_conditions": list(HealthCondition.objects.all().values())}


def get_risk_score_for_condition(prompt):
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a medical assistant calculating risk scores."},
            {"role": "user", "content": prompt}
        ]
    )

    content = response.choices[0].message.content
    cleaned = re.sub(r'```(?:json)?', '', content).strip()
    return json.loads(cleaned)



def safe_json_loads(content):
    """
    Cleans GPT response by removing triple backticks and loads JSON safely.
    """
    if not content:
        raise ValueError("LLM returned empty content.")
    # Remove ```json or ``` and ```
    cleaned = re.sub(r'```(?:json)?', '', content, flags=re.IGNORECASE)
    cleaned = cleaned.replace('```', '').strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        # Debugging
        print("=== Failed to parse JSON ===")
        print("Content:", content)
        raise


def get_health_conditions_from_analysis(analysis_text):
    client = OpenAI(api_key = os.environ.get("OPENAI_API_KEY"))

    health_conditions_data = list(HealthCondition.objects.all().values())
    condition_ids = [c["condition_id"] for c in health_conditions_data]

    system_prompt = (
        "You are a medical reasoning assistant. "
        "Given a blood analysis, predict likely conditions ONLY from this list of IDs: "
        f"{condition_ids}. "
        "Return JSON like: [{'condition_id': 'hypothyroidism', 'level_of_risk': 'High', 'explanation': '...'}]."
    )

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Here is the analysis:\n\n{analysis_text}"}
        ]
    )
    return response.choices[0].message.content
