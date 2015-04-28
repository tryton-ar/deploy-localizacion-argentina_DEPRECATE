#!/usr/bin/env python2
# -*- encoding: utf-8 -*-

# Imports
import os
from optparse import OptionParser
import datetime
from psycopg2 import connect
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import trytond
from proteus import Model, Wizard
from proteus import config as pconfig
from dateutil.relativedelta import relativedelta
today = datetime.date.today()


class Bunch(object):
  def __init__(self, adict):
    self.__dict__.update(adict)


def main(options):

    # create database
    print u'\n>>> creando database...'
    con = connect(user='tryton', dbname='template1', password='tryton', host=options.host)
    con.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = con.cursor()
    cur.execute('CREATE DATABASE %s' % options.database + ' WITH ENCODING = \'UTF8\'')
    cur.close()
    con.close()

    # init database
    print u'\n>>> inicializando...'
    os.environ["TRYTONPASSFILE"] = 'trytonpass'
    toptions = {
        'configfile': options.config_file,
        'database_names': [options.database],
        'update': ['ir'],
        'logconf': None,
        'pidfile': None,
        }
    try:
        trytond.server.TrytonServer(Bunch(toptions)).run()
    except SystemExit:
        pass

    config = pconfig.set_trytond(options.database, config_file=options.config_file, language='es_AR')

    Lang = Model.get('ir.lang')
    (es_AR,) = Lang.find([('code', '=', 'es_AR')])
    es_AR.translatable = True
    es_AR.save()

    try:
        trytond.server.TrytonServer(Bunch(toptions)).run()
    except SystemExit:
        pass

    install_modules()
    crear_scenario_tipo(config, es_AR)
    print "done."

def install_modules():
    print u'\n>>> instalando modulos...'
    Module = Model.get('ir.module.module')
    modules_to_install=[
        'account_ar',
        'company_logo',
        'account_invoice_ar',
        ]
    modules = Module.find([
        ('name', 'in', modules_to_install),
        ])
    for module in modules:
        module.click('install')
    Wizard('ir.module.module.install_upgrade').execute('upgrade')

    print u'\n>>> wizards de configuracion se marcan como done...'
    ConfigWizardItem = Model.get('ir.module.module.config_wizard.item')
    for item in ConfigWizardItem.find([('state', '!=', 'done')]):
        item.state = 'done'
        item.save()

