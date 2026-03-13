from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.core.mail import send_mail, EmailMessage
from django.conf import settings
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist
from django.db import DatabaseError, IntegrityError, transaction
from .models import College, CollegeAdmin, Lab, Professor, Student, Division, Experiment, Submission, Evaluation, Attendance, VivaSession, ExcelUpload
import json
import openpyxl
from io import BytesIO
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def home(request):
    return render(request, "base/home.html")

@login_required
def student_dashboard(request):
    try:
        student = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        return redirect('college_auth') # Or wherever appropriate

    # 1. Fetch Explicitly Assigned Labs
    labs = student.assigned_labs.all()

    # 2. Fetch Attendance Data
    attendance_data = []
    for lab in labs:
        attendances = Attendance.objects.filter(student=student, lab=lab).order_by('date')
        
        dates = [a.date.strftime('%d %b') for a in attendances]
        status_map = {a.date.strftime('%d %b'): ('present' if a.present else 'absent') for a in attendances}
        present_count = attendances.filter(present=True).count()
        total_count = attendances.count()
        percentage = round((present_count / total_count) * 100) if total_count > 0 else 0
        
        attendance_data.append({
            'lab_id': lab.id,
            'lab_name': lab.name,
            'dates': dates,
            'status_map': status_map,
            'percentage': percentage
        })

    # 3. Fetch Marks Data
    marks_data = []
    for lab in labs:
        submissions = Submission.objects.filter(student=student, experiment__lab=lab).select_related('evaluation', 'experiment')
        records = []
        lab_total = 0
        exp_count = 0

        for sub in submissions:
            if hasattr(sub, 'evaluation'):
                viva = sub.evaluation.viva_marks
                exp_marks = sub.evaluation.experiment_marks
                writeup = sub.evaluation.writeup_marks
                total = viva + exp_marks + writeup
                lab_total += total
                exp_count += 1
                records.append({
                    'exp_number': sub.experiment.number,
                    'viva': viva,
                    'exp_marks': exp_marks,
                    'writeup': writeup,
                    'total': total
                })

        average = round(lab_total / exp_count, 2) if exp_count > 0 else 0
        max_possible = exp_count * 15
        percentage = round((lab_total / max_possible) * 100, 2) if max_possible > 0 else 0

        marks_data.append({
            'lab_id': lab.id,
            'lab_name': lab.name,
            'records': records,
            'grand_total': lab_total,
            'average': average,
            'percentage': percentage
        })

    # 4. Fetch Submission History (only new-style submissions with experiment_name)
    history_data = []
    for lab in labs:
        submissions = Submission.objects.filter(
            student=student,
            lab=lab
        ).exclude(experiment_name='').order_by('-submitted_at')
        history_data.append({
            'lab_id': lab.id,
            'lab_name': lab.name,
            'submissions': submissions
        })

    # 5. Handle Upload Experiment (POST)
    if request.method == "POST":
        lab_id = request.POST.get('lab_id')
        experiment_name = request.POST.get('experiment_name', '').strip()
        code_screenshot = request.FILES.get('codeScreenshot')
        output_screenshot = request.FILES.get('outputScreenshot')

        if experiment_name and code_screenshot and output_screenshot and lab_id:
            try:
                lab = Lab.objects.get(id=lab_id)
                Submission.objects.create(
                    student=student,
                    lab=lab,
                    experiment_name=experiment_name,
                    code_screenshot=code_screenshot,
                    output_screenshot=output_screenshot,
                    status='pending'
                )
                messages.success(request, "Experiment submitted successfully!")
            except Lab.DoesNotExist:
                messages.error(request, "Selected lab not found.")
        else:
            messages.error(request, "Please fill in all fields.")
        return redirect('student_dashboard')

    # Check for active viva sessions
    active_session = VivaSession.objects.filter(student=student, is_active=True).first()

    context = {
        'student': student,
        'labs': labs,
        'attendance_data': attendance_data,
        'marks_data': marks_data,
        'history_data': history_data,
        'active_session': active_session,
    }

    return render(request, "student/student_dashboard.html", context)

@login_required
def update_profile(request):
    if request.method == "POST":
        try:
            student = Student.objects.get(user=request.user)
            user = request.user
            
            if 'profile_pic' in request.FILES:
                student.profile_pic = request.FILES['profile_pic']
                student.save()
            
            new_password = request.POST.get('new_password')
            confirm_password = request.POST.get('confirm_password')
            
            if new_password and confirm_password:
                if new_password == confirm_password:
                    user.set_password(new_password)
                    user.save()
                    update_session_auth_hash(request, user)  # Keeps user logged in after password change
                    messages.success(request, "Password updated successfully!")
                else:
                    messages.error(request, "Passwords do not match!")
            else:
                messages.success(request, "Profile updated successfully!")
                
        except Student.DoesNotExist:
            messages.error(request, "Student profile not found.")
            
    return redirect('student_dashboard')

@login_required
def student_logout(request):
    logout(request)
    return redirect('student_login')

@login_required
def export_marks_excel(request, lab_id):
    import openpyxl
    from openpyxl.styles import Font, Alignment
    
    try:
        student = Student.objects.get(user=request.user)
        lab = Lab.objects.get(id=lab_id)
    except (Student.DoesNotExist, Lab.DoesNotExist):
        return HttpResponse("Student or Lab not found.", status=404)

    # Need data for up to 10 experiments ideally or just those submitted
    submissions = Submission.objects.filter(student=student, experiment__lab=lab).select_related('evaluation', 'experiment').order_by('experiment__number')

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f"Marks - {lab.name}"

    # Header Row
    ws.merge_cells('A1:B1')
    ws['A1'] = "Student Details"
    ws['A1'].font = Font(bold=True)
    ws['C1'] = f"Name: {student.user.username}"
    ws['D1'] = f"PRN: {student.prn}"

    headers = ["Exp No", "Experiment (5 M)", "Write-up (5 M)", "Viva (5 M)", "Total (15 M)"]
    for col_num, header in enumerate(headers, 1):
        cell = ws.cell(row=3, column=col_num)
        cell.value = header
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal='center')

    row_num = 4
    total_obtained = 0
    total_possible = 0
    
    for sub in submissions:
        if hasattr(sub, 'evaluation'):
            viva = float(sub.evaluation.viva_marks or 0)
            exp_marks = float(sub.evaluation.experiment_marks or 0)
            writeup = float(sub.evaluation.writeup_marks or 0)
            total = viva + exp_marks + writeup
            
            ws.cell(row=row_num, column=1, value=sub.experiment.number).alignment = Alignment(horizontal='center')
            ws.cell(row=row_num, column=2, value=exp_marks).alignment = Alignment(horizontal='center')
            ws.cell(row=row_num, column=3, value=writeup).alignment = Alignment(horizontal='center')
            ws.cell(row=row_num, column=4, value=viva).alignment = Alignment(horizontal='center')
            ws.cell(row=row_num, column=5, value=total).alignment = Alignment(horizontal='center')
            
            total_obtained += total
            total_possible += 15 # Assuming max 15 per experiment
            row_num += 1

    # Add summary rows
    row_num += 1
    avg = round(total_obtained / max(1, (total_possible/15)), 2)
    percent = round((total_obtained / max(1, total_possible)) * 100, 2)
    
    ws.cell(row=row_num, column=4, value="Grand Total:").font = Font(bold=True)
    ws.cell(row=row_num, column=5, value=total_obtained)
    
    ws.cell(row=row_num+1, column=4, value="Average:").font = Font(bold=True)
    ws.cell(row=row_num+1, column=5, value=avg)

    ws.cell(row=row_num+2, column=4, value="Percentage:").font = Font(bold=True)
    ws.cell(row=row_num+2, column=5, value=f"{percent}%")

    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="marks_{student.prn}_{lab.name}.xlsx"'
    wb.save(response)
    
    return response

