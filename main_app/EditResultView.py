from django.shortcuts import get_object_or_404, render, redirect
from django.views import View
from django.contrib import messages
from .models import Subject, Staff, Student, StudentResult
from .forms import EditResultForm
from django.urls import reverse


class EditResultView(View):
    def get(self, request, *args, **kwargs):
        resultForm = EditResultForm()
        staff = get_object_or_404(Staff, admin=request.user)
        resultForm.fields['subject'].queryset = Subject.objects.filter(staff=staff)
        context = {
            'form': resultForm,
            'page_title': "Edit Student's Result"
        }
        return render(request, "staff_template/edit_student_result.html", context)

    def post(self, request, *args, **kwargs):
        # Check if it's the result form submission
        if 'student' in request.POST:
            form = EditResultForm(request.POST)
            context = {'form': form, 'page_title': "Edit Student's Result"}
            if form.is_valid():
                try:
                    student = form.cleaned_data.get('student')
                    subject = form.cleaned_data.get('subject')
                    test = form.cleaned_data.get('test')
                    exam = form.cleaned_data.get('exam')
                    # Validating
                    result = StudentResult.objects.get(student=student, subject=subject)
                    result.exam = exam
                    result.test = test
                    result.save()
                    messages.success(request, "Result Updated")
                    # Calculate current stats for the subject
                    total_marks = test + exam
                    # Assuming each of test and exam is out of 100, so total out of 200
                    percentage = (total_marks / 200) * 100
                    gpa = (percentage / 100) * 4.0
                    total_subjects = Subject.objects.filter(course=student.course).count()
                    remaining_subjects = total_subjects - 1  # assuming only this subject is done so far
                    context.update({
                        'total_marks': total_marks,
                        'percentage': percentage,
                        'gpa': gpa,
                        'total_subjects': total_subjects,
                        'remaining_subjects': remaining_subjects,
                        'student_id': student.id,
                        'subject_id': subject.id,
                        'show_prediction_form': True
                    })
                except Exception as e:
                    messages.warning(request, "Result Could Not Be Updated")
            else:
                messages.warning(request, "Result Could Not Be Updated")
            return render(request, "staff_template/edit_student_result.html", context)
        # Check if it's the prediction form submission
        elif 'target_gpa' in request.POST:
            try:
                target_gpa = float(request.POST.get('target_gpa'))
                student_id = request.POST.get('student_id')
                subject_id = request.POST.get('subject_id')
                student = Student.objects.get(id=student_id)
                subject = Subject.objects.get(id=subject_id)
                # Recalculate current stats (we need the test and exam from the saved result)
                result = StudentResult.objects.get(student=student, subject=subject)
                test = result.test
                exam = result.exam
                total_marks = test + exam
                percentage = (total_marks / 200) * 100
                gpa = (percentage / 100) * 4.0
                total_subjects = Subject.objects.filter(course=student.course).count()
                remaining_subjects = total_subjects - 1  # assuming only this subject is done so far
                if remaining_subjects > 0:
                    required_gpa_per_subject = (target_gpa * total_subjects - gpa) / remaining_subjects
                    # Convert GPA to percentage: GPA = (percentage/100)*4  => percentage = (GPA/4)*100
                    required_percentage = (required_gpa_per_subject / 4.0) * 100
                    # Convert percentage to marks out of 200
                    required_marks = (required_percentage / 100) * 200
                    # We'll split equally between test and exam? We don't know the split, so show total required marks for the subject
                    # But note: the student might have multiple remaining subjects, so we are giving the average required marks per subject
                    # We'll show the average required marks per subject (out of 200) for each remaining subject.
                    # Also, we can show the required percentage per subject.
                else:
                    required_marks = None
                    required_gpa_per_subject = None
                context = {
                    'target_gpa': target_gpa,
                    'gpa': gpa,
                    'total_marks': total_marks,
                    'percentage': percentage,
                    'required_marks': required_marks,
                    'required_gpa_per_subject': required_gpa_per_subject,
                    'total_subjects': total_subjects,
                    'remaining_subjects': remaining_subjects,
                    'student': student,
                    'subject': subject,
                    'show_prediction_result': True
                }
                return render(request, "staff_template/edit_student_result.html", context)
            except (ValueError, Student.DoesNotExist, Subject.DoesNotExist, StudentResult.DoesNotExist) as e:
                messages.error(request, "Error in calculation: " + str(e))
                return redirect(reverse('edit_student_result'))
        else:
            # Fallback
            form = EditResultForm()
            context = {'form': form, 'page_title': "Edit Student's Result"}
            return render(request, "staff_template/edit_student_result.html", context)
