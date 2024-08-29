import os
import tempfile
from datetime import timedelta
from urllib.parse import urlparse
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
from io import BytesIO

from django.contrib import messages
from django.contrib import auth
from django.contrib.auth import login
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.shortcuts import render
from PIL import Image
import firebase_admin
import firebase
from firebase_admin import auth
from firebase_admin import db
import json
from django.conf import settings
import requests
from . import form
from main.database_class import Database
from .models import *
import sys
from requests.exceptions import HTTPError
from django.http import HttpResponse, JsonResponse

config = {
    'apiKey': "AIzaSyB0LQ0NIf3r3iigp81MUD9TT4OVilDVJRs",
    'authDomain': "ponka-ef43a.firebaseapp.com",
    'projectId': "ponka-ef43a",
    'databaseURL': "https://ponka-ef43a-default-rtdb.firebaseio.com",
    'storageBucket': "ponka-ef43a.appspot.com",
    'messagingSenderId': "585322412214",
    'appId': "1:585322412214:web:59b9dfd3f655d456c50e17",
    'measurementId': "G-HS118Z0QVN"
}
api_key = "AIzaSyB0LQ0NIf3r3iigp81MUD9TT4OVilDVJRs"
databaseURL = "https://ponka-ef43a-default-rtdb.firebaseio.com"
session = requests.session()
database = Database(None, api_key, databaseURL, session)
user = User()



def sign_in_with_email_and_password(email, password):
    current_user = None
    request_ref = "https://www.googleapis.com/identitytoolkit/v3/relyingparty/verifyPassword?key={0}".format(
        api_key)
    headers = {"content-type": "application/json; charset=UTF-8"}
    data = json.dumps({"email": email, "password": password, "returnSecureToken": True})
    request_object = requests.post(request_ref, headers=headers, data=data)
    return request_object.json()


def create_user_with_email_and_password(email, password):
    request_ref = "https://www.googleapis.com/identitytoolkit/v3/relyingparty/signupNewUser?key={0}".format(api_key)
    headers = {"content-type": "application/json; charset=UTF-8"}
    data = json.dumps({"email": email, "password": password, "returnSecureToken": True})
    request_object = requests.post(request_ref, headers=headers, data=data)
    return request_object.json()


def signin(request):
    email = request.POST.get('email')
    password = request.POST.get('password')
    response_object = sign_in_with_email_and_password(email, password)
    if email == '' or password == '':
        message = "Missing email or password"
        return render(request, "autorize/signin.html", {"message": message})
    if "error" in response_object and 'EMAIL_NOT_FOUND' in response_object['error']['message']:
        message = "Invalid email"
        return render(request, "autorize/signin.html", {"message": message})
    elif "error" in response_object and 'INVALID_PASSWORD' in response_object['error']['message']:
        message = "Invalid password"
        return render(request, "autorize/signin.html", {"message": message})
    elif "error" in response_object and 'MISSING_EMAIL' in response_object['error']['message']:
        print(response_object)
        message = "LogIn or SignUp first."
        return render(request, "autorize/signin.html", {"message": message})
    else:
        session_id = response_object['localId']
        request.session['uid'] = str(session_id)
        global user
        user = User.objects.get(uid=request.session['uid'])
        login(request, user)
        request.user = user
        lenta_info = get_lenta()
        stories_info = get_stories()
        return render(request, 'main/index.html',
                      {'user_photo': user.photo, 'lenta_info': lenta_info, 'stories_info': stories_info})


def signup(request):
    return render(request, "autorize/signup.html")


def registered(request):
    name = request.POST.get('name')
    email = request.POST.get('email')
    passw = request.POST.get('password')
    _user = create_user_with_email_and_password(email, passw)
    if "error" in _user and 'WEAK_PASSWORD' in _user['error']['message']:
        message = 'Weak password. Try again'
        return render(request, "autorize/signup.html", {'message': message})
    elif "error" in _user and 'EMAIL_EXISTS' in _user['error']['message']:
        message = 'Email exists. Try again'
        return render(request, "autorize/signup.html", {'message': message})
    else:
        uid = _user['localId']
        data = {"email": email, "status": 1, "name": name, 'followers': 0, 'subscriptions': 0, 'friends': 0}
        database.child("users").child(uid).child("details").set(data)
        global user
        user = User.objects.create(uid=uid, username=name, uemail=email)
        settings = Settings.objects.create(user=user)
        return render(request, "autorize/signin.html")

