from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_POST
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt

import json
import os
import random
import string
import difflib
import threading
import time

from .forms import SignUpForm, LoginForm, BloodTestForm
from .models import Marker, HealthCondition, PatientProfile, AIAnalysisResult, RiskComputationTask
from .utils import (
    get_health_conditions_from_analysis,
    safe_json_loads,
    extract_text_from_pdf,
    map_pdf_values_to_markers,
    parse_signs_and_symptoms
)

def _random_username(prefix='demo'):
    return f"{prefix}_{''.join(random.choices(string.ascii_lowercase + string.digits, k=6))}"

def find_closest_condition_id(name, valid_ids):
    closest = difflib.get_close_matches(name.lower(), valid_ids, n=1, cutoff=0.5)
    return closest[0] if closest else None

def load_markers_data():
    return {"markers": list(Marker.objects.all().values())}

def load_health_conditions_data():
    return {"health_conditions": list(HealthCondition.objects.all().values())}

def clear_session(request):
    request.session.flush()
    return redirect('patient_info')

def save_ai_result(user, stage, analysis_data):
    """Save AI analysis results to database"""
    result, created = AIAnalysisResult.objects.get_or_create(
        user=user,
        stage=stage,
        defaults={'analysis_data': analysis_data, 'is_completed': True}
    )
    if not created:
        result.analysis_data = analysis_data
        result.is_completed = True
        result.save()
    return result

def get_ai_result(user, stage):
    """Get AI analysis results from database"""
    try:
        return AIAnalysisResult.objects.get(user=user, stage=stage)
    except AIAnalysisResult.DoesNotExist:
        return None

def analyze_patient_results_db(patient_values_by_name, unit_system_by_name):
    """Analyze using Marker DB choosing ranges based on per-marker unit system."""
    report_lines = []
    for m in Marker.objects.all():
        value = patient_values_by_name.get(m.name)
        if value is None:
            continue
        unit_sys = (unit_system_by_name.get(m.name) or 'standard').lower()
        # Choose ranges
        if unit_sys == 'international':
            normal_min = m.standard_min_international if m.standard_min_international is not None else m.standard_min
            normal_max = m.standard_max_international if m.standard_max_international is not None else m.standard_max
            optimal_min = m.optimal_min_international if m.optimal_min_international is not None else m.optimal_min
            optimal_max = m.optimal_max_international if m.optimal_max_international is not None else m.optimal_max
        else:
            normal_min = m.standard_min_conventional if m.standard_min_conventional is not None else m.standard_min
            normal_max = m.standard_max_conventional if m.standard_max_conventional is not None else m.standard_max
            optimal_min = m.optimal_min_conventional if m.optimal_min_conventional is not None else m.optimal_min
            optimal_max = m.optimal_max_conventional if m.optimal_max_conventional is not None else m.optimal_max
        in_normal = (normal_min is not None and normal_max is not None) and (normal_min <= value <= normal_max)
        in_optimal = (optimal_min is not None and optimal_max is not None) and (optimal_min <= value <= optimal_max)
        if not in_normal or not in_optimal:
            report_lines.append(f"[{m.name}]\n - Normal range: {normal_min}-{normal_max}\n - Optimal range: {optimal_min}-{optimal_max}\n - Patient has: {value} ({'intl' if unit_sys=='international' else 'std'})\n{m.background} {m.discussion}")
    return "\n\n".join(report_lines)

