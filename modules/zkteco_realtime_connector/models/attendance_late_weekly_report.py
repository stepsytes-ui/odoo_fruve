import json

from odoo import fields, models, tools
from odoo.exceptions import ValidationError


FIXED_DEVICE_TIMEZONE_NAME = 'America/Tijuana'


class AttendanceLateWeeklyReport(models.Model):
    _name = 'attendance.late.weekly.report'
    _description = 'Reporte Semanal de Retardos'
    _auto = False
    _order = 'custom_year desc, custom_week desc, employee_name asc'

    employee_id = fields.Many2one('hr.employee', string='Empleado', readonly=True)
    company_id = fields.Many2one('res.company', string='Compania', readonly=True)
    employee_name = fields.Char(string='Nombre', readonly=True)
    biometric_id = fields.Char(string='No. Empleado', readonly=True)

    custom_year = fields.Integer(string='Anio', readonly=True)
    custom_week = fields.Integer(string='Semana', readonly=True)
    week_group_label = fields.Char(string='Semana', readonly=True)
    week_label = fields.Char(string='Semana', readonly=True)
    week_start_date = fields.Date(string='Inicio Semana', readonly=True)
    week_end_date = fields.Date(string='Fin Semana', readonly=True)

    late_days_count = fields.Integer(string='Dias con Retardo', readonly=True)
    late_dates_text = fields.Text(string='Dias de Retardo', readonly=True)

    base_total_late_minutes = fields.Integer(string='Minutos Retardo Base', readonly=True)
    total_late_minutes = fields.Integer(string='Minutos Retardo', readonly=False)
    base_daily_minutes_json = fields.Text(string='Detalle Diario Base', readonly=True)
    daily_minutes_json = fields.Text(string='Detalle Diario', readonly=False)
    total_late_hours_floor = fields.Integer(string='Horas Retardo (Piso)', readonly=True)
    discount_days = fields.Float(string='Descuento Dias', digits=(16, 3), readonly=True)
    base_payable_days = fields.Float(string='Neto Total Base', digits=(16, 2), readonly=True)
    payable_days = fields.Float(string='Neto Total', digits=(16, 2), readonly=False)

    has_manual_override = fields.Boolean(string='Ajuste Manual', readonly=True)

    is_future = fields.Boolean(string='Semana Futura', readonly=True)

    def action_reset_weekly_adjustment(self):
        adjustment_model = self.env['attendance.late.weekly.adjustment']
        for record in self:
            if not record.employee_id:
                continue
            adjustment = adjustment_model.search([
                ('employee_id', '=', record.employee_id.id),
                ('custom_year', '=', record.custom_year),
                ('custom_week', '=', record.custom_week),
            ], limit=1)
            if adjustment:
                # Reiniciar solo el override de calculo, manteniendo observaciones.
                adjustment.write({
                    'manual_total_late_minutes': False,
                    'manual_daily_minutes_json': False,
                    'manual_payable_days': False,
                })
                if not (adjustment.manual_observation or '').strip():
                    # Si no hay comentario, limpiar registro para evitar basura historica.
                    adjustment.unlink()
        return True

    def write(self, vals):
        editable_fields = {'total_late_minutes', 'daily_minutes_json', 'payable_days'}
        if not (editable_fields & set(vals.keys())):
            return True

        adjustment_model = self.env['attendance.late.weekly.adjustment']
        wrote_adjustment = False

        for record in self:
            if not record.employee_id:
                continue

            adjustment = adjustment_model.search([
                ('employee_id', '=', record.employee_id.id),
                ('custom_year', '=', record.custom_year),
                ('custom_week', '=', record.custom_week),
            ], limit=1)

            adjustment_vals = {}

            if 'daily_minutes_json' in vals:
                raw_daily = vals.get('daily_minutes_json')
                if raw_daily in (False, None, ''):
                    adjustment_vals['manual_daily_minutes_json'] = False
                    adjustment_vals['manual_total_late_minutes'] = False
                else:
                    try:
                        parsed = json.loads(raw_daily)
                    except (TypeError, ValueError) as exc:
                        raise ValidationError('El detalle diario debe estar en formato JSON valido.') from exc

                    if not isinstance(parsed, list) or len(parsed) != 7:
                        raise ValidationError('El detalle diario debe contener exactamente 7 valores (viernes a jueves).')

                    normalized = []
                    for value in parsed:
                        try:
                            minutes_value = int(value)
                        except (TypeError, ValueError) as exc:
                            raise ValidationError('Todos los minutos diarios deben ser numeros enteros.') from exc
                        if minutes_value < 0:
                            raise ValidationError('Los minutos diarios no pueden ser negativos.')
                        normalized.append(minutes_value)

                    adjustment_vals['manual_daily_minutes_json'] = json.dumps(normalized)
                    adjustment_vals['manual_total_late_minutes'] = sum(normalized)

            if 'total_late_minutes' in vals:
                minutes_value = vals.get('total_late_minutes')
                if minutes_value in (False, None, ''):
                    adjustment_vals['manual_total_late_minutes'] = False
                    if 'daily_minutes_json' not in vals:
                        adjustment_vals['manual_daily_minutes_json'] = False
                else:
                    try:
                        minutes_int = int(minutes_value)
                    except (TypeError, ValueError):
                        raise ValidationError('Los minutos de retardo deben ser un numero entero.')
                    if minutes_int < 0:
                        raise ValidationError('Los minutos de retardo no pueden ser negativos.')
                    adjustment_vals['manual_total_late_minutes'] = minutes_int
                    if 'daily_minutes_json' not in vals:
                        adjustment_vals['manual_daily_minutes_json'] = False

                # Si se cambia minutos y no se edita dias manuales, se recalcula dias a pagar.
                if 'payable_days' not in vals:
                    adjustment_vals['manual_payable_days'] = False

            if 'payable_days' in vals:
                payable_value = vals.get('payable_days')
                if payable_value in (False, None, ''):
                    adjustment_vals['manual_payable_days'] = False
                else:
                    try:
                        payable_float = float(payable_value)
                    except (TypeError, ValueError):
                        raise ValidationError('Los dias a pagar deben ser un numero valido.')
                    if payable_float < 0:
                        raise ValidationError('Los dias a pagar no pueden ser negativos.')
                    adjustment_vals['manual_payable_days'] = round(payable_float, 2)

            if not adjustment_vals:
                continue

            if adjustment:
                adjustment.write(adjustment_vals)
            else:
                adjustment_model.create({
                    'employee_id': record.employee_id.id,
                    'custom_year': record.custom_year,
                    'custom_week': record.custom_week,
                    **adjustment_vals,
                })

            wrote_adjustment = True

        if wrote_adjustment:
            # Forzar recarga de la vista SQL para reflejar el ajuste en el primer guardado.
            self.env.invalidate_all()

        return True

    def init(self):
        tools.drop_view_if_exists(self._cr, self._table)
        self._cr.execute(f"""
            CREATE OR REPLACE VIEW {self._table} AS (
                WITH late_rows AS (
                    SELECT
                        att.id AS attendance_id,
                        att.employee_id,
                        emp.company_id,
                        att.punctuality_status,
                        emp.name AS employee_name,
                        emp.biometric_id,
                        ((att.check_in AT TIME ZONE 'UTC') AT TIME ZONE '{FIXED_DEVICE_TIMEZONE_NAME}') AS check_in_local,
                        (
                            CASE EXTRACT(ISODOW FROM ((att.check_in AT TIME ZONE 'UTC') AT TIME ZONE '{FIXED_DEVICE_TIMEZONE_NAME}'))::int
                                WHEN 1 THEN CASE WHEN sm.special_monday THEN sm.in_monday ELSE sm.hora_entrada END
                                WHEN 2 THEN CASE WHEN sm.special_tuesday THEN sm.in_tuesday ELSE sm.hora_entrada END
                                WHEN 3 THEN CASE WHEN sm.special_wednesday THEN sm.in_wednesday ELSE sm.hora_entrada END
                                WHEN 4 THEN CASE WHEN sm.special_thursday THEN sm.in_thursday ELSE sm.hora_entrada END
                                WHEN 5 THEN CASE WHEN sm.special_friday THEN sm.in_friday ELSE sm.hora_entrada END
                                WHEN 6 THEN CASE WHEN sm.special_saturday THEN sm.in_saturday ELSE sm.hora_entrada END
                                WHEN 7 THEN CASE WHEN sm.special_sunday THEN sm.in_sunday ELSE sm.hora_entrada END
                                ELSE sm.hora_entrada
                            END
                        ) AS shift_start_src
                    FROM hr_attendance att
                    INNER JOIN hr_employee emp ON emp.id = att.employee_id
                    LEFT JOIN shift_management sm ON sm.id = emp.turno_id
                    WHERE att.punctuality_status IN ('late', 'absence')
                        AND att.check_in IS NOT NULL
                        AND (
                            att.punctuality_status = 'absence'
                            OR (
                                emp.turno_id IS NOT NULL
                                AND sm.hora_entrada IS NOT NULL
                            )
                        )
                ),
                normalized AS (
                    SELECT
                        lr.attendance_id,
                        lr.employee_id,
                        lr.company_id,
                        lr.employee_name,
                        lr.biometric_id,
                        lr.check_in_local,
                        ((lr.shift_start_src AT TIME ZONE 'UTC') AT TIME ZONE '{FIXED_DEVICE_TIMEZONE_NAME}')::time AS shift_start_local_time,
                        date_trunc('day', lr.check_in_local)
                            + (((lr.shift_start_src AT TIME ZONE 'UTC') AT TIME ZONE '{FIXED_DEVICE_TIMEZONE_NAME}')::time) AS expected_check_in_local,
                        CASE
                            WHEN lr.punctuality_status = 'absence' THEN 480
                            ELSE GREATEST(
                                FLOOR(EXTRACT(EPOCH FROM (lr.check_in_local - (
                                    date_trunc('day', lr.check_in_local)
                                    + (((lr.shift_start_src AT TIME ZONE 'UTC') AT TIME ZONE '{FIXED_DEVICE_TIMEZONE_NAME}')::time)
                                ))) / 60.0),
                                0
                            )::int
                        END AS late_minutes
                    FROM late_rows lr
                    WHERE lr.punctuality_status = 'absence' OR lr.shift_start_src IS NOT NULL
                ),
                enriched AS (
                    SELECT
                        n.*,
                        (
                            n.check_in_local::date
                            + (((4 - EXTRACT(ISODOW FROM n.check_in_local)::int + 7) % 7) * INTERVAL '1 day')
                        )::date AS week_end_thursday,
                        (
                            (
                                n.check_in_local::date
                                + (((4 - EXTRACT(ISODOW FROM n.check_in_local)::int + 7) % 7) * INTERVAL '1 day')
                            )::date - INTERVAL '6 day'
                        )::date AS week_start_friday
                    FROM normalized n
                    WHERE n.late_minutes > 0
                ),
                per_day AS (
                    SELECT
                        e.employee_id,
                        e.company_id,
                        MAX(e.employee_name) AS employee_name,
                        MAX(e.biometric_id) AS biometric_id,
                        e.week_start_friday,
                        e.week_end_thursday,
                        e.check_in_local::date AS late_date,
                        MAX(e.late_minutes)::int AS late_minutes
                    FROM enriched e
                    GROUP BY
                        e.employee_id,
                        e.company_id,
                        e.week_start_friday,
                        e.week_end_thursday,
                        e.check_in_local::date
                ),
                grouped AS (
                    SELECT
                        d.employee_id,
                        d.company_id,
                        MAX(d.employee_name) AS employee_name,
                        MAX(d.biometric_id) AS biometric_id,
                        EXTRACT(ISOYEAR FROM d.week_end_thursday)::int AS custom_year,
                        EXTRACT(WEEK FROM d.week_end_thursday)::int AS custom_week,
                        d.week_start_friday AS week_start_date,
                        d.week_end_thursday AS week_end_date,
                        SUM(CASE WHEN d.late_date = d.week_start_friday THEN d.late_minutes ELSE 0 END)::int AS day_1_minutes,
                        SUM(CASE WHEN d.late_date = (d.week_start_friday + INTERVAL '1 day')::date THEN d.late_minutes ELSE 0 END)::int AS day_2_minutes,
                        SUM(CASE WHEN d.late_date = (d.week_start_friday + INTERVAL '2 day')::date THEN d.late_minutes ELSE 0 END)::int AS day_3_minutes,
                        SUM(CASE WHEN d.late_date = (d.week_start_friday + INTERVAL '3 day')::date THEN d.late_minutes ELSE 0 END)::int AS day_4_minutes,
                        SUM(CASE WHEN d.late_date = (d.week_start_friday + INTERVAL '4 day')::date THEN d.late_minutes ELSE 0 END)::int AS day_5_minutes,
                        SUM(CASE WHEN d.late_date = (d.week_start_friday + INTERVAL '5 day')::date THEN d.late_minutes ELSE 0 END)::int AS day_6_minutes,
                        SUM(CASE WHEN d.late_date = (d.week_start_friday + INTERVAL '6 day')::date THEN d.late_minutes ELSE 0 END)::int AS day_7_minutes,
                        COUNT(*)::int AS late_days_count,
                        STRING_AGG(TO_CHAR(d.late_date, 'DD/MM/YYYY'), ', ' ORDER BY d.late_date) AS late_dates_text,
                        SUM(d.late_minutes)::int AS total_late_minutes
                    FROM per_day d
                    GROUP BY
                        d.employee_id,
                        d.company_id,
                        EXTRACT(ISOYEAR FROM d.week_end_thursday),
                        EXTRACT(WEEK FROM d.week_end_thursday),
                        d.week_start_friday,
                        d.week_end_thursday
                ),
                with_adjustments AS (
                    SELECT
                        g.*,
                        adj.manual_total_late_minutes,
                        adj.manual_daily_minutes_json,
                        adj.manual_payable_days,
                        (
                            '[' || g.day_1_minutes || ',' || g.day_2_minutes || ',' || g.day_3_minutes || ',' ||
                            g.day_4_minutes || ',' || g.day_5_minutes || ',' || g.day_6_minutes || ',' || g.day_7_minutes || ']'
                        ) AS base_daily_minutes_json,
                        COALESCE(adj.manual_daily_minutes_json,
                            '[' || g.day_1_minutes || ',' || g.day_2_minutes || ',' || g.day_3_minutes || ',' ||
                            g.day_4_minutes || ',' || g.day_5_minutes || ',' || g.day_6_minutes || ',' || g.day_7_minutes || ']'
                        ) AS applied_daily_minutes_json,
                        COALESCE(
                            (
                                SELECT SUM(value::int)
                                FROM jsonb_array_elements_text(adj.manual_daily_minutes_json::jsonb) AS value
                            ),
                            adj.manual_total_late_minutes,
                            g.total_late_minutes
                        )::int AS applied_total_late_minutes
                    FROM grouped g
                    LEFT JOIN attendance_late_weekly_adjustment adj
                        ON adj.employee_id = g.employee_id
                        AND adj.custom_year = g.custom_year
                        AND adj.custom_week = g.custom_week
                ),
                current_week AS (
                    SELECT
                        EXTRACT(ISOYEAR FROM (
                            ((NOW() AT TIME ZONE '{FIXED_DEVICE_TIMEZONE_NAME}')::date)
                            + (((4 - EXTRACT(ISODOW FROM (NOW() AT TIME ZONE '{FIXED_DEVICE_TIMEZONE_NAME}'))::int + 7) % 7) * INTERVAL '1 day')
                        ))::int AS current_custom_year,
                        EXTRACT(WEEK FROM (
                            ((NOW() AT TIME ZONE '{FIXED_DEVICE_TIMEZONE_NAME}')::date)
                            + (((4 - EXTRACT(ISODOW FROM (NOW() AT TIME ZONE '{FIXED_DEVICE_TIMEZONE_NAME}'))::int + 7) % 7) * INTERVAL '1 day')
                        ))::int AS current_custom_week
                )
                SELECT
                    ROW_NUMBER() OVER (ORDER BY wa.custom_year DESC, wa.custom_week DESC, wa.employee_name ASC, wa.employee_id) AS id,
                    wa.employee_id,
                    wa.company_id,
                    wa.employee_name,
                    wa.biometric_id,
                    wa.custom_year,
                    wa.custom_week,
                    (wa.custom_year || ' - Semana ' || LPAD(wa.custom_week::text, 2, '0')) AS week_group_label,
                    ('Semana ' || wa.custom_week || ' (' || TO_CHAR(wa.week_start_date, 'DD/MM') || ' - ' || TO_CHAR(wa.week_end_date, 'DD/MM') || ')') AS week_label,
                    wa.week_start_date,
                    wa.week_end_date,
                    wa.late_days_count,
                    wa.late_dates_text,
                    wa.total_late_minutes AS base_total_late_minutes,
                    wa.applied_total_late_minutes AS total_late_minutes,
                    wa.base_daily_minutes_json,
                    wa.applied_daily_minutes_json AS daily_minutes_json,
                    FLOOR(wa.applied_total_late_minutes / 60.0)::int AS total_late_hours_floor,
                    ((wa.applied_total_late_minutes / 60.0) / 8.0)::numeric(16, 3) AS discount_days,
                    GREATEST(
                        ROUND((6 - ((wa.total_late_minutes / 60.0) / 8.0))::numeric, 2),
                        0
                    )::double precision AS base_payable_days,
                    COALESCE(
                        wa.manual_payable_days,
                        GREATEST(
                            ROUND((6 - ((wa.applied_total_late_minutes / 60.0) / 8.0))::numeric, 2),
                            0
                        )::double precision
                    ) AS payable_days,
                    (wa.manual_total_late_minutes IS NOT NULL OR wa.manual_payable_days IS NOT NULL) AS has_manual_override,
                    (
                        wa.custom_year > cw.current_custom_year
                        OR (wa.custom_year = cw.current_custom_year AND wa.custom_week > cw.current_custom_week)
                    ) AS is_future
                FROM with_adjustments wa
                CROSS JOIN current_week cw
            )
        """)
