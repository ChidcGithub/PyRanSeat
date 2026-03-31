"""
PyRanSeat - 教室座位编排工具
Flask 后端服务
支持：约束排座、前后排轮换、大组轮换
"""

import os
import json
import random
import threading
import copy
from flask import Flask, render_template, jsonify, request

app = Flask(__name__)

# 数据文件路径
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
DATA_FILE = os.path.join(DATA_DIR, 'seat_data.json')

# 数据锁，保证线程安全
data_lock = threading.Lock()

# 默认配置
DEFAULT_ROWS = 6
DEFAULT_COLS = 8


def ensure_data_dir():
    """确保数据目录存在"""
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)


def load_data():
    """加载座位数据"""
    ensure_data_dir()
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    # 返回默认数据
    return {
        'rows': DEFAULT_ROWS,
        'cols': DEFAULT_COLS,
        'seats': [[None for _ in range(DEFAULT_COLS)] for _ in range(DEFAULT_ROWS)],
        'students': [],
        'constraints': []
    }


def save_data(data):
    """保存座位数据"""
    ensure_data_dir()
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ==================== 约束算法 ====================

def get_neighbors(rows, cols, r, c):
    """获取指定座位的相邻座位（上下左右）"""
    neighbors = []
    directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]  # 上下左右
    for dr, dc in directions:
        nr, nc = r + dr, c + dc
        if 0 <= nr < rows and 0 <= nc < cols:
            neighbors.append((nr, nc))
    return neighbors


def find_student_position(seats, rows, cols, student_name):
    """查找学生在座位矩阵中的位置"""
    for r in range(rows):
        for c in range(cols):
            if seats[r][c] == student_name:
                return (r, c)
    return None


def check_constraint_satisfied(seats, rows, cols, constraint):
    """检查单个约束是否满足"""
    student_a = constraint['studentA']
    student_b = constraint['studentB']
    constraint_type = constraint['type']
    
    pos_a = find_student_position(seats, rows, cols, student_a)
    pos_b = find_student_position(seats, rows, cols, student_b)
    
    # 如果任一学生不在座位上，视为满足
    if pos_a is None or pos_b is None:
        return True
    
    r_a, c_a = pos_a
    neighbors = get_neighbors(rows, cols, r_a, c_a)
    
    is_adjacent = pos_b in neighbors
    
    if constraint_type == 'avoid':
        # 规避：不能相邻
        return not is_adjacent
    elif constraint_type == 'together':
        # 坐一起：必须相邻
        return is_adjacent
    
    return True


def count_violations(seats, rows, cols, constraints):
    """统计违反约束的数量"""
    violations = []
    for constraint in constraints:
        if not check_constraint_satisfied(seats, rows, cols, constraint):
            violations.append(constraint)
    return violations


def try_swap_students(seats, rows, cols, pos1, pos2):
    """尝试交换两个座位的学生"""
    r1, c1 = pos1
    r2, c2 = pos2
    seats[r1][c1], seats[r2][c2] = seats[r2][c2], seats[r1][c1]


def optimize_with_constraints(seats, rows, cols, constraints, max_attempts=500):
    """使用局部交换优化座位以满足约束"""
    seats = copy.deepcopy(seats)
    violations = count_violations(seats, rows, cols, constraints)
    
    if not violations:
        return seats, []
    
    # 收集所有有学生的座位位置
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
        # 随机选择一个违反约束的学生
        violation = random.choice(violations)
        
        # 随机选择两个位置尝试交换
        pos1 = find_student_position(seats, rows, cols, violation['studentA'])
        if pos1 is None:
            pos1 = random.choice(occupied_positions)
        
        # 选择另一个位置
        other_positions = [p for p in occupied_positions if p != pos1]
        if not other_positions:
            break
        pos2 = random.choice(other_positions)
        
        # 尝试交换
        try_swap_students(seats, rows, cols, pos1, pos2)
        new_violations = count_violations(seats, rows, cols, constraints)
        
        if len(new_violations) <= len(best_violations):
            # 接受交换
            if len(new_violations) < len(best_violations):
                best_seats = copy.deepcopy(seats)
                best_violations = new_violations
            violations = new_violations
        else:
            # 回退交换
            try_swap_students(seats, rows, cols, pos1, pos2)
        
        attempt += 1
    
    return best_seats, best_violations


