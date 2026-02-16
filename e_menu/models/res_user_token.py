import hashlib

from odoo import fields, models, api, _


class ResUserToken(models.Model):
    _name = "res.user.token"
    _description = "User token"

    user_id = fields.Many2one('res.users', string="User", required=True, ondelete='cascade')
    access_token = fields.Char(string="Access Token", required=True)
    refresh_token = fields.Char(string="Refresh Token", required=True)
    expires_at = fields.Datetime(string="Access Token Expiry")
    refresh_expires_at = fields.Datetime(string="Refresh Token Expiry")
    active = fields.Boolean(string="Active", default=True)
    deactivated_at = fields.Datetime()

    @api.model
    def create_token(self, user_id, access_token, refresh_token, access_expiry, refresh_expiry):
        """Generate and store a new token for a user."""
        hashed_access = hashlib.sha256(access_token.encode()).hexdigest()
        hashed_refresh = hashlib.sha256(refresh_token.encode()).hexdigest()
        return self.create([{
            'user_id': user_id,
            'access_token': hashed_access,
            'refresh_token': hashed_refresh,
            'expires_at': access_expiry,
            'refresh_expires_at': refresh_expiry,
            'active': True,
        }])

    def validate_token(self, token, token_type='access'):
        """Validate an access or refresh token and return user_id if valid."""
        hashed_token = hashlib.sha256(token.encode()).hexdigest()
        field = 'access_token' if token_type == 'access' else 'refresh_token'
        expiry_field = 'expires_at' if token_type == 'access' else 'refresh_expires_at'
        token_record = self.search([(field, '=', hashed_token), ('active', '=', True)], limit=1)
        if token_record and fields.Datetime.now() < token_record[expiry_field]:
            return token_record.user_id.id
        return False

    def refresh_access_token(self, refresh_token, new_access_token, access_expiry):
        """Rotate the access token on an existing record found by refresh token.

        Returns the user_id if the refresh token is valid, False otherwise.
        """
        hashed_refresh = hashlib.sha256(refresh_token.encode()).hexdigest()
        token_record = self.search([
            ('refresh_token', '=', hashed_refresh),
            ('active', '=', True),
        ], limit=1)
        if not token_record or fields.Datetime.now() >= token_record.refresh_expires_at:
            return False
        hashed_access = hashlib.sha256(new_access_token.encode()).hexdigest()
        token_record.write({
            'access_token': hashed_access,
            'expires_at': access_expiry,
        })
        return token_record.user_id.id

    def deactivate_token(self, token_type='access'):
        """Deactivate a token."""
        for record in self:
            record.write({
                'active': False,
                'deactivated_at': fields.Datetime.now(),
            })