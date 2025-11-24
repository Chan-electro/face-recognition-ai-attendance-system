from datetime import datetime, timedelta
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
import csv
import io
from models.user import User
from models.subject import Subject
from services.attendance_service import AttendanceService


class ReportService:
    """Service for generating attendance reports"""
    
    @staticmethod
    def generate_csv_report(student_id, start_date=None, end_date=None, subject_id=None):
        """Generate CSV attendance report"""
        try:
            # Get student
            student = User.query.get(student_id)
            if not student:
                return None
            
            # Set default date range if not provided
            if not end_date:
                end_date = datetime.now().date()
            if not start_date:
                start_date = end_date - timedelta(days=30)
            
            # Get attendance records
            records = AttendanceService.get_attendance_by_date_range(
                student_id, start_date, end_date, subject_id
            )
            
            # Create CSV in memory
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Write header
            writer.writerow([
                'Date', 'Time', 'Subject', 'Status', 'Marked By', 
                'Confidence', 'Is Manual', 'Notes'
            ])
            
            # Write data
            for record in records:
                writer.writerow([
                    record['date'],
                    record['time'],
                    record['subject_name'],
                    record['status'],
                    record.get('marked_by', 'N/A'),
                    record.get('confidence_score', 'N/A'),
                    'Yes' if record.get('is_manual') else 'No',
                    record.get('notes', '')
                ])
            
            return output.getvalue()
            
        except Exception as e:
            print(f"Error generating CSV report: {e}")
            return None
    
    @staticmethod
    def generate_pdf_report(student_id, start_date=None, end_date=None):
        """Generate PDF attendance report"""
        try:
            # Get student
            student = User.query.get(student_id)
            if not student:
                return None
            
            # Set default date range
            if not end_date:
                end_date = datetime.now().date()
            if not start_date:
                start_date = end_date - timedelta(days=30)
            
            # Create PDF in memory
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72,
                                   topMargin=72, bottomMargin=18)
            
            # Container for elements
            elements = []
            styles = getSampleStyleSheet()
            
            # Title
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=24,
                textColor=colors.HexColor('#1f2937'),
                spaceAfter=30,
                alignment=TA_CENTER
            )
            
            title = Paragraph("Attendance Report", title_style)
            elements.append(title)
            
            # Student info
            info_style = styles['Normal']
            info_data = [
                f"<b>Student Name:</b> {student.full_name}",
                f"<b>Student ID:</b> {student.student_id}",
                f"<b>Department:</b> {student.department}",
                f"<b>Semester:</b> {student.semester}",
                f"<b>Report Period:</b> {start_date} to {end_date}",
                f"<b>Generated On:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            ]
            
            for info in info_data:
                elements.append(Paragraph(info, info_style))
                elements.append(Spacer(1, 6))
            
            elements.append(Spacer(1, 20))
            
            # Subject-wise attendance
            subject_attendance = AttendanceService.get_subject_wise_attendance(student_id)
            
            if subject_attendance:
                # Table header
                table_data = [['Subject Code', 'Subject Name', 'Present', 'Absent', 'Late', 'Total', 'Percentage']]
                
                # Add rows
                for subject in subject_attendance:
                    table_data.append([
                        subject['subject_code'],
                        subject['subject_name'],
                        str(subject['present']),
                        str(subject['absent']),
                        str(subject['late']),
                        str(subject['total']),
                        f"{subject['percentage']}%"
                    ])
                
                # Create table
                table = Table(table_data, colWidths=[1*inch, 2.5*inch, 0.8*inch, 0.8*inch, 0.8*inch, 0.8*inch, 1*inch])
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3b82f6')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 12),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                
                elements.append(table)
            
            # Build PDF
            doc.build(elements)
            
            # Get buffer value
            pdf_data = buffer.getvalue()
            buffer.close()
            
            return pdf_data
            
        except Exception as e:
            print(f"Error generating PDF report: {e}")
            return None
    
    @staticmethod
    def generate_class_report_csv(subject_id, attendance_date=None):
        """Generate CSV report for entire class"""
        try:
            subject = Subject.query.get(subject_id)
            if not subject:
                return None
            
            if not attendance_date:
                attendance_date = datetime.now().date()
            
            # Get class attendance
            records = AttendanceService.get_class_attendance(subject_id, attendance_date)
            
            # Create CSV
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Header
            writer.writerow([
                'Student ID', 'Student Name', 'Status', 'Marked At', 'Confidence'
            ])
            
            # Data
            for record in records:
                writer.writerow([
                    record['student_code'],
                    record['student_name'],
                    record['status'],
                    record.get('marked_at', 'N/A'),
                    record.get('confidence', 'N/A')
                ])
            
            return output.getvalue()
            
        except Exception as e:
            print(f"Error generating class report: {e}")
            return None
