import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
import os
import math

# Optional OpenAI API
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


# ---------------- DATABASE ----------------

conn = sqlite3.connect("students.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    roll_no TEXT NOT NULL,
    class_name TEXT NOT NULL,
    math REAL,
    science REAL,
    english REAL,
    computer REAL,
    social_science REAL,
    attendance REAL,
    total REAL,
    percentage REAL,
    grade TEXT,
    result TEXT,
    analysis TEXT
)
""")
conn.commit()


# ---------------- ANALYSIS ----------------

def basic_analysis(percentage, attendance, grade):
    if percentage >= 90:
        performance = "Excellent academic performance."
        suggestion = "Continue regular revision and participate in advanced learning activities."
    elif percentage >= 80:
        performance = "Very good academic performance."
        suggestion = "Focus on weak subjects to improve the overall score."
    elif percentage >= 70:
        performance = "Good academic performance."
        suggestion = "Regular practice and revision can help achieve higher marks."
    elif percentage >= 60:
        performance = "Average academic performance."
        suggestion = "Increase study time and practice difficult topics regularly."
    elif percentage >= 50:
        performance = "Below average academic performance."
        suggestion = "Follow a daily study schedule and seek help in difficult subjects."
    else:
        performance = "Academic performance needs significant improvement."
        suggestion = "Focus on basic concepts, regular practice and teacher guidance."

    attendance_msg = ("Attendance is satisfactory." if attendance >= 75
                      else "Attendance is below the recommended level.")

    return f"""
Overall Performance:
{performance}

Grade:
{grade}

Attendance:
{attendance_msg}

Improvement Suggestions:
{suggestion}

Motivation:
Keep working consistently and improve step by step.
"""


def get_ai_analysis(name, percentage, attendance, grade, result):
    """Uses OpenAI if an API key is available, otherwise rule-based analysis."""
    api_key = os.getenv("OPENAI_API_KEY")

    if OPENAI_AVAILABLE and api_key:
        try:
            client = OpenAI(api_key=api_key, timeout=20)

            prompt = f"""
Analyze the academic performance of a student.

Student Name: {name}
Percentage: {percentage:.2f}%
Grade: {grade}
Attendance: {attendance:.2f}%
Result: {result}

Provide:
1. Overall performance
2. Strength
3. Weakness
4. Improvement suggestions
5. Short motivational message

Keep the answer simple and suitable for a college project.
"""
            response = client.responses.create(
                model="gpt-5-mini",
                input=prompt
            )
            return response.output_text

        except Exception:
            return ("AI analysis could not be generated. Basic analysis is shown below.\n\n"
                    + basic_analysis(percentage, attendance, grade))

    return basic_analysis(percentage, attendance, grade)


# ---------------- GRADE ----------------

def calculate_grade(percentage):
    if percentage >= 90:
        return "A+"
    elif percentage >= 80:
        return "A"
    elif percentage >= 70:
        return "B"
    elif percentage >= 60:
        return "C"
    elif percentage >= 50:
        return "D"
    return "F"


# ---------------- HELPERS ----------------

def parse_number(text):
    """Convert text to a finite float, else raise ValueError."""
    value = float(text)
    if not math.isfinite(value):
        raise ValueError("not finite")
    return value


# ---------------- ADD STUDENT ----------------

def add_student():
    name = name_entry.get().strip()
    roll = roll_entry.get().strip()
    class_name = class_entry.get().strip()

    if not name or not roll or not class_name:
        messagebox.showerror("Error", "Please enter student details.")
        return

    try:
        marks = [parse_number(e.get()) for e in mark_entries]
        attendance = parse_number(attendance_entry.get())
    except ValueError:
        messagebox.showerror("Error", "Please enter valid numeric marks and attendance.")
        return

    if any(m < 0 or m > 100 for m in marks):
        messagebox.showerror("Error", "Marks must be between 0 and 100.")
        return

    if attendance < 0 or attendance > 100:
        messagebox.showerror("Error", "Attendance must be between 0 and 100.")
        return

    cursor.execute("SELECT 1 FROM students WHERE roll_no = ?", (roll,))
    if cursor.fetchone():
        messagebox.showerror("Error", f"Roll No {roll} already exists.")
        return

    total = sum(marks)
    percentage = total / len(marks)

    result = "PASS" if all(m >= 33 for m in marks) else "FAIL"
    grade = calculate_grade(percentage) if result == "PASS" else "F"

    # AI call can take a moment, so show a wait cursor
    root.config(cursor="watch")
    root.update_idletasks()
    try:
        analysis = get_ai_analysis(name, percentage, attendance, grade, result)
    finally:
        root.config(cursor="")

    cursor.execute("""
        INSERT INTO students
        (name, roll_no, class_name, math, science, english, computer,
         social_science, attendance, total, percentage, grade, result, analysis)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (name, roll, class_name, *marks, attendance,
          total, percentage, grade, result, analysis))
    conn.commit()

    messagebox.showinfo(
        "Success",
        f"Student added successfully!\n\n"
        f"Percentage: {percentage:.2f}%\n"
        f"Grade: {grade}\n"
        f"Result: {result}"
    )

    clear_fields()
    show_students()


# ---------------- SHOW STUDENTS ----------------

def show_students():
    for item in tree.get_children():
        tree.delete(item)

    cursor.execute("""
        SELECT id, name, roll_no, class_name, percentage, grade, attendance, result
        FROM students
        ORDER BY id
    """)

    for rec in cursor.fetchall():
        # iid = database id, so selection maps to exactly one record
        tree.insert("", tk.END, iid=str(rec[0]), values=(
            rec[1], rec[2], rec[3],
            f"{rec[4]:.2f}%", rec[5], f"{rec[6]:.2f}%", rec[7]
        ))


