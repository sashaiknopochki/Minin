from flask import Blueprint, jsonify

bp = Blueprint('auth', __name__, url_prefix='/auth')


@bp.route('/test')
def test():
    return jsonify({'message': 'Auth blueprint working'})