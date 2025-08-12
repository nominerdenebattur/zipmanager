import shutil

from django.shortcuts import render, redirect
from django.http import FileResponse, HttpResponse
from django.conf import settings
from django.utils import timezone
from user_agents import parse
import os
import socket
import io
import base64
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from django.db import models
from django.db.models import Count
from django.utils.dateparse import parse_date
from .models import ZipFile, DownloadedDevice
from .forms import ZipFileForm
from django.core.paginator import Paginator
from django.shortcuts import render
import subprocess

#zip file upload hiih view
def upload_zip(request):
    if request.method == 'POST':  # Хэрэв POST хүсэлт ирвэл
        form = ZipFileForm(request.POST, request.FILES)  # Form-д өгөгдлийг оноох
        if form.is_valid():# Form зөв бөглөгдсөн бол
            ZipFile.objects.update(is_download=False)  # Өмнөх файлуудыг татаж авахаа больсон болгож update хийх
            zip_instance = form.save(commit=False)  # DB рүү хадгалахгүйгээр instance үүсгэх
            zip_instance.name = request.FILES['file'].name  # Файлын нэр оноох
            zip_instance.is_download = True  # Шинэ файл татаж авах боломжтой болгох
            zip_instance.save()  # DB рүү хадгалах

            return redirect('zip_list')  # Амжилттай бол list рүү чиглүүлэх
    else:
        form = ZipFileForm()  # GET хүсэлт дээр хоосон form үүсгэх
        return render(request, 'zip_file/upload.html', {'form': form})

#file-uudiin jagsaaltiig haruulah, shuuh, erembeleh
def zip_list(request):
    files_list = ZipFile.objects.all().order_by('-upload_date') # Бүх файл, хамгийн сүүлд upload хийсэн эхэнд

    # Get sorting parameters
    sort_by = request.GET.get('sort', 'upload_date')  # URL-аас sort параметр авах
    order = request.GET.get('order', 'desc')  # Default order

    # Determine sorting direction
    sort_prefix = '-' if order == 'desc' else ''
    files_list = files_list.order_by(f"{sort_prefix}{sort_by}")  # Эрэмбэлэх

    # Get filter values
    file_name = request.GET.get('file_name', '')
    version = request.GET.get('version', '')
    upload_date = request.GET.get('upload_date', '')
    download_count = request.GET.get('download_count', '')
    is_download = request.GET.get('is_download', '')

    # Apply filters
    if file_name:
        files_list = files_list.filter(name__icontains=file_name)
    if version:
        files_list = files_list.filter(version__icontains=version)
    if upload_date:
        files_list = files_list.filter(upload_date=upload_date)
    if download_count:
        files_list = files_list.filter(download_count__gte=download_count)
    if is_download:
        files_list = files_list.filter(is_download=(is_download == "True"))

    # Paginate results
    paginator = Paginator(files_list, 10) # 10 файл тутамд 1 хуудас
    page_number = request.GET.get('page')
    files = paginator.get_page(page_number)

    return render(request, 'zip_file/zip_list.html', {
        'files': files,
        'file_name': file_name,
        'version': version,
        'upload_date': upload_date,
        'download_count': download_count,
        'is_download': is_download,
        'sort': sort_by,
        'order': order
    })

#hamgiin suuld upload hiisen file-iig tataj avah
def download_latest_zip(request):
    # Сүүлд татах боломжтой ZipFile-ийг авна
    zip_file = ZipFile.objects.filter(is_download=True).order_by('-upload_date').first()
    if not zip_file:
        return HttpResponse("No files available for download.", status=404)

    # User Agent мэдээлэл задлах
    user_agent = request.META.get('HTTP_USER_AGENT', '')
    parsed_ua = parse(user_agent)
    os_info = f"{parsed_ua.os.family} {parsed_ua.os.version_string} - {parsed_ua.device.family}"

    # Клиент IP-г авах
    client_ip = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', '')).split(',')[0].strip()

    # IP-аас hostname хайх оролдлого
    device_name = None
    if client_ip and client_ip != "127.0.0.1":
        try:
            device_name = socket.gethostbyaddr(client_ip)[0]
        except (socket.herror, socket.gaierror, socket.timeout):
            device_name = None

    # Frontend-аас hostname ирсэн бол илүүд үзэх
    hostname_from_frontend = request.POST.get("hostname", "").strip()
    if hostname_from_frontend:
        device_name = hostname_from_frontend

    if not device_name:
        device_name = client_ip

    # Хэрэглэгч өмнө амжилттай татсан эсэхийг шалгах
    already_downloaded = DownloadedDevice.objects.filter(
        zip_file__name=zip_file.name,
        zip_file__version=zip_file.version,
        ip_address=client_ip,
        device_name=device_name,
        success=True
    ).exists()

    if already_downloaded:
        return HttpResponse("This file has already been downloaded successfully on this device.", status=403)

    # Файлын замыг тодорхойлох
    file_path = os.path.join(settings.MEDIA_ROOT, str(zip_file.file))
    if not os.path.exists(file_path):
        return HttpResponse("File not found.", status=404)

    # Хадгалах зориулалттай C:\ebarimt хавтсыг үүсгэх
    target_dir = r"C:\ebarimt"
    os.makedirs(target_dir, exist_ok=True)
    target_path = os.path.join(target_dir, zip_file.name)

    # Файлыг хуулж хадгалах
    try:
        shutil.copy2(file_path, target_path)
    except Exception as e:
        return HttpResponse(f"Failed to copy file: {e}", status=500)

    # Таталтын мэдээллийг хадгалах
    DownloadedDevice.objects.create(
        zip_file=zip_file,
        device_name=device_name,
        os_info=os_info,
        ip_address=client_ip,
        success=True
    )

    # Татсан тоогоо нэмэгдүүлэх
    zip_file.download_count += 1
    zip_file.save()

    # Файлыг хэрэглэгчид буцаах
    return FileResponse(open(file_path, 'rb'), as_attachment=True, filename=zip_file.name)

