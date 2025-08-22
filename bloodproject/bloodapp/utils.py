from openai import OpenAI
from django.conf import settings
import os

import json
import re
import difflib
from typing import List, Dict, Tuple, Optional

from .models import Marker, HealthCondition


def find_closest_condition_id(condition_name: str, valid_condition_ids: List[str], cutoff: float = 0.6) -> Optional[str]:
    """
    Find the closest matching condition ID using fuzzy string matching.
    
    Args:
        condition_name: The condition name to match
        valid_condition_ids: List of valid condition IDs to match against
        cutoff: Minimum similarity score (0.0 to 1.0) for a match to be considered
    
    Returns:
        The closest matching condition ID or None if no match above cutoff
    """
    # Normalize the input condition name
    normalized_name = condition_name.lower().strip()
    
    # Try exact match first
    if normalized_name in valid_condition_ids:
        return normalized_name
    
    # Try fuzzy matching
    matches = difflib.get_close_matches(normalized_name, valid_condition_ids, n=1, cutoff=cutoff)
    return matches[0] if matches else None


def condition_id_to_display_name(condition_id: str) -> str:
    """
    Convert a condition ID to a proper display name.
    
    Args:
        condition_id: The condition ID (e.g., 'oxidative_stress')
    
    Returns:
        Proper display name (e.g., 'Oxidative Stress')
    """
    if not condition_id:
        return "Unknown Condition"
    
    # Replace underscores with spaces and capitalize each word
    display_name = condition_id.replace('_', ' ').title()
    return display_name


def match_conditions_with_fallback(ai_conditions: List[Dict], valid_condition_ids: List[str]) -> Tuple[List[Dict], List[Dict]]:
    """
    Match AI-returned conditions to valid condition IDs with fallback for unmatched conditions.
    
    Args:
        ai_conditions: List of conditions returned by AI
        valid_condition_ids: List of valid condition IDs from database
    
    Returns:
        Tuple of (matched_conditions, other_conditions)
    """
    matched_conditions = []
    other_conditions = []
    
    for condition in ai_conditions:
        condition_id = condition.get('condition_id') or condition.get('id')
        if not condition_id:
            continue
            
        # Try to find a match
        matched_id = find_closest_condition_id(condition_id, valid_condition_ids)
        
        if matched_id:
            # Found a match, use the matched ID
            matched_conditions.append({
                'condition_id': matched_id,
                'level_of_risk': condition.get('level_of_risk') or condition.get('risk') or '',
                'explanation': condition.get('explanation') or '',
                'original_ai_id': condition_id  # Keep track of what AI originally returned
            })
        else:
            # No match found, add to other conditions
            other_conditions.append({
                'name': condition_id_to_display_name(condition_id),
                'original_id': condition_id,
                'level_of_risk': condition.get('level_of_risk') or condition.get('risk') or '',
                'explanation': condition.get('explanation') or ''
            })
    
    return matched_conditions, other_conditions


def load_health_conditions_data():
    return {"health_conditions": list(HealthCondition.objects.all().values())}


def get_risk_score_for_condition(prompt, condition_name=None):
    """
    Calculate risk score for a condition, optionally including expert comments
    
    Args:
        prompt: The analysis prompt
        condition_name: Optional condition name to include expert comments
    """
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    
    # Get expert comments if condition is provided
    expert_context = ""
    if condition_name:
        condition = find_health_condition(condition_name)
        if condition and condition.expert_comment_markers:
            expert_context = f"\n\nEXPERT COMMENTARY (IFM CP Functional Medicine Practitioner):\n{condition.expert_comment_markers}\n\nUse this expert commentary to weight the importance of different markers when calculating the risk score."
    
    system_prompt = "You are a medical assistant calculating risk scores."
    if expert_context:
        system_prompt += expert_context
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
    )

    content = response.choices[0].message.content
    cleaned = re.sub(r'```(?:json)?', '', content).strip()
    print("CLEANED:", cleaned)
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
    condition_ids = [c.get("condition_id") for c in health_conditions_data if c.get("condition_id")]

    system_prompt = (
        "You are a medical reasoning assistant. "
        "Given a blood analysis, predict likely conditions ONLY from this EXACT list of condition IDs: "
        f"{condition_ids}. "
        "CRITICAL: You MUST use the EXACT condition_id values from this list. "
        "Do not modify, misspell, or create variations of these IDs. "
        "If you need to reference a condition that's not in this list, include it as-is in your response "
        "but note that it will be handled separately. "
        "Return JSON like: [{'condition_id': 'hypothyroidism', 'level_of_risk': 'High', 'explanation': '...'}]."
    )

    print("SYSTEM PROMPT:", system_prompt)
    print("ANALYSIS TEXT:", analysis_text)

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Here is the analysis:\n\n{analysis_text}"}
        ]
    )
    print("RESPONSE:", response.choices[0].message.content)
    return response.choices[0].message.content


