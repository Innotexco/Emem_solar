from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from django.contrib.auth.models import User
from django.shortcuts import render, redirect
from django.contrib import messages
from django.db import transaction
from django.conf import settings
import requests
import logging
from .models import * 
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)


def register_user(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        password_confirm = request.POST.get('password_confirm')
        first_name = request.POST.get('first_name', '')
        last_name = request.POST.get('last_name', '')
        phone = request.POST.get('phone', '')
        category = request.POST.get('category')  # This is the chosen category
        
        # Validation
        if not all([username, email, password, password_confirm, category, phone]):
            messages.error(request, 'All required fields must be filled')
            return render(request, 'account/register.html')
        
        if password != password_confirm:
            messages.error(request, 'Passwords do not match')
            return render(request, 'account/register.html')
        
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists')
            return render(request, 'account/register.html')
        
        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email already exists')
            return render(request, 'account/register.html')
        
        try:
            with transaction.atomic():
                # Create user
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=password,
                    first_name=first_name,
                    last_name=last_name
                )
                
                # Update profile
                profile = user.profile
                profile.phone = phone
                profile.chosen_category = category  # Store what they selected
                
                # Set verification status and temporary category
                if category in ['Retail', 'Whole Sale']:
                    profile.verification_status = 'pending'
                    profile.category = 'End User'  # Temporarily End User until verified
                else:
                    profile.verification_status = 'not_required'
                    profile.category = category  # Set actual category immediately
                
                # Create customer via external API
                api_response = create_customer_via_api(user, phone, category)
                
                if api_response['success']:
                    profile.customer_id = api_response['customer_id']
                    profile.save()
                    
                    # Log user in
                    login(request, user)
                    
                    # Redirect based on category
                    if category in ['Retail', 'Whole Sale']:
                        messages.info(
                            request, 
                            'Account created! Please upload verification images to complete your registration.'
                        )
                        return redirect('account:upload_verification_images')
                    else:
                        messages.success(request, 'Registration successful!')
                        return redirect('main:products')
                else:
                    raise Exception(f"API Error: {api_response.get('error', 'Unknown error')}")
                    
        except Exception as e:
            logger.error(f"Registration error: {str(e)}")
            messages.error(request, f'Registration failed: {str(e)}')
            return render(request, 'account/register.html')
    
    return render(request, 'account/register.html')



@login_required
def upload_verification_images(request):
    profile = request.user.profile
    
    # Check if verification is required
    if not profile.requires_verification():
        messages.info(request, 'Verification not required for your account type.')
        return redirect('main:products')
    
    # Check if already verified
    if profile.verification_status == 'verified':
        messages.info(request, 'Your account is already verified.')
        return redirect('main:products')
    
    # Determine image type based on chosen category
    if profile.chosen_category == 'Retail':
        image_type = 'installation'
        image_label = 'Previous Installation'
        image_description = 'Upload up to 5 images of your previous installation work'
    else:  # Whole Sale
        image_type = 'warehouse'
        image_label = 'Warehouse/Outlet'
        image_description = 'Upload up to 5 images of your warehouse or outlet'
    
    existing_images = profile.verification_images.filter(image_type=image_type)
    
    if request.method == 'POST':
        images = request.FILES.getlist('verification_images')
        captions = request.POST.getlist('captions')
        
        # Validation
        if not images:
            messages.error(request, 'Please upload at least one image.')
            return redirect('account:upload_verification_images')
        
        if len(images) > 5:
            messages.error(request, 'You can only upload up to 5 images.')
            return redirect('account:upload_verification_images')
        
        # Check total images including existing
        total_images = existing_images.count() + len(images)
        if total_images > 5:
            messages.error(request, f'You can only have up to 5 images. You already have {existing_images.count()}.')
            return redirect('account:upload_verification_images')
        
        try:
            with transaction.atomic():
                # Save images
                for i, image in enumerate(images):
                    caption = captions[i] if i < len(captions) else ''
                    VerificationImage.objects.create(
                        profile=profile,
                        image=image,
                        image_type=image_type,
                        caption=caption
                    )
                
                # Update profile status
                profile.verification_status = 'pending'
                profile.save()
                
                messages.success(
                    request, 
                    'Images uploaded successfully! Your account is under review. You will be notified once verified.'
                )
                return redirect('account:verification_pending')
                
        except Exception as e:
            logger.error(f"Image upload error: {str(e)}")
            messages.error(request, f'Upload failed: {str(e)}')
    
    context = {
        'profile': profile,
        'image_type': image_type,
        'image_label': image_label,
        'image_description': image_description,
        'existing_images': existing_images,
        'max_images': 5,
        'remaining_slots': 5 - existing_images.count()
    }
    return render(request, 'account/upload_verification_images.html', context)



