# -*- coding: utf-8 -*-

from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


COUNT_ALL_DAYS_SHIFT_NAMES = {'ESPECIAL', 'SEGURIDAD'}


class HrVacation(models.Model):
    _name = 'hr.vacation'
    _description = 'Vacaciones de Empleado'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_from desc, id desc'

    name = fields.Char(
        string='Referencia',
        copy=False,
        readonly=True,
        default=lambda self: _('Nueva'),
        tracking=True,
    )

    employee_id = fields.Many2one(
        'hr.employee',
        string='Empleado',
        required=True,
        tracking=True,
        index=True,
    )

    biometric_id = fields.Char(
        string='Número de Empleado',
        related='employee_id.biometric_id',
        store=True,
        readonly=True,
    )

    employee_name = fields.Char(
        string='Nombre del Empleado',
        related='employee_id.name',
        store=True,
        readonly=True,
    )

    department_id = fields.Many2one(
        'hr.department',
        string='Departamento',
        related='employee_id.department_id',
        store=True,
        readonly=True,
    )

    turno_id = fields.Many2one(
        'shift.management',
        string='Turno',
        related='employee_id.turno_id',
        store=True,
        readonly=True,
    )

    expedient_id = fields.Many2one(
        'employee.expedient',
        string='Expediente',
        compute='_compute_expedient_id',
        store=True,
        readonly=True,
        help='Último expediente encontrado para el empleado.',
    )

    request_mode = fields.Selection(
        [
            ('range', 'Rango'),
            ('days', 'Por Días'),
        ],
        string='Modo',
        default='range',
        required=True,
        tracking=True,
    )

    supervisor_id = fields.Many2one(
        'res.users',
        string='Supervisor',
        tracking=True,
        help='Supervisor asignado (del grupo Supervisor Tiempo Extra)',
    )

    registered_by_id = fields.Many2one(
        'res.users',
        string='Registrado Por',
        default=lambda self: self.env.user,
        readonly=True,
        tracking=True,
    )

    company_id = fields.Many2one(
        'res.company',
        string='Compañía',
        default=lambda self: self.env.company,
        required=True,
    )

    date_from = fields.Date(
        string='Fecha Inicio',
        tracking=True,
        default=fields.Date.today,
    )

    date_to = fields.Date(
        string='Fecha Fin',
        tracking=True,
    )

    requested_day_ids = fields.One2many(
        'hr.vacation.requested.day',
        'vacation_id',
        string='Días Solicitados',
        copy=True,
    )

    vacation_modality = fields.Selection(
        [
            ('gozadas', 'Gozadas'),
            ('pagadas', 'Pagadas'),
            ('ambos', 'Ambos'),
        ],
        string='Modalidad',
        default='gozadas',
        tracking=True,
        help='Modalidad de la solicitud de vacaciones',
    )

    periodo = fields.Integer(
        string='Periodo',
        tracking=True,
        help='Años de antigüedad usados para calcular los días correspondientes.',
    )

    dias_correspondientes = fields.Float(
        string='Días Correspondientes',
        compute='_compute_dias_correspondientes',
        store=True,
        help='Días de vacaciones que corresponden según el periodo capturado.',
    )

    vacation_days_subtracted = fields.Boolean(
        string='Días Descontados',
        default=False,
        copy=False,
        help='Indica si esta vacación ya descontó días en el expediente.',
    )

    duration_days = fields.Float(
        string='Duración (Días)',
        compute='_compute_duration',
        inverse='_inverse_duration_days',
        store=True,
        help='Duración en días de las vacaciones',
    )

    paid_duration_days = fields.Float(
        string='Duración Manual Pagadas',
        default=0.0,
        copy=True,
        help='Duración capturada manualmente cuando la modalidad es Pagadas.',
    )

    vacation_days_available = fields.Float(
        string='Días Disponibles',
        related='expedient_id.dias_vacaciones_disponibles',
        store=True,
        readonly=True,
        help='Días de vacaciones disponibles al momento de la solicitud',
    )

    employee_antiguedad = fields.Char(
        string='Antigüedad',
        related='expedient_id.antiguedad',
        store=True,
        readonly=True,
        help='Antigüedad del empleado al momento de la solicitud',
    )

    description = fields.Text(
        string='Descripción',
        tracking=True,
    )

    leave_id = fields.Many2one(
        'hr.leave',
        string='Ausencia Relacionada',
        readonly=True,
        help='Ausencia de tipo Vacaciones que creó este registro',
    )

    state = fields.Selection([
        ('draft', 'Borrador'),
        ('confirm', 'Confirmado'),
        ('validate1', 'Primera Aprobación'),
        ('validate', 'Aprobado'),
        ('refuse', 'Rechazado'),
        ('cancel', 'Cancelado'),
    ], string='Estado', default='draft', tracking=True, required=True)

    @api.depends('employee_id')
    def _compute_expedient_id(self):
        for record in self:
            expedient = self.env['employee.expedient'].search([
                ('employee_id', '=', record.employee_id.id),
            ], order='fecha_movimiento desc', limit=1) if record.employee_id else False
            record.expedient_id = expedient.id if expedient else False

    @api.depends('periodo')
    def _compute_dias_correspondientes(self):
        for record in self:
            record.dias_correspondientes = self.env['employee.expedient']._get_vacation_days_for_period(
                record.periodo
            )

    def _get_employee_defaults_from_expedient(self, employee):
        defaults = {
            'periodo': 0,
            'dias_correspondientes': 0.0,
        }
        if not employee:
            return defaults

        expedient = self.env['employee.expedient'].search([
            ('employee_id', '=', employee.id),
        ], order='fecha_movimiento desc', limit=1)

        if not expedient:
            return defaults

        years = 0
        if expedient.fecha_movimiento:
            years = relativedelta(date.today(), expedient.fecha_movimiento).years

        defaults['periodo'] = max(years, 0)
        defaults['dias_correspondientes'] = self.env['employee.expedient']._get_vacation_days_for_period(
            defaults['periodo']
        )
        return defaults

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        default_employee_id = res.get('employee_id') or self.env.context.get('default_employee_id')
        if not default_employee_id:
            return res

        employee = self.env['hr.employee'].browse(default_employee_id)
        if not employee.exists():
            return res

        defaults = self._get_employee_defaults_from_expedient(employee)
        if 'periodo' in fields_list and not res.get('periodo'):
            res['periodo'] = defaults['periodo']
        if 'dias_correspondientes' in fields_list and not res.get('dias_correspondientes'):
            res['dias_correspondientes'] = defaults['dias_correspondientes']
        return res

    @api.onchange('employee_id')
    def _onchange_employee_id_defaults(self):
        for record in self:
            if not record.employee_id:
                continue
            defaults = record._get_employee_defaults_from_expedient(record.employee_id)
            record.periodo = defaults['periodo']
            record.dias_correspondientes = defaults['dias_correspondientes']

    def _counts_all_days_for_shift(self):
        self.ensure_one()
        shift_name = (self.turno_id.turno_name or '').strip().upper() if self.turno_id else ''
        return shift_name in COUNT_ALL_DAYS_SHIFT_NAMES

    def _is_workday_for_shift(self, current_date):
        self.ensure_one()
        if self._counts_all_days_for_shift():
            return True

        shift = self.turno_id
        if not shift:
            return True

        day_map = {
            0: 'work_monday',
            1: 'work_tuesday',
            2: 'work_wednesday',
            3: 'work_thursday',
            4: 'work_friday',
            5: 'work_saturday',
            6: 'work_sunday',
        }
        field_name = day_map.get(current_date.weekday())
        return bool(field_name and getattr(shift, field_name, False))

    def _get_public_holiday_dates(self, date_from, date_to):
        """Días festivos (asueto de empresa) que caen dentro del rango dado.

        Se toman de resource.calendar.leaves (Días Festivos globales de Odoo),
        filtrados por la compañía y el calendario de trabajo del empleado.
        """
        self.ensure_one()
        if not date_from or not date_to:
            return set()

        company = self.company_id or self.env.company
        calendar = self.employee_id.resource_calendar_id

        domain = [
            ('resource_id', '=', False),
            ('company_id', 'in', [company.id, False]),
            ('date_from', '<=', datetime.combine(date_to, datetime.max.time())),
            ('date_to', '>=', datetime.combine(date_from, datetime.min.time())),
        ]
        if calendar:
            domain += ['|', ('calendar_id', '=', calendar.id), ('calendar_id', '=', False)]

        holiday_dates = set()
        for leave in self.env['resource.calendar.leaves'].search(domain):
            current = leave.date_from.date()
            end = leave.date_to.date()
            while current <= end:
                if date_from <= current <= date_to:
                    holiday_dates.add(current)
                current += timedelta(days=1)
        return holiday_dates

    @api.depends(
        'request_mode',
        'vacation_modality',
        'periodo',
        'dias_correspondientes',
        'paid_duration_days',
        'date_from',
        'date_to',
        'requested_day_ids.requested_date',
        'turno_id',
        'turno_id.turno_name',
        'turno_id.work_monday',
        'turno_id.work_tuesday',
        'turno_id.work_wednesday',
        'turno_id.work_thursday',
        'turno_id.work_friday',
        'turno_id.work_saturday',
        'turno_id.work_sunday',
    )
    def _compute_duration(self):
        for record in self:
            if record.vacation_modality == 'pagadas':
                record.duration_days = max(record.paid_duration_days, 0.0)
                continue

            if record.request_mode == 'days':
                selected_dates = sorted({line.requested_date for line in record.requested_day_ids if line.requested_date})
                if not selected_dates:
                    record.duration_days = 0.0
                    continue

                holiday_dates = record._get_public_holiday_dates(selected_dates[0], selected_dates[-1])
                count = 0.0
                for requested_date in selected_dates:
                    if requested_date in holiday_dates:
                        continue
                    if record._is_workday_for_shift(requested_date):
                        count += 1.0
                record.duration_days = count
                continue

            if not record.date_from or not record.date_to:
                record.duration_days = 0.0
                continue

            if record.date_to < record.date_from:
                raise ValidationError(_('La fecha de fin no puede ser anterior a la fecha de inicio.'))

            holiday_dates = record._get_public_holiday_dates(record.date_from, record.date_to)

            if record._counts_all_days_for_shift():
                total_days = (record.date_to - record.date_from).days + 1
                record.duration_days = max(total_days - len(holiday_dates), 0.0)
                continue

            count = 0.0
            current_date = record.date_from
            while current_date <= record.date_to:
                if current_date not in holiday_dates and record._is_workday_for_shift(current_date):
                    count += 1.0
                current_date += timedelta(days=1)
            record.duration_days = count

    def _inverse_duration_days(self):
        for record in self:
            if record.vacation_modality == 'pagadas':
                record.paid_duration_days = max(record.duration_days or 0.0, 0.0)

    @api.onchange('request_mode', 'requested_day_ids')
    def _onchange_request_mode_requested_days(self):
        for record in self:
            if record.request_mode == 'days':
                selected_dates = sorted({line.requested_date for line in record.requested_day_ids if line.requested_date})
                record.date_from = selected_dates[0] if selected_dates else False
                record.date_to = selected_dates[-1] if selected_dates else False

    @api.constrains('request_mode', 'vacation_modality', 'date_from', 'date_to', 'requested_day_ids')
    def _check_request_mode(self):
        for record in self:
            if record.state == 'draft':
                continue

            if record.vacation_modality == 'pagadas':
                continue

            if record.request_mode == 'range':
                if not record.date_from or not record.date_to:
                    raise ValidationError(_('En modo Rango debe capturar fecha de inicio y fecha de fin.'))
                if record.date_to < record.date_from:
                    raise ValidationError(_('La fecha de fin no puede ser anterior a la fecha de inicio.'))
            elif record.request_mode == 'days' and not record.requested_day_ids:
                raise ValidationError(_('En modo Por Días debe seleccionar al menos un día.'))

    def action_open_requested_days_calendar(self):
        self.ensure_one()
        return {
            'name': _('Días Solicitados'),
            'type': 'ir.actions.act_window',
            'res_model': 'hr.vacation.requested.day',
            'view_mode': 'calendar,list,form',
            'domain': [('vacation_id', '=', self.id)],
            'context': {
                'default_vacation_id': self.id,
                'default_company_id': self.company_id.id,
            },
            'target': 'current',
        }

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            employee_id = vals.get('employee_id')
            if employee_id:
                employee = self.env['hr.employee'].browse(employee_id)
                if employee.exists():
                    defaults = self._get_employee_defaults_from_expedient(employee)
                    if not vals.get('periodo'):
                        vals['periodo'] = defaults['periodo']
                    if not vals.get('dias_correspondientes'):
                        vals['dias_correspondientes'] = defaults['dias_correspondientes']

            if vals.get('name', _('Nueva')) == _('Nueva'):
                vals['name'] = self.env['ir.sequence'].next_by_code('hr.vacation') or _('Nueva')
        vacations = super(HrVacation, self).create(vals_list)
        vacations.filtered(lambda v: v.state == 'validate' and not v.vacation_days_subtracted)._apply_vacation_discount()
        return vacations

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for record in self:
            if record.vacation_modality == 'pagadas':
                continue
            if record.date_from and record.date_to and record.date_to < record.date_from:
                raise ValidationError(_('La fecha de fin debe ser posterior a la fecha de inicio.'))

    def _apply_vacation_discount(self):
        for record in self:
            if record.leave_id or record.vacation_days_subtracted or record.state != 'validate':
                continue
            if not record.expedient_id:
                raise ValidationError(_(
                    'No se encontró un expediente activo para el empleado %s.'
                ) % (record.employee_id.name or ''))
            if record.duration_days <= 0:
                raise ValidationError(_('La vacación debe tener al menos 1 día para descontar saldo.'))

            new_used_days = record.expedient_id.dias_vacaciones_utilizados + record.duration_days
            record.expedient_id.write({'dias_vacaciones_utilizados': new_used_days})
            record.with_context(skip_vacation_balance_sync=True).write({'vacation_days_subtracted': True})

    def _revert_vacation_discount(self):
        for record in self:
            if record.leave_id or not record.vacation_days_subtracted:
                continue
            if not record.expedient_id:
                continue

            new_used_days = max(record.expedient_id.dias_vacaciones_utilizados - record.duration_days, 0.0)
            record.expedient_id.write({'dias_vacaciones_utilizados': new_used_days})
            record.with_context(skip_vacation_balance_sync=True).write({'vacation_days_subtracted': False})

    def write(self, vals):
        res = super(HrVacation, self).write(vals)

        if self.env.context.get('skip_vacation_balance_sync'):
            return res

        for record in self:
            if record.state == 'validate' and not record.vacation_days_subtracted:
                record._apply_vacation_discount()
            elif record.state in ['draft', 'refuse', 'cancel'] and record.vacation_days_subtracted:
                record._revert_vacation_discount()
        return res

    def action_draft(self):
        self.write({'state': 'draft'})

    def action_reset_approved_to_draft(self):
        """Allow reverting approved vacations back to draft.

        The write flow already restores deducted days when state moves to draft.
        """
        self.filtered(lambda r: r.state in ['validate', 'validate1']).write({'state': 'draft'})

    def action_confirm(self):
        self.write({'state': 'confirm'})

    def action_validate(self):
        self.write({'state': 'validate'})

    def action_refuse(self):
        self.write({'state': 'refuse'})

    def action_cancel(self):
        self.write({'state': 'cancel'})

    def action_open_leave(self):
        self.ensure_one()
        if self.leave_id:
            return {
                'name': 'Solicitud de Vacaciones',
                'type': 'ir.actions.act_window',
                'res_model': 'hr.leave',
                'res_id': self.leave_id.id,
                'view_mode': 'form',
                'target': 'current',
            }


