from flask import Blueprint, request, jsonify, current_app
import psycopg2
from config.db_config import get_db_connection
from dotenv import load_dotenv, find_dotenv
import logging
from emails.send_email_config import send_email

load_dotenv(find_dotenv())

auth_bp = Blueprint('auth', __name__)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

def is_valid_auth0_id(auth0_user_id):
    return True

admins_email = "nikhil.gaddam@gmail.com"

@auth_bp.route('/auth/requestAdminApproval', methods=['POST'])
def request_admin_approval():
    data = request.json
    current_app.logger.debug(f"Request data: {data}")
    auth0_user_id = data.get('auth0_user_id')
    user_email = data.get('user_email')
    user_metadata = data.get('user_metadata', {})
    first_name = user_metadata.get('first_name')
    last_name = user_metadata.get('last_name')
    user_role = user_metadata.get('role')
    grade = user_metadata.get('grade') if user_role == 'Student' else None
    student_school = user_metadata.get('student_school') if user_role == 'Student' else None
    teacher_school = user_metadata.get('teacher_school') if user_role == 'Teacher' else None
    teacher_expertise = user_metadata.get('teacher_expertise') if user_role == 'Teacher' else None
    child_email = user_metadata.get('child_email') if user_role == 'Parent' else None

    required_fields = [auth0_user_id, user_email, user_role, first_name, last_name]
    if not all(required_fields):
        current_app.logger.error("Missing required fields.")
        return jsonify({'error': 'Missing required fields'}), 400

    if user_role not in ['Teacher', 'Parent', 'Student']:
        current_app.logger.error(f"Invalid user role: {user_role}")
        return jsonify({'error': 'Invalid user role'}), 400

    if not is_valid_auth0_id(auth0_user_id):
        current_app.logger.error(f"Invalid auth0_user_id format: {auth0_user_id}")
        return jsonify({'error': 'Invalid auth0_user_id format'}), 400

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute("SELECT auth0_user_id FROM users WHERE auth0_user_id = %s", (auth0_user_id,))
        if cur.fetchone():
            current_app.logger.info(f"User already exists: {auth0_user_id}")
            return jsonify({'error': 'User Already Exists'}), 409

        is_approved = user_role == 'Student'
        approval_status = "Approved" if is_approved else "Pending Approval"

        cur.execute("""
            INSERT INTO users (
                auth0_user_id, first_name, last_name, user_role, is_approved, user_created_time
            ) VALUES (%s, %s, %s, %s, %s, NOW()) RETURNING UserID
        """, (auth0_user_id, first_name, last_name, user_role, is_approved))
        user_id = cur.fetchone()[0]
        current_app.logger.debug(f"User added with ID: {user_id}")

        if user_role == 'Student':
            cur.execute("""
                INSERT INTO students (UserID, Grade, School)
                VALUES (%s, %s, %s)
            """, (user_id, grade, student_school))
        elif user_role == 'Teacher':
            cur.execute("""
                INSERT INTO teachers (UserID, School, Expertise)
                VALUES (%s, %s, %s)
            """, (user_id, teacher_school, teacher_expertise))
        elif user_role == 'Parent':
            cur.execute("""
                INSERT INTO parents (UserID, ChildEmail)
                VALUES (%s, %s)
            """, (user_id, child_email))

        conn.commit()
        current_app.logger.info(f"User data committed for UserID: {user_id}")

        send_email(
            template_id='d-f41f6a5e55064abba59ebe9081d1c0a0',
            to_email=user_email,
            dynamic_data={'user_name': first_name}
        )

        if not is_approved:
            send_email(
                template_id='d-d311b1449ac044e8a41c2840db00ce45',
                to_email=admins_email,
                dynamic_data={'user_name': first_name, 'user_role': user_role}
            )

        return jsonify({'approval': approval_status}), 200

    except psycopg2.IntegrityError as e:
        current_app.logger.error(f"Integrity error: {e}")
        return jsonify({'error': 'Database integrity error'}), 400
    except Exception as e:
        current_app.logger.error(f"Error in requestAdminApproval: {e}")
        return jsonify({'error': 'Internal server error'}), 500
    finally:
        cur.close()
        conn.close()

