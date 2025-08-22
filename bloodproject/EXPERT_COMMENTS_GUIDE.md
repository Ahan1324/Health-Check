# Expert Comments for Health Condition Markers

This guide explains how to use the new expert comments feature that allows IFM CP functional medicine practitioners to provide commentary on which markers are most and least important when determining risk scores.

## Overview

The expert comments feature adds one new field to the `HealthCondition` model:
- `expert_comment_markers`: General commentary on marker importance for risk assessment

This comment is automatically included in risk score calculations when available.

## Database Structure

### New Field Added

```python
class HealthCondition(models.Model):
    # ... existing fields ...
    
    # Expert comments from IFM CP functional medicine practitioner
    expert_comment_markers = models.TextField(
        null=True, 
        blank=True,
        help_text="Expert commentary on which markers are most/least important for risk assessment"
    )
```

## How to Add Expert Comments

### 1. Django Admin Interface

1. Go to `http://localhost:8000/admin/`
2. Navigate to "Health conditions"
3. Click on any condition to edit
4. Scroll to the "Expert Commentary" section
5. Add your expert comments for low and/or high markers
6. Save the changes

### 2. Django Management Command

```bash
# Set expert comment for markers
python manage.py manage_health_condition_markers \
    --action set-expert-comment \
    --condition "iron_deficiency_anemia" \
    --expert-comment "Ferritin is the most critical marker for iron deficiency assessment, with levels < 30 ng/mL indicating depleted iron stores. HbA1c can be falsely elevated in iron deficiency but is less critical than ferritin levels."
```

### 3. Interactive Script

```bash
python manage_markers.py
```

Choose option 5 "Set expert comment for markers" and follow the prompts.

### 4. Programmatic API

```python
from bloodapp.utils import set_expert_comment

# Set expert comment for markers
result = set_expert_comment(
    condition_name="iron_deficiency_anemia",
    comment="Ferritin is the most critical marker for iron deficiency assessment, with levels < 30 ng/mL indicating depleted iron stores. HbA1c can be falsely elevated in iron deficiency but is less critical than ferritin levels."
)
```

## How Expert Comments Are Used in Risk Assessment

### Automatic Integration

When calculating risk scores, the system automatically includes expert comments in the AI prompt:

```python
from bloodapp.utils import get_risk_score_for_condition

# This will automatically include expert comments if available
risk_result = get_risk_score_for_condition(
    prompt="Patient has ferritin 15 ng/mL, hemoglobin 12 g/dL...",
    condition_name="iron_deficiency_anemia"  # Expert comments will be included
)
```

### Manual Retrieval

You can also retrieve expert comments manually:

```python
from bloodapp.utils import get_expert_comments_for_risk_assessment

expert_data = get_expert_comments_for_risk_assessment("iron_deficiency_anemia")
if expert_data['success'] and expert_data['has_expert_comments']:
    print(f"Expert comment: {expert_data['expert_comment_markers']}")
```

## Example Expert Comments

### Iron Deficiency Anemia

```
"Ferritin is the most critical marker for iron deficiency assessment, with levels < 30 ng/mL indicating depleted iron stores. Hemoglobin may remain normal until iron stores are severely depleted. HbA1c can be falsely elevated in iron deficiency due to shortened red blood cell lifespan, but this is less critical than the low ferritin levels. Transferrin saturation provides additional context but is less reliable than ferritin."
```

### Hypothyroidism

```
"TSH is the most sensitive marker for primary hypothyroidism, with levels > 4.5 mIU/L indicating hypothyroidism. Free T3 and Free T4 are the most important markers for assessing thyroid function. However, in secondary hypothyroidism, TSH may be low or normal. Reverse T3 can be elevated in stress and illness, indicating impaired T4 to T3 conversion."
```

### Type 2 Diabetes

```
"HbA1c ≥ 6.5% is diagnostic for diabetes, while 5.7-6.4% indicates prediabetes. Fasting glucose ≥ 126 mg/dL is also diagnostic. However, insulin resistance may be present for years before glucose levels become elevated. Fasting insulin levels can help identify early insulin resistance. Postprandial glucose levels may be elevated before fasting glucose, making them useful for early detection."
```

## Best Practices for Expert Comments

1. **Be Specific**: Mention which markers are most/least important and why
2. **Include Context**: Explain when certain markers might be misleading
3. **Prioritize**: Clearly indicate which markers should carry the most weight in risk assessment
4. **Consider Clinical Relevance**: Focus on markers that have the greatest impact on patient outcomes
5. **Keep Updated**: Review and update comments as new research emerges

## Integration with Risk Score Calculation

The expert comments are automatically included in the AI system prompt when calculating risk scores:

```
You are a medical assistant calculating risk scores.

EXPERT COMMENTARY (IFM CP Functional Medicine Practitioner):
Ferritin is the most critical marker for iron deficiency assessment, with levels < 30 ng/mL indicating depleted iron stores. HbA1c can be falsely elevated in iron deficiency but is less critical than ferritin levels.

Use this expert commentary to weight the importance of different markers when calculating the risk score.
```

This ensures that the AI model considers the expert's clinical judgment when determining risk scores and explanations.

## Viewing Expert Comments

### List All Conditions with Expert Comments

```bash
python manage.py manage_health_condition_markers --action list
```

### View Specific Condition

```bash
python manage_markers.py
# Choose option 2 "View markers for a specific condition"
```

### Programmatic Access

```python
from bloodapp.utils import list_all_conditions_with_markers

conditions = list_all_conditions_with_markers()
for condition in conditions:
    if condition['expert_comment_markers']:
        print(f"\n{condition['name']}:")
        print(f"  Expert comment: {condition['expert_comment_markers']}")
```

## Migration and Database Setup

The expert comment fields have been added to the database via migration. If you're setting up a new instance:

```bash
python manage.py migrate
```

This will create the new fields in your database schema.
