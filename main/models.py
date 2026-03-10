from django.db import models

# Create your models here.

from django.contrib.auth.models import User  

class Payment(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('success', 'Success'),
        ('failed', 'Failed'),
    ]
    
    customer = models.ForeignKey(User, on_delete=models.CASCADE)  
    item_id = models.CharField(max_length=100)
    item_name = models.CharField(max_length=200)
    amount = models.DecimalField(max_digits=10, decimal_places=2)  
    reference = models.CharField(max_length=100, unique=True)  
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Payment {self.reference} - {self.status}"

class PickupStation(models.Model):
    """Pickup stations where customers can collect orders"""
    name = models.CharField(max_length=200)
    address = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True, null=True)
    opening_hours = models.CharField(max_length=200, default="Mon-Fri: 9AM-5PM")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['state', 'city', 'name']
    
    def __str__(self):
        return f"{self.name} - {self.city}, {self.state}"

# Update your existing Order model to include pickup station
class Order(models.Model):
    DELIVERY_CHOICES = [
        ('home', 'Home Delivery'),
        ('pickup', 'Pickup Station'),
    ]
    
    STATUS_CHOICES = [
        # ('pending', 'Pending'),
        # ('processing', 'Processing'),
        # ('ready_pickup', 'Ready for Pickup'),
        # ('shipped', 'Shipped'),
        ('success', 'Success'),
        ('cancelled', 'Cancelled'),
    ]


    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    customer_id = models.CharField(max_length=100, blank=True, null=True)
    customer_category = models.CharField(max_length=50, blank=True, null=True)
    
    # Delivery information
    delivery_method = models.CharField(max_length=20, choices=DELIVERY_CHOICES, default='home')
    pickup_station = models.ForeignKey(PickupStation, on_delete=models.SET_NULL, null=True, blank=True)
    shipping_address = models.TextField(blank=True, null=True)
    phone = models.CharField(max_length=20)
    
    # Order details
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    notes = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Order #{self.id} - {self.user.username}"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    item_id = models.CharField(max_length=100)  # generated_code from your item API
    item_name = models.CharField(max_length=255)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.item_name} (x{self.quantity})"

    @property
    def total_price(self):
        """Returns total cost for this item."""
        return self.quantity * self.price






class StockAlert(models.Model):
    """Track when items will be back in stock"""
    expected_date = models.CharField(max_length=200)  
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-expected_date']
    
    def __str__(self):
        return f"Expected: {self.expected_date}"