def upload_user_photo(request):

    return render(request, "main/user_photo.html",{'user_photo':user.photo})

def user_search_result(request):
    name = request.POST.get('nickname')
    if name == user.username:
        message = "You can't find yourself"
        return render(request,'main/find_user.html',{'message': message,'user_photo':user.photo})
    if name == None:
        message = 'Enter a username'
        return render(request,'main/find_user.html', {'message':message, 'user_photo': user.photo})
    try:
        targetUser = User.objects.get(username = name)
    except User.DoesNotExist:
        message = 'Can not find a user'
        return render(request,'main/find_user.html', {'message': message, 'user_photo': user.photo})
    posts = Post.objects.filter(author=targetUser).order_by('-time')
    posts_data = []
    target_settings = Settings.objects.get(user = targetUser)
    if user.friends.filter(id=targetUser.id).exists():
        friend_info = 'Удалить из друзей'
    else:
        friend_info = 'Добавить в друзья'
    if user.subscriptions.filter(id=targetUser.id).exists():
        sub_info = 'Отписаться'
    else:
        sub_info = 'Подписаться'
    if ((target_settings.account_settings == 'All') or (target_settings.account_settings == 'Subscribers' and targetUser.subs.filter(id=user.id).exists()) or (target_settings.account_settings == 'Friends' and targetUser.friends.filter(id=user.id).exists())) and not targetUser.black_list.filter(id=user.id).exists():
        for post in posts:
            # Получение всех лайков для текущего поста
            likes = Like.objects.filter(post=post)

            # Получение всех комментариев для текущего поста
            comments = Comment.objects.filter(post=post)
            existing_like = Like.objects.filter(user=user, post=post).first()
            if existing_like:
                like_info = "fa-solid fa-heart"
            else:
                like_info = "fa-regular fa-heart"
            # Добавление данных в список
            posts_data.append({
                'post': post,
                'likes': likes,
                'comments': comments,
                'like_info':like_info,
            })
    return render(request, 'main/someone.html', {'posts_data': posts_data, 'your_photo': user.photo,'user_photo': targetUser.photo, 'name': targetUser.username,
                                                 'followers': targetUser.subscribers.count(), 'friend_info':friend_info,
                                                 'subs': targetUser.subscriptions.count(), 'sub_info':sub_info,
                                                 'friends': targetUser.friends.count()})
def add_comment(request):
    if request.method == 'POST':
        name = request.POST.get("username")
        print(name)
        targetUser = User.objects.get(username=name)
        text = request.POST.get("text")
        photo = request.POST.get("photo")
        post = Post.objects.get(author=targetUser, photo=photo)
        comment = Comment.objects.create(post=post, user=user, text=text)
        comment.save()
        return JsonResponse({'status': 'success', 'comment': comment.text})

def comments_input(request):
    name = request.POST.get("username")
    targetUser = User.objects.get(username = name)
    text = request.POST.get("comment")
    photo = request.POST.get("post")
    post = Post.objects.get(author = targetUser,photo = photo)
    comment = Comment.objects.create(post=post, user=user, text=text)
    comment.save()
    page = request.POST.get("page")
    if page == 'main':
        lenta_info = get_lenta()
        stories_info = get_stories()
        return render(request, 'main/index.html',
                      {'user_photo': user.photo, 'lenta_info': lenta_info, 'stories_info': stories_info})
    posts = Post.objects.filter(author=targetUser).order_by('-time')
    posts_data = []
    if user.friends.filter(id=targetUser.id).exists():
        friend_info = 'Удалить из друзей'
    else:
        friend_info = 'Добавить в друзья'
    if user.subscriptions.filter(id=targetUser.id).exists():
        sub_info = 'Отписаться'
    else:
        sub_info = 'Подписаться'
    for post in posts:
        # Получение всех лайков для текущего поста
        likes = Like.objects.filter(post=post)

        # Получение всех комментариев для текущего поста
        comments = Comment.objects.filter(post=post)
        existing_like = Like.objects.filter(user=user, post=post).first()
        if existing_like:
            like_info = "fa-solid fa-heart"
        else:
            like_info = "fa-regular fa-heart"
        # Добавление данных в список
        posts_data.append({
            'post': post,
            'likes': likes,
            'like_info':like_info,
            'comments': comments,
        })
    return render(request, 'main/someone.html', {'posts_data': posts_data, 'your_photo': user.photo,'user_photo': targetUser.photo, 'name': targetUser.username,
                                                 'followers': targetUser.subscribers.count(), 'friend_info':friend_info,
                                                 'subs': targetUser.subscriptions.count(), 'sub_info':sub_info,
                                                 'friends': targetUser.friends.count()})
