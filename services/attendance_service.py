from datetime import datetime, date, timedelta
from models import db
from models.attendance import Attendance
from models.user import User
from models.subject import Subject


class AttendanceService:
    """Service for attendance calculations and analytics"""
    
    @staticmethod
    def mark_attendance(student_id, subject_id, status='PRESENT', marked_by=None, 
                       confidence_score=None, is_manual=False, notes=None):
        """
        Mark attendance for a student
        
        Args:
            student_id: Student user ID
            subject_id: Subject ID
            status: PRESENT, ABSENT, or LATE
            marked_by: Teacher user ID who marked attendance
            confidence_score: Face recognition confidence (if applicable)
            is_manual: Whether manually marked or via face recognition
            notes: Optional notes
            
        Returns:
            Attendance object or None if failed
        """
        try:
            today = date.today()
            now = datetime.now()
            
            # Check if attendance already exists for today
            existing = Attendance.query.filter_by(
                student_id=student_id,
                subject_id=subject_id,
                date=today
            ).first()
            
            if existing:
                # Update existing record
                existing.status = status
                existing.marked_by = marked_by
                existing.marked_at = now
                existing.time = now.time()
                existing.confidence_score = confidence_score
                existing.is_manual = is_manual
                existing.notes = notes
                attendance = existing
            else:
                # Create new record
                attendance = Attendance(
                    student_id=student_id,
                    subject_id=subject_id,
                    date=today,
                    time=now.time(),
                    status=status,
                    marked_by=marked_by,
                    confidence_score=confidence_score,
                    is_manual=is_manual,
                    notes=notes
                )
                db.session.add(attendance)
            
            db.session.commit()
            return attendance
            
        except Exception as e:
            print(f"Error marking attendance: {e}")
            db.session.rollback()
            return None
    
    @staticmethod
    def get_attendance_percentage(student_id, subject_id=None, start_date=None, end_date=None):
        """Calculate attendance percentage"""
        query = Attendance.query.filter_by(student_id=student_id)
        
        if subject_id:
            query = query.filter_by(subject_id=subject_id)
        
        if start_date:
            query = query.filter(Attendance.date >= start_date)
        
        if end_date:
            query = query.filter(Attendance.date <= end_date)
        
        total = query.count()
        if total == 0:
            return 0.0
        
        present = query.filter(Attendance.status.in_(['PRESENT', 'LATE'])).count()
        return round((present / total) * 100, 2)
    
    @staticmethod
    def get_attendance_stats(student_id, subject_id=None):
        """Get detailed attendance statistics"""
        query = Attendance.query.filter_by(student_id=student_id)
        
        if subject_id:
            query = query.filter_by(subject_id=subject_id)
        
        records = query.all()
        
        if not records:
            return {
                'total': 0,
                'present': 0,
                'absent': 0,
                'late': 0,
                'percentage': 0.0
            }
        
        stats = {
            'total': len(records),
            'present': sum(1 for r in records if r.status == 'PRESENT'),
            'absent': sum(1 for r in records if r.status == 'ABSENT'),
            'late': sum(1 for r in records if r.status == 'LATE'),
        }
        
        stats['percentage'] = round(
            ((stats['present'] + stats['late']) / stats['total']) * 100, 2
        )
        
        return stats
    
    @staticmethod
    def calculate_required_classes(student_id, subject_id, target_percentage=75):
        """
        Calculate number of classes needed to reach target attendance percentage
        
        Returns:
            dict with current stats and classes needed
        """
        stats = AttendanceService.get_attendance_stats(student_id, subject_id)
        
        if stats['total'] == 0:
            return {
                'current_percentage': 0,
                'target_percentage': target_percentage,
                'classes_needed': 0,
                'can_skip': 0,
                'message': 'No attendance records found'
            }
        
        current_present = stats['present'] + stats['late']
        current_total = stats['total']
        current_percentage = stats['percentage']
        
        # Calculate classes needed
        if current_percentage >= target_percentage:
            # Calculate how many can be skipped
            can_skip = 0
            temp_present = current_present
            temp_total = current_total
            
            while ((temp_present / (temp_total + 1)) * 100) >= target_percentage:
                can_skip += 1
                temp_total += 1
            
            return {
                'current_percentage': current_percentage,
                'target_percentage': target_percentage,
                'classes_needed': 0,
                'can_skip': can_skip,
                'message': f'You can skip up to {can_skip} classes and still maintain {target_percentage}% attendance'
            }
        else:
            # Calculate classes needed to reach target
            classes_needed = 0
            temp_present = current_present
            temp_total = current_total
            
            while ((temp_present / temp_total) * 100) < target_percentage:
                classes_needed += 1
                temp_present += 1
                temp_total += 1
            
            return {
                'current_percentage': current_percentage,
                'target_percentage': target_percentage,
                'classes_needed': classes_needed,
                'can_skip': 0,
                'message': f'You need to attend {classes_needed} consecutive classes to reach {target_percentage}% attendance'
            }
    
    @staticmethod
    def get_subject_wise_attendance(student_id):
        """Get attendance breakdown by subject"""
        subjects = Subject.query.filter_by(is_active=True).all()
        result = []
        
        for subject in subjects:
            stats = AttendanceService.get_attendance_stats(student_id, subject.id)
            if stats['total'] > 0:
                result.append({
                    'subject_id': subject.id,
                    'subject_name': subject.name,
                    'subject_code': subject.code,
                    **stats
                })
        
        return result
    
    @staticmethod
    def get_recent_attendance(student_id, limit=10):
        """Get recent attendance records"""
        records = Attendance.query.filter_by(student_id=student_id)\
                                  .order_by(Attendance.date.desc(), Attendance.time.desc())\
                                  .limit(limit)\
                                  .all()
        
        return [record.to_dict() for record in records]
    
    @staticmethod
    def get_attendance_by_date_range(student_id, start_date, end_date, subject_id=None):
        """Get attendance records for a date range"""
        query = Attendance.query.filter_by(student_id=student_id)\
                                .filter(Attendance.date >= start_date)\
                                .filter(Attendance.date <= end_date)
        
        if subject_id:
            query = query.filter_by(subject_id=subject_id)
        
        records = query.order_by(Attendance.date.desc()).all()
        return [record.to_dict() for record in records]
    
    @staticmethod
    def get_class_attendance(subject_id, attendance_date=None):
        """Get attendance for entire class for a subject on a specific date"""
        if attendance_date is None:
            attendance_date = date.today()
        
        records = Attendance.query.filter_by(
            subject_id=subject_id,
            date=attendance_date
        ).all()
        
        # Get all students
        students = User.query.filter_by(role='STUDENT', is_active=True).all()
        
        result = []
        for student in students:
            record = next((r for r in records if r.student_id == student.id), None)
            result.append({
                'student_id': student.id,
                'student_name': student.full_name,
                'student_code': student.student_id,
                'status': record.status if record else 'NOT_MARKED',
                'marked_at': record.marked_at.isoformat() if record and record.marked_at else None,
                'confidence': record.confidence_score if record else None
            })
        
        return result
