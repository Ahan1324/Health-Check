from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from .forms import SignUpForm, LoginForm
from .forms import BloodTestForm
import json
import os
from django.conf import settings
from .utils import get_health_conditions_from_analysis
from .utils import safe_json_loads
from django.http import HttpResponse, JsonResponse

import difflib
from .models import Marker, HealthCondition

def find_closest_condition_id(name, valid_ids):
    closest = difflib.get_close_matches(name.lower(), valid_ids, n=1, cutoff=0.5)
    return closest[0] if closest else None

def load_markers_data():
    return {"markers": list(Marker.objects.all().values())}

def load_health_conditions_data():
    return {"health_conditions": list(HealthCondition.objects.all().values())}

from django.shortcuts import redirect

def clear_session(request):
    request.session.flush()
    return redirect('submit_blood_test')


def analyze_patient_results(markers_data, patient_data):
    markers = markers_data["markers"]
    patient_results = {k: v for k, v in patient_data.items() if k != "patient_name"}
    report = f"Analysis for patient: {patient_data.get('patient_name', 'Unknown')}\n"

    # First: out of normal
    for marker in markers:
        marker_id = marker["marker_id"]
        patient_value = patient_results.get(marker_id)
        if patient_value is not None:
            normal_min = marker["ranges"]["standard_us"]["min"]
            normal_max = marker["ranges"]["standard_us"]["max"]
            if patient_value < normal_min or patient_value > normal_max:
                report += build_marker_report(marker, patient_value)

    # Then: out of optimal only
    for marker in markers:
        marker_id = marker["marker_id"]
        patient_value = patient_results.get(marker_id)
        if patient_value is not None:
            normal_min = marker["ranges"]["standard_us"]["min"]
            normal_max = marker["ranges"]["standard_us"]["max"]
            optimal_min = marker["ranges"]["optimal_us"]["min"]
            optimal_max = marker["ranges"]["optimal_us"]["max"]
            if (normal_min <= patient_value <= normal_max) and not (optimal_min <= patient_value <= optimal_max):
                report += build_marker_report(marker, patient_value)
    return report

def build_marker_report(marker, patient_value):
    marker_id = marker["marker_id"]
    background = marker["background"]
    discussion = marker["discussion"]
    ranges = marker["ranges"]

    normal_min = ranges["standard_us"]["min"]
    normal_max = ranges["standard_us"]["max"]
    optimal_min = ranges["optimal_us"]["min"]
    optimal_max = ranges["optimal_us"]["max"]

    report = ""
    in_normal = normal_min <= patient_value <= normal_max
    in_optimal = optimal_min <= patient_value <= optimal_max

    if not in_normal:
        level_type = "below normal" if patient_value < normal_min else "above normal"
    else:
        level_type = "below optimal" if patient_value < optimal_min else "above optimal"

    report += f"\n[{marker_id}] is {level_type}.\n"
    report += f" - Normal range: {normal_min}-{normal_max}\n"
    report += f" - Optimal range: {optimal_min}-{optimal_max}\n"
    report += f" - Patient has: {patient_value}\n"
    report += f"{background} {discussion}\n"

    if patient_value < normal_min:
        if marker["low"]:
            report += "Possible clinical implications:\n"
            for item in marker["low"]:
                report += f" - {item['clinical_implication']}: {item['explanation']}\n"
        if marker["other_low"]:
            report += "Other considerations (low): " + ", ".join(marker["other_low"]) + "\n"
        if marker["interfering_factors"]["falsely_decreased"]:
            report += "Factors that may falsely decrease this marker: " + ", ".join(marker["interfering_factors"]["falsely_decreased"]) + "\n"
        if marker["drug_associations"]["decreased"]:
            report += "Drugs that may decrease this marker: " + ", ".join(marker["drug_associations"]["decreased"]) + "\n"
    elif patient_value > normal_max:
        if marker["high"]:
            report += "Possible clinical implications:\n"
            for item in marker["high"]:
                report += f" - {item['clinical_implication']}: {item['explanation']}\n"
        if marker["other_high"]:
            report += "Other considerations (high): " + ", ".join(marker["other_high"]) + "\n"
        if marker["interfering_factors"]["falsely_increased"]:
            report += "Factors that may falsely increase this marker: " + ", ".join(marker["interfering_factors"]["falsely_increased"]) + "\n"
        if marker["drug_associations"]["increased"]:
            report += "Drugs that may increase this marker: " + ", ".join(marker["drug_associations"]["increased"]) + "\n"
    return report

