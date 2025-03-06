from flask import Flask, render_template, redirect, request, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
import os
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt
from sqlalchemy.exc import IntegrityError

basedir = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(basedir, "app.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = os.urandom(24)

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

class User(db.Model, UserMixin):
    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False, unique=True)
    password_hash = db.Column(db.String(255), nullable=False)
    mobile = db.Column(db.String(15), nullable=False)
    age = db.Column(db.Integer, nullable=True)
    gender = db.Column(db.String(50), nullable=True)
    role = db.Column(db.String(50), nullable=False, default="user")

    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)

class Feedback(db.Model):
    __tablename__ = "feedback"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    rating = db.Column(db.Integer, nullable=True)  # Added rating field
    message = db.Column(db.Text, nullable=False)
    
    def __repr__(self):
        return f"<Feedback {self.id} - {self.name}>"

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Create all database tables
with app.app_context():
    db.create_all()

    # Check if an admin user already exists
    if not User.query.filter_by(role="admin").first():
        admin_user = User(name="Admin", email="admin@gmail.com", mobile="1234567890", role="admin")
        admin_user.set_password("admin@123")  # Set a default password
        db.session.add(admin_user)
        db.session.commit()
        print("Admin user created with email: admin@gmail.com and password: admin123")

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/submit", methods=['POST'])
def submit():
    try:
        name = request.form.get('name')
        email = request.form.get('email')
        message = request.form.get('message')
        rating = request.form.get('rating')
        
        # Debug prints
        print(f"Received form data - Name: {name}, Email: {email}, Rating: {rating}")
        
        # Check if required fields are present
        if not all([name, email, message]):
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({"success": False, "message": "Missing required fields"}), 400
            flash("Please fill in all required fields!", "danger")
            return redirect(url_for("feedback"))
        
        # Create new feedback
        new_feedback = Feedback(
            name=name, 
            email=email, 
            message=message,
            rating=int(rating) if rating else None
        )
        
        # Add to database
        db.session.add(new_feedback)
        db.session.commit()
        
        print(f"Feedback saved with ID: {new_feedback.id}")
        
        # Return appropriate response based on request type
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({"success": True, "message": "Feedback submitted successfully!"}), 200
        
        flash("Your feedback has been submitted successfully!", "success")
        return redirect('/thank_you')
        
    except Exception as e:
        print(f"Error in submit route: {str(e)}")
        db.session.rollback()
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({"success": False, "message": f"An error occurred: {str(e)}"}), 500
        
        flash(f"An error occurred: {str(e)}", "danger")
        return redirect(url_for("feedback"))

@app.route('/admin')
@login_required
def admin():
    feedback_list = Feedback.query.all()
    return render_template('admin.html', feedback_list=feedback_list)

@app.route('/thank_you')
def thank_you():
    return "<h2>Thank you for your feedback!</h2>"


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))

    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user)
            flash("Login successful!", "success")
            return redirect(url_for("profile"))
        else:
            flash("Invalid credentials!", "danger")
            return redirect(url_for("login"))

    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))

    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")
        mobile = request.form.get("mobile")
        age = request.form.get("age")
        gender = request.form.get("gender")
        terms = request.form.get("terms")

        if not all([name, email, password, confirm_password, mobile, age, gender, terms]):
            flash("Please fill in all fields!", "danger")
            return redirect(url_for("register"))

        if password != confirm_password:
            flash("Passwords do not match!", "danger")
            return redirect(url_for("register"))

        if int(age) < 13:
            flash("You must be at least 13 years old to register.", "danger")
            return redirect(url_for("register"))

        try:
            new_user = User(
                name=name, 
                email=email, 
                mobile=mobile, 
                age=int(age),
                gender=gender
            )
            new_user.set_password(password)
            
            db.session.add(new_user)
            db.session.commit()

            flash("Registration successful! Please log in.", "success")
            return redirect(url_for("login"))

        except IntegrityError:
            db.session.rollback()
            flash("Email already exists!", "danger")
            return redirect(url_for("register"))

    return render_template("register.html")

