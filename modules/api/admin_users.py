"""Admin user editing endpoint with explicit storage and authorization dependencies."""
import logging
from flask import jsonify

logger = logging.getLogger(__name__)


def create_edit_user_handler(*, check_admin_auth, read_body, user_exists, update_user_fields):
    def admin_edit_user():
        if not check_admin_auth():
            return jsonify({'error': 'Unauthorized'}), 401

        data = read_body()
        user_id = data.get('user_id')
        user_data = data.get('user_data')

        if not user_id or user_data is None:
            return jsonify({
                'success': False,
                'message': 'User ID and user data required'
            }), 400

        if not isinstance(user_data, dict) or not user_data:
            return jsonify({'success': False, 'message': 'User data must be a non-empty object'}), 400

        try:
            if not user_exists(user_id):
                return jsonify({
                    'success': False,
                    'message': f'User {user_id} not found'
                }), 404

            if not update_user_fields(user_id, user_data):
                return jsonify({
                    'success': False,
                    'message': 'Failed to save user data'
                }), 500

            logger.info(f"[Admin] ✓ User data edited: user_id={user_id}")


            return jsonify({
                'success': True,
                'message': 'User data updated successfully'
            })

        except Exception as e:
            logger.error(f"[Admin] ✗ Edit user error: user_id={user_id}, error={e}", exc_info=True)
            return jsonify({
                'success': False,
                'message': str(e)
            }), 500

    return admin_edit_user