@login_required
def patient_info_view(request):
    """Stage 1: Submit patient information and blood test results dynamically from DB markers."""
    profile, created = PatientProfile.objects.get_or_create(user=request.user)
    if profile.current_stage not in ['patient_info', 'health_concerns', 'treatment_plans', 'completed']:
        profile.current_stage = 'patient_info'
        profile.save()

    # Default unit system preference stored in session
    default_unit = request.session.get('default_unit', 'standard')

    markers = list(Marker.objects.all().order_by('display_name').values(
        'id','name','display_name','standard_unit','international_unit',
        'standard_min_conventional','standard_max_conventional',
        'standard_min_international','standard_max_international',
        'optimal_min_conventional','optimal_max_conventional',
        'optimal_min_international','optimal_max_international'
    ))

    if request.method == 'POST':
        # Update default unit if provided
        default_unit = request.POST.get('default_unit', default_unit)
        request.session['default_unit'] = default_unit

        # Collect values
        patient_values = {}
        unit_systems = {}
        for m in markers:
            val_str = request.POST.get(f"marker_{m['id']}_value", '').strip()
            unit_sel = request.POST.get(f"marker_{m['id']}_unit", default_unit)
            if val_str:
                try:
                    patient_values[m['name']] = float(val_str)
                    unit_systems[m['name']] = unit_sel
                except ValueError:
                    continue

        # Save in session for later steps
        request.session['patient_values'] = patient_values
        request.session['unit_systems'] = unit_systems

        # Analyze
        analysis_report = analyze_patient_results_db(patient_values, unit_systems)

        # Save AI analysis result to database
        ai_result_data = {
            'patient_values': patient_values,
            'unit_systems': unit_systems,
            'analysis_report': analysis_report
        }
        save_ai_result(request.user, 'patient_info', ai_result_data)

        # Advance stage
        profile.current_stage = 'health_concerns'
        profile.save()
        return redirect('health_concerns')

    # GET: If already completed, show completed summary page
    ai_result = get_ai_result(request.user, 'patient_info')
    if ai_result:
        return render(request, 'bloodapp/patient_info_completed.html', {
            'ai_result': ai_result.analysis_data
        })

    return render(request, 'bloodapp/patient_info.html', {
        'markers': markers,
        'default_unit': default_unit,
    })

@require_POST
@login_required
def parse_pdf_markers(request):
    """Receive a PDF, extract text, map values to known markers via OpenAI, return JSON."""
    pdf_file = request.FILES.get('pdf')
    if not pdf_file:
        return JsonResponse({'error': 'No PDF uploaded'}, status=400)
    try:
        pdf_text = extract_text_from_pdf(pdf_file)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    try:
        mappings = map_pdf_values_to_markers(pdf_text)
        # Expected: [{name, value, unit_system}]
        return JsonResponse({'mappings': mappings})
    except Exception as e:
        return JsonResponse({'error': f'LLM mapping failed: {e}'}, status=500)

@login_required
def health_concerns_view(request):
    """Stage 2: View AI-generated health concerns"""
    profile, created = PatientProfile.objects.get_or_create(user=request.user)

    # Check if user can access this stage
    if profile.current_stage == 'patient_info':
        return redirect('patient_info')

    # Get saved patient info
    patient_info_result = get_ai_result(request.user, 'patient_info')
    if not patient_info_result:
        return redirect('patient_info')

    # Check if we already have health concerns analysis
    health_concerns_result = get_ai_result(request.user, 'health_concerns')

    if not health_concerns_result:
        # Generate health concerns analysis using AI
        patient_values = patient_info_result.analysis_data.get('patient_values', {})
        analysis_report = analyze_patient_results_db(
            patient_values,
            patient_info_result.analysis_data.get('unit_systems', {})
        )

        # Call LLM to get structured health conditions
        try:
            structured_conditions_json = get_health_conditions_from_analysis(analysis_report)
        except Exception:
            structured_conditions_json = ''
        try:
            likely_conditions_raw = safe_json_loads(structured_conditions_json)
        except Exception:
            likely_conditions_raw = []

        # Get valid condition IDs for matching
        valid_condition_ids = list(HealthCondition.objects.values_list('condition_id', flat=True))
        
        # Use enhanced matching with fallback for unmatched conditions
        from .utils import match_conditions_with_fallback, condition_id_to_display_name
        matched_conditions, other_conditions = match_conditions_with_fallback(
            likely_conditions_raw or [], valid_condition_ids
        )

        # Normalize matched conditions and attach display_name
        normalized = []
        for item in matched_conditions:
            cond_id = item['condition_id']
            try:
                hc = HealthCondition.objects.get(condition_id=cond_id)
                disp = hc.display_name or hc.name or condition_id_to_display_name(cond_id)
            except HealthCondition.DoesNotExist:
                disp = condition_id_to_display_name(cond_id)
            normalized.append({
                'condition_id': cond_id,
                'display_name': disp,
                'level_of_risk': item.get('level_of_risk') or '',
                'explanation': item.get('explanation') or '',
                'original_ai_id': item.get('original_ai_id')  # Keep track of original AI response
            })

        # Save AI analysis result to database
        ai_result_data = {
            'likely_conditions': normalized,
            'other_conditions': other_conditions,  # Add other conditions
            'analysis_report': analysis_report,
            'patient_values': patient_values,
        }
        save_ai_result(request.user, 'health_concerns', ai_result_data)

        # Update user's stage
        profile.current_stage = 'treatment_plans' if not normalized else 'health_concerns'
        profile.save()

        health_concerns_result = get_ai_result(request.user, 'health_concerns')

    # Store in session for quiz flow
    likely = health_concerns_result.analysis_data.get('likely_conditions', [])
    other_conditions = health_concerns_result.analysis_data.get('other_conditions', [])
    
    if isinstance(likely, str):
        # Attempt to parse if stored as string
        try:
            likely = json.loads(likely)
        except Exception:
            likely = []
    
    # Combine matched and other conditions for session storage
    all_conditions = likely + other_conditions
    request.session['at_risk_conditions'] = all_conditions
    
    # Compute quiz completion progress (only for matched conditions that need quizzes)
    quiz_completed_count = sum(1 for c in likely if c.get('detailed_analysis')) if likely else 0
    quiz_total_count = len(likely)  # Only count matched conditions that need quizzes
    all_detailed_done = quiz_total_count > 0 and quiz_completed_count == quiz_total_count

    return render(request, 'bloodapp/health_concerns.html', {
        'ai_result': {**health_concerns_result.analysis_data, 'likely_conditions': likely, 'other_conditions': other_conditions},
        'quiz_completed_count': quiz_completed_count,
        'quiz_total_count': quiz_total_count,
        'all_detailed_done': all_detailed_done,
    })