def podpiska(request):
    name = request.POST.get('username')
    target_user = User.objects.get(username = name)
    posts = Post.objects.filter(author=target_user).order_by('-time')
    if user.subscriptions.filter(id=target_user.id).exists():
        # Если подписка существует, удаляем ее
        user.subscriptions.remove(target_user)
        target_user.subscribers.remove(user)
        sub_info = 'Подписаться'
    else:
        # Если подписки нет, создаем ее
        user.subscriptions.add(target_user)
        target_user.subscribers.add(user)
        sub_info = 'Отписаться'

    user.save()
    target_user.save()
    if user.friends.filter(id=target_user.id).exists():
        friend_info = 'Удалить из друзей'
    else:
        friend_info = 'Добавить в друзья'
    posts_data = []
    target_settings = Settings.objects.get(user=target_user)
    if ((target_settings.account_settings == 'All') or (
            target_settings.account_settings == 'Subscribers' and target_user.subs.filter(id=user.id).exists()) or (
            target_settings.account_settings == 'Friends' and target_user.friends.filter(id=user.id).exists())) and not target_user.black_list.filter(id=user.id).exists():
        for post in posts:
            # Получение всех лайков для текущего поста
            likes = Like.objects.filter(post=post)

            # Получение всех комментариев для текущего поста
            comments = Comment.objects.filter(post=post)
            existing_like = Like.objects.filter(user=user, post=post).first()
            if existing_like:
                like_info = "fa-solid fa-heart"
            else:
                like_info = "fa-regular fa-heart"
            # Добавление данных в список
            posts_data.append({
                'post': post,
                'likes': likes,
                'like_info':like_info,
                'comments': comments,
            })

    #return HttpResponse(message)
    return render(request, 'main/someone.html', {'posts_data': posts_data, 'your_photo': user.photo,'user_photo': target_user.photo, 'name': target_user.username,
                                                 'followers': target_user.subscribers.count(), 'friend_info':friend_info,
                                                 'subs': target_user.subscriptions.count(), 'sub_info':sub_info,
                                                 'friends': target_user.friends.count()})
def find_user(request):

    return render(request, "main/find_user.html",{'user_photo':user.photo})

def settings(request):
    account_settings = form.Account_settings()
    stories_settings = form.Stories_settings()
    comments_settings = form.Comments_settings()
    return render(request, "main/settings.html",{'user_photo':user.photo,'acc_set':account_settings,'stor_set':stories_settings,'com_set':comments_settings})

def change_settings(request):
    form_acc = form.Account_settings(request.POST)
    if form_acc.is_valid():
        acc = form_acc.cleaned_data['account_set']
    form_stor = form.Stories_settings(request.POST)
    if form_stor.is_valid():
        stor = form_stor.cleaned_data['stories_set']
    form_com = form.Comments_settings(request.POST)
    if form_com.is_valid():
        com = form_com.cleaned_data['comments_set']
    names = request.POST.get("blacklist")
    names.strip()
    if names != "":
        black_list = names.split(" ")
    else:
        black_list = []
    try:
        settings = Settings.objects.get(user=user)
        settings.account_settings = acc
        settings.comments_settings = com
        settings.stories_settings = stor
        for black in black_list:
            try:
                targetUser = User.objects.get(username=black)
                user.black_list.add(targetUser)
            except User.DoesNotExist:
                continue
        settings.save()
        user.save()
    except ObjectDoesNotExist:
        settings = Settings.objects.create(user=user, account_settings=acc, comments_settings = com, stories_settings = stor)
        for black in black_list:
            try:
                targetUser = User.objects.get(username=black)
                settings.black_list.add(targetUser)
            except User.DoesNotExist:
                continue
        settings.save()
    stories_info = get_stories()
    lenta_info = get_lenta()
    return render(request, 'main/index.html',
                  {'user_photo': user.photo, 'lenta_info': lenta_info, 'stories_info': stories_info})

