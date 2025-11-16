from flask import Blueprint, jsonify

bp = Blueprint('quiz', __name__, url_prefix='/quiz')


@bp.route('/test')
def test():
    return jsonify({'message': 'Quiz blueprint working'})