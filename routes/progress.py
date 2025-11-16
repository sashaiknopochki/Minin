from flask import Blueprint, jsonify

bp = Blueprint('progress', __name__, url_prefix='/progress')


@bp.route('/test')
def test():
    return jsonify({'message': 'Progress blueprint working'})