def search_results(request):

    return render(request, "main/user_photo.html", {'user_photo': user.photo})
def post_user_photo(request):
    if request.method == 'POST':
        photo = request.FILES.get('photo')
        if not photo:
            message = ('Please choose a photo.')
            return render(request, "main/photos.html", {'message': message, 'user_photo': user.photo})

        image = Image.open(photo)

        # Получаем размеры изображения
        width, height = image.size
        if width >= height:
            new_width = height
            new_height = height
        else:
            new_height = width
            new_width = width

        # Вычисляем координаты для обрезки
        left = (width - new_width) / 2
        top = (height - new_height) / 2
        right = (width + new_width) / 2
        bottom = (height + new_height) / 2

        # Обрезаем изображение
        cropped_image = image.crop((left, top, right, bottom))
        print(photo)
        # Создаем временный объект Post с обрезанным изображением
        cropped_image_io = BytesIO()
        cropped_image.save(cropped_image_io, format='PNG')  # Используйте нужный формат
        content_file = ContentFile(cropped_image_io.getvalue())
        assert isinstance(cropped_image, Image.Image), "cropped_image is not an instance of Image.Image"
        user.photo.save(photo.name, content_file, save=False)
        user.save()
    lenta_info = get_lenta()
    stories_info = get_stories()
    return  render(request, 'main/index.html', {'user_photo': user.photo, 'lenta_info':lenta_info,'stories_info':stories_info})


def post_upload(request):
    if request.method == 'POST':
        photo = request.FILES.get('photo')
        if not photo:
            message = ('Please choose a photo.')
            return render(request, "main/photos.html", {'message': message, 'user_photo': user.photo})

        image = Image.open(photo)

        # Получаем размеры изображения
        width, height = image.size
        if width >= height:
            new_width = height
            new_height = height
        else:
            if width * 5 / 4 > height:
                new_width = width - 0.8 * (height - 5 / 4 * width)
                new_height = height
            elif width * 1.2 == height:
                new_width = width
                new_height = height
            else:
                new_height = height - (1.2 * width - height)
                new_width = width

        # Вычисляем координаты для обрезки
        left = (width - new_width) / 2
        top = (height - new_height) / 2
        right = (width + new_width) / 2
        bottom = (height + new_height) / 2

        # Обрезаем изображение
        cropped_image = image.crop((left, top, right, bottom))
        print(photo)
        signature = request.POST.get('signature')
        # Создаем временный объект Post с обрезанным изображением
        temp_post = Post(author=user, signature=signature)
        cropped_image_io = BytesIO()
        cropped_image.save(cropped_image_io, format='PNG')  # Используйте нужный формат
        content_file = ContentFile(cropped_image_io.getvalue())
        assert isinstance(cropped_image, Image.Image), "cropped_image is not an instance of Image.Image"
        temp_post.photo.save(photo.name, content_file, save=False)
        temp_post.save()
    stories_info= get_stories()
    lenta_info=get_lenta()
    return  render(request, 'main/index.html', {'user_photo': user.photo, 'lenta_info':lenta_info,'stories_info':stories_info})

