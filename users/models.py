from django.db import models
from PIL import Image
from django.contrib.auth.models import AbstractUser
from django.conf import settings


class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    mobile = models.CharField(max_length=20, blank=True, null=True)
    address = models.CharField(max_length=500, blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', default='profile_pics/default.jpg')
    bio = models.TextField(blank=True, null=True)
    total_jobs = models.PositiveIntegerField(default=0)
    finished_jobs = models.PositiveIntegerField(default=0)
    unfinished_jobs = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"Profile of {self.user.username}"
    
    @property
    def completed_jobs_count(self):
        from tasks.models import Subtask 
        return Subtask.objects.filter(
            user=self.user,
            is_done=True,
            task__status='done',
            task__canceled=False
        ).count()

    @property
    def in_progress_jobs_count(self):
        from tasks.models import Subtask 
        return Subtask.objects.filter(
            user=self.user,
            is_done=False,
            task__status='in_progress',
            task__canceled=False
        ).count()

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        try:
            img = Image.open(self.profile_picture.path)
            if img.height > 400 or img.width > 400:
                img.thumbnail((400, 400))
                img.save(self.profile_picture.path)
        except Exception as e:
            pass  # In production, log this


class CustomUser(AbstractUser):
    
    def get_full_name(self):
        full_name = ''
        if self.first_name and self.last_name:
            full_name = f'{self.first_name} {self.last_name}'
        elif self.first_name:
            full_name = self.first_name
        elif self.last_name:
            full_name = self.last_name
        else:
            full_name = self.username
        return full_name
    
    @property
    def is_project_manager(self):
        from tasks.models import Subtask
        return Subtask.objects.filter(user=self, is_project_manager=True).exists()