@login_required
def treatment_plans_view(request):
    """Stage 3: View AI-generated treatment plans"""
    profile, created = PatientProfile.objects.get_or_create(user=request.user)
    
    # Check if user can access this stage
    if profile.current_stage in ['patient_info', 'health_concerns']:
        return redirect('health_concerns')
    
    # Get saved health concerns
    health_concerns_result = get_ai_result(request.user, 'health_concerns')
    if not health_concerns_result:
        return redirect('health_concerns')
    
    # Check if we already have treatment plans
    treatment_plans_result = get_ai_result(request.user, 'treatment_plans')
    
    if not treatment_plans_result:
        # Generate treatment plans using AI based on detailed quiz outputs
        likely_conditions = health_concerns_result.analysis_data.get('likely_conditions', [])
        other_conditions = health_concerns_result.analysis_data.get('other_conditions', [])

        # Build detailed analyses payload from completed quizzes
        detailed_analyses = []
        for cond in likely_conditions:
            if cond.get('detailed_analysis') and cond.get('risk_score') is not None:
                detailed_analyses.append({
                    'condition_id': cond.get('condition_id'),
                    'risk_score': cond.get('risk_score'),
                    'detailed_explanation': cond.get('detailed_explanation')
                })

        # Predefined supplement list (example, replace with your real list)
        supplement_list = [
            {'name': 'Vitamin D3', 'link': 'https://example.com/vitamin-d3'},
            {'name': 'Iron Bisglycinate', 'link': 'https://example.com/iron-bisglycinate'},
            {'name': 'Magnesium Glycinate', 'link': 'https://example.com/magnesium-glycinate'},
            {'name': 'Omega-3 Fish Oil', 'link': 'https://example.com/omega-3'},
        ]

        from .utils import get_treatment_plan
        try:
            raw_plan = get_treatment_plan(detailed_analyses, supplement_list, other_conditions)
        except Exception as e:
            raw_plan = {'error': str(e)}

        # Normalize LLM plan keys to match template expectations
        def normalize_plan(plan_dict):
            if not isinstance(plan_dict, dict):
                return {'error': 'Invalid plan format'}
            # If already normalized, return as-is
            if any(k in plan_dict for k in ['lifestyle_recommendations', 'supplement_recommendations', 'dietary_recommendations']):
                return plan_dict
            normalized = {
                'lifestyle_recommendations': [],
                'supplement_recommendations': [],
                'dietary_recommendations': [],
                'follow_up_recommendations': plan_dict.get('Follow-up Recommendations') or plan_dict.get('follow_up_recommendations') or [],
                'summary': plan_dict.get('Summary') or plan_dict.get('summary')
            }
            # Lifestyle
            lifestyle_list = plan_dict.get('Lifestyle changes') or plan_dict.get('Lifestyle') or []
            for item in lifestyle_list or []:
                if isinstance(item, dict):
                    normalized['lifestyle_recommendations'].append(item)
                else:
                    normalized['lifestyle_recommendations'].append({'title': None, 'description': str(item)})
            # Diet/Nutrition
            nutrition_list = plan_dict.get('Nutrition') or plan_dict.get('Dietary') or []
            for item in nutrition_list or []:
                if isinstance(item, dict):
                    normalized['dietary_recommendations'].append(item)
                else:
                    normalized['dietary_recommendations'].append({'title': None, 'description': str(item)})
            # Supplements
            supplements_list = plan_dict.get('Supplements') or []
            for supp in supplements_list:
                if isinstance(supp, dict):
                    normalized['supplement_recommendations'].append(supp)
                else:
                    normalized['supplement_recommendations'].append({'name': str(supp)})
            return normalized

        plan_json = normalize_plan(raw_plan)

        # Save AI analysis result to database
        ai_result_data = {
            'treatment_plan': plan_json,
            'likely_conditions': likely_conditions
        }
        save_ai_result(request.user, 'treatment_plans', ai_result_data)

        # Update user's stage
        profile.current_stage = 'completed'
        profile.save()

        treatment_plans_result = get_ai_result(request.user, 'treatment_plans')
    
    return render(request, 'bloodapp/treatment_plans.html', {
        'ai_result': treatment_plans_result.analysis_data
    })