def add_friend(request):
    name = request.POST.get('username')
    target_user = User.objects.get(username=name)
    posts = Post.objects.filter(author=target_user).order_by('-time')
    if user.friends.filter(id=target_user.id).exists():
        # Если подписка существует, удаляем ее
        user.friends.remove(target_user)
        target_user.friends.remove(user)
        friend_info = 'Добавить в друзья'
    else:
        # Если подписки нет, создаем ее
        user.friends.add(target_user)
        target_user.friends.add(user)
        friend_info = 'Удалить из друзей'
    if user.subscriptions.filter(id=target_user.id).exists():
        sub_info = 'Отписаться'
    else:
        sub_info = 'Подписаться'
    user.save()
    target_user.save()
    posts_data = []
    target_settings = Settings.objects.get(user=target_user)
    if ((target_settings.account_settings == 'All') or (
            target_settings.account_settings == 'Subscribers' and target_user.subs.filter(id=user.id).exists()) or (
            target_settings.account_settings == 'Friends' and target_user.friends.filter(id=user.id).exists())) and not target_user.black_list.filter(id=user.id).exists():
        for post in posts:
            # Получение всех лайков для текущего поста
            likes = Like.objects.filter(post=post)
            existing_like = Like.objects.filter(user=user, post=post).first()
            if existing_like:
                like_info = "fa-solid fa-heart"
            else:
                like_info = "fa-regular fa-heart"
            # Получение всех комментариев для текущего поста
            comments = Comment.objects.filter(post=post)

            # Добавление данных в список
            posts_data.append({
                'post': post,
                'like_info':like_info,
                'likes': likes,
                'comments': comments,
            })

    return render(request, 'main/someone.html',
                  {'your_photo': user.photo, 'user_photo': target_user.photo,
                   'name': target_user.username,'posts_data': posts_data,'friend_info':friend_info, 'sub_info':sub_info,
                   'followers': target_user.subscribers.count(),
                   'subs': target_user.subscriptions.count(),
                   'friends': target_user.friends.count()})
def logout(request):
    logout(request)
    return render(request, 'autorize/signin.html')

def like(request, post_id,page):
    post = Post.objects.get(id= post_id)
    targetUser=post.author
    existing_like = Like.objects.filter(user=user, post=post).first()
    if existing_like:
        # Если лайк существует, удаляем его
        existing_like.delete()

    else:
        # Если лайка не существует, создаем новый
        new_like = Like.objects.create(user=user, post=post)
    if page == 'main':
        lenta_info = get_lenta()
        stories_info = get_stories()
        return render(request, 'main/index.html',
                      {'user_photo': user.photo, 'lenta_info': lenta_info, 'stories_info': stories_info})
    if user.friends.filter(id=targetUser.id).exists():
        friend_info = 'Удалить из друзей'
    else:
        friend_info = 'Добавить в друзья'
    if user.subscriptions.filter(id=targetUser.id).exists():
        sub_info = 'Отписаться'
    else:
        sub_info = 'Подписаться'


    posts = Post.objects.filter(author=targetUser).order_by('-time')
    posts_data = []
    for post in posts:
        # Получение всех лайков для текущего поста
        likes = Like.objects.filter(post=post)
        existing_like = Like.objects.filter(user=user, post=post).first()
        if existing_like:
            like_info = "fa-solid fa-heart"
        else:
            like_info = "fa-regular fa-heart"
        # Получение всех комментариев для текущего поста
        comments = Comment.objects.filter(post=post)

        # Добавление данных в список
        posts_data.append({
            'post': post,
            'likes': likes,
            'like_info':like_info,
            'comments': comments,
        })
    return render(request, 'main/someone.html',
                  {'posts_data': posts_data, 'your_photo': user.photo, 'user_photo': targetUser.photo,
                   'name': targetUser.username, 'friend_info':friend_info, 'sub_info':sub_info,
                   'followers': targetUser.subscribers.count(),
                   'subs': targetUser.subscriptions.count(),
                   'friends': targetUser.friends.count()})
def index(request):
    lenta_info = get_lenta()
    stories_info=get_stories()
    return  render(request, 'main/index.html', {'user_photo': user.photo, 'lenta_info':lenta_info,'stories_info':stories_info})