#tataj avsan tuhuurumjuudiin medeelliig haruulna
from datetime import datetime, timedelta


from datetime import datetime, timedelta
from matplotlib.ticker import MultipleLocator

def downloaded_devices(request):
    devices_list = DownloadedDevice.objects.select_related('zip_file').order_by('-download_date')

    # Огноо авах
    selected_date_str = request.GET.get('selected_date', '').strip()
    parsed_date = None
    if selected_date_str:
        try:
            # selected_date-г datetime.date болгож хөрвүүлэх
            parsed_date = datetime.strptime(selected_date_str, "%Y-%m-%d").date()

            # Өдрийн эхлэл ба дараагийн өдрийн эхлэл
            start_datetime = timezone.make_aware(datetime.combine(parsed_date, datetime.min.time()))
            end_datetime = start_datetime + timedelta(days=1)

            # Огноо, цагийн хүрээнд шүүх
            devices_list = devices_list.filter(download_date__gte=start_datetime, download_date__lt=end_datetime)
        except ValueError:
            parsed_date = None

    # Эрэмбэ
    sort_by = request.GET.get('sort', 'download_date')
    order = request.GET.get('order', 'desc')
    sort_prefix = '-' if order == 'desc' else ''
    devices_list = devices_list.order_by(f"{sort_prefix}{sort_by}")

    # Excel export
    if 'export' in request.GET:
        data = devices_list.values_list(
            'zip_file__name',
            'zip_file__version',
            'device_name',
            'os_info',
            'ip_address',
            'download_date',
            'success'
        )
        df = pd.DataFrame(data, columns=[
            'File Name',
            'Version',
            'Device Name',
            'OS Info',
            'IP Address',
            'Download Date',
            'Success'
        ])
        if 'Download Date' in df.columns:
            df['Download Date'] = pd.to_datetime(df['Download Date']).dt.tz_localize(None)

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='Downloaded Devices', index=False)
        response = HttpResponse(
            output.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

    # Upload / Download тоо
    upload_count = ZipFile.objects.filter(upload_date__date=parsed_date).count() if parsed_date else 0
    download_counts = devices_list.aggregate(
        total_downloads=Count('id'),
        success_count=Count('id', filter=models.Q(success=True)),
        failure_count=Count('id', filter=models.Q(success=False)),
    ) if parsed_date else {'total_downloads': 0, 'success_count': 0, 'failure_count': 0}

    # График
    fig, ax = plt.subplots(figsize=(16, 3))
    categories = ['Uploads', 'Downloads Success', 'Downloads Failed']
    values = [upload_count, download_counts['success_count'], download_counts['failure_count']]
    bars = ax.bar(range(len(categories)), values, color=['blue', 'green', 'red'])
    ax.set_xticks(range(len(categories)))
    ax.set_xticklabels(categories)
    max_value = max(values) if values else 0
    step = max(1, max_value // 5)
    ax.set_ylim(0, max_value + step)
    ax.yaxis.set_major_locator(MultipleLocator(step))
    ax.set_ylabel("Count")
    ax.set_title(f"Uploads & Downloads on {parsed_date.strftime('%Y-%m-%d')}" if parsed_date else "No Date Selected")
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width() / 2, height, f'{int(height)}', ha='center', va='bottom')
    img_buffer = io.BytesIO()
    plt.savefig(img_buffer, format="png", bbox_inches="tight")
    plt.close(fig)
    img_buffer.seek(0)
    chart_image = base64.b64encode(img_buffer.getvalue()).decode()

    # Хуудаслалт
    paginator = Paginator(devices_list, 10)
    page_number = request.GET.get('page')
    devices = paginator.get_page(page_number)

    return render(request, 'zip_file/download_devices.html', {
        'devices': devices,
        'selected_date': selected_date_str,
        'chart_image': chart_image if parsed_date else None,
        'sort': sort_by,
        'order': order
    })