def get_treatment_plan(detailed_analyses, supplement_list, other_conditions=None):
    """
    Calls OpenAI to generate a treatment plan in JSON with Nutrition, Lifestyle changes, and Supplements.
    detailed_analyses: list of dicts, each with condition_id, risk_score, detailed_explanation
    supplement_list: list of dicts, each with name, link
    other_conditions: list of dicts, each with name, level_of_risk, explanation (for unmatched conditions)
    """
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    system_prompt = (
        "You are a medical assistant creating personalized treatment plans. "
        "Given the patient's detailed risk analyses for each condition (with explanations and risk scores), "
        "any additional conditions that couldn't be matched to our database, "
        "and a list of supplements (with names and links), return a JSON object with three parts: "
        "1. Nutrition: bullet points (with an option to expand for context), "
        "2. Lifestyle changes: bullet points (with an option to expand for context), "
        "3. Supplements: a table with supplement name, link, and regularity (e.g., morning, after [specific meal], before bed, twice daily, etc.). "
        "Consider ALL conditions mentioned, including the 'other conditions' when creating the treatment plan. "
        "Respond ONLY with JSON."
    )
    
    user_prompt_parts = [
        f"Detailed analyses: {json.dumps(detailed_analyses, ensure_ascii=False)}",
        f"Supplements: {json.dumps(supplement_list, ensure_ascii=False)}"
    ]
    
    if other_conditions:
        user_prompt_parts.append(f"Other conditions to consider: {json.dumps(other_conditions, ensure_ascii=False)}")
    
    user_prompt = "\n".join(user_prompt_parts)
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    )
    content = response.choices[0].message.content
    cleaned = re.sub(r'```(?:json)?', '', content).strip()
    print("TREATMENT PLAN RAW RESPONSE:", cleaned)
    return json.loads(cleaned)


# ===== New utilities for PDF-driven marker extraction =====

def get_marker_meta_list():
    """Return list of marker names and unit options for prompting the LLM."""
    meta = []
    for m in Marker.objects.all().order_by('display_name'):
        meta.append({
            'name': m.name,
            'display_name': m.display_name,
            'units': {
                'standard': m.standard_unit,
                'international': m.international_unit
            }
        })
    return meta


def extract_text_from_pdf(file_obj) -> str:
    """Extract text from a PDF file-like object using PyPDF2, if available."""
    try:
        import PyPDF2
    except Exception as e:
        raise RuntimeError("PyPDF2 not installed. Please install PyPDF2 to enable PDF extraction.")
    reader = PyPDF2.PdfReader(file_obj)
    text = []
    for page in reader.pages:
        try:
            text.append(page.extract_text() or '')
        except Exception:
            continue
    return "\n".join(text)


def map_pdf_values_to_markers(pdf_text: str) -> list:
    """Call OpenAI with marker meta and the PDF text to return list of {name, value, unit_system}."""
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    marker_meta = get_marker_meta_list()
    system_prompt = (
        "You receive: (1) a JSON array of blood markers with their possible unit systems; "
        "(2) raw text extracted from a user's lab PDF. "
        "For each marker found in the PDF, return JSON array of objects with: "
        "name (closest exact match to one of the provided markers' 'name'), value (number), unit_system ('standard' or 'international'). "
        "Use the provided units to infer which system is used if units are present in the text. Return ONLY JSON."
    )
    user_payload = {
        'marker_meta': marker_meta,
        'pdf_text': pdf_text[:20000],  # cap for token safety
    }
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)}
        ]
    )
    content = response.choices[0].message.content
    return safe_json_loads(content)


