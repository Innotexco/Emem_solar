from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import requests
import json
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_POST
from account.models import  Profile
from django.contrib.admin.views.decorators import staff_member_required
from .models import PickupStation, StockAlert, Order, OrderItem
from django.db.models import Count, Q, Sum
from datetime import datetime, timedelta
import os
import requests
from django.conf import settings
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime
from django.contrib.admin.views.decorators import staff_member_required

# Create your views here.
def home(request):
    return render(request, 'main/index.html')

def about(request):
    return render(request, 'main/about.html')

def products(request):
    stock_date = StockAlert.objects.first()
    return render(request, 'main/products.html', {'stock_date': stock_date})

def contact(request):
    return render(request, 'main/contact.html')


def get_pickup_stations(request):
    """API endpoint to get all active pickup stations"""
    state = request.GET.get('state', None)
    
    stations = PickupStation.objects.filter(is_active=True)
    
    if state:
        stations = stations.filter(state=state)
    
    stations_data = []
    for station in stations:
        stations_data.append({
            'id': station.id,
            'name': station.name,
            'address': station.address,
            'city': station.city,
            'state': station.state,
            'phone': station.phone,
            'email': station.email,
            'opening_hours': station.opening_hours
        })
    
    return JsonResponse({
        'success': True,
        'stations': stations_data
    })

def get_cart(request):
    """Get cart from session"""
    return request.session.get('cart', {})

def save_cart(request, cart):
    """Save cart to session"""
    request.session['cart'] = cart
    request.session.modified = True


def get_user_price(user, item_data):
    """
    Get price based on user category
    Categories: 'Retail', 'Whole Sale', 'End User'
    Returns the appropriate price field
    """
    if not user.is_authenticated:
        # Default to retail price for non-authenticated users
        return float(item_data.get('selling_price', 0))
    
    try:
        profile = user.profile
        category = profile.category
        
        # Map categories to price fields from your API
        if category == 'Retail':  # Installer
            return float(item_data.get('retailer_price', item_data.get('selling_price', 0)))
        elif category == 'Whole Sale':  # Distributor
            return float(item_data.get('wholesale_price', item_data.get('selling_price', 0)))
        elif category == 'End User':
            return float(item_data.get('selling_price', 0))
        else:
            return float(item_data.get('selling_price', 0))
    except:
        # If no profile or error, return default price
        return float(item_data.get('selling_price', 0))

