import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lab_project.settings')
django.setup()

from labapp.models import Student, Division, Lab, Experiment, Submission, Evaluation, Professor

def verify():
    print("--- Professors ---")
    for p in Professor.objects.all():
        print(f"User: {p.user.username}, College: {p.college.name}, Divisions: {p.divisions}")

    print("\n--- Labs ---")
    for l in Lab.objects.all():
        experiments = l.experiment_set.all()
        print(f"ID: {l.id}, Name: {l.name}, Experiments: {[e.number for e in experiments]}")

    print("\n--- Divisions ---")
    for d in Division.objects.all():
        print(f"ID: {d.id}, Name: {d.name}, College: {d.college.name}")

    print("\n--- Recent Evaluations (Last 5) ---")
    evals = Evaluation.objects.all().order_by('-id')[:5]
    if not evals:
        print("No evaluations found.")
    for e in evals:
        print(f"ID {e.id}: Student {e.submission.student.prn}, Exp {e.submission.experiment.number}, Marks: {e.viva_marks}/{e.experiment_marks}/{e.writeup_marks}")

if __name__ == "__main__":
    verify()
