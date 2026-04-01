"""
PyRanSeat - Classroom Seating Arrangement Tool
Flask Backend Service
Features: Constraint seating, front-back swap, group rotation, history, student tags, templates
"""

import os
import sys
import json
import random
import threading
import copy
from datetime import datetime
from flask import Flask, render_template, jsonify, request, send_file

app = Flask(__name__)

# Data file paths - handle PyInstaller packaging
def get_app_dir():
    """Get the application directory (works for both dev and PyInstaller)"""
    if getattr(sys, 'frozen', False):
        # Running as compiled executable (PyInstaller)
        return os.path.dirname(sys.executable)
    else:
        # Running in development mode
        return os.path.dirname(os.path.abspath(__file__))

DATA_DIR = os.path.join(get_app_dir(), 'data')
DATA_FILE = os.path.join(DATA_DIR, 'seat_data.json')
HISTORY_FILE = os.path.join(DATA_DIR, 'seat_history.json')

# Data lock for thread safety
data_lock = threading.Lock()

# Default configuration
DEFAULT_ROWS = 6
DEFAULT_COLS = 8

# Maximum history records
MAX_HISTORY = 20

# Seat templates
SEAT_TEMPLATES = {
    'standard': {
        'name': 'Standard Layout',
        'description': 'Standard single-seat arrangement',
        'icon': 'grid',
        'layout_mode': 'single',
        'default_rows': 6,
        'default_cols': 8
    },
    'double': {
        'name': 'Double Layout',
        'description': 'Paired seating with aisle in middle',
        'icon': 'columns',
        'layout_mode': 'double',
        'default_rows': 6,
        'default_cols': 8,
        'aisle_after': 2
    },
    'exam': {
        'name': 'Exam Layout',
        'description': 'Maximized spacing for exams',
        'icon': 'maximize',
        'layout_mode': 'exam',
        'default_rows': 5,
        'default_cols': 6,
        'spacing': 'wide'
    },
    'group_4': {
        'name': 'Group of 4',
        'description': 'Groups of 4 for collaboration',
        'icon': 'users',
        'layout_mode': 'group',
        'default_rows': 4,
        'default_cols': 8,
        'group_size': 4
    },
    'group_6': {
        'name': 'Group of 6',
        'description': 'Groups of 6 for larger teams',
        'icon': 'users',
        'layout_mode': 'group',
        'default_rows': 4,
        'default_cols': 6,
        'group_size': 6
    },
    'lecture': {
        'name': 'Lecture Layout',
        'description': 'Wide spacing, focus on front',
        'icon': 'monitor',
        'layout_mode': 'lecture',
        'default_rows': 5,
        'default_cols': 10
    }
}

# Student tag types
STUDENT_TAG_TYPES = {
    'vision': {
        'name': 'Vision',
        'color': '#3B82F6',
        'options': ['normal', 'nearsighted', 'farsighted', 'strong_nearsighted']
    },
    'height': {
        'name': 'Height',
        'color': '#10B981',
        'options': ['short', 'medium', 'tall']
    },
    'behavior': {
        'name': 'Behavior',
        'color': '#F59E0B',
        'options': ['normal', 'needs_attention', 'quiet', 'active']
    },
    'special': {
        'name': 'Special Needs',
        'color': '#EF4444',
        'options': ['none', 'front_row', 'wheelchair', 'hearing_impairment']
    },
    'academic': {
        'name': 'Academic',
        'color': '#8B5CF6',
        'options': ['excellent', 'good', 'average', 'needs_help']
    }
}


def ensure_data_dir():
    """Ensure data directory exists"""
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)


def load_data():
    """Load seating data"""
    ensure_data_dir()
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Ensure new fields exist
                if 'student_tags' not in data:
                    data['student_tags'] = {}
                if 'current_template' not in data:
                    data['current_template'] = 'standard'
                if 'desk_pairs' not in data:
                    data['desk_pairs'] = []  # List of [[r1,c1], [r2,c2]] pairs
                if 'layout_mode' not in data:
                    data['layout_mode'] = 'single'  # single, double, custom
                return data
        except (json.JSONDecodeError, IOError):
            pass
    # Return default data
    return {
        'rows': DEFAULT_ROWS,
        'cols': DEFAULT_COLS,
        'seats': [[None for _ in range(DEFAULT_COLS)] for _ in range(DEFAULT_ROWS)],
        'students': [],
        'constraints': [],
        'student_tags': {},
        'current_template': 'standard',
        'desk_pairs': [],
        'layout_mode': 'single'
    }


def save_data(data):
    """Save seating data"""
    ensure_data_dir()
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_history():
    """Load history records"""
    ensure_data_dir()
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return []


def save_history(history):
    """Save history records"""
    ensure_data_dir()
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def add_to_history(seats, rows, cols, students, constraints, action='manual', layout_mode='single', desk_pairs=None):
    """Add seating snapshot to history"""
    history = load_history()
    
    snapshot = {
        'id': datetime.now().strftime('%Y%m%d%H%M%S') + str(random.randint(100, 999)),
        'timestamp': datetime.now().isoformat(),
        'action': action,
        'rows': rows,
        'cols': cols,
        'seats': copy.deepcopy(seats),
        'students': copy.deepcopy(students),
        'constraints': copy.deepcopy(constraints),
        'layout_mode': layout_mode,
        'desk_pairs': copy.deepcopy(desk_pairs) if desk_pairs else []
    }
    
    history.insert(0, snapshot)
    
    # Limit history records
    if len(history) > MAX_HISTORY:
        history = history[:MAX_HISTORY]
    
    save_history(history)
    return snapshot


# ==================== Constraint Algorithm ====================

def get_neighbors(rows, cols, r, c):
    """Get adjacent seats (up, down, left, right)"""
    neighbors = []
    directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]  # up, down, left, right
    for dr, dc in directions:
        nr, nc = r + dr, c + dc
        if 0 <= nr < rows and 0 <= nc < cols:
            neighbors.append((nr, nc))
    return neighbors


