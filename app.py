from flask import Flask, render_template, request, redirect, url_for, flash, session
from pymongo import MongoClient
from bson import ObjectId  # Import ObjectId to work with MongoDB ObjectIds
import base64

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# MongoDB connection
client = MongoClient("mongodb+srv://tiger:tigersateesh@cluster0.0ggj59e.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
db = client['competition_db65']
photos_collection = db['photos']
votes_collection = db['votes']
emails_collection = db['emails']

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/verify_email', methods=['POST'])
def verify_email():
    email = request.form['email']
    user = emails_collection.find_one({"email": email})
    
    # Check if email is registered
    if not user:
        flash("EMAIL NOT REGISTERED OR YOU DONT BELONG TO DATA SCIENCE DEPARTMENT !", "error")
        return redirect(url_for('index'))
    
    # Check if user has already voted at the email verification step
    elif user.get("voted", False):
        flash("You have already voted.", "warning")
        return redirect(url_for('index'))
    
    # Store email in session to use later during voting
    session['email'] = email
    session['user_name'] = user.get("name", "User")
    
    # Redirect to gallery if they haven't voted yet
    return redirect(url_for('gallery'))

@app.route('/gallery')
def gallery():
    user_name = session.get('user_name', "User")
    email = session.get('email', None)
    
    if not email:
        flash("You need to verify your email first.", "error")
        return redirect(url_for('index'))
    
    # Retrieve and encode photos for display
    photos = list(photos_collection.find())
    for photo in photos:
        photo['image'] = base64.b64encode(photo['image']).decode('utf-8')
    
    return render_template('gallery.html', user_name=user_name, email=email, photos=photos)

@app.route('/vote', methods=['POST'])
def vote():
    photo_id = request.form['image_id']  # Get the photo ID from the form
    email = session.get('email', None)  # Get the email from session

    if not email:
        flash("You need to verify your email first.", "error")
        return redirect(url_for('index'))

    try:
        # Check if the photo ID exists in the database
        photo = photos_collection.find_one({"_id": ObjectId(photo_id)})
        if not photo:
            flash("The selected photo does not exist.", "error")
            return redirect(url_for('gallery'))

        # Check if the email exists in the database (optional check, since we assume it's verified)
        user = emails_collection.find_one({"email": email})
        if not user:
            flash("Email not found in the database.", "error")
            return redirect(url_for('index'))
        
        # Record the vote and save which email voted for which photo
        votes_collection.insert_one({"photo_id": photo_id, "email": email})

        # Mark the user as "voted" in emails_collection
        update_result = emails_collection.update_one({"email": email}, {"$set": {"voted": True}})

        # Check if the update was successful
        if update_result.modified_count == 0:
            flash("There was an issue marking your email as voted. Please try again.", "error")
            return redirect(url_for('index'))
        
        # Increment the vote count for the selected photo by 1
        photos_collection.update_one({"_id": ObjectId(photo_id)}, {"$inc": {"votes": 1}})

        flash("Thank you for voting! Your vote has been recorded.", "success")
        return redirect(url_for('index'))

    except Exception as e:
        print(f"Error occurred: {str(e)}")  # Log error for debugging
        flash("An error occurred while processing your vote.", "error")
        return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)