def student_login(request):
    active_tab = "login"

    if request.method == "POST":
        # LOGIN
        if "student_login_submit" in request.POST:
            identifier = request.POST.get("username")  # Can be username or PRN from the new form
            password = request.POST.get("password")
            
            # 1. Try direct authentication with the provided identifier
            user = authenticate(request, username=identifier, password=password)

            # 2. If it fails, check if the identifier is a PRN
            if user is None:
                try:
                    student_by_prn = Student.objects.get(prn=identifier)
                    # If PRN exists, try authenticating with the linked user's actual username
                    user = authenticate(request, username=student_by_prn.user.username, password=password)
                except Student.DoesNotExist:
                    pass

            if user is not None and hasattr(user, "student"):
                login(request, user)
                return redirect("student_dashboard")
            else:
                # Check if user exists but password is wrong OR if user doesn't exist at all
                messages.error(request, "Invalid username/PRN or password")

        # REGISTER
        elif "student_register_submit" in request.POST:
            active_tab = "register"

            username = request.POST.get("username")
            prn = request.POST.get("prn")
            password1 = request.POST.get("password1")
            password2 = request.POST.get("password2")
            division_name = request.POST.get("division")

            if password1 != password2:
                messages.error(request, "Passwords do not match")
                return render(request, "student/student_login.html", {"active_tab": active_tab})

            # Check if student PRN was uploaded by professor
            try:
                student = Student.objects.get(prn=prn)
            except Student.DoesNotExist:
                messages.error(request, "PRN does not exist. Please contact your professor or ensure it was uploaded in the Excel sheet.")
                return render(request, "student/student_login.html", {"active_tab": active_tab})
            
            # Check if this PRN already has a password set (is already registered fully)
            # The excel upload script creates a basic user with username=prn.lower() but no usable password.
            if student.user.has_usable_password():
                messages.error(request, "This PRN is already registered. Please go to the Sign In page.")
                return redirect("student_login")
            
            # If username changed, we should probably check if the new chosen username is taken by someone else
            if student.user.username != username and User.objects.filter(username=username).exists():
                messages.error(request, "Username already taken. Please choose a different ERP username or use your PRN.")
                return render(request, "student/student_login.html", {"active_tab": active_tab})

            try:
                # Update the existing user correctly
                user = student.user
                user.username = username
                user.set_password(password1)
                user.save()

                # Sync the division as well during registration if they picked a new one
                if division_name:
                    division_obj, _ = Division.objects.get_or_create(name=division_name, college=student.division.college)
                    student.division = division_obj
                    student.save()

                messages.success(request, "Student account registered successfully. Please sign in.")
                active_tab = "login"
            except Exception as e:
                messages.error(request, f"Error completing registration: {str(e)}")

    return render(request, "student/student_login.html", {"active_tab": active_tab})

def college_auth(request):

    if request.method == "POST":

        # LOGIN
        if "login_submit" in request.POST:

            username = request.POST.get("username", "").strip()
            password = request.POST.get("password")

            try:
                user = authenticate(request, username=username, password=password)
            except DatabaseError:
                messages.error(request, "Database is not ready. Run migrations and verify DATABASE_URL.")
                return redirect("college_auth")

            # Username login is case-sensitive by default in Django.
            # Try a case-insensitive username lookup for friendlier login behavior.
            if user is None and username:
                try:
                    matched_user = User.objects.get(username__iexact=username)
                    user = authenticate(request, username=matched_user.username, password=password)
                except User.DoesNotExist:
                    pass
                except DatabaseError:
                    messages.error(request, "Database is not ready. Run migrations and verify DATABASE_URL.")
                    return redirect("college_auth")

            if user is not None:
                try:
                    _ = user.collegeadmin
                    login(request, user)
                    return redirect("college_dashboard")
                except ObjectDoesNotExist:
                    messages.error(request, "This account is not registered as a college admin.")
                    return redirect("college_auth")

            messages.error(request, "Invalid username or password")

        # REGISTER
        elif "register_submit" in request.POST:

            college_name = request.POST.get("college_name", "").strip()
            college_email = request.POST.get("college_email", "").strip()
            username = request.POST.get("username", "").strip()
            password = request.POST.get("password")
            confirm_password = request.POST.get("confirm_password")

            if not college_name or not college_email or not username:
                messages.error(request, "College name, college email, and username are required.")
                return redirect("college_auth")

            if password != confirm_password:
                messages.error(request, "Passwords do not match")
                return redirect("college_auth")

            try:
                with transaction.atomic():
                    user = User.objects.create_user(
                        username=username,
                        password=password
                    )

                    college = College.objects.create(
                        name=college_name,
                        email=college_email
                    )

                    CollegeAdmin.objects.create(
                        user=user,
                        college=college
                    )
            except IntegrityError as exc:
                error_text = str(exc).lower()
                if "username" in error_text:
                    messages.error(request, "Username already exists. Please choose another username.")
                elif "email" in error_text:
                    messages.error(request, "College email already exists. Please use another email.")
                else:
                    messages.error(request, "Could not create account due to duplicate data.")
                return redirect("college_auth")
            except DatabaseError:
                messages.error(request, "Database is not ready. Run migrations and verify DATABASE_URL.")
                return redirect("college_auth")

            messages.success(request, "Account created successfully. Please login.")
            return redirect("college_auth")

    return render(request, "college/auth.html")

@login_required
def college_dashboard(request):

    try:
        college_admin = request.user.collegeadmin
    except ObjectDoesNotExist:
        messages.error(request, "Your account is not linked to a college admin profile.")
        logout(request)
        return redirect("college_auth")

    try:
        college = college_admin.college
        professors = Professor.objects.filter(college=college)
        labs = Lab.objects.filter(college=college)
    except DatabaseError:
        messages.error(request, "Database is not ready. Run migrations and verify DATABASE_URL.")
        return redirect("college_auth")

    return render(
        request,
        "college/dashboard.html",
        {
            "professors": professors,
            "labs": labs
        }
    )