def check_swap_violation(seats, rows, cols, constraints, pos1, pos2):
    """检查交换后是否会产生新的约束违反"""
    # 创建临时座位矩阵
    temp_seats = copy.deepcopy(seats)
    try_swap_students(temp_seats, rows, cols, pos1, pos2)
    
    # 检查是否违反约束
    violations = count_violations(temp_seats, rows, cols, constraints)
    return violations


def clean_constraints_for_students(constraints, students):
    """清理涉及已删除学生的约束"""
    student_set = set(students)
    return [
        c for c in constraints 
        if c['studentA'] in student_set and c['studentB'] in student_set
    ]


# ==================== 路由 ====================

@app.route('/')
def index():
    """主页"""
    return render_template('index.html')


@app.route('/api/seats', methods=['GET'])
def get_seats():
    """获取当前座位矩阵、行列数、学生列表、约束列表"""
    with data_lock:
        data = load_data()
    return jsonify({
        'success': True,
        'rows': data['rows'],
        'cols': data['cols'],
        'seats': data['seats'],
        'students': data['students'],
        'constraints': data.get('constraints', [])
    })


@app.route('/api/config', methods=['POST'])
def update_config():
    """修改行列数，重置空白座位矩阵"""
    try:
        payload = request.get_json()
        new_rows = int(payload.get('rows', DEFAULT_ROWS))
        new_cols = int(payload.get('cols', DEFAULT_COLS))
        
        # 验证范围
        if new_rows < 1 or new_rows > 20 or new_cols < 1 or new_cols > 20:
            return jsonify({'success': False, 'error': 'Rows and columns must be between 1-20'}), 400
        
        with data_lock:
            data = load_data()
            data['rows'] = new_rows
            data['cols'] = new_cols
            # 重置为空白座位矩阵
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
    """更新学生名单"""
    try:
        payload = request.get_json()
        students = payload.get('students', [])
        
        # 验证学生列表
        if not isinstance(students, list):
            return jsonify({'success': False, 'error': 'Student list must be an array'}), 400
        
        # 过滤空字符串
        students = [s.strip() for s in students if s and s.strip()]
        
        with data_lock:
            data = load_data()
            data['students'] = students
            # 清理涉及已删除学生的约束
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
    """随机排座（支持约束优化）"""
    with data_lock:
        data = load_data()
        students = data['students'].copy()
        rows = data['rows']
        cols = data['cols']
        constraints = data.get('constraints', [])
        total_seats = rows * cols
        
        # 检查学生数量
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
        
        # 随机打乱学生顺序
        random.shuffle(students)
        
        # 创建新的座位矩阵
        new_seats = [[None for _ in range(cols)] for _ in range(rows)]
        
        # 按行优先填充座位
        idx = 0
        for i in range(rows):
            for j in range(cols):
                if idx < len(students):
                    new_seats[i][j] = students[idx]
                    idx += 1
        
        # 如果有约束，进行优化
        violations = []
        if constraints:
            new_seats, violations = optimize_with_constraints(
                new_seats, rows, cols, constraints
            )
        
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
        response['warning'] = f'部分约束无法满足 ({len(violations)} 条)'
        response['violations'] = [
            {'studentA': v['studentA'], 'studentB': v['studentB'], 'type': v['type']}
            for v in violations
        ]
    
    return jsonify(response)


@app.route('/api/swap', methods=['POST'])
def swap_seats():
    """交换两个座位的学生"""
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
            
            # 验证坐标有效性
            if not (0 <= r1 < rows and 0 <= c1 < cols and 0 <= r2 < rows and 0 <= c2 < cols):
                return jsonify({'success': False, 'error': 'Seat coordinates out of range'}), 400
            
            # 不允许交换同一个座位
            if r1 == r2 and c1 == c2:
                return jsonify({'success': False, 'error': 'Cannot swap the same seat'}), 400
            
            # 检查约束
            violations = check_swap_violation(seats, rows, cols, constraints, (r1, c1), (r2, c2))
            if violations:
                violation_info = ', '.join([
                    f"{v['studentA']} and {v['studentB']}" for v in violations[:3]
                ])
                return jsonify({
                    'success': False, 
                    'error': f'Constraint violation after swap: {violation_info}'
                }), 400
            
            # 执行交换
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
    """重置座位（清空所有学生）"""
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


# ==================== 约束管理 API ====================

@app.route('/api/constraints', methods=['GET'])
def get_constraints():
    """获取约束列表"""
    with data_lock:
        data = load_data()
    return jsonify({
        'success': True,
        'constraints': data.get('constraints', []),
        'students': data['students']
    })