@auth_bp.route('/auth/updateApproval', methods=['POST'])
def update_approval():
    data = request.json
    auth0_user_id = data.get('auth0_user_id')
    is_approved = data.get('is_approved')
    user_email = data.get('user_email')
    student_id = data.get('student_id') if data.get('user_role') == 'Parent' else None

    if not all([auth0_user_id, is_approved, user_email]):
        current_app.logger.error("Invalid data types.")
        return jsonify({'error': 'Invalid data types'}), 400

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            UPDATE users
            SET is_approved = %s, approved_time = NOW()
            WHERE auth0_user_id = %s
        """, (is_approved, auth0_user_id))

        if cur.rowcount == 0:
            current_app.logger.info(f"User not found or state unchanged: {auth0_user_id}")
            return jsonify({'error': 'User not found or approval state unchanged'}), 404

        if is_approved and data.get('user_role') == 'Parent' and student_id:
            cur.execute("""
                INSERT INTO parents (UserID, StudentUserID)
                SELECT UserID, %s FROM users WHERE auth0_user_id = %s
            """, (student_id, auth0_user_id))

        send_email(
            template_id='d-6f7cc0a01dc84945b6b77fbd8171a2ec' if is_approved else 'd-7106815014014a7aa627d6fef2dbab0d',
            to_email=user_email,
            dynamic_data={'user_name': auth0_user_id}
        )

        conn.commit()
        current_app.logger.info(f"Approval updated successfully for: {auth0_user_id}")
        return jsonify({'message': 'Approval updated successfully'}), 200

    except Exception as e:
        current_app.logger.error(f"Error in updateApproval: {e}")
        return jsonify({'error': 'Internal server error'}), 500
    finally:
        cur.close()
        conn.close()

@auth_bp.route('/auth/validateUser', methods=['GET'])
def validate_user():
    auth0_user_id = request.args.get('auth0_user_id')

    if not auth0_user_id or not isinstance(auth0_user_id, str):
        current_app.logger.error("Invalid data.")
        return jsonify({'error': 'Invalid data'}), 400

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            SELECT is_approved, user_role
            FROM users
            WHERE auth0_user_id = %s
        """, (auth0_user_id,))
        result = cur.fetchone()

        if result is None:
            current_app.logger.info(f"User not found: {auth0_user_id}")
            return jsonify({'error': 'User not found'}), 404

        is_approved, user_role = result
        if user_role == 'Student':
            return jsonify({'is_approved': True}), 200

        return jsonify({'is_approved': is_approved}), 200
    except Exception as e:
        current_app.logger.error(f"Error in validateUser: {e}")
        return jsonify({'error': 'Internal server error'}), 500
    finally:
        cur.close()
        conn.close()

@auth_bp.route('/auth/listApprovals', methods=['GET'])
def list_approvals():
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            SELECT 
                u.auth0_user_id, 
                u.first_name, 
                u.last_name, 
                u.user_role, 
                u.user_created_time,
                s.grade, 
                s.school AS student_school,
                t.school AS teacher_school, 
                t.expertise AS teacher_expertise,
                p.childemail
            FROM users u
            LEFT JOIN students s ON u.UserID = s.UserID
            LEFT JOIN teachers t ON u.UserID = t.UserID
            LEFT JOIN parents p ON u.UserID = p.UserID
            WHERE u.is_approved = FALSE
        """)
        pending_approvals = cur.fetchall()

        response = []
        for row in pending_approvals:
            response.append({
                'auth0_user_id': row[0],
                'first_name': row[1],
                'last_name': row[2],
                'user_role': row[3],
                'user_created_time': row[4].isoformat(),
                'grade': row[5],
                'student_school': row[6],
                'teacher_school': row[7],
                'teacher_expertise': row[8],
                'child_email': row[9]
            })

        return jsonify(response), 200
    except Exception as e:
        current_app.logger.error(f"Error in listApprovals: {e}")
        return jsonify({'error': 'Internal server error'}), 500
    finally:
        cur.close()
        conn.close()
