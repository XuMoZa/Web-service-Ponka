# ваш_проект/ваше_приложение/middleware.py
from django.contrib.auth.middleware import get_user

class CustomUserMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Получаем пользователя из сессии (если он аутентифицирован)
        request.user = get_user(request)

        # Добавляем вашу логику для установки кастомного пользователя в request
        # Например:
        # request.custom_user = ваш_код_для_получения_или_установки_пользователя()

        response = self.get_response(request)

        return response
