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
        """Validate an access or refresh token."""
        hashed_token = hashlib.sha256(token.encode()).hexdigest()
        domain = [('access_token' if token_type == 'access' else 'refresh_token', '=', hashed_token),
                  ('active', '=', True)]
        token_record = self.search(domain, limit=1)
        if token_record and fields.Datetime.now() < (
        token_record.expires_at if token_type == 'access' else token_record.refresh_expires_at):
            return token_record.user_id.id
        return False

    def deactivate_token(self, token_type='access'):
        """Deactivate a token."""
        field = 'access_token' if token_type == 'access' else 'refresh_token'
        for record in self:
            record.write({'active': False})