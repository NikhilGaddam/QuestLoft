from flask import Blueprint, request, jsonify
import psycopg2
from psycopg2 import sql
from config import get_db_connection

# Create a blueprint for authentication routes
auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/auth/requestAdminApproval', methods=['POST'])
def request_admin_approval():
    data = request.json
    auth0_user_id = data.get('auth0_user_id')
    user_role = data.get('user_role')  # Either "Teacher" or "Parent"

    if not auth0_user_id or user_role not in ['Teacher', 'Parent']:
        return jsonify({'error': 'Invalid data'}), 400

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            INSERT INTO users (auth0_user_id, user_role, is_approved)
            VALUES (%s, %s, %s)
        """, (auth0_user_id, user_role, False))
        conn.commit()
        return jsonify({'message': 'Approval request submitted'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()

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
        response = [{'auth0_user_id': row[0], 'user_role': row[1], 'user_created_time':row[2]} for row in pending_approvals]
        return jsonify(response), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()

@auth_bp.route('/auth/updateApproval', methods=['POST'])
def update_approval():
    data = request.json
    auth0_user_id = data.get('auth0_user_id')
    is_approved = data.get('is_approved')  # Boolean: True for approve, False for reject

    if not auth0_user_id or is_approved is None:
        return jsonify({'error': 'Invalid data'}), 400

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            UPDATE users
            SET is_approved = %s
            WHERE auth0_user_id = %s
        """, (is_approved, auth0_user_id))
        conn.commit()

        return jsonify({'message': 'Approval updated successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()

@auth_bp.route('/auth/validateUser', methods=['GET'])
def validate_user():
    auth0_user_id = request.args.get('auth0_user_id')

    if not auth0_user_id:
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
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()
