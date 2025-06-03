from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import PeerReviewQuestionForm, EditStudentForm, UpdatePasswordForm
import csv
import io
import secrets
import string
import random
from django.http import HttpResponse
from .models import CustomUser, Student, Course, Assignment, Submission, PeerReview, PeerReviewTemplate, PeerReviewQuestion, PeerReviewAnswer, ResendRequest
from .forms import AssignmentForm, SubmissionForm, PeerReviewTemplateForm, PeerReviewQuestionFormSet, EvaluationForm, PeerReviewAnswerFormSet, PeerReviewAnswerForm
from django.utils import timezone
from django.contrib.auth.views import LogoutView
from django.forms import modelformset_factory
from django.db import models
import random
from django.contrib.auth import logout


def home(request):
   return render(request, 'evaluation/home.html', {'is_home': True})

@login_required
def upload_students(request):
    if request.user.role != 'teacher':
        messages.error(request, "Only teachers can upload students.")
        return redirect('dashboard')
    
    if request.method == 'POST':
        csv_file = request.FILES.get('csv_file')
        course_id = request.POST.get('course_id')
        
        if not csv_file or not course_id:
            messages.error(request, "Please upload a CSV and select a course.")
            return render(request, 'evaluation/upload_students.html')
        
        try:
            course = Course.objects.get(id=course_id, teacher=request.user)
            decoded_file = csv_file.read().decode('utf-8')
            csv_reader = csv.DictReader(io.StringIO(decoded_file))
            required_headers = ['username', 'email', 'first_name', 'last_name', 'roll_no']
            if not all(header in csv_reader.fieldnames for header in required_headers):
                messages.error(request, "CSV missing required columns: username, email, first_name, last_name, roll_no.")
                return render(request, 'evaluation/upload_students.html', {'courses': Course.objects.filter(teacher=request.user)})
            
            credentials = []
            for row in csv_reader:
                # Validate row data
                if not all(row.get(h, '').strip() for h in required_headers):
                    messages.error(request, f"Missing data in row: {row}")
                    continue

                password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(12))
                user, created = CustomUser.objects.get_or_create(
                    username=row['username'],
                    defaults={
                        'email': row['email'],
                        'first_name': row['first_name'],
                        'last_name': row['last_name'],
                        'roll_no': row['roll_no'],
                        'role': 'student',
                    }
                )
                if created:
                    user.set_password(password)
                    user.save()
                    Student.objects.create(user=user, course=course, roll_no=row['roll_no'])
                    credentials.append({'username': row['username'], 'email': row['email'], 'password': password})
                else:
                    messages.warning(request, f"User {row['username']} already exists. Skipped.")
            
            if credentials:
                response = HttpResponse(content_type='text/csv')
                response['Content-Disposition'] = 'attachment; filename="credentials.csv"'
                writer = csv.writer(response)
                writer.writerow(['username', 'email', 'password'])
                for cred in credentials:
                    writer.writerow([cred['username'], cred['email'], cred['password']])
                return response
            else:
                messages.info(request, "No new students were added.")
                return render(request, 'evaluation/upload_students.html', {'courses': Course.objects.filter(teacher=request.user)})
                
        except Exception as e:
            messages.error(request, f"Error: {str(e)}")
            return render(request, 'evaluation/upload_students.html', {'courses': Course.objects.filter(teacher=request.user)})
    
    courses = Course.objects.filter(teacher=request.user)
    return render(request, 'evaluation/upload_students.html', {'courses': courses})

