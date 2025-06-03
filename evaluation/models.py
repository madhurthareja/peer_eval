from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import FileExtensionValidator
from django.utils import timezone

class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ('teacher', 'Teacher'),
        ('student', 'Student'),
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='student')
    roll_no = models.CharField(max_length=20, unique=True, null=True, blank=True)
    email = models.EmailField(unique=True)

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
    
    def is_teacher(self):
        return self.role == 'teacher'
    
    def is_student(self):
        return self.role == 'student'

class Course(models.Model):
    name = models.CharField(max_length=100)
    teacher = models.ForeignKey('evaluation.CustomUser', on_delete=models.CASCADE, limit_choices_to={'role': 'teacher'})
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class Teacher(models.Model):
    user = models.OneToOneField('CustomUser', on_delete=models.CASCADE, limit_choices_to={'role': 'teacher'})

    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name}"

class Student(models.Model):
    user = models.OneToOneField('CustomUser', on_delete=models.CASCADE, limit_choices_to={'role': 'student'})
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='students')
    roll_no = models.CharField(max_length=20, unique=True)

    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name} ({self.roll_no})"

class Assignment(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='assignments')
    title = models.CharField(max_length=200)
    description = models.TextField()
    assignment_pdf = models.FileField(upload_to='assignments/', validators=[FileExtensionValidator(['pdf'])], null=True, blank=True)
    solution_pdf = models.FileField(upload_to='solutions/', null=True, blank=True, validators=[FileExtensionValidator(['pdf'])])
    deadline = models.DateTimeField()
    peer_review_deadline = models.DateTimeField()
    is_published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    results_published = models.BooleanField(default=False)

    def __str__(self):
        return self.title

    def is_locked(self):
        return timezone.now() > self.deadline
    
    def is_peer_review_deadline_passed(self):
        if self.peer_review_deadline:
            return timezone.now() > self.peer_review_deadline
        return False

class Submission(models.Model):
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name='submissions')
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    pdf = models.FileField(upload_to='submissions/', validators=[FileExtensionValidator(['pdf'])])
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('assignment', 'student')

    def __str__(self):
        return f"{self.student} - {self.assignment}"

class PeerReview(models.Model):
    submission = models.ForeignKey(Submission, on_delete=models.CASCADE, related_name='peer_reviews')
    reviewer = models.ForeignKey(Student, on_delete=models.CASCADE)
    template = models.ForeignKey('PeerReviewTemplate', on_delete=models.CASCADE)
    completed = models.BooleanField(default=False)
    overall_score = models.PositiveIntegerField(null=True, blank=True)
    overall_comment = models.TextField(blank=True)

    class Meta:
        unique_together = ('submission', 'reviewer')

    def __str__(self):
        return f"Review by {self.reviewer} for {self.submission}"

class PeerReviewTemplate(models.Model):
    assignment = models.OneToOneField(Assignment, on_delete=models.CASCADE)
    created_by = models.ForeignKey('CustomUser', on_delete=models.CASCADE)
    enable_peer_review = models.BooleanField(default=False)
    copies_per_student = models.PositiveIntegerField(default=2)
    rubric_pdf = models.FileField(upload_to='rubrics/', null=True, blank=True)

class PeerReviewQuestion(models.Model):
    template = models.ForeignKey(PeerReviewTemplate, on_delete=models.CASCADE, related_name='questions')
    text = models.CharField(max_length=255)
    max_marks = models.PositiveIntegerField()
    rubric = models.TextField(blank=True)  # Already optional

class PeerReviewAnswer(models.Model):
    review = models.ForeignKey(PeerReview, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(PeerReviewQuestion, on_delete=models.CASCADE)
    marks = models.IntegerField()
    comment = models.TextField(blank=True, null=True)

class Rubric(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    max_score = models.PositiveIntegerField()
    created_by = models.ForeignKey('CustomUser', on_delete=models.CASCADE)

class ResultRelease(models.Model):
    assignment = models.OneToOneField(Assignment, on_delete=models.CASCADE)
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)

class ResendRequest(models.Model):
    review = models.OneToOneField(PeerReview, on_delete=models.CASCADE, related_name='resend_request')
    teacher_comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_resolved = models.BooleanField(default=False)
    
    def __str__(self):
        return f"Resend request for {self.review}"