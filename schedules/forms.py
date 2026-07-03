from django import forms
from configuration.form_mixins import PlaceholderChoiceMixin
from services.models import Service
from user.models import User
from .models import GymClass


class ClassForm(PlaceholderChoiceMixin, forms.ModelForm):
    class Meta:
        model = GymClass
        fields = ["service", "kind", "instructor", "second_instructor", "day", "start_time", "end_time"]
        widgets = {
            "start_time": forms.TimeInput(attrs={"type": "time", "min": "05:00", "max": "22:00"}),
            "end_time": forms.TimeInput(attrs={"type": "time", "min": "05:00", "max": "22:00"}),
        }
        help_texts = {
            "start_time": "Entre 5:00 am y 10:00 pm.",
            "end_time": "Entre 5:00 am y 10:00 pm.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["service"].queryset = Service.objects.filter(
            kind=Service.Kind.GUIDED, is_active=True)
        instructors = User.objects.filter(role=User.Role.INSTRUCTOR)
        self.fields["instructor"].queryset = instructors
        self.fields["second_instructor"].queryset = instructors