@login_required
def dashboard(request):
    if request.user.role == 'teacher':
        if request.method == 'POST':
            course_name = request.POST.get('course_name')
            if course_name:
                # Prevent duplicate course names for the same teacher (optional)
                if not Course.objects.filter(name=course_name, teacher=request.user).exists():
                    Course.objects.create(name=course_name, teacher=request.user)
                    messages.success(request, f"Course '{course_name}' added successfully!")
                else:
                    messages.warning(request, f"You already have a course named '{course_name}'.")
                return redirect('dashboard')
        courses = Course.objects.filter(teacher=request.user)
        assignments = Assignment.objects.filter(course__teacher=request.user)
        chart_labels = []
        chart_data = []

        for assignment in assignments:
            chart_labels.append(assignment.title)
            chart_data.append(Submission.objects.filter(assignment=assignment).count())

        return render(request, 'evaluation/teacher_dashboard.html', {
            'courses': courses,
            'assignments': assignments,
            'chart_labels': chart_labels,
            'chart_data': chart_data,
        })
    elif request.user.role == 'student':
        try:
            student = Student.objects.get(user=request.user)
            courses = Course.objects.filter(students=student)
            assignments = Assignment.objects.filter(
                course=student.course,
                is_published=True,
            )
            now = timezone.now()
            overdue_assignments = []
            for assignment in assignments:
                assignment.is_submitted = Submission.objects.filter(assignment=assignment, student=student).exists()
                assignment.is_overdue = (assignment.deadline < now) and not assignment.is_submitted
                assignment.is_pending = (assignment.deadline > now) and not assignment.is_submitted
                if assignment.is_overdue:
                    overdue_assignments.append(assignment)
            
            upcoming_deadlines = [a for a in assignments if a.deadline > now]
            assigned_reviews = PeerReview.objects.filter(reviewer=student)
            all_reviews = PeerReview.objects.filter(reviewer=student).select_related('submission__assignment')
            pending_reviews = all_reviews.filter(completed=False)
            completed_reviews = all_reviews.filter(completed=True)
            oldest_review_deadline = None
            if pending_reviews:
                oldest_review_deadline = pending_reviews[0].submission.assignment.deadline
            resend_requests = ResendRequest.objects.filter(
                review__reviewer=student, 
                is_resolved=False
            )
            return render(request, 'evaluation/student_dashboard.html', {
                'courses': courses,
                'assignments': assignments,
                'overdue_assignments': overdue_assignments,
                'assigned_reviews': assigned_reviews,
                'now': now,
                'upcoming_deadlines': upcoming_deadlines,
                'oldest_review_deadline': oldest_review_deadline,
                'pending_reviews': pending_reviews,
                'completed_reviews': completed_reviews,
                'all_reviews': all_reviews,
                'resend_requests': resend_requests,
            })
        except Student.DoesNotExist:
            messages.error(request, "Student profile not found. Please contact your teacher.")
            return render(request, 'evaluation/registration/login.html', {'courses': []})
    else:
        messages.error(request, "Invalid user role.")
        return render(request, 'evaluation/registration/login.html', {'courses': []})


