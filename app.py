from pymongo import MongoClient
from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import hashlib
import logging
from bson import ObjectId
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key'


app.logger.setLevel(logging.DEBUG)
log_handler = logging.StreamHandler()
log_handler.setLevel(logging.DEBUG)
app.logger.addHandler(log_handler)

client = MongoClient("mongodb://localhost:27017")
db = client['note_app']
collection = db['notes']

# Send a ping to confirm a successful connection
try:
    client.admin.command('ping')
    app.logger.debug("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    app.logger.error(e)

conn = sqlite3.connect('note_app.db')
cursor = conn.cursor()

cursor.execute('''CREATE TABLE IF NOT EXISTS users
                  (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT NOT NULL,
                  email TEXT NOT NULL,
                  password TEXT NOT NULL)''')

conn.commit()
conn.close()

# Routes
@app.route('/')
def welcome():
    return render_template('welcome.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():

    if request.method == 'POST':

        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        conn = sqlite3.connect('note_app.db')
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (username, email, password) VALUES (?, ?, ?)", (username, email, password))
        conn.commit()

        user_id = cursor.lastrowid
        conn.close()

        db['notes'].update_many({'user_email': email}, {'$set': {'user_id': user_id}})

        return redirect(url_for('login'))

    return render_template('signup.html')




@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password'] 

        conn = sqlite3.connect('note_app.db')
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, password FROM users WHERE username=?", (username,))
        user_data = cursor.fetchone()  

        if user_data:
            user_id, stored_username, stored_password = user_data
            if password == stored_password:
                session['user_id'] = user_id
                session['username'] = stored_username
                conn.close()

                return redirect(url_for('notes'))

        flash('Invalid username or password. Please try again.', 'error')

    return render_template('login.html')




@app.route('/notes')
def notes():
    all_notes = list(collection.find())

    return render_template('notes.html', all_notes=all_notes)




@app.route('/add_note', methods=['GET', 'POST'])
def add_note():
    if 'user_id' in session:
        if request.method == 'POST':
            user_id = session['user_id']
            title = request.form['title']
            content = request.form['content']

            created_at = datetime.utcnow()
            note_data = {
                'user_id': user_id,
                'title': title,
                'content': content,
                'created_at': created_at  
            }
            result = collection.insert_one(note_data)

            flash('Note created successfully!', 'success')
            return redirect(url_for('notes'))

        return render_template('add_note.html')
    else:
        return redirect(url_for('login'))



@app.route('/notes/<note_id>')
def view_note(note_id):
    note = collection.find_one({'_id': ObjectId(note_id)})

    if note:
        return render_template('view_note.html', note=note)
    else:
        flash('Note not found.', 'error')
        return redirect(url_for('notes'))
    


@app.route('/edit_note/<note_id>', methods=['GET', 'POST'])
def edit_note(note_id):
    note = collection.find_one({'_id': ObjectId(note_id)})

    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        updated_at = datetime.utcnow()

        collection.update_one({'_id': ObjectId(note_id)}, {'$set': {'title': title, 'content': content, 'updated_at': updated_at}})
        return redirect(url_for('view_note', note_id=note_id))
    if note:
        return render_template('edit_note.html', note=note)
    else:
        flash('Note not found.', 'error')
        return redirect(url_for('notes'))



@app.route('/delete_note/<note_id>')
def delete_note(note_id):
    note = collection.find_one({'_id': ObjectId(note_id)})

    if note:
        collection.delete_one({'_id': ObjectId(note_id)})
        return redirect(url_for('notes'))
    else:
        flash('Note not found.', 'error')
        return redirect(url_for('notes'))



@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return redirect(url_for('login'))




if __name__ == '__main__':
    app.run(debug=True)
