
from odoo import http
from odoo.http import request


class TelegramWebhookController(http.Controller):
    @http.route(f"/angkort/api/v1/telegram/webhook/<string:token>/<string:chat_id>", auth="public", type="json", cors="*")
    def telegram_webhook(self, token, chat_id, **kwargs):
        partner = request.env['res.partner'].sudo().search([('telegram_token', '=', token)], limit=1)
        if partner:
            partner.write({'telegram_chat_id': chat_id})
            return {'status': 'success', 'message': 'Chat ID updated'}
        return {'status': 'error', 'message': 'Invalid token'}