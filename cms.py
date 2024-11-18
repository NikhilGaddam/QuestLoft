from flask import Blueprint, request, jsonify
from flask_cors import CORS
import boto3
import os
from datetime import datetime
import uuid
from config.db_config import get_db_connection

cms = Blueprint('cms', __name__)
# CORS(cms, resources={
#     r"/*": {
#         "origins": ["http://localhost:3000"],
#         "methods": ["GET", "POST", "PUT", "DELETE"],
#         "allow_headers": ["Content-Type"]
#     }
# })

s3_client = boto3.client(
    's3',
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
    region_name=os.getenv('AWS_REGION')
)
BUCKET_NAME = os.getenv('AWS_BUCKET_NAME')

@cms.route('/documents/upload', methods=['POST'])
def upload_document():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        title = request.form.get('title', file.filename)
        description = request.form.get('description')
        tags = request.form.get('tags', '').split(',') if request.form.get('tags') else []
        
        file_content = file.read()
        file_extension = os.path.splitext(file.filename)[1]
        s3_key = f"documents/{str(uuid.uuid4())}{file_extension}"
        
        s3_client.put_object(
            Bucket=BUCKET_NAME,
            Key=s3_key,
            Body=file_content,
            ContentType=file.content_type,
            ServerSideEncryption='AES256'
        )
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            INSERT INTO documents (title, filename, s3_key, size, tags, content_type, description, upload_date)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id, upload_date;
        """, (title, file.filename, s3_key, len(file_content), tags, file.content_type, description, datetime.utcnow()))
        
        document_id, upload_date = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({
            'id': document_id,
            'title': title,
            'filename': file.filename,
            'size': len(file_content),
            'upload_date': upload_date.isoformat(),
            'tags': tags,
            'content_type': file.content_type,
            'description': description
        }), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@cms.route('/documents/<int:document_id>/download-url', methods=['GET'])
def get_download_url(document_id):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("SELECT s3_key FROM documents WHERE id = %s", (document_id,))
        result = cur.fetchone()
        
        if not result:
            return jsonify({'error': 'Document not found'}), 404
            
        s3_key = result[0]
        url = s3_client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': BUCKET_NAME,
                'Key': s3_key
            },
            ExpiresIn=3600
        )
        
        cur.close()
        conn.close()
        return jsonify({'download_url': url})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@cms.route('/documents', methods=['GET'])
def list_documents():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT id, title, filename, size, upload_date, tags, content_type, description 
            FROM documents 
            ORDER BY upload_date DESC
        """)
        
        documents = [{
            'id': doc[0],
            'title': doc[1],
            'filename': doc[2],
            'size': doc[3],
            'upload_date': doc[4].isoformat(),
            'tags': doc[5],
            'content_type': doc[6],
            'description': doc[7]
        } for doc in cur.fetchall()]
        
        cur.close()
        conn.close()
        return jsonify(documents)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@cms.route('/documents/<int:document_id>', methods=['DELETE'])
def delete_document(document_id):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("SELECT s3_key FROM documents WHERE id = %s", (document_id,))
        result = cur.fetchone()
        
        if not result:
            return jsonify({'error': 'Document not found'}), 404
            
        s3_key = result[0]
        
        # Delete from S3
        s3_client.delete_object(
            Bucket=BUCKET_NAME,
            Key=s3_key
        )
        
        # Delete from database
        cur.execute("DELETE FROM documents WHERE id = %s", (document_id,))
        conn.commit()
        
        cur.close()
        conn.close()
        
        return jsonify({'message': 'Document deleted successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500