@login_required
def completed_view(request):
    """Stage 4: View completed analysis summary"""
    profile, created = PatientProfile.objects.get_or_create(user=request.user)
    
    # Check if user can access this stage
    if profile.current_stage != 'completed':
        return redirect('treatment_plans')
    
    # Get all saved results
    patient_info_result = get_ai_result(request.user, 'patient_info')
    health_concerns_result = get_ai_result(request.user, 'health_concerns')
    treatment_plans_result = get_ai_result(request.user, 'treatment_plans')

    if not all([patient_info_result, health_concerns_result, treatment_plans_result]):
        return redirect('patient_info')
    
    # Derive friendly display fields
    patient_name = (request.user.get_full_name() or '').strip() or request.user.username
    analysis_date = patient_info_result.created_at

    return render(request, 'bloodapp/completed.html', {
        'patient_info': patient_info_result.analysis_data,
        'health_concerns': health_concerns_result.analysis_data,
        'treatment_plans': treatment_plans_result.analysis_data,
        'patient_name': patient_name,
        'analysis_date': analysis_date,
    })


@login_required
def report_view(request):
    """Printable, detailed professional blood chemistry report."""
    profile, _ = PatientProfile.objects.get_or_create(user=request.user)

    # Fetch required analyses; if missing, redirect to start
    patient_info_result = get_ai_result(request.user, 'patient_info')
    health_concerns_result = get_ai_result(request.user, 'health_concerns')
    treatment_plans_result = get_ai_result(request.user, 'treatment_plans')
    if not patient_info_result:
        return redirect('patient_info')

    patient_name = (request.user.get_full_name() or '').strip() or request.user.username
    analysis_date = patient_info_result.created_at

    patient_values = patient_info_result.analysis_data.get('patient_values', {})
    unit_systems = patient_info_result.analysis_data.get('unit_systems', {})

    # Build marker display context with ranges and patient value positioning
    markers_ctx = []
    outside_normal_count = 0
    outside_optimal_count = 0
    for m in Marker.objects.all().order_by('display_name'):
        unit_sys = (unit_systems.get(m.name) or 'standard').lower()
        if unit_sys == 'international':
            normal_min = m.standard_min_international if m.standard_min_international is not None else m.standard_min
            normal_max = m.standard_max_international if m.standard_max_international is not None else m.standard_max
            optimal_min = m.optimal_min_international if m.optimal_min_international is not None else m.optimal_min
            optimal_max = m.optimal_max_international if m.optimal_max_international is not None else m.optimal_max
            units = m.international_unit or ''
        else:
            normal_min = m.standard_min_conventional if m.standard_min_conventional is not None else m.standard_min
            normal_max = m.standard_max_conventional if m.standard_max_conventional is not None else m.standard_max
            optimal_min = m.optimal_min_conventional if m.optimal_min_conventional is not None else m.optimal_min
            optimal_max = m.optimal_max_conventional if m.optimal_max_conventional is not None else m.optimal_max
            units = m.standard_unit or ''

        value = patient_values.get(m.name)
        normal_width = None
        opt_start_pct = None
        opt_width_pct = None
        patient_pos_pct = None
        severity = 0.0
        status_label = None
        in_optimal = False
        in_normal = False

        if normal_min is not None and normal_max is not None and normal_max > normal_min:
            normal_width = normal_max - normal_min
            if optimal_min is not None and optimal_max is not None and optimal_max > optimal_min:
                opt_start_pct = max(0, min(100, (optimal_min - normal_min) / normal_width * 100))
                opt_width_pct = max(0, min(100, (optimal_max - optimal_min) / normal_width * 100))
            if value is not None:
                # Position of patient value relative to normal range
                patient_pos_pct = (value - normal_min) / normal_width * 100
                if patient_pos_pct < 0:
                    patient_pos_pct = 0
                if patient_pos_pct > 100:
                    patient_pos_pct = 100

        if value is not None and normal_min is not None and normal_max is not None:
            in_normal = normal_min <= value <= normal_max
            if optimal_min is not None and optimal_max is not None and optimal_min <= optimal_max:
                in_optimal = optimal_min <= value <= optimal_max
            if in_optimal:
                severity = 0.0
                status_label = 'Optimal'
            elif in_normal:
                # Severity based on distance to nearest optimal bound
                if optimal_min is not None and optimal_max is not None and normal_width:
                    if value < optimal_min:
                        severity = min(1.0, (optimal_min - value) / normal_width)
                    elif value > optimal_max:
                        severity = min(1.0, (value - optimal_max) / normal_width)
                    else:
                        severity = 0.0
                else:
                    severity = 0.25
                status_label = 'Normal'
            else:
                # Outside normal: use distance beyond normal
                if normal_width:
                    if value < normal_min:
                        severity = min(1.5, (normal_min - value) / normal_width)
                    elif value > normal_max:
                        severity = min(1.5, (value - normal_max) / normal_width)
                    else:
                        severity = 1.0
                else:
                    severity = 1.0
                status_label = 'Out of Range'

        # Map severity to color hue (green -> red)
        # 0 => 120 (green), 1+ => 0 (red). Clamp 0..1.2
        hue = 120 - max(0.0, min(1.2, severity)) / 1.2 * 120
        patient_color = f"hsl({int(hue)}, 70%, 45%)"

        marker_entry = {
            'name': m.name,
            'display_name': m.display_name,
            'background': m.background,
            'units': units,
            'normal_min': normal_min,
            'normal_max': normal_max,
            'optimal_min': optimal_min,
            'optimal_max': optimal_max,
            'opt_start_pct': opt_start_pct,
            'opt_width_pct': opt_width_pct,
            'patient_value': value,
            'patient_pos_pct': patient_pos_pct,
            'patient_color': patient_color,
            'status_label': status_label,
            'in_optimal': in_optimal,
            'in_normal': in_normal,
            'severity': severity,
        }

        # Tally summary counts only when a patient value is present
        if value is not None:
            if not in_normal:
                outside_normal_count += 1
            elif not in_optimal:
                outside_optimal_count += 1

        markers_ctx.append(marker_entry)

    # Consider only markers that have a patient value
    analyzed_markers = [m for m in markers_ctx if m.get('patient_value') is not None]

    # Compute highlights: top deviations by severity
    highlights = sorted([m for m in analyzed_markers if m.get('severity') is not None], key=lambda x: x.get('severity', 0), reverse=True)[:5]

    # Health conditions section
    conditions_ctx = []
    if health_concerns_result:
        likely_conditions = health_concerns_result.analysis_data.get('likely_conditions', [])
        if isinstance(likely_conditions, str):
            try:
                likely_conditions = json.loads(likely_conditions)
            except Exception:
                likely_conditions = []
        for c in likely_conditions:
            cond_id = c.get('condition_id') or c.get('name') or c.get('display_name')
            display = c.get('display_name') or c.get('name') or cond_id or 'Health Condition'
            risk = c.get('risk_score')
            background = ''
            if cond_id:
                try:
                    hc = HealthCondition.objects.get(condition_id=cond_id)
                    background = hc.background or ''
                except HealthCondition.DoesNotExist:
                    background = ''
            # Color by risk
            risk_val = None
            try:
                risk_val = float(risk) if risk is not None else None
            except Exception:
                risk_val = None
            hue = 120
            if risk_val is not None:
                hue = int(120 - max(0, min(100, risk_val)) / 100 * 120)
            ring_color = f"hsl({hue}, 70%, 45%)"
            # SVG donut parameters
            radius = 45
            circumference = 2 * 3.1415926 * radius
            dash = (risk_val or 0) / 100.0 * circumference if risk_val is not None else 0
            conditions_ctx.append({
                'display_name': display,
                'risk_score': risk_val,
                'ring_color': ring_color,
                'background': background,
                'ring_radius': radius,
                'circumference': circumference,
                'ring_dash': dash,
            })

    # Sort conditions by risk descending for summary
    conditions_ctx = sorted(conditions_ctx, key=lambda c: (c['risk_score'] is not None, c['risk_score'] or -1), reverse=True)

    # Treatment plan
    plan_ctx = treatment_plans_result.analysis_data.get('treatment_plan') if treatment_plans_result else None

    return render(request, 'bloodapp/report.html', {
        'patient_name': patient_name,
        'analysis_date': analysis_date,
        'markers': analyzed_markers,
        'markers_count': len(analyzed_markers),
        'outside_normal_count': outside_normal_count,
        'outside_optimal_count': outside_optimal_count,
        'highlights': highlights,
        'conditions': conditions_ctx,
        'plan': plan_ctx,
    })


