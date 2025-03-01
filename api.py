from flask import Flask, jsonify, request
from flask_cors import CORS
import sqlite3
import os
import json
from waitress import serve
# from app import app

app = Flask(__name__)
CORS(app)

# SQLite database initialization
conn = sqlite3.connect('mydata.db', check_same_thread=False)
cursor = conn.cursor()

# Users table
cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL
    )
''')

# Profile table
cursor.execute('''
    CREATE TABLE IF NOT EXISTS profile (
        user_id INTEGER PRIMARY KEY,
        profile_image TEXT,
        address TEXT,
        cart TEXT,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
''')

# Orders table
cursor.execute('''
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        items TEXT NOT NULL,
        address TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
''')

conn.commit()

# User authentication routes
@app.route('/signup', methods=['POST'])
def signup():
    data = request.json
    name = data['name']
    email = data['email']
    password = data['password']

    # Check if email already exists
    cursor.execute('SELECT * FROM users WHERE email=?', (email,))
    existing_user = cursor.fetchone()

    if existing_user:
        return jsonify({'message': 'Email already exists'}), 400

    # Insert new user into database
    cursor.execute('''
        INSERT INTO users (name, email, password) VALUES (?, ?, ?)
    ''', (name, email, password))
    conn.commit()

    # Get the user_id of the newly inserted user
    cursor.execute('SELECT id FROM users WHERE email=?', (email,))
    user_id = cursor.fetchone()[0]

    # Create a profile for the new user
    cursor.execute('''
        INSERT INTO profile (user_id) VALUES (?)
    ''', (user_id,))
    conn.commit()

    return jsonify({'message': 'User signed up successfully'}), 201

@app.route('/signin', methods=['POST'])
def signin():
    data = request.json
    email = data['email']
    password = data['password']

    # Check if email and password match
    cursor.execute('SELECT id FROM users WHERE email=? AND password=?', (email, password))
    user = cursor.fetchone()

    if user:
        user_id = user[0]
        return jsonify({'message': 'Sign in successful', 'user_id': user_id}), 200
    else:
        return jsonify({'message': 'Invalid credentials'}), 401

@app.route('/user/<int:user_id>', methods=['GET'])
def get_user_details(user_id):
    cursor.execute('''
        SELECT u.name, u.email, p.profile_image, p.address, p.cart
        FROM users u
        JOIN profile p ON u.id = p.user_id
        WHERE u.id=?
    ''', (user_id,))
    user = cursor.fetchone()
    if user:
        return jsonify({
            'name': user[0],
            'email': user[1],
            'profile_image': user[2],
            'address': user[3],
            'cart': json.loads(user[4]) if user[4] else []
        })
    else:
        return jsonify({'error': 'User not found'}), 404

@app.route('/user/upload_image/<int:user_id>', methods=['POST'])
def upload_image(user_id):
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if file:
        filename = f'{user_id}_{file.filename}'
        file_path = os.path.join('uploads', filename)
        file.save(file_path)

        cursor.execute('UPDATE profile SET profile_image=? WHERE user_id=?', (filename, user_id))
        conn.commit()

        return jsonify({'message': 'Image uploaded successfully', 'filename': filename}), 200

@app.route('/update_profile/<int:user_id>', methods=['POST'])
def update_profile(user_id):
    data = request.json
    name = data['name']
    address = data['address']

    cursor.execute('UPDATE users SET name=? WHERE id=?', (name, user_id))
    cursor.execute('UPDATE profile SET address=? WHERE user_id=?', (address, user_id))
    conn.commit()

    return jsonify({'message': 'Profile updated successfully'}), 200

@app.route('/verify_email', methods=['POST'])
def verify_email():
    data = request.json
    email = data['email']

    cursor.execute('''
        SELECT u.id, u.name, u.email, p.profile_image, p.address, p.cart
        FROM users u
        JOIN profile p ON u.id = p.user_id
        WHERE u.email=?
    ''', (email,))
    user = cursor.fetchone()

    if user:
        return jsonify({
            'message': 'Email verified successfully',
            'user_id': user[0],
            'name': user[1],
            'email': user[2],
            'profile_image': user[3],
            'address': user[4],
            'cart': json.loads(user[5]) if user[5] else []
        }), 200
    else:
        return jsonify({'message': 'Email not found'}), 404

@app.route('/orders/<int:user_id>', methods=['GET'])
def get_orders(user_id):
    cursor.execute('SELECT id, items, address FROM orders WHERE user_id=?', (user_id,))
    orders = cursor.fetchall()
    orders_list = [{'id': order[0], 'items': json.loads(order[1]), 'address': order[2]} for order in orders]
    return jsonify({'orders': orders_list})

@app.route('/add_order', methods=['POST'])
def add_order():
    data = request.json
    user_id = data['user_id']
    items = json.dumps(data['items'])
    address = data['address']

    cursor.execute('''
        INSERT INTO orders (user_id, items, address) VALUES (?, ?, ?)
    ''', (user_id, items, address))
    conn.commit()

    return jsonify({'message': 'Order added successfully'}), 201

@app.route('/delete_order/<int:order_id>', methods=['DELETE'])
def delete_order(order_id):
    cursor.execute('DELETE FROM orders WHERE id=?', (order_id,))
    conn.commit()
    return jsonify({'message': 'Order deleted successfully'})

if __name__ == '__main__':
    app.run(debug=True)
    port = int(os.environ.get("PORT", 8080))  # Default to 8080 if PORT is not set
    serve(app, host="0.0.0.0", port=port)
    