def get_stories():
    if user.subscriptions.exists():
        users_with_specific_settings = User.objects.filter(settings__account_settings__in=['All', 'Subscribers'])
        users_with_friends_settings = User.objects.filter(settings__account_settings = 'Friends')
        subscriptions = users_with_specific_settings.filter(subscribers = user)
        friends = users_with_friends_settings.filter(friends = user)
        print(users_with_specific_settings)
        print(subscriptions)
        print(friends)
        filtered_subscriptions = []
        filtered_friends = []
        for sub in subscriptions:
            black_list = sub.black_list.all()
            should_delete = False
            for black in black_list:
                if black == user:
                    should_delete = True
                    break
            if not should_delete:
                filtered_subscriptions.append(sub)
        for fr in friends:
            should_delete = False
            black_list = fr.black_list.all()
            for black in black_list:
                if black == user:
                    should_delete = True
            if not should_delete:
                filtered_friends.append(fr)
        subs = User.objects.filter(id__in=[sub.id for sub in filtered_subscriptions])
        fri = User.objects.filter(id__in=[sub.id for sub in filtered_friends])
        subscriptions = subs.union(fri)
        print(subs)
        print(fri)
    else:
        subscriptions = []
    stories_info = []
    my_story = user.stories.filter(status = 1)
    my_content = []

    for story in my_story:
        if story.picture != None and story.picture != '':
            my_content.append({
                'content': story.picture,
            })
        elif story.video != None and story.video != '':
            my_content.append({
                'content': story.video,
            })
    if my_content != []:
        print(my_content)
        stories_info.append({
            'story': my_content,
            'user_name': user.username,
            'user_photo': user.photo,
        })

    # Перебор пользователей в подписках и получение их имен, фото и постов
    for subscription in subscriptions:
        # Получение имени и фото пользователя
        subscription_name = subscription.username
        subscription_photo = subscription.photo if subscription.photo else 'default_photo_url'
        sub_content = []
        print(subscription)
        subscription_stories = subscription.stories.filter(status = 1)
        for story in subscription_stories:
            if story.picture != None and story.picture != '':
                sub_content.append({
                    'content':story.picture
                })
            elif story.video != None and story.video != '':
                sub_content.append({
                    'content':story.video
                })

        if sub_content != []:
            print(sub_content)
            stories_info.append({
                'story': sub_content,
                'user_name': subscription_name,
                'user_photo': subscription_photo,
            })
    print(stories_info)
    return stories_info
def get_lenta():
    if user.subscriptions.exists():
        users_with_specific_settings = User.objects.filter(settings__account_settings__in=['All', 'Subscribers'])
        users_with_friends_settings = User.objects.filter(settings__account_settings = 'Friends')
        subscriptions = users_with_specific_settings.filter(subscribers = user)
        friends = users_with_friends_settings.filter(friends = user)
        print('users',users_with_specific_settings)
        print('fr',users_with_friends_settings)
        print('subs',subscriptions)
        print('fri',friends)
        filtered_subscriptions = []
        filtered_friends = []
        for sub in subscriptions:
            black_list = sub.black_list.all()
            should_delete = False
            for black in black_list:
                if black == user:
                    should_delete = True
                    break
            if not should_delete:
                filtered_subscriptions.append(sub)
        for fr in friends:
            should_delete = False
            black_list = fr.black_list.all()
            for black in black_list:
                if black == user:
                    should_delete = True
            if not should_delete:
                filtered_friends.append(fr)
        subs = User.objects.filter(id__in=[sub.id for sub in filtered_subscriptions])
        fri = User.objects.filter(id__in=[sub.id for sub in filtered_friends])
        subscriptions = subs.union(fri)
    else:
        subscriptions = []
    lenta_info = []
    # Перебор пользователей в подписках и получение их имен, фото и постов
    for subscription in subscriptions:
        # Получение имени и фото пользователя
        subscription_name = subscription.username
        subscription_photo = subscription.photo if subscription.photo else 'default_photo_url'

        # Получение постов пользователя с временем публикации менее чем две недели назад
        two_weeks_ago = timezone.now() - timedelta(weeks=2)
        subscription_posts = subscription.posts.filter(time__gte=two_weeks_ago).order_by('-time')
        for post in subscription_posts:
            # Получение всех лайков для текущего поста
            likes = Like.objects.filter(post=post)

            # Получение всех комментариев для текущего поста
            comments = Comment.objects.filter(post=post)
            existing_like = Like.objects.filter(user=user, post=post).first()
            if existing_like:
                like_info = "fa-solid fa-heart"
            else:
                like_info = "fa-regular fa-heart"
            lenta_info.append({
            'post': post,
            'likes': likes,
            'like_info': like_info,
            'comments': comments,
            'user_name': subscription_name,
            'user_photo': subscription_photo,
            })

    recomendations = User.objects.exclude(subscribers = user).exclude(id=user.id)
    print(recomendations)
    if recomendations.exists():
        recomendations = recomendations.filter(settings__account_settings__in=['All'])
        print(recomendations)
        filtered = []
        for rec in recomendations:
            should_delete = False
            black_list = rec.black_list.all()
            for black in black_list:
                if black == user:
                    should_delete = True
                    break
            if not should_delete:
                filtered.append(rec)
        recomendations = User.objects.filter(id__in=[sub.id for sub in filtered])
        print('----',recomendations)
        all_posts = Post.objects.filter(author__in=recomendations)
        sorted_posts = all_posts.order_by('-time')
        counter = 0
        for rec_post in sorted_posts:
            counter+=1
            rec = rec_post.author
            # Получение всех лайков для текущего поста
            likes = Like.objects.filter(post=rec_post)

            # Получение всех комментариев для текущего поста
            comments = Comment.objects.filter(post=rec_post)
            existing_like = Like.objects.filter(user=user, post=rec_post).first()
            if existing_like:
                like_info = "fa-solid fa-heart"
            else:
                like_info = "fa-regular fa-heart"
            lenta_info.append({
                'post': rec_post,
                'likes': likes,
                'like_info': like_info,
                'comments': comments,
                'user_name': rec.username,
                'user_photo': rec.photo,
            })
            if counter == 20:
                break
    print(lenta_info)
    return lenta_info
