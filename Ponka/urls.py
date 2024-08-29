from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include

import authorization.views
import main.views

urlpatterns = [
                  path('admin/', admin.site.urls),
                  path('autorized/', include('main.urls')),
                  path('', include('authorization.urls')),
                  path('registered/', main.views.registered,name='registered'),
              ] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