def college_logout(request):
    logout(request)
    return redirect("college_auth")

def professor_auth(request):
    # determine which tab should be active; default to login
    active_tab = "login"

    if request.method == "POST":
        # LOGIN
        if "login_submit" in request.POST:
            username = request.POST.get("username")
            password = request.POST.get("password")

            user = authenticate(request, username=username, password=password)

            if user is not None and hasattr(user, "professor"):
                login(request, user)
                return redirect("professor_dashboard")

            else:
                messages.error(request, "Invalid username or password")

        # REGISTER
        elif "register_submit" in request.POST:
            active_tab = "register"

            username = request.POST.get("username")
            email = request.POST.get("email")
            password1 = request.POST.get("password1")
            password2 = request.POST.get("password2")
            divisions = request.POST.getlist("divisions")

            if password1 != password2:
                messages.error(request, "Passwords do not match")
                return render(request, "professor/professor_login.html", {"active_tab": active_tab})

            # Check if email exists in Professor model
            try:
                professor = Professor.objects.get(email=email)
            except Professor.DoesNotExist:
                messages.error(request, "Email not found in professor records. Contact your college admin.")
                return render(request, "professor/professor_login.html", {"active_tab": active_tab})

            # Check if this professor profile is already linked to a User
            if professor.user:
                messages.error(request, "An account is already created for this email.")
                return render(request, "professor/professor_login.html", {"active_tab": active_tab})

            # Check if the desired username is already taken by any User
            if User.objects.filter(username=username).exists():
                messages.error(request, "This username is already taken. Please choose another one.")
                return render(request, "professor/professor_login.html", {"active_tab": active_tab})

            user = User.objects.create_user(
                username=username,
                password=password1
            )

            professor.user = user
            professor.divisions = ','.join(divisions) if divisions else ''
            professor.save()

            messages.success(request, "Account created successfully. Please login.")
            active_tab = "login"

    return render(request, "professor/professor_login.html", {"active_tab": active_tab})

@login_required
def view_professors(request):

    college = request.user.collegeadmin.college

    professors = Professor.objects.filter(college=college)

    return render(
        request,
        "college/view_professors.html",
        {
            "professors": professors
        }
    )


    
@login_required
def add_professor(request):
    if request.method != "POST":
        return redirect("college_dashboard")

    try:
        college = request.user.collegeadmin.college
    except ObjectDoesNotExist:
        messages.error(request, "Your account is not linked to a college admin profile.")
        logout(request)
        return redirect("college_auth")

    name = request.POST.get("name", "").strip()
    email = request.POST.get("email", "").strip()
    course = request.POST.get("course", "").strip()

    if not name or not email or not course:
        messages.error(request, "Name, email, and course are required.")
        return redirect("college_dashboard")

    if Professor.objects.filter(email__iexact=email).exists():
        messages.error(request, "A professor with this email already exists.")
        return redirect("college_dashboard")

    try:
        Professor.objects.create(
            college=college,
            name=name,
            email=email,
            course=course
        )
    except IntegrityError:
        messages.error(request, "Could not add professor due to duplicate data.")
        return redirect("college_dashboard")
    except DatabaseError:
        messages.error(request, "Database is not ready. Run migrations and verify DATABASE_URL.")
        return redirect("college_auth")

    messages.success(request, f"Professor {name} added successfully!")
    return redirect("college_dashboard")



@login_required
def edit_profile(request):

    if request.method == "POST":

        user = request.user

        current_password = request.POST.get("currentPassword")
        username = request.POST.get("newUsername")
        new_password = request.POST.get("newPassword")
        confirm_password = request.POST.get("confirmPassword")

        # Check current password
        if not user.check_password(current_password):
            messages.error(request, "Current password is incorrect.")
            return redirect("college_dashboard")

        if username:
            user.username = username
            user.save()

        if new_password:
            if new_password == confirm_password:
                user.set_password(new_password)
                user.save()
                update_session_auth_hash(request, user)
                messages.success(request, "Password updated successfully.")
            else:
                messages.error(request, "New passwords do not match.")
                return redirect("college_dashboard")

        messages.success(request, "Profile updated successfully.")
        return redirect("college_dashboard")
    
@login_required
def delete_professor(request, professor_id):
    try:
        professor = Professor.objects.get(id=professor_id)
        
        # 1. Delete associated ExcelUpload files
        uploads = ExcelUpload.objects.filter(professor=professor)
        for upload in uploads:
            if upload.file:
                upload.file.delete()
        
        # 2. Handle Labs: Clear student mappings, delete manual/syllabus files
        labs = Lab.objects.filter(professor=professor)
        for lab in labs:
            lab.students.clear()  # Drop the many-to-many relationship
            if lab.syllabus:
                lab.syllabus.delete()
            if lab.manual:
                lab.manual.delete()
                
        # 3. Store the linked user before deleting the professor
        linked_user = professor.user
        
        # 4. Delete the professor (this cascaded to Lab, ExcelUpload DB records)
        professor.delete()
        
        # 5. Delete the User auth record so the username is freed up
        if linked_user:
            linked_user.delete()
            
    except Professor.DoesNotExist:
        pass

    return redirect("college_dashboard")

@login_required
def edit_professor(request):

    if request.method == "POST":

        professor_id = request.POST.get("professor_id")

        name = request.POST.get("name")

        email = request.POST.get("email")

        course = request.POST.get("course")

        professor = Professor.objects.get(id=professor_id)

        professor.name = name
        professor.email = email
        professor.course = course

        professor.save()

    return redirect("college_dashboard")

@login_required
def add_lab(request):

    if request.method == "POST":

        lab_name = request.POST.get("lab_name")

        professor_id = request.POST.get("professor")

        college = request.user.collegeadmin.college

        professor = Professor.objects.get(id=professor_id)

        Lab.objects.create(

            name=lab_name,

            professor=professor,

            college=college

        )

        messages.success(request, "Lab created successfully")

        return redirect("college_dashboard")
    
def professor_register(request):

    if request.method == "POST" and "register_submit" in request.POST:
        
        email = request.POST.get("email")
        username = request.POST.get("username")
        password1 = request.POST.get("password1")
        password2 = request.POST.get("password2")

        divisions = request.POST.getlist("divisions")

        if password1 != password2:
            messages.error(request, "Passwords do not match")
            return redirect("professor_login")

        try:
            professor = Professor.objects.get(email=email)

        except Professor.DoesNotExist:
            messages.error(request, "This email is not assigned by admin")
            return redirect("professor_auth")

        if professor.user:
            messages.error(request, "Account already created for this email")
            return redirect("professor_auth")
            
        if User.objects.filter(username=username).exists():
            messages.error(request, "This username is already taken. Please choose another one.")
            return redirect("professor_auth")

        user = User.objects.create_user(
            username=username,
            password=password1,
            email=email
        )

        professor.user = user
        professor.divisions = ",".join(divisions)
        professor.save()

        messages.success(request, "Account created successfully")

        return redirect("professor_login")

    return redirect("professor_login")   