def delete_post(request,post_counter):
    print(post_counter)
    posts = Post.objects.filter(author=user).order_by('-time')
    for index, post in enumerate(posts, start=1):
        if index == post_counter:
            post.delete()
    posts = Post.objects.filter(author=user).order_by('-time')
    return render(request, 'main/account.html', {'posts': posts, 'user_photo': user.photo, 'name': user.username,
                                                 'followers': user.subscribers.count(),
                                                 'subs': user.subscriptions.count(),
                                                 'friends': user.friends.count()})
    pass
def friends(request):
    friends = user.friends.all()
    friend_info =[]
    for friend in friends:
        friend_name = friend.username
        friend_photo = friend.photo
        friend_info.append({
            'friend_name' : friend_name,
            'friend_photo':friend_photo
        })
        print(friend.username)
        print(friend.photo)
    print(friend_info)

    return render(request, 'main/friends.html', {'user_photo': user.photo, 'friend_info':friend_info})  # change to friends

def delete_story(request):
    stories = Stories.objects.filter(user=user,status=1)
    posts = Post.objects.filter(author=user).order_by('-time')
    if stories.exists():
        story = stories.last()
        story.delete()
        return render(request, 'main/account.html', {'posts': posts, 'user_photo': user.photo, 'name': user.username,
                                                     'followers': user.subscribers.count(),
                                                     'subs': user.subscriptions.count(),
                                                     'friends': user.friends.count()})
    else:
        message = 'История не найдена.'
        return render(request, 'main/account.html', {'posts': posts, 'user_photo': user.photo, 'name': user.username,
                                                     'followers': user.subscribers.count(),
                                                     'subs': user.subscriptions.count(),
                                                     'friends': user.friends.count(),
                                                     'message':message})

def story_history(request):
    stories = Stories.objects.filter(user=user)
    temp = []
    for story in stories:

        if story.picture != None and story.picture != '':
            print(story.picture)
            print(story.picture.url)
            relative_path = os.path.relpath(story.picture.url, '/media/').replace('\\', '/')
            temp.append(relative_path)

        elif story.video != None and story.video != '':
            relative_path = os.path.relpath(story.video.url, '/media/').replace('\\', '/')
            temp.append(relative_path)

    return render(request,'main/history.html',{'stories':temp, 'user_photo': user.photo})
