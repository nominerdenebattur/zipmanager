"""
URL configuration for updater project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from update_ap.views import upload_zip, zip_list, download_latest_zip, downloaded_devices

urlpatterns = [
    path('list/', zip_list, name='zip_list'),
    path('download/', download_latest_zip, name='download_latest_zip'),
    path('upload/', upload_zip, name='upload_zip'),
    path('downloads/', downloaded_devices, name='downloaded_devices'),
    path('admin/', admin.site.urls),
]
