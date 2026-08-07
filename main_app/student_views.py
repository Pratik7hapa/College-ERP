import json
import math
from datetime import datetime

from django.contrib import messages
from django.core.files.storage import FileSystemStorage
from django.http import HttpResponse, JsonResponse
from django.shortcuts import (HttpResponseRedirect, get_object_or_404,
                              redirect, render)
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt

from .forms import *
from .models import *


def predict_next_values(values, steps_ahead=1):
    """
    Given a list of values, predict the next 'steps_ahead' values using linear regression.
    Returns a list of predicted values.
    """
    n = len(values)
    if n < 2:
        # Not enough data to fit a trend, return the last value repeated
        if n == 1:
            return [values[-1]] * steps_ahead
        else:
            return [0.0] * steps_ahead

    # Convert to numerical indices
    x = list(range(n))
    y = values

    # Calculate slope (m) and intercept (c) for y = m*x + c
    sum_x = sum(x)
    sum_y = sum(y)
    sum_xy = sum(xi * yi for xi, yi in zip(x, y))
    sum_x2 = sum(xi * xi for xi in x)

    denominator = n * sum_x2 - sum_x * sum_x
    if denominator == 0:
        # Avoid division by zero (if all x are same, which shouldn't happen with indices)
        return [values[-1]] * steps_ahead

    m = (n * sum_xy - sum_x * sum_y) / denominator
    c = (sum_y - m * sum_x) / n

    # Predict for the next 'steps_ahead' steps
    predictions = []
    for i in range(steps_ahead):
        next_x = n + i
        predictions.append(m * next_x + c)

    return predictions


def student_home(request):
    student = get_object_or_404(Student, admin=request.user)
    total_subject = Subject.objects.filter(course=student.course).count()
    total_attendance = AttendanceReport.objects.filter(student=student).count()
    total_present = AttendanceReport.objects.filter(student=student, status=True).count()
    if total_attendance == 0:  # Don't divide. DivisionByZero
        percent_absent = percent_present = 0
    else:
        percent_present = math.floor((total_present/total_attendance) * 100)
        percent_absent = math.ceil(100 - percent_present)
    subject_name = []
    data_present = []
    data_absent = []
    subjects = Subject.objects.filter(course=student.course)
    for subject in subjects:
        attendance = Attendance.objects.filter(subject=subject)
        present_count = AttendanceReport.objects.filter(
            attendance__in=attendance, status=True, student=student).count()
        absent_count = AttendanceReport.objects.filter(
            attendance__in=attendance, status=False, student=student).count()
        subject_name.append(subject.name)
        data_present.append(present_count)
        data_absent.append(absent_count)
    context = {
        'total_attendance': total_attendance,
        'percent_present': percent_present,
        'percent_absent': percent_absent,
        'total_subject': total_subject,
        'subjects': subjects,
        'data_present': data_present,
        'data_absent': data_absent,
        'data_name': subject_name,
        'page_title': 'Student Homepage'

    }
    return render(request, 'student_template/erpnext_student_home.html', context)


@ csrf_exempt
def student_view_attendance(request):
    student = get_object_or_404(Student, admin=request.user)
    if request.method != 'POST':
        course = get_object_or_404(Course, id=student.course.id)
        context = {
            'subjects': Subject.objects.filter(course=course),
            'page_title': 'View Attendance'
        }
        return render(request, 'student_template/student_view_attendance.html', context)
    else:
        subject_id = request.POST.get('subject')
        start = request.POST.get('start_date')
        end = request.POST.get('end_date')
        try:
            subject = get_object_or_404(Subject, id=subject_id)
            start_date = datetime.strptime(start, "%Y-%m-%d")
            end_date = datetime.strptime(end, "%Y-%m-%d")
            attendance = Attendance.objects.filter(
                date__range=(start_date, end_date), subject=subject)
            attendance_reports = AttendanceReport.objects.filter(
                attendance__in=attendance, student=student)
            json_data = []
            for report in attendance_reports:
                data = {
                    "date":  str(report.attendance.date),
                    "status": report.status
                }
                json_data.append(data)
            return JsonResponse(json.dumps(json_data), safe=False)
        except Exception as e:
            return None