def parse_signs_and_symptoms(text):
    """
    Parse signs and symptoms text and extract individual bullet points.
    
    Handles various formatting patterns:
    - Numbered lists (1., 2., 3., etc.)
    - Bullet points with special characters (e, ¢, «, etc.)
    - Lines starting with common bullet markers
    - Text with preambles ending in colons
    
    Returns a list of individual symptoms.
    """
    if not text:
        return []

    # Fast-path: if the new CSV "s/sx bullet" format is present, split on «
    if '«' in text:
        parts = [p.strip() for p in re.split(r'«', text) if p and p.strip()]
        cleaned = []
        for p in parts:
            # Strip leading bullet glyphs that may have been persisted
            p = re.sub(r'^[•\-\*\d\.\s]+', '', p).strip()
            if p:
                cleaned.append(p)
        if cleaned:
            return cleaned
    
    # Pre-process text to handle common issues
    text = text.replace('L.', '1.')  # Fix common typo where L is used instead of 1
    
    # Split into lines and clean up
    lines = text.strip().split('\n')
    symptoms = []
    current_symptom = ""
    in_symptom_list = False
    
    # Patterns to identify bullet points
    bullet_patterns = [
        r'^\s*(\d+\.)\s*(.+)$',  # Numbered lists: 1. symptom
        r'^\s*([e¢«•·▪▫◦‣⁃])\s*(.+)$',  # Special bullet characters
        r'^\s*([A-Z]\.)\s*(.+)$',  # Letter bullets: A. symptom
        r'^\s*[-*]\s*(.+)$',  # Dash or asterisk bullets
    ]
    
    # Compile patterns for efficiency
    compiled_patterns = [re.compile(pattern) for pattern in bullet_patterns]
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Check if this line starts a symptom list
        if any(keyword in line.lower() for keyword in [
            'signs and symptoms', 'symptoms may include', 'common symptoms',
            'may include', 'can include', 'typically include', 'following signs and symptoms'
        ]):
            in_symptom_list = True
            continue
        
        # Skip preamble lines that don't contain actual symptoms
        if not in_symptom_list and any(keyword in line.lower() for keyword in [
            'early stages', 'as the disease progresses', 'depending on',
            'often present no symptoms', 'causes a decrease', 'leading to'
        ]):
            continue
            
        # Check if this line matches any bullet pattern
        is_bullet = False
        for pattern in compiled_patterns:
            match = pattern.match(line)
            if match:
                # If we have a current symptom being built, save it
                if current_symptom:
                    symptoms.append(current_symptom.strip())
                    current_symptom = ""
                
                # Extract the symptom text (group 2 for numbered/lettered, group 1 for others)
                if len(match.groups()) == 2:
                    symptom_text = match.group(2).strip()
                else:
                    symptom_text = match.group(1).strip()
                
                if symptom_text:
                    current_symptom = symptom_text
                is_bullet = True
                break
        
        # If no bullet pattern matched, check if it's a continuation of a symptom
        if not is_bullet and line:
            # Skip lines that are likely headers or preambles
            if not any(keyword in line.lower() for keyword in [
                'signs and symptoms', 'symptoms may include', 'common symptoms',
                'early stages', 'as the disease progresses', 'depending on',
                'may include', 'can include', 'typically include'
            ]):
                # Check if line ends with colon (likely a header)
                if not line.endswith(':'):
                    # If we have a current symptom, append to it
                    if current_symptom:
                        current_symptom += " " + line
                    else:
                        # Only add standalone lines if we're in a symptom list
                        if in_symptom_list:
                            symptoms.append(line)
    
    # Add the last symptom if there is one
    if current_symptom:
        symptoms.append(current_symptom.strip())
    
    # Clean up symptoms
    cleaned_symptoms = []
    for symptom in symptoms:
        # Remove extra whitespace and normalize
        cleaned = ' '.join(symptom.split())
        if cleaned and len(cleaned) > 2:  # Filter out very short items
            cleaned_symptoms.append(cleaned)
    
    return cleaned_symptoms

import os
import django
import json
from typing import List, Dict, Optional

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bloodproject.settings')
django.setup()

from .models import HealthCondition, Marker


def get_all_markers() -> List[Marker]:
    """Get all available markers"""
    return Marker.objects.all()


def get_all_health_conditions() -> List[HealthCondition]:
    """Get all health conditions"""
    return HealthCondition.objects.all()


def find_health_condition(condition_name: str) -> Optional[HealthCondition]:
    """Find a health condition by name or condition_id"""
    return (
        HealthCondition.objects.filter(name__icontains=condition_name).first() or
        HealthCondition.objects.filter(condition_id__icontains=condition_name).first()
    )


def find_marker(marker_name: str) -> Optional[Marker]:
    """Find a marker by name"""
    return Marker.objects.filter(name__icontains=marker_name).first()