@login_required
def manage_students(request):
    if request.user.role != 'teacher':
        messages.error(request, "Only teachers can manage students.")
        return redirect('dashboard')
    
    courses = Course.objects.filter(teacher=request.user)
    students = Student.objects.filter(course__in=courses).select_related('user', 'course')

    if request.method == 'POST':
        if 'delete_all' in request.POST:
            # Delete all students for this teacher's courses
            for student in students:
                student.user.delete()
            messages.success(request, "All students deleted successfully.")
            return redirect('manage_students')
        elif 'csv_file' in request.FILES and 'course_id' in request.POST:
            csv_file = request.FILES['csv_file']
            course_id = request.POST['course_id']
            try:
                course = Course.objects.get(id=course_id, teacher=request.user)
                decoded_file = csv_file.read().decode('utf-8')
                csv_reader = csv.DictReader(io.StringIO(decoded_file))
                required_headers = ['username', 'email', 'first_name', 'last_name', 'roll_no']
                if not all(header in csv_reader.fieldnames for header in required_headers):
                    messages.error(request, "CSV missing required columns: username, email, first_name, last_name, roll_no.")
                    return redirect('manage_students')
                credentials = []
                existing_passwords = set(CustomUser.objects.values_list('password', flat=True))
                for row in csv_reader:
                    if not all(row.get(h, '').strip() for h in required_headers):
                        messages.error(request, f"Missing data in row: {row}")
                        continue
                    user, created = CustomUser.objects.get_or_create(
                        username=row['username'],
                        defaults={
                            'email': row['email'],
                            'first_name': row['first_name'],
                            'last_name': row['last_name'],
                            'roll_no': row['roll_no'],
                            'role': 'student',
                        }
                    )
                    if created:
                        # Generate a unique password
                        while True:
                            password = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
                            if password not in existing_passwords:
                                break
                        user.set_password(password)
                        user.save()
                        Student.objects.create(user=user, course=course, roll_no=row['roll_no'])
                        credentials.append({'username': row['username'], 'email': row['email'], 'password': password})
                    else:
                        messages.warning(request, f"User {row['username']} already exists. Skipped.")
                if credentials:
                    response = HttpResponse(content_type='text/csv')
                    response['Content-Disposition'] = 'attachment; filename="credentials.csv"'
                    writer = csv.writer(response)
                    writer.writerow(['username', 'email', 'password'])
                    for cred in credentials:
                        writer.writerow([cred['username'], cred['email'], cred['password']])
                    return response
                else:
                    messages.info(request, "No new students were added.")
            except Exception as e:
                messages.error(request, f"Error: {str(e)}")
            return redirect('manage_students')

    return render(request, 'evaluation/manage_students.html', {
        'courses': courses,
        'students': students,
    })

@login_required
def edit_student(request, student_id):
    student = get_object_or_404(Student, id=student_id)
    if request.user.role != 'teacher' or student.course.teacher != request.user:
        messages.error(request, "Not authorized.")
        return redirect('manage_students')
    user = student.user
    if request.method == 'POST':
        form = EditStudentForm(request.POST, instance=student, user_instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, "Student updated successfully.")
            return redirect('manage_students')
    else:
        form = EditStudentForm(instance=student, user_instance=user)
    return render(request, 'evaluation/edit_student.html', {'form': form, 'student': student})

@login_required
def delete_student(request, student_id):
    if request.method == 'POST':
        try:
            student = Student.objects.get(id=student_id)
            student.user.delete()
            messages.success(request, "Student deleted successfully.")
        except Student.DoesNotExist:
            messages.error(request, "Student not found.")
    return redirect('manage_students')

def help(request):
    return render(request, 'evaluation/help.html')

@login_required
def assignment_dashboard(request):
    if request.user.role == 'teacher':
        courses = Course.objects.filter(teacher=request.user)
        assignments = Assignment.objects.filter(course__in=courses)
        return render(request, 'evaluation/assignment_dashboard.html', {'assignments': assignments})
    elif request.user.role == 'student':
        student = Student.objects.get(user=request.user)
        assignments = Assignment.objects.filter(
            course=student.course,
            is_published=True,
        )
        now = timezone.now()
        for assignment in assignments:
            assignment.is_submitted = Submission.objects.filter(assignment=assignment, student=student).exists()
            assignment.is_overdue = (assignment.deadline < now) and not assignment.is_submitted
        return render(request, 'evaluation/student_assignments.html', {'assignments': assignments})

@login_required
def create_assignment(request):
    if request.user.role != 'teacher':
        messages.error(request, "Only teachers can create assignments.")
        return redirect('assignment_dashboard')
    if request.method == 'POST':
        form = AssignmentForm(request.POST, request.FILES)
        if form.is_valid():
            assignment = form.save(commit=False)
            assignment.save()
            messages.success(request, "Assignment created successfully!")
            return redirect('assignment_dashboard')
    else:
        form = AssignmentForm()
    return render(request, 'evaluation/create_assignment.html', {'form': form})

