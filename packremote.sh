#!/bin/bash
git add . && git commit -m "$(date)" && git push
# Variables
SERVER_USER="catcoder"
SERVER_IP="localhost"
REMOTE_DIR="/home/catcoder/shared/shopifylambda"
ZIP_FILE="lambda_function.zip"
AWS_LAMBDA_FUNCTION="shopify"
GIT_BRANCH="develop_ms" # Cambia esto por la rama que desees
# Conexión SSH y ejecución de comandos remotos
ssh ${SERVER_USER}@${SERVER_IP} -p 2222 << EOF
    # Navegar al directorio
    cd ${REMOTE_DIR}

    # Cambiar a la rama especificada
    git checkout ${GIT_BRANCH}

    # Hacer pull de la última versión
    git pull origin ${GIT_BRANCH}

    # Ejecutar el script de empaquetado
    ./package.sh
EOF

# Descargar el archivo lambda_function.zip desde el servidor
scp -P 2222 ${SERVER_USER}@${SERVER_IP}:${REMOTE_DIR}/${ZIP_FILE} .

# Subir el archivo a AWS Lambda
aws lambda update-function-code --function-name ${AWS_LAMBDA_FUNCTION} --zip-file fileb://${ZIP_FILE} >> /tmp/null

# Mensaje de finalización
echo "Archivo ${ZIP_FILE} subido a AWS Lambda para la función ${AWS_LAMBDA_FUNCTION}"