def submit_blood_test(request):
    if request.method == 'POST':
        form = BloodTestForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data

            # Save patient data
            output_dir = os.path.join(settings.BASE_DIR, 'blood_data')
            os.makedirs(output_dir, exist_ok=True)
            file_path = os.path.join(output_dir, f"{data['patient_name']}.json")
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=4)

            # Analysis of markers
            markers_data = load_markers_data()
            analysis_report = analyze_patient_results(markers_data, data)

            # 💥 Call LLM to get structured health conditions
            structured_conditions_json = get_health_conditions_from_analysis(analysis_report)
            likely_conditions = safe_json_loads(structured_conditions_json)

            print("=== RAW GPT RESPONSE ===")
            print(structured_conditions_json)

            # Store in session
            request.session['patient_name'] = data['patient_name']
            request.session['analysis'] = analysis_report
            request.session['at_risk_conditions'] = likely_conditions
            request.session["patient_data"] = data

            # Pass to template
            return render(request, 'bloodapp/success.html', {
                'patient': data['patient_name'],
                'analysis': analysis_report,
                'at_risk_conditions': likely_conditions
            })

    else:
        form = BloodTestForm()
        patient = request.session.get('patient_name')
        analysis = request.session.get('analysis')
        at_risk_conditions = request.session.get('at_risk_conditions')

        if patient and analysis and at_risk_conditions:
            return render(request, 'bloodapp/success.html', {
                'patient': patient,
                'analysis': analysis,
                'at_risk_conditions': at_risk_conditions
            })
        else:
            return render(request, 'bloodapp/blood_test_form.html', {'form': form})





def quiz_condition(request, condition_name):
    try:
        condition = HealthCondition.objects.get(condition_id=condition_name)
    except HealthCondition.DoesNotExist:
        return HttpResponse("Condition not found", status=404)

    patient_data = request.session.get("patient_data")
    if not patient_data:
        return HttpResponse("Session expired or patient data missing. Please start over.", status=400)

    if request.method == 'POST':
        # Build structured responses
        symptom_answers = {}
        for symptom in condition.signs_and_symptoms:
            answer = request.POST.get(f"{symptom}_answer")
            info = request.POST.get(f"{symptom}_info", "").strip()
            symptom_answers[symptom] = {
                "answer": answer,
                "info": info
            }

        # Convert for prompt like: "Fatigue: Yes (onset after exercise)"
        formatted_symptoms = "\n".join(
            f"{symptom}: {data['answer'].capitalize()}"
            + (f" ({data['info']})" if data['info'] else "")
            for symptom, data in symptom_answers.items()
        )

        additional_context = f"Quiz responses:\n{formatted_symptoms}\n\n"

        markers_data = load_markers_data()
        patient_data = request.session.get("patient_data")
        patient_markers_analysis = analyze_patient_results(markers_data, patient_data)

        prompt = (
            f"Patient quiz for {condition_name}.\n"
            f"{additional_context}"
            f"Markers analysis:\n{patient_markers_analysis}\n"
            "Return JSON like: {'risk_score': 85, 'explanation': '...'}"
        )

        from .utils import get_risk_score_for_condition
        risk_json = get_risk_score_for_condition(prompt)

        # Store
        for cond in request.session["at_risk_conditions"]:
            if cond["condition_id"] == condition_name:
                cond["detailed_analysis"] = True
                cond["risk_score"] = risk_json["risk_score"]
                cond["detailed_explanation"] = risk_json["explanation"]
        request.session.modified = True

        return redirect('submit_blood_test')

    return render(request, 'bloodapp/quiz.html', {'condition': condition})

def signup_view(request):
    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("home")
    else:
        form = SignUpForm()
    return render(request, "bloodapp/signup.html", {"form": form})

def login_view(request):
    if request.method == "POST":
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect("home")
    else:
        form = LoginForm()
    return render(request, "bloodapp/login.html", {"form": form})

def logout_view(request):
    logout(request)
    return redirect("login")

@login_required
def home_view(request):
    return render(request, "bloodapp/home.html")