@login_required
def edit_assignment(request, pk):
    assignment = get_object_or_404(Assignment, pk=pk)
    if request.user.role != 'teacher' or assignment.course.teacher != request.user:
        messages.error(request, "Not authorized.")
        return redirect('assignment_dashboard')
    if request.method == 'POST':
        form = AssignmentForm(request.POST, request.FILES, instance=assignment)
        if form.is_valid():
            form.save()
            messages.success(request, "Assignment updated!")
            return redirect('assignment_dashboard')
    else:
        form = AssignmentForm(instance=assignment)
    return render(request, 'evaluation/edit_assignment.html', {'form': form, 'assignment': assignment})

@login_required
def delete_assignment(request, pk):
    assignment = get_object_or_404(Assignment, pk=pk)
    if request.user.role == 'teacher' and assignment.course.teacher == request.user:
        assignment.delete()
        messages.success(request, "Assignment deleted.")
    else:
        messages.error(request, "Not authorized.")
    return redirect('assignment_dashboard')

@login_required
def assignment_submissions(request, pk):
    assignment = get_object_or_404(Assignment, pk=pk)
    if request.user.role == 'teacher' and assignment.course.teacher == request.user:
        submissions = Submission.objects.filter(assignment=assignment)
        return render(request, 'evaluation/assignment_submissions.html', {'assignment': assignment, 'submissions': submissions})
    else:
        messages.error(request, "Not authorized.")
        return redirect('assignment_dashboard')

@login_required
def submit_assignment(request, pk):
    assignment = get_object_or_404(Assignment, pk=pk)
    
    # Check if deadline has passed
    if assignment.is_locked():
        messages.error(request, "Submission deadline has passed.")
        return redirect('dashboard')
    
    # Prevent multiple submissions
    student = Student.objects.get(user=request.user)
    if Submission.objects.filter(assignment=assignment, student=student).exists():
        messages.info(request, "You have already submitted this assignment. Multiple submissions are not allowed.")
        return redirect('student_assignments', student_id=student.id)
    
    if request.method == 'POST':
        form = SubmissionForm(request.POST, request.FILES)
        if form.is_valid():
            Submission.objects.create(
                assignment=assignment, student=student, pdf=form.cleaned_data['pdf']
            )
            messages.success(request, "Assignment submitted!")
            return redirect('student_assignments', student_id=student.id)
    else:
        form = SubmissionForm()
    return render(request, 'evaluation/submit_assignment.html', {'form': form, 'assignment': assignment})


@login_required
def student_assignments(request, student_id):
    student = get_object_or_404(Student, id=student_id)
    if request.user != student.user:
        messages.error(request, "You are not authorized to view this page.")
        return redirect('dashboard')
    assignments = Assignment.objects.filter(
        course=student.course,
        is_published=True,
    )
    now = timezone.now()
    active_assignments = []
    submitted_count = 0
    urgent_count = 0
    for assignment in assignments:
        assignment.is_submitted = Submission.objects.filter(assignment=assignment, student=student).exists()
        assignment.is_past_deadline = assignment.deadline < now
        assignment.is_urgent = (assignment.deadline - now).total_seconds() < 48*3600 and not assignment.is_submitted and not assignment.is_past_deadline
        if not assignment.is_past_deadline:
            active_assignments.append(assignment)
        if assignment.is_submitted:
            submitted_count += 1
        if assignment.is_urgent:
            urgent_count += 1
    return render(request, 'evaluation/student_assignments.html', {
        'student': student,
        'assignments': assignments,
        'active_assignments': active_assignments,
        'submitted_count': submitted_count,
        'urgent_count': urgent_count,
        'now': now,
    })

@login_required
def delete_submission(request, submission_id):
    submission = get_object_or_404(Submission, id=submission_id)
    # Only allow the teacher of the course to delete
    if request.user.role != 'teacher' or submission.assignment.course.teacher != request.user:
        messages.error(request, "You are not authorized to delete this submission.")
        return redirect('assignment_submissions', submission.assignment.id)
    if request.method == 'POST':
        submission.delete()
        messages.success(request, "Submission deleted successfully.")
        return redirect('assignment_submissions', submission.assignment.id)
    return render(request, 'evaluation/confirm_delete_submission.html', {'submission': submission})