@require_POST
def add_to_cart(request):
    """Add item to cart via AJAX"""
    try:
        data = json.loads(request.body)
        item_id = data.get('item_id')
        quantity = int(data.get('quantity', 1))
        name = data.get('name', '')
        image = data.get('image', '')
        
        # Get all three price tiers from the request
        retailer_price = data.get('retailer_price', '0')
        wholesaler_price = data.get('wholesale_price', '0')
        selling_price = data.get('selling_price', '0')
        
        print(f"Adding to cart - Item: {name}")
        print(f"Retailer: {retailer_price}, Wholesaler: {wholesaler_price}, Selling: {selling_price}")
        
        # Get cart from session
        cart = get_cart(request)
        
        # Add or update item in cart
        if item_id in cart:
            cart[item_id]['quantity'] += quantity
        else:
            # Store all three price tiers
            cart[item_id] = {
                'quantity': quantity,
                'name': name,
                'image': image,
                'retailer_price': retailer_price,
                'wholesale_price': wholesaler_price,
                'selling_price': selling_price
            }
        
        save_cart(request, cart)
        
        # Calculate cart total items
        total_items = sum(item['quantity'] for item in cart.values())
        
        print(f"Cart updated successfully. Total items: {total_items}")
        
        return JsonResponse({
            'success': True,
            'message': 'Item added to cart',
            'cart_count': total_items
        })
    except Exception as e:
        print(f"Error in add_to_cart: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)
    

@require_POST
def update_cart(request):
    """Update cart item quantity"""
    try:
        data = json.loads(request.body)
        item_id = data.get('item_id')
        quantity = int(data.get('quantity'))
        
        cart = get_cart(request)
        
        if quantity <= 0:
            cart.pop(item_id, None)
        elif item_id in cart:
            cart[item_id]['quantity'] = quantity
        
        save_cart(request, cart)
        
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

@require_POST
def remove_from_cart(request):
    """Remove item from cart"""
    try:
        data = json.loads(request.body)
        item_id = data.get('item_id')
        
        cart = get_cart(request)
        cart.pop(item_id, None)
        save_cart(request, cart)
        
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


def view_cart(request):
    """Display cart page"""
    cart = get_cart(request)
    
    # Build cart items from session data
    cart_items = []
    total = 0
    
    for item_id, details in cart.items():
        print(f"Processing item: {item_id}")
        print(f"Details: {details}")
        
        # Determine price based on user category
        if request.user.is_authenticated:
            try:
                profile = request.user.profile
                category = profile.category
                print(f"User category: {category}")
                
                if category == 'Retail':
                    price = float(details.get('retailer_price', details.get('selling_price', 0)))
                elif category == 'Whole Sale':
                    # Note: It's 'wholesaler_price' in the cart but 'wholesale_price' from API
                    price = float(details.get('wholesaler_price', details.get('wholesale_price', details.get('selling_price', 0))))
                else:  # End User
                    price = float(details.get('selling_price', 0))
            except Exception as e:
                print(f"Error getting user profile: {e}")
                price = float(details.get('selling_price', 0))
        else:
            price = float(details.get('selling_price', 0))
        
        print(f"Calculated price: {price}")
        
        quantity = details.get('quantity', 1)
        subtotal = price * quantity
        
        print(f"Quantity: {quantity}, Subtotal: {subtotal}")
        
        # Create a dict that mimics the Item object structure
        cart_items.append({
            'item': {
                'generated_code': item_id,
                'item_name': details.get('name', 'Unknown Item'),
                'selling_price': price,  # This is the category-adjusted price
                'image': details.get('image', '')
            },
            'quantity': quantity,
            'subtotal': subtotal
        })
        total += subtotal
    
    # Get user category for display
    user_category = None
    if request.user.is_authenticated:
        try:
            user_category = request.user.profile.category
        except:
            pass
    
    print(f"Total items: {len(cart_items)}")
    print(f"Total price: {total}")
    print(f"User category: {user_category}")
    
    context = {
        'cart_items': cart_items,
        'total': total,
        'cart_count': sum(item['quantity'] for item in cart.values()),
        'user_category': user_category
    }
    
    return render(request, 'main/cart.html', context)

def cart_count(request):
    """Return cart count as JSON"""
    cart = get_cart(request)
    total_items = sum(item.get('quantity', 0) for item in cart.values())
    return JsonResponse({'count': total_items})

# ============================================
# ORDER NOW (Direct Purchase)
# ============================================

def order_now(request, item_id):
    """Direct purchase of a single item"""
    try:
        api_url = 'http://127.0.0.1:8000/api/item_api/'
        response = requests.get(api_url)
        response.raise_for_status()  # Raise an error for bad responses
        items = response.json()

        # Find the specific item using generated_code
        item = None
        if isinstance(items, list):
            item = next((i for i in items if i.get('generated_code') == item_id), None)
        elif isinstance(items, dict) and items.get('generated_code') == item_id:
            item = items

        if not item:
            messages.error(request, 'Item not found.')
            return redirect('main:products')

    except Exception as e:
        messages.error(request, f'Error fetching item: {str(e)}')
        return redirect('main:products')

    item_id = item.get('generated_code')

    if request.user.is_authenticated:
        # User is logged in, go straight to checkout using generated_code
        return redirect('main:checkout_item', item_id=item_id)
    else:
        # User not logged in, redirect to login with next parameter
        return redirect(f'/account/login/?next=/order/{item_id}/')




@login_required(login_url='account:login')
def checkout(request, item_id=None):
    """Checkout page for cart or single item with Sales Invoice API integration"""
    
    items = []
    total = 0
    
    if item_id:
        # Single item checkout (Order Now) - fetch from API
        try:
            api_url = 'http://127.0.0.1:8000/api/item_api/'
            response = requests.get(api_url, timeout=10)
            all_items = response.json()
            
            # Find the specific item
            item_data = None
            if isinstance(all_items, list):
                item_data = next((i for i in all_items if i.get('generated_code') == item_id), None)
            else:
                if all_items.get('generated_code') == item_id:
                    item_data = all_items
            
            if item_data:
                price = float(item_data.get('selling_price', 0))
                purchase_price = float(item_data.get('Purchase_Price', price * 0.8))
                
                items = [{
                    'item': {
                        'generated_code': item_data.get('generated_code'),
                        'item_name': item_data.get('item_name'),
                        'description': item_data.get('description', ''),
                        'selling_price': price,
                        'purchase_price': purchase_price,
                        'image': item_data.get('image', '')
                    },
                    'quantity': 1,
                    'subtotal': price
                }]
                total = price
        except Exception as e:
            messages.error(request, f'Error fetching item: {str(e)}')
            return redirect('main:products')
    else:
        # Cart checkout - Fetch item details from API
        cart = get_cart(request)
        
        if not cart:
            messages.info(request, 'Your cart is empty')
            return redirect('main:cart')
        
        try:
            # Fetch all items from API
            api_url = 'http://127.0.0.1:8000/api/item_api/'
            response = requests.get(api_url, timeout=10)
            all_items_data = response.json()
            
            # Create a lookup dictionary for quick access
            items_lookup = {}
            if isinstance(all_items_data, list):
                items_lookup = {item['generated_code']: item for item in all_items_data}
            
            # Process cart items with API data
            for cart_item_id, cart_details in cart.items():
                # Get item details from API
                item_data = items_lookup.get(cart_item_id)
                
                if item_data:
                    # Use API data for pricing
                    price = float(item_data.get('selling_price', 0))
                    purchase_price = float(item_data.get('Purchase_Price', price * 0.8))
                    quantity = cart_details.get('quantity', 1)
                    subtotal = price * quantity
                    
                    items.append({
                        'item': {
                            'generated_code': item_data.get('generated_code'),
                            'item_name': item_data.get('item_name', cart_details.get('name', 'Unknown Item')),
                            'description': item_data.get('description', ''),
                            'selling_price': price,
                            'purchase_price': purchase_price,
                            'image': item_data.get('image', cart_details.get('image', ''))
                        },
                        'quantity': quantity,
                        'subtotal': subtotal
                    })
                    total += subtotal
                else:
                    # Fallback to cart data if API fails
                    price = float(cart_details.get('price', cart_details.get('selling_price', 0)))
                    quantity = cart_details.get('quantity', 1)
                    subtotal = price * quantity
                    
                    items.append({
                        'item': {
                            'generated_code': cart_item_id,
                            'item_name': cart_details.get('name', 'Unknown Item'),
                            'description': cart_details.get('description', ''),
                            'selling_price': price,
                            'purchase_price': price * 0.8,
                            'image': cart_details.get('image', '')
                        },
                        'quantity': quantity,
                        'subtotal': subtotal
                    })
                    total += subtotal
        
        except requests.RequestException as e:
            messages.error(request, 'Unable to fetch item details. Please try again.')
            return redirect('main:cart')
    
    # Get user profile
    try:
        profile = request.user.profile
    except Profile.DoesNotExist:
        profile = None
    
    if request.method == 'POST':
        # Process checkout
        delivery_method = request.POST.get('delivery_method', 'home')
        shipping_address = request.POST.get('shipping_address', '')
        pickup_station_id = request.POST.get('pickup_station_id', '')
        phone = request.POST.get('phone')
        notes = request.POST.get('notes', '')
        
        # Validate required fields
        if delivery_method == 'home' and not shipping_address:
            messages.error(request, 'Shipping address is required for home delivery')
            return render(request, 'main/checkout.html', {
                'items': items,
                'total': total,
                'user': request.user,
                'profile': profile
            })
        
        if delivery_method == 'pickup' and not pickup_station_id:
            messages.error(request, 'Please select a pickup station')
            return render(request, 'main/checkout.html', {
                'items': items,
                'total': total,
                'user': request.user,
                'profile': profile
            })
        
        try:
            # Create local order first
            order = Order.objects.create(
                user=request.user,
                customer_id=profile.customer_id if profile else None,
                total_amount=total,
                delivery_method=delivery_method,
                shipping_address=shipping_address if delivery_method == 'home' else None,
                pickup_station_id=pickup_station_id if delivery_method == 'pickup' else None,
                phone=phone,
                notes=notes,
                status='cancelled',
                payment_status='cancelled'
            )
            
            # Create order items
            for item_data in items:
                OrderItem.objects.create(
                    order=order,
                    item_id=item_data['item']['generated_code'],
                    item_name=item_data['item']['item_name'],
                    quantity=item_data['quantity'],
                    price=item_data['item']['selling_price']
                )
            
            # Initialize Paystack payment
            paystack_data = {
                'email': request.user.email,
                'amount': int(total * 100),  # Paystack amount in kobo
                'reference': f"ORD-{order.id}-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                'callback_url': request.build_absolute_uri('/payment/callback/'),
                'metadata': {
                    'order_id': order.id,
                    'customer_name': request.user.get_full_name(),
                    'phone': phone
                }
            }
            
            paystack_response = requests.post(
                'https://api.paystack.co/transaction/initialize',
                headers={
                    # 'Authorization': f'Bearer {os.getenv("PAYSTACK_SECRET_KEY")}',
                    'Authorization': f'Bearer {settings.PAYSTACK_SECRET_KEY}',
                    'Content-Type': 'application/json'
                },
                json=paystack_data,
                timeout=10
            )
            
            if paystack_response.status_code == 200:
                payment_data = paystack_response.json()
                
                if payment_data.get('status'):
                    # Save payment reference
                    order.payment_reference = paystack_data['reference']
                    order.save()
                    
                    # Redirect to Paystack payment page
                    return redirect(payment_data['data']['authorization_url'])
                else:
                    messages.error(request, 'Payment initialization failed')
            else:
                messages.error(request, f'Unable to process payment: {paystack_response.text}')
            
        except Exception as e:
            messages.error(request, f'Error processing order: {str(e)}')
    
    context = {
        'items': items,
        'total': total,
        'user': request.user,
        'profile': profile
    }
    
    return render(request, 'main/checkout.html', context)


@login_required(login_url='account:login')
def payment_callback(request):
    """Handle Paystack payment callback"""
    
    reference = request.GET.get('reference')
    
    if not reference:
        messages.error(request, 'Invalid payment reference')
        return redirect('main:checkout')
    
    try:
        # Verify payment with Paystack
        verify_response = requests.get(
            f'https://api.paystack.co/transaction/verify/{reference}',
            headers={
                'Authorization': f'Bearer {settings.PAYSTACK_SECRET_KEY}',
            },
            timeout=10
        )
        
        if verify_response.status_code == 200:
            payment_data = verify_response.json()
            
            if payment_data.get('status') and payment_data['data']['status'] == 'success':
                # Get order
                order_id = payment_data['data']['metadata']['order_id']
                order = Order.objects.get(id=order_id)
                
                # Update order payment status
                order.payment_status = 'paid'
                order.status = 'success'
                order.save()
                
                # Now create invoice via Sales Invoice API
                # invoice_created = create_sales_invoice_from_order(order, customer=order.customer_id)
                invoice_created = create_sales_invoice_from_order(request, order, customer=order.customer_id)
                
                if invoice_created:
                    # Clear cart if it was a cart checkout
                    request.session['cart'] = {}
                    request.session.modified = True
                    
                    messages.success(request, 'Payment successful! Your order is being processed.')
                    return redirect('main:products')
                else:
                    messages.warning(request, 'Payment received but invoice creation failed. Our team will contact you.')
                    return redirect('main:products')
            else:
                messages.error(request, 'Payment verification failed')
        else:
            messages.error(request, 'Unable to verify payment')
    
    except Order.DoesNotExist:
        messages.error(request, 'Order not found')
    except Exception as e:
        messages.error(request, f'Error processing payment: {str(e)}')
    
    return redirect('main:products')



def to_decimal(value):
    """Return a Decimal rounded to 2 decimal places"""
    return Decimal(str(value)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

def create_sales_invoice_from_order(request, order, customer):
    """Create sales invoice via API after successful payment"""
    user = order.user
    try:
        # Get order items
        order_items = OrderItem.objects.filter(order=order)
        
        # Calculate totals
        sub_total = to_decimal(order.total_amount)
        vat = to_decimal(sub_total * Decimal('0.075'))
        shipping_cost = to_decimal(0)
        total = to_decimal(sub_total + vat + shipping_cost)
        
        # Prepare items for API
        items_data = []
        for item in order_items:
            purchase_price = to_decimal(Decimal(item.price) * Decimal('0.8'))
            unit_price = to_decimal(item.price)
            amount = to_decimal(Decimal(item.price) * item.quantity)
            items_data.append({
                'itemcode': item.item_id,
                'item_name': item.item_name,
                'item_description': '',
                'qty': item.quantity,
                'unit': str(unit_price),
                'discount': '0.00',
                'amount': str(amount),
                'purchaseP': str(purchase_price)  # Estimate purchase price
            })
        
        # Prepare invoice data
        invoice_date = datetime.now().date()
        due_date = invoice_date + timedelta(days=30)
        
        invoice_data = {
            'cusID': order.customer_id if order.customer_id else 1,
            'accountType': 'Customer',
            'customer_name': user.get_full_name() or user.username,
            'invoice_date': invoice_date.strftime('%Y-%m-%d'),
            'due_date': due_date.strftime('%Y-%m-%d'),
            'invoiceID': f'INV-{order.id}-{datetime.now().strftime("%Y%m%d%H%M%S")}',
            'order_id': str(order.id),
            'Gdescription': f'Solar battery purchase - Order #{order.id}',
            'invoice_state': False,  # Supplied
            'credit_sales': False,  # Paid via Paystack
            'payment_method': 'Transfer',
            # 'shipping_method': 'Home Delivery' if order.delivery_method == 'home' else 'Pickup',
            'shipping_address':  '',
            # 'shipping_cost': str(shipping_cost),
            'vat': str(vat),
            'sub_total': str(sub_total),
            'total': str(total),
            'items': items_data
        }
        
        # Call Sales Invoice API
        api_url = 'http://127.0.0.1:8000/api/create/'
        
        response = requests.post(
            api_url,
            json=invoice_data,
            headers={'Content-Type': 'application/json'},
            timeout=15
        )
        
        if response.status_code == 201:
            invoice_response = response.json()
            order.invoice_id = invoice_response.get('invoiceID')
            order.save()
            return True
        else:
            print(f'Invoice API Error: {response.text}')
            return False
    
    except Exception as e:
        print(f'Error creating invoice: {str(e)}')
        return False
    """Create sales invoice via API after successful payment"""
    
    try:
        # Get order items
        order_items = OrderItem.objects.filter(order=order)
        
        # Calculate totals
        sub_total = float(order.total_amount)
        vat = sub_total * 0.075  # 7.5% VAT
        shipping_cost = 0  # Add your shipping cost logic here
        total = sub_total + vat + shipping_cost
        
        # Prepare items for API
        items_data = []
        for item in order_items:
            items_data.append({
                'itemcode': item.item_id,
                'item_name': item.item_name,
                'item_description': '',
                'qty': item.quantity,
                'unit': str(item.price),
                'discount': '0.00',
                'amount': str(item.price * item.quantity),
                'purchaseP': str(item.price * 0.8)  # Estimate purchase price
            })
        
        # Prepare invoice data
        invoice_date = datetime.now().date()
        due_date = invoice_date + timedelta(days=30)
        
        invoice_data = {
            'cusID': order.customer_id if order.customer_id else 1,  # Default customer ID
            'accountType': 'Customer',
            'customer_name': user.get_full_name() or user.username,
            'invoice_date': invoice_date.strftime('%Y-%m-%d'),
            'due_date': due_date.strftime('%Y-%m-%d'),
            'invoiceID': f'INV-{order.id}-{datetime.now().strftime("%Y%m%d%H%M%S")}',
            'order_id': str(order.id),
            'Gdescription': f'Solar battery purchase - Order #{order.id}',
            'invoice_state': False,  # Supplied
            'credit_sales': False,  # Paid via Paystack
            'payment_method': 'Transfer',  # Paystack = Bank Transfer
            'shipping_method': 'Home Delivery' if order.delivery_method == 'home' else 'Pickup',
            'shipping_address': order.shipping_address or '',
            'shipping_cost': str(shipping_cost),
            'vat': str(vat),
            'sub_total': str(sub_total),
            'total': str(total),
            'items': items_data
        }
        
        # Call Sales Invoice API
        api_url = 'http://127.0.0.1:8000/api/create/'
        
        response = requests.post(
            api_url,
            json=invoice_data,
            headers={
                'Content-Type': 'application/json',
                # Add authentication if needed
            }
        )
        
        if response.status_code == 201:
            invoice_response = response.json()
            
            # Save invoice ID to order
            order.invoice_id = invoice_response.get('invoiceID')
            order.save()
            
            return True
        else:
            print(f'Invoice API Error: {response.text}')
            return False
    
    except Exception as e:
        print(f'Error creating invoice: {str(e)}')
        return False


# ============================================
# ORDER CONFIRMATION
# ============================================

@login_required(login_url='account:login')
def order_confirmation(request, order_id):
    """Order confirmation page"""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    context = {
        'order': order
    }
    
    return render(request, 'main/order_confirmation.html', context)





@staff_member_required
def admin_dashboard(request):
    """Main admin dashboard"""
    # Statistics
    total_stations = PickupStation.objects.filter(is_active=True).count()
    total_orders = Order.objects.count()
    pending_orders = Order.objects.filter(status='pending').count()
    pickup_orders = Order.objects.filter(delivery_method='pickup').count()
    
    # Recent orders
    recent_orders = Order.objects.select_related('user', 'pickup_station').order_by('-created_at')[:10]
    
    # Active stock alerts
    active_alerts = StockAlert.objects.filter(is_active=True).order_by('expected_date')[:5]
    
    # Orders by delivery method
    orders_by_method = Order.objects.values('delivery_method').annotate(count=Count('id'))
    
    context = {
        'total_stations': total_stations,
        'total_orders': total_orders,
        'pending_orders': pending_orders,
        'pickup_orders': pickup_orders,
        'recent_orders': recent_orders,
        'active_alerts': active_alerts,
        'orders_by_method': orders_by_method,
    }
    
    return render(request, 'main/dashboard.html', context)


@staff_member_required
def manage_pickup_stations(request):
    """Manage pickup stations"""
    stations = PickupStation.objects.all().order_by('state', 'city')
    
    # Search functionality
    search = request.GET.get('search', '')
    if search:
        stations = stations.filter(
            Q(name__icontains=search) | 
            Q(city__icontains=search) | 
            Q(state__icontains=search)
        )
    
    # Filter by state
    state_filter = request.GET.get('state', '')
    if state_filter:
        stations = stations.filter(state=state_filter)
    
    # Get all states for filter dropdown
    all_states = PickupStation.objects.values_list('state', flat=True).distinct()
    
    context = {
        'stations': stations,
        'all_states': all_states,
        'search': search,
        'state_filter': state_filter,
    }
    
    return render(request, 'main/pickup_station.html', context)


@staff_member_required
def add_pickup_station(request):
    """Add new pickup station"""
    if request.method == 'POST':
        try:
            PickupStation.objects.create(
                name=request.POST.get('name'),
                address=request.POST.get('address'),
                city=request.POST.get('city'),
                state=request.POST.get('state'),
                phone=request.POST.get('phone'),
                email=request.POST.get('email', ''),
                opening_hours=request.POST.get('opening_hours', 'Mon-Fri: 9AM-5PM'),
                is_active=request.POST.get('is_active') == 'on'
            )
            messages.success(request, 'Pickup station added successfully!')
            return redirect('main:manage_stations')
        except Exception as e:
            messages.error(request, f'Error adding station: {str(e)}')
    
    return render(request, 'main/add_station.html')


@staff_member_required
def edit_pickup_station(request, station_id):
    """Edit pickup station"""
    station = get_object_or_404(PickupStation, id=station_id)
    
    if request.method == 'POST':
        try:
            station.name = request.POST.get('name')
            station.address = request.POST.get('address')
            station.city = request.POST.get('city')
            station.state = request.POST.get('state')
            station.phone = request.POST.get('phone')
            station.email = request.POST.get('email', '')
            station.opening_hours = request.POST.get('opening_hours')
            station.is_active = request.POST.get('is_active') == 'on'
            station.save()
            
            messages.success(request, 'Pickup station updated successfully!')
            return redirect('admin_dashboard:manage_stations')
        except Exception as e:
            messages.error(request, f'Error updating station: {str(e)}')
    
    context = {'station': station}
    return render(request, 'main/edit_station.html', context)


@staff_member_required
def delete_pickup_station(request, station_id):
    """Delete pickup station"""
    station = get_object_or_404(PickupStation, id=station_id)
    
    if request.method == 'POST':
        station_name = station.name
        station.delete()
        messages.success(request, f'Station "{station_name}" deleted successfully!')
        return redirect('main:manage_stations')
    
    context = {'station': station}
    return render(request, 'main/confirm_delete_station.html', context)


@staff_member_required
def manage_stock_alerts(request):
    """Manage stock alerts"""
    alerts = StockAlert.objects.all().order_by('-expected_date')
    
    # Search functionality
    search = request.GET.get('search', '')
    if search:
        alerts = alerts.filter(
            Q(item_name__icontains=search) | 
            Q(item_code__icontains=search)
        )
    
    # Filter by status
    status_filter = request.GET.get('status', '')
    if status_filter == 'active':
        alerts = alerts.filter(is_active=True)
    elif status_filter == 'inactive':
        alerts = alerts.filter(is_active=False)
    
    context = {
        'alerts': alerts,
        'search': search,
        'status_filter': status_filter,
    }
    
    return render(request, 'main/stock_alerts.html', context)


@staff_member_required
def add_stock_alert(request):
    """Add new stock alert"""
    if request.method == 'POST':
        try:
            StockAlert.objects.create(
                expected_date=request.POST.get('expected_date'),
                is_active=request.POST.get('is_active') == 'on',
                created_by=request.user
            )
            messages.success(request, 'Stock alert added successfully!')
            return redirect('main:manage_stock_alerts')
        except Exception as e:
            messages.error(request, f'Error adding stock alert: {str(e)}')
    
    return render(request, 'main/add_stock_alert.html')


@staff_member_required
def edit_stock_alert(request, alert_id):
    """Edit stock alert"""
    alert = get_object_or_404(StockAlert, id=alert_id)
    
    if request.method == 'POST':
        try:
            alert.expected_date = request.POST.get('expected_date')
            alert.is_active = request.POST.get('is_active') == 'on'
            alert.save()
            
            messages.success(request, 'Stock alert updated successfully!')
            return redirect('admin_dashboard:manage_stock_alerts')
        except Exception as e:
            messages.error(request, f'Error updating stock alert: {str(e)}')
    
    context = {'alert': alert}
    return render(request, 'main/edit_stock_alert.html', context)


@staff_member_required
def delete_stock_alert(request, alert_id):
    """Delete stock alert"""
    alert = get_object_or_404(StockAlert, id=alert_id)
    
    if request.method == 'POST':
        alert_name = alert.expected_date
        alert.delete()
        messages.success(request, f'Stock alert for "{alert_name}" deleted successfully!')
        return redirect('main:manage_stock_alerts')
    
    context = {'alert': alert}
    return render(request, 'main/confirm_delete_alert.html', context)


@staff_member_required
def toggle_station_status(request, station_id):
    """Toggle pickup station active status"""
    station = get_object_or_404(PickupStation, id=station_id)
    station.is_active = not station.is_active
    station.save()
    
    status = "activated" if station.is_active else "deactivated"
    messages.success(request, f'Station "{station.name}" {status} successfully!')
    return redirect('admin_dashboard:manage_stations')


# @staff_member_required
# def toggle_alert_status(request, alert_id):
#     """Toggle stock alert active status"""
#     alert = get_object_or_404(StockAlert, id=alert_id)
#     alert.is_active = not alert.is_active
#     alert.save()
    
#     status = "activated" if alert.is_active else "deactivated"
#     messages.success(request, f'Stock alert {status} successfully!')
#     return redirect('admin_dashboard:manage_stock_alerts')

@staff_member_required
def toggle_alert_status(request, alert_id):
    """Toggle stock alert active status"""
    alert = get_object_or_404(StockAlert, id=alert_id)
    alert.is_active = not alert.is_active
    alert.save()
    
    status = "activated" if alert.is_active else "deactivated"
    messages.success(request, f'Stock alert for "{alert.item_name}" {status} successfully!')
    return redirect('main:manage_stock_alerts')


@staff_member_required
def get_states_with_stations(request):
    """API endpoint to get states that have active pickup stations"""
    states = PickupStation.objects.filter(
        is_active=True
    ).values_list('state', flat=True).distinct().order_by('state')
    
    return JsonResponse({
        'success': True,
        'states': list(states)
    })


def view_orders(request):
    """Display all customer orders for the admin panel."""
    orders = Order.objects.select_related('user', 'pickup_station').prefetch_related('items').all()
    cancelled_orders = orders.filter(status='cancelled').count()
    completed_orders = orders.filter(status__in=['success']).count()
    return render(request, 'main/orders_list.html', {'orders': orders, 'cancelled_orders': cancelled_orders, 'completed_orders': completed_orders})


def order_detail(request, order_id):
    """Display a single order and its items."""
    order = get_object_or_404(Order.objects.prefetch_related('items', 'pickup_station'), id=order_id)
    return render(request, 'main/order_detail.html', {'order': order})


@login_required
def customer_dashboard_view(request):
    """Displays the user's dashboard with order stats and recent orders."""
    user = request.user

    # Get all user's orders
    orders = Order.objects.filter(user=user)

    # Stats
    total_orders = orders.count()
    cancelled_orders = orders.filter(status='cancelled').count()
    completed_orders = orders.filter(status__in=['success']).count()
    total_spent = orders.filter(status='success').aggregate(total=Sum('total_amount'))['total'] or 0

    # Recent orders (limit to last 5)
    recent_orders = orders.order_by('-created_at')[:5]

    context = {
        'user': user,
        'total_orders': total_orders,
        'cancelled_orders': cancelled_orders,
        'completed_orders': completed_orders,
        'total_spent': total_spent,
        'recent_orders': recent_orders,
    }

    return render(request, 'main/customer_dashboard.html', context)

@login_required
def my_orders_view(request):
    orders = Order.objects.filter(user=request.user)
    total_orders = orders.count()
    cancelled_orders = orders.filter(status='cancelled').count()
    completed_orders = orders.filter(status__in=['success']).count()
    total_spent = orders.filter(status='success').aggregate(total=Sum('total_amount'))['total'] or 0

    context = {
        'orders': orders,
        'total_orders': total_orders,
        'completed_orders': completed_orders,
        'cancelled_orders': cancelled_orders,
        'total_spent': total_spent,
    }
    return render(request, 'main/my_orders.html', context)


def safe_date_convert(date_str):
    """Convert ISO string from API to datetime object safely."""
    try:
        return datetime.fromisoformat(date_str)
    except:
        return None

def invoice_detail_view(request, invoice_id):
    """
    View to display detailed invoice information
    URL: /invoice/<invoice_id>/
    Public view - no authentication required
    """
    invoice_data = None
    
    try:
        # Fetch invoice from API
        response = requests.get(
            f'http://127.0.0.1:8000/api/invoices/{invoice_id}/',
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                invoice_data = data.get('invoice')
        elif response.status_code == 404:
            return render(request, '404.html', {'message': 'Invoice not found'})
    except Exception as e:
        print(f"Error fetching invoice: {str(e)}")
        return render(request, 'main/500.html', {'message': 'Failed to load invoice'})
    
    if not invoice_data:
        return render(request, 'main/404.html', {'message': 'Invoice not found'})
    
    date_str = invoice_data.get('invoice_date')
    date_str2 = invoice_data.get('due_date')

    # Convert invoice_date
    if date_str:
        converted = safe_date_convert(date_str)
        if converted:
            invoice_data['invoice_date'] = converted

    # Convert due_date
    if date_str2:
        converted2 = safe_date_convert(date_str2)
        if converted2:
            invoice_data['due_date'] = converted2

    context = {
        'invoice': invoice_data,
    }
    
    return render(request, 'main/invoice_detail.html', context)


@login_required
def order_detail_view(request, order_id):
    order = Order.objects.get(id=order_id, user=request.user)
    return render(request, 'main/cus_order_detail.html', {'order': order})