def quiz_condition(request, condition_name):
    try:
        condition = HealthCondition.objects.get(condition_id=condition_name)
    except HealthCondition.DoesNotExist:
        return HttpResponse("Condition not found", status=404)

    # Fetch saved patient inputs from DB
    if not request.user.is_authenticated:
        return HttpResponse("Unauthorized", status=401)
    patient_info_ai = get_ai_result(request.user, 'patient_info')
    if not patient_info_ai:
        return HttpResponse("Missing patient info. Please start over.", status=400)
    patient_values = patient_info_ai.analysis_data.get('patient_values', {})
    unit_systems = patient_info_ai.analysis_data.get('unit_systems', {})

    if request.method == 'POST':
        # Build structured responses from POST if any
        symptom_answers = {}
        for key, val in request.POST.items():
            if key.endswith('_answer'):
                symptom = key[:-7]
                info = request.POST.get(f"{symptom}_info", "").strip()
                symptom_answers[symptom] = {"answer": val, "info": info}

        # Persist the raw answers temporarily on the task for reproducibility
        task = RiskComputationTask.objects.create(
            user=request.user,
            condition_id=condition.condition_id,
            status='queued',
            result={
                'symptom_answers': symptom_answers
            }
        )

        # Mark this condition as in-progress in session (non-blocking for others)
        try:
            at_risk_conditions = request.session.get('at_risk_conditions', [])
            for cond in at_risk_conditions:
                if cond.get('condition_id') == condition.condition_id:
                    cond['in_progress'] = True
            request.session['at_risk_conditions'] = at_risk_conditions
            request.session.modified = True
        except Exception:
            pass

        # Mark in DB health concerns result as in-progress for this condition
        try:
            health_ai = get_ai_result(request.user, 'health_concerns')
            if health_ai:
                updated_list = []
                for cond in health_ai.analysis_data.get('likely_conditions', []):
                    if cond.get('condition_id') == condition.condition_id:
                        cond['in_progress'] = True
                    updated_list.append(cond)
                health_ai.analysis_data['likely_conditions'] = updated_list
                health_ai.save()
        except Exception:
            pass

        return redirect('quiz_condition', condition_name=condition.condition_id)

    # Parse signs and symptoms into individual bullet points
    symptoms_list = parse_signs_and_symptoms(condition.signs_and_symptoms)

    # Load any existing detailed analysis for this condition (to show saved results)
    existing_detail = None
    health_ai = get_ai_result(request.user, 'health_concerns')
    if health_ai:
        for cond in health_ai.analysis_data.get('likely_conditions', []):
            if cond.get('condition_id') == condition.condition_id and cond.get('detailed_analysis'):
                existing_detail = {
                    'risk_score': cond.get('risk_score'),
                    'detailed_explanation': cond.get('detailed_explanation'),
                }
                break

    return render(request, 'bloodapp/quiz.html', {
        'condition': condition,
        'symptoms': symptoms_list,
        'existing_detail': existing_detail,
    })


