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
                    # Assuming each of test and exam is out of 50, so total out of 100
                    percentage = total_marks  # since out of 100
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
                        'subject_id': subject.id
                    })
                except Exception as e:
                    messages.warning(request, "Result Could Not Be Updated")
            else:
                messages.warning(request, "Result Could Not Be Updated")
            return render(request, "staff_template/edit_student_result.html", context)
        else:
            # Fallback
            form = EditResultForm()
            context = {'form': form, 'page_title': "Edit Student's Result"}
            return render(request, "staff_template/edit_student_result.html", context)