@app.route('/api/constraints', methods=['POST'])
def add_constraint():
    """添加约束"""
    try:
        payload = request.get_json()
        student_a = payload.get('studentA', '').strip()
        student_b = payload.get('studentB', '').strip()
        constraint_type = payload.get('type')  # 'avoid' or 'together'
        
        # 验证
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
            
            # 验证学生存在
            if student_a not in students:
                return jsonify({'success': False, 'error': f'Student "{student_a}" not in list'}), 400
            if student_b not in students:
                return jsonify({'success': False, 'error': f'Student "{student_b}" not in list'}), 400
            
            # 检查是否已存在相同约束
            for c in constraints:
                if ((c['studentA'] == student_a and c['studentB'] == student_b) or
                    (c['studentA'] == student_b and c['studentB'] == student_a)):
                    if c['type'] == constraint_type:
                        return jsonify({'success': False, 'error': 'Constraint already exists'}), 400
            
            # 检查冲突约束
            for c in constraints:
                if ((c['studentA'] == student_a and c['studentB'] == student_b) or
                    (c['studentA'] == student_b and c['studentB'] == student_a)):
                    if c['type'] != constraint_type:
                        constraint_name = 'avoid' if c['type'] == 'avoid' else 'together'
                        return jsonify({
                            'success': False, 
                            'error': f'Conflicting constraint exists: {student_a} and {student_b} ({constraint_name})'
                        }), 400
            
            # 添加约束
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
    """删除约束"""
    try:
        payload = request.get_json()
        student_a = payload.get('studentA', '').strip()
        student_b = payload.get('studentB', '').strip()
        constraint_type = payload.get('type')
        
        with data_lock:
            data = load_data()
            constraints = data.get('constraints', [])
            
            # 查找并删除约束
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


# ==================== 轮换 API ====================

@app.route('/api/row_swap', methods=['POST'])
def row_swap():
    """前后排轮换"""
    with data_lock:
        data = load_data()
        rows, cols = data['rows'], data['cols']
        seats = copy.deepcopy(data['seats'])
        constraints = data.get('constraints', [])
        
        # 前后排轮换
        for i in range(rows // 2):
            j = rows - 1 - i
            seats[i], seats[j] = seats[j], seats[i]
        
        # 检查约束
        violations = count_violations(seats, rows, cols, constraints)
        
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
        response['warning'] = f'轮换后有 {len(violations)} 条约束被违反'
    
    return jsonify(response)


@app.route('/api/group_rotate', methods=['POST'])
def group_rotate():
    """大组轮换"""
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
            
            if group_by == 'col':
                # 按列分组
                if cols % group_size != 0:
                    return jsonify({
                        'success': False, 
                        'error': f'列数({cols})不能被组大小({group_size})整除'
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
                
                # 轮换
                if direction == 'right':
                    groups = [groups[-1]] + groups[:-1]
                else:
                    groups = groups[1:] + [groups[:1]]
                
                # 重新填充
                for g, group in enumerate(groups):
                    start_col = g * group_size
                    for r in range(rows):
                        for c_offset, val in enumerate(group[r]):
                            seats[r][start_col + c_offset] = val
            
            else:  # group_by == 'row'
                # 按行分组
                if rows % group_size != 0:
                    return jsonify({
                        'success': False, 
                        'error': f'行数({rows})不能被组大小({group_size})整除'
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
                
                # 轮换
                if direction == 'right':
                    groups = [groups[-1]] + groups[:-1]
                else:
                    groups = groups[1:] + [groups[:1]]
                
                # 重新填充
                for g, group in enumerate(groups):
                    start_row = g * group_size
                    for r_offset, row_data in enumerate(group):
                        seats[start_row + r_offset] = row_data[:]
            
            # 检查约束
            violations = count_violations(seats, rows, cols, constraints)
            
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
            response['warning'] = f'轮换后有 {len(violations)} 条约束被违反'
        
        return jsonify(response)
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400


if __name__ == '__main__':
    print("=" * 50)
    print("PyRanSeat - Classroom Seating Arrangement Tool")
    print("=" * 50)
    print(f"Server: http://127.0.0.1:5000")
    print(f"Data file: {DATA_FILE}")
    print("=" * 50)
    app.run(debug=True, host='127.0.0.1', port=5000)