@login_required
def api_start_risk_task(request, condition_id):
    """Start or reuse a background task for computing risk for given condition.
    This endpoint collects latest quiz answers from the last queued task and kicks off computation synchronously for now, but returns task id immediately.
    """
    try:
        condition = HealthCondition.objects.get(condition_id=condition_id)
    except HealthCondition.DoesNotExist:
        return JsonResponse({'error': 'Condition not found'}, status=404)

    # Find the most recent queued task for this user+condition
    task = RiskComputationTask.objects.filter(user=request.user, condition_id=condition_id, status__in=['queued', 'running']).order_by('-created_at').first()
    if not task:
        # create empty task if none queued
        task = RiskComputationTask.objects.create(user=request.user, condition_id=condition_id, status='queued', result={})

    # Move to running and spawn background thread
    task.status = 'running'
    task.save()

    user_id = request.user.id

    def _compute():
        try:
            # Re-fetch objects inside thread
            t = RiskComputationTask.objects.get(id=task.id)
            cond = HealthCondition.objects.get(condition_id=condition_id)
            from django.contrib.auth import get_user_model
            User = get_user_model()
            user = User.objects.get(id=user_id)
            patient_info_ai = get_ai_result(user, 'patient_info')
            patient_values = patient_info_ai.analysis_data.get('patient_values', {}) if patient_info_ai else {}
            unit_systems = patient_info_ai.analysis_data.get('unit_systems', {}) if patient_info_ai else {}

            from .utils import build_condition_marker_context, get_risk_score_for_condition
            patient_markers_analysis = build_condition_marker_context(
                condition=cond,
                patient_values_by_name=patient_values,
                unit_system_by_name=unit_systems,
                default_unit='standard'
            )

            symptom_answers = {}
            if t.result and isinstance(t.result, dict):
                symptom_answers = t.result.get('symptom_answers') or {}
            formatted_symptoms = "\n".join(
                f"{symptom}: {data['answer'].capitalize()}" + (f" ({data.get('info')})" if data.get('info') else "")
                for symptom, data in (symptom_answers or {}).items()
            )
            additional_context = f"Quiz responses:\n{formatted_symptoms}\n\n" if symptom_answers else ""
            prompt = (
                f"Patient quiz for {cond.display_name} ({cond.condition_id}).\n"
                f"{additional_context}"
                f"Relevant markers context (associated high/low, background, discussion, and patient vs ranges):\n{patient_markers_analysis}\n"
                "Return JSON like: {'risk_score': 55, 'explanation': '...'}"
            )
            risk_json = get_risk_score_for_condition(prompt, condition_name=cond.condition_id)

            # Save result on task
            t.result = {'risk_score': risk_json.get('risk_score'), 'explanation': risk_json.get('explanation')}
            t.status = 'done'
            t.save()

            # Update DB saved health concerns result (clear in_progress and set final values)
            health_ai = get_ai_result(user, 'health_concerns')
            if health_ai:
                updated_list = []
                for c in health_ai.analysis_data.get('likely_conditions', []):
                    if c.get('condition_id') == cond.condition_id:
                        c['detailed_analysis'] = True
                        c['risk_score'] = risk_json.get('risk_score')
                        c['detailed_explanation'] = risk_json.get('explanation')
                        if 'in_progress' in c:
                            try:
                                del c['in_progress']
                            except Exception:
                                c['in_progress'] = False
                    updated_list.append(c)
                health_ai.analysis_data['likely_conditions'] = updated_list
                health_ai.save()

            # Advance stage if all done based on DB snapshot
            try:
                profile, _ = PatientProfile.objects.get_or_create(user=user)
                matched_conditions = [c for c in (health_ai.analysis_data.get('likely_conditions', []) if health_ai else []) if c.get('condition_id')]
                all_done = all(c.get('detailed_analysis') for c in matched_conditions) if matched_conditions else False
                profile.current_stage = 'treatment_plans' if all_done else 'health_concerns'
                profile.save()
            except Exception:
                pass
        except Exception as e:
            try:
                t = RiskComputationTask.objects.get(id=task.id)
                t.status = 'error'
                t.error = str(e)
                t.save()
            except Exception:
                pass

    threading.Thread(target=_compute, daemon=True).start()

    return JsonResponse({'task_id': task.id, 'status': 'running'})