class HrVacationRequestedDay(models.Model):
    _name = 'hr.vacation.requested.day'
    _description = 'Días Solicitados de Vacaciones'
    _order = 'requested_date asc, id asc'

    vacation_id = fields.Many2one(
        'hr.vacation',
        string='Vacación',
        required=True,
        ondelete='cascade',
    )

    company_id = fields.Many2one(
        related='vacation_id.company_id',
        store=True,
        readonly=True,
    )

    requested_date = fields.Date(
        string='Fecha',
        required=True,
        index=True,
    )

    name = fields.Char(
        string='Referencia',
        compute='_compute_name',
        store=True,
    )

    day_name = fields.Char(
        string='Día',
        compute='_compute_day_name',
        store=False,
    )

    @api.depends('requested_date', 'vacation_id.name')
    def _compute_name(self):
        for record in self:
            if record.requested_date:
                record.name = '%s - %s' % (
                    record.vacation_id.name or _('Vacación'),
                    record.requested_date.strftime('%Y-%m-%d'),
                )
            else:
                record.name = record.vacation_id.name or _('Día solicitado')

    @api.depends('requested_date')
    def _compute_day_name(self):
        weekday_labels = [
            _('Lunes'),
            _('Martes'),
            _('Miércoles'),
            _('Jueves'),
            _('Viernes'),
            _('Sábado'),
            _('Domingo'),
        ]
        for record in self:
            if record.requested_date:
                record.day_name = weekday_labels[record.requested_date.weekday()]
            else:
                record.day_name = False

    @api.onchange('requested_date')
    def _onchange_requested_date(self):
        for record in self:
            if record.requested_date and (not record.name or record.name == _('Nueva')):
                record.name = record.requested_date.strftime('%Y-%m-%d')

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        requested_date = res.get('requested_date') or self.env.context.get('default_requested_date') or self.env.context.get('date_start') or self.env.context.get('default_date_start')
        if requested_date and not res.get('name'):
            requested_date_value = fields.Date.to_date(requested_date)
            if requested_date_value:
                res['name'] = requested_date_value.strftime('%Y-%m-%d')
        return res
