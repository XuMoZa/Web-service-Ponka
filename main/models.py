from django.db import models
# Create your models here.

class User(models.Model):
    uid = models.CharField(max_length=255, default='1')
    username = models.CharField(max_length=30)
    uemail = models.EmailField()
    friends = models.ManyToManyField('self', symmetrical=True)
    subscribers = models.ManyToManyField('self', symmetrical=False, related_name='subs')
    subscriptions = models.ManyToManyField('self', symmetrical=False)
    black_list = models.ManyToManyField('self', symmetrical=False, related_name='black_list_users')
    last_login = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    photo = models.ImageField(upload_to='photos_root/',default='photos_root/default.png', null=True, blank=True)
    def __str__(self):
        return self.username


class Post(models.Model):
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posts')
    photo = models.ImageField(upload_to="post_photos_root/", null=True, blank=True)
    video = models.FileField(upload_to='post_photos_root/', null=True, blank=True)
    signature = models.TextField(max_length=255, null=True, blank=True)
    time = models.DateTimeField(auto_now_add=True)
class Like(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    post = models.ForeignKey(Post, on_delete=models.CASCADE)
class Comment(models.Model):
    text = models.TextField(max_length=255)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    post = models.ForeignKey(Post, on_delete=models.CASCADE)
    time = models.DateTimeField(auto_now_add=True)
class Stories(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='stories')
    picture = models.ImageField(upload_to='stories_images/', null=True, blank=True)
    video = models.FileField(upload_to='stories_videos/', null=True, blank=True)
    starttime = models.DateTimeField(auto_now_add=True)
    status = models.SmallIntegerField(default=1)

class Settings(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='settings')
    account_settings = models.TextField(max_length=255, default='All')
    stories_settings = models.TextField(max_length=255, default='All')
    comments_settings = models.TextField(max_length=255, default='All')