@login_required
def api_risk_task_status(request, task_id):
    try:
        task = RiskComputationTask.objects.get(id=task_id, user=request.user)
    except RiskComputationTask.DoesNotExist:
        return JsonResponse({'error': 'Task not found'}, status=404)
    return JsonResponse({'task_id': task.id, 'status': task.status, 'result': task.result, 'error': task.error})

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
    user = request.user
    try:
        profile = PatientProfile.objects.get(user=user)
        if profile.current_stage == 'patient_info':
            return redirect('patient_info')
        elif profile.current_stage == 'health_concerns':
            return redirect('health_concerns')
        elif profile.current_stage == 'treatment_plans':
            return redirect('treatment_plans')
        elif profile.current_stage == 'completed':
            return redirect('completed')
        else:
            # Default to patient info if stage is unknown
            profile.current_stage = 'patient_info'
            profile.save()
            return redirect('patient_info')
    except PatientProfile.DoesNotExist:
        # Create profile and redirect to patient info
        PatientProfile.objects.create(user=user, current_stage='patient_info')
        return redirect('patient_info')


def demo_signup_view(request):
    # Create or reuse a demo user
    base_username = _random_username()
    username = base_username
    while User.objects.filter(username=username).exists():
        username = _random_username()
    email = f"{username}@demo.local"
    password = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
    user = User.objects.create_user(username=username, email=email, password=password)
    # Ensure profile exists
    PatientProfile.objects.get_or_create(user=user, defaults={'current_stage': 'patient_info'})
    login(request, user)
    return redirect('home')

