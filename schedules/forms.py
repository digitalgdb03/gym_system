from django import forms
from services.models import Service
from user.models import User
from .models import GymClass


class ClassForm(forms.ModelForm):
    class Meta:
        model = GymClass
        fields = ["service", "kind", "instructor", "second_instructor", "day", "block"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["service"].queryset = Service.objects.filter(
            kind=Service.Kind.GUIDED, is_active=True)
        instructors = User.objects.filter(role=User.Role.INSTRUCTOR)
        self.fields["instructor"].queryset = instructors
        self.fields["second_instructor"].queryset = instructors