def student_apply_leave(request):
    form = LeaveReportStudentForm(request.POST or None)
    student = get_object_or_404(Student, admin_id=request.user.id)
    context = {
        'form': form,
        'leave_history': LeaveReportStudent.objects.filter(student=student),
        'page_title': 'Apply for leave'
    }
    if request.method == 'POST':
        if form.is_valid():
            try:
                obj = form.save(commit=False)
                obj.student = student
                obj.save()
                messages.success(
                    request, "Application for leave has been submitted for review")
                return redirect(reverse('student_apply_leave'))
            except Exception:
                messages.error(request, "Could not submit")
        else:
            messages.error(request, "Form has errors!")
    return render(request, "student_template/student_apply_leave.html", context)


def student_feedback(request):
    form = FeedbackStudentForm(request.POST or None)
    student = get_object_or_404(Student, admin_id=request.user.id)
    context = {
        'form': form,
        'feedbacks': FeedbackStudent.objects.filter(student=student),
        'page_title': 'Student Feedback'

    }
    if request.method == 'POST':
        if form.is_valid():
            try:
                obj = form.save(commit=False)
                obj.student = student
                obj.save()
                messages.success(
                    request, "Feedback submitted for review")
                return redirect(reverse('student_feedback'))
            except Exception:
                messages.error(request, "Could not Submit!")
        else:
            messages.error(request, "Form has errors!")
    return render(request, "student_template/student_feedback.html", context)


def student_view_profile(request):
    student = get_object_or_404(Student, admin=request.user)
    form = StudentEditForm(request.POST or None, request.FILES or None,
                           instance=student)
    context = {'form': form,
               'page_title': 'View/Edit Profile'
               }
    if request.method == 'POST':
        try:
            if form.is_valid():
                first_name = form.cleaned_data.get('first_name')
                last_name = form.cleaned_data.get('last_name')
                password = form.cleaned_data.get('password') or None
                address = form.cleaned_data.get('address')
                gender = form.cleaned_data.get('gender')
                passport = request.FILES.get('profile_pic') or None
                admin = student.admin
                if password != None:
                    admin.set_password(password)
                if passport != None:
                    fs = FileSystemStorage()
                    filename = fs.save(passport.name, passport)
                    passport_url = fs.url(filename)
                    admin.profile_pic = passport_url
                admin.first_name = first_name
                admin.last_name = last_name
                admin.address = address
                admin.gender = gender
                admin.save()
                student.save()
                messages.success(request, "Profile Updated!")
                return redirect(reverse('student_view_profile'))
            else:
                messages.error(request, "Invalid Data Provided")
        except Exception as e:
            messages.error(request, "Error Occured While Updating Profile " + str(e))

    return render(request, "student_template/student_view_profile.html", context)


@csrf_exempt
def student_fcmtoken(request):
    token = request.POST.get('token')
    student_user = get_object_or_404(CustomUser, id=request.user.id)
    try:
        student_user.fcm_token = token
        student_user.save()
        return HttpResponse("True")
    except Exception as e:
        return HttpResponse("False")


def student_view_notification(request):
    student = get_object_or_404(Student, admin=request.user)
    notifications = NotificationStudent.objects.filter(student=student)
    context = {
        'notifications': notifications,
        'page_title': "View Notifications"
    }
    return render(request, "student_template/student_view_notification.html", context)