# @app.route("/update", methods=["GET", "POST"])
# @login_required
# def update():
#     if request.method == "POST":
#         try:
#             current_user.name = request.form.get("name")
#             current_user.email = request.form.get("email")
#             current_user.mobile = request.form.get("mobile")
#             current_user.age = int(request.form.get("age"))
#             current_user.gender = request.form.get("gender")

#             db.session.commit()
#             flash("Profile updated successfully!", "success")
#             return redirect(url_for('profile'))
#         except Exception as e:
#             db.session.rollback()
#             flash(f"An error occurred: {str(e)}", "danger")
#             return redirect(url_for('profile'))

#     return render_template("update.html")

@app.route("/update", methods=["GET", "POST"])
@login_required
def update():
    if request.method == "POST":
        try:
            # Only update the fields that are present in the form
            current_user.email = request.form.get("email")
            current_user.mobile = request.form.get("mobile")
            current_user.age = int(request.form.get("age"))
            current_user.gender = request.form.get("gender")

            db.session.commit()
            flash("Profile updated successfully!", "success")
            return redirect(url_for('profile'))
        except Exception as e:
            db.session.rollback()
            flash(f"An error occurred: {str(e)}", "danger")
            return redirect(url_for('profile'))

    return render_template("update.html")

# @app.route("/delete", methods=["GET", "POST"])
# @login_required
# def delete():
#     if request.method == "POST":
#         try:
#             user = current_user
#             logout_user()
#             db.session.delete(user)
#             db.session.commit()
#             flash("Your account has been deleted.", "info")
#             return redirect(url_for('home'))
#         except Exception as e:
#             db.session.rollback()
#             flash(f"An error occurred: {str(e)}", "danger")
#             return redirect(url_for('profile'))

#     return render_template("delete_confirmation.html")

@app.route("/delete", methods=["GET", "POST"])
@login_required
def delete():
    if request.method == "POST":
        try:
            # Store user ID for logging purposes
            user_id = current_user.id
            user_email = current_user.email
            
            # Log out the user first
            logout_user()
            
            # Find the user by ID to ensure we're deleting the right one
            user = User.query.get(user_id)
            if user:
                # Delete the user from the database
                db.session.delete(user)
                # Flush to ensure the deletion is sent to the database
                db.session.flush()
                # Commit the transaction to make it permanent
                db.session.commit()
                
                # Optional: Log the deletion (you would need to set up logging)
                app.logger.info(f"User (ID: {user_id}, Email: {user_email}) has been permanently deleted")
                
                flash("Your account has been successfully deleted from our system.", "info")
            else:
                flash("User not found. Please contact support.", "danger")
                
            return redirect(url_for('home'))
            
        except Exception as e:
            # Rollback in case of errors
            db.session.rollback()
            app.logger.error(f"Error deleting user: {str(e)}")
            flash(f"An error occurred while deleting your account: {str(e)}", "danger")
            return redirect(url_for('profile'))

    return render_template("delete_confirmation.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged out successfully!", "info")
    return redirect(url_for("login"))

@app.route("/profile")
@login_required
def profile():
    return render_template("profile.html")

@app.route("/about_us")
def about_us():
    return render_template("about_us.html")

@app.route("/learn")
def learn():
    return render_template("learn.html")

@app.route("/contact")
def contact():
    return render_template("contact.html")


@app.route("/term")
def term():
    return render_template("term.html")

@app.route("/pcod")
def pcod():
    return render_template("pcod.html")

@app.route("/blog")
def blog():
    return render_template("blog.html")

@app.route("/help")
def help():
    return render_template("help.html")

@app.route("/recommendation")
def recommendation():
    return render_template("recommendation.html")

@app.route("/meditation")
def meditation():
    return render_template("meditation.html")

@app.route("/sleep")
def sleep():
    return render_template("sleep.html")
    

@app.route("/feedback")
def feedback():
    return render_template("feedback.html")

if __name__ == "__main__":
    app.run(debug=True)