def get_deskmate_position(rows, cols, r, c):
    """Get deskmate position (left or right adjacent) for double-seat mode"""
    # Prefer right neighbor, then left neighbor
    for dc in [1, -1]:
        nc = c + dc
        if 0 <= nc < cols:
            return (r, nc)
    return None


def get_all_deskmate_pairs(rows, cols):
    """Get all possible deskmate pairs for double-seat mode"""
    pairs = []
    for r in range(rows):
        c = 0
        while c < cols:
            if c + 1 < cols:
                pairs.append(((r, c), (r, c + 1)))
                c += 2
            else:
                c += 1
    return pairs


def find_student_position(seats, rows, cols, student_name):
    """Find student position in seat matrix"""
    for r in range(rows):
        for c in range(cols):
            if seats[r][c] == student_name:
                return (r, c)
    return None


def check_constraint_satisfied(seats, rows, cols, constraint, layout_mode='single'):
    """Check if a single constraint is satisfied"""
    student_a = constraint['studentA']
    student_b = constraint['studentB']
    constraint_type = constraint['type']
    
    pos_a = find_student_position(seats, rows, cols, student_a)
    pos_b = find_student_position(seats, rows, cols, student_b)
    
    # If either student not in seat, consider satisfied
    if pos_a is None or pos_b is None:
        return True
    
    r_a, c_a = pos_a
    
    if constraint_type == 'avoid':
        # Avoid: cannot be adjacent
        neighbors = get_neighbors(rows, cols, r_a, c_a)
        is_adjacent = pos_b in neighbors
        return not is_adjacent
    elif constraint_type == 'together':
        if layout_mode in ['double', 'custom']:
            # In double/custom mode, together means deskmate (left-right)
            deskmate_pos = get_deskmate_position(rows, cols, r_a, c_a)
            if deskmate_pos:
                # Check if B is the deskmate of A
                is_deskmate = pos_b == deskmate_pos
                # Also check reverse: A is deskmate of B
                r_b, c_b = pos_b
                deskmate_pos_b = get_deskmate_position(rows, cols, r_b, c_b)
                if deskmate_pos_b:
                    is_deskmate = is_deskmate or pos_a == deskmate_pos_b
                return is_deskmate
            return False
        else:
            # Single mode: must be adjacent (any direction)
            neighbors = get_neighbors(rows, cols, r_a, c_a)
            return pos_b in neighbors
    
    return True


def count_violations(seats, rows, cols, constraints, layout_mode='single'):
    """Count constraint violations"""
    violations = []
    for constraint in constraints:
        if not check_constraint_satisfied(seats, rows, cols, constraint, layout_mode):
            violations.append(constraint)
    return violations


def try_swap_students(seats, rows, cols, pos1, pos2):
    """Try swapping two seat students"""
    r1, c1 = pos1
    r2, c2 = pos2
    seats[r1][c1], seats[r2][c2] = seats[r2][c2], seats[r1][c1]


def optimize_with_constraints(seats, rows, cols, constraints, layout_mode='single', max_attempts=500):
    """Use local swap to optimize seats for constraints"""
    seats = copy.deepcopy(seats)
    violations = count_violations(seats, rows, cols, constraints, layout_mode)
    
    if not violations:
        return seats, []
    
    # Collect all occupied seat positions
    occupied_positions = []
    for r in range(rows):
        for c in range(cols):
            if seats[r][c] is not None:
                occupied_positions.append((r, c))
    
    if len(occupied_positions) < 2:
        return seats, violations
    
    attempt = 0
    best_seats = copy.deepcopy(seats)
    best_violations = violations
    
    while attempt < max_attempts and violations:
        # Randomly select a violating student
        violation = random.choice(violations)
        
        # Randomly select two positions to try swap
        pos1 = find_student_position(seats, rows, cols, violation['studentA'])
        if pos1 is None:
            pos1 = random.choice(occupied_positions)
        
        # For together constraint in double mode, try to place students as deskmates
        if violation['type'] == 'together' and layout_mode in ['double', 'custom']:
            pos2 = find_student_position(seats, rows, cols, violation['studentB'])
            if pos2 is None:
                pos2 = random.choice(other_positions)
            
            # Find the deskmate position for pos1
            r1, c1 = pos1
            deskmate_pos = get_deskmate_position(rows, cols, r1, c1)
            
            if deskmate_pos:
                # Try to swap someone into the deskmate position
                r_d, c_d = deskmate_pos
                # If pos2 is not already the deskmate, swap
                if pos2 != deskmate_pos:
                    try_swap_students(seats, rows, cols, pos2, deskmate_pos)
                    new_violations = count_violations(seats, rows, cols, constraints, layout_mode)
                    
                    if len(new_violations) <= len(best_violations):
                        if len(new_violations) < len(best_violations):
                            best_seats = copy.deepcopy(seats)
                            best_violations = new_violations
                        violations = new_violations
                    else:
                        # Revert
                        try_swap_students(seats, rows, cols, pos2, deskmate_pos)
            
            attempt += 1
            continue
        
        # Select another position
        other_positions = [p for p in occupied_positions if p != pos1]
        if not other_positions:
            break
        pos2 = random.choice(other_positions)
        
        # Try swap
        try_swap_students(seats, rows, cols, pos1, pos2)
        new_violations = count_violations(seats, rows, cols, constraints, layout_mode)
        
        if len(new_violations) <= len(best_violations):
            # Accept swap
            if len(new_violations) < len(best_violations):
                best_seats = copy.deepcopy(seats)
                best_violations = new_violations
            violations = new_violations
        else:
            # Revert swap
            try_swap_students(seats, rows, cols, pos1, pos2)
        
        attempt += 1
    
    return best_seats, best_violations


