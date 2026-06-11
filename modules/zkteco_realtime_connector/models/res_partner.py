from odoo import models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def _get_signup_target_company(self):
        self.ensure_one()

        # Priority: user main company linked to this contact.
        linked_users = self.sudo().user_ids
        if linked_users:
            user_with_company = linked_users.filtered(lambda user: user.company_id)
            if user_with_company:
                return user_with_company[0].company_id

        employee_domain = ['|', ('work_contact_id', '=', self.id), ('address_home_id', '=', self.id)]
        employee = self.env['hr.employee'].sudo().search(employee_domain, limit=1)

        if not employee and linked_users:
            employee = self.env['hr.employee'].sudo().search([('user_id', 'in', linked_users.ids)], limit=1)

        return employee.company_id if employee else False

    def get_base_url(self):
        if self.env.context.get('use_company_signup_base_url'):
            self.ensure_one()
            target_company = self._get_signup_target_company()
            if target_company:
                if hasattr(target_company, 'get_attendance_reports_base_url'):
                    company_url = target_company.get_attendance_reports_base_url()
                else:
                    company_url = (target_company.attendance_reports_base_url or '').rstrip('/')
                if company_url:
                    return company_url
        return super().get_base_url()

    def _get_signup_url_for_action(self, url=None, action=None, view_type=None, menu_id=None, res_id=None, model=None):
        # Only signup/reset invitation links should honor company-specific base URL.
        return super(
            ResPartner,
            self.with_context(use_company_signup_base_url=True),
        )._get_signup_url_for_action(
            url=url,
            action=action,
            view_type=view_type,
            menu_id=menu_id,
            res_id=res_id,
            model=model,
        )