@login_required
def delete_verification_image(request, image_id):
    image = get_object_or_404(VerificationImage, id=image_id, profile=request.user.profile)
    
    if request.method == 'POST':
        image.delete()
        messages.success(request, 'Image deleted successfully.')
    
    return redirect('account:upload_verification_images')



@login_required
def verification_pending(request):
    profile = request.user.profile
    
    context = {
        'profile': profile,
        'images': profile.verification_images.all()
    }
    return render(request, 'account/verification_pending.html', context)


from django.contrib.admin.views.decorators import staff_member_required

@staff_member_required
def pending_verifications(request):
    pending_profiles = Profile.objects.filter(
        verification_status='pending'
    ).select_related('user').prefetch_related('verification_images').order_by('-created_at')
    
    context = {
        'pending_profiles': pending_profiles
    }
    return render(request, 'account/pending_verifications.html', context)


@staff_member_required
def verify_profile(request, profile_id):
    profile = get_object_or_404(Profile, id=profile_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'approve':
            profile.verification_status = 'verified'
            profile.rejection_reason = None
            
            # Change category to their chosen one
            if profile.chosen_category:
                profile.category = profile.chosen_category
            
            profile.save()
            messages.success(request, f'{profile.user.username} has been verified as {profile.category}.')
            
            # Send approval email
            try:
                subject = 'Your Emem Energy account has been verified'
                
                html_message = render_to_string('account/emails/verification_approved.html', {
                    'user':     profile.user,
                    'category': profile.category,
                })
                
                plain_message = (
                    f"Hi {profile.user.first_name or profile.user.username},\n\n"
                    f"Great news — your Emem Energy account has been verified!\n\n"
                    f"Your account category: {profile.category}\n\n"
                    f"You now have full access to all features and your special pricing tier is active.\n\n"
                    f"Sign in at: https://ememenergy.com/account/login/\n\n"
                    f"— Emem Energy Team"
                )
                
                send_mail(
                    subject,
                    plain_message,
                    settings.DEFAULT_FROM_EMAIL,
                    [profile.user.email],
                    html_message=html_message,
                    fail_silently=False,
                )
            except Exception as e:
                # Don't block the approval if email fails — just log it
                messages.warning(request, f'Account approved but email notification failed: {e}')
                
        elif action == 'reject':
            reason = request.POST.get('reason')
            if not reason:
                messages.error(request, 'Please provide a rejection reason.')
                return redirect('account:verify_profile', profile_id=profile_id)
            
            profile.verification_status = 'rejected'
            profile.rejection_reason = reason
            profile.save()
            messages.warning(request, f'{profile.user.username} has been rejected.')
            
            # Send rejection email
            try:
                subject = 'Update on your Emem Energy verification request'
                
                html_message = render_to_string('account/emails/verification_rejected.html', {
                    'user':   profile.user,
                    'reason': reason,
                })
                
                plain_message = (
                    f"Hi {profile.user.first_name or profile.user.username},\n\n"
                    f"Thank you for submitting your verification request.\n\n"
                    f"Unfortunately, we were unable to approve your request at this time.\n\n"
                    f"Reason: {reason}\n\n"
                    f"Please review the reason above and resubmit with the correct documents.\n\n"
                    f"Upload new images at: https://ememenergy.com/account/upload-verification/\n\n"
                    f"If you have any questions, contact us at info@ememenergy.com\n\n"
                    f"— Emem Energy Team"
                )
                
                send_mail(
                    subject,
                    plain_message,
                    settings.DEFAULT_FROM_EMAIL,
                    [profile.user.email],
                    html_message=html_message,
                    fail_silently=False,
                )
            except Exception as e:
                messages.warning(request, f'Account rejected but email notification failed: {e}')
        
        return redirect('account:pending_verifications')
    
    context = {
        'profile': profile,
        'images':  profile.verification_images.all()
    }
    return render(request, 'account/verify_profile.html', context)
 


@login_required
def update_profile(request):
    profile = get_object_or_404(Profile, user=request.user)
    
    if request.method == 'POST':
        phone = request.POST.get('phone')
        category = request.POST.get('category')
        
        # Check if category is changing to one that requires verification
        old_chosen_category = profile.chosen_category or profile.category
        category_changed = old_chosen_category != category
        
        if category_changed and category in ['Retail', 'Whole Sale']:
            # Reset verification status
            profile.verification_status = 'pending'
            profile.chosen_category = category
            profile.category = 'End User'  # Back to End User until verified
            profile.verification_images.all().delete()  # Remove old images
        elif category_changed:
            # Changing to End User
            profile.category = category
            profile.chosen_category = category
            profile.verification_status = 'not_required'
        
        # Update phone
        profile.phone = phone
        profile.save()
        
        if category_changed and category in ['Retail', 'Whole Sale']:
            messages.info(request, 'Category changed. Please upload verification images.')
            return redirect('account:upload_verification_images')
        
        messages.success(request, 'Your profile has been updated successfully!')
        return redirect('account:update_profile')
    
    context = {'profile': profile}
    return render(request, 'account/update_profile.html', context)


def create_customer_via_api(user, phone, category):
    """
    Create a customer in external system via SECURE API
    """
    API_URL = settings.CUSTOMER_API_URL
    API_KEY = settings.API_KEY
    
    customer_data = {
        'name': user.username,  
        'email': user.email,
        'phone': phone,
        'category': category,
    }
    
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'ApiKey {API_KEY}',  # This is the security!
    }
    
    try:
        response = requests.post(
            API_URL,
            json=customer_data,
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 201:
            response_data = response.json()
            return {
                'success': True,
                'customer_id': response_data.get('customer_id'),
                'message': response_data.get('message'),
                'error': None
            }
        elif response.status_code == 401:
            logger.error("API authentication failed - check API key")
            return {
                'success': False,
                'customer_id': None,
                'error': 'API authentication failed'
            }
        elif response.status_code == 429:
            logger.warning("Rate limit exceeded")
            return {
                'success': False,
                'customer_id': None,
                'error': 'Too many requests. Please try again later.'
            }
        elif response.status_code == 400:
            response_data = response.json()
            return {
                'success': False,
                'customer_id': None,
                'error': response_data.get('error', 'Validation error')
            }
        else:
            logger.error(f"API error: {response.status_code} - {response.text}")
            return {
                'success': False,
                'customer_id': None,
                'error': f"API error: {response.status_code}"
            }
            
    except requests.exceptions.Timeout:
        logger.error("API request timed out")
        return {
            'success': False,
            'customer_id': None,
            'error': 'Request timed out. Please try again.'
        }
    except requests.exceptions.RequestException as e:
        logger.error(f"API request failed: {str(e)}")
        return {
            'success': False,
            'customer_id': None,
            'error': 'Unable to connect to customer service. Please try again later.'
        }


def login_user(request):
    # Redirect if already logged in
    if request.user.is_authenticated:
        if request.user.is_staff or request.user.is_superuser:
            return redirect('main:dashboard')
        else:
            return redirect('main:products')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        remember_me = request.POST.get('remember_me')

        # Validation
        if not all([username, password]):
            messages.error(request, 'Please provide both username and password')
            return render(request, 'account/login.html')

        # Authenticate user
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            
            # Handle "Remember Me"
            if not remember_me:
                request.session.set_expiry(0)  # Session expires on browser close
            else:
                request.session.set_expiry(1209600)  # 2 weeks
            
            messages.success(request, f'Welcome back, {user.first_name or user.username}!')
            
            if request.user.is_staff or request.user.is_superuser:
                return redirect('main:dashboard')
            else:
                return redirect('main:products')

        else:
            messages.error(request, 'Invalid username or password')
            return render(request, 'account/login.html')

    return render(request, 'account/login.html')

# @login_required
# def update_profile(request):
#     profile = get_object_or_404(Profile, user=request.user)

#     if request.method == 'POST':
#         phone = request.POST.get('phone')
#         category = request.POST.get('category')

#         # update fields
#         profile.phone = phone
#         profile.category = category
#         profile.save()

#         messages.success(request, 'Your profile has been updated successfully!')
#         return redirect('account:update_profile')  # reload page

#     context = {'profile': profile}
#     return render(request, 'account/update_profile.html', context)

@login_required
def logout_user(request):
    logout(request)
    messages.success(request, 'You have been logged out successfully')
    return redirect('account:login')
