import json
from datetime import datetime

def build_project_report(form, analysis, ad_copy, prompt, model, duration):
    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "input": form,
        "market_analysis": analysis,
        "ad_copy": ad_copy,
        "runway": {"model": model, "duration_seconds": duration, "prompt": prompt},
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)