def crear_scenario_tipo(config, lang):
    """ Crear el scenario base """
    Currency = Model.get('currency.currency')
    Company = Model.get('company.company')
    Party = Model.get('party.party')
    User = Model.get('res.user')
    #Group = Model.get('res.group')


    # crear company
    # obtener nombre de la compania de un archivo.
    print u'\n>>> creando company...'

    import ConfigParser
    config = ConfigParser.ConfigParser()
    config.read('company.ini')
    currencies = Currency.find([('code', '=', 'ARS')])
    currency, = currencies
    company_config = Wizard('company.company.config')
    company_config.execute('company')
    company = company_config.form
    party = Party(name=config['company']['name'])
    party.lang = lang

    party.vat_country = 'AR'
    party.vat_number = str(config['company']['cuit'])
    party.iva_condition = str(config['company']['iva_condition'])
    party.addresses.street = str(config['company']['direccion'])
    party.addresses.zip = str(config['company']['codigo_postal'])
    party.addresses.country = '191'
    party.addresses.city = str(config['company']['ciudad'])
    party.save()

    company.party = party
    company.currency = currency
    company_config.execute('add')
    company, = Company.find([])

    print u'\n>>> obtengo el logo de la company...'
    try:
        file_p = open('logo.jpg', 'rb')
        logo = buffer(file_p.read())
        print u'\n>>> configuro el logo de la company...'
        company.logo = logo
        company.save()
    except IOError:
        print u'\n>>> no encontre el archivo logo.jpg ...'

    # reload the context
    print u'\n>>> creando admin...'
    config._context = User.get_preferences(True, config.context)
    admin_user = User.find()[0]
    admin_user.password = 'admin'
    admin_user.main_company = company
    admin_user.language = lang
    admin_user.save()

    # create fiscal year:
    print u'\n>>> creando fiscal actual...'
    FiscalYear = Model.get('account.fiscalyear')
    Sequence = Model.get('ir.sequence')
    SequenceStrict = Model.get('ir.sequence.strict')
    fiscalyear = FiscalYear(name=str(today.year))
    fiscalyear.start_date = today + relativedelta(month=1, day=1)
    fiscalyear.end_date = today + relativedelta(month=12, day=31)
    fiscalyear.company = company
    post_move_seq = Sequence(name=str(today.year), code='account.move',
        company=company)
    post_move_seq.save()
    fiscalyear.post_move_sequence = post_move_seq
    invoice_seq = SequenceStrict(name=str(today.year),
        code='account.invoice', company=company)
    invoice_seq.save()
    fiscalyear.out_invoice_sequence = invoice_seq
    fiscalyear.in_invoice_sequence = invoice_seq
    fiscalyear.out_credit_note_sequence = invoice_seq
    fiscalyear.in_credit_note_sequence = invoice_seq
    fiscalyear.save()
    FiscalYear.create_period([fiscalyear.id], config.context)

    ## create chart of accounts::
    print u'\n>>> creando cuentas...'
    AccountTemplate = Model.get('account.account.template')
    Account = Model.get('account.account')
    Journal = Model.get('account.journal')
    account_template, = AccountTemplate.find(
      [('parent', '=', None),
       ('name', '=', 'Plan Contable Argentino para Cooperativas')]
    )
    create_chart = Wizard('account.create_chart')
    create_chart.execute('account')
    create_chart.form.account_template = account_template
    create_chart.form.company = company
    create_chart.execute('create_account')

    receivable, = Account.find([
            ('kind', '=', 'receivable'),
            ('code', '=', '1131'), # Deudores por servicios
            ('company', '=', company.id),
            ])
    payable, = Account.find([
            ('kind', '=', 'payable'),
            ('code', '=', '2111'), # Proveedores
            ('company', '=', company.id),
            ])
    revenue, = Account.find([
            ('kind', '=', 'revenue'),
            ('code', '=', '511'), # Ingresos por servicios realizados
            ('company', '=', company.id),
            ])
    expense, = Account.find([
            ('kind', '=', 'expense'),
            ('code', '=', '5249'), # Gastos Varios
            ('company', '=', company.id),
            ])
    #receivable, = Account.find([
    #        ('kind', '=', 'receivable'),
    #        ('code', '=', '11301'), # deudores por venta
    #        ('company', '=', company.id),
    #        ])
    #payable, = Account.find([
    #        ('kind', '=', 'payable'),
    #        ('code', '=', '21301'), # proveedores
    #        ('company', '=', company.id),
    #        ])
    #revenue, = Account.find([
    #        ('kind', '=', 'revenue'),
    #        ('code', '=', '41100'), # ingresos por venta
    #        ('company', '=', company.id),
    #        ])
    #expense, = Account.find([
    #        ('kind', '=', 'expense'),
    #        ('code', '=', '5119'), # gastos operativos en general
    #        ('company', '=', company.id),
    #        ])
    create_chart.form.account_receivable = receivable
    create_chart.form.account_payable = payable
    create_chart.execute('create_properties')
    cash, = Account.find([
            ('kind', '=', 'other'),
            ('name', '=', 'Caja pesos'),
            ('code', '=', '11101'),
            ('company', '=', company.id),
            ])
    cash_journal, = Journal.find([('type', '=', 'cash')])
    cash_journal.credit_account = cash
    cash_journal.debit_account = cash
    cash_journal.save()

    ## create payment term:
    print u'\n>>> creando terminos de pago...'
    PaymentTerm = Model.get('account.invoice.payment_term')
    PaymentTermLine = Model.get('account.invoice.payment_term.line')

    print u'\n>>> creando termino de pago 30 dias...'
    payment_term = PaymentTerm(name=u'30 días')
    payment_term_line = PaymentTermLine(type='remainder', days=30)
    payment_term.lines.append(payment_term_line)
    payment_term.save()

    print u'\n>>> creando termino de pago 60 dias...'
    payment_term = PaymentTerm(name=u'60 días')
    payment_term_line = PaymentTermLine(type='remainder', days=60)
    payment_term.lines.append(payment_term_line)
    payment_term.save()

    print u'\n>>> creando termino de pago Efectivo...'
    payment_term = PaymentTerm(name='Contado')
    payment_term_line = PaymentTermLine(type='remainder', days=0)
    payment_term.lines.append(payment_term_line)
    payment_term.save()


    # instalo modulo stock
    print u'\n>>> instalando stock...'
    Module = Model.get('ir.module.module')
    module, = Module.find([('name', '=', 'stock')])
    module.click('install')
    Wizard('ir.module.module.install_upgrade').execute('upgrade')

    config.user = admin_user.id
    Inventory = Model.get('stock.inventory')
    Location = Model.get('stock.location')
    storage, = Location.find([
            ('code', '=', 'STO'),
            ])
    inventory = Inventory()
    inventory.location = storage
    inventory.save()

    PartyConfig = Model.get('party.configuration')

    print u'\n>>> Idioma de la entidad por defecto es Spanish Argentina...'
    party_config = PartyConfig([])
    party_config.party_lang = lang
    party_config.save()

    print u'\n>>> Comienza configuracion_contable...'
    AccountConfiguration = Model.get('account.configuration')
    Account = Model.get('account.account')
    account_config, = AccountConfiguration.find([])
    account_config.default_account_receivable = receivable
    account_config.default_account_payable = payable
    account_config.save()

    print u'\n>>> scenario base done.'

if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option('-d', '--database', dest='database')
    parser.add_option('-c', '--config-file', dest='config_file')
    parser.add_option('-l', '--host', dest='host')
    parser.set_defaults(user='admin')

    options, args = parser.parse_args()
    if args:
        parser.error('Parametros incorrectos')
    if not options.database:
        parser.error('Se debe definir [nombre] de base de datos')
    if not options.config_file:
        parser.error(u'Se debe definir el path absoluto al archivo de configuración de trytond')
    if not options.host:
        parser.error(u'Debe definir host de conexión a base de datos Postgres')

    main(options)