def student_view_result(request):
    student = get_object_or_404(Student, admin=request.user)
    # Order results by created_at to have a time sequence for prediction
    results = StudentResult.objects.filter(student=student).order_by('created_at')

    # Prepare results with additional data
    results_with_data = []
    total_gpa = 0.0
    test_scores = []
    exam_scores = []
    for result in results:
        # Test (Internal Exam) out of 50, Exam (Final Exam) out of 50, total out of 100
        total_marks = result.test + result.exam
        percentage = total_marks  # out of 100
        gpa = (percentage / 100) * 4.0  # convert to 4.0 scale
        results_with_data.append({
            'result': result,
            'total_marks': total_marks,
            'percentage': percentage,
            'gpa': gpa
        })
        total_gpa += gpa
        test_scores.append(result.test)
        exam_scores.append(result.exam)

    overall_gpa = total_gpa / len(results_with_data) if results_with_data else 0.0

    total_subjects = Subject.objects.filter(course=student.course).count()
    completed_subjects = len(results_with_data)
    remaining_subjects = total_subjects - completed_subjects

    # AI-based GPA prediction for future subjects based on trend
    predicted_future_gpa = None
    if completed_subjects > 0:
        # Predict test and exam scores for the remaining subjects
        predicted_test_scores = predict_next_values(test_scores, steps_ahead=remaining_subjects) if test_scores else [0.0] * remaining_subjects
        predicted_exam_scores = predict_next_values(exam_scores, steps_ahead=remaining_subjects) if exam_scores else [0.0] * remaining_subjects

        # Calculate GPA for each predicted subject
        predicted_gpa_sum = 0.0
        for p_test, p_exam in zip(predicted_test_scores, predicted_exam_scores):
            # Each predicted score is out of 50, total out of 100
            p_total_marks = p_test + p_exam
            p_percentage = p_total_marks  # out of 100
            p_gpa = (p_percentage / 100) * 4.0
            predicted_gpa_sum += p_gpa

        # Predicted future GPA = (GPA of completed subjects + GPA of predicted remaining subjects) / total subjects
        predicted_future_gpa = (total_gpa + predicted_gpa_sum) / total_subjects if total_subjects > 0 else 0.0
    else:
        predicted_future_gpa = 0.0

    context = {
        'results_with_data': results_with_data,
        'overall_gpa': overall_gpa,
        'total_subjects': total_subjects,
        'remaining_subjects': remaining_subjects,
        'predicted_future_gpa': predicted_future_gpa,
        'page_title': "View Results"
    }

    # Handle target GPA form submission
    show_prediction_form = False
    show_prediction_result = False
    if request.method == 'POST' and 'target_gpa' in request.POST:
        try:
            target_gpa = float(request.POST.get('target_gpa'))
            if remaining_subjects > 0:
                required_gpa_per_subject = (target_gpa * total_subjects - overall_gpa * completed_subjects) / remaining_subjects
                # Convert required GPA per subject to total marks out of 100 (since each subject out of 100)
                required_total_marks_per_subject = required_gpa_per_subject * 25.0  # because GPA = (marks/100)*4 => marks = GPA*25
                # Split equally between Internal and Final Exam (each out of 50)
                required_internal_per_subject = required_total_marks_per_subject / 2.0
                required_final_per_subject = required_total_marks_per_subject / 2.0
            else:
                required_gpa_per_subject = None
                required_total_marks_per_subject = None
                required_internal_per_subject = None
                required_final_per_subject = None
            context.update({
                'target_gpa': target_gpa,
                'required_gpa_per_subject': required_gpa_per_subject,
                'required_total_marks_per_subject': required_total_marks_per_subject,
                'required_internal_per_subject': required_internal_per_subject,
                'required_final_per_subject': required_final_per_subject,
                'show_prediction_result': True
            })
        except (ValueError, TypeError):
            pass  # Ignore invalid input
    else:
        show_prediction_form = True

    context.update({
        'show_prediction_form': show_prediction_form,
        'show_prediction_result': show_prediction_result
    })

    return render(request, "student_template/student_view_result.html", context)


#library

def view_books(request):
    books = Book.objects.all()
    context = {
        'books': books,
        'page_title': "Library"
    }
    return render(request, "student_template/view_books.html", context)

