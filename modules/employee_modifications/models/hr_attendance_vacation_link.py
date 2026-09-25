# -*- coding: utf-8 -*-

from odoo import api, models


class HrAttendanceVacationLink(models.Model):
    _inherit = 'hr.attendance'

    @api.model
    def _get_approved_leave_type_name(self, employee, process_date, start_utc_str, end_utc_str):
        """Reconoce también vacaciones dadas de alta directamente en hr.vacation
        (sin pasar por Time Off), para que el cron de faltas no las marque como
        ausencia injustificada.
        """
        leave_name = super()._get_approved_leave_type_name(employee, process_date, start_utc_str, end_utc_str)
        if leave_name:
            return leave_name

        vacation = self.env['hr.vacation'].sudo().search([
            ('employee_id', '=', employee.id),
            ('state', '=', 'validate'),
            ('date_from', '<=', process_date),
            ('date_to', '>=', process_date),
        ], limit=1)
        return 'Vacaciones' if vacation else False