def place_deskmates_together(seats, rows, cols, together_constraints):
    """Pre-place students with 'together' constraint as deskmates in double mode"""
    seats = copy.deepcopy(seats)
    placed_students = set()
    
    # Get all deskmate pair positions
    deskmate_pairs = get_all_deskmate_pairs(rows, cols)
    used_pairs = set()
    
    for constraint in together_constraints:
        student_a = constraint['studentA']
        student_b = constraint['studentB']
        
        if student_a in placed_students or student_b in placed_students:
            continue
        
        # Find current positions
        pos_a = find_student_position(seats, rows, cols, student_a)
        pos_b = find_student_position(seats, rows, cols, student_b)
        
        if pos_a is None or pos_b is None:
            continue
        
        # Check if already deskmates
        r_a, c_a = pos_a
        deskmate_of_a = get_deskmate_position(rows, cols, r_a, c_a)
        
        if deskmate_of_a == pos_b:
            # Already deskmates
            placed_students.add(student_a)
            placed_students.add(student_b)
            continue
        
        # Find an available deskmate pair
        for idx, ((r1, c1), (r2, c2)) in enumerate(deskmate_pairs):
            if idx in used_pairs:
                continue
            
            # Check if both positions are available or occupied by our students
            seat1 = seats[r1][c1]
            seat2 = seats[r2][c2]
            
            # Skip if either seat occupied by someone else (not our students)
            if seat1 and seat1 not in [student_a, student_b]:
                continue
            if seat2 and seat2 not in [student_a, student_b]:
                continue
            
            # Place both students as deskmates
            # First, find where they currently are and clear those spots
            if pos_a:
                seats[pos_a[0]][pos_a[1]] = None
            if pos_b:
                seats[pos_b[0]][pos_b[1]] = None
            
            seats[r1][c1] = student_a
            seats[r2][c2] = student_b
            
            used_pairs.add(idx)
            placed_students.add(student_a)
            placed_students.add(student_b)
            break
    
    return seats, placed_students


def check_swap_violation(seats, rows, cols, constraints, pos1, pos2, layout_mode='single'):
    """Check if swap would create new constraint violations"""
    # Create temporary seat matrix
    temp_seats = copy.deepcopy(seats)
    try_swap_students(temp_seats, rows, cols, pos1, pos2)
    
    # Check for violations
    violations = count_violations(temp_seats, rows, cols, constraints, layout_mode)
    return violations


def clean_constraints_for_students(constraints, students):
    """Clean constraints involving deleted students"""
    student_set = set(students)
    return [
        c for c in constraints 
        if c['studentA'] in student_set and c['studentB'] in student_set
    ]


# ==================== Routes ====================

@app.route('/')
def index():
    """Home page"""
    return render_template('index.html')


@app.route('/favicon.png')
def favicon():
    """Serve favicon"""
    favicon_path = os.path.join(get_app_dir(), 'icon.png')
    if os.path.exists(favicon_path):
        return send_file(favicon_path, mimetype='image/png')
    return '', 404


@app.route('/api/seats', methods=['GET'])
def get_seats():
    """Get current seat matrix, rows, cols, student list, constraint list"""
    with data_lock:
        data = load_data()
    return jsonify({
        'success': True,
        'rows': data['rows'],
        'cols': data['cols'],
        'seats': data['seats'],
        'students': data['students'],
        'constraints': data.get('constraints', []),
        'student_tags': data.get('student_tags', {}),
        'current_template': data.get('current_template', 'standard'),
        'desk_pairs': data.get('desk_pairs', []),
        'layout_mode': data.get('layout_mode', 'single')
    })


@app.route('/api/config', methods=['POST'])
def update_config():
    """Update rows and cols, reset empty seat matrix"""
    try:
        payload = request.get_json()
        new_rows = int(payload.get('rows', DEFAULT_ROWS))
        new_cols = int(payload.get('cols', DEFAULT_COLS))
        
        # Validate range
        if new_rows < 1 or new_rows > 20 or new_cols < 1 or new_cols > 20:
            return jsonify({'success': False, 'error': 'Rows and columns must be between 1-20'}), 400
        
        with data_lock:
            data = load_data()
            data['rows'] = new_rows
            data['cols'] = new_cols
            # Reset to empty seat matrix
            data['seats'] = [[None for _ in range(new_cols)] for _ in range(new_rows)]
            save_data(data)
        
        return jsonify({
            'success': True,
            'rows': new_rows,
            'cols': new_cols,
            'seats': data['seats'],
            'students': data['students'],
            'constraints': data.get('constraints', [])
        })
    except (ValueError, TypeError) as e:
        return jsonify({'success': False, 'error': str(e)}), 400


