from odoo import models, fields, tools


class HrLeaveReportCalendar(models.Model):
    _inherit = 'hr.leave.report.calendar'

    biometric_id = fields.Char(
        string='Número de Empleado',
        related='employee_id.biometric_id',
        readonly=True
    )

    biometric_id_numeric = fields.Integer(
        string='No. Empleado',
        related='employee_id.biometric_id_numeric',
        readonly=True,
        help='Campo numérico para ordenamiento'
    )

    def init(self):
        """Sobrescribir para agregar biometric_id a la vista SQL"""
        tools.drop_view_if_exists(self._cr, 'hr_leave_report_calendar')
        self._cr.execute("""CREATE OR REPLACE VIEW hr_leave_report_calendar AS
        (SELECT
            hl.id AS id,
            hl.id AS leave_id,
            hl.date_from AS start_datetime,
            hl.date_to AS stop_datetime,
            hl.employee_id AS employee_id,
            hl.state AS state,
            hl.department_id AS department_id,
            hl.number_of_days as duration,
            hl.private_name AS description,
            hl.holiday_status_id AS holiday_status_id,
            em.company_id AS company_id,
            em.job_id AS job_id,
            em.biometric_id AS biometric_id,
            COALESCE(
                rr.tz,
                rc.tz,
                cc.tz,
                'UTC'
            ) AS tz,
            hl.state = 'refuse' as is_striked,
            hl.state not in ('validate', 'refuse') as is_hatched
        FROM hr_leave hl
            LEFT JOIN hr_employee em
                ON em.id = hl.employee_id
            LEFT JOIN resource_resource rr
                ON rr.id = em.resource_id
            LEFT JOIN resource_calendar rc
                ON rc.id = em.resource_calendar_id
            LEFT JOIN res_company co
                ON co.id = em.company_id
            LEFT JOIN resource_calendar cc
                ON cc.id = co.resource_calendar_id
        WHERE
            hl.state IN ('confirm', 'validate', 'validate1', 'refuse')
        );
        """)
