from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.contrib import messages
from django.http import JsonResponse
from django.urls import reverse
from django.db import IntegrityError
from django.core.exceptions import ValidationError
from django.db.models import Q, Sum
from django.contrib.contenttypes.models import ContentType
from tasks.models import Task
from .models import Customer, Phone
from .forms import CustomerForm, Phoneform
from django.db import transaction
from activity_logs.models import ActivityLog

def log_activity(user, action, obj):
    ActivityLog.objects.create(
        user=user,
        action=action,
        content_type=ContentType.objects.get_for_model(obj),
        object_id=obj.pk
    )

@login_required    
def customers_data(request):
    draw = int(request.GET.get("draw", 1))
    start = int(request.GET.get("start", 0))
    length = int(request.GET.get("length", 10))
    search_value = request.GET.get("search[value]", "").strip()

    qs = Customer.objects.all()

    if search_value:
        qs = qs.filter(
            Q(customer_name__icontains=search_value) |
            Q(account_number__icontains=search_value) |
            Q(company__icontains=search_value) |
            Q(customer_phone__icontains=search_value)
        )

    total_records = Customer.objects.count()
    filtered_records = qs.count()

    data = []
    for customer in qs[start:start+length]:
        view_url = reverse('customers:customer_detail', args=[customer.customer_id])
        edit_url = reverse('customers:customer_edit', args=[customer.customer_id])

        data.append({
            'account_number': customer.account_number,
            'customer_name': f'<a href="{view_url}">{customer.customer_name}</a>',
            'company': customer.company,
            'customer_phone': f"{customer.country_code.country_phone_code if customer.country_code else ''} {customer.customer_phone}",
            'customer_address': customer.customer_address,
            'email': customer.email,
            'tax_number': customer.tax_number,
            'view': f'<a href="{view_url}" class="btn btn-sm btn-outline-info"><i class="fa fa-eye"></i></a>',
            'edit': f'<a href="{edit_url}" class="btn btn-sm btn-outline-primary"><i class="fa fa-edit"></i></a>',
        })

    return JsonResponse({
        "draw": draw,
        "recordsTotal": total_records,
        "recordsFiltered": filtered_records,
        "data": data
    })

@login_required
def customers_list(request):
    customers = Customer.objects.all().order_by('customer_name')

    # Server-side pagination
    page_number = request.GET.get('page', 1)
    paginator = Paginator(customers, 50)  # 🔁 50 per page

    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'paginator': paginator,
        'nav_title': 'Customers',
    }

    return render(request, 'customers/customers-list.html', context)

@login_required
def customer_detail(request, pk):
    form = Phoneform()
    customer = get_object_or_404(Customer, pk=pk)
    customer_tasks = Task.objects.filter(customer_name=customer).order_by('-created_at')

    # ✅ Get all additional phones related to this customer
    additional_phones = Phone.objects.filter(customer=customer)

    phone_forms = {phone.id: Phoneform(instance=phone) for phone in additional_phones}

    context = {
        'customer': customer,
        'customer_tasks': customer_tasks,
        'form': form,
        'additional_phones': additional_phones,
        'phone_forms': phone_forms,
        'nav_title': 'Customer Detail',
    }
    return render(request, 'customers/customer-detail.html', context)


def customer_edit(request, pk):
    customer = get_object_or_404(Customer, pk=pk)

    if request.method == 'POST':
        form = CustomerForm(request.POST, request.FILES, instance=customer)
        if form.is_valid():
            form.save()
            messages.success(request, 'Customer info updated successfully.')
            return redirect('customers:customer_detail', pk=customer.pk)
    else:
        form = CustomerForm(instance=customer)

    return render(request, 'customers/edit-customer.html', {'form': form, 'customer': customer, 'nav_title': 'Edit Customer',})


@login_required
def add_customer_modal(request):
    if request.method == 'POST':
        form = CustomerForm(request.POST, request.FILES)

        if form.is_valid():
            try:
                customer = form.save(commit=False)
                customer.created_by = request.user
                customer.save()

                # ✅ Log the creation
                log_activity(request.user, f'Created new customer "{customer.customer_name}" via modal', customer)

                # ✅ Store ID of newly created customer
                request.session['new_customer_id'] = customer.pk

                messages.success(request, f'Customer "{customer.customer_name}" added successfully.')
                return redirect(request.POST.get('next') or 'task-add')

            except IntegrityError as e:
                if 'unique_non_null_email' in str(e):
                    messages.error(request, "A customer with this email already exists.")  # ✅ Correct usage
                else:
                    messages.error(request, "An unexpected error occurred while saving the customer.")
                return redirect(request.POST.get('next') or 'task-add')  # ✅ don't lose the message

        # If form is invalid (validation errors from clean_email, etc.)
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(request, f"{field.capitalize()}: {error}")  # ✅ collect form validation errors

        return redirect(request.POST.get('next') or 'task-add')

    return redirect('task-add')


