from flask import Blueprint, request, jsonify
import psycopg2
from psycopg2 import sql
from config import get_db_connection
import re
import logging

# Create a blueprint for authentication routes
auth_bp = Blueprint('auth', __name__)

# Logger setup
logging.basicConfig(level=logging.ERROR)

# Function to validate the format of auth0_user_id
def is_valid_auth0_id(auth0_user_id):
    # pattern = r'^auth0\|[a-zA-Z0-9]+$'
    # return re.match(pattern, auth0_user_id) is not None
    return True

# API to request admin approval
@auth_bp.route('/auth/requestAdminApproval', methods=['POST'])
def request_admin_approval():
    data = request.json
    auth0_user_id = data.get('auth0_user_id')
    user_role = data.get('user_role')  # Either "Teacher", "Parent", or "Student"

    # Validate payload
    if not auth0_user_id or not isinstance(auth0_user_id, str) or not user_role or not isinstance(user_role, str):
        return jsonify({'error': 'Invalid data types'}), 400

    # Validate user_role
    if user_role not in ['Teacher', 'Parent', 'Student']:
        return jsonify({'error': 'Invalid user role'}), 400

    # Validate auth0_user_id format
    if not is_valid_auth0_id(auth0_user_id):
        return jsonify({'error': 'Invalid auth0_user_id format'}), 400

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # Check if the user with the provided auth0_user_id already exists
        cur.execute("SELECT auth0_user_id FROM users WHERE auth0_user_id = %s", (auth0_user_id,))
        user_exists = cur.fetchone()

        if user_exists:
            return jsonify({'error': 'User Already Exists'}), 409  # Conflict status code

        # If the user role is "Student", they are automatically approved
        if user_role == 'Student':
            is_approved = True
            approval_status = "Approved"
        else:
            is_approved = False
            approval_status = "Pending Approval"

        # Insert the user details into the users table
        cur.execute("""
            INSERT INTO users (auth0_user_id, user_role, is_approved, user_created_time)
            VALUES (%s, %s, %s, NOW())
        """, (auth0_user_id, user_role, is_approved))
        conn.commit()

        return jsonify({'approval': approval_status}), 200
    except psycopg2.IntegrityError:
        return jsonify({'error': 'Database integrity error'}), 400
    except Exception as e:
        logging.error(f"Error in requestAdminApproval: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500
    finally:
        cur.close()
        conn.close()

# API to list all pending approvals for admin
@auth_bp.route('/auth/listApprovals', methods=['GET'])
def list_approvals():
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            SELECT auth0_user_id, user_role, user_created_time
            FROM users
            WHERE is_approved = FALSE
        """)
        pending_approvals = cur.fetchall()
        
        # Convert datetime to ISO 8601 for better serialization
        response = [{
            'auth0_user_id': row[0],
            'user_role': row[1],
            'user_created_time': row[2].isoformat()
        } for row in pending_approvals]

        return jsonify(response), 200
    except Exception as e:
        logging.error(f"Error in listApprovals: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500
    finally:
        cur.close()
        conn.close()

# API for admin to approve or reject a user
@auth_bp.route('/auth/updateApproval', methods=['POST'])
def update_approval():
    data = request.json
    auth0_user_id = data.get('auth0_user_id')
    is_approved = data.get('is_approved')  # Boolean: True for approve, False for reject

    # Validate input
    if not auth0_user_id or not isinstance(auth0_user_id, str) or is_approved is None:
        return jsonify({'error': 'Invalid data types'}), 400

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # Update approval status in the database
        cur.execute("""
            UPDATE users
            SET is_approved = %s, approved_time = NOW() WHERE auth0_user_id = %s
        """, (is_approved, auth0_user_id))

        if cur.rowcount == 0:
            return jsonify({'error': 'User not found or approval state unchanged'}), 404

        conn.commit()
        return jsonify({'message': 'Approval updated successfully'}), 200
    except Exception as e:
        logging.error(f"Error in updateApproval: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500
    finally:
        cur.close()
        conn.close()

# API to validate if a user is approved
@auth_bp.route('/auth/validateUser', methods=['GET'])
def validate_user():
    auth0_user_id = request.args.get('auth0_user_id')

    # Validate input
    if not auth0_user_id or not isinstance(auth0_user_id, str):
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
            return jsonify({'error': 'User not found'}), 404

        is_approved, user_role = result

        # Auto-approve students
        if user_role == 'Student':
            return jsonify({'is_approved': True}), 200

        return jsonify({'is_approved': is_approved}), 200
    except Exception as e:
        logging.error(f"Error in validateUser: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500
    finally:
        cur.close()
        conn.close()