class CustomLogoutView(LogoutView):
    next_page = '/'

@login_required
def peer_review_dashboard(request):
    if request.user.role != 'teacher':
        messages.error(request, "Only teachers can access this page.")
        return redirect('dashboard')
    assignments = Assignment.objects.filter(course__teacher=request.user)
    templates = PeerReviewTemplate.objects.filter(assignment__in=assignments)
    template_map = {t.assignment.id: t for t in templates}
    return render(request, 'evaluation/peer_review_dashboard.html', {
        'assignments': assignments,
        'template_map': template_map,
    })

@login_required
def create_peer_review_template(request, assignment_id):
    assignment = get_object_or_404(Assignment, id=assignment_id)
    num_questions = int(request.GET.get('num_questions', 3))  # Default to 3

    if request.method == 'POST':
        template_form = PeerReviewTemplateForm(request.POST, request.FILES)
        question_formset = PeerReviewQuestionFormSet(request.POST, queryset=PeerReviewQuestion.objects.none())
        if template_form.is_valid() and question_formset.is_valid():
            template = template_form.save(commit=False)
            template.assignment = assignment
            template.created_by = request.user
            template.save()
            questions = question_formset.save(commit=False)
            for q in questions:
                q.template = template
                q.save()
            messages.success(request, "Peer review template created!")
            return redirect('peer_review_dashboard')
    else:
        PeerReviewQuestionFormSetDynamic = modelformset_factory(
            PeerReviewQuestion,
            form=PeerReviewQuestionForm,
            extra=num_questions
        )
        template_form = PeerReviewTemplateForm()
        question_formset = PeerReviewQuestionFormSetDynamic(queryset=PeerReviewQuestion.objects.none())
    return render(request, 'evaluation/create_peer_review_template.html', {
        'template_form': template_form,
        'question_formset': question_formset,
        'assignment': assignment,
        'num_questions': num_questions,
    })

@login_required
def distribute_peer_reviews(request, assignment_id):
    assignment = get_object_or_404(Assignment, id=assignment_id, course__teacher=request.user)
    template = get_object_or_404(PeerReviewTemplate, assignment=assignment)
    if not template.enable_peer_review:
        messages.error(request, "Peer review is not enabled for this assignment.")
        return redirect('peer_review_dashboard')
    submissions = list(Submission.objects.filter(assignment=assignment))
    reviews_per_submission = template.copies_per_student

    # Use your round-robin algorithm
    assignments = randomized_peer_review_distribution(submissions, reviews_per_submission)

    for submission, reviewers in assignments:
        for reviewer in reviewers:
            PeerReview.objects.get_or_create(
                submission=submission,
                reviewer=reviewer,
                template=template
            )
    messages.success(request, "Peer reviews distributed!")
    return redirect('peer_review_dashboard')

@login_required
def assigned_peer_reviews(request):
    student = Student.objects.get(user=request.user)
    reviews = PeerReview.objects.filter(reviewer=student)
    return render(request, 'evaluation/assigned_peer_reviews.html', {'reviews': reviews})