def to_user(request, user_name):
    if user_name.endswith('.flag'):
        user_name = 'photos_root/' + user_name.replace('.flag','')
        user_ = User.objects.get(photo = user_name)
        user_name = user_.username
        print(user_name)
    if user_name == user.username:
        posts = Post.objects.filter(author=user).order_by('-time')
        temp = []
        stories = Stories.objects.filter(user=user, status=1)
        for story in stories:
            if story.picture != None and story.picture != '':
                temp.append(story.picture)
            elif story.video != None and story.video != '':
                temp.append(story.video)

        return render(request, 'main/account.html', {'posts': posts, 'user_photo': user.photo, 'name': user.username,
                                                     'followers': user.subscribers.count(),
                                                     'subs': user.subscriptions.count(),
                                                     'friends': user.friends.count(),
                                                     'stories': temp})
    else:
        targetUser = User.objects.get(username = user_name)
        posts = Post.objects.filter(author=targetUser).order_by('-time')
        posts_data = []
        target_settings = Settings.objects.get(user=targetUser)
        if user.friends.filter(id=targetUser.id).exists():
            friend_info = 'Удалить из друзей'
        else:
            friend_info = 'Добавить в друзья'
        if user.subscriptions.filter(id=targetUser.id).exists():
            sub_info = 'Отписаться'
        else:
            sub_info = 'Подписаться'
        if ((target_settings.account_settings == 'All') or (
                target_settings.account_settings == 'Subscribers' and targetUser.subs.filter(id=user.id).exists()) or (
                target_settings.account_settings == 'Friends' and targetUser.friends.filter(id=user.id).exists())) and not targetUser.black_list.filter(id=user.id).exists():
            for post in posts:
                # Получение всех лайков для текущего поста
                likes = Like.objects.filter(post=post)
                existing_like = Like.objects.filter(user=user, post=post).first()
                if existing_like:
                    like_info = "fa-solid fa-heart"
                else:
                    like_info = "fa-regular fa-heart"
                # Получение всех комментариев для текущего поста
                comments = Comment.objects.filter(post=post)

                # Добавление данных в список
                posts_data.append({
                    'post': post,
                    'likes': likes,
                    'like_info':like_info,
                    'comments': comments,
                })
        return render(request, 'main/someone.html',
                      {'posts_data': posts_data, 'your_photo': user.photo, 'user_photo': targetUser.photo,
                       'name': targetUser.username,'friend_info': friend_info, 'sub_info':sub_info,
                       'followers': targetUser.subscribers.count(),
                       'subs': targetUser.subscriptions.count(),
                       'friends': targetUser.friends.count()})

def account(request):
    global user
    print (request.user)
    posts = Post.objects.filter(author=user).order_by('-time')
    temp = []
    stories = Stories.objects.filter(user=user, status = 1)
    for story in stories:
        if story.picture != None and story.picture!='':
            temp.append(story.picture)
        elif story.video != None and story.video !='':
            temp.append(story.video)

    return render(request, 'main/account.html', {'posts': posts, 'user_photo': user.photo, 'name': user.username,
                                                 'followers': user.subscribers.count(),
                                                 'subs': user.subscriptions.count(),
                                                 'friends': user.friends.count(),
                                                 'stories':temp})

def stories(request):

    return render(request, 'main/stories.html', {'user_photo': user.photo})
def story_upload(request):
    file = request.FILES['file']
    file_name = file.name
    if file_name.endswith('.img') or file_name.endswith('.png') or file_name.endswith('.jpg') or file_name.endswith('.jpeg') or file_name.endswith('.bmp'):
        story = Stories.objects.create(user = user, picture = file)
        story.save()
    elif file_name.endswith('.mp4') or file_name.endswith('.mob') or file_name.endswith('.webm') or file_name.endswith('.avi') or file_name.endswith('.mkv'):
        story = Stories.objects.create(user=user, video=file)
        story.save()
    else:
        message = 'Произошла ошибка во время загрузки файла. Проверьте чтобы файл являлся фотографией или видеофайлом.'
        return render(request,'main/stories.html', {'user_photo': user.photo, 'message':message})
    lenta_info = get_lenta()
    stories_info = get_stories()
    return render(request,'main/index.html',{'lenta_info':lenta_info, 'user_photo':user.photo,'stories_info':stories_info})

def photos(request):
    print(request.user)
    return render(request, 'main/photos.html', {'user_photo': user.photo})
