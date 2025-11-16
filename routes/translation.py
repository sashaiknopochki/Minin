from flask import Blueprint, jsonify

bp = Blueprint('translation', __name__, url_prefix='/translation')


@bp.route('/test')
def test():
    return jsonify({'message': 'Translation blueprint working'})