def treatment_plan_view(request):
    # Only allow if all at-risk conditions have detailed_analysis True
    at_risk_conditions = request.session.get('at_risk_conditions', [])
    if not at_risk_conditions or not all(c.get('detailed_analysis') for c in at_risk_conditions):
        return redirect('home')

    # Prepare detailed analyses for LLM
    detailed_analyses = [
        {
            'condition_id': c['condition_id'],
            'risk_score': c.get('risk_score'),
            'detailed_explanation': c.get('detailed_explanation')
        }
        for c in at_risk_conditions
    ]

    # Predefined supplement list (example, replace with your real list)
    supplement_list = [
        {'name': 'Vitamin D3', 'link': 'https://example.com/vitamin-d3'},
        {'name': 'Iron Bisglycinate', 'link': 'https://example.com/iron-bisglycinate'},
        {'name': 'Magnesium Glycinate', 'link': 'https://example.com/magnesium-glycinate'},
        {'name': 'Omega-3 Fish Oil', 'link': 'https://example.com/omega-3'},
    ]

    from .utils import get_treatment_plan
    try:
        plan_json = get_treatment_plan(detailed_analyses, supplement_list)
    except Exception as e:
        return HttpResponse(f"Error generating treatment plan: {e}", status=500)

    # Store in session for possible re-display
    request.session['treatment_plan'] = plan_json
    return render(request, 'bloodapp/treatment_plan.html', {'plan': plan_json})


@csrf_exempt
def health_check(request):
    """Health check endpoint for Cloud Run"""
    try:
        # Check database connection
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        
        return JsonResponse({
            'status': 'healthy',
            'database': 'connected',
            'timestamp': time.time()
        })
    except Exception as e:
        return JsonResponse({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': time.time()
        }, status=500)