def professor_login(request):

    if request.method == "POST":

        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if user is not None:

            try:
                Professor.objects.get(user=user)

                login(request, user)

                return redirect("professor_dashboard")

            except Professor.DoesNotExist:

                messages.error(request, "Not a professor account")

        else:
            messages.error(request, "Invalid login")

    return render(request, "professor/professor_login.html")

@login_required
def professor_dashboard(request):

    professor = Professor.objects.get(user=request.user)
    
    # Parse divisions from comma-separated string
    divisions_list = [d.strip() for d in professor.divisions.split(',') if d.strip()] if professor.divisions else []

    # Parse courses from the professor's profile
    course_names = [c.strip() for c in professor.course.split(',') if c.strip()] if professor.course else []
    
    # Ensure Lab objects exist for each assigned course
    assigned_labs = []
    for name in course_names:
        lab, created = Lab.objects.get_or_create(
            professor=professor,
            college=professor.college,
            name=name
        )
        assigned_labs.append(lab)

    # Get all divisions for this college
    all_divisions = Division.objects.filter(college=professor.college).order_by('name')

    # Fetch all pending viva submissions for the professor's labs
    pending_vivas = Submission.objects.filter(
        lab__in=assigned_labs,
        status='pending'
    ).select_related('student__user', 'experiment').order_by('-submitted_at')

    return render(
        request,
        "professor/professor_dashboard.html",
        {
            "professor": professor,
            "professor_divisions": divisions_list,
            "assigned_labs": assigned_labs,
            "all_divisions": all_divisions,
            "pending_vivas": pending_vivas
        }
    )

@login_required
def professor_logout(request):
    logout(request)
    return redirect("professor_auth")

@login_required
def professor_edit_profile(request):
    if request.method == "POST":
        user = request.user
        professor = Professor.objects.get(user=user)
        
        # Handle profile picture upload
        if 'profile_pic' in request.FILES:
            profile_pic = request.FILES['profile_pic']
            # Save the image to media folder (requires MEDIA_URL and MEDIA_ROOT configured)
            # For now, we'll just show a success message
            messages.success(request, "Profile updated successfully!")
        else:
            messages.success(request, "Profile updated successfully!")
        
        return redirect("professor_dashboard")
    
    return redirect("professor_dashboard")

# New views for enhanced functionality

@csrf_exempt
@require_POST
@login_required
def upload_student_excel(request):
    """Upload student excel file for a division and assign to a specific lab"""
    try:
        professor = Professor.objects.get(user=request.user)
        excel_file = request.FILES.get('excel_file')
        division_name = request.POST.get('division', '').strip()
        lab_id = request.POST.get('lab_id')

        if not excel_file or not division_name or not lab_id:
            return JsonResponse({'success': False, 'error': 'Missing file, division, or lab selection'}, status=400)

        if not excel_file.name.lower().endswith('.xlsx'):
            return JsonResponse({'success': False, 'error': 'Please upload a valid .xlsx file.'}, status=400)

        # Get the lab
        try:
            lab = Lab.objects.get(id=lab_id, professor=professor)
        except Lab.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Invalid lab selected'}, status=400)

        # Get or create division
        division, created = Division.objects.get_or_create(
            name=division_name,
            college=professor.college
        )

        # Check if an upload already exists for this Lab and Division
        if ExcelUpload.objects.filter(professor=professor, lab=lab, division=division).exists():
            return JsonResponse({
                'success': False, 
                'error': f'An Excel file is already uploaded for {lab.name} - {division_name}. Please delete the existing upload first.'
            }, status=409)

        # Guard file size on memory-constrained instances (Render starter/free).
        max_excel_size_bytes = 3 * 1024 * 1024  # 3 MB
        if getattr(excel_file, 'size', 0) > max_excel_size_bytes:
            return JsonResponse(
                {
                    'success': False,
                    'error': 'Excel file is too large for current server plan. Keep it under 3 MB.'
                },
                status=400
            )

        # Load workbook in read-only mode to reduce memory usage.
        wb = None
        try:
            wb = openpyxl.load_workbook(excel_file, read_only=True, data_only=True)
        except Exception:
            return JsonResponse({'success': False, 'error': 'Could not read this Excel file. Use a valid .xlsx file.'}, status=400)

        parsed_rows = []
        seen_prns = set()
        try:
            sheet = wb.active
            for row in sheet.iter_rows(min_row=2, values_only=True):  # Skip header
                if not row or len(row) < 2 or not row[0] or not row[1]:
                    continue

                name = str(row[0]).strip()
                prn = str(row[1]).strip()
                if not prn or prn.lower() == 'none' or prn in seen_prns:
                    continue

                seen_prns.add(prn)
                parsed_rows.append((name, prn))
        finally:
            if wb is not None:
                wb.close()

        if not parsed_rows:
            return JsonResponse({'success': False, 'error': 'No valid student rows found in the Excel file.'}, status=400)

        total_processed = 0
        conflicts_skipped = 0

        with transaction.atomic():
            prns = [prn for _, prn in parsed_rows]
            usernames = [prn.lower() for prn in prns]
            name_by_username = {prn.lower(): name for name, prn in parsed_rows}

            existing_users = {u.username: u for u in User.objects.filter(username__in=usernames)}
            missing_usernames = [uname for uname in usernames if uname not in existing_users]

            if missing_usernames:
                new_users = []
                for username in missing_usernames:
                    full_name = name_by_username.get(username, '').strip()
                    parts = full_name.split()
                    first_name = parts[0] if parts else ''
                    last_name = ' '.join(parts[1:]) if len(parts) > 1 else ''
                    user = User(username=username, first_name=first_name, last_name=last_name)
                    user.set_unusable_password()
                    new_users.append(user)

                User.objects.bulk_create(new_users, ignore_conflicts=True)
                existing_users = {u.username: u for u in User.objects.filter(username__in=usernames)}

            existing_students = {s.prn: s for s in Student.objects.filter(prn__in=prns)}
            linked_students = {
                s.user_id: s for s in Student.objects.filter(user_id__in=[u.id for u in existing_users.values() if u.id])
            }

            students_to_create = []
            students_to_update = []

            for _, prn in parsed_rows:
                username = prn.lower()
                user = existing_users.get(username)
                if not user:
                    continue

                student = existing_students.get(prn)
                if student:
                    if student.division_id != division.id:
                        student.division = division
                        students_to_update.append(student)
                    continue

                # Avoid one-to-one conflicts: same user linked to another PRN.
                linked_student = linked_students.get(user.id)
                if linked_student and linked_student.prn != prn:
                    conflicts_skipped += 1
                    continue

                students_to_create.append(Student(prn=prn, user=user, division=division))

            if students_to_create:
                Student.objects.bulk_create(students_to_create, ignore_conflicts=True)

            if students_to_update:
                Student.objects.bulk_update(students_to_update, ['division'])

            assigned_students = list(Student.objects.filter(prn__in=prns))
            through_model = lab.students.through
            through_rows = [through_model(lab_id=lab.id, student_id=stu.id) for stu in assigned_students]
            if through_rows:
                through_model.objects.bulk_create(through_rows, ignore_conflicts=True)

            total_processed = len(assigned_students)

        # Update professor's divisions list if new
        division_added = False
        current_divisions = [d.strip() for d in professor.divisions.split(',') if d.strip()]
        if division_name not in current_divisions:
            current_divisions.append(division_name)
            professor.divisions = ','.join(current_divisions)
            professor.save()
            division_added = True

        # Save upload tracking. If file storage fails, keep processing outcome
        # and save filename-only marker to avoid blocking student imports.
        try:
            excel_file.seek(0)
            ExcelUpload.objects.create(
                professor=professor,
                lab=lab,
                division=division,
                file=excel_file,
                filename=excel_file.name
            )
        except Exception:
            logger.exception(
                "ExcelUpload file save failed for professor_id=%s, lab_id=%s, division=%s",
                professor.id,
                lab.id,
                division.name,
            )
            ExcelUpload.objects.create(
                professor=professor,
                lab=lab,
                division=division,
                file=f"excel_uploads/{excel_file.name}",
                filename=excel_file.name
            )

        message = f'Successfully processed {total_processed} students and assigned to division {division_name}.'
        if conflicts_skipped:
            message += f' Skipped {conflicts_skipped} conflicted rows (same user linked to another PRN).'

        return JsonResponse({
            'success': True,
            'students_count': total_processed,
            'division_added': division_added,
            'message': message
        })

    except Professor.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Professor profile not found for this account.'}, status=403)
    except Exception as e:
        logger.exception("Student Excel upload failed")
        return JsonResponse(
            {
                'success': False,
                'error': f'{e.__class__.__name__}: {str(e)}'
            },
            status=500
        )