def add_markers_to_condition(
    condition_name: str, 
    markers: List[str], 
    marker_type: str
) -> Dict[str, any]:
    """
    Add markers to a health condition
    
    Args:
        condition_name: Name or ID of the health condition
        markers: List of marker names to add
        marker_type: 'low' or 'high'
    
    Returns:
        Dict with success status and details
    """
    condition = find_health_condition(condition_name)
    if not condition:
        return {
            'success': False,
            'error': f'Health condition "{condition_name}" not found'
        }
    
    if marker_type not in ['low', 'high']:
        return {
            'success': False,
            'error': 'marker_type must be "low" or "high"'
        }
    
    marker_field = (
        condition.associated_markers_low if marker_type == 'low' 
        else condition.associated_markers_high
    )
    
    markers_to_add = []
    not_found = []
    
    for marker_name in markers:
        marker = find_marker(marker_name)
        if marker:
            markers_to_add.append(marker)
        else:
            not_found.append(marker_name)
    
    if markers_to_add:
        marker_field.add(*markers_to_add)
    
    return {
        'success': True,
        'condition': condition.name or condition.condition_id,
        'added': [m.name for m in markers_to_add],
        'not_found': not_found,
        'total_added': len(markers_to_add)
    }


def remove_markers_from_condition(
    condition_name: str, 
    markers: List[str], 
    marker_type: str
) -> Dict[str, any]:
    """
    Remove markers from a health condition
    
    Args:
        condition_name: Name or ID of the health condition
        markers: List of marker names to remove
        marker_type: 'low' or 'high'
    
    Returns:
        Dict with success status and details
    """
    condition = find_health_condition(condition_name)
    if not condition:
        return {
            'success': False,
            'error': f'Health condition "{condition_name}" not found'
        }
    
    if marker_type not in ['low', 'high']:
        return {
            'success': False,
            'error': 'marker_type must be "low" or "high"'
        }
    
    marker_field = (
        condition.associated_markers_low if marker_type == 'low' 
        else condition.associated_markers_high
    )
    
    markers_to_remove = []
    not_found = []
    
    for marker_name in markers:
        marker = find_marker(marker_name)
        if marker:
            markers_to_remove.append(marker)
        else:
            not_found.append(marker_name)
    
    if markers_to_remove:
        marker_field.remove(*markers_to_remove)
    
    return {
        'success': True,
        'condition': condition.name or condition.condition_id,
        'removed': [m.name for m in markers_to_remove],
        'not_found': not_found,
        'total_removed': len(markers_to_remove)
    }


def get_condition_markers(condition_name: str) -> Dict[str, any]:
    """
    Get all markers associated with a health condition
    
    Args:
        condition_name: Name or ID of the health condition
    
    Returns:
        Dict with low and high markers and expert comments
    """
    condition = find_health_condition(condition_name)
    if not condition:
        return {
            'success': False,
            'error': f'Health condition "{condition_name}" not found'
        }
    
    return {
        'success': True,
        'condition': condition.name or condition.condition_id,
        'low_markers': [m.name for m in condition.associated_markers_low.all()],
        'high_markers': [m.name for m in condition.associated_markers_high.all()],
        'expert_comment_markers': condition.expert_comment_markers
    }


def list_all_conditions_with_markers() -> List[Dict[str, any]]:
    """
    Get all health conditions with their associated markers
    
    Returns:
        List of dicts with condition info, markers, and expert comments
    """
    conditions = get_all_health_conditions()
    result = []
    
    for condition in conditions:
        result.append({
            'name': condition.name or condition.condition_id,
            'condition_id': condition.condition_id,
            'low_markers': [m.name for m in condition.associated_markers_low.all()],
            'high_markers': [m.name for m in condition.associated_markers_high.all()],
            'expert_comment_markers': condition.expert_comment_markers
        })
    
    return result


def get_expert_comments_for_risk_assessment(condition_name: str) -> Dict[str, any]:
    """
    Get expert comments for risk assessment of a specific condition
    
    Args:
        condition_name: Name or ID of the health condition
    
    Returns:
        Dict with expert comments for risk assessment
    """
    condition = find_health_condition(condition_name)
    if not condition:
        return {
            'success': False,
            'error': f'Health condition "{condition_name}" not found'
        }
    
    return {
        'success': True,
        'condition': condition.name or condition.condition_id,
        'expert_comment_markers': condition.expert_comment_markers,
        'has_expert_comments': bool(condition.expert_comment_markers)
    }