@login_required
def fill_peer_review(request, review_id):
    review = get_object_or_404(PeerReview, id=review_id, reviewer=request.user.student)
    template = review.template
    assignment = review.submission.assignment  # Get the related assignment

    # Check if peer review deadline has passed (assuming deadline is on Assignment)
    if hasattr(assignment, 'peer_review_deadline') and assignment.peer_review_deadline:
        if timezone.now() > assignment.peer_review_deadline:
            messages.error(request, "Peer review deadline has passed. You can no longer submit reviews.")
            return redirect('dashboard')

    questions = PeerReviewQuestion.objects.filter(template=template).order_by('id')

    if review.completed:
        messages.info(request, "You have already completed this peer review.")
        return redirect('dashboard')

    for question in questions:
        PeerReviewAnswer.objects.get_or_create(
            review=review,
            question=question,
            defaults={'marks': 0}
        )

    AnswerFormSet = modelformset_factory(
        PeerReviewAnswer,
        form=PeerReviewAnswerForm,
        extra=0,
        can_delete=False
    )

    if request.method == 'POST':
        answer_formset = AnswerFormSet(
            request.POST,
            queryset=PeerReviewAnswer.objects.filter(review=review).order_by('question__id')
        )
        if answer_formset.is_valid():
            instances = answer_formset.save()
            total = 0
            for form in answer_formset:
                if form.cleaned_data and not form.cleaned_data.get('DELETE', False):
                    marks = form.cleaned_data.get('marks', 0)
                    if marks is not None:
                        total += int(marks)
            review.overall_score = int(total)
            review.completed = True
            review.save()
            messages.success(request, "Peer review submitted!")
            return redirect('dashboard')
        else:
            print(answer_formset.errors)
    else:
        answer_formset = AnswerFormSet(queryset=PeerReviewAnswer.objects.filter(review=review).order_by('question__id'))

    return render(request, 'evaluation/fill_peer_review.html', {
        'review': review,
        'answer_formset': answer_formset,
    })


@login_required
def manage_results(request):
    if request.user.role != 'teacher':
        messages.error(request, "Only teachers can access this page.")
        return redirect('dashboard')
    assignments = Assignment.objects.filter(course__teacher=request.user)
    return render(request, 'evaluation/manage_results.html', {'assignments': assignments})

@login_required
def assignment_results(request, assignment_id):
    assignment = get_object_or_404(Assignment, id=assignment_id, course__teacher=request.user)
    submissions = Submission.objects.filter(assignment=assignment)
    
    # Calculate overall average
    completed_reviews = PeerReview.objects.filter(
        submission__assignment=assignment, 
        completed=True, 
        overall_score__isnull=False
    )
    
    if completed_reviews.exists():
        overall_average = completed_reviews.aggregate(avg_score=models.Avg('overall_score'))['avg_score']
    else:
        overall_average = 0
    
    # Calculate total reviews
    total_reviews = completed_reviews.count()
    
    # Calculate max score
    try:
        template = PeerReviewTemplate.objects.get(assignment=assignment)
        max_score = sum(q.max_marks for q in template.questions.all())
    except PeerReviewTemplate.DoesNotExist:
        max_score = 0
    
    return render(request, 'evaluation/assignment_results.html', {
        'assignment': assignment,
        'submissions': submissions,
        'overall_average': overall_average,
        'total_reviews': total_reviews,
        'max_score': max_score,
    })

@login_required
def my_results(request):
    student = getattr(request.user, 'student', None)
    if not student:
        messages.error(request, "You are not a student.")
        return redirect('dashboard')
    # Only show results for assignments where results are published!
    submissions = Submission.objects.filter(student=student, assignment__results_published=True)
    return render(request, 'evaluation/my_results.html', {'submissions': submissions})

@login_required
def publish_results(request, assignment_id):
    assignment = get_object_or_404(Assignment, id=assignment_id, course__teacher=request.user)
    assignment.results_published = True
    assignment.save()
    messages.success(request, "Results published!")
    return redirect('assignment_results', assignment_id=assignment.id)

@login_required
def unpublish_results(request, assignment_id):
    assignment = get_object_or_404(Assignment, id=assignment_id, course__teacher=request.user)
    assignment.results_published = False
    assignment.save()
    messages.success(request, "Results unpublished!")
    return redirect('assignment_results', assignment_id=assignment.id)

