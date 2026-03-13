from django.db import models
from django.contrib.auth.models import User 

class College(models.Model):
    name = models.CharField(max_length=200)
    email = models.EmailField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
    
class CollegeAdmin(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    college = models.ForeignKey(College, on_delete=models.CASCADE)

    def __str__(self):
        return self.user.username

class Division(models.Model):
    name = models.CharField(max_length=50)
    college = models.ForeignKey(College, on_delete=models.CASCADE)

    def __str__(self):
        return self.name       
    
class Professor(models.Model):

    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)

    college = models.ForeignKey(
        College,
        on_delete=models.CASCADE
    )

    name = models.CharField(max_length=200)

    email = models.EmailField(unique=True)

    course = models.CharField(max_length=200)

    divisions = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return self.name
    
class Lab(models.Model):

    college = models.ForeignKey(
        College,
        on_delete=models.CASCADE
    )

    professor = models.ForeignKey(
        Professor,
        on_delete=models.CASCADE
    )

    name = models.CharField(max_length=200)

    syllabus = models.FileField(
        upload_to="syllabus/",
        blank=True,
        null=True
    )

    manual = models.FileField(
        upload_to="manuals/",
        blank=True,
        null=True
    )
    students = models.ManyToManyField('Student', related_name='assigned_labs', blank=True)

    def __str__(self):
        return self.name

class Student(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    prn = models.CharField(max_length=50, unique=True)
    division = models.ForeignKey(Division, on_delete=models.CASCADE)
    profile_pic = models.ImageField(upload_to="student_profiles/", blank=True, null=True)

    def __str__(self):
        return f"{self.user.username} ({self.prn})"    

class Experiment(models.Model):
    lab = models.ForeignKey(Lab, on_delete=models.CASCADE)
    number = models.IntegerField()
    title = models.CharField(max_length=200)

    def __str__(self):
        return f"{self.lab.name} - Exp {self.number}"    

def submission_path(instance, filename):
    return f"submissions/{instance.student.prn}/{filename}"


class Submission(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    lab = models.ForeignKey(Lab, on_delete=models.CASCADE, null=True, blank=True)
    experiment = models.ForeignKey(Experiment, on_delete=models.CASCADE, null=True, blank=True)
    experiment_name = models.CharField(max_length=200, blank=True, default='')

    code_screenshot = models.ImageField(upload_to=submission_path)
    output_screenshot = models.ImageField(upload_to=submission_path)

    submitted_at = models.DateTimeField(auto_now_add=True)

    status = models.CharField(
        max_length=20,
        choices=[
            ("pending", "Pending"),
            ("evaluated", "Evaluated"),
        ],
        default="pending",
    ) 

class Evaluation(models.Model):
    submission = models.OneToOneField(Submission, on_delete=models.CASCADE)

    viva_marks = models.FloatField(default=0)
    experiment_marks = models.FloatField(default=0)
    writeup_marks = models.FloatField(default=0)

    comments = models.TextField(blank=True)

class Attendance(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    lab = models.ForeignKey(Lab, on_delete=models.CASCADE)

    date = models.DateField()
    present = models.BooleanField(default=False)  

class VivaSession(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    professor = models.ForeignKey(Professor, on_delete=models.CASCADE)

    room_name = models.CharField(max_length=200)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)      

class ExcelUpload(models.Model):
    professor = models.ForeignKey(Professor, on_delete=models.CASCADE)
    lab = models.ForeignKey(Lab, on_delete=models.CASCADE)
    division = models.ForeignKey(Division, on_delete=models.CASCADE)
    file = models.FileField(upload_to='excel_uploads/', max_length=500)
    filename = models.CharField(max_length=255)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.filename} - {self.lab.name} ({self.division.name})"
