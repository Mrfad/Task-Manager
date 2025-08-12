# tasks/utils.py or tasks/exports.py
import openpyxl
from django.http import HttpResponse
from django.utils.encoding import smart_str
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


def export_tasks_to_excel(queryset, filename="tasks_export.xlsx"):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Tasks"

    headers = ['ID', 'Job Number', 'Job Name', 'Status', 'Paid', 'Customer']
    ws.append(headers)

    for task in queryset:
        ws.append([
            task.id,
            task.order_number,
            str(task.task_name),
            task.get_status_display(),
            task.get_paid_status_display(),
            task.customer_name.customer_name
        ])

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename={smart_str(filename)}'
    wb.save(response)
    return response


def export_tasks_to_pdf(queryset, filename="tasks_export.pdf"):
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename={filename}'

    p = canvas.Canvas(response, pagesize=letter)
    width, height = letter

    y = height - 40
    p.setFont("Helvetica-Bold", 14)
    p.drawString(30, y, "Task Export")

    y -= 30
    p.setFont("Helvetica", 10)
    for task in queryset:
        line = f"{task.id} | {task.order_number} | {task.task_name} | {task.get_status_display()} | {task.get_paid_status_display()} | {task.customer_name.customer_name}"
        p.drawString(30, y, line)
        y -= 15
        if y < 40:
            p.showPage()
            y = height - 40

    p.save()
    return response