@login_required
def edit_peer_review_template(request, template_id):
    template = get_object_or_404(PeerReviewTemplate, id=template_id, assignment__course__teacher=request.user)
    assignment = template.assignment
    questions = PeerReviewQuestion.objects.filter(template=template)
    PeerReviewQuestionFormSetDynamic = modelformset_factory(
        PeerReviewQuestion,
        form=PeerReviewQuestionForm,
        extra=0,  # No extra blank forms by default
        can_delete=True
    )
    prefix = 'questions'
    if request.method == 'POST':
        template_form = PeerReviewTemplateForm(request.POST, request.FILES, instance=template)
        question_formset = PeerReviewQuestionFormSetDynamic(request.POST, queryset=questions, prefix=prefix)
        if template_form.is_valid() and question_formset.is_valid():
            template_form.save()
            questions = question_formset.save(commit=False)
            for q in questions:
                q.template = template  # Ensure the template FK is set
                q.save()
            # Handle deleted questions
            for obj in question_formset.deleted_objects:
                obj.delete()
            messages.success(request, "Peer review template updated!")
            return redirect('peer_review_dashboard')
    else:
        template_form = PeerReviewTemplateForm(instance=template)
        question_formset = PeerReviewQuestionFormSetDynamic(queryset=questions, prefix=prefix)
    return render(request, 'evaluation/edit_peer_review_template.html', {
        'template_form': template_form,
        'question_formset': question_formset,
        'assignment': assignment,
        'template': template,
    })

@login_required
def student_assignment_detail(request, assignment_id):
    assignment = get_object_or_404(Assignment, id=assignment_id)
    # Fix the course check
    if not hasattr(request.user, 'student') or assignment.course != request.user.student.course:
        messages.error(request, "You're not authorised to view this page.")
        return redirect('student_dashboard')
    peer_reviews = PeerReview.objects.filter(submission__assignment=assignment, completed=True)
    # or for all answers:
    answers = PeerReviewAnswer.objects.filter(review__submission__assignment=assignment, review__completed=True)
    return render(request, 'evaluation/student_assignment_detail.html', {
        'assignment': assignment,
        'peer_reviews': peer_reviews,
        'answers': answers,
    })

# def round_robin_peer_review_distribution(submissions, reviews_per_submission):
#     n = len(submissions)
#     assignments = []
#     for i, submission in enumerate(submissions):
#         reviewers = []
#         for j in range(1, reviews_per_submission + 1):
#             reviewer_idx = (i + j) % n
#             reviewers.append(submissions[reviewer_idx].student)
#         assignments.append((submission, reviewers))
#     return assignments

def randomized_peer_review_distribution(submissions, reviews_per_submission):
    """
    Assigns each submission to be reviewed by `reviews_per_submission` different students,
    ensuring no student reviews their own submission and all reviews are distributed fairly.
    Returns a list of (submission, [reviewers]) tuples.
    """
    students = [s.student for s in submissions]
    n = len(submissions)
    assignments = {sub: [] for sub in submissions}
    reviewer_workload = {student: 0 for student in students}
    max_reviews_per_student = (n * reviews_per_submission) // n

    # Build a pool of (submission, needed reviews)
    pool = []
    for sub in submissions:
        pool.extend([sub] * reviews_per_submission)
    random.shuffle(pool)

    for sub in pool:
        # Eligible reviewers: not the owner, not already assigned, not overloaded
        eligible = [
            student for student in students
            if student != sub.student
            and reviewer_workload[student] < max_reviews_per_student
            and student not in assignments[sub]
        ]
        if not eligible:
            # Fallback: allow a bit more workload if needed
            eligible = [
                student for student in students
                if student != sub.student and student not in assignments[sub]
            ]
        if not eligible:
            raise ValueError(f"Cannot assign enough reviewers for submission {sub.id}")
        reviewer = random.choice(eligible)
        assignments[sub].append(reviewer)
        reviewer_workload[reviewer] += 1

    # Convert to list of tuples for compatibility
    return [(sub, reviewers) for sub, reviewers in assignments.items()]

@login_required
def delete_peer_review(request, review_id):
    if request.user.role != 'teacher':
        messages.error(request, "Only teachers can delete peer reviews.")
        return redirect('dashboard')
    review = get_object_or_404(PeerReview, id=review_id)
    if request.method == 'POST':
        review.answers.all().delete()
        review.delete()
        messages.success(request, "Peer review deleted. The student can now refill it.")
        return redirect('assignment_results', assignment_id=review.submission.assignment.id)
    return render(request, 'evaluation/confirm_delete_peer_review.html', {'review': review})

