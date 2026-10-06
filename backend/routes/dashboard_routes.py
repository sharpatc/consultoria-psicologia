from flask import Blueprint, jsonify
from ..middlewares.auth_middleware import login_required
from ..models.message_repository import MessageRepository

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/api/dashboard/stats', methods=['GET'])
@login_required
def dashboard_stats():
    stats = MessageRepository.get_dashboard_stats()
    return jsonify(stats), 200
