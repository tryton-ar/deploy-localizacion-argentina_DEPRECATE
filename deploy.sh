#!/bin/bash

# Se loggea en /var/log/syslog
exec 1> >(logger -s -t $(basename $0)) 2>&1

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
    --database-host)
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

if [ ! -f $VERSION ]; then
    echo "Debemos definir que version de Tryton queremos instalar" >&2
    echo "Por defecto usamos la version: 3.4" >&2
    VERSION="3.4"
    exit 1
fi

DATABASE_NAME=${DATABASE}_${VERSION}
DATABASE_NAME=${DATABASE_NAME//./_}
DATABASE_NAME=${DATABASE_NAME////_}

source `which virtualenvwrapper.sh`

if [ ! -f $TRYTON_CONFIG_FILE ]; then
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

echo "---------------------------------------------------------"
echo "Comenzamos instalacion de paquetes pip"
echo "---------------------------------------------------------"
pip install -r requirements-trytond-3.4.txt

echo "---------------------------------------------------------"
echo "Instalar pyafipws"
echo "---------------------------------------------------------"

cdsitepackages
wget https://github.com/reingart/pyafipws/archive/2.7.tar.gz 
tar zxvf 2.7.tar.gz
mv pyafipws-2.7 pyafipws
rm 2.7.tar.gz

echo "---------------------------------------------------------"
echo "Ejecutamos scripts de instalacion de scenario base"
echo "---------------------------------------------------------"
python2 scenario_base.py -d $DATABASE_NAME -c $TRYTON_CONFIG_FILE -a admin -l $DATABASE_HOST

echo "----------------------------------------------------------------"
echo "Finalizamos deploy de instalacion TRYTON Localizacion Argentina."
echo "----------------------------------------------------------------"