@login_required
def export_review_results(request, assignment_id):
    assignment = get_object_or_404(Assignment, id=assignment_id)
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{assignment.title}_results.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Student', 'Roll No', 'Average Score', 'Total Reviews'])
    
    for submission in assignment.submissions.all():
        reviews = submission.peer_reviews.all()
        avg_score = reviews.aggregate(avg=models.Avg('overall_score'))['avg'] or 0
        writer.writerow([
            submission.student.user.get_full_name(),
            submission.student.roll_no,
            round(avg_score, 2),
            reviews.count()
        ])
    
    return response

@login_required
def resend_for_evaluation(request, review_id):
    if request.user.role != 'teacher':
        messages.error(request, "Only teachers can resend evaluations.")
        return redirect('dashboard')
    
    review = get_object_or_404(PeerReview, id=review_id)
    
    if request.method == 'POST':
        teacher_comment = request.POST.get('teacher_comment', '').strip()
        if not teacher_comment:
            messages.error(request, "Please provide a comment explaining why the evaluation needs to be redone.")
            return redirect('assignment_results', assignment_id=review.submission.assignment.id)
        
        # Create resend request
        ResendRequest.objects.get_or_create(
            review=review,
            defaults={'teacher_comment': teacher_comment}
        )
        
        # Mark review as incomplete and reset scores
        review.completed = False
        review.overall_score = None
        review.save()
        
        # Optionally delete existing answers
        review.answers.all().delete()
        
        messages.success(request, f"Review sent back to {review.reviewer.user.get_full_name()} for re-evaluation.")
        return redirect('assignment_results', assignment_id=review.submission.assignment.id)
    
    return render(request, 'evaluation/resend_evaluation.html', {'review': review})

@login_required
def revoke_peer_review_distributions(request, assignment_id):
    if request.user.role != 'teacher':
        messages.error(request, "Only teachers can revoke distributions.")
        return redirect('dashboard')
    
    assignment = get_object_or_404(Assignment, id=assignment_id, course__teacher=request.user)
    
    if request.method == 'POST':
        # Delete all peer reviews and answers for this assignment
        peer_reviews = PeerReview.objects.filter(submission__assignment=assignment)
        answer_count = PeerReviewAnswer.objects.filter(review__in=peer_reviews).count()
        review_count = peer_reviews.count()
        
        # Delete answers first, then reviews
        PeerReviewAnswer.objects.filter(review__in=peer_reviews).delete()
        peer_reviews.delete()
        
        messages.success(request, f"Revoked {review_count} peer review assignments and {answer_count} answers. Students can now be redistributed.")
        return redirect('peer_review_dashboard')
    
    # Show confirmation page
    peer_reviews = PeerReview.objects.filter(submission__assignment=assignment)
    return render(request, 'evaluation/confirm_revoke_distributions.html', {
        'assignment': assignment,
        'peer_reviews': peer_reviews,
        'review_count': peer_reviews.count(),
    })

@login_required
def update_password(request, user_id):
    user_to_update = get_object_or_404(CustomUser, id=user_id)
    if request.user.role != 'teacher' and request.user != user_to_update:
        messages.error(request, "Not authorized.")
        return redirect('dashboard')

    if request.method == 'POST':
        form = UpdatePasswordForm(request.POST)
        if form.is_valid():
            new_password = form.cleaned_data['new_password']
            user_to_update.set_password(new_password)
            user_to_update.save()
            if request.user == user_to_update:
                logout(request)
                messages.success(request, "Password updated! Please log in again with your new password.")
                return redirect('login')
            else:
                messages.success(request, "Password updated successfully!")
                return redirect('manage_students')
    else:
        form = UpdatePasswordForm()

    return render(request, 'evaluation/update_password.html', {
        'form': form,
        'user_to_update': user_to_update,
    })



