from django import forms

class Account_settings(forms.Form):
    Choices = [
        ('All', 'Все'),
        ('Subscribers','Только подписчики'),
        ('Friends','Только друзья')
    ]
    account_set = forms.CharField(widget=forms.Select(choices=Choices))

class Stories_settings(forms.Form):
    Choices = [
        ('All', 'Все'),
        ('Subscribers','Только подписчики'),
        ('Friends','Только друзья')
    ]
    stories_set = forms.CharField(widget=forms.Select(choices=Choices))

class Comments_settings(forms.Form):
    Choices = [
        ('All', 'Все'),
        ('Subscribers','Только подписчики'),
        ('Friends','Только друзья'),
        ('Nobody','Никто')
    ]
    comments_set = forms.CharField(widget=forms.Select(choices=Choices))