from django import forms

from .models import Chore, Member


class ChoreForm(forms.ModelForm):
    class Meta:
        model = Chore
        fields = ["title", "assignee", "due_date"]
        widgets = {
            "title": forms.TextInput(
                attrs={"class": "field-control", "placeholder": "e.g. Take out recycling"}
            ),
            "assignee": forms.Select(attrs={"class": "field-control"}),
            "due_date": forms.DateInput(
                format="%Y-%m-%d",
                attrs={"class": "field-control", "type": "date"},
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["assignee"].queryset = Member.objects.all()
        self.fields["due_date"].input_formats = ["%Y-%m-%d"]


class OverdueChoreForm(forms.ModelForm):
    class Meta:
        model = Chore
        fields = ["assignee", "due_date"]
        widgets = {
            "assignee": forms.Select(attrs={"class": "field-control"}),
            "due_date": forms.DateInput(
                format="%Y-%m-%d",
                attrs={"class": "field-control", "type": "date"},
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["assignee"].queryset = Member.objects.all()
        self.fields["due_date"].input_formats = ["%Y-%m-%d"]