from flask import Flask, render_template, request, redirect, url_for, flash, session
from pymongo import MongoClient
from bson import ObjectId  # Import ObjectId to work with MongoDB ObjectIds
import base64
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# MongoDB connection
client = MongoClient("mongodb+srv://tiger:tigersateesh@cluster0.0ggj59e.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
db = client['competition_db65']
photos_collection = db['photos']
votes_collection = db['votes']
emails_collection = db['emails']

# Configure Flask to accept larger file uploads
app.config['MAX_CONTENT_LENGTH'] = 15 * 1024 * 1024  # Set max file size to 15 MB

# Load HTML templates from the root folder
@app.route('/')
def index():
    with open('index.html', 'r') as f:
        content = f.read()
    return content

@app.route('/verify_email', methods=['POST'])
def verify_email():
    email = request.form['email']
    user = emails_collection.find_one({"email": email})
    
    if not user:
        flash("EMAIL NOT REGISTERED OR YOU DONT BELONG TO DATA SCIENCE DEPARTMENT !", "error")
        return redirect(url_for('index'))
    elif user.get("voted", False):
        flash("You have already voted.", "warning")
        return redirect(url_for('index'))

    session['email'] = email
    session['user_name'] = user.get("name", "User")
    
    return redirect(url_for('gallery'))

@app.route('/gallery')
def gallery():
    user_name = session.get('user_name', "User")
    email = session.get('email', None)
    
    if not email:
        flash("You need to verify your email first.", "error")
        return redirect(url_for('index'))

    photos = list(photos_collection.find())
    for photo in photos:
        photo['image'] = base64.b64encode(photo['image']).decode('utf-8')
    
    # Load gallery.html from the root folder
    with open('gallery.html', 'r') as f:
        content = f.read()
    
    # Replace placeholder for photos in the gallery.html file
    photos_html = ""
    for photo in photos:
        photos_html += f"""
            <div class="photo-item">
                <img src="data:image/jpeg;base64,{photo['image']}" alt="Photo">
                <form action="{url_for('vote')}" method="POST">
                    <input type="hidden" name="image_id" value="{photo['_id']}">
                    <button type="submit">Vote</button>
                </form>
            </div>
        """
    
    content = content.replace("{{ photos_placeholder }}", photos_html)
    content = content.replace("{{ user_name }}", user_name)
    content = content.replace("{{ email }}", email)

    return content

@app.route('/vote', methods=['POST'])
def vote():
    photo_id = request.form['image_id']
    email = session.get('email', None)

    if not email:
        flash("You need to verify your email first.", "error")
        return redirect(url_for('index'))

    try:
        photo = photos_collection.find_one({"_id": ObjectId(photo_id)})
        if not photo:
            flash("The selected photo does not exist.", "error")
            return redirect(url_for('gallery'))

        user = emails_collection.find_one({"email": email})
        if not user:
            flash("Email not found in the database.", "error")
            return redirect(url_for('index'))
        
        votes_collection.insert_one({"photo_id": photo_id, "email": email})

        update_result = emails_collection.update_one({"email": email}, {"$set": {"voted": True}})
        
        if update_result.modified_count == 0:
            flash("There was an issue marking your email as voted. Please try again.", "error")
            return redirect(url_for('index'))
        
        photos_collection.update_one({"_id": ObjectId(photo_id)}, {"$inc": {"votes": 1}})

        flash("Thank you for voting! Your vote has been recorded.", "success")
        return redirect(url_for('index'))

    except Exception as e:
        print(f"Error occurred: {str(e)}")  # Log error for debugging
        flash("An error occurred while processing your vote.", "error")
        return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
