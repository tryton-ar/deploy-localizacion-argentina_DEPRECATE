#!/bin/bash

# Se loggea en /var/log/syslog
exec 1> >(logger -s -t $(basename $0)) 2>&1

# exit if using uninitialized variable
# set -u
# exit on error
# set -e

if [ "$1" == "-h" ]; then
  echo "Usage: `basename $0` -t 3.4 -c /etc/trytond.conf --database-host localhost"
  exit 0
fi

VERSION="3.4"
while [[ $# > 1 ]]
do
key="$1"

case $key in
    -t|--tag)
    VERSION="$2"
    shift
    ;;
    -c|--config-file)
    TRYTON_CONFIG_FILE="$2"
    shift
    ;;
    -d|--database-host)
    DATABASE_HOST="$2"
    shift
    ;;
    --default)
    DEFAULT=YES
    shift
    ;;
    *)
    # unknown option
    ;;
esac
shift
done

echo "---------------------------------------------------------"
echo "Comienza instalacion TRYTON Localizacion Argentina"
echo "---------------------------------------------------------"

#TRYTON_CONFIG_FILE="/etc/trytond.conf"
VIRTUALENV="tryton-localizacion-ar"
DATABASE="tryton_ar"

if [ -z "$VERSION" ]; then
    echo "Debemos definir que version de Tryton queremos instalar" >&2
    echo "Por defecto usamos la version: 3.4" >&2
    exit 1
fi


DATABASE_NAME=${DATABASE}_${VERSION}
DATABASE_NAME=${DATABASE_NAME//./_}
DATABASE_NAME=${DATABASE_NAME////_}

source `which virtualenvwrapper.sh`

if [ ! -e "$TRYTON_CONFIG_FILE" ]; then
    echo "El archivo de configuracion de trytond no existe $TRYTON_CONFIG_FILE" >&2
    exit 1
fi

echo "---------------------------------------------------------"
echo "Borramos virtualenv anteriormente creado"
echo "---------------------------------------------------------"
rmvirtualenv $VIRTUALENV
echo "---------------------------------------------------------"
echo "Creamos nuevo virtualenv"
echo "---------------------------------------------------------"
mkvirtualenv $VIRTUALENV -p `which python2`

echo "---------------------------------------------------------"
echo "Ingresamos al virtualenv"
echo "---------------------------------------------------------"
workon $VIRTUALENV
INSTALACION_ACTUAL=`pwd`

echo "---------------------------------------------------------"
echo "Comenzamos instalacion de paquetes pip"
echo "---------------------------------------------------------"
pip install -r requirements-trytond-$VERSION.txt

cdsitepackages
cd ../../../src
MODULES_EXTRA=`pwd`

echo "---------------------------------------------------------"
echo "Instalar pyafipws"
echo "---------------------------------------------------------"

wget https://github.com/reingart/pyafipws/archive/2.7.tar.gz 
tar zxvf 2.7.tar.gz
rm 2.7.tar.gz

echo "---------------------------------------------------------"
echo "Instalamos modulos locales en el virtualen"
echo "---------------------------------------------------------"

cdsitepackages
SITEPACKAGES=`pwd`
cd trytond/modules
MODULES_TRYTON=`pwd`

echo "---------------------------------------------------------"
echo "Creamos symbolic links de los modulos extras"
echo "---------------------------------------------------------"
ln -v -s $MODULES_EXTRA/account-ar $MODULES_TRYTON/account_ar
ln -v -s $MODULES_EXTRA/account-invoice-ar $MODULES_TRYTON/account_invoice_ar
ln -v -s $MODULES_EXTRA/trytond-company-logo $MODULES_TRYTON/company_logo
ln -v -s $MODULES_EXTRA/pyafipws-2.7 $SITEPACKAGES/pyafipws

echo "---------------------------------------------------------"
echo "Ejecutamos scripts de instalacion de scenario base"
echo "---------------------------------------------------------"
cd $INSTALACION_ACTUAL
python2 scenario_base.py -d $DATABASE_NAME -c $TRYTON_CONFIG_FILE -l $DATABASE_HOST

echo "----------------------------------------------------------------"
echo "Finalizamos deploy de instalacion TRYTON Localizacion Argentina."
echo "----------------------------------------------------------------"
