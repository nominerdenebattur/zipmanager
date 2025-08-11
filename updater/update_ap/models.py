from django.db import models


class ZipFile(models.Model):
    name = models.CharField(max_length=255)
    file = models.FileField(upload_to='zips/')
    upload_date = models.DateTimeField(auto_now_add=True)
    version = models.CharField(max_length=20)
    download_count = models.IntegerField(default=0)
    is_download = models.BooleanField(default=False)

    class Meta:
        unique_together = ('name', 'version')

    def __str__(self):
        return f"{self.name} - {self.version} (Downloadable: {self.is_download})"


class DownloadedDevice(models.Model):
    zip_file = models.ForeignKey(ZipFile, on_delete=models.CASCADE)
    device_name = models.CharField(max_length=255, default="Unknown Device")
    os_info = models.CharField(max_length=255, default="Unknown OS")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    download_date = models.DateTimeField(auto_now_add=True)
    success = models.BooleanField(default=True)

    def __str__(self):
        status = "Successful" if self.success else "Failed"
        return f"{self.device_name} ({self.os_info}) downloaded {self.zip_file.name} ({self.zip_file.version}) - {status}"
