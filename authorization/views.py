from django.contrib import messages
from django.shortcuts import render
from firebase_admin import auth
import json
import requests
from requests.exceptions import HTTPError
from django.http import HttpResponse
def autorize_main(request):
    return render(request, 'autorize/signin.html')
