# app.py
from flask import Flask, render_template, redirect, url_for, flash, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from config import Config
from forms import UploadForm, LoginForm, ShopCodeForm
from models import db, Shop, User, FileRequest
from printshops.views import printshops_bp
from werkzeug.utils import secure_filename
import os
from pypdf import PdfReader
from datetime import datetime
import random
import uuid

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

# Register blueprint for print shop views
app.register_blueprint(printshops_bp, url_prefix='/shop')

# Create database tables and initialize test data
with app.app_context():
    # Drop all tables and recreate them to ensure schema is up-to-date
    db.drop_all()
    db.create_all()
    # First shop: SHOP123
    if not Shop.query.filter_by(code='SHOP123').first():
        shop1 = Shop(code='SHOP123', name='first Print Shop', color_price=10.0, bw_price=1.0)
        db.session.add(shop1)
        db.session.commit()
        # Create shop owner user for SHOP123
        user1 = User(username='shopowner', shop_id=shop1.id)
        user1.set_password('password123')
        db.session.add(user1)
        db.session.commit()
    # Second shop: BAN12
    if not Shop.query.filter_by(code='BAN12').first():
        shop2 = Shop(code='BAN12', name='Second Print Shop', color_price=10.0, bw_price=1)
        db.session.add(shop2)
        db.session.commit()
        # Create shop owner user for BAN12
        user2 = User(username='dwk123', shop_id=shop2.id)
        user2.set_password('1234')
        db.session.add(user2)
        db.session.commit()


# Home route: Enter shop code
@app.route('/', methods=['GET', 'POST'])
def home():
    form = ShopCodeForm()
    if form.validate_on_submit():
        shop_code = form.shop_code.data
        shop = Shop.query.filter_by(code=shop_code).first()
        if shop:
            return redirect(url_for('upload', shop_code=shop_code))
        else:
            flash('Invalid shop code. Please try again.', 'danger')
    return render_template('home.html', form=form)


# Upload route: File upload for specific shop
@app.route('/upload/<shop_code>', methods=['GET', 'POST'])
def upload(shop_code):
    shop = Shop.query.filter_by(code=shop_code).first()
    if not shop:
        flash('Invalid shop code.', 'danger')
        return redirect(url_for('home'))

    form = UploadForm()
    if form.validate_on_submit():
        files = form.files.data
        copies = form.copies.data
        color = form.color.data
        duplex = form.duplex.data
        notes = form.notes.data
        scheduled_at = form.scheduled_at.data

        # Validate scheduled_at is in the future
        if scheduled_at <= datetime.now():
            flash('Scheduled date and time must be in the future.', 'danger')
            return render_template('upload.html', form=form, shop_code=shop_code)

        # Generate a unique request group ID for this batch of files
        request_group_id = str(uuid.uuid4())
        queue_number = random.randint(1, 99)  # Two-digit random queue number
        queue_number_str = f"{queue_number:02d}"  # Format as two digits

        # Calculate total pages for timer and total price
        total_pages = 0
        total_price = 0
        file_requests = []

        for file in files:
            if not file:
                continue
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)

            # Count pages in the file
            num_pages = 1  # Default for non-PDF files
            if filename.lower().endswith('.pdf'):
                try:
                    with open(file_path, 'rb') as f:
                        pdf = PdfReader(f)
                        num_pages = len(pdf.pages)
                except Exception as e:
                    flash(f'Error reading PDF pages for {filename}: {str(e)}. Assuming 1 page.', 'warning')

            total_pages += num_pages * copies

            # Calculate total price based on pages, copies, and color
            price_per_page = shop.color_price if color else shop.bw_price
            file_price = num_pages * copies * price_per_page
            total_price += file_price

            # Save file request to database
            file_request = FileRequest(
                shop_id=shop.id,
                filename=filename,
                file_path=file_path,
                copies=copies,
                color=color,
                duplex=duplex,
                notes=notes,
                total_price=file_price,
                num_pages=num_pages,
                scheduled_at=scheduled_at,
                queue_number=queue_number_str,
                request_group_id=request_group_id
            )
            db.session.add(file_request)
            file_requests.append(file_request)

        db.session.commit()

        # Calculate timer duration (in seconds)
        if total_pages <= 20:
            timer_duration = 40  # 40 seconds
        elif total_pages > 100:
            timer_duration = 300  # 5 minutes
        else:
            # Linear interpolation between 40 seconds (20 pages) and 300 seconds (100 pages)
            timer_duration = 40 + (total_pages - 20) * (300 - 40) / (100 - 20)

        flash('Files sent to print shop successfully!', 'success')
        return render_template('upload_success.html',
                               queue_number=queue_number_str,
                               timer_duration=int(timer_duration),
                               request_group_id=request_group_id,
                               total_price=total_price)

    return render_template('upload.html', form=form, shop_code=shop_code)


# Login route for shop owners
@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            flash('Login successful!', 'success')
            return redirect(url_for('printshops.dashboard', shop_id=user.shop_id))
        else:
            flash('Invalid username or password.', 'danger')
    return render_template('login.html', form=form)


# Route to check or mark printing as done
@app.route('/mark_done/<request_group_id>', methods=['GET', 'POST'])
def mark_done(request_group_id):
    file_requests = FileRequest.query.filter_by(request_group_id=request_group_id).all()
    if not file_requests:
        return jsonify({'status': 'not_found'}), 404

    if request.method == 'POST':
        for file_request in file_requests:
            file_request.status = 'printed'
            file_request.bill_generated = True
        db.session.commit()
        return jsonify({'status': 'completed'})

    # GET request: Check status
    all_printed = all(fr.status == 'printed' for fr in file_requests)
    bill_details = None
    if all_printed:
        bill_details = [
            {'filename': fr.filename, 'copies': fr.copies, 'price': fr.total_price}
            for fr in file_requests
        ]
    return jsonify({'status': 'completed' if all_printed else 'pending', 'bill': bill_details})


if __name__ == '__main__':
    app.run(debug=True)