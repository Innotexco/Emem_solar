from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


class Profile(models.Model):
    CATEGORY_CHOICES = [
        ('Retail', 'Installer'),
        ('Whole Sale', 'Distributor'),
        ('End User', 'End User'),
    ]
    
    VERIFICATION_STATUS = [
        ('pending', 'Pending Verification'),
        ('verified', 'Verified'),
        ('rejected', 'Rejected'),
        ('not_required', 'Not Required'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone = models.CharField(max_length=20)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='End User')
    chosen_category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, blank=True, null=True)  # Original choice
    customer_id = models.CharField(max_length=100, blank=True, null=True)
    verification_status = models.CharField(
        max_length=20, 
        choices=VERIFICATION_STATUS, 
        default='not_required'
    )
    rejection_reason = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.category}"
    
    def is_verified(self):
        """Check if user is verified or verification not required"""
        return self.verification_status in ['verified', 'not_required']
    
    def requires_verification(self):
        """Check if category requires verification"""
        return self.chosen_category in ['Retail', 'Whole Sale'] if self.chosen_category else False
    
    def get_actual_category(self):
        """Get the category user actually wants (chosen_category) or current category"""
        return self.chosen_category if self.chosen_category else self.category


class VerificationImage(models.Model):
    IMAGE_TYPES = [
        ('warehouse', 'Warehouse/Outlet'),
        ('installation', 'Previous Installation'),
    ]
    
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='verification_images')
    image = models.ImageField(upload_to='verification_images')
    image_type = models.CharField(max_length=20, choices=IMAGE_TYPES)
    caption = models.CharField(max_length=255, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['uploaded_at']

    def __str__(self):
        return f"{self.profile.user.username} - {self.image_type}"


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()

