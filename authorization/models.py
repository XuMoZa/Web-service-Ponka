from django.db import models

class Ponko_user(models.Model):
    username = models.CharField('Никнейм', max_length=20)
    password = models.CharField('Пароль', max_length=20)
    email = models.CharField('Майл', max_length=50)
    registration_time = models.TimeField('Дата')

    def __str__(self):
        return self.username