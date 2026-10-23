# -*- coding: utf-8 -*-
from odoo import models, fields, api


class EnfermeriaAccidente(models.Model):
    _name = 'enfermeria.accidente'
    _description = 'Registro de Incidente'
    _order = 'id desc'

    name = fields.Char(
        string='No. Reporte',
        readonly=True,
        copy=False,
        default='Nuevo',
    )

    tipo_registro = fields.Selection(
        selection=[
            ('accidente', 'Accidente'),
            ('incidente', 'Incidente'),
        ],
        string='Tipo de Registro',
        required=True,
        default='accidente',
    )

    company_id = fields.Many2one(
        'res.company',
        string='Empresa',
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )

    # NO. EMP — biometric_id del empleado (relacionado via hr.employee)
    employee_id = fields.Many2one(
        'hr.employee',
        string='Empleado',
        required=True,
        ondelete='restrict',
    )
    no_emp = fields.Char(
        string='No. EMP',
        related='employee_id.biometric_id',
        store=True,
        readonly=True,
    )
    supervisor_id = fields.Many2one(
        'employee.supervisor',
        string='Supervisor',
        domain="[('company_id', '=', company_id), ('active', '=', True)]",
        ondelete='restrict',
    )

    # Área del accidente — tomada del modelo hr.area del módulo overtime
    area_id = fields.Many2one(
        'hr.area',
        string='Área del Incidente',
    )

    tipo_causa = fields.Selection(
        selection=[
            ('acto_inseguro', 'Acto Inseguro'),
            ('condicion_insegura', 'Condición Insegura'),
            ('mixto', 'Mixto'),
        ],
        string='Tipo de Causa',
        required=True,
    )

    dia_accidente = fields.Date(
        string='Día del Incidente',
        required=True,
    )

    inicia_st7 = fields.Date(
        string='Inicia con S-T7',
    )

    cierre_st2 = fields.Date(
        string='Cierre con ST-2',
    )

    atencion = fields.Selection(
        selection=[
            ('imss', 'IMSS'),
            ('interno', 'Interno'),
            ('clinica', 'Clínica'),
        ],
        string='Atención',
        required=True,
    )

    riesgo_trabajo_imss = fields.Selection(
        selection=[
            ('si', 'Sí'),
            ('no', 'No'),
        ],
        string='Riesgo de Trabajo por IMSS',
        required=True,
    )

    dias_incapacidad = fields.Integer(
        string='Días de Incapacidad',
        default=0,
    )

    # incapacidad = fields.Integer(
    #     string='Incapacidad',
    #     default=0,
    #     help='0 representa N/A cuando no existe incapacidad.',
    # )

    descripcion_accidente = fields.Text(string='Descripción del Incidente')

    registrado_por = fields.Many2one(
        'res.users',
        string='Registrado por',
        domain=lambda self: [
            ('groups_id', 'in', [
                self.env.ref('maintenance_fruvemex.group_maintenance_seguridad_higiene').id,
            ])
        ],
        ondelete='restrict',
    )

    resultado_investigacion = fields.Text(string='Resultado de la investigación')

    parte_cuerpo_afectada = fields.Text(string='Parte del cuerpo afectada')

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        if self.employee_id.company_id:
            self.company_id = self.employee_id.company_id

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'Nuevo') == 'Nuevo':
                vals['name'] = self.env['ir.sequence'].next_by_code('enfermeria.accidente') or 'Nuevo'
        return super().create(vals_list)