# ---------------- VIEW ANALYSIS ----------------

def view_analysis():
    selected = tree.selection()
    if not selected:
        messagebox.showwarning("Select Student", "Please select a student first.")
        return

    student_id = int(selected[0])
    cursor.execute("SELECT name, analysis FROM students WHERE id = ?", (student_id,))
    record = cursor.fetchone()
    if not record:
        return

    win = tk.Toplevel(root)
    win.title("AI Performance Analysis")
    win.geometry("650x500")

    tk.Label(win, text="AI PERFORMANCE ANALYSIS",
             font=("Arial", 18, "bold"), fg="#1d3557").pack(pady=15)
    tk.Label(win, text=f"Student: {record[0]}",
             font=("Arial", 13, "bold")).pack(pady=5)

    text_box = tk.Text(win, wrap=tk.WORD, font=("Arial", 11), width=70, height=20)
    text_box.pack(padx=20, pady=15, fill=tk.BOTH, expand=True)
    text_box.insert(tk.END, record[1] or "No analysis available.")
    text_box.config(state=tk.DISABLED)


# ---------------- DELETE STUDENT ----------------

def delete_student():
    selected = tree.selection()
    if not selected:
        messagebox.showwarning("Select Student", "Please select a student to delete.")
        return

    if messagebox.askyesno("Confirm Delete",
                           "Are you sure you want to delete this student?"):
        cursor.execute("DELETE FROM students WHERE id = ?", (int(selected[0]),))
        conn.commit()
        show_students()
        messagebox.showinfo("Deleted", "Student record deleted successfully.")


# ---------------- CLEAR FIELDS ----------------

def clear_fields():
    for entry in [name_entry, roll_entry, class_entry,
                  *mark_entries, attendance_entry]:
        entry.delete(0, tk.END)


# ---------------- CLOSE ----------------

def on_close():
    conn.close()
    root.destroy()


# ---------------- GUI ----------------

root = tk.Tk()
root.title("AI-Based Student Performance Analysis System")
root.geometry("1100x700")
root.configure(bg="#eef2f7")
root.protocol("WM_DELETE_WINDOW", on_close)

# Header
header = tk.Frame(root, bg="#1d3557", height=80)
header.pack(fill=tk.X)
tk.Label(header, text="AI-BASED STUDENT PERFORMANCE ANALYSIS SYSTEM",
         font=("Arial", 20, "bold"), bg="#1d3557", fg="white").pack(pady=22)

# Student info
input_frame = tk.LabelFrame(root, text="Student Information",
                            font=("Arial", 13, "bold"), bg="#eef2f7",
                            padx=15, pady=15)
input_frame.pack(fill=tk.X, padx=20, pady=15)

tk.Label(input_frame, text="Student Name:", bg="#eef2f7").grid(row=0, column=0, padx=10, pady=8)
name_entry = tk.Entry(input_frame, width=20)
name_entry.grid(row=0, column=1, padx=10)

tk.Label(input_frame, text="Roll No:", bg="#eef2f7").grid(row=0, column=2, padx=10)
roll_entry = tk.Entry(input_frame, width=15)
roll_entry.grid(row=0, column=3, padx=10)

tk.Label(input_frame, text="Class:", bg="#eef2f7").grid(row=0, column=4, padx=10)
class_entry = tk.Entry(input_frame, width=15)
class_entry.grid(row=0, column=5, padx=10)

# Marks
subject_frame = tk.LabelFrame(root, text="Marks & Attendance",
                              font=("Arial", 13, "bold"), bg="#eef2f7",
                              padx=15, pady=15)
subject_frame.pack(fill=tk.X, padx=20, pady=5)

subjects = ["Math", "Science", "English", "Computer", "Social Science"]
mark_entries = []

for i, subject in enumerate(subjects):
    tk.Label(subject_frame, text=subject + ":", bg="#eef2f7").grid(row=0, column=i * 2, padx=5)
    entry = tk.Entry(subject_frame, width=8)
    entry.grid(row=0, column=i * 2 + 1, padx=5)
    mark_entries.append(entry)

tk.Label(subject_frame, text="Attendance %:", bg="#eef2f7").grid(row=1, column=0, padx=5, pady=15)
attendance_entry = tk.Entry(subject_frame, width=8)
attendance_entry.grid(row=1, column=1)

# Buttons
button_frame = tk.Frame(root, bg="#eef2f7")
button_frame.pack(pady=10)

buttons = [
    ("Add Student", add_student, "#2a9d8f", 15),
    ("View AI Analysis", view_analysis, "#457b9d", 17),
    ("Delete Student", delete_student, "#e63946", 17),
    ("Clear", clear_fields, "#6c757d", 12),
]
for col, (text, cmd, color, width) in enumerate(buttons):
    tk.Button(button_frame, text=text, command=cmd, bg=color, fg="white",
              font=("Arial", 11, "bold"), width=width).grid(row=0, column=col, padx=8)

# Table
table_frame = tk.Frame(root)
table_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

columns = ("Name", "Roll No", "Class", "Percentage", "Grade", "Attendance", "Result")
tree = ttk.Treeview(table_frame, columns=columns, show="headings")

for column in columns:
    tree.heading(column, text=column)
    tree.column(column, width=130, anchor=tk.CENTER)

scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=tree.yview)
tree.configure(yscrollcommand=scrollbar.set)
tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

show_students()
root.mainloop()