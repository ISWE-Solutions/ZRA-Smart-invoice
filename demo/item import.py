class ImportItem(models.Model):
    _name = 'import.item'
    _description = 'Import Item'

    import_id = fields.Many2one('import.data', string='Import ID')
    item_seq = fields.Integer(string='Item Sequence')
    hs_cd = fields.Char(string='HS Code')
    item_nm = fields.Char(string='Item Name')
    confirmed_qty = fields.Float(string='Confirmed Quantity', default=0.0)
    pkg = fields.Integer(string='Package')
    pkg_unit_cd = fields.Char(string='Package Unit Code')
    qty = fields.Integer(string=' Accepted Quantity')
    fetched_qty = fields.Integer(string='Received Quantity')
    qty_unit_cd = fields.Char(string='Quantity Unit Code')
    orgn_nat_cd = fields.Char(string="Original Country Code")
    expt_nat_cd = fields.Char(string="Expected Country Code")
    tot_wt = fields.Float(string='Total Weight')
    net_wt = fields.Float(string='Net Weight')
    agnt_nm = fields.Char(string='Agent Name')
    invc_fcur_amt = fields.Float(string='Invoice Foreign Currency Amount')
    remark = fields.Text(string='Remark')
    item_cd = fields.Char(string='Item Code')
    task_cd = fields.Char(string='Task Code')
    classification = fields.Many2one(
        'zra.item.data',
        string='Item Classification',
        required=False
    )
    item_cls_cd = fields.Char(string='Item Classification Code', readonly=False, store=True)
    item_cls_lvl = fields.Integer(string='Item Classification Level', readonly=True, store=True)
    tax_ty_cd = fields.Char(string='Tax Type Code', readonly=True, store=True)
    mjr_tg_yn = fields.Char(string='Major Target', readonly=True, store=True)
    use_yn = fields.Char(string='Use', readonly=True, store=True)

    @api.onchange('classification')
    def _onchange_classification(self):
        if self.classification:
            self.item_cls_cd = self.classification.itemClsCd
            self.item_cls_lvl = self.classification.itemClsLvl
            self.tax_ty_cd = self.classification.taxTyCd
            self.mjr_tg_yn = self.classification.mjrTgYn
            self.use_yn = self.classification.useYn
        else:
            self.item_cls_cd = False
            self.item_cls_lvl = False
            self.tax_ty_cd = False
            self.mjr_tg_yn = False
            self.use_yn = False

    @api.model
    def _find_product_classification(self, item_name, item_cd):
        product = self.env['product.template'].search([
            ('name', '=', item_name),
            ('item_cd', '=', item_cd)
        ], limit=1)
        return product.classification if product else False

    @api.model
    def create(self, vals):
        if not vals.get('classification'):
            classification = self._find_product_classification(vals.get('item_nm'), vals.get('item_cd'))
            if classification:
                vals['classification'] = classification.id

        if 'classification' in vals:
            classification = self.env['zra.item.data'].browse(vals['classification'])
            if classification.exists():
                vals.update({
                    'item_cls_cd': classification.itemClsCd,
                    'item_cls_lvl': classification.itemClsLvl,
                    'tax_ty_cd': classification.taxTyCd,
                    'mjr_tg_yn': classification.mjrTgYn,
                    'use_yn': classification.useYn
                })

        res = super(ImportItem, self).create(vals)
        return res

    def write(self, vals):
        if not vals.get('classification'):
            classification = self._find_product_classification(self.item_nm, self.item_cd)
            if classification:
                vals['classification'] = classification.id

        if 'classification' in vals:
            classification = self.env['zra.item.data'].browse(vals['classification'])
            if classification.exists():
                vals.update({
                    'item_cls_cd': classification.itemClsCd,
                    'item_cls_lvl': classification.itemClsLvl,
                    'tax_ty_cd': classification.taxTyCd,
                    'mjr_tg_yn': classification.mjrTgYn,
                    'use_yn': classification.useYn
                })

        res = super(ImportItem, self).write(vals)
        return res

    @api.constrains('qty')
    def _check_qty(self):
        for record in self:
            if record.qty < 0:
                raise ValidationError("Accepted Quantity cannot be less than 0.")
            if record.qty > record.fetched_qty:
                raise ValidationError("Accepted Quantity cannot be greater than Received Quantity.")

    @api.depends('import_id.item_list')
    def _compute_confirmed_qty(self):
        for item in self:
            item.confirmed_qty = item.qty