@login_required
def get_students_for_division(request):
    """Get students for a division and lab for marks entry"""
    division_name = request.GET.get('division', '').strip()
    lab_id = request.GET.get('lab_id')
    
    if not division_name or not lab_id:
        return JsonResponse({'students': []})

    try:
        professor = Professor.objects.get(user=request.user)
        # Use __iexact for safer division name matching
        division = Division.objects.get(name__iexact=division_name, college=professor.college)
        lab = Lab.objects.get(id=lab_id)
        
        # Filter students who are in this division AND assigned to this lab
        students = Student.objects.filter(division=division, assigned_labs=lab).order_by('prn')
        print(f"DEBUG: Found {students.count()} students for this division/lab")

        date = request.GET.get('date')
        
        students_data = []
        for student in students:
            # Get existing evaluations for this student in this lab
            marks = {}
            from django.db.models import Q
            submissions = Submission.objects.filter(
                Q(experiment__lab=lab) | Q(lab=lab), 
                student=student
            ).select_related('experiment', 'evaluation')
            
            for sub in submissions:
                eval_obj = getattr(sub, 'evaluation', None)
                if eval_obj:
                    exp_num = None
                    if sub.experiment:
                        exp_num = sub.experiment.number
                    elif sub.experiment_name:
                        import re
                        match = re.search(r'\d+', sub.experiment_name)
                        if match:
                            exp_num = int(match.group())
                    
                    if exp_num is not None:
                        marks[str(exp_num)] = {
                            'viva': float(eval_obj.viva_marks),
                            'marks': float(eval_obj.experiment_marks),
                            'writing': float(eval_obj.writeup_marks)
                        }
            
            student_dict = {
                'id': student.id,
                'name': student.user.get_full_name() or student.user.username,
                'prn': student.prn,
                'marks': marks,
                'attendance': None # Default is not marked
            }

            # Get attendance for specific date if provided
            if date:
                try:
                    att = Attendance.objects.filter(student=student, lab=lab, date=date).first()
                    if att:
                        student_dict['attendance'] = att.present
                except Exception:
                    pass

            students_data.append(student_dict)

        return JsonResponse({'students': students_data})
    except Exception as e:
        return JsonResponse({'students': [], 'error': str(e)})

@login_required
def get_submissions_for_division(request):
    """Get submissions for a division and lab for view uploads"""
    division_name = request.GET.get('division', '').strip()
    lab_id = request.GET.get('lab_id')
    if not division_name or not lab_id:
        return JsonResponse({'submissions': []})

    try:
        professor = Professor.objects.get(user=request.user)
        division = Division.objects.get(name__iexact=division_name, college=professor.college)
        lab = Lab.objects.get(id=lab_id)
        
        # Only fetch new-style submissions (experiment_name set, lab FK used)
        students = Student.objects.filter(division=division, assigned_labs=lab)
        submissions = Submission.objects.filter(
            student__in=students,
            lab=lab
        ).exclude(experiment_name='').select_related('student', 'student__user').order_by('student__prn', 'submitted_at')

        submissions_data = []
        for i, submission in enumerate(submissions, 1):
            submissions_data.append({
                'id': submission.id,
                'student_name': submission.student.user.get_full_name() or submission.student.user.username,
                'student_prn': submission.student.prn,
                'experiment_name': submission.experiment_name,
                'experiment_title': submission.experiment_name,
                'code_screenshot': submission.code_screenshot.url if submission.code_screenshot else '',
                'output_screenshot': submission.output_screenshot.url if submission.output_screenshot else '',
                'submitted_at': submission.submitted_at.strftime('%d %b %Y %I:%M %p'),
                'status': submission.status
            })

        return JsonResponse({'submissions': submissions_data})
    except Exception as e:
        return JsonResponse({'submissions': [], 'error': str(e)})

@login_required
def check_upload_status(request):
    """Check if an Excel file has already been uploaded for a lab/division"""
    lab_id = request.GET.get('lab_id')
    division_name = request.GET.get('division', '').strip()
    
    if not lab_id or not division_name:
        return JsonResponse({'exists': False})

    try:
        professor = Professor.objects.get(user=request.user)
        # We search by name and college to find the right division
        division = Division.objects.get(name__iexact=division_name, college=professor.college)
        
        upload = ExcelUpload.objects.filter(
            professor=professor,
            lab_id=lab_id,
            division=division
        ).first()

        if upload:
            return JsonResponse({
                'exists': True,
                'filename': upload.filename,
                'uploaded_at': timezone.localtime(upload.uploaded_at).strftime('%d %b %Y %I:%M %p')
            })
    except Exception:
        pass

    return JsonResponse({'exists': False})

