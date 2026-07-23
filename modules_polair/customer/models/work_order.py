from odoo import api, fields, models


class CustomerWorkOrder(models.Model):
    _name = 'customer.work.order'
    _description = 'Orden de Trabajo'
    _order = 'id desc'

    name = fields.Char(string='Orden', required=True, copy=False, default='Nueva')

    partner_id = fields.Many2one('res.partner', string='Cliente', required=True)
    partner_contact = fields.Char(string='Tel. / Contacto')
    partner_city = fields.Char(string='Ciudad', related='partner_id.city', readonly=True)
    partner_street = fields.Char(string='Direccion', related='partner_id.street', readonly=True)
    work_description = fields.Char(string='Trabajo a realizar')
    area = fields.Char(string='Area')
    technician_id = fields.Many2one('hr.employee', string='Tecnico')

    unit_name = fields.Char(string='Unidad')
    equipment_brand = fields.Char(string='Marca')
    equipment_model = fields.Char(string='Modelo')
    equipment_serial = fields.Char(string='Serie')
    equipment_status = fields.Char(string='Estatus del equipo')

    checklist_filter_cleaning = fields.Boolean(string='Limpieza de filtro')
    checklist_condenser_cleaning = fields.Boolean(string='Limpieza de condensador')
    checklist_motor_cleaning = fields.Boolean(string='Limpieza de motores')
    checklist_injection_temp = fields.Boolean(string='Temp. de inyeccion')
    checklist_summer_service = fields.Boolean(string='Servicio general de verano')
    checklist_leak_fix = fields.Boolean(string='Correccion de fugas')
    checklist_fuse_change = fields.Boolean(string='Cambio de fusibles')
    checklist_duct_insulation = fields.Boolean(string='Aislamiento de ductos')
    checklist_refrigerant_charge = fields.Boolean(string='Carga total o parcial refrigerante')
    checklist_capacitor_issues = fields.Boolean(string='Se observa problemas de capacitor')

    checklist_evaporator_cleaning = fields.Boolean(string='Limpieza de evaporador')
    checklist_outdoor_cleaning = fields.Boolean(string='Limpieza exterior de unidad')
    checklist_motor_lubrication = fields.Boolean(string='Lubricacion de motores')
    checklist_system_wash = fields.Boolean(string='Lavado de sistema')
    checklist_pipe_insulation = fields.Boolean(string='Aislamiento de tuberia')
    checklist_electric_controls = fields.Boolean(string='Revision controles electricos')
    checklist_belt_tension = fields.Boolean(string='Tension de bandas')
    checklist_compressor_change = fields.Boolean(string='Cambio de compresor')
    checklist_unit_efficiency = fields.Boolean(string='Eficiencia de la unidad')

    correction_notes = fields.Text(string='Describa correcciones adicionales')
    materials_used = fields.Text(string='Liste los materiales utilizados')

    psi_low_circuit_1 = fields.Float(string='Baja circuito 1 (PSI)')
    psi_low_circuit_2 = fields.Float(string='Baja circuito 2 (PSI)')
    psi_high_circuit_1 = fields.Float(string='Alta circuito 1 (PSI)')
    psi_high_circuit_2 = fields.Float(string='Alta circuito 2 (PSI)')

    temp_superheat = fields.Float(string='Sobrecalentamiento (C)')
    temp_subcooling = fields.Float(string='Subenfriamiento (C)')
    amp_plate = fields.Float(string='Amp. placa (Amp)')

    voltage_l1_l2 = fields.Float(string='L1-L2 (V)')
    voltage_l2_l3 = fields.Float(string='L2-L3 (V)')
    voltage_l1_l3 = fields.Float(string='L1-L3 (V)')

    amp_general_l1 = fields.Float(string='L1 (A)')
    amp_general_l2 = fields.Float(string='L2 (A)')
    amp_general_l3 = fields.Float(string='L3 (A)')

    amp_comp_1_l1 = fields.Float(string='L1 (A)')
    amp_comp_1_l2 = fields.Float(string='L2 (A)')
    amp_comp_1_l3 = fields.Float(string='L3 (A)')

    amp_comp_2_l1 = fields.Float(string='L1 (A)')
    amp_comp_2_l2 = fields.Float(string='L2 (A)')
    amp_comp_2_l3 = fields.Float(string='L3 (A)')

    amp_blower_l1 = fields.Float(string='L1 (A)')
    amp_blower_l2 = fields.Float(string='L2 (A)')
    amp_blower_l3 = fields.Float(string='L3 (A)')

    amp_cond_motor_1_l1 = fields.Float(string='L1 (A)')
    amp_cond_motor_1_l2 = fields.Float(string='L2 (A)')

    amp_cond_motor_23_mc2_l1 = fields.Float(string='MC2 L1 (A)')
    amp_cond_motor_23_mc2_l2 = fields.Float(string='MC2 L2 (A)')
    amp_cond_motor_23_mc3_l1 = fields.Float(string='MC3 L1 (A)')
    amp_cond_motor_23_mc3_l2 = fields.Float(string='MC3 L2 (A)')

    @api.model_create_multi
    def create(self, vals_list):
        sequence = self.env['ir.sequence']
        for vals in vals_list:
            if vals.get('name', 'Nueva') == 'Nueva':
                vals['name'] = sequence.next_by_code('customer_polair.work.order') or 'Nueva'
        return super().create(vals_list)

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        for record in self:
            if not record.partner_id:
                record.partner_contact = False
                continue
            record.partner_contact = record.partner_id.phone or record.partner_id.email or False