@login_required
def add_customer(request):
    if request.method == 'POST':
        form = CustomerForm(request.POST, request.FILES)

        if form.is_valid():
            cleaned_data = form.cleaned_data
            name = cleaned_data.get('customer_name')
            phone = cleaned_data.get('customer_phone')
            email = cleaned_data.get('email')  # May be None or blank — that's OK

            # ✅ Required field check (although `CustomerForm` handles this)
            if not name or not phone:
                if not name:
                    messages.error(request, 'Customer name is required.')
                if not phone:
                    messages.error(request, 'Phone number is required.')

            else:
                # ✅ Check uniqueness only if email is provided
                duplicates = Customer.objects.filter(
                    Q(customer_phone=phone) | (Q(email=email) if email else Q())
                )

                if duplicates.exists():
                    if duplicates.filter(customer_phone=phone).exists():
                        form.add_error('customer_phone', 'Phone number already exists.')

                    if email and duplicates.filter(email=email).exists():
                        form.add_error('email', 'Email already exists.')

                else:
                    try:
                        customer = form.save(commit=False)
                        customer.created_by = request.user
                        customer.save()

                        # ✅ Log the creation
                        log_activity(request.user, f'Created new customer "{customer.customer_name}"', customer)

                        messages.success(request, f'Customer "{customer.customer_name}" added successfully ✅')
                        return redirect('customers:customers_list')

                    except IntegrityError as e:
                        error_msg = str(e).lower()
                        if 'unique_non_null_email' in error_msg:
                            form.add_error('email', 'A customer with this email already exists.')
                        elif 'unique constraint' in error_msg and 'customer_phone' in error_msg:
                            form.add_error('customer_phone', 'A customer with this phone number already exists.')
                        else:
                            form.add_error(None, 'An unknown error occurred while saving the customer.')

        else:
            messages.error(request, 'Please correct the errors below.')

    else:
        form = CustomerForm()

    return render(request, 'customers/add-customer.html', {'form': form, 'nav_title': 'Add Customer',})

@login_required
def add_phone(request):
    if request.method == 'POST':
        form = Phoneform(request.POST)
        customer_id = request.POST.get('customer')
        customer = get_object_or_404(Customer, customer_id=customer_id)
        if form.is_valid():
            new_phone = form.save(commit=False)
            new_phone.customer = customer
            new_phone.save()

            # ✅ Log the phone addition
            log_activity(
                request.user,
                f'Added phone {new_phone.customer_phone} to customer "{customer.customer_name}"',
                new_phone
            )

            messages.success(request, 'Phone Added successfully.')
            return redirect('customers:customer_detail', pk=customer.pk)
        else:
            print(form.errors)



@login_required
def edit_phone(request, pk):
    phone = get_object_or_404(Phone, pk=pk)
    customer = phone.customer

    if request.method == 'POST':
        form = Phoneform(request.POST, instance=phone)
        if form.is_valid():
            form.save()

            # ✅ Log BEFORE deletion
            log_activity(
                request.user,
                f'edited phone {phone.customer_phone} ({phone.name}) for customer {customer.customer_name}',
                phone
            )
            messages.success(request, 'Phone updated successfully.')
            return redirect('customers:customer_detail', pk=customer.pk)
    else:
        form = Phoneform(instance=phone)

    return render(request, 'customers/modals/edit-phone-modal.html', {
        'form': form,
        'phone': phone,
        'customer': customer
    })


@login_required
def delete_phone(request):
    if request.method == 'POST':
        phone_id = request.POST.get('phone')
        phone = get_object_or_404(Phone, id=phone_id)
        customer = phone.customer
        # ✅ Log BEFORE deletion
        log_activity(
            request.user,
            f'Deleted phone {phone.customer_phone} ({phone.name}) for customer {customer.customer_name}',
            phone
        )
        phone.delete()
        
        messages.success(request, 'Phone Deleted successfully.')
        return redirect('customers:customer_detail', pk=customer.pk)
    

@login_required
def merge_customers_view(request):
    customers = Customer.objects.all().order_by('customer_name')

    if request.method == 'POST':
        selected_ids = request.POST.getlist('merge_ids')
        primary_id = request.POST.get('primary_id')
        if not selected_ids or not primary_id:
            messages.error(request, "Please select customers and primary.")
            return redirect('customers:merge_customers')

        if primary_id not in selected_ids:
            messages.error(request, "Primary must be among selected.")
            return redirect('customers:merge_customers')

        selected_ids.remove(primary_id)

        try:
            with transaction.atomic():
                primary = Customer.objects.get(pk=primary_id)
                merged_names = []
                
                for cid in selected_ids:
                    duplicate = Customer.objects.get(pk=cid)
                    merged_names.append(duplicate.customer_name)

                    # Reassign tasks
                    Task.objects.filter(customer_name=duplicate).update(customer_name=primary)

                    # Transfer phones - preserve as additional phones
                    if duplicate.customer_phone:
                        # Check if phone already exists as additional phone
                        if not Phone.objects.filter(
                            customer=primary, 
                            customer_phone=duplicate.customer_phone
                        ).exists():
                            Phone.objects.create(
                                customer=primary,
                                customer_phone=duplicate.customer_phone,
                                country_code=duplicate.country_code,
                                name=f"Merged from {duplicate.customer_name}"
                            )

                    # Transfer additional phones
                    for phone in Phone.objects.filter(customer=duplicate):
                        phone.customer = primary
                        phone.save()

                    # Merge notes
                    if duplicate.notes:
                        primary.notes = (primary.notes or '') + f"\n[Merged from {duplicate.customer_name}]:\n{duplicate.notes}"

                    duplicate.delete()

                primary.save()

                # 🟢 Improved LOGGING
                action_message = (
                    f"Merged customers: {', '.join(merged_names)} "
                    f"into primary customer: {primary.customer_name} (ID: {primary.customer_id})"
                )
                ActivityLog.objects.create(
                    user=request.user,
                    action=action_message,
                    content_type=ContentType.objects.get_for_model(Customer),
                    object_id=primary.customer_id
                )

                messages.success(request, f"Successfully merged {len(merged_names)} customers into {primary.customer_name}")
                return redirect('customers:merge_customers')

        except Exception as e:
            messages.error(request, f"Error during merge: {e}")

    return render(request, 'customers/merge-customers.html', {'customers': customers, 'nav_title': 'Merge Customers',})


    