@csrf_exempt
@require_POST
@login_required
def delete_upload(request):
    """Delete an existing Excel upload and reset the student assignments for that lab"""
    try:
        data = json.loads(request.body)
        lab_id = data.get('lab_id')
        division_name = data.get('division', '').strip()
        
        if not lab_id or not division_name:
            return JsonResponse({'success': False, 'error': 'Missing lab or division information'})

        professor = Professor.objects.get(user=request.user)
        division = Division.objects.get(name__iexact=division_name, college=professor.college)
        lab = Lab.objects.get(id=lab_id, professor=professor)

        upload = ExcelUpload.objects.filter(
            professor=professor,
            lab=lab,
            division=division
        ).first()

        if upload:
            # 1. Find students from this division
            students_in_division = Student.objects.filter(division=division)
            
            # 2. Delete all their submissions for THIS specific lab
            # This will automatically delete Evaluation records due to OneToOne CASCADE
            Submission.objects.filter(student__in=students_in_division, experiment__lab=lab).delete()
            
            # 3. Remove these students from the lab's student list (reset assignments)
            for student in students_in_division:
                lab.students.remove(student)
            
            # 4. Delete the actual file from storage
            if upload.file:
                upload.file.delete()
            
            # 5. Delete the tracking record
            upload.delete()

            return JsonResponse({'success': True, 'message': 'Upload deleted, marks cleared, and lab assignments reset.'})
        
        return JsonResponse({'success': False, 'error': 'No upload record found to delete.'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@csrf_exempt
@require_POST
@login_required
def save_marks(request):
    """Save marks for students"""
    try:
        data = json.loads(request.body)
        division_name = data.get('division')
        lab_id = data.get('lab_id')
        marks_data = data.get('marks_data')
 
        if not division_name or not marks_data or not lab_id:
            return JsonResponse({'success': False, 'error': 'Missing division, lab, or marks data'})

        professor = Professor.objects.get(user=request.user)
        division = Division.objects.get(name__iexact=division_name, college=professor.college)
        lab = Lab.objects.get(id=lab_id)

        saved_count = 0
        for student_data in marks_data:
            # Find student within the context of the division and lab
            student = Student.objects.get(prn=student_data['prn'], division=division, assigned_labs=lab)
            
            for exp_data in student_data['experiments']:
                exp_num = exp_data['experiment_number']
                
                # Get or create experiment for this lab to ensure storage works
                experiment, _ = Experiment.objects.get_or_create(
                    number=exp_num,
                    lab=lab,
                    defaults={'title': f"Experiment {exp_num}"}
                )
                
                submission, created = Submission.objects.get_or_create(
                    student=student, 
                    experiment=experiment
                )
                
                evaluation, created = Evaluation.objects.get_or_create(
                    submission=submission
                )
                
                evaluation.viva_marks = float(exp_data.get('viva_marks', 0))
                evaluation.experiment_marks = float(exp_data.get('experiment_marks', 0))
                evaluation.writeup_marks = float(exp_data.get('writeup_marks', 0))
                evaluation.save()
                
                saved_count += 1
 
        return JsonResponse({'success': True, 'saved_count': saved_count})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
def download_marks_excel(request):
    """Download marks as Excel file"""
    division_name = request.GET.get('division')
    lab_id = request.GET.get('lab_id')
    if not division_name or not lab_id:
        return HttpResponse("Division or Lab not specified", status=400)

    try:
        professor = Professor.objects.get(user=request.user)
        division = Division.objects.get(name=division_name, college=professor.college)
        lab = Lab.objects.get(id=lab_id)
        
        # Create workbook
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = f"Marks_{division_name}"
        
        # Headers
        headers = ['PRN', 'Student Name']
        for exp in range(1, 11): # Assuming up to 10 experiments per lab
            headers.extend([f'Exp{exp}_Viva', f'Exp{exp}_Marks', f'Exp{exp}_Writing', f'Exp{exp}_Total'])
        headers.extend(['Total_Marks', 'Average_Marks'])
        ws.append(headers)

        # Get students and their marks
        students = Student.objects.filter(division=division, assigned_labs=lab).order_by('prn')
        for student in students:
            row = [student.prn, student.user.get_full_name() or student.user.username]
            
            total_marks = float(0)
            exp_count = float(0)
            
            for exp_num in range(1, 11):
                try:
                    experiment = Experiment.objects.get(
                        number=exp_num,
                        lab=lab
                    )
                    submission = Submission.objects.filter(
                        student=student,
                        experiment=experiment
                    ).first()
                    
                    if submission and hasattr(submission, 'evaluation'):
                        viva = float(submission.evaluation.viva_marks or 0)
                        exp_marks = float(submission.evaluation.experiment_marks or 0)
                        writing = float(submission.evaluation.writeup_marks or 0)
                        exp_total = viva + exp_marks + writing
                        
                        row.extend([viva, exp_marks, writing, exp_total])
                        total_marks = total_marks + exp_total
                        exp_count = exp_count + 1
                    else:
                        row.extend([0, 0, 0, 0])
                except Exception:
                    row.extend([0, 0, 0, 0])
            
            average = float(total_marks) / float(exp_count) if exp_count > 0 else 0.0
            row.extend([total_marks, round(average, 2)])
            ws.append(row)
        
        # Save to BytesIO
        buffer = BytesIO()
        wb.save(buffer)
        buffer.seek(0)
        
        response = HttpResponse(
            buffer.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename=marks_{division_name}.xlsx'
        return response
        
    except Exception as e:
        return HttpResponse(f"Error: {str(e)}", status=500)

@login_required
def download_total_marks_excel(request):
    """Download Excel with only total marks per experiment per student (no breakdown)"""
    division_name = request.GET.get('division')
    lab_id = request.GET.get('lab_id')

    if not division_name or not lab_id:
        return HttpResponse("Missing division or lab_id", status=400)

    try:
        professor = Professor.objects.get(user=request.user)
        division = Division.objects.get(name=division_name, college=professor.college)
        lab = Lab.objects.get(id=lab_id)

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = f"Totals_{division_name}"

        from openpyxl.styles import Font, Alignment, PatternFill
        bold_font = Font(bold=True)
        header_fill = PatternFill("solid", fgColor="1E3A8A")
        header_font = Font(bold=True, color="FFFFFF")

        # Build header: Student Name | PRN | Exp 1 Total | ... | Exp 10 Total | Grand Total
        headers = ['Student Name', 'PRN']
        for exp in range(1, 11):
            headers.append(f'Exp {exp} Total (15)')
        headers.append('Grand Total')

        # Write header row
        for col_idx, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col_idx, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal='center')

        students = Student.objects.filter(division=division, assigned_labs=lab).order_by('prn')

        for row_idx, student in enumerate(students, 2):
            row = [
                student.user.get_full_name() or student.user.username,
                student.prn
            ]
            grand_total = float(0)

            for exp_num in range(1, 11):
                try:
                    experiment = Experiment.objects.get(number=exp_num, lab=lab)
                    submission = Submission.objects.filter(
                        student=student, experiment=experiment
                    ).first()

                    if submission and hasattr(submission, 'evaluation'):
                        exp_total = float((
                            submission.evaluation.viva_marks or 0) +
                            (submission.evaluation.experiment_marks or 0) +
                            (submission.evaluation.writeup_marks or 0)
                        )
                        grand_total = grand_total + exp_total
                        row.append(exp_total)
                    else:
                        row.append(0)
                except Exception:
                    row.append(0)

            row.append(grand_total)
            ws.append(row)

            # Bold grand total cell
            ws.cell(row=row_idx, column=len(headers)).font = bold_font

        # Auto fit column widths
        for col in ws.columns:
            max_len = max(len(str(cell.value)) if cell.value else 0 for cell in col)
            ws.column_dimensions[col[0].column_letter].width = max(12, max_len + 2)

        buffer = BytesIO()
        wb.save(buffer)
        buffer.seek(0)

        response = HttpResponse(
            buffer.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename=total_marks_{division_name}_{lab.name}.xlsx'
        return response

    except Exception as e:
        return HttpResponse(f"Error: {str(e)}", status=500)

@csrf_exempt
@require_POST
@login_required
def send_marks_report(request):
    """Send marks report as Excel attachment to professor's email"""
    try:
        data = json.loads(request.body)
        division_name = data.get('division')
        lab_id = data.get('lab_id')

        professor = Professor.objects.get(user=request.user)
        division = Division.objects.get(name=division_name, college=professor.college)
        lab = Lab.objects.get(id=lab_id)
        students = Student.objects.filter(division=division).order_by('prn')

        from openpyxl.styles import Font, Alignment

        # --- Build Excel exactly like the individual marks export ---
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = f"Marks - {division_name}"

        # Report title at the very top
        ws['A1'] = f"Marks Report — Division {division_name} | {lab.name}"
        ws['A1'].font = Font(bold=True, size=13)
        ws['A2'] = f"Professor: {professor.name}   |   Course: {professor.course}   |   Generated: {timezone.now().strftime('%d %b %Y %I:%M %p')}"
        ws['A2'].font = Font(italic=True)

        current_row = 4  # start below title

        col_headers = ["Exp No", "Experiment (5 M)", "Write-up (5 M)", "Viva (5 M)", "Total (15 M)"]

        for student in students:
            submissions = Submission.objects.filter(
                student=student, experiment__lab=lab
            ).select_related('evaluation', 'experiment').order_by('experiment__number')

            # Collect only evaluated submissions
            eval_subs = [s for s in submissions if hasattr(s, 'evaluation')]
            if not eval_subs:
                continue  # skip students with nothing evaluated

            # Student details row (same as individual export)
            ws.merge_cells(start_row=current_row, start_column=1, end_row=current_row, end_column=2)
            ws.cell(row=current_row, column=1, value="Student Details").font = Font(bold=True)
            ws.cell(row=current_row, column=3, value=f"Name: {student.user.username}")
            ws.cell(row=current_row, column=4, value=f"PRN: {student.prn}")
            current_row += 1

            # Blank row then column headers
            for col_num, header in enumerate(col_headers, 1):
                cell = ws.cell(row=current_row, column=col_num)
                cell.value = header
                cell.font = Font(bold=True)
                cell.alignment = Alignment(horizontal='center')
            current_row += 1

            # Data rows — exactly same as individual export
            total_obtained = float(0)
            total_possible = float(0)
            for sub in eval_subs:
                viva      = float(sub.evaluation.viva_marks or 0)
                exp_marks = float(sub.evaluation.experiment_marks or 0)
                writeup   = float(sub.evaluation.writeup_marks or 0)
                total     = viva + exp_marks + writeup

                ws.cell(row=current_row, column=1, value=sub.experiment.number).alignment = Alignment(horizontal='center')
                ws.cell(row=current_row, column=2, value=exp_marks).alignment   = Alignment(horizontal='center')
                ws.cell(row=current_row, column=3, value=writeup).alignment     = Alignment(horizontal='center')
                ws.cell(row=current_row, column=4, value=viva).alignment        = Alignment(horizontal='center')
                ws.cell(row=current_row, column=5, value=total).alignment       = Alignment(horizontal='center')
                total_obtained += total
                total_possible += 15
                current_row += 1

            # Summary rows — same as individual export
            current_row += 1  # blank gap
            avg     = round(total_obtained / max(1, total_possible / 15), 2)
            percent = round((total_obtained / max(1, total_possible)) * 100, 2)

            ws.cell(row=current_row,   column=4, value="Grand Total:").font = Font(bold=True)
            ws.cell(row=current_row,   column=5, value=total_obtained)
            ws.cell(row=current_row+1, column=4, value="Average:").font    = Font(bold=True)
            ws.cell(row=current_row+1, column=5, value=avg)
            ws.cell(row=current_row+2, column=4, value="Percentage:").font = Font(bold=True)
            ws.cell(row=current_row+2, column=5, value=f"{percent}%")

            current_row += 4  # gap before next student

        # Save to in-memory buffer
        buffer = BytesIO()
        wb.save(buffer)
        buffer.seek(0)
        excel_data = buffer.getvalue()
        filename = f"marks_report_{division_name}_{lab.name}_{timezone.now().strftime('%Y%m%d_%H%M')}.xlsx"

        # --- Send email with Excel attachment ---
        email = EmailMessage(
            subject=f"Marks Report — Division {division_name} | {lab.name}",
            body=(
                f"Dear {professor.name},\n\n"
                f"Please find the marks report for Division {division_name} ({lab.name}) attached.\n\n"
                f"Generated on: {timezone.now().strftime('%d %b %Y %I:%M %p')}\n\n"
                f"Regards,\nLab Management System"
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[professor.email],
        )
        email.attach(filename, excel_data, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        email.send(fail_silently=False)

        return JsonResponse({'success': True, 'message': f'Report sent to {professor.email}'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

from django.views.decorators.clickjacking import xframe_options_exempt

@login_required
@xframe_options_exempt
def evaluate_submission(request, submission_id):
    """Evaluate a specific submission"""
    try:
        submission = Submission.objects.get(id=submission_id)
        professor = Professor.objects.get(user=request.user)
        
        # Check if professor has access to this submission
        # Use direct lab FK (new-style) or fall back to experiment's lab (old-style)
        sub_lab = submission.lab if submission.lab else (
            submission.experiment.lab if submission.experiment else None
        )
        if sub_lab is None or sub_lab.professor != professor:
            return redirect("professor_dashboard")
        
        evaluation, created = Evaluation.objects.get_or_create(submission=submission)
        
        if request.method == "POST":
            viva_marks_raw = request.POST.get('viva_marks', 0)
            experiment_marks_raw = request.POST.get('experiment_marks', 0)
            writeup_marks_raw = request.POST.get('writeup_marks', 0)

            evaluation.viva_marks = float(viva_marks_raw) if viva_marks_raw else 0.0
            evaluation.experiment_marks = float(experiment_marks_raw) if experiment_marks_raw else 0.0
            evaluation.writeup_marks = float(writeup_marks_raw) if writeup_marks_raw else 0.0
            
            evaluation.comments = request.POST.get('comments', '')
            evaluation.save()
            
            submission.status = 'evaluated'
            submission.save()
            
            messages.success(request, "✅ Evaluation saved successfully!")
            # Redirect back to same page so the success alert is visible
            from django.urls import reverse
            return redirect(reverse('evaluate_submission', args=[submission_id]))
        
        return render(request, "professor/evaluate_submission.html", {
            'submission': submission,
            'evaluation': evaluation
        })
        
    except Submission.DoesNotExist:
        messages.error(request, "Submission not found")
        return redirect("professor_dashboard")

@login_required
def delete_submission(request, submission_id):
    """Allow students to delete their own pending submissions"""
    try:
        student = Student.objects.get(user=request.user)
        submission = Submission.objects.get(id=submission_id, student=student)
        
        if submission.status == 'pending':
            submission.delete()
            messages.success(request, "Submission deleted successfully.")
        else:
            messages.error(request, "Cannot delete an already evaluated submission.")
            
    except (Student.DoesNotExist, Submission.DoesNotExist):
        messages.error(request, "Submission not found.")
        
    return redirect('student_dashboard')

@login_required
@csrf_exempt
def save_attendance(request):
    """Save/update attendance records for a division on a specific date"""
    if request.method != "POST":
        return JsonResponse({'success': False, 'error': 'Invalid method'})

    try:
        data = json.loads(request.body)
        lab_id = data.get('lab_id')
        division_name = data.get('division')
        date_str = data.get('date')
        attendance_data = data.get('attendance', []) # List of {student_id: int, present: bool}

        if not all([lab_id, division_name, date_str]):
            return JsonResponse({'success': False, 'error': 'Missing required fields'})

        professor = Professor.objects.get(user=request.user)
        lab = Lab.objects.get(id=lab_id)
        # Parse date from YYYY-MM-DD
        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()

        for entry in attendance_data:
            student_id = entry.get('student_id')
            is_present = entry.get('present')
            
            student = Student.objects.get(id=student_id)
            
            # Create or update attendance record
            Attendance.objects.update_or_create(
                student=student,
                lab=lab,
                date=date_obj,
                defaults={'present': is_present}
            )

        return JsonResponse({
            'success': True, 
            'message': f'Attendance for {date_str} saved successfully.'
        })

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
@csrf_exempt
@require_POST
def toggle_viva_session(request):
    """Activates or Deactivates a live Viva Session for a specific student"""
    try:
        data = json.loads(request.body)
        student_id = data.get('student_id')
        is_active = data.get('is_active')
        room_name = data.get('room_name', '')
        
        professor = Professor.objects.get(user=request.user)
        student = Student.objects.get(id=student_id)
        
        # Deactivate any existing active sessions to prevent ghost calls
        if is_active:
            VivaSession.objects.filter(professor=professor, student=student, is_active=True).update(is_active=False)
            
            # Create the new session
            VivaSession.objects.create(
                professor=professor,
                student=student,
                room_name=room_name,
                is_active=True
            )
            return JsonResponse({'success': True, 'message': 'Session activated'})
        else:
            # End the current session
            VivaSession.objects.filter(professor=professor, student=student, is_active=True).update(is_active=False)
            return JsonResponse({'success': True, 'message': 'Session ended'})
            
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
def check_call(request):
    """Student dashboard pings this to see if a professor is calling them"""
    try:
        student = Student.objects.get(user=request.user)
        active_session = VivaSession.objects.filter(student=student, is_active=True).first()
        
        if active_session:
            return JsonResponse({
                'active': True,
                'room_name': active_session.room_name
            })
            
    except Student.DoesNotExist:
        pass
        
    return JsonResponse({'active': False})

@login_required
def check_lab_resources_status(request):
    """Check if syllabus or manual are uploaded for a specific lab"""
    lab_id = request.GET.get('lab_id')
    if not lab_id:
        return JsonResponse({'success': False, 'error': 'Lab ID is required'})
    
    try:
        professor = Professor.objects.get(user=request.user)
        lab = Lab.objects.get(id=lab_id, professor=professor)
        
        return JsonResponse({
            'success': True,
            'syllabus_name': lab.syllabus.name.split('/')[-1] if lab.syllabus else None,
            'syllabus_url': lab.syllabus.url if lab.syllabus else None,
            'manual_name': lab.manual.name.split('/')[-1] if lab.manual else None,
            'manual_url': lab.manual.url if lab.manual else None
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@csrf_exempt
@require_POST
@login_required
def upload_lab_resource(request):
    """Upload syllabus or lab manual for a specific lab"""
    lab_id = request.POST.get('lab_id')
    resource_type = request.POST.get('resource_type') # 'syllabus' or 'manual'
    uploaded_file = request.FILES.get('file')
    
    if not all([lab_id, resource_type, uploaded_file]):
        return JsonResponse({'success': False, 'error': 'Missing required fields'})
    
    try:
        professor = Professor.objects.get(user=request.user)
        lab = Lab.objects.get(id=lab_id, professor=professor)
        
        if resource_type == 'syllabus':
            # Delete old file if exists
            if lab.syllabus:
                lab.syllabus.delete()
            lab.syllabus = uploaded_file
        elif resource_type == 'manual':
            if lab.manual:
                lab.manual.delete()
            lab.manual = uploaded_file
        else:
            return JsonResponse({'success': False, 'error': 'Invalid resource type'})
            
        lab.save()
        return JsonResponse({
            'success': True, 
            'message': f'{resource_type.capitalize()} uploaded successfully',
            'filename': uploaded_file.name,
            'url': getattr(lab, resource_type).url
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@csrf_exempt
@require_POST
@login_required
def delete_lab_resource(request):
    """Delete syllabus or lab manual for a specific lab"""
    try:
        data = json.loads(request.body)
        lab_id = data.get('lab_id')
        resource_type = data.get('resource_type') # 'syllabus' or 'manual'
        
        if not all([lab_id, resource_type]):
            return JsonResponse({'success': False, 'error': 'Missing required fields'})
            
        professor = Professor.objects.get(user=request.user)
        lab = Lab.objects.get(id=lab_id, professor=professor)
        
        if resource_type == 'syllabus':
            if lab.syllabus:
                lab.syllabus.delete()
                lab.syllabus = None
        elif resource_type == 'manual':
            if lab.manual:
                lab.manual.delete()
                lab.manual = None
        else:
            return JsonResponse({'success': False, 'error': 'Invalid resource type'})
            
        lab.save()
        return JsonResponse({'success': True, 'message': f'{resource_type.capitalize()} deleted successfully'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})
