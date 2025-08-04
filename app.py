from flask import Flask, render_template, request, jsonify, redirect, url_for
import requests
import threading
import time
import sqlite3
import os
from datetime import datetime
import schedule

app = Flask(__name__)

# Database initialization
def init_db():
    conn = sqlite3.connect('batches.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS batches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            batch_name TEXT NOT NULL,
            batch_id TEXT NOT NULL UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

# Initialize database
init_db()

def send_batch_request(batch_id):
    """Send request to the batch URL"""
    try:
        url = f"https://bhanuyadav.xyz/kgprojects/liveplayer/auto/?batch={batch_id}"
        response = requests.get(url, timeout=30)
        print(f"Request sent to batch {batch_id}: Status {response.status_code}")
        return response.status_code
    except Exception as e:
        print(f"Error sending request to batch {batch_id}: {str(e)}")
        return None

def send_all_batch_requests():
    """Send requests to all batches in database"""
    conn = sqlite3.connect('batches.db')
    cursor = conn.cursor()
    cursor.execute('SELECT batch_id FROM batches')
    batches = cursor.fetchall()
    conn.close()
    
    print(f"Sending requests to {len(batches)} batches at {datetime.now()}")
    for batch in batches:
        batch_id = batch[0]
        send_batch_request(batch_id)

def background_scheduler():
    """Background task that runs every 10 minutes"""
    schedule.every(10).minutes.do(send_all_batch_requests)
    
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute

# Start background scheduler
scheduler_thread = threading.Thread(target=background_scheduler, daemon=True)
scheduler_thread.start()

@app.route('/')
def index():
    """Main HTML page"""
    conn = sqlite3.connect('batches.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM batches ORDER BY created_at DESC')
    batches = cursor.fetchall()
    conn.close()
    
    return render_template('index.html', batches=batches)

@app.route('/add_batch', methods=['POST'])
def add_batch():
    """Add a new batch"""
    try:
        batch_name = request.form['batch_name']
        batch_id = request.form['batch_id']
        
        if not batch_name or not batch_id:
            return jsonify({'success': False, 'message': 'Batch name and ID are required'})
        
        conn = sqlite3.connect('batches.db')
        cursor = conn.cursor()
        
        # Check if batch_id already exists
        cursor.execute('SELECT id FROM batches WHERE batch_id = ?', (batch_id,))
        if cursor.fetchone():
            conn.close()
            return jsonify({'success': False, 'message': 'Batch ID already exists'})
        
        cursor.execute('INSERT INTO batches (batch_name, batch_id) VALUES (?, ?)', (batch_name, batch_id))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Batch added successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/delete_batch/<int:batch_id>', methods=['DELETE'])
def delete_batch(batch_id):
    """Delete a batch"""
    try:
        conn = sqlite3.connect('batches.db')
        cursor = conn.cursor()
        cursor.execute('DELETE FROM batches WHERE id = ?', (batch_id,))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Batch deleted successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/test_batch/<batch_id>')
def test_batch(batch_id):
    """Test a specific batch request"""
    status_code = send_batch_request(batch_id)
    if status_code:
        return jsonify({'success': True, 'status_code': status_code})
    else:
        return jsonify({'success': False, 'message': 'Failed to send request'})

@app.route('/health')
def health():
    """Health check endpoint for deployment"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False) 