def set_expert_comment(
    condition_name: str, 
    comment: str
) -> Dict[str, any]:
    """
    Set expert comment for a health condition's markers
    
    Args:
        condition_name: Name or ID of the health condition
        comment: Expert comment text
    
    Returns:
        Dict with success status and details
    """
    condition = find_health_condition(condition_name)
    if not condition:
        return {
            'success': False,
            'error': f'Health condition "{condition_name}" not found'
        }
    
    try:
        condition.expert_comment_markers = comment
        condition.save()
        
        return {
            'success': True,
            'condition': condition.name or condition.condition_id,
            'comment': comment
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


def import_markers_from_json(json_file_path: str) -> Dict[str, any]:
    """
    Import marker associations from a JSON file
    
    Expected JSON format:
    {
        "condition_name": {
            "low_markers": ["marker1", "marker2"],
            "high_markers": ["marker3", "marker4"],
            "expert_comment_markers": "Expert comment on marker importance"
        }
    }
    """
    try:
        with open(json_file_path, 'r') as f:
            data = json.load(f)
        
        results = []
        for condition_name, marker_data in data.items():
            condition_result = {
                'condition': condition_name,
                'low_markers': {'success': False, 'error': ''},
                'high_markers': {'success': False, 'error': ''},
                'expert_comments': {'success': False, 'error': ''}
            }
            
            # Add low markers
            if 'low_markers' in marker_data and marker_data['low_markers']:
                low_result = add_markers_to_condition(
                    condition_name, 
                    marker_data['low_markers'], 
                    'low'
                )
                condition_result['low_markers'] = low_result
            
            # Add high markers
            if 'high_markers' in marker_data and marker_data['high_markers']:
                high_result = add_markers_to_condition(
                    condition_name, 
                    marker_data['high_markers'], 
                    'high'
                )
                condition_result['high_markers'] = high_result
            
            # Set expert comments
            if 'expert_comment_markers' in marker_data:
                comment_result = set_expert_comment(
                    condition_name, 
                    marker_data['expert_comment_markers']
                )
                condition_result['expert_comments'] = comment_result
            
            results.append(condition_result)
        
        return {
            'success': True,
            'results': results
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


# Example usage functions
def example_add_markers():
    """Example of how to add markers to a condition"""
    result = add_markers_to_condition(
        condition_name="iron_deficiency_anemia",
        markers=["Ferritin", "Iron"],
        marker_type="low"
    )
    print(f"Result: {result}")


def example_list_conditions():
    """Example of how to list all conditions with markers"""
    conditions = list_all_conditions_with_markers()
    for condition in conditions:
        print(f"\n{condition['name']}:")
        print(f"  Low markers: {', '.join(condition['low_markers'])}")
        print(f"  High markers: {', '.join(condition['high_markers'])}")


if __name__ == "__main__":
    # Example usage
    example_list_conditions()


def _resolve_ranges_for_marker(marker: Marker, unit_system: str) -> Dict[str, Optional[float]]:
    """Helper to pick appropriate normal/optimal ranges based on unit system."""
    unit_sys = (unit_system or 'standard').lower()
    if unit_sys == 'international':
        normal_min = marker.standard_min_international if marker.standard_min_international is not None else marker.standard_min
        normal_max = marker.standard_max_international if marker.standard_max_international is not None else marker.standard_max
        optimal_min = marker.optimal_min_international if marker.optimal_min_international is not None else marker.optimal_min
        optimal_max = marker.optimal_max_international if marker.optimal_max_international is not None else marker.optimal_max
        unit = marker.international_unit or marker.standard_unit or ''
    else:
        normal_min = marker.standard_min_conventional if marker.standard_min_conventional is not None else marker.standard_min
        normal_max = marker.standard_max_conventional if marker.standard_max_conventional is not None else marker.standard_max
        optimal_min = marker.optimal_min_conventional if marker.optimal_min_conventional is not None else marker.optimal_min
        optimal_max = marker.optimal_max_conventional if marker.optimal_max_conventional is not None else marker.optimal_max
        unit = marker.standard_unit or marker.international_unit or ''

    return {
        'normal_min': normal_min,
        'normal_max': normal_max,
        'optimal_min': optimal_min,
        'optimal_max': optimal_max,
        'unit': unit,
    }


def build_condition_marker_context(
    condition: HealthCondition,
    patient_values_by_name: Dict[str, float],
    unit_system_by_name: Dict[str, str],
    default_unit: str = 'standard'
) -> str:
    """
    Build a comprehensive textual context for all markers associated with the given condition.

    For each associated marker (low/high):
    - Include patient's value and both optimal and normal ranges (based on per-marker unit system, defaulting to 'standard').
    - Include marker background and discussion.
    - Include the relevant high/low narrative depending on the patient's direction:
        * If patient's value is above optimal → include HIGH narratives only.
        * If below optimal → include LOW narratives only.
        * If within optimal → include BOTH high and low narratives.
      If no patient value is provided, include BOTH for context.
    - Note the condition's association side for this marker (HIGH/LOW) if applicable.
    """
    lines: List[str] = []

    try:
        assoc_low = list(condition.associated_markers_low.all())
    except Exception:
        assoc_low = []
    try:
        assoc_high = list(condition.associated_markers_high.all())
    except Exception:
        assoc_high = []

    # Unique set preserving order: low then high additions
    seen = set()
    ordered_markers: List[Marker] = []
    for m in assoc_low + assoc_high:
        if m.id not in seen:
            ordered_markers.append(m)
            seen.add(m.id)

    if not ordered_markers:
        return "No associated markers defined for this condition."

    lines.append(f"Condition: {condition.display_name or condition.name or condition.condition_id}")
    if condition.background:
        lines.append(f"Condition background: {condition.background}")

    for marker in ordered_markers:
        val_present = marker.name in patient_values_by_name
        value = patient_values_by_name.get(marker.name)
        unit_system = unit_system_by_name.get(marker.name, default_unit)
        ranges = _resolve_ranges_for_marker(marker, unit_system)

        optimal_min = ranges['optimal_min']
        optimal_max = ranges['optimal_max']
        normal_min = ranges['normal_min']
        normal_max = ranges['normal_max']
        unit = ranges['unit'] or ''

        # Determine direction vs optimal
        in_optimal = (
            optimal_min is not None and optimal_max is not None and
            val_present and optimal_min <= value <= optimal_max
        )
        direction = None
        if val_present and optimal_min is not None and optimal_max is not None:
            if value < optimal_min:
                direction = 'low'
            elif value > optimal_max:
                direction = 'high'
            else:
                direction = 'optimal'

        # Condition association flags
        assoc_label_parts: List[str] = []
        if any(marker.id == m.id for m in assoc_low):
            assoc_label_parts.append('LOW')
        if any(marker.id == m.id for m in assoc_high):
            assoc_label_parts.append('HIGH')
        assoc_label = '/'.join(assoc_label_parts) if assoc_label_parts else '—'

        lines.append(f"\n[Marker: {marker.display_name} ({marker.name})]  Condition association: {assoc_label}")
        if val_present:
            lines.append(
                f" - Patient: {value}{(' ' + unit) if unit else ''} | Optimal: {optimal_min}-{optimal_max} | Normal: {normal_min}-{normal_max}"
            )
        else:
            lines.append(
                f" - Patient: (no value) | Optimal: {optimal_min}-{optimal_max} | Normal: {normal_min}-{normal_max}"
            )

        if marker.background:
            lines.append(f" - Background: {marker.background}")
        if marker.discussion:
            lines.append(f" - Discussion: {marker.discussion}")

        # Include relevant narrative
        include_low = False
        include_high = False
        if direction == 'low':
            include_low = True
        elif direction == 'high':
            include_high = True
        else:
            # within optimal or no value → include both for context
            include_low = True
            include_high = True

        if include_low:
            if marker.clinical_implications_low:
                lines.append(f" - When LOW: Clinical implications: {marker.clinical_implications_low}")
            if marker.other_conditions_low:
                lines.append(f" - When LOW: Other related conditions: {marker.other_conditions_low}")
            if marker.interfering_factors_falsely_decreased:
                lines.append(f" - When LOW: Interfering factors (falsely decreased): {marker.interfering_factors_falsely_decreased}")
            if marker.drug_causes_decreased:
                lines.append(f" - When LOW: Drug causes (decreased): {marker.drug_causes_decreased}")

        if include_high:
            if marker.clinical_implications_high:
                lines.append(f" - When HIGH: Clinical implications: {marker.clinical_implications_high}")
            if marker.other_conditions_high:
                lines.append(f" - When HIGH: Other related conditions: {marker.other_conditions_high}")
            if marker.interfering_factors_falsely_elevated:
                lines.append(f" - When HIGH: Interfering factors (falsely elevated): {marker.interfering_factors_falsely_elevated}")
            if marker.drug_causes_increased:
                lines.append(f" - When HIGH: Drug causes (increased): {marker.drug_causes_increased}")

    return "\n".join(lines)
