from django.contrib import admin
from .models import (
    CustomUser, Course, Teacher, Student
)

admin.site.register(CustomUser)
admin.site.register(Course)
admin.site.register(Teacher)
admin.site.register(Student)