@app.route('/api/students', methods=['POST'])
def update_students():
    """Update student list"""
    try:
        payload = request.get_json()
        students = payload.get('students', [])
        
        # Validate student list
        if not isinstance(students, list):
            return jsonify({'success': False, 'error': 'Student list must be an array'}), 400
        
        # Filter empty strings
        students = [s.strip() for s in students if s and s.strip()]
        
        with data_lock:
            data = load_data()
            data['students'] = students
            # Clean constraints involving deleted students
            data['constraints'] = clean_constraints_for_students(
                data.get('constraints', []), students
            )
            save_data(data)
        
        return jsonify({
            'success': True,
            'students': students,
            'rows': data['rows'],
            'cols': data['cols'],
            'seats': data['seats'],
            'constraints': data['constraints']
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400


@app.route('/api/randomize', methods=['POST'])
def randomize_seats():
    """Randomize seats with constraint optimization"""
    with data_lock:
        data = load_data()
        students = data['students'].copy()
        rows = data['rows']
        cols = data['cols']
        constraints = data.get('constraints', [])
        total_seats = rows * cols
        
        # Check student count
        if len(students) > total_seats:
            return jsonify({
                'success': False, 
                'error': f'Students ({len(students)}) exceed total seats ({total_seats})'
            }), 400
        
        if len(students) == 0:
            return jsonify({
                'success': False,
                'error': 'Student list is empty'
            }), 400
        
        # Get layout mode
        layout_mode = data.get('layout_mode', 'single')
        
        # Shuffle students
        random.shuffle(students)
        
        # Create new seat matrix
        new_seats = [[None for _ in range(cols)] for _ in range(rows)]
        
        # In double/custom mode, prioritize together constraints as deskmates
        placed_students = set()
        if layout_mode in ['double', 'custom'] and constraints:
            together_constraints = [c for c in constraints if c['type'] == 'together']
            
            if together_constraints:
                # First fill seats randomly
                idx = 0
                for i in range(rows):
                    for j in range(cols):
                        if idx < len(students):
                            new_seats[i][j] = students[idx]
                            idx += 1
                
                # Place together students as deskmates
                new_seats, placed_students = place_deskmates_together(
                    new_seats, rows, cols, together_constraints
                )
        
        # Fill remaining seats
        remaining_students = [s for s in students if s not in placed_students]
        if remaining_students or not placed_students:
            idx = 0
            for i in range(rows):
                for j in range(cols):
                    if new_seats[i][j] is None and idx < len(remaining_students if placed_students else students):
                        new_seats[i][j] = remaining_students[idx] if placed_students else students[idx]
                        idx += 1
        
        # Optimize with constraints
        violations = []
        if constraints:
            new_seats, violations = optimize_with_constraints(
                new_seats, rows, cols, constraints, layout_mode
            )
        
        # Add to history
        add_to_history(new_seats, rows, cols, data['students'], constraints, 'randomize', layout_mode, data.get('desk_pairs', []))
        
        data['seats'] = new_seats
        save_data(data)
    
    response = {
        'success': True,
        'seats': new_seats,
        'rows': rows,
        'cols': cols,
        'students': data['students'],
        'constraints': constraints
    }
    
    if violations:
        response['warning'] = f'Some constraints cannot be satisfied ({len(violations)})'
        response['violations'] = [
            {'studentA': v['studentA'], 'studentB': v['studentB'], 'type': v['type']}
            for v in violations
        ]
    
    return jsonify(response)


@app.route('/api/swap', methods=['POST'])
def swap_seats():
    """Swap two seat students"""
    try:
        payload = request.get_json()
        pos1 = payload.get('pos1')  # [row, col]
        pos2 = payload.get('pos2')  # [row, col]
        
        if not pos1 or not pos2:
            return jsonify({'success': False, 'error': 'Missing seat coordinates'}), 400
        
        r1, c1 = int(pos1[0]), int(pos1[1])
        r2, c2 = int(pos2[0]), int(pos2[1])
        
        with data_lock:
            data = load_data()
            rows, cols = data['rows'], data['cols']
            seats = data['seats']
            constraints = data.get('constraints', [])
            
            # Validate coordinates
            if not (0 <= r1 < rows and 0 <= c1 < cols and 0 <= r2 < rows and 0 <= c2 < cols):
                return jsonify({'success': False, 'error': 'Seat coordinates out of range'}), 400
            
            # Cannot swap the same seat
            if r1 == r2 and c1 == c2:
                return jsonify({'success': False, 'error': 'Cannot swap the same seat'}), 400
            
            # Check constraints
            violations = check_swap_violation(seats, rows, cols, constraints, (r1, c1), (r2, c2))
            if violations:
                violation_info = ', '.join([
                    f"{v['studentA']} and {v['studentB']}" for v in violations[:3]
                ])
                return jsonify({
                    'success': False, 
                    'error': f'Constraint violation after swap: {violation_info}'
                }), 400
            
            # Execute swap
            seats[r1][c1], seats[r2][c2] = seats[r2][c2], seats[r1][c1]
            data['seats'] = seats
            save_data(data)
        
        return jsonify({
            'success': True,
            'seats': seats,
            'rows': rows,
            'cols': cols,
            'students': data['students'],
            'constraints': constraints
        })
    except (ValueError, TypeError, IndexError) as e:
        return jsonify({'success': False, 'error': str(e)}), 400


@app.route('/api/reset', methods=['POST'])
def reset_seats():
    """Reset seats (clear all students)"""
    with data_lock:
        data = load_data()
        rows, cols = data['rows'], data['cols']
        data['seats'] = [[None for _ in range(cols)] for _ in range(rows)]
        save_data(data)
    
    return jsonify({
        'success': True,
        'seats': data['seats'],
        'rows': rows,
        'cols': cols,
        'students': data['students'],
        'constraints': data.get('constraints', [])
    })


# ==================== Constraint Management API ====================

@app.route('/api/constraints', methods=['GET'])
def get_constraints():
    """Get constraint list"""
    with data_lock:
        data = load_data()
    return jsonify({
        'success': True,
        'constraints': data.get('constraints', []),
        'students': data['students']
    })


@app.route('/api/constraints', methods=['POST'])
def add_constraint():
    """Add constraint"""
    try:
        payload = request.get_json()
        student_a = payload.get('studentA', '').strip()
        student_b = payload.get('studentB', '').strip()
        constraint_type = payload.get('type')  # 'avoid' or 'together'
        
        # Validate
        if constraint_type not in ['avoid', 'together']:
            return jsonify({'success': False, 'error': 'Constraint type must be "avoid" or "together"'}), 400
        
        if not student_a or not student_b:
            return jsonify({'success': False, 'error': 'Student names cannot be empty'}), 400
        
        if student_a == student_b:
            return jsonify({'success': False, 'error': 'Cannot set constraint for the same student'}), 400
        
        with data_lock:
            data = load_data()
            students = data['students']
            constraints = data.get('constraints', [])
            
            # Validate student exists
            if student_a not in students:
                return jsonify({'success': False, 'error': f'Student "{student_a}" not in list'}), 400
            if student_b not in students:
                return jsonify({'success': False, 'error': f'Student "{student_b}" not in list'}), 400
            
            # Check if same constraint exists
            for c in constraints:
                if ((c['studentA'] == student_a and c['studentB'] == student_b) or
                    (c['studentA'] == student_b and c['studentB'] == student_a)):
                    if c['type'] == constraint_type:
                        return jsonify({'success': False, 'error': 'Constraint already exists'}), 400
            
            # Check conflicting constraint
            for c in constraints:
                if ((c['studentA'] == student_a and c['studentB'] == student_b) or
                    (c['studentA'] == student_b and c['studentB'] == student_a)):
                    if c['type'] != constraint_type:
                        constraint_name = 'avoid' if c['type'] == 'avoid' else 'together'
                        return jsonify({
                            'success': False, 
                            'error': f'Conflicting constraint exists: {student_a} and {student_b} ({constraint_name})'
                        }), 400
            
            # Add constraint
            new_constraint = {
                'studentA': student_a,
                'studentB': student_b,
                'type': constraint_type
            }
            constraints.append(new_constraint)
            data['constraints'] = constraints
            save_data(data)
        
        return jsonify({
            'success': True,
            'constraints': constraints,
            'students': students
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400


@app.route('/api/constraints', methods=['DELETE'])
def delete_constraint():
    """Delete constraint"""
    try:
        payload = request.get_json()
        student_a = payload.get('studentA', '').strip()
        student_b = payload.get('studentB', '').strip()
        constraint_type = payload.get('type')
        
        with data_lock:
            data = load_data()
            constraints = data.get('constraints', [])
            
            # Find and delete constraint
            original_len = len(constraints)
            constraints = [
                c for c in constraints
                if not (
                    c['studentA'] == student_a and 
                    c['studentB'] == student_b and 
                    c['type'] == constraint_type
                ) and not (
                    c['studentA'] == student_b and 
                    c['studentB'] == student_a and 
                    c['type'] == constraint_type
                )
            ]
            
            if len(constraints) == original_len:
                return jsonify({'success': False, 'error': 'Constraint not found'}), 404
            
            data['constraints'] = constraints
            save_data(data)
        
        return jsonify({
            'success': True,
            'constraints': constraints,
            'students': data['students']
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400


# ==================== Rotation API ====================

@app.route('/api/row_swap', methods=['POST'])
def row_swap():
    """Front-back row swap"""
    with data_lock:
        data = load_data()
        rows, cols = data['rows'], data['cols']
        seats = copy.deepcopy(data['seats'])
        constraints = data.get('constraints', [])
        layout_mode = data.get('layout_mode', 'single')
        
        # Front-back swap
        for i in range(rows // 2):
            j = rows - 1 - i
            seats[i], seats[j] = seats[j], seats[i]
        
        # Check constraints
        violations = count_violations(seats, rows, cols, constraints, layout_mode)
        
        data['seats'] = seats
        save_data(data)
    
    response = {
        'success': True,
        'seats': seats,
        'rows': rows,
        'cols': cols,
        'students': data['students'],
        'constraints': constraints
    }
    
    if violations:
        response['warning'] = f'{len(violations)} constraints violated after swap'
    
    return jsonify(response)


@app.route('/api/group_rotate', methods=['POST'])
def group_rotate():
    """Group rotation"""
    try:
        payload = request.get_json()
        group_by = payload.get('groupBy', 'col')  # 'col' or 'row'
        group_size = int(payload.get('groupSize', 2))
        direction = payload.get('direction', 'right')  # 'right' or 'left'
        
        with data_lock:
            data = load_data()
            rows, cols = data['rows'], data['cols']
            seats = copy.deepcopy(data['seats'])
            constraints = data.get('constraints', [])
            layout_mode = data.get('layout_mode', 'single')
            
            if group_by == 'col':
                # Group by columns
                if cols % group_size != 0:
                    return jsonify({
                        'success': False, 
                        'error': f'Columns ({cols}) cannot be divided by group size ({group_size})'
                    }), 400
                
                num_groups = cols // group_size
                groups = []
                for g in range(num_groups):
                    start_col = g * group_size
                    end_col = start_col + group_size
                    group = []
                    for r in range(rows):
                        row_data = []
                        for c in range(start_col, end_col):
                            row_data.append(seats[r][c])
                        group.append(row_data)
                    groups.append(group)
                
                # Rotate
                if direction == 'right':
                    groups = [groups[-1]] + groups[:-1]
                else:
                    groups = groups[1:] + [groups[:1]]
                
                # Refill
                for g, group in enumerate(groups):
                    start_col = g * group_size
                    for r in range(rows):
                        for c_offset, val in enumerate(group[r]):
                            seats[r][start_col + c_offset] = val
            
            else:  # group_by == 'row'
                # Group by rows
                if rows % group_size != 0:
                    return jsonify({
                        'success': False, 
                        'error': f'Rows ({rows}) cannot be divided by group size ({group_size})'
                    }), 400
                
                num_groups = rows // group_size
                groups = []
                for g in range(num_groups):
                    start_row = g * group_size
                    end_row = start_row + group_size
                    group = []
                    for r in range(start_row, end_row):
                        group.append(seats[r][:])
                    groups.append(group)
                
                # Rotate
                if direction == 'right':
                    groups = [groups[-1]] + groups[:-1]
                else:
                    groups = groups[1:] + [groups[:1]]
                
                # Refill
                for g, group in enumerate(groups):
                    start_row = g * group_size
                    for r_offset, row_data in enumerate(group):
                        seats[start_row + r_offset] = row_data[:]
            
            # Check constraints
            violations = count_violations(seats, rows, cols, constraints, layout_mode)
            
            data['seats'] = seats
            save_data(data)
        
        response = {
            'success': True,
            'seats': seats,
            'rows': rows,
            'cols': cols,
            'students': data['students'],
            'constraints': constraints
        }
        
        if violations:
            response['warning'] = f'{len(violations)} constraints violated after rotation'
        
        return jsonify(response)
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400


# ==================== History API ====================

@app.route('/api/history', methods=['GET'])
def get_history():
    """Get history list"""
    with data_lock:
        history = load_history()
    
    # Only return summary, not full seat data
    summaries = []
    for record in history:
        summaries.append({
            'id': record['id'],
            'timestamp': record['timestamp'],
            'action': record['action'],
            'rows': record['rows'],
            'cols': record['cols'],
            'student_count': len(record['students']),
            'constraint_count': len(record['constraints'])
        })
    
    return jsonify({
        'success': True,
        'history': summaries,
        'total': len(summaries)
    })


@app.route('/api/history/<record_id>', methods=['GET'])
def get_history_detail(record_id):
    """Get history detail"""
    with data_lock:
        history = load_history()
    
    for record in history:
        if record['id'] == record_id:
            return jsonify({
                'success': True,
                'record': record
            })
    
    return jsonify({'success': False, 'error': 'Record not found'}), 404


@app.route('/api/history/<record_id>', methods=['DELETE'])
def delete_history(record_id):
    """Delete history record"""
    with data_lock:
        history = load_history()
        original_len = len(history)
        history = [r for r in history if r['id'] != record_id]
        
        if len(history) == original_len:
            return jsonify({'success': False, 'error': 'Record not found'}), 404
        
        save_history(history)
    
    return jsonify({
        'success': True,
        'message': 'History record deleted'
    })


@app.route('/api/history/<record_id>/restore', methods=['POST'])
def restore_history(record_id):
    """Restore seats from history"""
    with data_lock:
        history = load_history()
        
        for record in history:
            if record['id'] == record_id:
                data = load_data()
                data['rows'] = record['rows']
                data['cols'] = record['cols']
                data['seats'] = copy.deepcopy(record['seats'])
                data['students'] = copy.deepcopy(record['students'])
                data['constraints'] = copy.deepcopy(record['constraints'])
                # Restore layout mode and desk pairs
                data['layout_mode'] = record.get('layout_mode', 'single')
                data['desk_pairs'] = copy.deepcopy(record.get('desk_pairs', []))
                save_data(data)
                
                return jsonify({
                    'success': True,
                    'rows': data['rows'],
                    'cols': data['cols'],
                    'seats': data['seats'],
                    'students': data['students'],
                    'constraints': data['constraints'],
                    'layout_mode': data['layout_mode'],
                    'desk_pairs': data['desk_pairs']
                })
        
        return jsonify({'success': False, 'error': 'Record not found'}), 404


# ==================== Student Tags API ====================

@app.route('/api/tags/types', methods=['GET'])
def get_tag_types():
    """Get all tag type definitions"""
    return jsonify({
        'success': True,
        'tag_types': STUDENT_TAG_TYPES
    })


@app.route('/api/students/<student_name>/tags', methods=['GET'])
def get_student_tags(student_name):
    """Get student tags"""
    with data_lock:
        data = load_data()
        tags = data.get('student_tags', {}).get(student_name, {})
    
    return jsonify({
        'success': True,
        'student': student_name,
        'tags': tags
    })


@app.route('/api/students/<student_name>/tags', methods=['POST'])
def set_student_tag(student_name):
    """Set student tag"""
    try:
        payload = request.get_json()
        tag_type = payload.get('tag_type')
        tag_value = payload.get('value')
        
        if not tag_type or not tag_value:
            return jsonify({'success': False, 'error': 'Missing tag_type or value'}), 400
        
        if tag_type not in STUDENT_TAG_TYPES:
            return jsonify({'success': False, 'error': 'Invalid tag type'}), 400
        
        if tag_value not in STUDENT_TAG_TYPES[tag_type]['options']:
            return jsonify({'success': False, 'error': 'Invalid tag value'}), 400
        
        with data_lock:
            data = load_data()
            
            if student_name not in data['students']:
                return jsonify({'success': False, 'error': 'Student not found'}), 404
            
            if 'student_tags' not in data:
                data['student_tags'] = {}
            
            if student_name not in data['student_tags']:
                data['student_tags'][student_name] = {}
            
            data['student_tags'][student_name][tag_type] = tag_value
            save_data(data)
        
        return jsonify({
            'success': True,
            'student': student_name,
            'tags': data['student_tags'][student_name]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400


@app.route('/api/students/<student_name>/tags/<tag_type>', methods=['DELETE'])
def delete_student_tag(student_name, tag_type):
    """Delete student tag"""
    with data_lock:
        data = load_data()
        
        if student_name in data.get('student_tags', {}):
            if tag_type in data['student_tags'][student_name]:
                del data['student_tags'][student_name][tag_type]
                save_data(data)
    
    return jsonify({
        'success': True,
        'message': 'Tag deleted'
    })


@app.route('/api/students/tags', methods=['GET'])
def get_all_student_tags():
    """Get all student tags"""
    with data_lock:
        data = load_data()
        tags = data.get('student_tags', {})
    
    return jsonify({
        'success': True,
        'student_tags': tags
    })


# ==================== Templates API ====================

@app.route('/api/templates', methods=['GET'])
def get_templates():
    """Get all seat templates"""
    return jsonify({
        'success': True,
        'templates': SEAT_TEMPLATES
    })


@app.route('/api/templates/<template_id>', methods=['GET'])
def get_template(template_id):
    """Get single template detail"""
    if template_id not in SEAT_TEMPLATES:
        return jsonify({'success': False, 'error': 'Template not found'}), 404
    
    return jsonify({
        'success': True,
        'template': SEAT_TEMPLATES[template_id]
    })


@app.route('/api/templates/<template_id>/apply', methods=['POST'])
def apply_template(template_id):
    """Apply seat template"""
    if template_id not in SEAT_TEMPLATES:
        return jsonify({'success': False, 'error': 'Template not found'}), 404
    
    template = SEAT_TEMPLATES[template_id]
    
    with data_lock:
        data = load_data()
        
        # Update row/col config
        new_rows = template.get('default_rows', DEFAULT_ROWS)
        new_cols = template.get('default_cols', DEFAULT_COLS)
        
        data['rows'] = new_rows
        data['cols'] = new_cols
        data['seats'] = [[None for _ in range(new_cols)] for _ in range(new_rows)]
        data['current_template'] = template_id
        
        save_data(data)
    
    return jsonify({
        'success': True,
        'rows': new_rows,
        'cols': new_cols,
        'seats': data['seats'],
        'students': data['students'],
        'constraints': data.get('constraints', []),
        'current_template': template_id,
        'template': template
    })


# ==================== Smart Randomize ====================

@app.route('/api/smart_randomize', methods=['POST'])
def smart_randomize_seats():
    """Smart randomize seats considering student tags"""
    with data_lock:
        data = load_data()
        students = data['students'].copy()
        student_tags = data.get('student_tags', {})
        rows = data['rows']
        cols = data['cols']
        constraints = data.get('constraints', [])
        layout_mode = data.get('layout_mode', 'single')
        total_seats = rows * cols
        
        if len(students) > total_seats:
            return jsonify({
                'success': False, 
                'error': f'Students ({len(students)}) exceed total seats ({total_seats})'
            }), 400
        
        if len(students) == 0:
            return jsonify({
                'success': False,
                'error': 'Student list is empty'
            }), 400
        
        # Sort students by tags
        # 1. Students needing front row (vision, special needs)
        # 2. Other students random
        
        front_row_students = []
        other_students = []
        
        for student in students:
            tags = student_tags.get(student, {})
            needs_front = (
                tags.get('vision') == 'strong_nearsighted' or
                tags.get('special') == 'front_row' or
                tags.get('vision') == 'nearsighted'
            )
            
            if needs_front:
                front_row_students.append(student)
            else:
                other_students.append(student)
        
        # Shuffle each group
        random.shuffle(front_row_students)
        random.shuffle(other_students)
        
        # Combine: front row students first
        ordered_students = front_row_students + other_students
        
        # Create new seat matrix
        new_seats = [[None for _ in range(cols)] for _ in range(rows)]
        
        # In double/custom mode, prioritize together constraints as deskmates
        placed_students = set()
        if layout_mode in ['double', 'custom'] and constraints:
            together_constraints = [c for c in constraints if c['type'] == 'together']
            
            if together_constraints:
                # First fill seats
                idx = 0
                for i in range(rows):
                    for j in range(cols):
                        if idx < len(ordered_students):
                            new_seats[i][j] = ordered_students[idx]
                            idx += 1
                
                # Place together students as deskmates
                new_seats, placed_students = place_deskmates_together(
                    new_seats, rows, cols, together_constraints
                )
        
        # Fill remaining seats
        remaining_students = [s for s in ordered_students if s not in placed_students]
        if remaining_students or not placed_students:
            idx = 0
            for i in range(rows):
                for j in range(cols):
                    if new_seats[i][j] is None and idx < len(remaining_students if placed_students else ordered_students):
                        new_seats[i][j] = remaining_students[idx] if placed_students else ordered_students[idx]
                        idx += 1
        
        # Optimize with constraints
        violations = []
        if constraints:
            new_seats, violations = optimize_with_constraints(
                new_seats, rows, cols, constraints, layout_mode
            )
        
        # Add to history
        add_to_history(new_seats, rows, cols, data['students'], constraints, 'smart_randomize', layout_mode, data.get('desk_pairs', []))
        
        data['seats'] = new_seats
        save_data(data)
    
    response = {
        'success': True,
        'seats': new_seats,
        'rows': rows,
        'cols': cols,
        'students': data['students'],
        'constraints': constraints,
        'front_row_count': len(front_row_students)
    }
    
    if violations:
        response['warning'] = f'Some constraints cannot be satisfied ({len(violations)})'
        response['violations'] = [
            {'studentA': v['studentA'], 'studentB': v['studentB'], 'type': v['type']}
            for v in violations
        ]
    
    return jsonify(response)


# ==================== Desk Pairs API ====================

@app.route('/api/desk_pairs', methods=['GET'])
def get_desk_pairs():
    """Get all desk pairs and layout mode"""
    with data_lock:
        data = load_data()
    return jsonify({
        'success': True,
        'desk_pairs': data.get('desk_pairs', []),
        'layout_mode': data.get('layout_mode', 'single')
    })


@app.route('/api/desk_pairs/layout_mode', methods=['POST'])
def set_layout_mode():
    """Set layout mode (single, double, custom)"""
    with data_lock:
        data = load_data()
        layout_mode = request.json.get('layout_mode', 'single')
        
        if layout_mode not in ['single', 'double', 'custom']:
            return jsonify({'success': False, 'error': 'Invalid layout mode'}), 400
        
        data['layout_mode'] = layout_mode
        
        # Auto-generate desk pairs for double mode
        if layout_mode == 'double':
            rows = data['rows']
            cols = data['cols']
            desk_pairs = []
            
            # Create pairs: seats 0-1, 2-3, etc. (with aisle in middle if even cols)
            for i in range(rows):
                for j in range(0, cols - 1, 2):
                    # Skip if this would cross the aisle (for even number of columns)
                    if cols % 2 == 0 and j == cols // 2 - 1:
                        continue
                    desk_pairs.append([[i, j], [i, j + 1]])
            
            data['desk_pairs'] = desk_pairs
        elif layout_mode == 'single':
            data['desk_pairs'] = []
        # custom mode keeps existing pairs
        
        save_data(data)
    
    return jsonify({
        'success': True,
        'layout_mode': data['layout_mode'],
        'desk_pairs': data['desk_pairs']
    })


@app.route('/api/desk_pairs', methods=['POST'])
def add_desk_pair():
    """Add a desk pair (two seats together)"""
    with data_lock:
        data = load_data()
        seat1 = request.json.get('seat1')  # [row, col]
        seat2 = request.json.get('seat2')  # [row, col]
        
        if not seat1 or not seat2:
            return jsonify({'success': False, 'error': 'Both seats required'}), 400
        
        # Check if either seat is already paired
        desk_pairs = data.get('desk_pairs', [])
        for pair in desk_pairs:
            if seat1 in pair or seat2 in pair:
                return jsonify({'success': False, 'error': 'One or both seats already paired'}), 400
        
        desk_pairs.append([seat1, seat2])
        data['desk_pairs'] = desk_pairs
        data['layout_mode'] = 'custom'
        save_data(data)
    
    return jsonify({
        'success': True,
        'desk_pairs': desk_pairs,
        'layout_mode': 'custom'
    })


@app.route('/api/desk_pairs/<int:pair_index>', methods=['DELETE'])
def delete_desk_pair(pair_index):
    """Remove a desk pair"""
    with data_lock:
        data = load_data()
        desk_pairs = data.get('desk_pairs', [])
        
        if pair_index < 0 or pair_index >= len(desk_pairs):
            return jsonify({'success': False, 'error': 'Invalid pair index'}), 400
        
        desk_pairs.pop(pair_index)
        data['desk_pairs'] = desk_pairs
        save_data(data)
    
    return jsonify({
        'success': True,
        'desk_pairs': desk_pairs
    })


@app.route('/api/desk_pairs/toggle', methods=['POST'])
def toggle_desk_pair():
    """Toggle a seat's pair status (add/remove from pairs)"""
    with data_lock:
        data = load_data()
        seat = request.json.get('seat')  # [row, col]
        
        if not seat:
            return jsonify({'success': False, 'error': 'Seat required'}), 400
        
        desk_pairs = data.get('desk_pairs', [])
        found_index = -1
        partner = None
        
        # Find if seat is in a pair
        for i, pair in enumerate(desk_pairs):
            if seat in pair:
                found_index = i
                partner = pair[0] if pair[1] == seat else pair[1]
                break
        
        if found_index >= 0:
            # Remove the pair
            desk_pairs.pop(found_index)
            action = 'removed'
        else:
            # Try to find adjacent seat to pair with
            row, col = seat
            adjacent_seats = [
                [row, col - 1],  # left
                [row, col + 1],  # right
            ]
            
            # Find first unpaired adjacent seat
            for adj in adjacent_seats:
                if 0 <= adj[1] < data['cols']:
                    is_paired = any(adj in p for p in desk_pairs)
                    if not is_paired:
                        desk_pairs.append([seat, adj])
                        partner = adj
                        action = 'added'
                        break
            else:
                return jsonify({'success': False, 'error': 'No available adjacent seat to pair'}), 400
        
        data['desk_pairs'] = desk_pairs
        if action == 'added':
            data['layout_mode'] = 'custom'
        save_data(data)
    
    return jsonify({
        'success': True,
        'action': action,
        'partner': partner,
        'desk_pairs': desk_pairs,
        'layout_mode': data['layout_mode']
    })


@app.route('/api/seats/drag', methods=['POST'])
def drag_seat():
    """Drag a seat from one position to another"""
    with data_lock:
        data = load_data()
        from_pos = request.json.get('from')  # [row, col]
        to_pos = request.json.get('to')  # [row, col]
        
        if not from_pos or not to_pos:
            return jsonify({'success': False, 'error': 'From and to positions required'}), 400
        
        seats = data['seats']
        rows = data['rows']
        cols = data['cols']
        
        # Validate positions
        if not (0 <= from_pos[0] < rows and 0 <= from_pos[1] < cols and
                0 <= to_pos[0] < rows and 0 <= to_pos[1] < cols):
            return jsonify({'success': False, 'error': 'Invalid position'}), 400
        
        # Swap the students
        from_r, from_c = from_pos
        to_r, to_c = to_pos
        
        temp = seats[from_r][from_c]
        seats[from_r][from_c] = seats[to_r][to_c]
        seats[to_r][to_c] = temp
        
        # Update desk pairs if needed
        desk_pairs = data.get('desk_pairs', [])
        for pair in desk_pairs:
            if pair[0] == [from_r, from_c]:
                pair[0] = [to_r, to_c]
            elif pair[1] == [from_r, from_c]:
                pair[1] = [to_r, to_c]
        
        data['seats'] = seats
        data['desk_pairs'] = desk_pairs
        save_data(data)
    
    return jsonify({
        'success': True,
        'seats': seats,
        'desk_pairs': desk_pairs
    })


@app.route('/api/seats/move', methods=['POST'])
def move_seat():
    """Move a student from one seat to another (swap or place)"""
    with data_lock:
        data = load_data()
        from_pos = request.json.get('from')  # [row, col]
        to_pos = request.json.get('to')  # [row, col]
        
        if not from_pos or not to_pos:
            return jsonify({'success': False, 'error': 'From and to positions required'}), 400
        
        seats = data['seats']
        rows = data['rows']
        cols = data['cols']
        
        from_r, from_c = from_pos
        to_r, to_c = to_pos
        
        # Swap students
        seats[from_r][from_c], seats[to_r][to_c] = seats[to_r][to_c], seats[from_r][from_c]
        
        data['seats'] = seats
        save_data(data)
    
    return jsonify({
        'success': True,
        'seats': seats
    })


if __name__ == '__main__':
    import os
    
    print("=" * 50)
    print("PyRanSeat - Classroom Seating Arrangement Tool")
    print("=" * 50)
    print(f"Server: http://127.0.0.1:5000")
    print(f"Data file: {DATA_FILE}")
    print(f"History file: {HISTORY_FILE}")
    print("=" * 50)
    
    # Use waitress for production, Flask dev server for development
    debug_mode = os.environ.get('FLASK_DEBUG', '').lower() in ('1', 'true', 'yes')
    
    if debug_mode:
        print("Running in DEBUG mode (Flask development server)")
        app.run(debug=True, host='127.0.0.1', port=5000)
    else:
        from waitress import serve
        print("Running in PRODUCTION mode (Waitress WSGI server)")
        serve(app, host='127.0.0.1', port=5000)