# -*- coding: utf-8 -*-

import json
import threading

from odoo.tests.common import HttpCase, new_test_user, tagged


@tagged("-at_install", "post_install")
class TestAPIRoutes(HttpCase):
    readonly_enabled = False
    OWNER_PASSWORD = "Pl1bhD@2!owner"
    OTHER_PASSWORD = "Pl1bhD@2!other"

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["ir.config_parameter"].sudo().set_param("database.secret", "test-jwt-secret")

        cls.owner_user = new_test_user(
            cls.env,
            login="merchant.owner@example.com",
            password=cls.OWNER_PASSWORD,
            groups="base.group_user,e_menu.group_merchant",
            name="Merchant Owner",
        )
        cls.other_user = new_test_user(
            cls.env,
            login="merchant.other@example.com",
            password=cls.OTHER_PASSWORD,
            groups="base.group_user,e_menu.group_merchant",
            name="Merchant Other",
        )

        cls.owner_shop = cls.env["res.partner"].sudo().with_context(create_company=True).create({
            "name": "Owner Shop",
            "phone": "012345678",
            "customer_address": "Owner Street",
            "type": "store",
            "owner_user_id": cls.owner_user.id,
        })
        cls.other_shop = cls.env["res.partner"].sudo().with_context(create_company=True).create({
            "name": "Other Shop",
            "phone": "098765432",
            "customer_address": "Other Street",
            "type": "store",
            "owner_user_id": cls.other_user.id,
        })

        cls.owner_user.partner_id.parent_id = cls.owner_shop
        cls.other_user.partner_id.parent_id = cls.other_shop

        cls.owner_order = cls.env["sale.order"].sudo().create({
            "partner_id": cls.owner_user.partner_id.id,
            "shop_id": cls.owner_shop.id,
        })
        cls.other_order = cls.env["sale.order"].sudo().create({
            "partner_id": cls.other_user.partner_id.id,
            "shop_id": cls.other_shop.id,
        })

    def _post_json(self, path, payload, headers=None):
        request_headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if headers:
            request_headers.update(headers)
        return self.url_open(path, data=json.dumps(payload), headers=request_headers)

    def _post_form(self, path, payload, headers=None):
        url = self.base_url() + path
        request_headers = {
            "Accept": "application/json",
        }
        if headers:
            request_headers.update(headers)
        return self.opener.post(url, data=payload, headers=request_headers, timeout=12)

    def _patch_form(self, path, payload, headers=None):
        url = self.base_url() + path
        request_headers = {
            "Accept": "application/json",
        }
        if headers:
            request_headers.update(headers)
        return self.opener.patch(url, data=payload, headers=request_headers, timeout=12)

    def _login_and_get_tokens(self, login, password):
        response = self._post_json("/angkort/api/v1/login", {
            "username": login,
            "password": password,
        })
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertTrue(payload["status"], payload)
        return payload["data"]

    def _auth_headers(self, access_token):
        return {"Authorization": f"Bearer {access_token}"}

    def mandatory_request_route(self, route):
        return False

    def _wait_remaining_requests(self, timeout=10):
        """Ignore unrelated websocket threads to keep API tests fast and quiet."""
        def get_non_websocket_threads():
            threads = []
            for thread in threading.enumerate():
                if not thread.name.startswith('odoo.service.http.request.'):
                    continue
                url = getattr(thread, 'url', '') or ''
                if '/websocket' in url:
                    continue
                threads.append(thread)
            return threads

        request_threads = get_non_websocket_threads()
        if not request_threads:
            return

        for thread in request_threads:
            thread.join(timeout)

    def test_login_returns_owned_shops_from_owner_field(self):
        tokens = self._login_and_get_tokens("merchant.owner@example.com", self.OWNER_PASSWORD)

        self.assertEqual(tokens["roles"], "MERCHANT")
        self.assertIn(
            self.owner_shop.id,
            [shop["id"] for shop in tokens["shops"]],
        )
        self.assertNotIn(
            self.other_shop.id,
            [shop["id"] for shop in tokens["shops"]],
        )

    def test_refresh_accepts_form_encoded_request(self):
        tokens = self._login_and_get_tokens("merchant.owner@example.com", self.OWNER_PASSWORD)

        response = self._post_form("/angkort/api/v1/refresh", {
            "refresh_token": tokens["refresh_token"],
        })

        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertTrue(payload["status"], payload)
        self.assertTrue(payload["data"]["access_token"])

    def test_create_shop_sets_owner_and_parent_shop(self):
        tokens = self._login_and_get_tokens("merchant.owner@example.com", self.OWNER_PASSWORD)

        response = self._post_form(
            "/angkort/api/v1/shop",
            {
                "name": "Fresh Shop",
                "phone": "011223344",
                "customer_address": "Fresh Street",
                "email": "fresh.shop@example.com",
            },
            headers=self._auth_headers(tokens["access_token"]),
        )

        self.assertEqual(response.status_code, 201, response.text)
        payload = response.json()
        created_shop = self.env["res.partner"].sudo().browse(payload["id"])
        self.assertTrue(created_shop.exists())
        self.assertEqual(created_shop.type, "store")
        self.assertEqual(created_shop.owner_user_id.id, self.owner_user.id)
        self.owner_user.partner_id.invalidate_recordset(["parent_id"])
        self.assertEqual(self.owner_user.partner_id.parent_id.id, created_shop.id)

    def test_create_variant_for_owned_shop(self):
        tokens = self._login_and_get_tokens("merchant.owner@example.com", self.OWNER_PASSWORD)

        response = self._post_form(
            f"/angkort/api/v1/shop/{self.owner_shop.id}/product/variant",
            {
                "name": "Spice Level",
                "create_variant": "always",
                "display_type": "radio",
            },
            headers=self._auth_headers(tokens["access_token"]),
        )

        self.assertEqual(response.status_code, 201, response.text)
        payload = response.json()
        self.assertEqual(payload["name"], "Spice Level")
        created_variant = self.env["product.attribute"].sudo().browse(payload["id"])
        self.assertTrue(created_variant.exists())
        self.assertEqual(created_variant.shop_id.id, self.owner_shop.id)
        self.assertEqual(created_variant.display_type, "radio")
        self.assertEqual(created_variant.create_variant, "always")

    def test_create_product_for_owned_shop(self):
        tokens = self._login_and_get_tokens("merchant.owner@example.com", self.OWNER_PASSWORD)
        variant = self.env["product.attribute"].sudo().create({
            "name": "Temperature",
            "shop_id": self.owner_shop.id,
            "create_variant": "always",
            "display_type": "radio",
        })
        hot_value = self.env["product.attribute.value"].sudo().create({
            "name": "Hot",
            "attribute_id": variant.id,
        })

        response = self._post_json(
            f"/angkort/api/v1/shop/{self.owner_shop.id}/product",
            {
                "name": "Noodle Soup",
                "code": "SOUP-001",
                "description": "House noodle soup",
                "sale_price": 4.5,
                "attribute_lines": [
                    {
                        "attribute_id": variant.id,
                        "value_ids": [hot_value.id],
                    }
                ],
            },
            headers=self._auth_headers(tokens["access_token"]),
        )

        self.assertEqual(response.status_code, 201, response.text)
        payload = response.json()
        product_data = payload["data"]
        self.assertEqual(product_data["name"], "Noodle Soup")
        created_product = self.env["product.template"].sudo().browse(product_data["id"])
        self.assertTrue(created_product.exists())
        self.assertEqual(created_product.shop_id.id, self.owner_shop.id)
        self.assertEqual(created_product.default_code, "SOUP-001")
        self.assertEqual(created_product.list_price, 4.5)
        self.assertEqual(created_product.attribute_line_ids.mapped("attribute_id").ids, [variant.id])

    def test_owner_can_patch_shop_created_with_sudo(self):
        tokens = self._login_and_get_tokens("merchant.owner@example.com", self.OWNER_PASSWORD)

        response = self._patch_form(
            f"/angkort/api/v1/shop/{self.owner_shop.id}",
            {"name": "Owner Shop Updated"},
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )

        self.assertEqual(response.status_code, 200, response.text)
        self.owner_shop.invalidate_recordset(["name"])
        self.assertEqual(self.owner_shop.name, "Owner Shop Updated")

    def test_non_owner_cannot_patch_foreign_shop(self):
        tokens = self._login_and_get_tokens("merchant.other@example.com", self.OTHER_PASSWORD)

        response = self._patch_form(
            f"/angkort/api/v1/shop/{self.owner_shop.id}",
            {"name": "Should Not Work"},
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )

        self.assertEqual(response.status_code, 403, response.text)
        payload = response.json()
        self.assertIn("Unauthorized", payload["error"])

    def test_sale_route_requires_authentication(self):
        response = self.url_open("/angkort/api/v1/sale")

        self.assertEqual(response.status_code, 401, response.text)

    def test_sale_route_is_scoped_to_owned_shop(self):
        tokens = self._login_and_get_tokens("merchant.owner@example.com", self.OWNER_PASSWORD)

        response = self.url_open(
            "/angkort/api/v1/sale",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )

        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        order_ids = [order["id"] for order in payload["data"]]
        self.assertIn(self.owner_order.id, order_ids)
        self.assertNotIn(self.other_order.id, order_ids)

    def test_logout_revokes_token_for_protected_routes(self):
        tokens = self._login_and_get_tokens("merchant.owner@example.com", self.OWNER_PASSWORD)
        auth_header = {"Authorization": f"Bearer {tokens['access_token']}"}

        logout_response = self._post_form("/angkort/api/v1/logout", {}, headers=auth_header)
        self.assertEqual(logout_response.status_code, 200, logout_response.text)

        sale_response = self.url_open("/angkort/api/v1/sale", headers=auth_header)
        self.assertEqual(sale_response.status_code, 401, sale_response.text)
