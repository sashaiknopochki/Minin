from flask import Blueprint, jsonify

bp = Blueprint('settings', __name__, url_prefix='/settings')


@bp.route('/test')
def test():
    return jsonify({'message': 'Settings blueprint working'})