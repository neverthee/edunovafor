from datetime import datetime

from backend.extensions import db


teacher_class_students = db.Table(
    'teacher_class_students',
    db.Column('class_id', db.Integer, db.ForeignKey('teacher_classes.id'), primary_key=True),
    db.Column('student_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
)


assessment_publish_classes = db.Table(
    'assessment_publish_classes',
    db.Column('assessment_id', db.Integer, db.ForeignKey('assessments.id'), primary_key=True),
    db.Column('class_id', db.Integer, db.ForeignKey('teacher_classes.id'), primary_key=True),
)


class TeacherClass(db.Model):
    __tablename__ = 'teacher_classes'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    teacher = db.relationship('User', backref=db.backref('teacher_classes', lazy='dynamic'))
    students = db.relationship(
        'User',
        secondary=teacher_class_students,
        lazy='subquery',
        backref=db.backref('joined_teacher_classes', lazy=True),
    )

    def __repr__(self):
        return f'<TeacherClass {self.name}>'

    def to_dict(self, include_students=True):
        data = {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'teacher_id': self.teacher_id,
            'student_count': len(self.students) if self.students else 0,
            'student_ids': [student.id for student in self.students] if self.students else [],
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

        if include_students:
            data['students'] = [student.to_dict() for student in self.students] if self.students else []

        return data
