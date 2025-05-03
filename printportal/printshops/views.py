# printshops/views.py
from flask import render_template, redirect, url_for, flash, send_file
from . import printshops_bp
from models import Shop, FileRequest, db
from forms import UploadForm
from datetime import datetime
from sqlalchemy import func


@printshops_bp.route('/dashboard/<int:shop_id>')
def dashboard(shop_id):
    shop = Shop.query.get_or_404(shop_id)
    # Group file requests by request_group_id
    file_requests = FileRequest.query.filter_by(shop_id=shop_id).order_by(FileRequest.created_at.asc()).all()
    grouped_requests = {}
    for req in file_requests:
        group_id = req.request_group_id
        if group_id not in grouped_requests:
            grouped_requests[group_id] = {
                'queue_number': req.queue_number,
                'files': [],
                'total_price': 0,
                'notes': req.notes,
                'scheduled_at': req.scheduled_at,
                'status': req.status,
                'copies': req.copies,
                'color': req.color,
                'duplex': req.duplex
            }
        grouped_requests[group_id]['files'].append(req)
        grouped_requests[group_id]['total_price'] += req.total_price

    # Determine current queue number (first pending request)
    current_queue_number = None
    for group_id, group in grouped_requests.items():
        if group['status'] == 'pending':
            current_queue_number = group['queue_number']
            break

    return render_template('shop_dashboard.html', shop=shop, grouped_requests=grouped_requests,
                           current_queue_number=current_queue_number)


@printshops_bp.route('/monthly_stats/<int:shop_id>')
def monthly_stats(shop_id):
    shop = Shop.query.get_or_404(shop_id)

    # Calculate monthly stats for May 2025
    current_year = 2025
    current_month = 5  # May
    monthly_requests = FileRequest.query.filter(
        FileRequest.shop_id == shop_id,
        func.strftime('%Y', FileRequest.created_at) == str(current_year),
        func.strftime('%m', FileRequest.created_at) == f'{current_month:02d}'
    ).all()

    # Calculate today's stats (May 2, 2025)
    current_day = 2  # May 2
    today_requests = FileRequest.query.filter(
        FileRequest.shop_id == shop_id,
        func.strftime('%Y', FileRequest.created_at) == str(current_year),
        func.strftime('%m', FileRequest.created_at) == f'{current_month:02d}',
        func.strftime('%d', FileRequest.created_at) == f'{current_day:02d}'
    ).all()

    # Initialize monthly stats
    monthly_bw_pages = 0
    monthly_color_pages = 0
    monthly_bw_earnings = 0.0
    monthly_color_earnings = 0.0
    monthly_total_earnings = 0.0

    for request in monthly_requests:
        total_pages = request.num_pages * request.copies
        if request.color:
            monthly_color_pages += total_pages
            monthly_color_earnings += request.total_price
        else:
            monthly_bw_pages += total_pages
            monthly_bw_earnings += request.total_price
        monthly_total_earnings += request.total_price

    monthly_total_pages = monthly_bw_pages + monthly_color_pages

    # Initialize daily stats
    daily_bw_pages = 0
    daily_color_pages = 0
    daily_bw_earnings = 0.0
    daily_color_earnings = 0.0
    daily_total_earnings = 0.0

    for request in today_requests:
        total_pages = request.num_pages * request.copies
        if request.color:
            daily_color_pages += total_pages
            daily_color_earnings += request.total_price
        else:
            daily_bw_pages += total_pages
            daily_bw_earnings += request.total_price
        daily_total_earnings += request.total_price

    daily_total_pages = daily_bw_pages + daily_color_pages

    # Prepare data for charts
    monthly_chart_data = {
        'bw_pages': monthly_bw_pages,
        'color_pages': monthly_color_pages,
        'total_pages': monthly_total_pages,
        'bw_earnings': monthly_bw_earnings,
        'color_earnings': monthly_color_earnings,
        'total_earnings': monthly_total_earnings
    }

    daily_chart_data = {
        'bw_pages': daily_bw_pages,
        'color_pages': daily_color_pages,
        'total_pages': daily_total_pages,
        'bw_earnings': daily_bw_earnings,
        'color_earnings': daily_color_earnings,
        'total_earnings': daily_total_earnings
    }

    return render_template('monthly_stats.html', shop=shop, monthly_chart_data=monthly_chart_data,
                           daily_chart_data=daily_chart_data)


@printshops_bp.route('/download/<int:file_id>')
def download_file(file_id):
    file_request = FileRequest.query.get_or_404(file_id)
    # Find the current queue number (first pending request)
    pending_requests = FileRequest.query.filter_by(shop_id=file_request.shop_id, status='pending').order_by(
        FileRequest.created_at.asc()).all()
    current_queue_number = None
    for req in pending_requests:
        if req.status == 'pending':
            current_queue_number = req.queue_number
            break
    if current_queue_number:
        flash(f'Current Queue Number: {current_queue_number}', 'info')
    return send_file(file_request.file_path, as_attachment=True)


@printshops_bp.route('/update_status/<int:file_id>/<status>')
def update_status(file_id, status):
    file_request = FileRequest.query.get_or_404(file_id)
    if status in ['pending', 'printed', 'rejected']:
        file_request.status = status
        db.session.commit()
    if status == 'printed':
        file_request.bill_generated = True
        db.session.commit()
        flash(f'File status updated to {status} and bill generated.', 'success')
    else:
        flash(f'File status updated to {status}.', 'success')
    return redirect(url_for('printshops.dashboard', shop_id=file_request.shop_id))