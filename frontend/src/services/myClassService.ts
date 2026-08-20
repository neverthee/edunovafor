export interface MyClassStudentRecord {
  id: number;
  username: string;
  email: string;
  full_name?: string;
  role: 'student';
  created_at?: string;
  added_at?: string;
}

export interface TeacherClassRecord {
  id: number;
  name: string;
  description?: string;
  teacher_id: number;
  student_count: number;
  student_ids: number[];
  students: MyClassStudentRecord[];
  created_at?: string;
  updated_at?: string;
}

function getStorageKey(teacherId?: number | string | null) {
  return `edunova:teacher-classes:${teacherId ?? 'anonymous'}`;
}

export function getMyClasses(teacherId?: number | string | null): TeacherClassRecord[] {
  if (typeof window === 'undefined') {
    return [];
  }

  try {
    const raw = window.localStorage.getItem(getStorageKey(teacherId));
    if (!raw) {
      return [];
    }

    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) {
      return [];
    }

    return parsed
      .filter((item): item is TeacherClassRecord => Boolean(item && typeof item.id === 'number'))
      .sort((left, right) => new Date(right.updated_at || right.created_at || 0).getTime() - new Date(left.updated_at || left.created_at || 0).getTime());
  } catch (error) {
    console.error('读取我的班级缓存失败:', error);
    return [];
  }
}

export function syncMyClassesCache(teacherId: number | string | null | undefined, classes: TeacherClassRecord[]) {
  if (typeof window === 'undefined') {
    return;
  }

  window.localStorage.setItem(getStorageKey(teacherId), JSON.stringify(classes));
}

export function getMyClassStudents(teacherId?: number | string | null): MyClassStudentRecord[] {
  const classes = getMyClasses(teacherId);
  const studentMap = new Map<number, MyClassStudentRecord>();

  classes.forEach((teacherClass) => {
    (teacherClass.students || []).forEach((student) => {
      if (!studentMap.has(student.id)) {
        studentMap.set(student.id, student);
      }
    });
  });

  return Array.from(studentMap.values()).sort((left, right) => {
    const leftTime = new Date(left.added_at || left.created_at || 0).getTime();
    const rightTime = new Date(right.added_at || right.created_at || 0).getTime();
    return rightTime - leftTime;
  });
}

export function getMyClassStudentIds(teacherId?: number | string | null) {
  return getMyClassStudents(teacherId).map(student => student.id);
}
