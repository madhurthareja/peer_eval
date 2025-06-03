from django import forms
from django.forms import modelformset_factory
from .models import Assignment, Submission, PeerReview, PeerReviewAnswer, PeerReviewTemplate, PeerReviewQuestion, Student, CustomUser

class AssignmentForm(forms.ModelForm):
    class Meta:
        model = Assignment
        fields = ['course', 'title', 'description', 'assignment_pdf', 'solution_pdf', 'deadline', 'peer_review_deadline', 'is_published']
        widgets = {
            'peer_review_deadline': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }

class SubmissionForm(forms.ModelForm):
    class Meta:
        model = Submission
        fields = ['pdf']
        
class EvaluationForm(forms.ModelForm):
    class Meta:
        model = PeerReview
        fields = ['overall_score', 'overall_comment']

class CSVUploadForm(forms.Form):
    csv_file = forms.FileField(label="Upload CSV file")

PeerReviewAnswerFormSet = modelformset_factory(
    PeerReviewAnswer,
    fields=('question', 'marks', 'comment'),
    extra=0
)

class PeerReviewTemplateForm(forms.ModelForm):
    class Meta:
        model = PeerReviewTemplate
        fields = ['enable_peer_review', 'copies_per_student', 'rubric_pdf']

class PeerReviewQuestionForm(forms.ModelForm):
    class Meta:
        model = PeerReviewQuestion
        fields = ['text', 'max_marks', 'rubric']

PeerReviewQuestionFormSet = modelformset_factory(
    PeerReviewQuestion,
    form=PeerReviewQuestionForm,
    extra=3  # or any number you want
)

class EditStudentForm(forms.ModelForm):
    email = forms.EmailField()
    first_name = forms.CharField()
    last_name = forms.CharField()
    username = forms.CharField()

    class Meta:
        model = Student
        fields = ['roll_no']

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user_instance', None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields['email'].initial = user.email
            self.fields['first_name'].initial = user.first_name
            self.fields['last_name'].initial = user.last_name
            self.fields['username'].initial = user.username

    def save(self, commit=True):
        student = super().save(commit=False)
        user = student.user
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.username = self.cleaned_data['username']
        if commit:
            user.save()
            student.save()
        return student

class PeerReviewAnswerForm(forms.ModelForm):
    class Meta:
        model = PeerReviewAnswer
        fields = ['question', 'marks', 'comment']
        widgets = {
            'question': forms.HiddenInput(),
            'comment': forms.Textarea(attrs={'rows': 2}),
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['comment'].required = False

    def save_review(self, review, answer_formset):
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

class UpdatePasswordForm(forms.Form):
    new_password = forms.CharField(
        label="New Password",
        widget=forms.PasswordInput,
        min_length=8,
        help_text="Password must be at least 8 characters."
    )
    confirm_password = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput,
        min_length=8
    )

    def clean(self):
        cleaned_data = super().clean()
        pw1 = cleaned_data.get("new_password")
        pw2 = cleaned_data.get("confirm_password")
        if pw1 and pw2 and pw1 != pw2:
            raise forms.ValidationError("Passwords do not match.")
        return cleaned_data