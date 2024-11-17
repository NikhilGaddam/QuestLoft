from flask import Blueprint, jsonify, request
from config.db_config import get_db_connection

quiz_analysis_bp = Blueprint('quiz_analysis_bp', __name__)

@quiz_analysis_bp.route('/users', methods=['GET'])
def get_users():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT DISTINCT userid, first_name, last_name FROM users')
    users = cursor.fetchall()
    conn.close()
    user_list = [{'userid': row[0], 'name': f"{row[1] or ''}{' ' if row[1] and row[2] else ''}{row[2] or ''}"} for row in users]
    return jsonify(user_list)

# API to get test scores for a specific user
@quiz_analysis_bp.route('/users/<int:userid>/testscores', methods=['GET'])
def get_user_testscores(userid):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM testscores WHERE userid = %s', (userid,))
    testscores = cursor.fetchall()
    conn.close()
    testscores_list = []
    for row in testscores:
        testscores_list.append({
            'testid': row[0],
            'userid': row[1],
            'score': row[2],
            'totalquestions': row[3],
            'correctanswers': row[4],
            'incorrectanswers': row[5],
            'areaswelldone': row[6],
            'areastoimprove': row[7],
            'testdate': row[8]
        })
    return jsonify(testscores_list)

# API for Bar Chart: Number of Correct vs Incorrect Answers
@quiz_analysis_bp.route('/users/<int:userid>/correct_incorrect_totals', methods=['GET'])
def get_correct_incorrect_totals(userid):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT SUM(correctanswers), SUM(incorrectanswers)
        FROM testscores
        WHERE userid = %s
    ''', (userid,))
    result = cursor.fetchone()
    conn.close()
    correct_total = result[0] if result[0] else 0
    incorrect_total = result[1] if result[1] else 0
    return jsonify({'correct': correct_total, 'incorrect': incorrect_total})

# API for Stacked Bar Chart: Performance per Test
@quiz_analysis_bp.route('/users/<int:userid>/performance_per_test', methods=['GET'])
def get_performance_per_test(userid):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT testid, correctanswers, incorrectanswers
        FROM testscores
        WHERE userid = %s
        ORDER BY testdate ASC
    ''', (userid,))
    results = cursor.fetchall()
    conn.close()
    performance_list = []
    for row in results:
        performance_list.append({
            'testid': row[0],
            'correctanswers': row[1],
            'incorrectanswers': row[2]
        })
    return jsonify(performance_list)

# API for Time-Series Line Chart: Correct vs Incorrect Answers over time
@quiz_analysis_bp.route('/users/<int:userid>/correct_incorrect_over_time', methods=['GET'])
def get_correct_incorrect_over_time(userid):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT testdate, correctanswers, incorrectanswers
        FROM testscores
        WHERE userid = %s
        ORDER BY testdate ASC
    ''', (userid,))
    results = cursor.fetchall()
    conn.close()
    data_list = []
    for row in results:
        data_list.append({
            'testdate': row[0],
            'correctanswers': row[1],
            'incorrectanswers': row[2]
        })
    return jsonify(data_list)

# API for Number of Tests Taken
@quiz_analysis_bp.route('/users/<int:userid>/number_of_tests', methods=['GET'])
def get_number_of_tests(userid):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT COUNT(*)
        FROM testscores
        WHERE userid = %s
    ''', (userid,))
    result = cursor.fetchone()
    conn.close()
    num_tests = result[0] if result[0] else 0
    return jsonify({'number_of_tests': num_tests})

# API for Line Graph: Score based on Date/Time
@quiz_analysis_bp.route('/users/<int:userid>/scores_over_time', methods=['GET'])
def get_scores_over_time(userid):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT testdate, score
        FROM testscores
        WHERE userid = %s
        ORDER BY testdate ASC
    ''', (userid,))
    results = cursor.fetchall()
    conn.close()
    data_list = []
    for row in results:
        data_list.append({
            'testdate': row[0],
            'score': row[1]
        })
    return jsonify(data_list)